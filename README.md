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
