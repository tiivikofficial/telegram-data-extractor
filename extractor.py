import os
import re
import asyncio
import sqlite3
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv

# Telethon Imports
from telethon import TelegramClient
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# Rich UI Imports
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.traceback import install

# Setup
install()
load_dotenv()
console = Console()

# --- CONFIGURATION ---
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
SESSION_NAME = os.getenv('SESSION_NAME', 'cyber_session')
TELEGRAM_2FA_PASSWORD = os.getenv('TELEGRAM_2FA_PASSWORD')
DB_NAME = os.getenv('DB_NAME', 'scraped_data.db')

# --- ADVANCED REGEX PATTERNS ---
PATTERNS = {
    'telegram_user': re.compile(r'(?<!\w)@([a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9])'),
    'email': re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    'phone_ir': re.compile(r'(?:\+98|0)?9\d{9}'),
    'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'),
    'ip_v4': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'btc_wallet': re.compile(r'\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'),
    'eth_bsc_wallet': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
    'trx_wallet': re.compile(r'\bT[a-zA-Z0-9]{33}\b'),
    'solana_wallet': re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'),
    'ton_wallet': re.compile(r'\b(?:UQ|EQ)[a-zA-Z0-9_-]{46}\b'),
    'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    'private_key': re.compile(r'\b[a-fA-F0-9]{64}\b'), # Hex format
    'api_key': re.compile(r'sk_live_[0-9a-zA-Z]{24}'), # Example Stripe
}

def is_valid_ipv4(value):
    """Return True only for syntactically valid dotted-quad IPv4 addresses."""
    try:
        octets = value.split('.')
        return len(octets) == 4 and all(0 <= int(octet) <= 255 for octet in octets)
    except (TypeError, ValueError):
        return False


def is_valid_credit_card(value):
    """Validate a candidate PAN with the Luhn checksum after removing separators."""
    digits = re.sub(r'\D', '', value)
    if len(digits) != 16 or len(set(digits)) == 1:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(map(int, digits)):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def clean_extracted_value(data_type, value):
    """Normalize extracted IOCs and reject obvious false positives."""
    value = value.strip().rstrip('.,;:!?)]}')
    if data_type in {'telegram_user', 'email'}:
        return value.lower()
    if data_type == 'ip_v4':
        return value if is_valid_ipv4(value) else None
    if data_type == 'credit_card':
        return value if is_valid_credit_card(value) else None
    return value or None


# --- DATABASE MANAGER ---
class DatabaseHandler:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                title TEXT,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                data_type TEXT,
                value TEXT,
                message_id INTEGER,
                found_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_id, data_type, value)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_state (
                source_id INTEGER PRIMARY KEY,
                last_message_id INTEGER NOT NULL DEFAULT 0,
                last_scanned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_id) REFERENCES sources(id)
            )
        ''')
        self.conn.commit()

    def add_source(self, username, title):
        try:
            self.cursor.execute("INSERT OR IGNORE INTO sources (username, title) VALUES (?, ?)", (username, title))
            self.conn.commit()
            self.cursor.execute("SELECT id FROM sources WHERE username = ?", (username,))
            return self.cursor.fetchone()[0]
        except Exception as e:
            console.print(f"[red]DB Error:[/red] {e}")
            return None

    def insert_data(self, source_id, data_type, value, msg_id):
        """Insert one finding and report whether a new row was created."""
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO data (source_id, data_type, value, message_id) VALUES (?, ?, ?, ?)",
                (source_id, data_type, value, msg_id)
            )
            return self.cursor.rowcount == 1
        except sqlite3.Error as e:
            console.print(f"[red]DB Error:[/red] {e}")
            return False
        # Commit happens in bulk or at end for speed

    def get_last_message_id(self, source_id):
        row = self.cursor.execute(
            "SELECT last_message_id FROM scan_state WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return int(row[0]) if row else 0

    def set_last_message_id(self, source_id, message_id):
        self.cursor.execute(
            """
            INSERT INTO scan_state (source_id, last_message_id, last_scanned_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(source_id) DO UPDATE SET
                last_message_id = excluded.last_message_id,
                last_scanned_at = CURRENT_TIMESTAMP
            """,
            (source_id, int(message_id)),
        )

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

# --- MAIN SCRAPER CLASS ---
class CyberScraper:
    def __init__(self):
        if not API_ID or not API_HASH:
            console.print("[bold red]Error:[/] API_ID or API_HASH not found in .env file!")
            exit(1)
            
        self.client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)
        self.db = DatabaseHandler(DB_NAME)
        self.stats = {k: 0 for k in PATTERNS.keys()}

    async def start(self):
        """Connect using the saved session and only prompt when a login is required."""
        console.print(
            Panel.fit(
                "[bold cyan]CyberScraper Pro V2[/bold cyan]\n"
                "[dim]Powered by Telethon & Rich[/dim]"
            )
        )

        if await self.client.is_user_authorized():
            me = await self.client.get_me()
        else:
            if not PHONE_NUMBER:
                raise RuntimeError(
                    "PHONE_NUMBER is missing from .env and no authorized Telegram session exists."
                )
            await self.client.send_code_request(PHONE_NUMBER)
            code = Prompt.ask("Telegram verification code", password=False).strip()
            try:
                await self.client.sign_in(
                    phone=PHONE_NUMBER,
                    code=code,
                )
            except SessionPasswordNeededError:
                if not TELEGRAM_2FA_PASSWORD:
                    raise RuntimeError(
                        "Telegram 2FA is enabled. Set TELEGRAM_2FA_PASSWORD in .env "
                        "instead of entering the password interactively."
                    )
                await self.client.sign_in(password=TELEGRAM_2FA_PASSWORD)
            me = await self.client.get_me()

        console.print(
            f"[green]✔ Connected as:[/green] "
            f"[bold]{getattr(me, 'username', None) or me.id}[/bold] "
            f"(+{getattr(me, 'phone', '')})"
        )

    def extract_from_text(self, text):
        """Extract normalized, de-duplicated indicators from message text."""
        results = []
        seen = set()
        if not text:
            return results
        for key, pattern in PATTERNS.items():
            for match in pattern.findall(text):
                if isinstance(match, tuple):
                    match = match[0]
                value = clean_extracted_value(key, match)
                if value is None:
                    continue
                identity = (key, value)
                if identity in seen:
                    continue
                seen.add(identity)
                results.append(identity)
        return results

    async def get_hidden_links(self, message):
        """Extracts links hidden behind text [Link](url)"""
        links = []
        if not message.entities: return links
        
        for entity in message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                links.append(('url', entity.url))
            elif isinstance(entity, MessageEntityUrl):
                # Usually caught by regex, but good fallback
                pass
        return links

    @staticmethod
    def message_link(source, message_id):
        """Build a public t.me message URL when the source has a username."""
        source = (source or "").strip().lstrip("@")
        return f"https://t.me/{source}/{int(message_id)}" if source and message_id else None

    @staticmethod
    def normalize_target(value):
        """Normalize common Telegram target forms without altering invite links."""
        value = (value or "").strip()
        for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
            if value.lower().startswith(prefix):
                value = value[len(prefix):]
                break
        value = value.split("?", 1)[0].split("#", 1)[0].strip("/")
        if value.startswith("@"):
            value = value[1:]
        if "/" in value or value.startswith("+"):
            raise ValueError("Enter a public Telegram username or t.me username link.")
        return value

    async def scrape_target(self, target_username, limit=None, days_back=None, incremental=False):
        target_username = self.normalize_target(target_username)
        if not target_username:
            raise ValueError("Target username cannot be empty.")
        if limit is not None and limit <= 0:
            raise ValueError("Limit must be greater than zero.")
        if days_back is not None and days_back <= 0:
            raise ValueError("Days back must be greater than zero.")

        try:
            entity = await self.client.get_entity(target_username)
            title = getattr(entity, 'title', target_username)
            source_id = self.db.add_source(target_username, title)
            if source_id is None:
                raise RuntimeError("Could not create or load the target source in SQLite.")

            last_message_id = self.db.get_last_message_id(source_id) if incremental else 0
            if incremental and last_message_id:
                console.print(
                    f"[cyan]Incremental scan:[/cyan] only messages newer than ID "
                    f"{last_message_id} will be checked."
                )

            console.print(
                f"\n[bold yellow]Target acquired:[/bold yellow] {title} "
                f"[dim](ID: {entity.id})[/dim]"
            )

            offset_date = None
            if days_back:
                offset_date = datetime.now(timezone.utc) - timedelta(days=days_back)
                console.print(
                    f"[blue]Filter:[/blue] Scraping messages after "
                    f"{offset_date.strftime('%Y-%m-%d')}"
                )

            msg_count = 0
            new_items_count = 0
            started_at = datetime.now(timezone.utc)
            highest_message_id = last_message_id

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed} msgs"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    f"[cyan]Scanning {target_username}...",
                    total=limit if limit else None
                )

                iterator_kwargs = {
                    "limit": limit,
                    "offset_date": offset_date,
                }
                if last_message_id:
                    iterator_kwargs["min_id"] = last_message_id

                async for message in self.client.iter_messages(entity, **iterator_kwargs):
                    msg_text = message.text or ""
                    caption = message.message or ""
                    full_text = f"{msg_text} {caption}"

                    extracted = self.extract_from_text(full_text)
                    extracted += await self.get_hidden_links(message)

                    for dtype, val in extracted:
                        if self.db.insert_data(source_id, dtype, val, message.id):
                            self.stats[dtype] += 1
                            new_items_count += 1

                    msg_count += 1
                    highest_message_id = max(highest_message_id, int(message.id))
                    progress.update(task, advance=1)

                    if msg_count % 50 == 0:
                        self.db.set_last_message_id(source_id, highest_message_id)
                        self.db.commit()

            if msg_count:
                self.db.set_last_message_id(source_id, highest_message_id)
            self.db.commit()

            elapsed = datetime.now(timezone.utc) - started_at
            console.print(
                f"[green]✔ Finished![/green] Scanned {msg_count} messages. "
                f"Added {new_items_count} new data points in "
                f"{elapsed.total_seconds():.1f}s."
            )

        except FloodWaitError as e:
            console.print(
                f"[bold red]!! FLOOD WAIT !![/bold red] "
                f"Sleeping for {e.seconds} seconds."
            )
            await asyncio.sleep(e.seconds)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    async def export_data(self, target_username):
        """Export target findings with source/message metadata to CSV and JSON."""
        target_username = self.normalize_target(target_username)
        clean_name = re.sub(r'[\\/*?:"<>|]', '_', target_username)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Fetch from DB
        self.db.cursor.execute("""
            SELECT s.username, s.title, d.data_type, d.value, d.message_id, d.found_at
            FROM data d
            JOIN sources s ON d.source_id = s.id
            WHERE s.username = ?
            ORDER BY d.found_at ASC, d.id ASC
        """, (target_username,))
        rows = self.db.cursor.fetchall()
        
        if not rows:
            console.print("[yellow]No data to export.[/yellow]")
            return

        # CSV Export
        filename_csv = f"export_{clean_name}_{ts}.csv"
        with open(filename_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Source', 'Source Title', 'Type', 'Value',
                'Message ID', 'Message Link', 'Found At'
            ])
            for row in rows:
                writer.writerow([*row[:4], row[4], self.message_link(row[0], row[4]), row[5]])

        # JSON Export
        filename_json = f"export_{clean_name}_{ts}.json"
        payload = [
            {
                "source": source,
                "source_title": source_title,
                "type": data_type,
                "value": value,
                "message_id": message_id,
                "message_link": self.message_link(source, message_id),
                "found_at": found_at,
            }
            for source, source_title, data_type, value, message_id, found_at in rows
        ]
        with open(filename_json, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        console.print(f"[blue]Exported:[/blue] {filename_csv}")
        console.print(f"[blue]Exported:[/blue] {filename_json}")

    def show_stats(self):
        table = Table(title="Session Statistics")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="magenta")
        
        for k, v in self.stats.items():
            if v > 0:
                table.add_row(k, str(v))
        
        console.print(table)

    async def main_loop(self):
        await self.start()
        
        while True:
            console.print("\n[bold]OPTIONS:[/bold]")
            console.print("1. [green]Scrape a Target[/green]")
            console.print("2. [blue]Export Data (from DB)[/blue]")
            console.print("3. [red]Exit[/red]")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3"], default="1")
            
            if choice == '1':
                target = Prompt.ask("Enter Target Username/Link")
                target = self.normalize_target(target)
                
                limit_str = Prompt.ask("Limit messages (Enter for all)", default="0")
                limit = int(limit_str) if limit_str.isdigit() and int(limit_str) > 0 else None
                
                days_str = Prompt.ask("How many days back? (Enter for all time)", default="0")
                days_back = int(days_str) if days_str.isdigit() and int(days_str) > 0 else None
                incremental = Confirm.ask(
                    "Only scan messages newer than the previous scan?",
                    default=False
                )

                await self.scrape_target(
                    target,
                    limit,
                    days_back,
                    incremental=incremental,
                )
                self.show_stats()
                
            elif choice == '2':
                target = Prompt.ask("Enter Target Username to export")
                target = self.normalize_target(target)
                await self.export_data(target)
                
            elif choice == '3':
                console.print("[bold]Goodbye![/bold]")
                self.db.close()
                await self.client.disconnect()
                break

if __name__ == '__main__':
    scraper = CyberScraper()
    asyncio.run(scraper.main_loop())
