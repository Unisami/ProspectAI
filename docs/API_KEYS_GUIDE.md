# API Keys Configuration Guide

This guide provides detailed instructions for obtaining and configuring all required API keys for the Job Prospect Automation system.

## 📋 Overview

The system requires several API keys for enhanced functionality:
- **Notion Integration Token** - For data storage and organization
- **Hunter.io API Key** - For email discovery and verification
- **Azure OpenAI API Key** - For AI-powered email generation and data parsing (recommended)
- **OpenAI API Key** - Alternative to Azure OpenAI for AI features
- **Resend API Key** - For automated email sending and delivery tracking

## 🔑 Notion Integration Setup

### Step 1: Create Notion Integration

1. **Go to Notion Developers**
   - Visit [https://developers.notion.com/](https://developers.notion.com/)
   - Click "View my integrations" or "Create new integration"

2. **Create New Integration**
   - Click "Create new integration"
   - Fill in the details:
     - **Name**: `Job Prospect Automation`
     - **Associated workspace**: Select your workspace
     - **Logo**: Optional (you can upload a custom logo)

3. **Set Capabilities**
   - ✅ **Read content**
   - ✅ **Insert content** 
   - ✅ **Update content**
   - ❌ **Read user information** (not needed)
   - ❌ **Read user information without email** (not needed)

4. **Submit and Get Token**
   - Click "Submit"
   - Copy the "Internal Integration Token" (starts with `secret_`)
   - **Important**: Save this token securely - it won't be shown again

### Step 2: Configure Workspace Access

#### Option A: Let System Create Database (Recommended for beginners)
- No additional setup needed
- System will create a new database automatically
- Integration will have full access to the created database

#### Option B: Use Existing Database
1. **Create or select a database** in your Notion workspace
2. **Share the database** with your integration:
   - Open the database in Notion
   - Click "Share" in the top-right corner
   - Click "Invite" and search for your integration name
   - Select your integration and click "Invite"

3. **Get Database ID** (if using existing database):
   - Open the database in Notion
   - Copy the URL: `https://notion.so/workspace/DATABASE_ID?v=...`
   - Extract the DATABASE_ID part
   - Add to your configuration: `NOTION_DATABASE_ID=your_database_id`

### Step 3: Verify Notion Setup

Test your Notion integration:

```bash
# Test with dry-run
python cli.py --dry-run status

# Check if token is valid (will show in logs)
python cli.py --verbose --dry-run discover --limit 1
```

### Notion Troubleshooting

**Issue**: "Unauthorized" or "Invalid token"
- Verify token starts with `secret_`
- Check if integration exists and is active
- Ensure workspace access is granted

**Issue**: "Cannot access database"
- Verify database is shared with integration
- Check database ID is correct
- Try letting system create new database

**Issue**: "Insufficient permissions"
- Verify integration has Read, Insert, Update capabilities
- Check workspace permissions

## 🎯 Hunter.io API Setup

### Step 1: Create Hunter.io Account

1. **Sign Up**
   - Go to [https://hunter.io/](https://hunter.io/)
   - Click "Sign up for free"
   - Enter your email and create password
   - Verify your email address

2. **Complete Profile**
   - Add your name and company information
   - This helps with API approval and limits

### Step 2: Get API Key

1. **Access Dashboard**
   - Log in to your Hunter.io account
   - Go to your dashboard

2. **Navigate to API Section**
   - Click on "API" in the left sidebar
   - Or go directly to [https://hunter.io/api_keys](https://hunter.io/api_keys)

3. **Copy API Key**
   - Your API key will be displayed
   - Copy the entire key (usually starts with letters/numbers)

### Step 3: Understand Limits

#### Free Plan Limits:
- **25 requests per month**
- **10 requests per minute**
- Email finder and verifier access
- Domain search functionality

#### Paid Plan Benefits:
- Higher monthly limits (100-10,000+ requests)
- Higher rate limits
- Additional features (bulk processing, etc.)
- Priority support

### Step 4: Configure Rate Limits

Adjust your configuration based on your plan:

```env
# Free plan settings
HUNTER_REQUESTS_PER_MINUTE=10
HUNTER_MONTHLY_LIMIT=25

# Paid plan example (adjust based on your plan)
HUNTER_REQUESTS_PER_MINUTE=50
HUNTER_MONTHLY_LIMIT=1000
```

### Hunter.io Troubleshooting

**Issue**: "Invalid API key"
- Verify key is copied correctly (no extra spaces)
- Check if account is activated
- Try generating a new API key

**Issue**: "Rate limit exceeded"
- Reduce `HUNTER_REQUESTS_PER_MINUTE` setting
- Wait for rate limit reset (1 minute)
- Consider upgrading plan

**Issue**: "Monthly quota exceeded"
- Check usage in Hunter.io dashboard
- Wait for monthly reset
- Consider upgrading plan

## 🤖 Azure OpenAI API Setup (Recommended)

### Why Azure OpenAI?

Azure OpenAI provides enterprise-grade AI services with:
- **Better reliability** and uptime guarantees
- **Enhanced security** and compliance features
- **Predictable pricing** with reserved capacity options
- **Regional deployment** for data residency requirements
- **Integration** with Azure ecosystem

### Step 1: Create Azure Account

1. **Sign Up for Azure**
   - Go to [https://azure.microsoft.com/](https://azure.microsoft.com/)
   - Click "Start free" or "Sign in"
   - Complete account setup with payment method

2. **Apply for Azure OpenAI Access**
   - Visit [https://aka.ms/oai/access](https://aka.ms/oai/access)
   - Fill out the application form
   - Wait for approval (usually 1-3 business days)

### Step 2: Create Azure OpenAI Resource

1. **Navigate to Azure Portal**
   - Go to [https://portal.azure.com/](https://portal.azure.com/)
   - Sign in with your Azure account

2. **Create OpenAI Resource**
   - Click "Create a resource"
   - Search for "OpenAI"
   - Select "Azure OpenAI"
   - Click "Create"

3. **Configure Resource**
   - **Subscription**: Select your subscription
   - **Resource Group**: Create new or use existing
   - **Region**: Choose region (e.g., East US, West Europe)
   - **Name**: Give it a descriptive name (e.g., "job-prospect-ai")
   - **Pricing Tier**: Select appropriate tier

### Step 3: Deploy AI Models

1. **Access Azure OpenAI Studio**
   - Go to your OpenAI resource in Azure Portal
   - Click "Go to Azure OpenAI Studio"

2. **Create Model Deployments**
   - Navigate to "Deployments" section
   - Click "Create new deployment"
   - **For Email Generation**: Deploy GPT-4 or GPT-3.5-turbo
   - **For AI Parsing**: Deploy GPT-4 (recommended for better accuracy)
   - **Deployment Name**: Use descriptive names (e.g., "gpt-4-email-gen")

### Step 4: Get API Keys and Endpoint

1. **Get API Key**
   - In Azure Portal, go to your OpenAI resource
   - Navigate to "Keys and Endpoint"
   - Copy "KEY 1" or "KEY 2"

2. **Get Endpoint URL**
   - Copy the "Endpoint" URL (e.g., `https://your-resource.openai.azure.com/`)

3. **Note Deployment Names**
   - Remember the deployment names you created
   - You'll need these for configuration

### Step 5: Configure Environment Variables

```env
# Azure OpenAI Configuration
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-email-gen
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# AI Parsing Configuration
AI_PARSING_MODEL=gpt-4
PRODUCT_ANALYSIS_MODEL=gpt-4
EMAIL_GENERATION_MODEL=gpt-4
```

### Step 6: OpenAI Client Manager

The system now uses a centralized **OpenAI Client Manager** that provides enhanced functionality:

#### Key Features:
- **Singleton Pattern**: Single instance manages all OpenAI operations
- **Connection Pooling**: Efficient HTTP connection reuse with configurable limits
- **Multi-Client Support**: Support for multiple client configurations
- **Standardized Error Handling**: Consistent error responses with detailed categorization
- **Automatic Retry Logic**: Built-in retry mechanisms for failed requests
- **Thread Safety**: Safe for concurrent operations

#### Testing Your Configuration:

```python
from services.openai_client_manager import get_client_manager, configure_default_client
from utils.config import Config

# Configure the default client
config = Config.from_env()
configure_default_client(config)

# Get client manager instance
manager = get_client_manager()

# Test client configuration
client_info = manager.get_client_info()
print(f"Client Type: {client_info['client_type']}")
print(f"Model: {client_info['model_name']}")
print(f"Endpoint: {client_info['endpoint']}")

# Test a simple completion
try:
    response = manager.make_simple_completion([
        {"role": "user", "content": "Hello, this is a test message."}
    ])
    print(f"✅ OpenAI Client Manager working: {response[:50]}...")
except Exception as e:
    print(f"❌ OpenAI Client Manager failed: {e}")
```

#### Advanced Configuration:

```env
# Multiple client configurations (optional)
# You can configure different clients for different purposes

# Default client (used by most operations)
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-email-gen

# Connection pooling settings (optional)
OPENAI_MAX_CONNECTIONS=10
OPENAI_MAX_KEEPALIVE_CONNECTIONS=5
OPENAI_TIMEOUT=30
```

### Azure OpenAI Troubleshooting

**Issue**: "Access denied" or "Subscription not approved"
- Ensure you've applied for and received Azure OpenAI access
- Check that your subscription is approved
- Try a different Azure region

**Issue**: "Deployment not found"
- Verify deployment name matches exactly
- Check that model is deployed and running
- Ensure deployment is in the same region as your resource

**Issue**: "Quota exceeded"
- Check your Azure OpenAI quota limits
- Request quota increase if needed
- Monitor usage in Azure Portal

## 🤖 Regular OpenAI API Setup (Alternative)

If you prefer to use regular OpenAI instead of Azure OpenAI:

### Step 1: Create OpenAI Account

1. **Sign Up**
   - Go to [https://platform.openai.com/](https://platform.openai.com/)
   - Click "Sign up"
   - Use email or Google/Microsoft account

2. **Verify Account**
   - Verify your email address
   - Complete phone verification if required

### Step 2: Set Up Billing

**Important**: OpenAI requires a payment method for API access.

1. **Add Payment Method**
   - Go to "Billing" in your dashboard
   - Click "Add payment method"
   - Add credit card or other payment method

2. **Set Usage Limits** (Recommended)
   - Set monthly spending limit (e.g., $10-50)
   - Set up usage alerts
   - This prevents unexpected charges

### Step 3: Create API Key

1. **Navigate to API Keys**
   - Go to "API Keys" section
   - Or visit [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

2. **Create New Key**
   - Click "Create new secret key"
   - Give it a descriptive name: "Job Prospect Automation"
   - Copy the key immediately (starts with `sk-`)
   - **Important**: Save it securely - it won't be shown again

### Step 4: Configure for Regular OpenAI

```env
# Regular OpenAI Configuration
USE_AZURE_OPENAI=false
OPENAI_API_KEY=sk-your_openai_key_here

# Model Configuration
AI_PARSING_MODEL=gpt-3.5-turbo
PRODUCT_ANALYSIS_MODEL=gpt-4
EMAIL_GENERATION_MODEL=gpt-3.5-turbo
```

### Step 5: Understand Costs

#### Typical Usage Costs:
- **GPT-3.5-turbo**: ~$0.002 per 1K tokens
- **GPT-4**: ~$0.03 per 1K tokens
- **Email generation**: ~$0.01-0.05 per email
- **AI parsing**: ~$0.02-0.10 per parsing operation
- **Monthly estimate**: $10-50 for moderate usage

### OpenAI Troubleshooting

**Issue**: "Invalid API key"
- Verify key starts with `sk-`
- Check if key was copied completely
- Try creating a new API key

**Issue**: "Insufficient quota"
- Check billing setup
- Add payment method
- Increase usage limits

**Issue**: "Rate limit exceeded"
- Wait for rate limit reset
- Consider upgrading to higher tier
- Reduce concurrent requests

## 📧 Resend API Setup

### Why Resend?

Resend provides reliable email delivery with:
- **High deliverability** rates
- **Real-time tracking** and analytics
- **Webhook support** for delivery status
- **Developer-friendly** API and documentation
- **Reasonable pricing** for transactional emails

### Step 1: Create Resend Account

1. **Sign Up**
   - Go to [https://resend.com/](https://resend.com/)
   - Click "Get Started"
   - Sign up with email or GitHub

2. **Verify Email**
   - Check your email for verification link
   - Complete email verification

### Step 2: Set Up Domain (Recommended)

1. **Add Your Domain**
   - In Resend dashboard, go to "Domains"
   - Click "Add Domain"
   - Enter your domain (e.g., `yourdomain.com`)

2. **Configure DNS Records**
   - Add the provided DNS records to your domain
   - **SPF Record**: Helps with deliverability
   - **DKIM Record**: Authenticates your emails
   - **DMARC Record**: Prevents spoofing

3. **Verify Domain**
   - Click "Verify" in Resend dashboard
   - Wait for DNS propagation (can take up to 24 hours)

### Step 3: Get API Key

1. **Navigate to API Keys**
   - In Resend dashboard, go to "API Keys"
   - Click "Create API Key"

2. **Configure API Key**
   - **Name**: "Job Prospect Automation"
   - **Permission**: "Sending access"
   - **Domain**: Select your verified domain (or use resend.dev for testing)

3. **Copy API Key**
   - Copy the generated API key (starts with `re_`)
   - **Important**: Save it securely - it won't be shown again

### Step 4: Configure Email Settings

```env
# Resend Configuration
RESEND_API_KEY=re_your_resend_api_key_here
SENDER_EMAIL=your-name@yourdomain.com
SENDER_NAME=Your Name
REPLY_TO_EMAIL=your-name@yourdomain.com

# Email Sending Configuration
RESEND_REQUESTS_PER_MINUTE=100
AUTO_SEND_EMAILS=false
EMAIL_REVIEW_REQUIRED=true
```

### Step 5: Test Email Sending

```bash
# Test email configuration
python cli.py --dry-run test-email your-email@example.com

# Send a real test email
python cli.py test-email your-email@example.com
```

### Resend Troubleshooting

**Issue**: "Invalid API key"
- Verify key starts with `re_`
- Check if key was copied correctly
- Ensure API key has sending permissions

**Issue**: "Domain not verified"
- Check DNS records are properly configured
- Wait for DNS propagation (up to 24 hours)
- Use resend.dev domain for testing

**Issue**: "Rate limit exceeded"
- Check your Resend plan limits
- Reduce `RESEND_REQUESTS_PER_MINUTE` setting
- Consider upgrading your Resend plan

**Issue**: "Email bounced or rejected"
- Verify recipient email address is valid
- Check sender domain reputation
- Review email content for spam indicators

## 🔒 Security Best Practices

### API Key Storage

1. **Use Environment Variables**
   ```bash
   # .env file (never commit to git)
   
   # Required API Keys
   NOTION_TOKEN=secret_your_actual_notion_token_here
   HUNTER_API_KEY=your_actual_hunter_api_key_here
   
   # Azure OpenAI Configuration (Recommended)
   USE_AZURE_OPENAI=true
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-email-gen
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   
   # Alternative: Regular OpenAI (if not using Azure)
   # USE_AZURE_OPENAI=false
   # OPENAI_API_KEY=sk-your_actual_openai_key_here
   
   # Email Sending Configuration
   RESEND_API_KEY=re_your_resend_api_key_here
   SENDER_EMAIL=your-name@yourdomain.com
   SENDER_NAME=Your Name
   REPLY_TO_EMAIL=your-name@yourdomain.com
   
   # Enhanced AI Features
   ENABLE_AI_PARSING=true
   ENABLE_PRODUCT_ANALYSIS=true
   ENHANCED_PERSONALIZATION=true
   AI_PARSING_MODEL=gpt-4
   PRODUCT_ANALYSIS_MODEL=gpt-4
   EMAIL_GENERATION_MODEL=gpt-4
   
   # Processing Configuration
   SCRAPING_DELAY=2.0
   HUNTER_REQUESTS_PER_MINUTE=10
   RESEND_REQUESTS_PER_MINUTE=100
   MAX_PRODUCTS_PER_RUN=50
   MAX_PROSPECTS_PER_COMPANY=10
   
   # Email Configuration
   EMAIL_TEMPLATE_TYPE=professional
   PERSONALIZATION_LEVEL=medium
   MAX_EMAIL_LENGTH=500
   
   # Workflow Configuration
   ENABLE_ENHANCED_WORKFLOW=true
   AUTO_SEND_EMAILS=false
   EMAIL_REVIEW_REQUIRED=true
   BATCH_PROCESSING_ENABLED=true
   ```

2. **Set File Permissions**
   ```bash
   chmod 600 .env
   chmod 600 config.yaml
   ```

3. **Use .gitignore**
   ```gitignore
   .env
   config.yaml
   *.key
   secrets/
   ```

### Key Rotation

1. **Regular Rotation**
   - Rotate keys every 3-6 months
   - Rotate immediately if compromised
   - Keep old keys until transition is complete

2. **Monitor Usage**
   - Check API usage regularly
   - Set up alerts for unusual activity
   - Monitor costs and quotas

### Access Control

1. **Principle of Least Privilege**
   - Only grant necessary permissions
   - Use separate keys for different environments
   - Limit integration access scope

2. **Environment Separation**
   ```bash
   # Development
   OPENAI_API_KEY=sk-dev_key_here

   # Production  
   OPENAI_API_KEY=sk-prod_key_here
   ```

## 📊 Monitoring and Usage

### Track API Usage

1. **Hunter.io Dashboard**
   - Monitor monthly quota usage
   - Check request history
   - View success/failure rates

2. **OpenAI Usage Dashboard**
   - Monitor token usage and costs
   - Set up billing alerts
   - Track model performance

3. **Notion Integration Logs**
   - Check integration activity
   - Monitor database operations
   - Review access patterns

### System Monitoring

Use the built-in monitoring features:

```bash
# Check API health
python cli.py status

# View detailed monitoring
python examples/error_handling_example.py

# Check quota status
python -c "
from utils.error_handling import get_error_handler
handler = get_error_handler()
quotas = handler.get_quota_status()
for name, quota in quotas.items():
    print(f'{name}: {quota.used}/{quota.limit} ({quota.usage_percentage:.1f}%)')
"
```

## 🧪 Testing Your Configuration

### Complete API Test

```bash
# Test all API connections and configuration
python cli.py validate-config

# Test all APIs with dry-run
python cli.py --dry-run --verbose discover --limit 1

# Test individual components
python -c "
from utils.config import Config
config = Config.from_env()
config.validate()
print('✅ All API keys configured correctly')
"
```

### Quota Check Script

Create a script to check all quotas:

```python
#!/usr/bin/env python3
"""Check API quotas and health."""

from utils.config import Config
from utils.error_handling import get_error_handler
from utils.api_monitor import get_api_monitor

def main():
    # Load config
    config = Config.from_env()
    
    # Check quotas
    error_handler = get_error_handler()
    quotas = error_handler.get_quota_status()
    
    print("API Quota Status:")
    print("-" * 40)
    for name, quota in quotas.items():
        status = "⚠️ NEAR LIMIT" if quota.is_near_limit else "✅ OK"
        print(f"{quota.service_name}: {quota.used}/{quota.limit} ({quota.usage_percentage:.1f}%) {status}")
    
    # Check API health
    api_monitor = get_api_monitor()
    health = api_monitor.get_service_health()
    
    print("\nAPI Health Status:")
    print("-" * 40)
    for service, status in health.items():
        print(f"{service}: {status.status.value} (Success: {status.success_rate:.1f}%)")

if __name__ == "__main__":
    main()
```

## 🆘 Getting Help

### Common Issues Resolution

1. **Configuration Validation Errors**
   ```bash
   python cli.py --dry-run status
   ```

2. **API Connection Issues**
   ```bash
   python cli.py --verbose --dry-run discover --limit 1
   ```

3. **Quota and Limit Issues**
   ```bash
   python examples/error_handling_example.py
   ```

### Support Resources

- **Notion**: [Notion Developer Support](https://developers.notion.com/docs)
- **Hunter.io**: [Hunter.io API Documentation](https://hunter.io/api-documentation)
- **OpenAI**: [OpenAI API Documentation](https://platform.openai.com/docs)

### Emergency Procedures

If API keys are compromised:

1. **Immediately revoke** the compromised keys
2. **Generate new keys** with different names
3. **Update configuration** with new keys
4. **Monitor usage** for any unauthorized activity
5. **Review access logs** in each service

---

**Security Reminder**: Never share your API keys or commit them to version control. Always use environment variables or secure configuration files with proper permissions.