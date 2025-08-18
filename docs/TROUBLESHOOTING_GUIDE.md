# Troubleshooting Guide

This comprehensive guide helps you diagnose and resolve common issues with the Job Prospect Automation system.

## 🚨 Quick Diagnostic Commands

Before diving into specific issues, run these commands to get system status:

```bash
# 1. Apply performance optimizations (recommended first)
python fix_all_performance_issues.py

# 2. Validate configuration and test all API connections
python cli.py validate-config

# 3. Test basic configuration
python cli.py --dry-run status

# 4. Verbose system check
python cli.py --verbose --dry-run discover --limit 1

# 5. Check API health
python examples/error_handling_example.py

# 6. View recent logs
tail -f logs/prospect_automation_$(date +%Y%m%d).log
```

## ⚡ Performance Issues

### Issue: "Pipeline is running too slowly"

**Symptoms:**
- LinkedIn finding takes 6-7 minutes per profile
- Overall pipeline takes 15-20 minutes
- WebDriver operations are slow
- HTTP requests timeout frequently

**Quick Fix:**
```bash
# Apply comprehensive performance optimizations
python fix_all_performance_issues.py
```

**Expected Improvements:**
- LinkedIn finding: 6-7 minutes → 10-30 seconds (20x faster)
- Overall pipeline: 15-20 minutes → 3-5 minutes (4-6x faster)
- WebDriver operations: 2-3x faster page loads
- HTTP requests: 3-5x faster response times

**Manual Performance Tuning:**
```bash
# Check current performance
python performance_benchmark.py

# Test LinkedIn finder speed
python -c "from fix_all_performance_issues import test_performance_improvements; test_performance_improvements()"

# Monitor cache performance
python -c "from services.caching_service import CachingService; from utils.config import Config; cs = CachingService(Config.from_env()); print(cs.get_stats())"
```

### Issue: "LinkedIn profile finding is extremely slow"

**Diagnosis:**
```bash
# Check if using optimized LinkedIn finder
python -c "from services.linkedin_finder_optimized import LinkedInFinderOptimized; print('Optimized finder available')"

# Test LinkedIn finder performance
python test_linkedin_performance.py
```

**Solutions:**
1. **Use the performance fix script:**
   ```bash
   python fix_all_performance_issues.py
   ```

2. **Manual optimization in .env:**
   ```env
   LINKEDIN_FINDER_DELAY=0.5
   LINKEDIN_SEARCH_TIMEOUT=3
   LINKEDIN_URL_CHECK_TIMEOUT=2
   LINKEDIN_CACHE_FAILED_SEARCHES=true
   ```

### Issue: "WebDriver operations are slow or timing out"

**Solutions:**
1. **Apply WebDriver optimizations:**
   ```bash
   python fix_all_performance_issues.py
   ```

2. **Manual WebDriver tuning:**
   ```env
   WEBDRIVER_PAGE_LOAD_TIMEOUT=8
   WEBDRIVER_IMPLICIT_WAIT=3
   WEBDRIVER_DISABLE_IMAGES=true
   ```

## 🔧 Configuration Issues

### Issue: "Environment variable is required"

**Error Messages:**
```
Error: NOTION_TOKEN environment variable is required
Error: HUNTER_API_KEY environment variable is required
Error: OPENAI_API_KEY environment variable is required
```

**Diagnosis:**
```bash
# Check if .env file exists
ls -la .env

# Check environment variables
python -c "import os; print('NOTION_TOKEN' in os.environ)"

# Use new configuration service for validation
python -c "from utils.configuration_service import ConfigurationService; ConfigurationService().validate_config()"
```

**Solutions:**

1. **Create .env file:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Check file format:**
   ```bash
   # Correct format (no spaces around =)
   NOTION_TOKEN=secret_your_token_here
   HUNTER_API_KEY=your_key_here
   OPENAI_API_KEY=sk-your_key_here
   
   # Incorrect format
   NOTION_TOKEN = secret_your_token_here  # ❌ Extra spaces
   NOTION_TOKEN="secret_your_token_here"  # ❌ Quotes not needed
   ```

3. **Verify file permissions:**
   ```bash
   chmod 644 .env  # Make readable
   ```

4. **Use centralized configuration service:**
   ```bash
   # Validate configuration with enhanced service
   python -c "
   from utils.configuration_service import ConfigurationService
   config_service = ConfigurationService()
   try:
       config = config_service.get_config()
       print('✅ Configuration valid')
   except Exception as e:
       print(f'❌ Configuration error: {e}')
   "
   ```

5. **Use configuration file instead:**
   ```bash
   python cli.py init-config config.yaml
   # Edit config.yaml with your keys
   python cli.py --config config.yaml discover
   ```

### Issue: "Invalid configuration values"

**Error Messages:**
```
Error: Scraping delay must be non-negative
Error: Hunter requests per minute must be positive
Error: Max products per run must be positive
```

**Solutions:**

1. **Check numeric values:**
   ```env
   SCRAPING_DELAY=2.0          # ✅ Valid
   SCRAPING_DELAY=-1.0         # ❌ Invalid (negative)
   SCRAPING_DELAY=abc          # ❌ Invalid (not a number)
   ```

2. **Reset to defaults:**
   ```bash
   python cli.py init-config --reset
   ```

3. **Validate configuration with enhanced service:**
   ```python
   from utils.configuration_service import ConfigurationService
   from utils.validation_framework import ValidationFramework
   
   config_service = ConfigurationService()
   validator = ValidationFramework()
   
   # Comprehensive configuration validation
   config = config_service.get_config()
   validation_result = validator.validate_configuration(config)
   
   if not validation_result.is_valid:
       print("Configuration errors:")
       for error in validation_result.errors:
           print(f"  - {error}")
   ```

4. **Use centralized configuration management:**
   ```python
   from utils.configuration_service import ConfigurationService
   
   # Get validated configuration
   config_service = ConfigurationService()
   config = config_service.get_config()
   
   # Access specific configuration sections
   openai_config = config_service.get_openai_config()
   notion_config = config_service.get_notion_config()
   ```

## 🔄 Refactored Architecture Issues

### Issue: "Direct config parameter is deprecated"

**Warning Message:**
```
WARNING - Direct config parameter is deprecated. Consider using ConfigurationService.
```

**Cause:** Using legacy configuration patterns with refactored services.

**Solutions:**

1. **Update service initialization:**
   ```python
   # ❌ Old pattern
   from services.some_service import SomeService
   service = SomeService(config)
   
   # ✅ New pattern
   from utils.configuration_service import ConfigurationService
   config_service = ConfigurationService()
   service = SomeService(config_service.get_config())
   ```

2. **Use centralized configuration:**
   ```python
   from utils.configuration_service import ConfigurationService
   
   config_service = ConfigurationService()
   
   # Get validated configuration
   config = config_service.get_config()
   
   # Access specific configurations
   ai_config = config_service.get_ai_config()
   cache_config = config_service.get_cache_config()
   ```

### Issue: AI Service Import Errors

**Error Messages:**
```
ImportError: cannot import name 'AIParser' from 'services.ai_parser'
ImportError: cannot import name 'EmailGenerator' from 'services.email_generator'
```

**Cause:** Attempting to import legacy AI services that have been consolidated.

**Solutions:**

1. **Update to unified AI service:**
   ```python
   # ❌ Old imports
   from services.ai_parser import AIParser
   from services.email_generator import EmailGenerator
   from services.product_analyzer import ProductAnalyzer
   
   # ✅ New unified import
   from services.ai_service import AIService, EmailTemplate
   
   # Initialize unified service
   ai_service = AIService(config)
   
   # Use unified methods
   profile_result = ai_service.parse_linkedin_profile(html)
   email_result = ai_service.generate_email(
       prospect=prospect,
       template_type=EmailTemplate.COLD_OUTREACH
   )
   ```

2. **Update method calls:**
   ```python
   # ❌ Old pattern
   ai_parser = AIParser(config)
   email_generator = EmailGenerator(config)
   
   profile = ai_parser.parse_linkedin_profile(html)
   email = email_generator.generate_email(prospect)
   
   # ✅ New pattern
   ai_service = AIService(config)
   
   profile = ai_service.parse_linkedin_profile(html)
   email = ai_service.generate_email(
       prospect=prospect,
       template_type=EmailTemplate.COLD_OUTREACH
   )
   ```

### Issue: Caching Performance Problems

**Symptoms:**
- High memory usage
- Slow response times
- Cache misses

**Diagnosis:**
```python
from services.caching_service import CachingService

cache_service = CachingService(config)
stats = cache_service.get_stats()

print(f"Memory usage: {stats.memory_usage_mb:.1f} MB")
print(f"Hit rate: {stats.hit_rate:.2%}")
print(f"Total entries: {stats.total_entries}")
```

**Solutions:**

1. **Configure cache limits:**
   ```python
   from services.caching_service import CachingService
   
   cache_service = CachingService(config)
   
   # Set memory limits
   cache_service.configure_limits(
       max_memory_mb=100,
       max_entries=1000
   )
   ```

2. **Clear cache if needed:**
   ```python
   # Clear all cache
   cache_service.clear_all()
   
   # Clear specific patterns
   cache_service.invalidate_pattern("linkedin_profile_*")
   
   # Clean up expired entries
   cache_service.cleanup_expired()
   ```

3. **Optimize cache usage:**
   ```python
   # Use appropriate TTL values
   cache_service.set("key", value, ttl=3600)  # 1 hour
   
   # Use cache warming for frequently accessed data
   warming_config = {
       "common_profiles": {
           "factory": lambda: load_common_profiles(),
           "ttl": 7200,
           "priority": 10
       }
   }
   cache_service.warm_cache(warming_config)
   ```

### Issue: Validation Framework Errors

**Error Messages:**
```
ValidationError: Email format is invalid
ValidationError: URL format is invalid
ValidationError: Required field is missing
```

**Cause:** New validation framework has stricter requirements.

**Solutions:**

1. **Check validation requirements:**
   ```python
   from utils.validation_framework import ValidationFramework
   
   validator = ValidationFramework()
   
   # Validate individual fields
   email_result = validator.validate_email("test@example.com")
   if not email_result.is_valid:
       print(f"Email validation errors: {email_result.errors}")
   
   # Validate complex data structures
   prospect_result = validator.validate_prospect_data(prospect_data)
   if not prospect_result.is_valid:
       print(f"Prospect validation errors: {prospect_result.errors}")
   ```

2. **Update data structures:**
   ```python
   # Ensure required fields are present
   prospect_data = {
       "name": "John Doe",  # Required
       "email": "john@example.com",  # Must be valid email format
       "company": "Example Corp",  # Required
       "role": "CEO",  # Required
       "linkedin_url": "https://linkedin.com/in/johndoe"  # Must be valid URL
   }
   
   # Validate before processing
   validation_result = validator.validate_prospect_data(prospect_data)
   if validation_result.is_valid:
       # Process data
       pass
   else:
       # Handle validation errors
       for error in validation_result.errors:
           print(f"Validation error: {error}")
   ```

### Issue: Enhanced Error Handling Integration

**Problem:** Existing error handling patterns not working with new enhanced error handling service.

**Solutions:**

1. **Update error handling patterns:**
   ```python
   from utils.error_handling_enhanced import EnhancedErrorHandler
   
   error_handler = EnhancedErrorHandler(config)
   
   # ❌ Old pattern
   try:
       result = risky_operation()
   except Exception as e:
       logger.error(f"Operation failed: {e}")
   
   # ✅ New pattern
   result = error_handler.execute_with_handling(
       risky_operation,
       context="operation_name",
       max_retries=3
   )
   ```

2. **Use centralized error categorization:**
   ```python
   try:
       result = some_operation()
   except Exception as e:
       # Enhanced error handling with categorization
       error_info = error_handler.handle_error(e, context="operation_name")
       
       if error_info.is_recoverable:
           # Retry logic
           result = error_handler.retry_operation(some_operation)
       else:
           # Log and escalate
           logger.error(f"Unrecoverable error: {error_info.message}")
   ```
   config = Config.from_env()
   config.validate()  # Will show specific validation errors
   ```

## 🌐 Network and API Issues

### Issue: "Failed to connect to API"

**Error Messages:**
```
Error: Failed to connect to Notion API
Error: Hunter.io API connection failed
Error: OpenAI API request failed
```

**Diagnosis:**
```bash
# Test all API connections automatically
python cli.py validate-config

# Test internet connectivity
ping google.com

# Test specific API endpoints manually
curl -I https://api.notion.com/v1/users/me
curl -I https://api.hunter.io/v2/account
curl -I https://api.openai.com/v1/models
```

**Solutions:**

1. **Check internet connection:**
   - Verify stable internet connection
   - Try accessing APIs from browser
   - Check if behind corporate firewall

2. **Verify API endpoints:**
   ```bash
   # Test with verbose mode
   python cli.py --verbose --dry-run status
   ```

3. **Check proxy settings:**
   ```bash
   # If behind corporate proxy
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

4. **Retry with backoff:**
   ```bash
   # System has automatic retry - wait and try again
   python cli.py discover --limit 1
   ```

### Issue: "API Authentication Failed"

**Error Messages:**
```
Error: Notion API returned 401 Unauthorized
Error: Hunter.io API key is invalid
Error: OpenAI API authentication failed
```

**Diagnosis:**
```bash
# Test each API key individually
python -c "
from services.notion_manager import NotionDataManager
from utils.config import Config
config = Config.from_env()
try:
    notion = NotionDataManager(config)
    print('✅ Notion API key valid')
except Exception as e:
    print(f'❌ Notion API key invalid: {e}')
"
```

**Solutions:**

1. **Verify API keys:**
   - Notion token should start with `secret_`
   - OpenAI key should start with `sk-`
   - Hunter.io key format varies

2. **Check key permissions:**
   - Notion: Ensure integration has proper workspace access
   - OpenAI: Verify billing is set up
   - Hunter.io: Check account is activated

3. **Regenerate keys:**
   - Create new API keys in respective dashboards
   - Update configuration with new keys
   - Test with new keys

### Issue: "Rate limit exceeded"

**Error Messages:**
```
Error: Hunter.io rate limit exceeded (10 requests per minute)
Error: OpenAI rate limit exceeded
Error: Too many requests to ProductHunt
```

**Diagnosis:**
```bash
# Check current rate limit settings
python -c "
from utils.config import Config
config = Config.from_env()
print(f'Scraping delay: {config.scraping_delay}s')
print(f'Hunter requests/min: {config.hunter_requests_per_minute}')
"
```

**Solutions:**

1. **Increase delays:**
   ```env
   SCRAPING_DELAY=5.0                    # Increase from 2.0
   HUNTER_REQUESTS_PER_MINUTE=5          # Decrease from 10
   linkedin_scraping_delay=10.0          # Increase LinkedIn delay
   ```

2. **Use smaller batch sizes:**
   ```bash
   python cli.py discover --limit 10 --batch-size 2
   ```

3. **Wait and retry:**
   ```bash
   # Rate limits typically reset after 1 minute
   sleep 60
   python cli.py discover
   ```

4. **Monitor API usage:**
   ```bash
   python examples/error_handling_example.py
   ```

## 💾 Data and Storage Issues

### Issue: "Cannot access Notion database"

**Error Messages:**
```
Error: Notion database not found
Error: Insufficient permissions for Notion database
Error: Failed to create Notion database
```

**Diagnosis:**
```bash
# Test Notion connection
python -c "
from services.notion_manager import NotionDataManager
from utils.config import Config
config = Config.from_env()
notion = NotionDataManager(config)
print('Notion connection successful')
"

# Debug raw Notion field data extraction
python debug_notion_fields.py

# This debug script will show:
# - Raw Notion field data for email-related fields
# - Field extraction method testing
# - Email Generation Status, Email Delivery Status, Email Subject, Email Content fields
# - Comparison between raw data and extracted values

# Verify Notion database schema and field mappings
python verify_notion_schema.py

# This comprehensive schema verification will show:
# - Database connectivity and access permissions
# - Complete field mapping analysis
# - Email-related field configuration
# - Sample data extraction testing
# - Field type validation and options
```

**Solutions:**

1. **Let system create database:**
   ```env
   # Remove or comment out this line to let system create new database
   # NOTION_DATABASE_ID=your_database_id
   ```

2. **Check integration permissions:**
   - Ensure Notion integration has workspace access
   - Integration should have "Insert content", "Update content", and "Read content" permissions
   - Verify integration is added to the workspace

3. **Verify database ID:**
   ```bash
   # Get database ID from URL
   # https://notion.so/workspace/DATABASE_ID?v=...
   # Use only the DATABASE_ID part
   ```

4. **Create database manually:**
   - Create new database in Notion
   - Add required properties (Name, Role, Company, etc.)
   - Share with integration
   - Add database ID to configuration

### Issue: "Dashboard creation failed"

**Error Messages:**
```
Error: Failed to create campaign dashboard
Error: Dashboard Not Created
Error: Cannot create dashboard page
```

**Diagnosis:**
```bash
# Test dashboard creation
python setup_dashboard.py

# Isolate the specific issue with step-by-step testing
python test_dashboard_creation.py
```

**Solutions:**

1. **Check workspace permissions:**
   - Ensure Notion integration has workspace-level access
   - Integration needs permission to create pages and databases
   - Verify integration is properly connected to workspace

2. **Verify integration setup:**
   - Go to Notion → Settings & Members → Integrations
   - Find your integration and ensure it's connected
   - Check that integration has necessary capabilities

3. **Manual dashboard setup:**
   - Create a new page in Notion manually
   - Run setup script to create databases within that page
   - Update configuration with generated database IDs

4. **Check API token:**
   - Ensure NOTION_TOKEN is valid and current
   - Token should start with "secret_"
   - Regenerate token if needed

### Issue: "Data validation errors"

**Error Messages:**
```
Error: Invalid email format
Error: Required field missing
Error: Data type mismatch
```

**Solutions:**

1. **Check data models:**
   ```python
   from models.data_models import Prospect
   # Ensure all required fields are provided
   ```

2. **Validate input data:**
   ```bash
   # Use dry-run to test data validation
   python cli.py --dry-run process-company "Test Company"
   ```

3. **Review logs for details:**
   ```bash
   grep -i "validation" logs/prospect_automation_*.log
   ```

## 🕷️ Scraping Issues

### Issue: "ProductHunt scraping failed"

**Error Messages:**
```
Error: Failed to scrape ProductHunt
Error: No products found on ProductHunt
Error: ProductHunt blocked request
Error: Only 1 company discovered (expected more)
```

**Diagnosis:**
```bash
# Debug the discovery process to understand filtering issues
python debug_discovery.py

# This comprehensive debug script will show:
# - Number of processed companies and domains in Notion
# - Recent processed companies for reference
# - Companies found from ProductHunt scraping
# - Which companies would be filtered out and why (by name or domain)
# - Unprocessed companies after filtering
# - Clear diagnosis of why no unprocessed companies are found

# Debug team extraction and LinkedIn URL discovery
python debug_team_extraction.py

# This debug script will show:
# - Raw team member extraction results from ProductHunt
# - LinkedIn URLs found directly in ProductHunt team sections
# - Analysis of LinkedIn URL extraction success rate
# - Raw content that would be passed to AI for processing

# Test ProductHunt accessibility
curl -I https://www.producthunt.com/

# Check scraping configuration
python -c "
from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config
config = Config.from_env()
scraper = ProductHuntScraper(config)
print('ProductHunt scraper initialized')
"
```

**Solutions:**

1. **Clear processed companies cache if too aggressive:**
   ```python
   # Clear the cache to force refresh
   from controllers.prospect_automation_controller import ProspectAutomationController
   from utils.config import Config
   
   config = Config.from_env()
   controller = ProspectAutomationController(config)
   controller._clear_processed_companies_cache()
   print("✅ Cleared processed companies cache")
   ```

2. **Increase scraping delays:**
   ```env
   SCRAPING_DELAY=5.0  # Increase from 2.0
   ```

3. **Check ProductHunt status:**
   - Visit ProductHunt manually
   - Check if site is accessible
   - Verify no maintenance mode

4. **Use different scraping approach:**
   ```bash
   # Try with different settings
   python cli.py discover --limit 5 --batch-size 1
   ```

5. **Consider clearing old data if you have many processed companies:**
   - If you have 50+ processed companies, the system might be too aggressive in filtering
   - Consider clearing old data or adjusting the filtering logic
   - The debug script will show you exactly how many companies are being filtered out

### Issue: "LinkedIn scraping blocked"

**Error Messages:**
```
Error: LinkedIn blocked request
Error: LinkedIn profile not accessible
Error: Too many LinkedIn requests
```

**Solutions:**

1. **Increase LinkedIn delays:**
   ```env
   linkedin_scraping_delay=10.0  # Increase significantly
   ```

2. **Reduce LinkedIn requests:**
   ```env
   MAX_PROSPECTS_PER_COMPANY=5   # Reduce from 10
   ```

3. **Use LinkedIn alternatives:**
   - Focus on email discovery instead
   - Use publicly available information only

4. **Implement rotation:**
   - Consider using multiple IP addresses
   - Implement request rotation

### Issue: "WebDriver initialization failed"

**Error Messages:**
```
Error: Failed to create WebDriver
Error: Chrome driver not found
Error: WebDriver pool exhausted
Error: Browser startup failed
```

**Diagnosis:**
```bash
# Test WebDriver manager
python -c "
from utils.webdriver_manager import get_webdriver_manager
from utils.config import Config

config = Config.from_env()
manager = get_webdriver_manager(config)
print('WebDriver manager initialized successfully')

# Test driver creation
with manager.get_driver('test') as driver:
    print('WebDriver created successfully')
    print(f'Driver session: {driver.session_id}')
"
```

**Solutions:**

1. **Check Chrome installation:**
   ```bash
   # Verify Chrome is installed
   google-chrome --version  # Linux
   # or
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version  # macOS
   ```

2. **Update WebDriver configuration:**
   ```env
   WEBDRIVER_HEADLESS=true                # Ensure headless mode
   WEBDRIVER_POOL_SIZE=2                  # Reduce pool size
   WEBDRIVER_PAGE_LOAD_TIMEOUT=30         # Increase timeout
   ```

3. **Check system resources:**
   ```bash
   # Monitor memory usage
   free -h  # Linux
   # or
   vm_stat  # macOS
   ```

4. **Disable resource-intensive options:**
   ```env
   WEBDRIVER_DISABLE_IMAGES=true          # Disable images
   WEBDRIVER_DISABLE_JAVASCRIPT=true      # Disable JS if not needed
   ```

### Issue: "WebDriver pool exhausted"

**Error Messages:**
```
Error: No available WebDriver instances
Error: WebDriver pool timeout
Error: Maximum pool size reached
```

**Solutions:**

1. **Increase pool size:**
   ```env
   WEBDRIVER_POOL_SIZE=5                  # Increase from 3
   ```

2. **Check for driver leaks:**
   ```python
   # Monitor pool statistics
   from utils.webdriver_manager import get_webdriver_manager
   manager = get_webdriver_manager()
   stats = manager.get_pool_stats()
   print(f"Active drivers: {stats['active_drivers']}")
   print(f"Pool size: {stats['pool_size']}")
   ```

3. **Reduce concurrent operations:**
   ```bash
   # Use smaller batch sizes
   python cli.py discover --batch-size 2 --limit 10
   ```

4. **Manual cleanup:**
   ```python
   # Force cleanup if needed
   from utils.webdriver_manager import get_webdriver_manager
   manager = get_webdriver_manager()
   manager.cleanup()
   ```

## 📧 Email Generation Issues

### Issue: "Email generation failed"

**Error Messages:**
```
Error: Email generation failed
Error: AI service initialization failed
Error: Template processing failed
Error: Personalization data missing
```

**Diagnosis:**
```bash
# Debug email generation step-by-step
python debug_email_generation.py

# This debug script will show:
# - AI Service initialization status
# - Test prospect creation
# - Email generation attempt with detailed error reporting
# - Success/failure with specific error messages

# Verify Notion database schema for email fields
python verify_notion_schema.py

# This schema verification script will show:
# - Database connectivity and field mappings
# - Email-related field presence and configuration
# - Field extraction method testing
# - Sample prospect data analysis

# Test Azure OpenAI connection
python -c "
from services.email_generator import EmailGenerator
from utils.config import Config
config = Config.from_env()
generator = EmailGenerator(config)
print('Azure OpenAI connection successful')
"
```

### Issue: "Azure OpenAI API errors"

**Error Messages:**
```
Error: Azure OpenAI API quota exceeded
Error: Azure OpenAI deployment not found
Error: Azure OpenAI authentication failed
Error: Email generation failed
```

**Diagnosis:**
```bash
# Debug email generation first
python debug_email_generation.py

# Test Azure OpenAI connection
python -c "
from services.email_generator import EmailGenerator
from utils.config import Config
config = Config.from_env()
generator = EmailGenerator(config)
print('Azure OpenAI connection successful')
"
```

**Solutions:**

1. **Check Azure OpenAI configuration:**
   ```env
   USE_AZURE_OPENAI=true
   AZURE_OPENAI_API_KEY=your_key_here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
   ```

2. **Verify deployment exists:**
   - Check Azure OpenAI Studio
   - Ensure deployment is running
   - Verify deployment name matches configuration

3. **Check quota and billing:**
   - Review Azure OpenAI quota in Azure Portal
   - Ensure subscription is active
   - Request quota increase if needed

4. **Fallback to regular OpenAI:**
   ```env
   USE_AZURE_OPENAI=false
   OPENAI_API_KEY=sk-your_openai_key_here
   ```

### Issue: "Regular OpenAI API errors"

**Error Messages:**
```
Error: OpenAI API quota exceeded
Error: OpenAI model not available
Error: Email generation failed
```

**Solutions:**

1. **Check OpenAI billing:**
   - Verify payment method is active
   - Check available credits
   - Review usage limits

2. **Use different model:**
   ```env
   EMAIL_GENERATION_MODEL=gpt-3.5-turbo  # Instead of gpt-4
   AI_PARSING_MODEL=gpt-3.5-turbo
   ```

3. **Reduce token usage:**
   ```env
   MAX_EMAIL_LENGTH=300        # Reduce from 500
   AI_PARSING_TIMEOUT=20       # Reduce timeout
   ```

4. **Switch to Azure OpenAI:**
   - Often more reliable for production use
   - Better rate limits and availability

### Issue: "Email validation failed"

**Error Messages:**
```
Error: Generated email too long
Error: Email content validation failed
Error: Spam-like content detected
```

**Solutions:**

1. **Adjust generation parameters:**
   ```env
   MAX_EMAIL_LENGTH=300        # Shorter emails
   PERSONALIZATION_LEVEL=low   # Less personalization
   ENHANCED_PERSONALIZATION=false  # Disable enhanced features
   ```

2. **Review email templates:**
   - Check templates in services/email_generator.py
   - Ensure templates follow best practices

3. **Manual review:**
   ```bash
   # Generate emails with review
   python cli.py generate-emails --prospect-ids "1,2,3" --output review.json
   # Review generated emails before sending
   ```

## 🤖 AI Parsing Issues

### Issue: "AI parsing failed"

**Error Messages:**
```
Error: Failed to parse LinkedIn profile
Error: AI parsing timeout
Error: Invalid JSON from AI response
Error: AI parsing confidence too low
```

**Diagnosis:**
```bash
# Test AI parsing
python -c "
from services.ai_parser import AIParser
from utils.config import Config
config = Config.from_env()
parser = AIParser(config)
print('AI Parser initialized successfully')
"
```

**Solutions:**

1. **Check AI parsing configuration:**
   ```env
   ENABLE_AI_PARSING=true
   AI_PARSING_MODEL=gpt-4
   AI_PARSING_MAX_RETRIES=3
   AI_PARSING_TIMEOUT=30
   ```

2. **Use enhanced validation with fallback data:**
   ```python
   # The system now includes enhanced validation and fallback handling
   from services.ai_parser import AIParser
   
   parser = AIParser(config)
   
   # Provide fallback data for critical fields
   fallback_data = {
       "name": "John Doe",
       "current_role": "Software Engineer",
       "experience": [],
       "skills": [],
       "summary": ""
   }
   
   result = parser.parse_linkedin_profile(html_content, fallback_data)
   # This ensures you always get valid data, even if AI parsing fails
   ```

3. **Increase timeout and retries:**
   ```env
   AI_PARSING_TIMEOUT=60       # Increase timeout
   AI_PARSING_MAX_RETRIES=5    # More retries
   ```

4. **Use fallback parsing:**
   ```env
   ENABLE_AI_PARSING=false     # Disable AI parsing temporarily
   ```

5. **Check model availability:**
   - Verify AI model is deployed (Azure OpenAI)
   - Check model name matches deployment
   - Ensure sufficient quota

6. **Validate required fields:**
   - The system now validates that critical fields (`name`, `current_role`) are present
   - Provides meaningful defaults ("Unknown Profile", "Unknown Role") when data is missing
   - Uses fallback data when AI parsing returns incomplete results

### Issue: "Product analysis failed"

**Error Messages:**
```
Error: Failed to analyze product
Error: Product analysis timeout
Error: Cannot extract product features
```

**Solutions:**

1. **Check product analysis settings:**
   ```env
   ENABLE_PRODUCT_ANALYSIS=true
   PRODUCT_ANALYSIS_MODEL=gpt-4
   PRODUCT_ANALYSIS_MAX_RETRIES=3
   ```

2. **Reduce analysis scope:**
   ```env
   PRODUCT_ANALYSIS_MODEL=gpt-3.5-turbo  # Faster model
   ```

3. **Disable enhanced analysis:**
   ```env
   ENABLE_PRODUCT_ANALYSIS=false
   ```

## 📧 Email Sending Issues

### Issue: "Resend API errors"

**Error Messages:**
```
Error: Resend API key invalid
Error: Email sending failed
Error: Domain not verified
Error: Rate limit exceeded
```

**Diagnosis:**
```bash
# Test Resend configuration
python -c "
from services.email_sender import EmailSender
from utils.config import Config
config = Config.from_env()
sender = EmailSender(config)
print('Resend EmailSender initialized successfully')
"
```

**Solutions:**

1. **Check Resend configuration:**
   ```env
   RESEND_API_KEY=re_your_api_key_here
   SENDER_EMAIL=your-name@yourdomain.com
   SENDER_NAME=Your Name
   ```

2. **Verify domain setup:**
   - Check domain verification in Resend dashboard
   - Ensure DNS records are configured
   - Use resend.dev for testing

3. **Check rate limits:**
   ```env
   RESEND_REQUESTS_PER_MINUTE=50  # Reduce from 100
   ```

4. **Test email sending:**
   ```bash
   python cli.py test-email your-email@example.com
   ```

5. **Debug email sending issues:**
   ```bash
   # Run comprehensive email send debugging
   python test_email_send.py
   ```
   
   This script tests:
   - Simple email sending
   - Special character handling
   - Actual email content from database
   - Resend API troubleshooting

6. **Debug email content issues:**
   ```bash
   # Analyze email content for problematic characters
   python debug_email_content.py
   ```
   
   This script analyzes:
   - Control characters and null bytes in email content
   - Non-ASCII characters that might cause issues
   - Smart quotes, em dashes, and special formatting
   - Provides cleaned content for testing
   - Tests sending cleaned email content

### Issue: "Email content contains problematic characters"

**Error Messages:**
```
Error: Email sending failed due to invalid characters
Error: Special characters in email content
Error: Email content encoding issues
```

**Diagnosis:**
```bash
# Analyze email content for problematic characters
python debug_email_content.py
```

**Solutions:**

1. **Clean email content:**
   - The debug script automatically tests cleaned content
   - Removes control characters and null bytes
   - Replaces smart quotes with regular quotes
   - Converts em dashes to regular dashes

2. **Check email generation settings:**
   ```env
   EMAIL_GENERATION_MODEL=gpt-3.5-turbo  # May produce cleaner content
   MAX_EMAIL_LENGTH=300                  # Shorter emails
   ```

3. **Manual content cleaning:**
   ```python
   import re
   # Remove control characters
   clean_content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content)
   # Replace smart quotes
   clean_content = clean_content.replace('"', '"').replace('"', '"')
   ```

### Issue: "Email delivery tracking failed"

**Error Messages:**
```
Error: Cannot track email delivery
Error: Webhook processing failed
Error: Email status not updated
```

**Solutions:**

1. **Check webhook configuration:**
   - Ensure webhooks are configured in Resend
   - Verify webhook URL is accessible
   - Check webhook authentication

2. **Manual status checking:**
   ```bash
   # Check delivery status manually
   python -c "
   from services.email_sender import EmailSender
   from utils.config import Config
   config = Config.from_env()
   sender = EmailSender(config)
   report = sender.get_delivery_report()
   print(report)
   "
   ```

3. **Update Notion manually:**
   - Check Notion database for email status
   - Update status manually if needed

4. **Fix email field defaults:**
   ```bash
   # Update existing prospects with correct email field defaults
   python update_existing_prospects_defaults.py
   ```
   
   This script will:
   - Identify prospects with empty email status fields
   - Set proper default values ("Not Generated", "Not Sent")
   - Ensure data consistency for email workflow tracking

## 🔍 Enhanced Workflow Issues

### Issue: "Enhanced workflow failed"

**Error Messages:**
```
Error: Enhanced workflow disabled
Error: AI structuring failed
Error: Comprehensive analysis failed
```

**Solutions:**

1. **Check enhanced workflow settings:**
   ```env
   ENABLE_ENHANCED_WORKFLOW=true
   ENHANCED_PERSONALIZATION=true
   BATCH_PROCESSING_ENABLED=true
   ```

2. **Disable problematic features:**
   ```env
   ENABLE_AI_PARSING=false
   ENABLE_PRODUCT_ANALYSIS=false
   ENHANCED_PERSONALIZATION=false
   ```

3. **Use basic workflow:**
   ```bash
   # Run basic discovery without enhancements
   python cli.py discover --basic-mode --limit 10
   ```

### Issue: "Notion enhanced data storage failed"

**Error Messages:**
```
Error: Cannot store AI-structured data
Error: Enhanced Notion schema not found
Error: AI data fields missing
```

**Solutions:**

1. **Recreate Notion database:**
   ```bash
   # Let system create new database with enhanced schema
   unset NOTION_DATABASE_ID
   python cli.py discover --limit 1
   ```

2. **Check Notion database schema:**
   - Ensure database has enhanced fields
   - Add missing properties manually
   - Check field types match expectations

3. **Debug storage process:**
   ```bash
   # Verify Notion storage during parallel processing
   python debug_notion_storage.py
   ```

4. **Disable enhanced storage:**
   ```env
   # Store basic data only
   ENABLE_ENHANCED_WORKFLOW=false
   ```

## 🔍 Performance Issues

### Issue: "System running slowly"

**Symptoms:**
- Long processing times
- High memory usage
- Frequent timeouts

**Diagnosis:**
```bash
# Monitor system resources
top -p $(pgrep -f "python.*cli.py")

# Check processing times
python cli.py --verbose discover --limit 5
```

**Solutions:**

1. **Reduce batch sizes:**
   ```bash
   python cli.py discover --batch-size 2 --limit 10
   ```

2. **Increase delays:**
   ```env
   SCRAPING_DELAY=3.0
   HUNTER_REQUESTS_PER_MINUTE=5
   ```

3. **Optimize configuration:**
   ```env
   MAX_PROSPECTS_PER_COMPANY=5   # Reduce from 10
   MAX_PRODUCTS_PER_RUN=25       # Reduce from 50
   ```

4. **Monitor memory usage:**
   ```bash
   # Use memory profiling
   python -m memory_profiler cli.py discover --limit 5
   ```

### Issue: "Database operations slow"

**Solutions:**

1. **Check Notion API limits:**
   - Notion has rate limits
   - System implements automatic backoff

2. **Optimize database structure:**
   - Ensure proper indexing
   - Remove unnecessary properties

### Issue: "Caching system problems"

**Error Messages:**
```
Error: Cache initialization failed
Error: Cache memory limit exceeded
Error: Persistent cache directory not accessible
Error: Cache corruption detected
```

**Diagnosis:**
```bash
# Test caching service
python -c "
from services.caching_service import CachingService
from utils.config import Config
config = Config.from_env()
cache = CachingService(config)
stats = cache.get_stats()
print(f'Cache entries: {stats.total_entries}')
print(f'Memory usage: {stats.memory_usage_mb:.1f} MB')
print(f'Hit rate: {stats.hit_rate:.2%}')
"
```

**Solutions:**

1. **Check cache configuration:**
   ```env
   ENABLE_CACHING=true
   CACHE_MEMORY_MAX_ENTRIES=1000
   CACHE_MEMORY_MAX_MB=100
   CACHE_PERSISTENT_DIR=.cache
   CACHE_DEFAULT_TTL=3600
   ```

2. **Clear corrupted cache:**
   ```bash
   # Clear persistent cache files
   rm -rf .cache/*
   
   # Or clear programmatically
   python -c "
   from services.caching_service import CachingService
   from utils.config import Config
   cache = CachingService(Config.from_env())
   cache.clear()
   print('Cache cleared successfully')
   "
   ```

3. **Reduce cache memory usage:**
   ```env
   CACHE_MEMORY_MAX_ENTRIES=500    # Reduce from 1000
   CACHE_MEMORY_MAX_MB=50          # Reduce from 100
   ```

4. **Check disk space:**
   ```bash
   # Ensure sufficient disk space for persistent cache
   df -h .cache
   ```

5. **Monitor cache performance:**
   ```python
   from services.caching_service import CachingService
   from utils.config import Config
   
   cache = CachingService(Config.from_env())
   stats = cache.get_stats()
   
   print(f"Cache Statistics:")
   print(f"  Hit rate: {stats.hit_rate:.2%}")
   print(f"  Memory usage: {stats.memory_usage_mb:.1f} MB")
   print(f"  Total entries: {stats.total_entries}")
   
   # If hit rate is low, consider cache warming
   if stats.hit_rate < 0.5:
       print("Consider implementing cache warming")
   ```

6. **Implement cache warming:**
   ```python
   # Warm cache with frequently accessed data
   warming_config = {
       "common_profiles": {
           "factory": lambda: load_common_data(),
           "ttl": 7200,
           "priority": 10
       }
   }
   cache.warm_cache(warming_config)
   ```

7. **Clean up expired entries:**
   ```bash
   # Regular cache maintenance
   python -c "
   from services.caching_service import CachingService
   from utils.config import Config
   cache = CachingService(Config.from_env())
   cache.cleanup_expired()
   print('Expired cache entries cleaned up')
   "
   ```

3. **Batch database operations:**
   - System already batches operations
   - Consider smaller batch sizes

## 🐛 Debugging Techniques

### Specialized Debug Scripts

The system includes several debug scripts for diagnosing specific issues:

```bash
# Update existing prospects with email field defaults
python update_existing_prospects_defaults.py
# Shows: Prospect email status updates, batch processing, data consistency fixes
# Debug discovery filtering issues step-by-step
python debug_discovery.py
# Shows: Processed companies cache, ProductHunt scraping, company filtering logic, diagnosis

# Debug email generation issues step-by-step
python debug_email_generation.py
# Shows: AI service initialization, test prospect creation, email generation attempt, error details

# Test dashboard creation components
python test_dashboard_creation.py
# Shows: Notion connection, database creation, permissions

# Debug daily analytics creation issues
python debug_daily_analytics.py
# Shows: Analytics database access, entry creation, data validation

# Debug email content character issues
python debug_email_content.py
# Shows: Character analysis, content cleaning, test sending

# Debug Notion storage during parallel processing
python debug_notion_storage.py
# Shows: Prospect storage verification, data consistency, parallel processing integrity

# Debug parallel processor functionality
python debug_parallel_processor.py
# Shows: Parallel processor initialization, batch processing, worker management

# Test complete pipeline
python test_full_pipeline.py
# Shows: End-to-end workflow testing

# Test email functionality
python test_email_pipeline.py
# Shows: Email generation and sending capabilities

# Analyze import issues and circular dependencies
python utils/import_analyzer.py
# Shows: Unused imports, circular dependencies, import analysis report

# Validate import organization and standards
python utils/validate_imports.py
# Shows: Import organization compliance, validation errors
```

### Enable Debug Logging

```bash
# Maximum verbosity
python cli.py --verbose discover --limit 1

# Debug specific components
LOG_LEVEL=DEBUG python cli.py discover --limit 1
```

### Use Dry-Run Mode

```bash
# Test without API calls
python cli.py --dry-run discover --limit 10
python cli.py --dry-run process-company "Test Company"
python cli.py --dry-run generate-emails --prospect-ids "1,2,3"
```

### Isolate Components

```bash
# Test individual services
python -c "
from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config
config = Config.from_env()
scraper = ProductHuntScraper(config)
products = scraper.get_latest_products(limit=1)
print(f'Found {len(products)} products')
"
```

### Monitor API Calls

```bash
# Run monitoring example
python examples/error_handling_example.py

# Check API health
python cli.py status
```

### Review Logs

```bash
# View all logs
ls -la logs/

# View recent errors
grep -i error logs/prospect_automation_*.log | tail -20

# View API calls
grep -i "api" logs/prospect_automation_*.log | tail -10
```

## 🆘 Emergency Procedures

### System Completely Broken

1. **Reset configuration:**
   ```bash
   mv .env .env.backup
   cp .env.example .env
   # Re-enter API keys
   ```

2. **Reinstall dependencies:**
   ```bash
   pip uninstall -r requirements.txt -y
   pip install -r requirements.txt
   ```

3. **Clear cache and logs:**
   ```bash
   rm -rf __pycache__/ */__pycache__/
   rm -rf logs/*.log
   ```

4. **Test basic functionality:**
   ```bash
   python cli.py --help
   python cli.py --dry-run status
   ```

### API Keys Compromised

1. **Immediately revoke old keys**
2. **Generate new keys**
3. **Update configuration**
4. **Test new keys**
5. **Monitor for unauthorized usage**

### Data Corruption

1. **Check Notion database integrity**
2. **Review recent logs for errors**
3. **Restore from backup if available**
4. **Re-run discovery with small batch**

## 📞 Getting Additional Help

### Self-Help Resources

1. **Documentation:**
   - [README.md](../README.md) - Main documentation
   - [SETUP_GUIDE.md](SETUP_GUIDE.md) - Installation guide
   - [CLI_USAGE.md](CLI_USAGE.md) - Command reference

2. **Examples:**
   - `examples/cli_usage_examples.py` - CLI examples
   - `examples/batch_processing_example.py` - Batch processing
   - `examples/error_handling_example.py` - Error handling

3. **Logs:**
   - `logs/prospect_automation_*.log` - Main application logs
   - `logs/error_monitoring.json` - Error tracking
   - `logs/error_notifications.json` - Error notifications

### Creating Bug Reports

When reporting issues, include:

1. **System information:**
   ```bash
   python --version
   pip list | grep -E "(notion|hunter|openai)"
   ```

2. **Configuration (without API keys):**
   ```bash
   python -c "
   from utils.config import Config
   config = Config.from_env()
   print(f'Scraping delay: {config.scraping_delay}')
   print(f'Max products: {config.max_products_per_run}')
   # Don't print API keys!
   "
   ```

3. **Error logs:**
   ```bash
   tail -50 logs/prospect_automation_*.log
   ```

4. **Steps to reproduce:**
   - Exact commands used
   - Expected vs actual behavior
   - Any error messages

### Support Channels

- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check all documentation first
- **Community**: Share experiences with other users

---

**Remember**: Most issues can be resolved by carefully checking configuration, API keys, and network connectivity. When in doubt, start with dry-run mode and verbose logging to understand what's happening.