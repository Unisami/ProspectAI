# Setup and Installation Guide

This comprehensive guide will walk you through setting up the Job Prospect Automation system from scratch.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Python 3.8 or higher** installed on your system
- **pip** package manager (usually comes with Python)
- **Git** for cloning the repository
- **Internet connection** for API access
- **API accounts** for required services (details below)

### System Requirements

- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 4GB (8GB recommended for large operations)
- **Storage**: At least 1GB free space
- **Network**: Stable internet connection for API calls

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd job-prospect-automation

# Verify the structure
ls -la
```

Expected directory structure:
```
job-prospect-automation/
├── controllers/
├── services/
├── models/
├── utils/
├── tests/
├── examples/
├── docs/
├── requirements.txt
├── cli.py
├── main.py
└── README.md
```

### Step 2: Set Up Python Environment

#### Option A: Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Verify activation (should show venv path)
which python
```

#### Option B: Using Conda

```bash
# Create conda environment
conda create -n job-prospect-automation python=3.9

# Activate environment
conda activate job-prospect-automation
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(notion|hunter|openai|scrapy|crawl4ai)"
```

If you encounter issues, try:
```bash
# Upgrade pip first
pip install --upgrade pip

# Install with verbose output
pip install -r requirements.txt -v
```

### Step 4: Verify Installation

```bash
# Test CLI access
python cli.py --help

# Test dry-run mode
python cli.py --dry-run status
```

Expected output should show CLI help and dry-run confirmation.

## 🔑 API Keys Setup

### Required API Keys

You need to obtain API keys from several services for full functionality:

#### Required Services:
- **Notion Integration Token** - For data storage and organization
- **Hunter.io API Key** - For email discovery and verification

#### Enhanced Features (Recommended):
- **Azure OpenAI API Key** - For AI-powered email generation and data parsing (recommended)
- **OpenAI API Key** - Alternative to Azure OpenAI for AI features
- **Resend API Key** - For automated email sending and delivery tracking

#### 1. Notion Integration Token

**Steps:**
1. Go to [Notion Developers](https://developers.notion.com/)
2. Click "Create new integration"
3. Fill in integration details:
   - Name: "Job Prospect Automation"
   - Associated workspace: Select your workspace
   - Capabilities: Read, Insert, Update content
4. Click "Submit"
5. Copy the "Internal Integration Token"

**Important**: After creating the integration, you must:
- Share your Notion workspace with the integration
- Or let the system create a new database (recommended for first-time users)

#### 2. Hunter.io API Key

**Steps:**
1. Sign up at [Hunter.io](https://hunter.io/)
2. Verify your email address
3. Go to your dashboard
4. Navigate to "API" section
5. Copy your API key

**Free Tier Limits:**
- 25 requests per month
- 10 requests per minute
- Email finder and verifier access

**Paid Plans**: Higher limits and additional features

#### 3. Azure OpenAI API Key (Recommended)

**Why Azure OpenAI?**
- Enterprise-grade reliability and security
- Better rate limits and availability
- Predictable pricing with reserved capacity
- Regional deployment options

**Steps:**
1. Create Azure account at [Azure Portal](https://portal.azure.com/)
2. Apply for Azure OpenAI access at [aka.ms/oai/access](https://aka.ms/oai/access)
3. Create Azure OpenAI resource in your subscription
4. Deploy GPT-4 models for email generation and AI parsing
5. Get API key and endpoint from Azure Portal

**Configuration:**
```env
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
```

#### 4. Regular OpenAI API Key (Alternative)

**Steps:**
1. Create account at [OpenAI Platform](https://platform.openai.com/)
2. Add payment method (required for API access)
3. Go to "API Keys" section
4. Click "Create new secret key"
5. Copy the key immediately (won't be shown again)

**Configuration:**
```env
USE_AZURE_OPENAI=false
OPENAI_API_KEY=sk-your_openai_key_here
```

**Usage Costs:**
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- GPT-4: ~$0.03 per 1K tokens
- Typical email generation: $0.01-0.05 per email
- AI parsing: ~$0.02-0.10 per operation

#### 5. Resend API Key (For Email Sending)

**Why Resend?**
- High email deliverability rates
- Real-time tracking and analytics
- Webhook support for delivery status
- Developer-friendly API

**Steps:**
1. Sign up at [Resend](https://resend.com/)
2. Verify your email address
3. Add and verify your domain (recommended)
4. Create API key with sending permissions
5. Configure DNS records for better deliverability

**Configuration:**
```env
RESEND_API_KEY=re_your_resend_api_key
SENDER_EMAIL=your-name@yourdomain.com
SENDER_NAME=Your Full Name
```

### Configuration Methods

#### Method 1: Environment Variables (Recommended)

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file:**
   ```bash
   # On Windows
   notepad .env
   
   # On macOS/Linux
   nano .env
   ```

3. **Add your API keys:**
   ```env
   # Required API Keys
   NOTION_TOKEN=secret_your_actual_notion_token_here
   HUNTER_API_KEY=your_actual_hunter_api_key_here
   
   # Azure OpenAI Configuration (Recommended)
   USE_AZURE_OPENAI=true
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   
   # Alternative: Regular OpenAI (if not using Azure)
   # USE_AZURE_OPENAI=false
   # OPENAI_API_KEY=sk-your_actual_openai_key_here
   
   # Email Sending Configuration (Optional but Recommended)
   RESEND_API_KEY=re_your_resend_api_key_here
   SENDER_EMAIL=your-name@yourdomain.com
   SENDER_NAME=Your Full Name
   REPLY_TO_EMAIL=your-name@yourdomain.com
   
   # Enhanced AI Features
   ENABLE_AI_PARSING=true
   ENABLE_PRODUCT_ANALYSIS=true
   ENHANCED_PERSONALIZATION=true
   
   # Processing Configuration
   SCRAPING_DELAY=2.0
   HUNTER_REQUESTS_PER_MINUTE=10
   RESEND_REQUESTS_PER_MINUTE=100
   MAX_PRODUCTS_PER_RUN=50
   MAX_PROSPECTS_PER_COMPANY=10
   
   # Email Configuration
   EMAIL_TEMPLATE_TYPE=professional
   PERSONALIZATION_LEVEL=high
   MAX_EMAIL_LENGTH=500
   
   # Workflow Configuration
   ENABLE_ENHANCED_WORKFLOW=true
   AUTO_SEND_EMAILS=false
   EMAIL_REVIEW_REQUIRED=true
   ```

4. **Secure the file:**
   ```bash
   # On Unix systems
   chmod 600 .env
   ```

#### Method 2: Configuration File

1. **Generate template:**
   ```bash
   python cli.py init-config config.yaml
   ```

2. **Edit the configuration:**
   ```yaml
   # API Keys (Required)
   NOTION_TOKEN: "secret_your_actual_notion_token_here"
   HUNTER_API_KEY: "your_actual_hunter_api_key_here"
   OPENAI_API_KEY: "sk-your_actual_openai_key_here"
   
   # Optional: Pre-existing Notion database ID
   NOTION_DATABASE_ID: ""
   
   # Rate Limiting Settings
   SCRAPING_DELAY: 2.0
   HUNTER_REQUESTS_PER_MINUTE: 10
   
   # Processing Limits
   MAX_PRODUCTS_PER_RUN: 50
   MAX_PROSPECTS_PER_COMPANY: 10
   
   # Email Generation Settings
   EMAIL_TEMPLATE_TYPE: "professional"
   PERSONALIZATION_LEVEL: "medium"
   
   # Logging Configuration
   LOG_LEVEL: "INFO"
   ```

3. **Use with CLI:**
   ```bash
   python cli.py --config config.yaml discover
   ```

## ✅ Configuration Validation

### Test Your Setup

1. **Basic Configuration Test:**
   ```bash
   python cli.py --dry-run status
   ```
   
   Expected output:
   ```
   Running in DRY-RUN mode - no actual API calls will be made
   DRY-RUN: Would show workflow status
   ```

2. **Set Up Progress Dashboard:**
   ```bash
   python scripts/setup_dashboard.py
   ```
   
   This creates Notion databases for campaign tracking, processing logs, and system status monitoring.

3. **API Keys Validation:**
   ```bash
   python cli.py --dry-run discover --limit 1
   ```
   
   This should show what would be discovered without making actual API calls.

4. **Full System Test:**
   ```bash
   python cli.py --verbose --dry-run discover --limit 5
   ```
   
   This provides detailed logging of what would happen.

5. **Test OpenAI Client Manager:**
   ```bash
   python -c "
   from services.openai_client_manager import get_client_manager, configure_default_client
   from utils.config import Config
   
   config = Config.from_env()
   configure_default_client(config)
   manager = get_client_manager()
   
   print('OpenAI Client Manager Status:')
   client_info = manager.get_client_info()
   print(f'  Client Type: {client_info[\"client_type\"]}')
   print(f'  Model: {client_info[\"model_name\"]}')
   print(f'  Configured: {client_info[\"configured\"]}')
   print('✅ OpenAI Client Manager working correctly')
   "
   ```

### Common Configuration Issues

#### Issue: "NOTION_TOKEN environment variable is required"

**Solutions:**
- Check `.env` file exists in project root
- Verify no typos in variable names
- Ensure no extra spaces around the `=` sign
- Check file permissions (should be readable)

#### Issue: "Invalid Notion token"

**Solutions:**
- Verify token starts with `secret_`
- Check token hasn't expired
- Ensure integration has proper permissions
- Try creating a new integration token

#### Issue: "Hunter.io API key invalid"

**Solutions:**
- Verify account is activated (check email)
- Ensure API key is copied correctly
- Check if you've exceeded free tier limits
- Try generating a new API key

#### Issue: "OpenAI API authentication failed"

**Solutions:**
- Verify API key starts with `sk-`
- Check if billing is set up (required for API access)
- Ensure you have available credits
- Try creating a new API key

## 🔧 Advanced Configuration

### Custom Notion Database

If you want to use an existing Notion database:

1. **Create a database in Notion** with these properties:
   - Name (Title)
   - Role (Text)
   - Company (Text)
   - LinkedIn (URL)
   - Email (Email)
   - Contacted (Checkbox)
   - Status (Select: Not Contacted, Contacted, Responded, Rejected)
   - Notes (Rich Text)
   - Source (Text)
   - Added Date (Date)

2. **Share the database** with your integration

3. **Get the database ID** from the URL:
   ```
   https://notion.so/your-workspace/DATABASE_ID?v=...
   ```

4. **Add to configuration:**
   ```env
   NOTION_DATABASE_ID=your_database_id_here
   ```

### Rate Limiting Configuration

Adjust these settings based on your API limits and needs:

```env
# Scraping delays (seconds between requests)
SCRAPING_DELAY=2.0              # ProductHunt/LinkedIn scraping
linkedin_scraping_delay=3.0     # LinkedIn-specific delay

# Hunter.io limits
HUNTER_REQUESTS_PER_MINUTE=10   # Free tier: 10/min
HUNTER_MONTHLY_LIMIT=25         # Free tier: 25/month

# Processing limits
MAX_PRODUCTS_PER_RUN=50         # Products per discovery run
MAX_PROSPECTS_PER_COMPANY=10    # Max prospects per company
```

### Email Generation Settings

Customize email generation:

```env
# Template types: professional, casual, formal
EMAIL_TEMPLATE_TYPE=professional

# Personalization levels: low, medium, high
PERSONALIZATION_LEVEL=medium

# OpenAI model settings
OPENAI_MODEL=gpt-3.5-turbo      # or gpt-4 for better quality
OPENAI_MAX_TOKENS=500           # Max tokens per email
OPENAI_TEMPERATURE=0.7          # Creativity level (0-1)
```

### Logging Configuration

Configure logging levels and output:

```env
# Log levels: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# Log file settings
LOG_FILE_MAX_SIZE=10MB          # Max size before rotation
LOG_FILE_BACKUP_COUNT=5         # Number of backup files
LOG_TO_CONSOLE=true             # Also log to console
```

## 🐳 Docker Setup (Optional)

For containerized deployment:

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.9-slim
   
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY . .
   
   CMD ["python", "cli.py", "discover"]
   ```

2. **Build image:**
   ```bash
   docker build -t job-prospect-automation .
   ```

3. **Run with environment file:**
   ```bash
   docker run --env-file .env job-prospect-automation discover --limit 10
   ```

## 🧪 Testing Your Installation

### Quick Test Suite

Run these commands to verify everything works:

```bash
# 1. Test CLI help
python cli.py --help

# 2. Test configuration
python cli.py --dry-run status

# 3. Test discovery (dry-run)
python cli.py --dry-run discover --limit 3

# 4. Test company processing (dry-run)
python cli.py --dry-run process-company "Test Company"

# 5. Test email generation (dry-run)
python cli.py --dry-run generate-emails --prospect-ids "1,2,3"

# 6. Run example scripts
python examples/cli_usage_examples.py
```

### Integration Test

For a complete test with actual API calls (uses your quotas):

```bash
# Small-scale real test
python cli.py discover --limit 1 --batch-size 1

# Check results
python cli.py status
```

## 📁 Directory Structure

After setup, your directory should look like:

```
job-prospect-automation/
├── .env                        # Your API keys (keep private!)
├── config.yaml                 # Optional config file
├── logs/                       # Generated log files
│   ├── prospect_automation_YYYYMMDD.log
│   ├── error_monitoring.json
│   └── error_notifications.json
├── controllers/                # Main logic controllers
├── services/                   # API service integrations
├── models/                     # Data models
├── utils/                      # Utility functions
├── tests/                      # Test files
├── examples/                   # Usage examples
├── docs/                       # Documentation
├── requirements.txt            # Python dependencies
├── cli.py                      # Command-line interface
├── main.py                     # Main entry point
└── README.md                   # Main documentation
```

## 🚨 Security Considerations

### API Key Security

1. **Never commit API keys** to version control
2. **Use environment variables** or secure config files
3. **Set proper file permissions:**
   ```bash
   chmod 600 .env config.yaml
   ```
4. **Rotate keys regularly** (especially if compromised)

### Notion Security

1. **Limit integration permissions** to only what's needed
2. **Use dedicated workspace** for automation
3. **Regularly review** integration access
4. **Monitor database access** logs

### Network Security

1. **Use HTTPS** for all API calls (default in the system)
2. **Monitor API usage** for unusual patterns
3. **Set up rate limiting** to avoid being blocked
4. **Use VPN** if required by your organization

## 🎯 Next Steps

After successful installation:

1. **Read the [CLI Usage Guide](CLI_USAGE.md)** for detailed command information
2. **Review [examples/](../examples/)** for usage patterns
3. **Start with small tests** using `--dry-run` mode
4. **Monitor your API usage** to stay within limits
5. **Set up monitoring** for production use

## 🆘 Getting Help

If you encounter issues during setup:

1. **Check the [Troubleshooting](../README.md#troubleshooting)** section
2. **Review error logs** in the `logs/` directory
3. **Use verbose mode** for detailed error information:
   ```bash
   python cli.py --verbose --dry-run [command]
   ```
4. **Test individual components** to isolate issues
5. **Open an issue** on GitHub with detailed error information

---

**Congratulations!** 🎉 You've successfully set up the Job Prospect Automation system. You're now ready to start automating your job prospecting workflow!