import re
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio
import csv
import os
from datetime import datetime

# You need to get these from https://my.telegram.org/
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
PHONE_NUMBER = 'YOUR_PHONE_NUMBER'

# Regular expressions for extracting data
TELEGRAM_ID_PATTERN = r'@([a-zA-Z][a-zA-Z0-9_]{3,30}[a-zA-Z0-9])'
EMAIL_PATTERN = r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
PHONE_PATTERN = r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}'

class TelegramExtractor:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = None
        
        # Data containers
        self.telegram_ids = set()
        self.emails = set()
        self.phone_numbers = set()
        
    async def connect(self):
        """Connect to Telegram client"""
        self.client = TelegramClient('session_name', self.api_id, self.api_hash)
        await self.client.start(phone=self.phone_number)
        print("Client connected successfully!")
        
    async def extract_from_entity(self, entity_username_or_id):
        """Extract data from a Telegram group or channel"""
        try:
            # Get the entity
            entity = await self.client.get_entity(entity_username_or_id)
            print(f"Extracting data from: {entity.title if hasattr(entity, 'title') else entity_username_or_id}")
            
            # Get the message history
            offset_id = 0
            limit = 100
            total_messages = 0
            total_extracted = 0
            
            while True:
                history = await self.client(GetHistoryRequest(
                    peer=entity,
                    offset_id=offset_id,
                    offset_date=None,
                    add_offset=0,
                    limit=limit,
                    max_id=0,
                    min_id=0,
                    hash=0
                ))
                
                # If there are no more messages
                if not history.messages:
                    break
                
                # Process each message
                for message in history.messages:
                    if message.message:
                        # Extract Telegram IDs
                        ids = re.findall(TELEGRAM_ID_PATTERN, message.message)
                        self.telegram_ids.update(ids)
                        
                        # Extract emails
                        emails = re.findall(EMAIL_PATTERN, message.message)
                        self.emails.update(emails)
                        
                        # Extract phone numbers
                        phones = re.findall(PHONE_PATTERN, message.message)
                        self.phone_numbers.update(phones)
                        
                        total_extracted += len(ids) + len(emails) + len(phones)
                
                # Update the offset
                offset_id = history.messages[-1].id
                total_messages += len(history.messages)
                print(f"Processed {total_messages} messages, found {total_extracted} data points...")
                
                # Sleep to avoid hitting rate limits
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error extracting data: {e}")
            
    async def save_results(self):
        """Save extracted data to CSV file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"telegram_extracted_data_{timestamp}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Type', 'Value'])
            
            for telegram_id in self.telegram_ids:
                writer.writerow(['Telegram ID', f'@{telegram_id}'])
                
            for email in self.emails:
                writer.writerow(['Email', email])
                
            for phone in self.phone_numbers:
                writer.writerow(['Phone Number', phone])
                
        print(f"Data saved to {filename}")
        print(f"Found {len(self.telegram_ids)} Telegram IDs, {len(self.emails)} emails, and {len(self.phone_numbers)} phone numbers.")
        
    async def run(self, entity_username_or_id):
        """Main method to run the extraction process"""
        await self.connect()
        await self.extract_from_entity(entity_username_or_id)
        await self.save_results()
        await self.client.disconnect()

# Example usage
async def main():
    # Create extractor instance
    extractor = TelegramExtractor(API_ID, API_HASH, PHONE_NUMBER)
    
    # Get target from user
    target = input("Enter the username or ID of the Telegram group/channel: ")
    
    # Run the extraction
    await extractor.run(target)

if __name__ == '__main__':
    # Run the main function
    asyncio.run(main())

