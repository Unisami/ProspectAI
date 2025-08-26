# Testing Guide

This guide provides comprehensive instructions for testing the Job Prospect Automation system, from basic configuration validation to full pipeline testing.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Scripts](#test-scripts)
- [Configuration Testing](#configuration-testing)
- [Pipeline Testing](#pipeline-testing)
- [Email Testing](#email-testing)
- [Component Testing](#component-testing)
- [Performance Testing](#performance-testing)
- [Troubleshooting Tests](#troubleshooting-tests)

## 🔍 Overview

The system includes several test scripts and validation tools to ensure everything works correctly:

### Available Test Scripts

1. **`test_full_pipeline.py`** - Comprehensive end-to-end pipeline test
2. **`test_email_pipeline.py`** - Email generation and sending test
3. **`test_simple_email.py`** - Basic email functionality test
4. **`test_email_sending.py`** - Email delivery test
5. **`test_email_send.py`** - Debug email sending issues with Resend API
6. **`debug_email_generation.py`** - Debug email generation process step-by-step
7. **`debug_email_content.py`** - Analyze email content for problematic characters
8. **`debug_notion_storage.py`** - Debug Notion storage during parallel processing
9. **`test_personalization_fix.py`** - Verify AI personalization data quality and completeness
10. **`test_interactive_controls.py`** - Interactive campaign controls test
11. **`test_company_deduplication.py`** - Test company deduplication functionality and performance
12. **`test_base_provider.py`** - Test BaseAIProvider interface for multi-model AI support
13. **CLI validation commands** - Built-in configuration validation and comprehensive API connection testing

### Testing Approach

- **Dry-run mode**: Test without making actual API calls
- **Incremental testing**: Test individual components before full pipeline
- **Configuration validation**: Verify all API keys and settings
- **Error handling**: Test system behavior under various failure conditions

## 🧪 Test Scripts

### 1. Full Pipeline Test

The most comprehensive test that validates the entire workflow:

```bash
# Run complete pipeline test
python test_full_pipeline.py
```

**What it tests:**
- Configuration validation
- Service initialization
- Discovery pipeline (ProductHunt scraping)
- Team member extraction with AI
- Email finding
- LinkedIn profile extraction
- Data storage in Notion
- Email generation
- Workflow status

**Expected output:**
```
================================================================================
 JOB PROSPECT AUTOMATION - FULL PIPELINE TEST
================================================================================

🔧 SERVICE INITIALIZATION STATUS:
   ProductHunt Scraper: ✅
   Notion Manager: ✅
   Email Finder: ✅
   LinkedIn Scraper: ✅
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
   Duration: 45.2 seconds

🚀 PARALLEL PROCESSING SUMMARY:
   Workers Used: 3
   Processing Rate: 4.0 companies/min
   Performance: 3-5x faster than sequential

✅ Configuration validation: PASSED
✅ Discovery pipeline: PASSED
✅ Email generation: PASSED
✅ Email sending: SKIPPED
✅ Workflow status: PASSED
```

### 2. Email Pipeline Test

Focused test for email generation and sending:

```bash
# Test email generation only
python test_email_pipeline.py

# Test email generation and sending
python test_email_pipeline.py --send-emails
```

**What it tests:**
- Prospect retrieval from Notion
- Email generation with AI personalization
- Email content validation
- Optional email sending via Resend

**Expected output:**
```
📊 PROSPECT SUMMARY:
   Total prospects: 5
   With emails: 3
   Without emails: 2

📧 SAMPLE GENERATED EMAIL:
   Prospect: John Smith at TechCorp
   Subject: Exploring collaboration opportunities with TechCorp
   Body preview: Hi John, I came across TechCorp on ProductHunt and was impressed by your AI analytics platform...
   Personalization score: 0.85

✅ Email generation results: 3 successful, 0 failed
```

### 3. Simple Email Test

Basic email functionality test:

```bash
python test_simple_email.py
```

**What it tests:**
- Basic email generation
- Template processing
- Sender profile integration

### 4. Email Sending Test

Test email delivery functionality:

```bash
python test_email_sending.py
```

**What it tests:**
- Resend API integration
- Email delivery
- Delivery tracking
- Error handling

### 5. Email Send Debug Test

Debug email sending issues with the Resend API:

```bash
python test_email_send.py
```

**What it tests:**
- Simple email sending functionality
- Special character handling in emails
- Actual email content from database
- Resend API troubleshooting

**Expected output:**
```
🚀 Starting email send test...
🧪 Testing simple email send...

📧 Test 1: Very simple email
✅ Simple email result: sent (ID: email-123)

📧 Test 2: Email with special characters
✅ Special chars email result: sent (ID: email-124)

🧪 Testing with actual email content...
📧 Test 3: Actual email content
Subject: 'Exploring collaboration opportunities with TechCorp'
Content length: 450
Content preview: 'Hi John,\n\nI came across TechCorp on ProductHunt...'
✅ Actual content email result: sent (ID: email-125)

✅ Test completed!
```

### 6. Email Generation Debug Test

Debug the email generation process step-by-step to identify AI service issues:

```bash
python debug_email_generation.py
```

**What it tests:**
- AI Service initialization and configuration
- Test prospect creation with sample data
- Email generation attempt with detailed error reporting
- OpenAI/Azure OpenAI connection and model access
- Template processing and personalization

**Expected output:**
```
🔍 DEBUGGING EMAIL GENERATION
==================================================
✅ AI Service initialized
✅ Test prospect created: Test User
🤖 Attempting email generation...
✅ Email generation successful!
Subject: Exploring opportunities at TestCorp
Body preview: Hi Test User, I came across TestCorp and was impressed by your work in software engineering...
```

### 7. Email Content Debug Test

Analyze email content for problematic characters that might cause sending issues:

```bash
python debug_email_content.py
```

**What it tests:**
- Control characters and null bytes in email content
- Unicode characters that might cause encoding issues
- JSON-breaking characters (quotes, backslashes, newlines)
- Progressive content length testing to identify size limits
- Content cleaning and validation

**Expected output:**
```
🔍 Debugging email content from database...

📧 Analyzing email content for: John Smith
Subject: 'Exploring collaboration opportunities with TechCorp'
Content length: 450

🔍 Character analysis:
- Contains null bytes: False
- Contains control chars: False
- Contains unicode: True
- Contains quotes: 4
- Contains single quotes: 2
- Contains backslashes: 0

📝 First 500 characters (repr):
'Hi John,\n\nI discovered TechCorp on ProductHunt and was impressed...'

🚨 Potential issues:
- Contains 2 '"' characters
- Contains 8 '\n' characters

🧹 Testing content cleaning:
- After control char removal: 450 chars
- After ASCII conversion: 448 chars

🧪 Testing with progressively more content:
  ✅ Length 100: SUCCESS (ID: email-123)
  ✅ Length 200: SUCCESS (ID: email-124)
  ✅ Length 500: SUCCESS (ID: email-125)
  ✅ Length 1000: SUCCESS (ID: email-126)
  ✅ Length 450: SUCCESS (ID: email-127)
```

**Prerequisites:**
- At least one prospect with generated email content in Notion
- Valid Resend API configuration
- Email content that may contain problematic characters

### 8. Notion Storage Debug Test

Debug and verify that prospects are being properly stored in Notion during parallel processing:

```bash
python debug_notion_storage.py
```

**What it tests:**
- Notion database connectivity and access
- Prospect storage during parallel processing
- Data consistency between reported and actual stored prospects
- Campaign execution with small test batch
- Storage verification and mismatch detection

**Expected output:**
```
🔍 Debugging Notion Storage During Parallel Processing
======================================================================

📊 Checking current prospects in Notion...
Initial prospect count: 45

🔄 Running test campaign with 2 companies...

📊 Checking prospects after processing...
Final prospect count: 52
New prospects added: 7

📈 Campaign Results:
  • Companies Processed: 2
  • Prospects Found (reported): 7
  • Prospects Found (actual in Notion): 7

✅ SUCCESS: All reported prospects were stored in Notion!

👥 New Prospects Added:
  1. John Smith at TechCorp ✅
  2. Sarah Johnson at InnovateLab ❌
  3. Mike Chen at DataFlow ✅
  4. Lisa Wang at CloudSync ✅
  5. David Brown at AITools ❌
======================================================================
```

**Prerequisites:**
- Valid Notion API configuration
- Existing prospect database in Notion
- Functional parallel processing setup

**Use cases:**
- Troubleshooting missing prospects after campaigns
- Verifying parallel processing data integrity
- Debugging Notion API storage issues
- Testing campaign execution with small batches

### 9. Personalization Data Quality Test

Test and verify that AI-generated personalization data is complete and not truncated:

```bash
python test_personalization_fix.py
```

**What it tests:**
- AI-structured data completeness and quality
- Personalization data length and content structure
- Product summary, business insights, and LinkedIn summary generation
- Data truncation detection and analysis
- Overall AI content generation effectiveness

**Expected output:**
```
🧪 Testing Personalization Data Generation (No Truncation)
======================================================================

🔄 Running test campaign to check personalization data...
✅ Found 1 prospects

📊 Checking personalization data for: John Smith at TechCorp

📝 AI-Generated Data Analysis:
==================================================
🎯 Personalization Data:
   Length: 847 characters
   Word count: 142 words
   Preview: Key personalization points for outreach:
   • TechCorp's AI analytics platform shows strong market traction...
   ✅ Contains 'personalization points' - good structure
   📋 Estimated points: 5
   ✅ Has 3+ personalization points - truncation fixed!

📊 Product Summary:
   Length: 523 characters
   Word count: 89 words
   ✅ Good length - not truncated

💼 Business Insights:
   Length: 312 characters
   Word count: 52 words
   ✅ Good length - not truncated

👤 LinkedIn Summary:
   Length: 298 characters
   Word count: 48 words
   ✅ Good length - not truncated

🎯 Overall Assessment:
   Total AI-generated content: 1980 characters
   ✅ EXCELLENT: Rich, detailed AI-generated content
======================================================================
```

**Prerequisites:**
- Valid AI parsing configuration (OpenAI or Azure OpenAI)
- Functional discovery pipeline
- Notion database with AI-structured data fields

**Use cases:**
- Verifying AI data generation quality after system updates
- Troubleshooting truncated personalization data
- Validating AI parsing improvements
- Quality assurance for email personalization content

### 10. Quick Personalization Check

Quickly check personalization data for the most recent prospects without running a full campaign:

```bash
python check_personalization.py
```

**What it tests:**
- Personalization data length and quality for recent prospects
- Product summary, business insights, and LinkedIn summary completeness
- Bullet point counting for personalization effectiveness
- Quick assessment of AI-generated content quality

**Expected output:**
```
🔍 Checking Personalization Data for Recent Prospects
============================================================
Total prospects in database: 45

1. John Smith at TechCorp
   ID: abc123-def456-ghi789
   📊 Data Lengths:
      Personalization: 847 chars
      Product Summary: 523 chars
      Business Insights: 312 chars
      LinkedIn Summary: 298 chars
   🎯 Personalization Data:
      Key personalization points for outreach:
      • TechCorp's AI analytics platform shows strong market traction...
      📋 Estimated points: 5
      ✅ Good: Has 5 personalization points
============================================================
```

**Prerequisites:**
- At least one prospect in the Notion database
- AI-structured data fields populated

**Use cases:**
- Quick quality check after running campaigns
- Verifying personalization data without full pipeline test
- Debugging specific prospect data issues
- Monitoring AI content generation effectiveness

### 11. Interactive Controls Test

Test the interactive campaign control system:

```bash
python test_interactive_controls.py
```

**What it tests:**
- Campaign database connectivity
- Control command detection
- Command execution
- Interactive control system functionality

**Expected output:**
```
🎮 Testing Interactive Campaign Controls...
📊 Campaigns DB ID: your-campaigns-db-id
1. Checking for active campaigns...
   Found 1 active campaigns
   Testing controls for: Discovery Campaign 2024-01-31 14:30
2. Testing control command detection...
   Check 1/5...
   🎮 Found 1 control commands:
      - Action: pause
      - Parameters: {'reason': 'User requested via Notion'}
      - Requested by: Notion User
      - Executing command...
      - Result: ✅ Success

📋 Instructions for manual testing:
1. Go to your Notion 'Campaign Runs' database
2. Find the active campaign
3. Try these actions:
   • Change Status to 'Paused' to pause the campaign
   • Change Status to 'Failed' to stop the campaign
   • Change 'Current Company' to 'PRIORITY: TestCompany' to add priority
4. Run this script again to see if commands are detected

🔗 Direct link to campaigns database:
https://notion.so/[campaigns-db-id]
```

**Prerequisites:**
- Dashboard must be set up (`python setup_dashboard.py`)
- At least one active campaign in the database
- Campaigns database ID configured in config

### 12. Company Deduplication Test

Test and verify that the company deduplication functionality is working correctly to prevent processing the same companies multiple times:

```bash
python test_company_deduplication.py
```

### 13. Notion Database Updates Test

Test that Notion database updates work correctly and verify email status tracking:

```bash
python test_notion_updates.py
```

**What it tests:**
- Notion manager initialization and connectivity
- Email generation statistics retrieval from database
- Email generation and sent count calculation accuracy
- Prospect status breakdown by email generation status
- Database update functionality

**Expected output:**
```
🧪 TESTING NOTION DATABASE UPDATES
==================================================
✅ Notion manager initialized

📊 TESTING EMAIL GENERATION STATS
Email generation stats: {'total_generated': 5, 'total_sent': 0, 'prospects_with_emails': 3}
Emails generated: 5
Emails sent: 0
✅ Correct - no emails actually sent

👥 TESTING PROSPECT STATUS
Total prospects: 15
Email generation status breakdown:
  Generated: 5
  Not Generated: 8
  Sent: 0
  Failed: 2

🎯 FIXES APPLIED:
1. ✅ Fixed email sent count calculation
2. ✅ Added explicit email generation status updates
3. ✅ Improved daily stats accuracy
```

**Prerequisites:**
- Valid Notion API configuration
- Existing prospect database with email data
- Functional notion manager setup

**Use cases:**
- Verifying email status tracking after system updates
- Testing database update functionality
- Debugging email statistics calculation issues
- Validating Notion database connectivity

### 14. AI Provider Interface Test

Test the BaseAIProvider interface to verify multi-model AI provider support functionality:

```bash
# Run from project root directory
python test_base_provider.py
```

**What it tests:**
- BaseAIProvider interface implementation and functionality
- Mock provider creation and configuration
- Completion request/response handling
- Provider configuration validation
- Model information retrieval
- Connection testing capabilities

**Expected output:**
```
🧪 Testing BaseAIProvider interface...
✅ Provider name: MockAIProvider
✅ Safe config: {'api_key': '***', 'model': 'mock-model-v1'}
✅ Completion response: Hello! This is a mock response.
✅ Config validation: SUCCESS - Mock provider configuration is valid
✅ Model info: {'models': ['mock-model-v1', 'mock-model-v2'], 'capabilities': ['text-generation', 'chat'], 'max_tokens': 4096}
✅ Connection test: SUCCESS - Connection test successful

🎉 All tests passed! BaseAIProvider interface is working correctly.
```

**Prerequisites:**
- BaseAIProvider interface implementation in `services/providers/base_provider.py`
- Multi-model AI provider support system

**Use cases:**
- Verifying provider interface implementation during development
- Testing provider abstraction layer functionality
- Validating new provider implementations
- Debugging provider configuration issues
- Testing provider switching capabilities

### 15. Notion Schema Verification Test

Verify Notion database schema and field mappings to identify issues with email generation status fields:

```bash
python verify_notion_schema.py
```

**What it tests:**
- Notion database connectivity and schema retrieval
- Email-related field presence and configuration
- Field type validation and select options
- Sample prospect data extraction and analysis
- Field extraction method testing with sample data

**Expected output:**
```
🔍 NOTION DATABASE SCHEMA VERIFICATION
============================================================

✅ Notion manager initialized
Prospects Database ID: abc123-def456-ghi789

Database Title: Job Prospects

Total Properties: 25

📧 EMAIL-RELATED FIELDS FOUND:
  • Email Generation Status
    Type: select
    ID: field-id-123
    Options: ['Not Generated', 'Generated', 'Sent', 'Failed']

  • Email Delivery Status
    Type: select
    ID: field-id-124
    Options: ['Not Sent', 'Sent', 'Delivered', 'Failed']

🎯 CHECKING EXPECTED EMAIL FIELDS:
  ✅ Email Generation Status (select)
     Options: ['Not Generated', 'Generated', 'Sent', 'Failed']
  ✅ Email Delivery Status (select)
  ✅ Email Subject (title)
  ✅ Email Content (rich_text)
  ✅ Email Generated Date (date)

🧪 TESTING PROSPECT DATA EXTRACTION
Sample prospect: John Smith
Email-related attributes:
  email_generation_status: Generated
  email_delivery_status: Not Sent
  email_subject: Exploring opportunities at TechCorp
  email_content: Hi John, I came across TechCorp...

🎯 SCHEMA VERIFICATION SUMMARY:
1. ✅ Database connection working
2. ✅ Can retrieve database schema
3. ✅ Can read prospect data
4. ✅ All expected email fields present
```

**Prerequisites:**
- Valid Notion API configuration
- Existing prospect database in Notion
- Database with email-related fields configured

**Use cases:**
- Diagnosing email generation status field issues
- Verifying database schema after updates
- Troubleshooting field mapping problems
- Validating field extraction methods
- Debugging prospect data retrieval issues

**What it tests:**
- Retrieval of processed companies and domains from Notion
- Individual company processing status checks
- Cache functionality and performance improvements
- Company filtering with mock data (existing vs new companies)
- Performance comparison between cached and uncached operations

**Expected output:**
```
🚀 Starting company deduplication tests...
🧪 Testing company deduplication functionality...

📋 Test 1: Getting processed companies...
Found 45 processed companies:
  1. TechCorp
  2. InnovateLab
  3. DataFlow
  ... and 42 more

Found 45 processed domains:
  1. techcorp.com
  2. innovatelab.io
  3. dataflow.ai
  ... and 42 more

🔍 Test 2: Testing individual company checks...
Company 'TechCorp' is processed: True
Fake company 'Test Company 20240131143052' is processed: False

💾 Test 3: Testing cache functionality...
First cache call took 0.245 seconds
Second cache call took 0.003 seconds
Cache working: True
Performance improvement: 81.7x faster

🔄 Test 4: Testing company filtering...
Created 6 mock companies for testing
Filtering took 0.008 seconds
Original companies: 6
Unprocessed companies: 3
Filtered out: 3

Filtered out companies:
  - TechCorp
  - InnovateLab
  - DataFlow

Companies that passed filtering:
  + New Company 0 20240131143052
  + New Company 1 20240131143052
  + New Company 2 20240131143052

⚡ Test 5: Performance comparison...
First run (fresh cache): 0.251 seconds
Second run (cached): 0.004 seconds
Cache performance improvement: 62.8x faster

✅ All deduplication tests completed successfully!
🎉 All tests passed! Company deduplication is working correctly.
```

**Prerequisites:**
- Valid Notion API configuration
- Existing prospect database with processed companies
- Functional controller and notion manager setup

**Use cases:**
- Verifying deduplication logic after system updates
- Testing cache performance improvements
- Debugging duplicate company processing issues
- Validating filtering efficiency for large datasets
- Performance testing for company lookup operations

## ⚙️ Configuration Testing

### CLI Configuration Validation

```bash
# Validate all configuration settings
python cli.py validate-config

# Check specific sender profile
python cli.py validate-config --check-profile profiles/my_profile.md
```

**Expected output:**
```
✅ Configuration validation passed
✅ Sender profile validation passed
Profile completeness: 85.0%

API Connection Tests:
   Notion: ✅ Connected successfully
   Hunter.io: ✅ API key valid (23/25 requests remaining)
   OpenAI: ✅ API key valid
   Resend: ✅ Domain verified
```

### Manual Configuration Check

```python
#!/usr/bin/env python3
"""Manual configuration validation."""

from utils.config import Config

def test_config():
    try:
        config = Config.from_file("config.yaml")
        config.validate()
        print("✅ Configuration is valid")
        
        # Check required fields
        required_fields = [
            'notion_token', 'hunter_api_key', 'openai_api_key'
        ]
        
        for field in required_fields:
            value = getattr(config, field, None)
            if value:
                print(f"✅ {field}: configured")
            else:
                print(f"❌ {field}: missing")
                
    except Exception as e:
        print(f"❌ Configuration error: {e}")

if __name__ == "__main__":
    test_config()
```

## 🔄 Pipeline Testing

### Discovery Pipeline Test

```bash
# Test discovery with dry-run
python cli.py --dry-run discover --limit 3

# Test discovery with actual API calls
python cli.py discover --limit 3
```

### Individual Component Testing

**Test WebDriver Manager:**
```bash
python -c "
from utils.webdriver_manager import get_webdriver_manager
from utils.config import Config

config = Config.from_env()
manager = get_webdriver_manager(config)

print('Testing WebDriver manager...')
print(f'Pool stats: {manager.get_pool_stats()}')

# Test driver creation and usage
with manager.get_driver('test') as driver:
    driver.get('https://www.google.com')
    print(f'Successfully loaded: {driver.title}')
    
print('WebDriver manager test completed successfully')
"
```

**Test ProductHunt Scraping:**
```bash
python -c "
from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config

config = Config.from_file('config.yaml')
scraper = ProductHuntScraper(config)
products = scraper.get_latest_products(limit=2)
print(f'Found {len(products)} products')
for product in products:
    print(f'- {product.name}: {product.url}')
"
```

**Test Email Finding:**
```bash
python test_email_finder.py
```

**Test AI Parsing:**
```bash
python test_json_extraction.py
```

**Test Team Extraction:**
```bash
python test_team_extraction.py
```

### Company Processing Test

```bash
# Test processing specific company
python cli.py process-company "OpenAI" --domain openai.com

# Test with dry-run
python cli.py --dry-run process-company "OpenAI" --domain openai.com
```

## 📧 Email Testing

### Email Generation Testing

```bash
# Generate emails for existing prospects
python cli.py generate-emails --prospect-ids "id1,id2,id3"

# Test with different templates
python cli.py generate-emails --prospect-ids "id1" --template referral

# Test with sender profile
python cli.py generate-emails --prospect-ids "id1" --sender-profile profiles/my_profile.md
```

### Email Sending Testing

```bash
# Generate and send test email
python cli.py generate-emails --prospect-ids "id1" --send

# Test email delivery
python test_email_debug.py
```

### Sender Profile Testing

```bash
# Create new sender profile
python cli.py profile-setup --interactive

# Validate existing profile
python cli.py validate-config --check-profile profiles/my_profile.md

# Test profile completeness
python -c "
from services.sender_profile_manager import SenderProfileManager

manager = SenderProfileManager()
profile = manager.load_profile_from_markdown('profiles/my_profile.md')
score = profile.get_completeness_score()
print(f'Profile completeness: {score:.1%}')
"
```

## 🚀 Performance Testing

### Load Testing

```bash
# Test with larger batch sizes
python cli.py discover --limit 20 --batch-size 10

# Test processing time
python -c "
import time
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

config = Config.from_file('config.yaml')
controller = ProspectAutomationController(config)

start_time = time.time()
results = controller.run_discovery_pipeline(limit=5)
end_time = time.time()

print(f'Processing time: {end_time - start_time:.1f} seconds')
print(f'Companies processed: {results[\"summary\"][\"companies_processed\"]}')
print(f'Time per company: {(end_time - start_time) / max(1, results[\"summary\"][\"companies_processed\"]):.1f} seconds')
"
```

### Memory Usage Testing

```bash
# Monitor memory usage during processing
python -c "
import psutil
import os
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

process = psutil.Process(os.getpid())
initial_memory = process.memory_info().rss / 1024 / 1024  # MB

config = Config.from_file('config.yaml')
controller = ProspectAutomationController(config)
results = controller.run_discovery_pipeline(limit=3)

final_memory = process.memory_info().rss / 1024 / 1024  # MB
print(f'Memory usage: {initial_memory:.1f} MB -> {final_memory:.1f} MB')
print(f'Memory increase: {final_memory - initial_memory:.1f} MB')
"
```

## 🔧 Troubleshooting Tests

### API Connection Testing

```bash
# Test individual API connections
python -c "
from utils.config import Config
import requests

config = Config.from_file('config.yaml')

# Test Notion
try:
    headers = {'Authorization': f'Bearer {config.notion_token}'}
    response = requests.get('https://api.notion.com/v1/users/me', headers=headers)
    print(f'Notion API: {\"✅ Connected\" if response.status_code == 200 else \"❌ Failed\"}')
except Exception as e:
    print(f'Notion API: ❌ Error - {e}')

# Test Hunter.io
try:
    response = requests.get(f'https://api.hunter.io/v2/account?api_key={config.hunter_api_key}')
    if response.status_code == 200:
        data = response.json()
        print(f'Hunter.io API: ✅ Connected ({data[\"data\"][\"requests\"][\"used\"]}/{data[\"data\"][\"requests\"][\"available\"]} requests used)')
    else:
        print(f'Hunter.io API: ❌ Failed')
except Exception as e:
    print(f'Hunter.io API: ❌ Error - {e}')
"
```

### Error Simulation Testing

```bash
# Test with invalid API keys
python -c "
import os
os.environ['HUNTER_API_KEY'] = 'invalid_key'
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

try:
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    results = controller.run_discovery_pipeline(limit=1)
    print('System handled invalid API key gracefully')
except Exception as e:
    print(f'Error handling test: {e}')
"
```

### Rate Limit Testing

```bash
# Test rate limiting behavior
python -c "
from utils.config import Config
config = Config.from_file('config.yaml')
config.hunter_requests_per_minute = 1  # Very low limit
config.scraping_delay = 0.1  # Very fast scraping

from controllers.prospect_automation_controller import ProspectAutomationController
controller = ProspectAutomationController(config)

try:
    results = controller.run_discovery_pipeline(limit=3)
    print('Rate limiting handled correctly')
except Exception as e:
    print(f'Rate limiting test: {e}')
"
```

## 📊 Test Results Interpretation

### Success Indicators

**Full Pipeline Test:**
- All services initialized: ✅
- Companies processed > 0
- Success rate > 80%
- No critical errors

**Email Pipeline Test:**
- Email generation successful
- Personalization score > 0.7
- No template errors

**Configuration Test:**
- All API keys valid
- Profile completeness > 70%
- No validation errors

### Common Issues and Solutions

**Issue: "No prospects found"**
- Check ProductHunt scraping is working
- Verify team extraction is functioning
- Ensure Notion database is accessible

**Issue: "Email generation failed"**
- Check OpenAI API key and quota
- Verify sender profile is complete
- Check prospect data quality

**Issue: "API rate limit exceeded"**
- Increase delays in configuration
- Reduce batch sizes
- Check API quotas

**Issue: "Configuration validation failed"**
- Verify all required API keys are set
- Check file permissions on .env
- Validate API key formats

## 🎯 Best Practices for Testing

### 1. Start Small
```bash
# Always start with small limits
python cli.py --dry-run discover --limit 1
python test_full_pipeline.py  # Uses limit=3 by default
```

### 2. Use Dry-Run Mode
```bash
# Test configuration without API calls
python cli.py --dry-run --verbose discover --limit 5
```

### 3. Test Incrementally
```bash
# Test each component individually
python test_email_finder.py
python test_team_extraction.py
python test_email_pipeline.py
```

### 4. Monitor Resources
```bash
# Check API quotas regularly
python cli.py status
```

### 5. Validate Before Production
```bash
# Always validate configuration
python cli.py validate-config
python test_full_pipeline.py
```

## 🆘 Getting Help

If tests fail:

1. **Check logs**: Look in `logs/` directory for detailed error information
2. **Use verbose mode**: Add `--verbose` flag to CLI commands
3. **Test individual components**: Isolate the failing component
4. **Check API quotas**: Ensure you haven't exceeded limits
5. **Verify configuration**: Run `python cli.py validate-config`

For additional support, refer to the [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) or check the system logs for detailed error information.