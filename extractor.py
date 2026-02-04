import re
import csv
import json
import asyncio
import os
from datetime import datetime
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.errors import FloodWaitError
from tqdm.asyncio import tqdm
from colorama import Fore, Style, init

init(autoreset=True)

# --- CONFIG ---
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER'

# --- REGEX ---
PATTERNS = {
    'telegram_id': re.compile(r'(?<!\w)@([a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9])'),
    'email': re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    'phone': re.compile(r'(?:\+|00)?(?:98|1)?9\d{9}|(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'),
    'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'),
    'ip': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'btc_wallet': re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'),
    'eth_wallet': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
    'trx_wallet': re.compile(r'\bT[a-zA-Z0-9]{33}\b'),
    'card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
}

class UltimateScraper:
    def __init__(self, api_id, api_hash, phone_number):
        self.client = TelegramClient('session_ult', api_id, api_hash)
        self.phone = phone_number
        self.data = {k: set() for k in PATTERNS.keys()}

    async def connect(self):
        print(f"{Fore.CYAN}[*] Connecting...{Style.RESET_ALL}")
        await self.client.start(phone=self.phone)
        me = await self.client.get_me()
        print(f"{Fore.GREEN}[+] Logged in as: {me.username}{Style.RESET_ALL}")

    def extract(self, text):
        if not text: return
        for key, pattern in PATTERNS.items():
            self.data[key].update(pattern.findall(text))

    async def scrape(self, target, limit=None):
        try:
            entity = await self.client.get_entity(target)
            print(f"{Fore.YELLOW}[*] Target: {entity.title} ({entity.id}){Style.RESET_ALL}")
            
            offset_id = 0
            total = 0
            pbar = tqdm(total=limit if limit else 0, desc="Scraping", unit="msg", colour="green")

            while True:
                try:
                    history = await self.client(GetHistoryRequest(
                        peer=entity, offset_id=offset_id, offset_date=None,
                        add_offset=0, limit=100, max_id=0, min_id=0, hash=0
                    ))
                    
                    if not history.messages: break

                    for msg in history.messages:
                        if msg.message:
                            self.extract(msg.message)
                        
                        total += 1
                        pbar.update(1)
                        if limit and total >= limit: return

                    offset_id = history.messages[-1].id
                    
                except FloodWaitError as e:
                    print(f"{Fore.RED}[!] FloodWait: Sleeping {e.seconds}s{Style.RESET_ALL}")
                    await asyncio.sleep(e.seconds)
                except Exception:
                    break

            pbar.close()

        except Exception as e:
            print(f"{Fore.RED}[!] Error: {e}{Style.RESET_ALL}")

    async def save_results(self, target):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = str(target).replace('@', '').replace(' ', '_')
        base = f"data_{name}_{ts}"
        
        # Save JSON
        json_out = {k: list(v) for k, v in self.data.items()}
        with open(f"{base}.json", 'w', encoding='utf-8') as f:
            json.dump(json_out, f, indent=4)

        # Save CSV
        with open(f"{base}.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Value'])
            for k, v in self.data.items():
                for item in v:
                    writer.writerow([k, item])

        print(f"\n{Fore.GREEN}[+] Saved: {base}.csv / .json{Style.RESET_ALL}")
        for k, v in self.data.items():
            if v: print(f"   - {k}: {len(v)}")

    async def run(self):
        await self.connect()
        while True:
            print(f"\n{Fore.BLUE}--- MENU ---{Style.RESET_ALL}")
            target = input("Target (User/Link/ID) [q to quit]: ").strip()
            if target.lower() == 'q': break
            
            lim = input("Limit (Empty for all): ").strip()
            limit = int(lim) if lim.isdigit() else None
            
            # Reset data
            self.data = {k: set() for k in PATTERNS.keys()}
            
            await self.scrape(target, limit)
            await self.save_results(target)

        await self.client.disconnect()

if __name__ == '__main__':
    if 'YOUR_' in API_ID:
        print("Please set API_ID/HASH in the script.")
    else:
        app = UltimateScraper(API_ID, API_HASH, PHONE_NUMBER)
        asyncio.run(app.run())
