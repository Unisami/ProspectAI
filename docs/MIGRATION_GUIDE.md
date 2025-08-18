# Migration Guide: Refactored Architecture

This guide helps developers migrate from the legacy architecture to the new refactored system with unified services, centralized configuration, and enhanced performance optimizations.

## Overview of Changes

The refactoring introduces several major architectural improvements:

- **Unified AI Service**: Consolidated all AI operations into a single `AIService` class
- **Centralized Configuration**: New `ConfigurationService` for unified configuration management
- **Enhanced Caching**: Multi-tier caching system with intelligent cache warming
- **Centralized Rate Limiting**: Unified rate limiting service across all APIs
- **Improved Error Handling**: Enhanced error categorization and recovery mechanisms
- **Optimized Parallel Processing**: Enhanced parallel processing with resource management
- **Validation Framework**: Centralized validation with type safety and error reporting

## Breaking Changes

### 1. AI Service Consolidation

**Before (Legacy):**
```python
from services.ai_parser import AIParser
from services.email_generator import EmailGenerator
from services.product_analyzer import ProductAnalyzer

# Multiple service instances
ai_parser = AIParser(config)
email_generator = EmailGenerator(config)
product_analyzer = ProductAnalyzer(config)

# Separate method calls
profile_result = ai_parser.parse_linkedin_profile(html)
product_result = product_analyzer.analyze_product(content)
email_result = email_generator.generate_email(prospect)
```

**After (Refactored):**
```python
from services.ai_service import AIService, EmailTemplate

# Single unified service
ai_service = AIService(config)

# Unified method calls with consistent response format
profile_result = ai_service.parse_linkedin_profile(html)
product_result = ai_service.analyze_product(content)
email_result = ai_service.generate_email(
    prospect=prospect,
    template_type=EmailTemplate.COLD_OUTREACH
)
```

### 2. Configuration Management

**Before (Legacy):**
```python
from utils.config import Config

# Direct config usage
config = Config.from_env()
service = SomeService(config)
```

**After (Refactored):**
```python
from utils.configuration_service import ConfigurationService

# Centralized configuration service
config_service = ConfigurationService()
config = config_service.get_config()
service = SomeService(config)

# Or use the service directly
service = SomeService(config_service)
```

### 3. Error Handling

**Before (Legacy):**
```python
from utils.error_handling import handle_error

try:
    result = some_operation()
except Exception as e:
    handle_error(e, "Operation failed")
```

**After (Refactored):**
```python
from utils.error_handling_enhanced import EnhancedErrorHandler

error_handler = EnhancedErrorHandler(config)

try:
    result = some_operation()
except Exception as e:
    error_handler.handle_error(e, context="Operation failed", operation_type="api_call")
```

### 4. Caching Integration

**Before (Legacy):**
```python
# No centralized caching
result = expensive_operation()
```

**After (Refactored):**
```python
from services.caching_service import CachingService

cache_service = CachingService(config)

# Use caching for expensive operations
cache_key = f"operation_{param_hash}"
result = cache_service.get(cache_key)

if result is None:
    result = expensive_operation()
    cache_service.set(cache_key, result, ttl=3600)
```

## Migration Steps

### Step 1: Update Import Statements

Replace legacy imports with new unified services:

```python
# Remove these legacy imports
# from services.ai_parser import AIParser
# from services.email_generator import EmailGenerator
# from services.product_analyzer import ProductAnalyzer

# Add these new imports
from services.ai_service import AIService, EmailTemplate, AIOperationType
from utils.configuration_service import ConfigurationService
from services.caching_service import CachingService
from utils.error_handling_enhanced import EnhancedErrorHandler
```

### Step 2: Update Service Initialization

**Legacy Pattern:**
```python
def __init__(self, config):
    self.config = config
    self.ai_parser = AIParser(config)
    self.email_generator = EmailGenerator(config)
    self.product_analyzer = ProductAnalyzer(config)
```

**Refactored Pattern:**
```python
def __init__(self, config_service=None):
    self.config_service = config_service or ConfigurationService()
    self.config = self.config_service.get_config()
    self.ai_service = AIService(self.config)
    self.cache_service = CachingService(self.config)
    self.error_handler = EnhancedErrorHandler(self.config)
```

### Step 3: Update AI Operations

**Legacy AI Parsing:**
```python
# Old way - multiple services
profile_data = self.ai_parser.parse_linkedin_profile(html_content)
product_data = self.product_analyzer.analyze_product(raw_content)
email_content = self.email_generator.generate_email(prospect_data)
```

**Refactored AI Operations:**
```python
# New way - unified service
profile_result = self.ai_service.parse_linkedin_profile(html_content)
if profile_result.success:
    profile_data = profile_result.data
    confidence = profile_result.confidence_score

product_result = self.ai_service.analyze_product(raw_content)
if product_result.success:
    product_data = product_result.data

email_result = self.ai_service.generate_email(
    prospect=prospect_data,
    template_type=EmailTemplate.COLD_OUTREACH,
    linkedin_profile=profile_data,
    product_analysis=product_data
)
```

### Step 4: Update Error Handling

**Legacy Error Handling:**
```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return None
```

**Enhanced Error Handling:**
```python
try:
    result = risky_operation()
except Exception as e:
    error_context = {
        'operation': 'risky_operation',
        'parameters': {'param1': value1},
        'timestamp': datetime.now()
    }
    
    recovery_result = self.error_handler.handle_error(
        error=e,
        context=error_context,
        operation_type='api_call',
        allow_retry=True
    )
    
    if recovery_result.recovered:
        result = recovery_result.result
    else:
        return None
```

### Step 5: Add Caching Support

For expensive operations, add caching:

```python
def expensive_ai_operation(self, input_data):
    # Generate cache key
    cache_key = f"ai_operation_{hash(str(input_data))}"
    
    # Try to get from cache first
    cached_result = self.cache_service.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Perform expensive operation
    result = self.ai_service.some_expensive_operation(input_data)
    
    # Cache the result
    if result.success:
        self.cache_service.set(cache_key, result, ttl=3600)
    
    return result
```

## Configuration Updates

### Environment Variables

Add new configuration options to your `.env` file:

```env
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
```

### Configuration Validation

Update your configuration validation:

```python
from utils.configuration_service import ConfigurationService

def validate_configuration():
    config_service = ConfigurationService()
    
    # Validate all configuration
    validation_result = config_service.validate_config()
    
    if not validation_result.is_valid:
        print("Configuration validation failed:")
        for error in validation_result.errors:
            print(f"  - {error}")
        return False
    
    return True
```

## Testing Updates

### Update Test Imports

```python
# Update test imports
from services.ai_service import AIService
from utils.configuration_service import ConfigurationService
from services.caching_service import CachingService
from tests.test_utilities import create_test_config, mock_ai_service
```

### Mock Services in Tests

```python
import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing"""
    service = Mock(spec=AIService)
    service.parse_linkedin_profile.return_value = Mock(
        success=True,
        data={'name': 'Test User', 'role': 'Developer'},
        confidence_score=0.95,
        cached=False
    )
    return service

@pytest.fixture
def test_config_service():
    """Test configuration service"""
    return ConfigurationService(config_path="test_config.yaml")
```

## Performance Optimizations

### Enable Caching

```python
# Initialize caching service
cache_service = CachingService(config)

# Use cache warming for frequently accessed data
warming_config = {
    "common_profiles": {
        "factory": lambda: load_common_linkedin_profiles(),
        "ttl": 7200,
        "priority": 10
    },
    "email_templates": {
        "factory": lambda: load_email_templates(),
        "ttl": 3600,
        "priority": 5
    }
}

cache_service.warm_cache(warming_config)
```

### Optimize AI Operations

```python
# Use batch operations when possible
results = []
for item in batch_items:
    # Check cache first
    cache_key = f"ai_operation_{item.id}"
    cached = cache_service.get(cache_key)
    
    if cached:
        results.append(cached)
    else:
        # Process and cache
        result = ai_service.process_item(item)
        cache_service.set(cache_key, result)
        results.append(result)
```

## Troubleshooting Migration Issues

### Common Issues

1. **Import Errors**: Update all import statements to use new service locations
2. **Configuration Errors**: Ensure all new environment variables are set
3. **Cache Issues**: Clear cache directory if experiencing cache-related problems
4. **Rate Limiting**: Adjust rate limits if hitting API limits

### Debug Commands

```bash
# Validate new configuration
python -c "from utils.configuration_service import ConfigurationService; ConfigurationService().validate_config()"

# Test AI service
python -c "from services.ai_service import AIService; from utils.config import Config; AIService(Config.from_env())"

# Clear cache
rm -rf .cache/

# Run migration tests
python -m pytest tests/test_migration.py -v
```

### Rollback Plan

If migration issues occur, you can temporarily rollback by:

1. Reverting to legacy import statements
2. Using legacy service initialization patterns
3. Disabling new features via environment variables:

```env
# Disable new features for rollback
AI_SERVICE_CACHE_ENABLED=false
ENABLE_CACHING=false
ERROR_HANDLING_ENABLED=false
RATE_LIMITING_ENABLED=false
```

## Validation Checklist

After migration, verify:

- [ ] All services initialize without errors
- [ ] AI operations return consistent results
- [ ] Caching is working (check cache hit rates)
- [ ] Error handling captures and recovers from failures
- [ ] Rate limiting prevents API quota issues
- [ ] Configuration validation passes
- [ ] All tests pass with new architecture
- [ ] Performance metrics show improvements

## Support

For migration assistance:

1. Check the troubleshooting guide: `docs/TROUBLESHOOTING_GUIDE.md`
2. Run diagnostic commands to identify issues
3. Review test examples in `tests/` directory
4. Check service documentation in `docs/` directory

The refactored architecture provides significant performance and maintainability improvements while maintaining backward compatibility where possible.