<div align="center">

# 🚀 Quick Start Guide
*Get the Job Prospect Automation system running in 5 minutes*

📋 **5-minute setup** • 🤖 **AI-powered automation** • 📊 **Results in Notion**

**Created by [Minhal Abdul Sami](https://www.linkedin.com/in/minhal-abdul-sami/)**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Setup Time](https://img.shields.io/badge/setup-5%20minutes-green.svg)]()
[![First Campaign](https://img.shields.io/badge/first%20campaign-3--5%20minutes-brightgreen.svg)]()

</div>

---

## 📋 Prerequisites Checklist

<div align="center">

| Requirement | ✓ Status | Action Required |
|:---|:---:|:---|
| **Python 3.13+** | ☐ | [Download & Install](https://www.python.org/downloads/) |
| **Internet Connection** | ☐ | For API access |
| **API Keys** | ☐ | [Get API keys](docs/API_KEYS_GUIDE.md) |

</div>

> 💡 **First time?** Check out our [🚀 Getting Started Guide](GETTING_STARTED.md) for the one-command setup!

## ⚡ 5-Minute Setup Guide

<div align="center">

**🎯 Follow these steps in order for guaranteed success**

</div>

### Step 1: 💫 Install Dependencies

```bash
pip install -r requirements.txt
```

<div align="center">

**✅ Expected Output:**
```
Successfully installed click-8.1.3 rich-13.5.2 ...
```

</div>

<details>
<summary>🔧 <strong>Troubleshooting Installation Issues</strong></summary>

**🚫 Common Issues & Solutions:**

| Problem | Solution |
|:---|:---|
| `pip: command not found` | Install Python first: [python.org](https://www.python.org/downloads/) |
| Permission denied | Use `pip install --user -r requirements.txt` |
| Version conflicts | Create virtual environment: `python -m venv venv` |
| Windows PATH issues | Add Python to PATH during installation |

**💡 Virtual Environment (Recommended):**
```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

</details>

### Step 2: 🔑 Configure API Keys

<div align="center">

**🎯 Create your `.env` file with these essential API keys**

</div>

```env
# 📊 CORE API CONFIGURATION (Required)
NOTION_TOKEN=your_notion_integration_token_here
HUNTER_API_KEY=your_hunter_io_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# 📧 EMAIL SENDING (Optional but recommended)
RESEND_API_KEY=your_resend_api_key_here
SENDER_EMAIL=your-name@yourdomain.com
SENDER_NAME=Your Full Name

# 📱 NOTIFICATIONS (Optional)
ENABLE_NOTIFICATIONS=true
NOTIFICATION_METHODS=['notion']

# 👤 USER MENTIONS (Future feature)
NOTION_USER_ID=your-notion-user-id  # For @mentions
USER_EMAIL=your-email@domain.com    # For @remind notifications

# 🤖 AI PROVIDER CONFIGURATION
AI_PROVIDER=openai  # Options: openai, azure-openai, anthropic, google, deepseek

# Choose your AI provider based on your needs:
# - openai: Most popular, proven performance, extensive features
# - azure-openai: Enterprise security, custom deployments, Microsoft integration
# - anthropic: Constitutional AI, safety-focused, long context (Claude models)
# - google: Multimodal capabilities, long context, Google ecosystem (Gemini)
# - deepseek: Cost-effective, specialized for coding and reasoning tasks

# 🎆 ENHANCED FEATURES (Recommended)
ENABLE_AI_PARSING=true
ENABLE_PRODUCT_ANALYSIS=true
ENHANCED_PERSONALIZATION=true
AI_PARSING_MODEL=gpt-4
EMAIL_GENERATION_MODEL=gpt-4

# ⚡ PROCESSING SETTINGS
SCRAPING_DELAY=0.3
HUNTER_REQUESTS_PER_MINUTE=10
MAX_PRODUCTS_PER_RUN=50
MAX_PROSPECTS_PER_COMPANY=3

# 💫 CACHING CONFIGURATION (Performance boost)
ENABLE_CACHING=true
CACHE_MEMORY_MAX_ENTRIES=1000
CACHE_MEMORY_MAX_MB=100
CACHE_PERSISTENT_DIR=.cache
CACHE_DEFAULT_TTL=3600
```

<details>
<summary>🔑 <strong>Where to get API keys (click to expand)</strong></summary>

### 🔑 **API Keys Guide**

| Service | Purpose | Free Tier | Link |
|:---|:---|:---:|:---|
| **Notion** | Data storage | ✓ Unlimited | [Get Token](https://developers.notion.com/) |
| **Hunter.io** | Email discovery | 25/month | [Get Key](https://hunter.io/api) |
| 🤖 **AI Provider** | AI processing | Choose provider | [Setup Guide](docs/API_KEYS_GUIDE.md) |
| **Resend** | Email sending | 3k/month | [Get Key](https://resend.com/api-keys) |

🔗 **Detailed setup guide**: [🔑 Complete API Keys Guide](docs/API_KEYS_GUIDE.md)

</details>

<details>
<summary>🔧 <strong>Configuration troubleshooting</strong></summary>

**🚫 Common Configuration Issues:**

| Problem | Solution |
|:---|:---|
| `Configuration validation failed` | Check API key formats |
| `Notion connection failed` | Verify integration token & permissions |
| `AI quota exceeded` | Check billing & usage limits |
| `Hunter.io rate limit` | Reduce `HUNTER_REQUESTS_PER_MINUTE` |

**📊 Validation patterns:**
- Notion: `secret_[a-zA-Z0-9]{43,70}` or `ntn_[a-zA-Z0-9]{40,60}`
- Hunter.io: Standard API key format
- AI Provider: Various formats (see [API Keys Guide](docs/API_KEYS_GUIDE.md))
- Resend: `re_[a-zA-Z0-9_]{25,35}`

</details>

### Step 3: 🖥️ GUI Application (Alternative to CLI)

For users who prefer a graphical interface, you can use the GUI application instead of the command line:

```bash
# Run the GUI application
python run_gui.py

# Or on Windows:
run_gui.bat

# Or on Linux/macOS:
./run_gui.sh
```

The GUI provides the same functionality as the CLI but with a user-friendly interface:
- 🎨 Simple point-and-click operation
- 📋 Access to all main commands (discover, run-campaign, etc.)
- ⚙️ Easy configuration management
- 📊 Real-time output display
- 🚫 Cancel operations when needed

For detailed information about the GUI, see [GUI Runner Documentation](docs/GUI_RUNNER.md).

### Step 4: ✅ Validate Configuration

```bash
python cli.py validate-config
```

<div align="center">

**✅ Expected Success Output:**

</div>

```
✅ Configuration validation passed
✅ API connection testing:
   - Notion: ✅ Connection successful
   - Hunter.io: ✅ Connection successful  
   - AI Provider: ✅ Connection successful
   - Resend: ✅ Connection successful
✅ Sender profile validation passed
Profile completeness: 85.0%
```

<details>
<summary>🚫 <strong>Configuration issues? Click for solutions</strong></summary>

**📊 Common validation errors:**

| Error Message | Solution |
|:---|:---|
| `Notion connection failed` | Check token format & permissions |
| `AI authentication failed` | Verify API key & billing status |
| `Hunter.io quota exceeded` | Check your Hunter.io dashboard |
| `Configuration file not found` | Create `.env` file in project root |

**🔧 Debug commands:**
```bash
# Test individual components
python cli.py test-notifications
python scripts/debug_notion_storage.py
```

</details>

---

### Step 4: 📊 Set Up Progress Dashboard

```bash
python scripts/setup_dashboard.py
```

<div align="center">

**✅ Expected Dashboard Setup Output:**

</div>

```
📊 Job Prospect Automation Dashboard Setup

✓ Created prospect database: [database-id]
✓ Campaign dashboard created successfully!

Dashboard Components:
📊 Main Dashboard: https://notion.so/[dashboard-id]
🎯 Campaign Runs: https://notion.so/[campaigns-db-id]
📋 Processing Log: https://notion.so/[logs-db-id]
⚙️ System Status: https://notion.so/[status-db-id]
```

<details>
<summary>🔧 <strong>Dashboard setup issues</strong></summary>

**🚫 Common dashboard issues:**

| Problem | Solution |
|:---|:---|
| Permission denied | Share Notion integration with pages |
| Database creation failed | Check Notion integration permissions |
| URLs not accessible | Verify sharing settings in Notion |

**📊 Manual dashboard creation:**
If automatic setup fails, you can create databases manually in Notion and update the IDs in your configuration.

</details>

### 5. Apply Performance Optimizations (Recommended)

```bash
python scripts/fix_all_performance_issues.py
```

Expected output:
```
🚀 COMPREHENSIVE PERFORMANCE OPTIMIZATION
==================================================

1️⃣ LINKEDIN FINDER OPTIMIZATION
✅ Reduced timeouts from 15s to 2-3s
✅ Single strategy instead of 4 strategies
✅ Direct URL pattern matching
✅ Quick HEAD requests for validation
✅ Failed search caching
✅ Rate limiting reduced from 2s to 0.5s

[... additional optimizations ...]

⚡ EXPECTED PERFORMANCE IMPROVEMENTS:
LinkedIn Finding: 6-7 minutes → 10-30 seconds (20x faster)
Overall Pipeline: 15-20 minutes → 3-5 minutes (4-6x faster)
WebDriver Operations: 2-3x faster page loads
HTTP Requests: 3-5x faster response times

🎉 ALL PERFORMANCE FIXES APPLIED!
```

### 6. Run Full Pipeline Test

```bash
python scripts/test_full_pipeline.py
```

Expected output:
```
🔧 SERVICE INITIALIZATION STATUS:
   ProductHunt Scraper: ✅
   Notion Manager: ✅
   Email Finder: ✅
   LinkedIn Finder (Optimized): ✅
   Email Generator: ✅
   Email Sender: ✅
   Product Analyzer: ✅
   AI Parser: ✅
   Sender Profile: ✅ Your Name

📊 PIPELINE RESULTS SUMMARY:
   Companies processed: 3
   Prospects found: 2
   Emails found: 1
   LinkedIn profiles: 1
   Success rate: 100.0%
   Duration: 45.2 seconds (much faster with optimizations!)

🚀 PARALLEL PROCESSING SUMMARY:
   Workers Used: 5
   Processing Rate: 4.0 companies/min
   Performance: 3-5x faster than sequential

✅ Full pipeline test completed successfully!
```

### 7. Run Complete Campaign Workflow

```bash
python cli.py run-campaign --limit 5 --generate-emails --campaign-name "First Test Campaign"
```

### 8. Test Email Generation

```bash
python scripts/test_email_pipeline.py
```

## 🎯 Next Steps

### Generate Emails for Prospects

```bash
# Generate emails for recent prospects (easiest)
python cli.py generate-emails-recent --limit 5

# Alternative: Get prospect IDs from Notion and generate emails
python cli.py generate-emails --prospect-ids "id1,id2,id3" --sender-profile profiles/my_profile.md
```

### Send Emails (Optional)

```bash
# Generate emails (sending is handled separately)
python cli.py generate-emails --prospect-ids "id1,id2" --sender-profile profiles/my_profile.md

# Alternative: Send recently generated emails separately
python cli.py send-emails-recent --limit 5
```

### Monitor System Status

```bash
python cli.py status
```

## 🔧 API Keys Setup

### Required APIs

1. **Notion** (Free)
   - Go to [developers.notion.com](https://developers.notion.com/)
   - Create integration with read/write permissions
   - Copy the token

2. **Hunter.io** (Free tier: 25 requests/month)
   - Sign up at [hunter.io](https://hunter.io/)
   - Get API key from dashboard

3. **AI Provider** (Choose one)
   - Create account at [platform.openai.com](https://platform.openai.com/)
   - Generate API key
   - Add payment method

4. **Resend** (Optional - for email sending)
   - Sign up at [resend.com](https://resend.com/)
   - Create API key
   - Verify domain for better deliverability

## 🧪 Testing Commands

```bash
# Apply performance optimizations (recommended first)
python scripts/fix_all_performance_issues.py

# Test configuration
python cli.py validate-config

# Test full pipeline
python scripts/test_full_pipeline.py

# Test email functionality
python scripts/test_email_pipeline.py

# Test interactive campaign controls
python scripts/test_interactive_controls.py

# Test AI personalization data quality
python scripts/test_personalization_fix.py

# Test company deduplication functionality
python scripts/test_company_deduplication.py

# Debug discovery issues (why no unprocessed companies found)
python scripts/debug_discovery.py

# Debug email generation issues
python scripts/debug_email_generation.py

# Test with dry-run (no API calls)
python cli.py --dry-run discover --limit 1

# Test specific company
python cli.py --dry-run process-company "OpenAI" --domain openai.com

# Debug specific issues
python scripts/debug_discovery.py          # Debug company discovery filtering
python scripts/debug_team_extraction.py    # Debug team extraction and LinkedIn URLs
python scripts/debug_email_generation.py   # Debug email generation process
python scripts/verify_notion_schema.py     # Verify Notion database schema and field mappings

# Code quality and import analysis
python utils/import_analyzer.py
python utils/validate_imports.py
```

## 🚨 Common Issues

### "Configuration validation failed"
```bash
# Check your .env file
python cli.py validate-config
```

### "No prospects found"
```bash
# Test with a known company
python cli.py process-company "OpenAI" --domain openai.com
```

### "Email generation failed"
```bash
# Debug email generation step-by-step
python scripts/debug_email_generation.py

# Verify Notion database schema for email fields
python scripts/verify_notion_schema.py

# Test email pipeline specifically
python scripts/test_email_pipeline.py
```

### "Rate limit exceeded"
```bash
# Increase delays in .env file
SCRAPING_DELAY=1.0
HUNTER_REQUESTS_PER_MINUTE=5
```

## 📖 Full Documentation

For detailed information, see:
- [README.md](README.md) - Complete overview
- [docs/API_KEYS_GUIDE.md](docs/API_KEYS_GUIDE.md) - Detailed API setup
- [docs/CLI_USAGE.md](docs/CLI_USAGE.md) - All CLI commands
- [docs/DASHBOARD_MONITORING_GUIDE.md](docs/DASHBOARD_MONITORING_GUIDE.md) - Progress tracking and monitoring
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Comprehensive testing
- [docs/TROUBLESHOOTING_GUIDE.md](docs/TROUBLESHOOTING_GUIDE.md) - Problem solving

## 🎉 Success!

If all tests pass, you're ready to start automating your job prospecting workflow!

**Next recommended actions:**
1. Apply performance optimizations: `python scripts/fix_all_performance_issues.py`
2. Set up your sender profile: `python cli.py profile-setup --interactive`
3. Run complete campaign: `python cli.py run-campaign --limit 10 --generate-emails --campaign-name "My First Campaign"`
4. Generate emails for found prospects
5. Review and send emails
6. Test notifications: `python cli.py send-notification --type test`

**Need help?** Check the troubleshooting guide or run tests with `--verbose` flag for detailed logging.