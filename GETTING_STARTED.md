# 🚀 Getting Started - One Command Setup

## For Complete Beginners

**Just run ONE command to get everything working:**

```bash
python cli.py quick-start
```

This single command will:
- ✅ Validate your configuration
- ✅ Set up your Notion dashboard automatically
- ✅ Find and process 5 companies
- ✅ Extract prospects and contact information
- ✅ Generate personalized emails
- ✅ Update analytics and send notifications

**That's it!** Everything is automated.

## For Regular Use

**Run complete campaigns with one command:**

```bash
python cli.py run-campaign --limit 10 --generate-emails --send-emails
```

**Options:**
- `--limit 10` - Process 10 companies
- `--generate-emails` - Generate personalized emails
- `--send-emails` - Send emails immediately (optional)
- `--campaign-name "My Campaign"` - Custom campaign name

## Prerequisites

1. **Install Python 3.13+**
2. **Install dependencies:** `pip install -r requirements.txt`
3. **Set up API keys in .env file:**

```env
NOTION_TOKEN=your_notion_token
HUNTER_API_KEY=your_hunter_api_key
OPENAI_API_KEY=your_openai_api_key
```

## That's It!

The system handles everything else automatically:
- Creates Notion databases
- Tracks progress in real-time
- Processes companies in parallel (3-5x faster)
- Sends notifications when complete
- Updates daily analytics
- Generates comprehensive reports

## Advanced Usage

If you want more control, you can run individual steps:

```bash
# Setup only
python setup_dashboard.py

# Discovery only
python cli.py discover --limit 10

# Email generation for specific prospects
python cli.py generate-emails --prospect-ids "id1,id2,id3"

# Email generation for recent prospects (easier)
python cli.py generate-emails-recent --limit 5

# Analytics update
python cli.py daily-summary
```

But for most users, `quick-start` and `run-campaign` are all you need!

## Need Help?

- **Check configuration:** `python cli.py validate-config`
- **Test notifications:** `python cli.py test-notifications`
- **View campaign status:** `python cli.py campaign-status`
- **Generate reports:** `python cli.py analytics-report`

## Success!

After running `quick-start`, check your Notion workspace for:
- 📊 **Main Dashboard** - Overview and navigation
- 🎯 **Campaign Runs** - Real-time campaign tracking
- 📋 **Processing Log** - Detailed step logs
- 📈 **Daily Analytics** - Performance metrics
- 📧 **Email Queue** - Generated emails for review
- ⚙️ **System Status** - Component health

The system is designed to be **completely automated** while giving you full visibility and control through Notion!