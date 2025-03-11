# Telegram Data Extractor

A Python tool for extracting contact information (Telegram IDs, emails, and phone numbers) from Telegram groups and channels.

## Overview

This tool connects to the Telegram API and scans messages in specified groups or channels to extract and collect:
- Telegram usernames (@username)
- Email addresses
- Phone numbers

All extracted data is saved to a CSV file for easy access and further processing.

## Features

- Authenticate with Telegram using official API
- Extract contact information from public groups or channels
- Process message history efficiently
- Detect patterns using regular expressions
- Export data to CSV format
- Remove duplicates automatically
- Rate limiting to avoid API restrictions

## Requirements

- Python 3.6+
- Telethon library
- Telegram API credentials (API ID and API Hash)

## Installation

1. Clone the repository:git clone https://github.com/yourusername/telegram-data-extractor.git cd telegram-data-extractor
2. ## Sample Output

Here's an example of what the exported CSV file looks like:

![Sample CSV Output](images/sample_output.png)
## Sample Output

Here's an example of what the exported CSV file looks like:

| Username | Email | Phone Number |
|----------|-------|--------------|
| @user1 | user1@example.com | +1 (123) 456-7890 |
| @telegram_user | contact@gmail.com | +44 7911 123456 |
| @john_doe | john@company.org | 555-123-4567 |

