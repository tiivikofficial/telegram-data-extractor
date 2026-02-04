import os
import re
import asyncio
import sqlite3
import csv
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Telethon Imports
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.errors import FloodWaitError

# Rich UI Imports
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.traceback import install

# Setup
install()
load_dotenv()
console = Console()

# --- CONFIGURATION ---
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')
SESSION_NAME = 'cyber_session'
DB_NAME = 'scraped_data.db'

# --- ADVANCED REGEX PATTERNS ---
PATTERNS = {
    'telegram_user': re.compile(r'(?<!\w)@([a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9])'),
    'email': re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    'phone_ir': re.compile(r'(?:\+98|0)?9\d{9}'),
    'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'),
    'ip_v4': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'btc_wallet': re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'),
    'eth_bsc_wallet': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
    'trx_wallet': re.compile(r'\bT[a-zA-Z0-9]{33}\b'),
    'solana_wallet': re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b'),
    'ton_wallet': re.compile(r'\bUQ[a-zA-Z0-9_-]{46}\b|\bEQ[a-zA-Z0-9_-]{46}\b'),
    'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    'private_key': re.compile(r'\b[a-fA-F0-9]{64}\b'), # Hex format
    'api_key': re.compile(r'sk_live_[0-9a-zA-Z]{24}'), # Example Stripe
}

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
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO data (source_id, data_type, value, message_id) VALUES (?, ?, ?, ?)",
                (source_id, data_type, value, msg_id)
            )
        except:
            pass 
        # Commit happens in bulk or at end for speed

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
        console.print(Panel.fit("[bold cyan]CyberScraper Pro V2[/bold cyan]\n[dim]Powered by Telethon & Rich[/dim]"))
        await self.client.start(phone=PHONE_NUMBER)
        me = await self.client.get_me()
        console.print(f"[green]✔ Connected as:[/green] [bold]{me.username}[/bold] (+{me.phone})")

    def extract_from_text(self, text):
        results = []
        if not text: return results
        for key, pattern in PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                # Cleaning
                if isinstance(match, tuple): match = match[0]
                match = match.strip()
                results.append((key, match))
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

    async def scrape_target(self, target_username, limit=None, days_back=None):
        try:
            entity = await self.client.get_entity(target_username)
            title = getattr(entity, 'title', target_username)
            source_id = self.db.add_source(target_username, title)
            
            console.print(f"\n[bold yellow]Target acquired:[/bold yellow] {title} [dim](ID: {entity.id})[/dim]")
            
            # Calculate date limit
            offset_date = None
            if days_back:
                offset_date = datetime.now() - timedelta(days=days_back)
                console.print(f"[blue]Filter:[/blue] Scraping messages after {offset_date.strftime('%Y-%m-%d')}")

            msg_count = 0
            new_items_count = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed} msgs"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(f"[cyan]Scanning {target_username}...", total=limit if limit else None)
                
                async for message in self.client.iter_messages(entity, limit=limit, offset_date=offset_date):
                    msg_text = message.text or ""
                    caption = message.message or "" # Sometimes text is in message field
                    full_text = f"{msg_text} {caption}"
                    
                    # 1. Regex Extraction
                    extracted = self.extract_from_text(full_text)
                    
                    # 2. Hidden Links extraction
                    extracted += await self.get_hidden_links(message)

                    # 3. Save to DB
                    for dtype, val in extracted:
                        self.db.insert_data(source_id, dtype, val, message.id)
                        self.stats[dtype] += 1
                        new_items_count += 1
                    
                    msg_count += 1
                    progress.update(task, advance=1)
                    
                    if msg_count % 50 == 0:
                        self.db.commit() # Periodic commit

            self.db.commit()
            console.print(f"[green]✔ Finished![/green] Scanned {msg_count} messages. Found {new_items_count} data points.")

        except FloodWaitError as e:
            console.print(f"[bold red]!! FLOOD WAIT !![/bold red] Sleeping for {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

    async def export_data(self, target_username):
        """Exports data for a specific target from DB to JSON/CSV"""
        clean_name = re.sub(r'[\\/*?:"<>|]', '_', target_username)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Fetch from DB
        self.db.cursor.execute("""
            SELECT d.data_type, d.value 
            FROM data d 
            JOIN sources s ON d.source_id = s.id 
            WHERE s.username = ?
        """, (target_username,))
        rows = self.db.cursor.fetchall()
        
        if not rows:
            console.print("[yellow]No data to export.[/yellow]")
            return

        # CSV Export
        filename_csv = f"export_{clean_name}_{ts}.csv"
        with open(filename_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Value'])
            writer.writerows(rows)
            
        console.print(f"[blue]Exported:[/blue] {filename_csv}")

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
                # Clean input
                target = target.replace('https://t.me/', '').replace('@', '').strip()
                
                limit_str = Prompt.ask("Limit messages (Enter for all)", default="0")
                limit = int(limit_str) if limit_str.isdigit() and int(limit_str) > 0 else None
                
                days_str = Prompt.ask("How many days back? (Enter for all time)", default="0")
                days_back = int(days_str) if days_str.isdigit() and int(days_str) > 0 else None

                # Reset stats for new run or keep cumulative? Let's keep cumulative for session
                await self.scrape_target(target, limit, days_back)
                self.show_stats()
                
            elif choice == '2':
                target = Prompt.ask("Enter Target Username to export")
                target = target.replace('https://t.me/', '').replace('@', '').strip()
                await self.export_data(target)
                
            elif choice == '3':
                console.print("[bold]Goodbye![/bold]")
                self.db.close()
                await self.client.disconnect()
                break

if __name__ == '__main__':
    scraper = CyberScraper()
    asyncio.run(scraper.main_loop())
