<div align="center">

# 🔑 API Keys Configuration Guide
*Complete setup guide for all required and optional API services*

🎯 **Step-by-step** • 📱 **Interactive Setup** • 💰 **Cost Analysis** • 🔒 **Security Best Practices**

[![Required APIs](https://img.shields.io/badge/required%20APIs-2-red.svg)]()
[![Optional APIs](https://img.shields.io/badge/optional%20APIs-5-blue.svg)]()
[![Setup Time](https://img.shields.io/badge/setup%20time-15--20%20min-green.svg)]()
[![Free Tiers](https://img.shields.io/badge/free%20tiers-available-brightgreen.svg)]()

</div>

---

## 🎨 API Services Overview

<div align="center">

**🎯 Choose your services based on needs and budget**

</div>

<div align="center">

### 📈 **API Services Matrix**

| Service | Purpose | Required | Free Tier | Monthly Cost | Setup Time |
|:---|:---|:---:|:---:|:---:|:---:|
| 📊 **Notion** | Data storage | ✅ Required | ✓ Unlimited | $0 | 5 min |
| 🔍 **Hunter.io** | Email discovery | ✅ Required | 25/month | $49/mo | 3 min |
| 🤖 **AI Provider** | AI processing | ❗ Choose one+ | Varies | ~$6-12/mo | 2-10 min |
| ☁️ **Azure OpenAI** | Enterprise AI | ❗ Alternative | Pay-as-go | ~$8/mo | 10 min |
| 🧠 **Anthropic** | Claude AI | ❗ Alternative | $5 credit | ~$12/mo | 3 min |
| 🌎 **Google** | Gemini AI | ❗ Alternative | Free tier | ~$6/mo | 5 min |
| 📧 **Resend** | Email sending | ❓ Optional | 3k/month | $20/mo | 2 min |

</div>

### 💰 **Cost Analysis**

<div align="center">

| Usage Level | Monthly Cost | Recommended Setup |
|:---|:---:|:---|
| **Beginner** | $0-15 | Notion + Hunter.io + AI provider free tier |
| **Regular User** | $15-30 | All required + Resend for automation |
| **Power User** | $30-60 | Enterprise AI + multiple providers |

</div>

---

## 📊 Notion Integration Setup

<div align="center">

**🎯 Required for data storage • Free forever • 5-minute setup**

</div>

### 🚀 Quick Setup Process

```mermaid
flowchart LR
    A[🚀 Go to Notion Developers] --> B[🎆 Create Integration]
    B --> C[🔑 Copy Token]
    C --> D[⚙️ Configure Workspace]
    D --> E[✅ Test Connection]
    
    style A fill:#e8f5e8
    style E fill:#d4edda
```

### Step 1: 🎆 Create Notion Integration

<details>
<summary><strong>📱 Interactive Setup (click to expand)</strong></summary>

#### 1.1 Navigate to Notion Developers
- 🔗 **Link**: [https://developers.notion.com/](https://developers.notion.com/)
- 📡 **Action**: Click "View my integrations" or "Create new integration"

#### 1.2 Create Integration
```
🏷️ Name: "ProspectAI Automation"
🏢 Workspace: [Select your workspace]
🖼️ Logo: [Optional - upload custom logo]
```

#### 1.3 Configure Capabilities
✅ **Read content** ← Required for reading existing data
✅ **Insert content** ← Required for creating new entries
✅ **Update content** ← Required for updating prospect data
❌ **Read user information** ← Not needed
❌ **Read user information without email** ← Not needed

#### 1.4 Get Your Token
- 📾 **Click**: "Submit" to create integration
- 🔑 **Copy**: The "Internal Integration Token" (starts with `secret_`)
- ⚠️ **Important**: Save securely - won't be shown again!

</details>

### Step 2: ⚙️ Configure Workspace Access

<div align="center">

**🎯 Choose your setup method**

</div>

<div align="center">

| 🎆 **Auto-Setup** (Recommended) | 📋 **Existing Database** |
|:---:|:---:|
| Let system create everything | Use your existing Notion setup |
| No manual configuration | Manual database sharing required |
| Perfect for beginners | Full control over structure |
| ✅ **Just add API key** | ⚙️ **Additional setup needed** |

</div>

<details>
<summary><strong>🎆 Option A: Auto-Setup (Recommended for beginners)</strong></summary>

**✨ Zero configuration needed!**

1. Just add your token to `.env` file:
   ```env
   NOTION_TOKEN=secret_your_token_here
   ```

2. Run the setup command:
   ```bash
   python scripts/setup_dashboard.py
   ```

3. System will automatically:
   - 📊 Create main dashboard
   - 📄 Create prospect database
   - 📊 Create analytics database
   - 🔗 Set up all relationships

**✅ Result**: Fully functional Notion workspace in 30 seconds!

</details>

<details>
<summary><strong>📋 Option B: Use Existing Database</strong></summary>

**🔧 For advanced users who want control**

#### B.1 Create or Select Database
1. Open Notion and create a new database
2. Or select an existing database you want to use

#### B.2 Share Database with Integration
1. Open the database in Notion
2. Click "Share" in the top-right corner
3. Click "Invite" and search for "ProspectAI Automation"
4. Select your integration and click "Invite"

#### B.3 Get Database ID
1. Copy the database URL from browser:
   ```
   https://notion.so/workspace/DATABASE_ID?v=...
   ```
2. Extract the DATABASE_ID part
3. Add to your `.env` file:
   ```env
   NOTION_TOKEN=secret_your_token_here
   NOTION_DATABASE_ID=your_database_id
   ```

</details>

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

## 🤖 Anthropic Claude API Setup

Anthropic Claude offers constitutional AI with strong safety features and excellent reasoning capabilities.

### Step 1: Create Anthropic Account

1. **Sign Up**
   - Go to [https://console.anthropic.com/](https://console.anthropic.com/)
   - Click "Sign up"
   - Use email or Google account

2. **Verify Account**
   - Verify your email address
   - Complete any required verification steps

### Step 2: Set Up Billing

**Important**: Anthropic requires a payment method for API access.

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
   - Go to "API Keys" section in the console
   - Or visit [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

2. **Create New Key**
   - Click "Create Key"
   - Give it a descriptive name: "Job Prospect Automation"
   - Copy the key immediately (starts with `sk-ant-`)
   - **Important**: Save it securely - it won't be shown again

### Step 4: Configure for Anthropic Claude

```env
# Anthropic Claude Configuration
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here

# Model Configuration (choose one)
AI_MODEL=claude-3-sonnet-20240229      # Balanced performance and speed
# AI_MODEL=claude-3-opus-20240229      # Most capable, slower
# AI_MODEL=claude-3-haiku-20240307     # Fastest, good for simple tasks
# AI_MODEL=claude-3-5-sonnet-20241022  # Latest with improved capabilities
```

### Step 5: Understand Costs

#### Typical Usage Costs:
- **Claude-3-Haiku**: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
- **Claude-3-Sonnet**: ~$3 per 1M input tokens, ~$15 per 1M output tokens  
- **Claude-3-Opus**: ~$15 per 1M input tokens, ~$75 per 1M output tokens
- **Claude-3.5-Sonnet**: ~$3 per 1M input tokens, ~$15 per 1M output tokens

#### For This Application:
- **Per company processed**: ~47K tokens (~$0.08-0.40 depending on model)
- **10 companies**: ~$0.80-4.00
- **100 companies**: ~$8-40

### Step 6: Model Selection Guide

- **Claude-3-Haiku**: Best for cost-conscious users, simple email generation
- **Claude-3-Sonnet**: Recommended balance of quality and cost
- **Claude-3-Opus**: Best quality for complex analysis and personalization
- **Claude-3.5-Sonnet**: Latest model with improved capabilities

## 🤖 Google Gemini API Setup

Google Gemini offers multimodal AI capabilities with competitive pricing and strong performance.

### Step 1: Create Google Cloud Account

1. **Sign Up**
   - Go to [https://console.cloud.google.com/](https://console.cloud.google.com/)
   - Click "Get started for free"
   - Use your Google account or create a new one

2. **Verify Account**
   - Complete phone verification
   - Add payment method (required for API access)
   - Accept terms of service

### Step 2: Enable Generative AI API

1. **Create or Select Project**
   - Create a new project or select existing one
   - Give it a descriptive name: "Job Prospect Automation"

2. **Enable APIs**
   - Go to "APIs & Services" > "Library"
   - Search for "Generative Language API"
   - Click on it and press "Enable"

### Step 3: Create API Key

1. **Navigate to Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"

2. **Secure Your Key**
   - Copy the API key immediately
   - Click "Restrict Key" (recommended)
   - Under "API restrictions", select "Restrict key"
   - Choose "Generative Language API"
   - Save the restrictions

### Step 4: Configure for Google Gemini

```env
# Google Gemini Configuration
AI_PROVIDER=google
GOOGLE_API_KEY=your_google_api_key_here

# Model Configuration (choose one)
AI_MODEL=gemini-pro                    # Recommended for most use cases
# AI_MODEL=gemini-1.5-pro             # Latest with enhanced capabilities
# AI_MODEL=gemini-1.5-flash           # Faster, cost-effective option
# AI_MODEL=gemini-pro-vision          # For multimodal tasks
```

### Step 5: Understand Costs

#### Typical Usage Costs:
- **Gemini Pro**: ~$0.50 per 1M input tokens, ~$1.50 per 1M output tokens
- **Gemini 1.5 Pro**: ~$3.50 per 1M input tokens, ~$10.50 per 1M output tokens
- **Gemini 1.5 Flash**: ~$0.075 per 1M input tokens, ~$0.30 per 1M output tokens

#### For This Application:
- **Per company processed**: ~47K tokens (~$0.02-0.15 depending on model)
- **10 companies**: ~$0.20-1.50
- **100 companies**: ~$2-15

### Step 6: Model Selection Guide

- **Gemini Pro**: Good balance of performance and cost
- **Gemini 1.5 Pro**: Best quality with long context support (1M tokens)
- **Gemini 1.5 Flash**: Most cost-effective, good for simple tasks
- **Gemini Pro Vision**: Use when you need image/multimodal capabilities

## 🤖 DeepSeek API Setup

DeepSeek offers specialized AI models with strong code generation capabilities and cost-effective pricing.

### Step 1: Create DeepSeek Account

1. **Sign Up**
   - Go to [https://platform.deepseek.com/](https://platform.deepseek.com/)
   - Click "Sign up"
   - Use email or other supported authentication methods

2. **Verify Account**
   - Verify your email address
   - Complete any required verification steps

### Step 2: Set Up Billing

**Important**: DeepSeek requires a payment method for API access.

1. **Add Payment Method**
   - Go to "Billing" in your dashboard
   - Click "Add payment method"
   - Add credit card or other payment method

2. **Set Usage Limits** (Recommended)
   - Set monthly spending limit (e.g., $5-25)
   - Set up usage alerts
   - This prevents unexpected charges

### Step 3: Create API Key

1. **Navigate to API Keys**
   - Go to "API Keys" section in the console
   - Or visit the API keys management page

2. **Create New Key**
   - Click "Create Key"
   - Give it a descriptive name: "Job Prospect Automation"
   - Copy the key immediately
   - **Important**: Save it securely - it won't be shown again

### Step 4: Configure for DeepSeek

```env
# DeepSeek Configuration
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key_here

# Model Configuration (choose one)
AI_MODEL=deepseek-chat                 # General purpose model
# AI_MODEL=deepseek-coder             # Code-specialized model
# AI_MODEL=deepseek-math              # Math-specialized model
```

### Step 5: Understand Costs

#### Typical Usage Costs:
- **DeepSeek-Chat**: ~$0.14 per 1M input tokens, ~$0.28 per 1M output tokens
- **DeepSeek-Coder**: ~$0.14 per 1M input tokens, ~$0.28 per 1M output tokens
- **DeepSeek-Math**: ~$0.14 per 1M input tokens, ~$0.28 per 1M output tokens

#### For This Application:
- **Per company processed**: ~47K tokens (~$0.01-0.02)
- **10 companies**: ~$0.10-0.20
- **100 companies**: ~$1-2

### Step 6: Model Selection Guide

- **DeepSeek-Chat**: Best for general email generation and business communication
- **DeepSeek-Coder**: Excellent for technical content and code-related analysis
- **DeepSeek-Math**: Specialized for mathematical and analytical content

### DeepSeek Troubleshooting

**Issue**: "Invalid API key"
- Verify key is copied correctly (no extra spaces)
- Check if account is activated
- Try generating a new API key

**Issue**: "Rate limit exceeded"
- DeepSeek uses OpenAI-compatible rate limiting
- Wait for rate limit reset
- Consider upgrading plan if needed

**Issue**: "Model not available"
- Verify model name is correct (deepseek-chat, deepseek-coder, etc.)
- Check if model is available in your region
- Try using the default deepseek-chat model

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

## 🤖 Multi-Provider AI Configuration

The system now supports multiple AI providers through a unified **AI Provider Manager** that handles provider registration, discovery, instantiation, and switching functionality with thread-safe operations.

### AI Provider Manager Features

- **Unified Interface**: Single API for all AI providers with consistent request/response handling
- **Automatic Provider Discovery**: Auto-configures providers based on available credentials
- **Thread-Safe Operations**: Singleton pattern with thread-safe provider management
- **Dynamic Provider Loading**: Providers loaded on-demand to avoid import issues
- **Configuration Validation**: Built-in validation for provider-specific requirements
- **Connection Testing**: Test provider connections before use
- **Provider Switching**: Runtime switching between configured providers

### Provider Selection

Configure your preferred provider using the AI_PROVIDER environment variable:

```env
# Select your AI provider
AI_PROVIDER=openai  # Options: openai, azure-openai, anthropic, google, deepseek

# Provider-specific model configuration
AI_MODEL=gpt-4  # Use provider-specific model names
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
```

### Provider-Specific Setup

#### OpenAI (Default)
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your_openai_key_here
AI_MODEL=gpt-4
```

#### Azure OpenAI (Recommended for Enterprise)
```env
AI_PROVIDER=azure-openai
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
AI_MODEL=gpt-4
```

#### Anthropic Claude
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
AI_MODEL=claude-3-sonnet-20240229
```

#### Google Gemini
```env
AI_PROVIDER=google
GOOGLE_API_KEY=your_google_key
AI_MODEL=gemini-pro
```

#### DeepSeek
```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key
AI_MODEL=deepseek-chat
```

### CLI Provider Management

Manage AI providers through CLI commands:

```bash
# List available providers
python cli.py list-ai-providers

# Configure a specific provider interactively
python cli.py configure-ai --provider anthropic

# Switch active provider
python cli.py set-ai-provider anthropic

# Validate current provider configuration
python cli.py validate-ai-config

# Test provider connection
python cli.py test-ai-provider anthropic
```

### Python API Usage

Use the AI Provider Manager programmatically:

```python
from services.ai_provider_manager import get_provider_manager, configure_provider_manager
from services.openai_client_manager import CompletionRequest
from utils.config import Config

# Configure the provider manager
config = Config.from_env()
configure_provider_manager(config)

# Get the provider manager
manager = get_provider_manager()

# List available providers
providers = manager.list_providers()
print(f"Available providers: {providers}")

# Get active provider
active_provider = manager.get_active_provider_name()
print(f"Active provider: {active_provider}")

# Make a completion request
request = CompletionRequest(
    messages=[{"role": "user", "content": "Hello, world!"}],
    model="gpt-4",
    temperature=0.7
)
response = manager.make_completion(request)

# Switch providers at runtime
manager.set_active_provider("anthropic")

# Validate provider configuration
validation_result = manager.validate_provider("openai")
print(f"OpenAI validation: {validation_result.status}")
```

### Provider Status and Monitoring

Check provider status and configuration:

```python
# Get comprehensive provider status
status = manager.get_provider_status()
print(f"Active provider: {status['active_provider']}")
print(f"Total configured: {status['total_configured']}")

# Validate all providers
results = manager.validate_all_providers()
for provider_name, result in results.items():
    print(f"{provider_name}: {result.status} - {result.message}")
```

### Provider Comparison

| Provider | Strengths | Best For | Cost | Status |
|----------|-----------|----------|------|--------|
| **OpenAI** | Proven performance, extensive ecosystem | General use, development | $ | ✅ Available |
| **Azure OpenAI** | Enterprise security, SLA guarantees | Production, compliance | $$ | ✅ Available |
| **Anthropic** | Safety focus, longer context | Complex reasoning, safety-critical | $ | ✅ Available |
| **Google Gemini** | Multimodal, competitive pricing | Cost optimization, multimodal | $ | ✅ Available |
| **DeepSeek** | Code specialization, cost-effective | Code generation, budget-conscious | $ | ✅ Available |

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