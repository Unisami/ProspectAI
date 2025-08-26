# AI Service Architecture

## Overview

The Job Prospect Automation system now features a unified `AIService` class that consolidates all AI operations into a single, standardized service. This architectural change improves performance, maintainability, and provides consistent AI processing patterns across the entire system.

## Key Benefits

### 🚀 Performance Improvements
- **Advanced Caching System**: Multi-tier caching with in-memory and persistent storage
- **Result Caching**: Expensive AI operations are cached for 1 hour by default
- **Reduced API Calls**: Consolidated processing reduces redundant AI requests
- **Connection Pooling**: Centralized OpenAI client management with HTTP connection reuse
- **Batch Processing**: Optimized for processing multiple operations efficiently

### 🔧 Standardized Processing
- **Consistent Error Handling**: Unified error recovery and fallback strategies
- **Standardized Responses**: All AI operations return `AIResult` objects with consistent structure
- **Confidence Scoring**: Quality assessment for all AI-extracted data
- **Performance Monitoring**: Detailed metrics and operation tracking

### 🎯 Simplified Integration
- **Single Service**: One service handles all AI operations instead of multiple specialized services
- **Unified API**: Consistent method signatures and response formats
- **Easy Configuration**: Single configuration point for all AI settings
- **Better Testing**: Centralized service is easier to mock and test

## Architecture Components

### Multi-Provider AI Architecture

The system now features a **multi-provider AI architecture** that supports various AI providers through a unified interface:

- **OpenAI** - GPT-3.5-turbo, GPT-4, GPT-4-turbo models
- **Azure OpenAI** - Enterprise-grade OpenAI with custom deployments
- **Anthropic Claude** - Claude-3 models (coming soon)
- **Google Gemini** - Gemini Pro models (coming soon)
- **DeepSeek** - DeepSeek models (coming soon)

### AI Provider Abstraction Layer

The new provider system enables seamless switching between AI providers:

```python
from services.providers.base_provider import BaseAIProvider, CompletionRequest, CompletionResponse

# All providers implement the same interface
class BaseAIProvider:
    def make_completion(self, request: CompletionRequest) -> CompletionResponse
    def validate_config(self) -> ValidationResult
    def get_model_info(self) -> Dict[str, Any]
```

### AIService Class
The main service class that handles all AI operations with multi-provider support:

```python
from services.ai_service import AIService, AIOperationType, EmailTemplate

# Initialize service (automatically uses configured provider)
ai_service = AIService(config)

# Parse LinkedIn profile
result = ai_service.parse_linkedin_profile(html_content)

# Generate personalized email
email_result = ai_service.generate_email(
    prospect=prospect,
    template_type=EmailTemplate.COLD_OUTREACH,
    linkedin_profile=profile
)

# Analyze product information
product_result = ai_service.analyze_product(raw_content)
```

### Supported Operations
- **LinkedIn Profile Parsing**: Extract structured data from LinkedIn HTML with enhanced validation and fallback handling
- **Email Generation**: Create personalized outreach emails with multiple templates
- **Product Analysis**: Analyze product information and market positioning
- **Team Data Extraction**: Structure team member information
- **Business Metrics**: Extract funding, growth stage, and key business insights

### Email Templates
- `COLD_OUTREACH`: Initial outreach to new prospects
- `REFERRAL_FOLLOWUP`: Follow-up emails with referral context
- `PRODUCT_INTEREST`: Product-focused outreach emails
- `NETWORKING`: Networking and relationship-building emails

## Migration from Legacy Services

### Before (Multiple Services)
```python
# Old approach - multiple services
from services.ai_parser import AIParser
from services.email_generator import EmailGenerator
from services.product_analyzer import ProductAnalyzer

ai_parser = AIParser(config)
email_generator = EmailGenerator(config)
product_analyzer = ProductAnalyzer(config)

# Multiple API calls and configurations
profile_result = ai_parser.parse_linkedin_profile(html)
product_result = product_analyzer.analyze_product(content)
email_result = email_generator.generate_email(prospect)
```

### After (Unified Service)
```python
# New approach - single service
from services.ai_service import AIService

ai_service = AIService(config)

# Single service with caching and optimization
profile_result = ai_service.parse_linkedin_profile(html)
product_result = ai_service.analyze_product(content)
email_result = ai_service.generate_email(prospect)
```

## Configuration

### Multi-Provider Configuration
```env
# AI Provider Selection
AI_PROVIDER=openai  # openai, azure-openai, anthropic, google, deepseek

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Azure OpenAI Configuration (Recommended for Enterprise)
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Anthropic Configuration (Coming Soon)
ANTHROPIC_API_KEY=your_anthropic_key

# Google Configuration (Coming Soon)
GOOGLE_API_KEY=your_google_key

# DeepSeek Configuration (Coming Soon)
DEEPSEEK_API_KEY=your_deepseek_key

# Model Configuration
AI_MODEL=gpt-4  # Provider-specific model names
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000

# AI Service Settings
AI_SERVICE_CACHE_ENABLED=true
AI_SERVICE_CACHE_TTL=3600
AI_SERVICE_RATE_LIMIT_DELAY=1.0

# Caching Configuration
ENABLE_CACHING=true
CACHE_MEMORY_MAX_ENTRIES=1000
CACHE_MEMORY_MAX_MB=100
CACHE_PERSISTENT_DIR=.cache
CACHE_DEFAULT_TTL=3600
```

### Service Configuration
```python
from utils.base_service import ServiceConfig

service_config = ServiceConfig(
    name="AIService",
    rate_limit_delay=1.0,
    max_retries=3,
    timeout=60,
    enable_caching=True,
    cache_ttl=3600
)

ai_service = AIService(config, service_config)
```

## Performance Monitoring

### Cache Statistics
```python
# Get cache performance metrics
cache_stats = ai_service.get_cache_stats()
print(f"Cache entries: {cache_stats['total_entries']}")
print(f"Cache size: {cache_stats['cache_size_mb']} MB")
print(f"Cache hit rate: {cache_stats['hit_rate']:.2%}")

# Access the underlying caching service
from services.caching_service import CachingService
cache_service = CachingService(config)

# Get detailed cache statistics
detailed_stats = cache_service.get_stats()
print(f"Memory usage: {detailed_stats.memory_usage_mb:.1f} MB")
print(f"Hit rate: {detailed_stats.hit_rate:.2%}")
print(f"Total entries: {detailed_stats.total_entries}")
```

### Service Metrics
```python
# Get service performance metrics
metrics = ai_service.get_performance_metrics()
print(f"Total operations: {metrics['total_operations']}")
print(f"Average response time: {metrics['average_response_time']:.2f}s")
print(f"Success rate: {metrics['success_rate']:.2%}")
```

## Best Practices

### 1. Enable Caching
Always enable caching for production use to reduce API costs and improve performance:

```python
ai_service = AIService(config)  # Caching enabled by default
```

### 2. Handle Results Properly
Always check the success status of AI operations and use fallback data when needed:

```python
# Basic parsing
result = ai_service.parse_linkedin_profile(html_content)
if result.success:
    profile = result.data
    print(f"Confidence: {result.confidence_score:.2f}")
    print(f"Cached: {result.cached}")
else:
    print(f"Error: {result.error_message}")

# Enhanced parsing with fallback data
fallback_data = {
    "name": "John Doe",
    "current_role": "Software Engineer",
    "experience": [],
    "skills": [],
    "summary": ""
}

result = ai_service.parse_linkedin_profile(html_content, fallback_data=fallback_data)
# This ensures you always get valid data, even if AI parsing fails
```

### 3. Use Appropriate Templates
Choose the right email template for your use case:

```python
# For initial outreach
email_result = ai_service.generate_email(
    prospect=prospect,
    template_type=EmailTemplate.COLD_OUTREACH
)

# For product-focused emails
email_result = ai_service.generate_email(
    prospect=prospect,
    template_type=EmailTemplate.PRODUCT_INTEREST,
    product_analysis=product_data
)
```

### 4. Monitor Performance
Regularly check service performance and cache effectiveness:

```python
# Clear cache if needed
ai_service.clear_cache()

# Monitor cache usage
stats = ai_service.get_cache_stats()
if stats['cache_size_mb'] > 100:  # If cache is too large
    ai_service.clear_cache()

# Advanced cache management
from services.caching_service import CachingService
cache_service = CachingService(config)

# Clean up expired entries
cache_service.cleanup_expired()

# Invalidate specific patterns
cache_service.invalidate_pattern("linkedin_profile_*")

# Warm cache with frequently accessed data
warming_config = {
    "common_profiles": {
        "factory": lambda: load_common_profiles(),
        "ttl": 7200,
        "priority": 10
    }
}
cache_service.warm_cache(warming_config)
```

## Troubleshooting

### Common Issues

1. **High API Costs**: Enable caching and check cache hit rates
2. **Slow Performance**: Monitor cache statistics and clear if needed
3. **Low Confidence Scores**: Provide more complete input data
4. **Email Quality Issues**: Use email content validation

### Debug Mode
Enable verbose logging for debugging:

```python
import logging
logging.getLogger('AIService').setLevel(logging.DEBUG)

ai_service = AIService(config)
```

## Multi-Provider Support (New Feature)

### Provider Abstraction Layer

The system now includes a **provider abstraction layer** that enables support for multiple AI providers:

```python
from services.providers.base_provider import BaseAIProvider, CompletionRequest, CompletionResponse

# All providers implement the same interface
provider = get_ai_provider("anthropic")  # or "openai", "google", etc.
response = provider.make_completion(request)
```

### Supported Providers

#### Currently Available:
- **OpenAI** - GPT-3.5-turbo, GPT-4, GPT-4-turbo
- **Azure OpenAI** - Enterprise deployments with custom models

#### Coming Soon:
- **Anthropic Claude** - Claude-3 Sonnet, Claude-3 Opus
- **Google Gemini** - Gemini Pro, Gemini Pro Vision
- **DeepSeek** - DeepSeek Coder, DeepSeek Chat

### Provider Configuration

Configure your preferred AI provider through environment variables:

```env
# Set your preferred provider
AI_PROVIDER=anthropic

# Provider-specific credentials
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
```

### Testing Provider Interface

Test the BaseAIProvider interface implementation:

```bash
# Test the provider interface
python test_base_provider.py
```

This test validates:
- Provider interface implementation
- Configuration handling and validation
- Completion request/response processing
- Model information retrieval
- Connection testing capabilities

### CLI Provider Management

Manage AI providers through CLI commands:

```bash
# List available providers
python cli.py list-ai-providers

# Configure a specific provider
python cli.py configure-ai --provider anthropic

# Switch active provider
python cli.py set-ai-provider anthropic

# Validate provider configuration
python cli.py validate-ai-config
```

### Provider-Specific Features

Each provider offers unique capabilities:

- **OpenAI**: Proven performance, extensive model selection
- **Azure OpenAI**: Enterprise security, custom deployments, SLA guarantees
- **Anthropic**: Constitutional AI, longer context windows, safety focus
- **Google Gemini**: Multimodal capabilities, competitive pricing
- **DeepSeek**: Code-specialized models, cost-effective options

## Future Enhancements

- **Multi-Model Support**: Support for different AI models per operation type
- **Intelligent Cache Warming**: Predictive cache warming based on usage patterns
- **Batch Operations**: Process multiple items in single API calls
- **Custom Templates**: User-defined email templates
- **A/B Testing**: Template performance comparison across providers
- **Cache Analytics**: Advanced cache performance analytics and optimization recommendations
- **Provider Fallbacks**: Automatic fallback to secondary providers on failure
- **Cost Optimization**: Intelligent provider selection based on cost and performance