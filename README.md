# 🕵️‍♂️ CyberScraper Pro V2

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Telethon](https://img.shields.io/badge/Telethon-Async-green.svg)
![Rich](https://img.shields.io/badge/UI-Rich-purple.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

**CyberScraper Pro V2** is a high-performance, asynchronous Telegram OSINT tool designed for researchers, data analysts, and cybersecurity professionals. 

It automates the extraction of sensitive data (Emails, Crypto Wallets, IPs, Cards, etc.) from Telegram public channels and groups using the Telegram API (`Telethon`). It features a modern TUI (Terminal User Interface), SQLite database integration for data persistence, and advanced filtering capabilities.

---

## 🚀 Key Features

*   **⚡ Asynchronous Core:** Built on `Telethon` and `asyncio` for blazing fast scraping speeds.
*   **💾 SQLite Database:** Automatically saves every found item to a local database (`scraped_data.db`). No duplicates, no data loss on crashes.
*   **🎨 Rich UI:** Beautiful terminal interface with real-time progress bars, spinners, and formatted tables.
*   **🔗 Hidden Link Extraction:** Detects and extracts URLs hidden behind Markdown text (e.g., `[Click Here](http://malicious-site.com)`).
*   **⏳ Time Travel Filter:** Option to scrape only messages from the last `X` days (e.g., "Last 30 days").
*   **💎 Advanced Regex Patterns:** Detects modern assets including **TON**, **Solana**, **TRON**, and private keys.
*   **📂 Export Options:** Export data per target to `.CSV` format for analysis in Excel or other tools.
*   **🛡️ Session Management:** Handles `FloodWait` errors automatically to prevent account bans.

---

## 👁️ Supported Patterns

CyberScraper Pro V2 automatically detects and categorizes the following data types:

| Category | Patterns Detected |
| :--- | :--- |
| **Identity** | Emails, Iranian Mobile Numbers (+98) |
| **Financial** | Credit Cards (16 digits) |
| **Crypto (L1)** | Bitcoin (`bc1`, `1`, `3`), Ethereum/BSC (`0x...`) |
| **Crypto (Alt)** | **TON** (The Open Network), **Solana**, **TRON** |
| **Network** | IPv4 Addresses, URLs (HTTP/HTTPS) |
| **Secrets** | Private Keys (Hex), API Keys (e.g., Stripe `sk_live`) |

---

## 🛠️ Installation

### Prerequisites
*   Python 3.8 or higher.
*   A Telegram account.
*   API ID and Hash from [my.telegram.org](https://my.telegram.org).

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/CyberScraper-V2.git
cd CyberScraper-V2

### Step 2: Install Dependencies
bash
pip install telethon rich python-dotenv aiofiles

---

## ⚙️ Configuration

1.  Create a file named `.env` in the root directory of the project.
2.  Add your Telegram credentials (get them from [my.telegram.org](https://my.telegram.org)):

env
API_ID=12345678
API_HASH=your_32_char_api_hash_here
PHONE_NUMBER=+989123456789

> **Note:** The `PHONE_NUMBER` must include the country code (e.g., +1, +98, +44).

---

## 🖥️ Usage

Run the script using Python:

bash
python scraper.py

### Main Menu
Once launched, you will see the interactive menu:

1.  **Scrape a Target:**
*   Enter the `Username` (e.g., `@durov`) or `Link`.
*   **Limit:** (Optional) Set max number of messages to scan.
*   **Days Back:** (Optional) Scan only messages from the last X days.

2.  **Export Data:**
*   Enter the username you previously scraped.
*   The tool will generate a `.csv` file with all findings for that target.

3.  **Exit:**
*   Closes the session and database connection safely.

---

## 🗄️ Database Structure

The tool uses a lightweight SQLite database (`scraped_data.db`) with two main tables:

1.  **`sources`**: Stores info about the Channels/Groups scanned.
2.  **`data`**: Stores the actual extracted items, linked to the source message ID.

This ensures that if you scan the same channel twice, **duplicate entries are ignored** automatically.

---

## ⚠️ Disclaimer

This tool is developed for **educational purposes and legitimate cybersecurity research only** (OSINT).
*   **Do not** use this tool to infringe on privacy or collect personal data without consent.
*   **Do not** use this tool for illegal activities such as carding or hacking.
*   The developer assumes **no responsibility** for how this tool is used.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

[MIT](https://choosealicense.com/licenses/mit/)
