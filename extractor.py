"""
TG-REAPER: Telegram Reconnaissance & Extraction Advanced Framework
A professional OSINT tool for Telegram intelligence gathering
"""

import re
import csv
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import FloodWaitError, ChannelPrivateError
from tqdm.asyncio import tqdm
from colorama import Fore, Style, init
import sqlite3
from typing import Dict, Set, List, Optional
import logging
from hashlib import sha256

init(autoreset=True)

# --- CONFIGURATION ---
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER'

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ADVANCED REGEX PATTERNS ---
PATTERNS = {
    'telegram_id': re.compile(r'(?<!\w)@([a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9])'),
    'email': re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
    'phone': re.compile(r'(?:\+|00)?(?:98|1)?9\d{9}|(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'),
    'url': re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'),
    'ip': re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    'btc_wallet': re.compile(r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'),
    'eth_wallet': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
    'trx_wallet': re.compile(r'\bT[a-zA-Z0-9]{33}\b'),
    'card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    'domain': re.compile(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'),
    'hashtag': re.compile(r'#[a-zA-Z0-9_\u0600-\u06FF]+'),
    'mention': re.compile(r'@[a-zA-Z0-9_]+'),
    'sheba': re.compile(r'IR\d{24}'),  # Iranian SHEBA numbers
    'national_id': re.compile(r'\b\d{10}\b'),  # Iranian National ID
}

# --- SCAM INDICATORS (Keywords for flagging suspicious content) ---
SCAM_KEYWORDS = [
    'wallet', 'deposit', 'usdt', 'btc', 'eth', 'crypto', 'investment',
    'profit', 'guarantee', 'double', 'triple', 'earn', 'contact admin',
    'vip', 'premium', 'signal', 'free money', 'click here', 'urgent',
    'limited time', 'bonus', 'reward', 'airdrop', 'withdraw'
]


class DatabaseManager:
    """SQLite database manager for persistent data storage"""
    
    def __init__(self, db_name='scraper_data.db'):
        self.db_name = db_name
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """Initialize database tables"""
        self.conn = sqlite3.connect(self.db_name)
        cursor = self.conn.cursor()
        
        # Main data extraction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS extracted_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                data_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence_score INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_id INTEGER,
                UNIQUE(source, data_type, value)
            )
        ''')
        
        # Scraping statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                total_messages INTEGER,
                total_members INTEGER DEFAULT 0,
                media_downloaded INTEGER DEFAULT 0,
                risk_score INTEGER DEFAULT 0,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT
            )
        ''')
        
        # Flagged messages table (for suspicious content)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS flagged_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                message_id INTEGER,
                message_text TEXT,
                flag_reason TEXT,
                risk_level TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def save_data(self, source: str, data_type: str, values: Set[str], 
                  confidence: int = 50, message_id: int = None):
        """Save extracted data to database"""
        cursor = self.conn.cursor()
        for value in values:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO extracted_data 
                    (source, data_type, value, confidence_score, message_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (source, data_type, value, confidence, message_id))
            except Exception as e:
                logger.error(f"Error saving {data_type}: {e}")
        self.conn.commit()
    
    def flag_message(self, source: str, message_id: int, text: str, 
                     reason: str, risk_level: str):
        """Flag suspicious messages"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO flagged_messages (source, message_id, message_text, flag_reason, risk_level)
                VALUES (?, ?, ?, ?, ?)
            ''', (source, message_id, text[:500], reason, risk_level))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error flagging message: {e}")
    
    def save_stats(self, target: str, stats: Dict):
        """Save scraping statistics"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO scrape_stats 
            (target, total_messages, total_members, media_downloaded, risk_score, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            target,
            stats.get('total_messages', 0),
            stats.get('total_members', 0),
            stats.get('media_count', 0),
            stats.get('risk_score', 0),
            stats.get('start_time'),
            stats.get('end_time'),
            stats.get('status', 'completed')
        ))
        self.conn.commit()
    
    def get_stats(self, source: str) -> Dict:
        """Retrieve statistics for a specific source"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT data_type, COUNT(*) 
            FROM extracted_data 
            WHERE source = ? 
            GROUP BY data_type
        ''', (source,))
        return dict(cursor.fetchall())
    
    def get_cross_channel_data(self, data_value: str) -> List[str]:
        """Find which channels contain the same data (e.g., same wallet)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT source 
            FROM extracted_data 
            WHERE value = ?
        ''', (data_value,))
        return [row[0] for row in cursor.fetchall()]
    
    def export_to_csv(self, source: str, output_file: str):
        """Export data to CSV format"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT data_type, value, confidence_score, timestamp 
            FROM extracted_data 
            WHERE source = ?
            ORDER BY data_type, confidence_score DESC
        ''', (source,))
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Value', 'Confidence', 'Timestamp'])
            writer.writerows(cursor.fetchall())
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class IntelligenceAnalyzer:
    """Analyze content for suspicious patterns and calculate risk scores"""
    
    @staticmethod
    def calculate_suspicion_score(text: str, extracted_data: Dict) -> int:
        """Calculate suspicion score based on content patterns"""
        score = 0
        text_lower = text.lower() if text else ""
        
        # Check for scam keywords
        keyword_matches = sum(1 for keyword in SCAM_KEYWORDS if keyword in text_lower)
        score += keyword_matches * 10
        
        # Financial indicators
        if extracted_data.get('btc_wallet') or extracted_data.get('eth_wallet') or extracted_data.get('trx_wallet'):
            score += 30
        
        if extracted_data.get('card'):
            score += 40
        
        # Multiple contact methods (suspicious)
        contact_types = sum(1 for k in ['email', 'phone', 'telegram_id'] if extracted_data.get(k))
        if contact_types >= 2:
            score += 20
        
        # URLs + financial data = likely scam
        if extracted_data.get('url') and (extracted_data.get('btc_wallet') or extracted_data.get('card')):
            score += 25
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def get_risk_level(score: int) -> str:
        """Convert numeric score to risk level"""
        if score >= 70:
            return "HIGH"
        elif score >= 40:
            return "MEDIUM"
        elif score >= 20:
            return "LOW"
        else:
            return "MINIMAL"
    
    @staticmethod
    def detect_flag_reasons(text: str, extracted_data: Dict) -> List[str]:
        """Identify specific reasons for flagging"""
        reasons = []
        text_lower = text.lower() if text else ""
        
        if any(keyword in text_lower for keyword in ['wallet', 'deposit', 'usdt']):
            reasons.append("Crypto transaction request")
        
        if extracted_data.get('card'):
            reasons.append("Credit card number detected")
        
        if 'guarantee' in text_lower or 'double' in text_lower:
            reasons.append("Unrealistic promises")
        
        if 'urgent' in text_lower or 'limited time' in text_lower:
            reasons.append("Urgency tactics")
        
        return reasons


class UltimateScraper:
    """Main scraper class for Telegram intelligence gathering"""
    
    def __init__(self, api_id, api_hash, phone_number):
        self.client = TelegramClient('session_ult', api_id, api_hash)
        self.phone = phone_number
        self.data: Dict[str, Set[str]] = {k: set() for k in PATTERNS.keys()}
        self.db = DatabaseManager()
        self.analyzer = IntelligenceAnalyzer()
        self.stats = {
            'total_messages': 0,
            'media_count': 0,
            'error_count': 0,
            'flagged_count': 0,
            'total_members': 0,
            'risk_score': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Create output directories
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / 'exports').mkdir(exist_ok=True)
        (self.output_dir / 'media').mkdir(exist_ok=True)
        (self.output_dir / 'evidence').mkdir(exist_ok=True)

    async def connect(self):
        """Establish connection to Telegram"""
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}🚀 TG-REAPER: Telegram Intelligence Framework v2.0{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        
        await self.client.start(phone=self.phone)
        me = await self.client.get_me()
        print(f"{Fore.GREEN}✓ Authenticated as: {me.username} ({me.first_name}){Style.RESET_ALL}")
        print(f"{Fore.GREEN}✓ User ID: {me.id}{Style.RESET_ALL}\n")

    def extract(self, text: str, message_id: int = None) -> Dict[str, Set[str]]:
        """Extract patterns from text and return what was found"""
        if not text:
            return {}
        
        found = {}
        for key, pattern in PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                self.data[key].update(matches)
                found[key] = set(matches)
        
        return found

    async def scrape_members(self, entity) -> List[Dict]:
        """Extract channel/group members"""
        members = []
        try:
            print(f"{Fore.YELLOW}[*] Extracting members...{Style.RESET_ALL}")
            offset = 0
            limit = 200
            
            while True:
                try:
                    participants = await self.client(GetParticipantsRequest(
                        entity, ChannelParticipantsSearch(''), offset, limit, hash=0
                    ))
                    
                    if not participants.users:
                        break
                    
                    for user in participants.users:
                        member_info = {
                            'id': user.id,
                            'username': user.username or 'N/A',
                            'first_name': user.first_name or '',
                            'last_name': user.last_name or '',
                            'phone': user.phone or 'N/A',
                            'is_bot': user.bot,
                            'is_verified': getattr(user, 'verified', False)
                        }
                        members.append(member_info)
                    
                    offset += len(participants.users)
                    
                    if len(participants.users) < limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Member extraction error: {e}")
                    break
            
            self.stats['total_members'] = len(members)
            print(f"{Fore.GREEN}✓ Extracted {len(members)} members{Style.RESET_ALL}")
            
        except ChannelPrivateError:
            print(f"{Fore.RED}✗ Cannot access members (private channel){Style.RESET_ALL}")
        except Exception as e:
            logger.error(f"Member scraping error: {e}")
        
        return members

    async def download_media(self, message, target_name: str) -> Optional[str]:
        """Download media files from messages"""
        try:
            media_dir = self.output_dir / 'media' / target_name
            media_dir.mkdir(parents=True, exist_ok=True)
            
            path = await self.client.download_media(
                message.media, 
                file=str(media_dir)
            )
            
            if path:
                self.stats['media_count'] += 1
                return path
        except Exception as e:
            logger.error(f"Media download error: {e}")
        
        return None

    def save_evidence(self, target_name: str, message_id: int, text: str, 
                      extracted: Dict, risk_level: str):
        """Save evidence of suspicious messages"""
        evidence_dir = self.output_dir / 'evidence' / target_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        evidence = {
            'message_id': message_id,
            'timestamp': datetime.now().isoformat(),
            'risk_level': risk_level,
            'text': text[:1000],  # Limit text length
            'extracted_data': {k: list(v) for k, v in extracted.items()},
            'text_hash': sha256(text.encode()).hexdigest()
        }
        
        filename = f"evidence_{message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(evidence_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(evidence, f, indent=2, ensure_ascii=False)

    async def scrape(self, target: str, limit: int = None, 
                    download_media: bool = False, evidence_mode: bool = False):
        """Main scraping function"""
        try:
            entity = await self.client.get_entity(target)
            target_name = getattr(entity, 'username', None) or str(entity.id)
            
            # Display target information
            print(f"\n{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}📊 Target Intelligence{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")
            print(f"  Title: {getattr(entity, 'title', 'N/A')}")
            print(f"  Username: @{target_name}")
            print(f"  ID: {entity.id}")
            print(f"  Type: {type(entity).__name__}")
            print(f"  Evidence Mode: {'ENABLED' if evidence_mode else 'DISABLED'}")
            print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")
            
            self.stats['start_time'] = datetime.now().isoformat()
            
            # Extract members if possible
            members = await self.scrape_members(entity)
            
            offset_id = 0
            total = 0
            
            pbar = tqdm(
                total=limit if limit else 0, 
                desc=f"{Fore.GREEN}Analyzing Messages{Style.RESET_ALL}",
                unit="msg",
                colour="green",
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]'
            )

            while True:
                try:
                    history = await self.client(GetHistoryRequest(
                        peer=entity,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=100,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    if not history.messages:
                        break

                    for msg in history.messages:
                        # Extract text patterns
                        extracted = {}
                        if msg.message:
                            extracted = self.extract(msg.message, msg.id)
                            
                            # Calculate risk score
                            score = self.analyzer.calculate_suspicion_score(
                                msg.message, extracted
                            )
                            
                            # Flag suspicious messages
                            if score >= 40:
                                risk_level = self.analyzer.get_risk_level(score)
                                reasons = self.analyzer.detect_flag_reasons(
                                    msg.message, extracted
                                )
                                
                                self.db.flag_message(
                                    target_name,
                                    msg.id,
                                    msg.message,
                                    ', '.join(reasons),
                                    risk_level
                                )
                                
                                self.stats['flagged_count'] += 1
                                
                                # Save evidence if enabled
                                if evidence_mode and score >= 60:
                                    self.save_evidence(
                                        target_name,
                                        msg.id,
                                        msg.message,
                                        extracted,
                                        risk_level
                                    )
                        
                        # Download media if requested
                        if download_media and msg.media:
                            await self.download_media(msg, target_name)
                        
                        total += 1
                        pbar.update(1)
                        
                        if limit and total >= limit:
                            pbar.close()
                            self.stats['total_messages'] = total
                            self.stats['end_time'] = datetime.now().isoformat()
                            return

                    offset_id = history.messages[-1].id
                    
                    # Adaptive delay to avoid flood
                    await asyncio.sleep(0.5)
                    
                except FloodWaitError as e:
                    wait_time = e.seconds
                    print(f"\n{Fore.RED}⚠ FloodWait: Pausing for {wait_time}s{Style.RESET_ALL}")
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    self.stats['error_count'] += 1
                    logger.error(f"Message processing error: {e}")
                    break

            pbar.close()
            self.stats['total_messages'] = total
            self.stats['end_time'] = datetime.now().isoformat()
            
            # Calculate overall risk score
            if total > 0:
                self.stats['risk_score'] = int((self.stats['flagged_count'] / total) * 100)
            
            # Save members data
            if members:
                self.save_members(members, target_name)

        except Exception as e:
            logger.error(f"Scraping error: {e}")
            print(f"{Fore.RED}✗ Error: {e}{Style.RESET_ALL}")

    def save_members(self, members: List[Dict], target_name: str):
        """Save member information to file"""
        members_file = self.output_dir / 'exports' / f'{target_name}_members.json'
        
        with open(members_file, 'w', encoding='utf-8') as f:
            json.dump(members, f, indent=4, ensure_ascii=False)
        
        print(f"{Fore.GREEN}✓ Members saved: {members_file}{Style.RESET_ALL}")

    async def save_results(self, target: str):
        """Save all collected data and generate reports"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = str(target).replace('https://', '').replace('http://', '').replace('t.me/', '')
        clean_name = re.sub(r'[\\/*?:"<>|]', '_', clean_name)
        
        base_name = f"intel_{clean_name}_{ts}"
        
        # Save to database
        for data_type, values in self.data.items():
            if values:
                # Calculate confidence based on data type
                confidence = 70 if data_type in ['btc_wallet', 'eth_wallet', 'card'] else 50
                self.db.save_data(clean_name, data_type, values, confidence)
        
        # Save statistics
        self.db.save_stats(clean_name, self.stats)
        
        # Generate JSON intelligence report
        json_file = self.output_dir / 'exports' / f'{base_name}.json'
        
        # Check for cross-channel correlation
        cross_channel = {}
        for data_type, values in self.data.items():
            for value in list(values)[:5]:  # Check first 5 of each type
                channels = self.db.get_cross_channel_data(value)
                if len(channels) > 1:
                    cross_channel[value] = channels
        
        intelligence_report = {
            'target': target,
            'timestamp': ts,
            'risk_assessment': {
                'overall_score': self.stats['risk_score'],
                'risk_level': self.analyzer.get_risk_level(self.stats['risk_score']),
                'flagged_messages': self.stats['flagged_count'],
                'total_analyzed': self.stats['total_messages']
            },
            'statistics': self.stats,
            'extracted_indicators': {k: list(v) for k, v in self.data.items() if v},
            'cross_channel_correlation': cross_channel,
            'metadata': {
                'collection_method': 'TG-REAPER v2.0',
                'data_integrity_hash': sha256(json.dumps(self.stats).encode()).hexdigest()
            }
        }
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(intelligence_report, f, indent=4, ensure_ascii=False)

        # Generate CSV export
        csv_file = self.output_dir / 'exports' / f'{base_name}.csv'
        self.db.export_to_csv(clean_name, str(csv_file))

        # Display comprehensive results
        print(f"\n{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}📈 INTELLIGENCE REPORT{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
        print(f"  Target: {target}")
        print(f"  Total Messages Analyzed: {self.stats['total_messages']}")
        print(f"  Members Extracted: {self.stats['total_members']}")
        print(f"  Media Downloaded: {self.stats['media_count']}")
        print(f"  Flagged Messages: {self.stats['flagged_count']}")
        print(f"  Processing Errors: {self.stats['error_count']}")
        
        risk_colo Fore.RED if self.stats['risk_score'] >= 70 else \
                     Fore.YELLOW if self.stats['risk_score'] >= 40 else Fore.GREEN
        print(f"  {risk_color}Risk Score: {self.stats['risk_score']}/100 " + 
              f"({self.analyzer.get_risk_level(self.stats['risk_score'])}){Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}{'='*70}{Style.RESET_ALL}")
        
        # Display extracted indicators
        if any(self.data.values()):
            print(f"\n{Fore.CYAN}🎯 Extracted Indicators:{Style.RESET_ALL}")
            for k, v in sorte(self.data.items(), key=lambda x: len(x[1]), reverse=True):
                if v:
                    indicator_color = Fore.RED if k in ['btc_wallet', 'eth_wallet', 'card'] else Fore.YELLOW
                    print(f"  {indicator_color}•{Style.RESET_ALL} {k.replace('_', ' ').title()}: " +
                          f"{Fore.GREEN}{len(v)}{Style.RESET_ALL}")
