# 🕵️‍♂️ CyberScraper Pro V2

Asynchronous Telegram OSINT extraction tool built with Telethon and Rich.

> Use only on public data and in accordance with Telegram's Terms of Service and applicable law. Avoid collecting sensitive personal data without a legitimate purpose and appropriate authorization.

## Features

- ⚡ Async Telegram message scanning with Telethon
- 💾 SQLite persistence with duplicate protection
- 🔎 Extracts emails, Telegram usernames, URLs, IPv4 addresses, selected crypto identifiers, and other configured indicators
- 🔗 Extracts hidden Telegram text-entity links
- ⏳ Optional message-count and lookback-day limits
- 📊 Rich terminal progress and session statistics
- 📤 CSV and JSON exports
- 🛡️ Automatic handling of Telegram FloodWait pauses

## Installation

Requires Python 3.8+.

```bash
git clone https://github.com/tiivikofficial/telegram-data-extractor.git
cd telegram-data-extractor
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1

python -m pip install -r requirements.txt
```

## Configuration

Create a .env file in the project root:

```env
API_ID=12345678
API_HASH=your_32_char_api_hash_here
PHONE_NUMBER=+1234567890
SESSION_NAME=cyber_session
# TELEGRAM_2FA_PASSWORD=your_2fa_password
```

Get an API ID and API hash from https://my.telegram.org.

Never commit your real API credentials, 2FA password, or Telegram session files. On first login, the app asks only for the Telegram verification code. If 2-Step Verification is enabled, set TELEGRAM_2FA_PASSWORD in .env.

## Usage

```bash
python extractor.py
```

From the menu you can:

1. Scan a public Telegram target by username or t.me link.
2. Limit the number of messages and/or scan only the last N days.
3. Export the stored findings for a target to both CSV and JSON.
4. Exit cleanly and close the SQLite database/session.

Exported JSON has the shape:

```json
[
  {"type": "email", "value": "example@example.com"},
  {"type": "url", "value": "https://example.com"}
]
```

## Database

The local scraped_data.db SQLite database contains:

- sources: scanned target metadata
- data: extracted values linked to the source and message ID

Values are de-duplicated per source and type.

## Detection notes

The extractor performs lightweight validation for:

- IPv4 addresses (each octet must be 0–255)
- 16-digit credit-card candidates using a Luhn checksum
- Telegram usernames and email addresses are normalized to lowercase
- Duplicate (type, value) findings within a message are removed

Detection is pattern-based and should be treated as candidate data, not proof that an identifier is valid or active.

## Contributing

Pull requests are welcome. For larger changes, open an issue first.

## License

MIT.
