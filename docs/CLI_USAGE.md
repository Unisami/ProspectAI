# Job Prospect Automation CLI Usage Guide

## Overview

The Job Prospect Automation CLI provides a command-line interface for running different stages of the job prospecting workflow. It supports configuration management, dry-run mode for testing, and comprehensive help documentation.

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your configuration (see Configuration section below)

3. Run the CLI:
```bash
python cli.py --help
```

## Configuration

### Environment Variables

Set the following environment variables or create a `.env` file:

```bash
# Required API Keys
NOTION_TOKEN=your_notion_token_here
HUNTER_API_KEY=your_hunter_api_key_here

# Azure OpenAI Configuration (Recommended)
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment

# Alternative: Regular OpenAI
# USE_AZURE_OPENAI=false
# OPENAI_API_KEY=your_openai_api_key_here

# Email Sending (Optional)
RESEND_API_KEY=your_resend_api_key_here
SENDER_EMAIL=your-name@yourdomain.com
SENDER_NAME=Your Full Name


# Optional: User mention settings for enhanced notifications (future feature)
NOTION_USER_ID=your-notion-user-id  # For @mentions in notifications
USER_EMAIL=your-email@domain.com    # For @remind notifications

# Enhanced AI Service Configuration
AI_SERVICE_CACHE_ENABLED=true
AI_SERVICE_CACHE_TTL=3600
AI_SERVICE_RATE_LIMIT_DELAY=1.0

# Caching Configuration
ENABLE_CACHING=true
CACHE_MEMORY_MAX_ENTRIES=1000
CACHE_MEMORY_MAX_MB=100
CACHE_PERSISTENT_DIR=.cache
CACHE_DEFAULT_TTL=3600

# Enhanced Error Handling
ERROR_HANDLING_ENABLED=true
ERROR_RECOVERY_ATTEMPTS=3
ERROR_NOTIFICATION_ENABLED=true

# Rate Limiting
RATE_LIMITING_ENABLED=true
OPENAI_RATE_LIMIT=60
HUNTER_RATE_LIMIT=100
LINKEDIN_RATE_LIMIT=60

# Legacy Settings (still supported)
ENABLE_AI_PARSING=true
ENABLE_PRODUCT_ANALYSIS=true
ENHANCED_PERSONALIZATION=true

# Processing Settings
SCRAPING_DELAY=2.0
HUNTER_REQUESTS_PER_MINUTE=10
MAX_PRODUCTS_PER_RUN=50
MAX_PROSPECTS_PER_COMPANY=10
EMAIL_TEMPLATE_TYPE=professional
PERSONALIZATION_LEVEL=high
```

### Configuration File

Create a configuration file using the template:

```bash
# Create a configuration template
python cli.py init-config config.yaml

# Edit the file with your API keys
# Then use it with the CLI
python cli.py --config config.yaml discover
```

### Configuration Validation

The refactored architecture includes enhanced configuration validation:

```bash
# Validate configuration with new centralized service
python cli.py validate-config

# Test configuration with dry-run mode
python cli.py --dry-run --verbose status

# Check specific service configurations
python -c "from utils.configuration_service import ConfigurationService; ConfigurationService().validate_config()"
```

### Performance Monitoring

Monitor system performance with the new architecture:

```bash
# Check cache performance
python -c "from services.caching_service import CachingService; from utils.config import Config; cs = CachingService(Config.from_env()); print(cs.get_stats())"

# Monitor AI service performance
python -c "from services.ai_service import AIService; from utils.config import Config; ai = AIService(Config.from_env()); print(ai.get_performance_metrics())"

# Clear cache if needed
python -c "from services.caching_service import CachingService; from utils.config import Config; CachingService(Config.from_env()).clear_all()"
```

## Commands

### Global Options

- `--config, -c`: Path to configuration file (YAML or JSON)
- `--dry-run`: Run in dry-run mode (no actual API calls)
- `--verbose, -v`: Enable verbose logging
- `--help`: Show help message

### run-campaign

🚀 Run the COMPLETE automation workflow - from discovery to email sending!

```bash
# Complete workflow with email generation and sending
python cli.py run-campaign --limit 10 --generate-emails --send-emails

# Discovery and email generation only (no sending)
python cli.py run-campaign --limit 10 --generate-emails

# With sender profile and custom campaign name
python cli.py run-campaign --limit 10 --sender-profile profiles/my_profile.md --campaign-name "Weekly Outreach"

# Auto-setup dashboard if not configured
python cli.py run-campaign --limit 10 --auto-setup --generate-emails

# Dry run to test complete workflow
python cli.py --dry-run run-campaign --limit 5 --generate-emails --send-emails
```

**Options:**
- `--limit, -l`: Maximum number of companies to process (default: 10)
- `--campaign-name, -c`: Name for this campaign
- `--sender-profile, -p`: Path to sender profile file
- `--generate-emails`: Generate emails for found prospects
- `--send-emails`: Send generated emails immediately
- `--auto-setup`: Auto-setup dashboard if not configured

### discover

Run the discovery pipeline to find prospects (discovery only).

```bash
# Basic usage
python cli.py discover

# With options
python cli.py discover --limit 10 --batch-size 3

# With sender profile
python cli.py discover --limit 10 --sender-profile profiles/my_profile.md

# With custom campaign name for progress tracking
python cli.py discover --limit 10 --campaign-name "Weekly Discovery - Jan 2024"

# Dry run to test without API calls
python cli.py --dry-run discover --limit 5
```

**Options:**
- `--limit, -l`: Maximum number of products to process (default: 50)
- `--batch-size, -b`: Batch size for processing companies (default: 5)
- `--sender-profile, -p`: Path to sender profile file for personalization
- `--campaign-name, -c`: Name for this campaign (for progress tracking)

**Performance:**
- Uses parallel processing with 3 concurrent workers by default
- Processing rate: ~10-15 companies/minute (3-5x faster than sequential)
- Automatic progress tracking and error recovery

### process-company

Process a specific company to find prospects.

```bash
# Process a company by name
python cli.py process-company "Acme Corp"

# Specify domain if known
python cli.py process-company "Acme Corp" --domain acme.com

# Dry run
python cli.py --dry-run process-company "Test Company"
```

**Arguments:**
- `company_name`: Name of the company to process

**Options:**
- `--domain`: Company domain (if known)

### generate-emails

Generate personalized outreach emails for prospects.

```bash
# Generate emails for specific prospects
python cli.py generate-emails --prospect-ids "id1,id2,id3"

# Use different template
python cli.py generate-emails --prospect-ids "id1,id2" --template referral

# Generate emails (sending is handled separately)
python cli.py generate-emails --prospect-ids "id1,id2"

# Use sender profile for personalization
python cli.py generate-emails --prospect-ids "id1" --sender-profile profiles/my_profile.md

# Save to file
python cli.py generate-emails --prospect-ids "id1" --output emails.json
```

**Options:**
- `--prospect-ids`: Comma-separated list of prospect IDs (required)
- `--template`: Email template type (cold_outreach, referral, follow_up)
- `--output, -o`: Output file for generated emails
- `--send`: (Deprecated) Use send-emails-recent command instead
- `--sender-profile, -p`: Path to sender profile file for personalization
- `--use-default-profile`: Use default sender profile
- `--interactive-profile`: Create sender profile interactively
- `--validate-profile`: Validate sender profile before generating emails

### generate-emails-recent

Generate emails for the most recently discovered prospects (convenience command).

```bash
# Generate emails for 10 most recent prospects
python cli.py generate-emails-recent

# Generate for specific number of recent prospects
python cli.py generate-emails-recent --limit 5

# Use different template
python cli.py generate-emails-recent --template referral_followup

# Generate emails for recent prospects
python cli.py generate-emails-recent --limit 5

# Use specific template
python cli.py generate-emails-recent --limit 3 --template product_interest
```

**Options:**
- `--limit, -l`: Number of recent prospects to generate emails for (default: 10)
- `--template`: Email template type (cold_outreach, referral_followup, product_interest, networking)
- `--send`: (Deprecated) Use send-emails-recent command instead

### send-emails-recent

Send the most recently generated emails that haven't been sent yet. This command finds prospects with generated email content and sends them using batch processing with configurable delays.

```bash
# Send 10 most recent generated emails
python cli.py send-emails-recent

# Send specific number of recent emails
python cli.py send-emails-recent --limit 5

# Use custom batch size and delay
python cli.py send-emails-recent --limit 20 --batch-size 3 --delay 60

# Dry run to see what would be sent
python cli.py --dry-run send-emails-recent --limit 5
```

**Options:**
- `--limit, -l`: Number of recent generated emails to send (default: 10)
- `--batch-size, -b`: Batch size for sending emails (default: 5)
- `--delay, -d`: Delay between batches in seconds (default: 30)

**Output:**
The command provides detailed results categorized as:
- ✅ **Sent**: Successfully delivered emails with email IDs
- ⏭️ **Skipped**: Emails already sent (prevents duplicates)
- ❌ **Failed**: Emails that couldn't be sent with error details

### validate-config

Validate your configuration, API keys, and test all API connections.

```bash
# Validate current configuration and test API connections
python cli.py validate-config

# Validate specific config file and test connections
python cli.py --config config.yaml validate-config

# Check specific sender profile
python cli.py validate-config --check-profile profiles/my_profile.md
```

**What it tests:**
- ✅ **Configuration validation**: Checks all required settings and values
- ✅ **API connection testing**: Tests connections to Notion, Hunter.io, OpenAI, and Resend APIs
- ✅ **Sender profile validation**: Validates profile completeness and format
- ✅ **Service initialization**: Ensures all services can be properly initialized

**Options:**
- `--check-profile, -p`: Path to sender profile file to validate

### Test Scripts

Run comprehensive tests using the provided test scripts:

```bash
# Apply comprehensive performance optimizations (recommended first)
python scripts/fix_all_performance_issues.py

# Run full pipeline test
python scripts/test_full_pipeline.py

# Test email generation and sending
python scripts/test_email_pipeline.py

# Test email generation and actually send emails
python scripts/test_email_pipeline.py --send-emails

# Debug email generation process step-by-step
python scripts/debug_email_generation.py

# Test simple email functionality
python scripts/test_simple_email.py

# Test email sending functionality
python scripts/test_email_sending.py

# Debug email sending issues with Resend API
python scripts/test_email_send.py

# Test AI personalization data quality and completeness
python scripts/test_personalization_fix.py

# Test company deduplication functionality and performance
python scripts/test_company_deduplication.py

# Debug discovery issues (why no unprocessed companies found)
python scripts/debug_discovery.py

# Update existing prospects with correct email field defaults
python update_existing_prospects_defaults.py
```

### profile-setup

Set up a sender profile for email personalization.

```bash
# Create profile interactively
python cli.py profile-setup --interactive

# Generate a profile template
python cli.py profile-setup --template --format markdown

# Create profile and set as default
python cli.py profile-setup --interactive --set-default

# Generate template in different formats
python cli.py profile-setup --template --format json --output profiles/template.json
```

**Options:**
- `--interactive`: Create profile interactively
- `--template`: Generate a profile template
- `--format, -f`: Output format (markdown, json, yaml)
- `--output, -o`: Output file path
- `--set-default`: Set as default profile

### analyze-products

Run comprehensive product analysis on companies.

```bash
# Analyze specific companies
python cli.py analyze-products --company-ids "id1,id2"

# Analyze latest companies
python cli.py analyze-products --limit 10

# Dry run
python cli.py --dry-run analyze-products --limit 5
```

**Options:**
- `--company-ids`: Comma-separated list of company IDs to analyze
- `--limit, -l`: Maximum number of companies to analyze (default: 10)

### ai-parse

Parse raw data using AI parsing capabilities.

```bash
# Parse LinkedIn profile data
python cli.py ai-parse --input-file profile.html --data-type linkedin --output parsed.json

# Parse product information
python cli.py ai-parse --input-file product.html --data-type product --output product.json

# Parse team data
python cli.py ai-parse --input-file team.html --data-type team --output team.json
```

**Options:**
- `--input-file`: File containing raw data to parse (required)
- `--data-type`: Type of data to parse (linkedin, product, team, company)
- `--output, -o`: Output file for parsed data

### test-components

Test individual system components.

```bash
# Test all components
python cli.py test-components

# Test specific component
python cli.py test-components --component ai-parser

# Test email sender
python cli.py test-components --component email-sender
```

**Options:**
- `--component`: Component to test (ai-parser, product-analyzer, email-sender, all)

### validate-config

Validate your configuration, API keys, and test all API connections.

```bash
# Validate current configuration and test API connections
python cli.py validate-config

# Validate specific config file and test connections
python cli.py --config config.yaml validate-config
```

**What it tests:**
- Configuration validation and API connection testing
- Tests connections to Notion, Hunter.io, OpenAI, and Resend APIs
- Service initialization and sender profile validation

### status

Show current workflow status and statistics.

```bash
# Show system status
python cli.py status

# Dry run
python cli.py --dry-run status
```

### setup-dashboard

Set up the Notion progress dashboard for campaign tracking and monitoring.

```bash
# Set up dashboard with default configuration
python scripts/setup_dashboard.py

# Set up dashboard and save configuration
python scripts/setup_dashboard.py --save-config
```

This command creates:
- **Campaign Runs Database**: Track campaign progress and metrics
- **Processing Log Database**: Detailed step-by-step processing logs
- **System Status Database**: Component health and API quota monitoring
- **Daily Analytics Database**: Daily summary statistics and trends
- **Email Queue Database**: Email approval and sending queue
- **Main Dashboard Page**: Central hub with links to all databases

### daily-summary

Create or update today's daily analytics summary with campaign statistics.

```bash
# Create/update today's daily summary
python cli.py daily-summary

# Dry run to see what would be updated
python cli.py --dry-run daily-summary
```

This command:
- Aggregates daily statistics from all campaigns
- Creates a new daily entry or updates existing one
- Tracks metrics like campaigns run, companies processed, prospects found
- Calculates success rates and processing efficiency
- Estimates API call usage across all operations

**Troubleshooting:** If daily summary creation fails, use the debug script:
```bash
python scripts/debug_daily_analytics.py
```

### campaign-status

Show current campaign status and progress information.

```bash
# Show current campaign status
python cli.py campaign-status
```

This command displays:
- Campaign name and current status
- Progress percentage and current step
- Companies processed vs target
- Prospects found and emails generated
- Success rate and error count

### email-queue

Manage the email approval queue for review and sending.

```bash
# List pending emails for approval
python cli.py email-queue

# List with specific action
python cli.py email-queue --action list

# Approve specific email (future feature)
python cli.py email-queue --action approve --email-id "email-123"

# Reject specific email (future feature)
python cli.py email-queue --action reject --email-id "email-123"
```

**Options:**
- `--action`: Action to perform (list, approve, reject)
- `--email-id`: Email ID for approve/reject actions

### pause-campaign

Pause the current active campaign with a reason.

```bash
# Pause current campaign
python cli.py pause-campaign

# Pause with specific reason
python cli.py pause-campaign --reason "API rate limit reached"
```

**Options:**
- `--reason`: Reason for pausing (default: "User requested")

### test-notifications

Test all notification types to see how they appear in Notion with enhanced formatting.

```bash
# Test all notification types
python cli.py test-notifications
```

This command sends sample notifications of each type to your Notion dashboard, allowing you to see:
- Enhanced callout formatting with priority-based colors
- Quick action links to relevant dashboard sections
- High priority notification reminders
- Rich formatting with contextual troubleshooting guides

### send-notification

Send a test notification or daily summary.

```bash
# Send test notification
python cli.py send-notification --type test

# Send daily summary
python cli.py send-notification --type daily
```

**Options:**
- `--type`: Type of notification to send (test, daily)

The notification system provides automated alerts for:
- **Campaign Completion**: Success metrics and duration
- **Campaign Failures**: Error details and context
- **Daily Summaries**: Daily statistics and performance
- **Error Alerts**: Real-time component failure notifications
- **Weekly Reports**: Comprehensive performance analysis

### batch-history

Show batch processing history.

```bash
# Show batch history
python cli.py batch-history
```

### init-config

Initialize a configuration file with default values.

```bash
# Create config.yaml with defaults
python cli.py init-config

# Create custom filename
python cli.py init-config my-config.yaml
```

## Usage Examples

### Complete Workflow

```bash
# 1. Validate configuration
python cli.py validate-config

# 2. Test full pipeline
python scripts/test_full_pipeline.py

# 3. Run complete campaign workflow (recommended)
python cli.py run-campaign --limit 10 --generate-emails --send-emails --sender-profile profiles/my_profile.md

# Alternative: Step-by-step approach
# 3a. Run discovery only
python cli.py discover --limit 10 --sender-profile profiles/my_profile.md --campaign-name "Weekly Outreach"

# 3b. Check status
python cli.py status

# 3c. Test email generation
python scripts/test_email_pipeline.py

# 3c-alt. Debug email generation issues
python scripts/debug_email_generation.py

# 3d. Generate emails for found prospects
python cli.py generate-emails --prospect-ids "id1,id2,id3" --sender-profile profiles/my_profile.md

# Alternative: Generate emails for recent prospects (easier)
python cli.py generate-emails-recent --limit 5

# 3e. Send emails (use separate command)
# Send recently generated emails
python cli.py send-emails-recent --limit 5

# Alternative: Send specific emails
python cli.py send-emails-recent --limit 5
```

### Development and Testing

```bash
# Test configuration without API calls
python cli.py --dry-run --verbose discover

# Process a single company for testing
python cli.py --dry-run process-company "Test Company" --domain test.com

# Check what emails would be generated
python cli.py --dry-run generate-emails --prospect-ids "test1,test2"
```

### Batch Processing

```bash
# Run with smaller batches for better control
python cli.py discover --batch-size 3 --limit 15

# Check batch history
python cli.py batch-history
```

### Configuration Management

```bash
# Create YAML config
python cli.py init-config config.yaml

# Create JSON config
python cli.py init-config config.json

# Use different configs for different environments
python cli.py --config dev-config.yaml discover
python cli.py --config prod-config.yaml discover
```

## Error Handling

The CLI provides comprehensive error handling:

- **Configuration Errors**: Clear messages about missing or invalid configuration
- **API Errors**: Graceful handling of API failures with retry mechanisms
- **Network Errors**: Automatic retries with exponential backoff
- **Validation Errors**: Input validation with helpful error messages

## Logging

The CLI supports different logging levels:

```bash
# Normal logging (INFO level)
python cli.py discover

# Verbose logging (DEBUG level)
python cli.py --verbose discover

# Quiet operation (redirect output)
python cli.py discover > results.log 2>&1
```

## Output Formats

The CLI provides rich, formatted output:

- **Tables**: Results displayed in formatted tables
- **Progress Bars**: Real-time progress indication
- **Color Coding**: Status indicators with colors
- **Panels**: Important information highlighted in panels

## Dry-Run Mode

Use dry-run mode to test commands without making actual API calls:

```bash
# Test discovery workflow
python cli.py --dry-run discover --limit 10

# Test email generation
python cli.py --dry-run generate-emails --prospect-ids "1,2,3"

# Test company processing
python cli.py --dry-run process-company "Test Company"
```

Dry-run mode will:
- Show what actions would be performed
- Validate configuration
- Test command syntax
- Display expected output format

## Troubleshooting

### Common Issues

1. **Missing API Keys**
   ```bash
   Error: NOTION_TOKEN environment variable is required
   ```
   Solution: Set environment variables or use configuration file

2. **Invalid Configuration**
   ```bash
   Error: Scraping delay must be non-negative
   ```
   Solution: Check configuration values in file or environment

3. **Network Errors**
   ```bash
   Error: Failed to connect to API
   ```
   Solution: Check internet connection and API key validity

4. **Permission Errors**
   ```bash
   Error: Cannot write to output file
   ```
   Solution: Check file permissions and directory access

### Testing Interactive Controls

If you're having issues with campaign controls or want to verify the interactive control system is working:

```bash
# Test interactive campaign controls
python scripts/test_interactive_controls.py
```

This script will:
- Check for active campaigns in your database
- Test control command detection and execution
- Provide manual testing instructions
- Display direct links to your Notion databases

### Getting Help

```bash
# General help
python cli.py --help

# Command-specific help
python cli.py discover --help
python cli.py generate-emails --help

# Version information
python cli.py --version
```

## Integration with Other Tools

The CLI can be integrated with other tools and scripts:

```bash
# Use in shell scripts
#!/bin/bash
python cli.py discover --limit 50
if [ $? -eq 0 ]; then
    echo "Discovery completed successfully"
    python cli.py status
fi

# Use with cron for scheduled runs
0 9 * * 1 /usr/bin/python /path/to/cli.py discover --limit 25

# Pipe output to other tools
python cli.py status | grep "Connected"
```