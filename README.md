
**Telegram Reconnaissance & Extraction Advanced Framework**

A professional OSINT (Open Source Intelligence) tool for Telegram intelligence gathering, designed for security researchers, threat analysts, and digital forensics professionals.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)

---

## 🎯 Features

### 📊 Data Extraction
- **Pattern Recognition**: Automatically extracts emails, phone numbers, crypto wallets (BTC/ETH/TRX), credit cards, URLs, IPs, domains, hashtags, mentions, and more
- **Member Intelligence**: Collects channel/group member information including usernames, names, and verification status
- **Media Archiving**: Downloads and organizes photos, videos, and files from target channels
- **Cross-Channel Analysis**: Identifies shared indicators across multiple channels

### 🔍 Intelligence Analysis
- **Risk Scoring**: Automatically calculates suspicion scores based on content patterns
- **Scam Detection**: Flags potentially fraudulent messages using keyword analysis
- **Evidence Collection**: Forensic-grade evidence preservation with SHA-256 hashing
- **Timeline Reconstruction**: Tracks when specific indicators first appeared

### 💾 Data Management
- **SQLite Database**: Persistent storage with automatic deduplication
- **Multiple Export Formats**: JSON intelligence reports and CSV data exports
- **Statistics Tracking**: Comprehensive scraping metrics and analytics
- **Cross-Reference Lookup**: Find which channels contain the same data points

### 🛡️ Advanced Capabilities
- **Adaptive Rate Limiting**: Smart delays to avoid Telegram flood restrictions
- **Error Recovery**: Automatic retry logic with detailed logging
- **Confidence Scoring**: Assigns reliability scores to extracted data
- **Batch Processing**: Handle multiple targets in sequence

---

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- Telegram account
- Telegram API credentials

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/tg-reaper.git
cd tg-reaper

### Step 2: Install Dependencies
bash
pip install telethon tqdm colorama

### Step 3: Get Telegram API Credentials
1. Visit https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note your `API_ID` and `API_HASH`

### Step 4: Configure
Edit `tg_reaper.py` and set your credentials:
python
API_ID = 'your_api_id_here'
API_HASH = 'your_api_hash_here'
PHONE_NUMBER = '+1234567890'

---

## 🚀 Usage

### Basic Usage
bash
python tg_reaper.py

### Interactive Menu
The tool provides an interactive menu where you can:
1. Enter target (username, link, or channel ID)
2. Set message limit (or leave empty for all messages)
3. Choose whether to download media
4. Enable evidence collection mode for high-risk targets

### Example Session

Target: @example_channel
Message Limit: 1000
Download media? (y/n): n
Enable evidence collection? (y/n): y

[Processing...]

✓ Analyzed 1000 messages
✓ Extracted 45 emails
✓ Extracted 12 crypto wallets
✓ Flagged 8 suspicious messages
✓ Risk Score: 67/100 (MEDIUM)

---

## 📂 Output Structure


output/
├── exports/
│   ├── intel_channelname_20240205_143022.json    # Intelligence report
│   ├── intel_channelname_20240205_143022.csv     # Data export
│   └── channelname_members.json                  # Member list
├── media/
│   └── channelname/                              # Downloaded media files
└── evidence/
└── channelname/                              # Flagged message evidence
└── evidence_12345_20240205_143022.json

---

## 🎓 Use Cases

### Security Research
- Identify phishing campaigns
- Track malware distribution channels
- Monitor threat actor communications

### Digital Forensics
- Collect evidence of fraudulent activity
- Preserve channel data for legal proceedings
- Generate forensic reports with integrity hashing

### Threat Intelligence
- Track cryptocurrency scams
- Monitor darknet market channels
- Identify shared infrastructure across threat groups

### OSINT Investigations
- Profile target channels and groups
- Map social networks and connections
- Uncover hidden relationships through cross-channel analysis

---

## 📊 Extracted Data Types

| Category | Examples | Use Case |
|----------|----------|----------|
| **Financial** | BTC/ETH/TRX wallets, credit cards, SHEBA numbers | Track payment methods in scams |
| **Contact** | Emails, phone numbers, Telegram IDs | Identify contact methods |
| **Infrastructure** | URLs, domains, IP addresses | Map attacker infrastructure |
| **Social** | Hashtags, mentions | Analyze campaigns and trends |
| **Identity** | National IDs (Iran) | Regional identity verification |

---

## 🔒 Security & Ethics

### Responsible Use
This tool is intended for:
- ✅ Security research
- ✅ Threat intelligence
- ✅ Digital forensics
- ✅ Educational purposes
- ✅ Authorized investigations

**NOT for:**
- ❌ Unauthorized surveillance
- ❌ Privacy invasion
- ❌ Harassment
- ❌ Illegal activities

### Privacy Considerations
- Only collect publicly available data
- Respect Telegram's Terms of Service
- Follow applicable laws and regulations
- Obtain proper authorization when required

---

## 🛠️ Technical Details

### Pattern Recognition Regex
The tool uses advanced regex patterns to extract:
- Telegram usernames: `@username`
- Emails: RFC 5322 compliant
- Phone numbers: International and Iranian formats
- Crypto wallets: BTC (Legacy, SegWit, Bech32), ETH, TRX
- Credit cards: Various formats with separators
- Iranian SHEBA: 24-digit IR format

### Risk Scoring Algorithm
Suspicion scores are calculated based on:
- Presence of scam keywords (10 points each)
- Financial indicators (30-40 points)
- Multiple contact methods (20 points)
- URL + financial data combination (25 points)
- Capped at 100 maximum

### Database Schema
**extracted_data**: Stores all extracted patterns with confidence scores  
**scrape_stats**: Tracks scraping sessions and statistics  
**flagged_messages**: Preserves suspicious message evidence  

---

## 🐛 Troubleshooting

### FloodWaitError
**Problem**: Telegram temporarily blocks requests  
**Solution**: The tool automatically waits; reduce scraping speed if persistent

### Session File Issues
**Problem**: Authentication errors  
**Solution**: Delete `session_ult.session` and re-authenticate

### Private Channel Access
**Problem**: Cannot extract members  
**Solution**: You must be a member of private channels; public channels have no restrictions

### Empty Results
**Problem**: No data extracted  
**Solution**: Check if target has messages; try different patterns; verify network connection

---

## 📈 Roadmap

- [ ] Multi-target batch processing
- [ ] AI-powered content classification
- [ ] Graph visualization of channel networks
- [ ] Web dashboard (Flask/FastAPI)
- [ ] Export to Excel with formatted sheets
- [ ] Proxy/Tor support
- [ ] Real-time monitoring mode
- [ ] Automated report generation

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## ⚠️ Disclaimer

This tool is provided for educational and research purposes only. Users are responsible for ensuring their use complies with applicable laws and Telegram's Terms of Service. The authors assume no liability for misuse or any damages caused by this software.

---

## 📧 Contact

For questions, suggestions, or security concerns:
- GitHub Issues: [Create an issue](https://github.com/yourusername/tg-reaper/issues)
- Email: security@example.com

---

## 🙏 Acknowledgments

- Built with [Telethon](https://github.com/LonamiWebs/Telethon)
- Inspired by OSINT frameworks and security research tools
- Thanks to the security research community

---

**Made with ❤️ for the security re

Now let me create a requirements.txt file:
```/
# TG-REAPER Dependencies
# Telegram Intelligence Framework Requirements

# Core Telegram API
telethon>=1.24.0

# Progress indicators
tqdm>=4.65.0

# Colored terminal output
colorama>=0.4.6

# Additional useful packages (optional but recommended)
# Uncomment if needed:

# cryptography>=41.0.0        # For enhanced security
# aiofiles>=23.0.0            # Async file operations
# python-dotenv>=1.0.0        # Environment variable management
# pandas>=2.0.0               # Advanced data analysis
# openpyxl>=3.1.0             # Excel export functionality
