# Usage Examples and Best Practices

This guide provides practical examples and best practices for using the Job Prospect Automation system effectively.

## 📚 Table of Contents

- [Getting Started Examples](#getting-started-examples)
- [Enhanced AI Features](#enhanced-ai-features)
- [Azure OpenAI Configuration](#azure-openai-configuration)
- [Email Sending with Resend](#email-sending-with-resend)
- [Common Workflows](#common-workflows)
- [Advanced Usage Patterns](#advanced-usage-patterns)
- [Best Practices](#best-practices)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting Scenarios](#troubleshooting-scenarios)

## 🚀 Getting Started Examples

### First-Time Setup and Test

```bash
# 1. Initial setup
git clone <repository-url>
cd job-prospect-automation
pip install -r requirements.txt

# 2. Configure API keys
cp .env.example .env
# Edit .env with your API keys

# 3. Test configuration
python cli.py --dry-run status

# 4. Small test run
python cli.py --dry-run run-campaign --limit 3 --generate-emails

# 5. First real run (small scale)
python cli.py run-campaign --limit 5 --generate-emails
```

**Note:** The system automatically detects and skips companies that have already been processed, preventing duplicate work and API usage.

### Daily Workflow Example

```bash
#!/bin/bash
# daily_prospect_search.sh - Daily automation script

echo "Starting daily prospect search..."

# Run complete campaign workflow with reasonable limits
python cli.py run-campaign --limit 20 --generate-emails

# Check results
python cli.py status

# Generate emails for recent prospects (easier)
# python cli.py generate-emails-recent --limit 5

# Alternative: Generate emails for specific prospects (you'll need to get prospect IDs)
# python cli.py generate-emails --prospect-ids "id1,id2,id3" --output daily_emails.json

echo "Daily prospect search completed!"
```

## 🤖 Enhanced AI Features

### AI-Powered Data Parsing

The system now includes advanced AI parsing capabilities that structure raw scraped data into organized formats optimized for email personalization, using consolidated AI calls for improved performance.

#### What AI Parsing Does

1. **LinkedIn Profile Parsing**: Converts raw LinkedIn HTML into structured profile data
2. **Product Information Structuring**: Organizes product features, pricing, and market analysis
3. **Team Data Extraction**: Identifies and structures team member information
4. **Business Metrics Analysis**: Extracts funding, growth stage, and key business insights
5. **Combined AI Processing**: Optimized single-call approach for product and business analysis (25% fewer API calls)

#### Configuring AI Parsing

```bash
# Enable AI parsing features
ENABLE_AI_PARSING=true
AI_PARSING_MODEL=gpt-4
AI_PARSING_MAX_RETRIES=3
AI_PARSING_TIMEOUT=30

# Enable product analysis
ENABLE_PRODUCT_ANALYSIS=true
PRODUCT_ANALYSIS_MODEL=gpt-4
PRODUCT_ANALYSIS_MAX_RETRIES=3
```

#### AI Service Example

```python
#!/usr/bin/env python3
"""Example of unified AI service capabilities with refactored architecture."""

from services.ai_service import AIService, EmailTemplate, AIOperationType
from utils.configuration_service import ConfigurationService
from services.caching_service import CachingService
from utils.logging_config import setup_logging

def main():
    # Setup with new configuration service
    setup_logging(log_level="INFO")
    config_service = ConfigurationService()
    config = config_service.get_config()
    
    # Initialize unified AI service with caching
    ai_service = AIService(config)
    cache_service = CachingService(config)
    
    # Example 1: Parse LinkedIn profile with caching
    linkedin_html = "<html>...</html>"  # Raw LinkedIn HTML
    
    # Check cache first
    cache_key = f"linkedin_profile_{hash(linkedin_html)}"
    cached_result = cache_service.get(cache_key)
    
    if cached_result:
        print("Using cached LinkedIn profile data")
        profile_result = cached_result
    else:
        print("Parsing LinkedIn profile with AI...")
        profile_result = ai_service.parse_linkedin_profile(linkedin_html)
        
        if profile_result.success:
            # Cache successful results
            cache_service.set(cache_key, profile_result, ttl=3600)
    
    if profile_result.success:
        profile_data = profile_result.data
        print(f"Profile parsed with confidence: {profile_result.confidence_score:.2f}")
        print(f"Name: {profile_data.get('name')}")
        print(f"Role: {profile_data.get('role')}")
        print(f"Company: {profile_data.get('company')}")
    
    # Example 2: Analyze product with business metrics
    product_content = "Product description and website content..."
    
    print("Analyzing product with AI...")
    product_result = ai_service.analyze_product(product_content)
    
    if product_result.success:
        product_data = product_result.data
        print(f"Product analysis confidence: {product_result.confidence_score:.2f}")
        print(f"Category: {product_data.get('category')}")
        print(f"Key features: {product_data.get('key_features')}")
        print(f"Target market: {product_data.get('target_market')}")
    
    # Example 3: Generate personalized email with unified service
    prospect_data = {
        'name': 'John Doe',
        'role': 'CTO',
        'company': 'TechCorp',
        'linkedin_url': 'https://linkedin.com/in/johndoe'
    }
    
    print("Generating personalized email...")
    email_result = ai_service.generate_email(
        prospect=prospect_data,
        template_type=EmailTemplate.COLD_OUTREACH,
        linkedin_profile=profile_data if profile_result.success else None,
        product_analysis=product_data if product_result.success else None
    )
    
    if email_result.success:
        email_data = email_result.data
        print(f"Email generated with confidence: {email_result.confidence_score:.2f}")
        print(f"Subject: {email_data.get('subject')}")
        print(f"Personalization score: {email_data.get('personalization_score', 0):.2f}")
        print("Email preview:")
        print(email_data.get('body', '')[:200] + "...")
    
    # Example 4: Check cache performance
    cache_stats = cache_service.get_stats()
    print(f"\nCache Performance:")
    print(f"Hit rate: {cache_stats.hit_rate:.2%}")
    print(f"Total entries: {cache_stats.total_entries}")
    print(f"Memory usage: {cache_stats.memory_usage_mb:.1f} MB")

if __name__ == "__main__":
    main()

```

### Performance Monitoring Example

```python
#!/usr/bin/env python3
"""Monitor AI service and caching performance with refactored architecture."""

from services.ai_service import AIService
from services.caching_service import CachingService
from utils.configuration_service import ConfigurationService
import time

def monitor_performance():
    config_service = ConfigurationService()
    config = config_service.get_config()
    
    ai_service = AIService(config)
    cache_service = CachingService(config)
    
    # Perform some operations
    start_time = time.time()
    
    # Simulate AI operations
    for i in range(5):
        test_data = f"Test content {i}"
        result = ai_service.analyze_product(test_data)
        print(f"Operation {i+1}: Success={result.success}, Cached={result.cached}")
    
    end_time = time.time()
    
    # Get performance metrics
    ai_metrics = ai_service.get_performance_metrics()
    cache_stats = cache_service.get_stats()
    
    print(f"\n=== Performance Report ===")
    print(f"Total time: {end_time - start_time:.2f}s")
    print(f"AI operations: {ai_metrics.get('total_operations', 0)}")
    print(f"Average response time: {ai_metrics.get('average_response_time', 0):.2f}s")
    print(f"Success rate: {ai_metrics.get('success_rate', 0):.2%}")
    print(f"Cache hit rate: {cache_stats.hit_rate:.2%}")
    print(f"Cache entries: {cache_stats.total_entries}")
    print(f"Memory usage: {cache_stats.memory_usage_mb:.1f} MB")

if __name__ == "__main__":
    monitor_performance()
    
    print(f"\nAI Service Performance:")
    print(f"Total operations: {performance_metrics.get('total_operations', 0)}")
    print(f"Average response time: {performance_metrics.get('average_response_time', 0):.2f}s")
    print(f"Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}")

if __name__ == "__main__":
    main()
```

#### Enhanced Caching Example

```python
#!/usr/bin/env python3
"""Example of enhanced caching capabilities."""

from services.caching_service import CachingService
from utils.configuration_service import ConfigurationService

def demonstrate_caching():
    """Demonstrate multi-tier caching system."""
    config_service = ConfigurationService()
    config = config_service.get_config()
    
    # Initialize caching service
    cache_service = CachingService(config)
    
    # Basic caching operations
    cache_service.set("user_profile", {"name": "John", "role": "CEO"}, ttl=3600)
    cached_profile = cache_service.get("user_profile")
    
    # Cache with computation
    def expensive_computation():
        # Simulate expensive operation
        import time
        time.sleep(2)
        return {"result": "computed_value"}
    
    # Get or compute with caching
    result = cache_service.get_or_compute(
        key="expensive_operation",
        compute_func=expensive_computation,
        ttl=7200
    )
    
    # Cache warming for frequently accessed data
    warming_config = {
        "common_profiles": {
            "factory": lambda: load_common_profiles(),
            "ttl": 7200,
            "priority": 10
        },
        "product_templates": {
            "factory": lambda: load_product_templates(),
            "ttl": 3600,
            "priority": 5
        }
    }
    cache_service.warm_cache(warming_config)
    
    # Monitor cache performance
    stats = cache_service.get_stats()
    print(f"Cache Statistics:")
    print(f"  Memory usage: {stats.memory_usage_mb:.1f} MB")
    print(f"  Hit rate: {stats.hit_rate:.2%}")
    print(f"  Total entries: {stats.total_entries}")
    
    # Cache management
    if stats.memory_usage_mb > 100:  # If cache is too large
        cache_service.cleanup_expired()
        # Or clear specific patterns
        cache_service.invalidate_pattern("temp_*")

def load_common_profiles():
    """Load frequently accessed profiles."""
    return [{"name": "Profile 1"}, {"name": "Profile 2"}]

def load_product_templates():
    """Load email templates."""
    return {"cold_outreach": "Template content..."}

if __name__ == "__main__":
    demonstrate_caching()
    raw_product_content = """
    ProductHunt page content with product description,
    features, pricing, and team information...
    """
    
    product_result = ai_service.analyze_product(raw_product_content)
    
    if product_result.success:
        product = product_result.data
        print(f"Product: {product.name}")
        print(f"Description: {product.description}")
        print(f"Features: {', '.join(product.features[:3])}")
        print(f"Target Market: {product.target_market}")
    
    # Example: Generate personalized email
    prospect = Prospect(
        name="John Doe",
        role="Software Engineer",
        company="TechCorp",
        linkedin_url="https://linkedin.com/in/johndoe"
    )
    
    email_result = ai_service.generate_email(
        prospect=prospect,
        template_type=EmailTemplate.COLD_OUTREACH,
        linkedin_profile=profile if result.success else None
    )
    
    if email_result.success:
        email = email_result.data
        print(f"Generated email subject: {email.subject}")
        print(f"Personalization score: {email.personalization_score:.2f}")

if __name__ == "__main__":
    demonstrate_ai_service()
```

#### AI Service Customization

You can customize AI service behavior:

```python
# Parse with fallback data
fallback_data = {
    'name': 'John Doe',
    'current_role': 'Software Engineer',
    'skills': ['Python', 'JavaScript']
}

result = ai_service.parse_linkedin_profile(
    raw_html_content,
    fallback_data=fallback_data
)

# Check cache statistics
cache_stats = ai_service.get_cache_stats()
print(f"Cache entries: {cache_stats['total_entries']}")
print(f"Cache size: {cache_stats['cache_size_mb']} MB")

# Clear cache if needed
ai_service.clear_cache()

# Validate email content
email_content = "Your generated email content here..."
validation = ai_service.validate_email_content(email_content)
print(f"Email valid: {validation.is_valid}")
print(f"Spam score: {validation.spam_score:.2f}")
```

### Enhanced Product Analysis

The system now includes comprehensive product analysis that goes beyond basic information extraction.

#### Product Analysis Features

1. **Feature Extraction**: Identifies and categorizes product features
2. **Pricing Analysis**: Structures pricing models and tiers
3. **Market Position**: Analyzes competitive landscape
4. **Business Insights**: Extracts funding, team size, and growth metrics

#### Product Analysis Example

```python
#!/usr/bin/env python3
"""Enhanced product analysis with refactored AI service."""

from services.ai_service import AIService
from utils.configuration_service import ConfigurationService
from services.caching_service import CachingService

def analyze_product_comprehensive():
    config_service = ConfigurationService()
    config = config_service.get_config()
    
    ai_service = AIService(config)
    cache_service = CachingService(config)
    
    # Sample product content from ProductHunt or company website
    product_content = """
    ProductName: AI-Powered Analytics Platform
    Description: Transform your business data into actionable insights with our AI-driven analytics platform.
    Features: Real-time dashboards, predictive analytics, automated reporting, custom integrations
    Pricing: Starter $29/month, Professional $99/month, Enterprise custom pricing
    Team: 15 employees, Series A funded, $5M raised
    Founded: 2022, San Francisco
    """
    
    print("Analyzing product with enhanced AI service...")
    
    # Use caching for expensive analysis
    cache_key = f"product_analysis_{hash(product_content)}"
    cached_result = cache_service.get(cache_key)
    
    if cached_result:
        print("Using cached product analysis")
        analysis_result = cached_result
    else:
        analysis_result = ai_service.analyze_product(product_content)
        if analysis_result.success:
            cache_service.set(cache_key, analysis_result, ttl=7200)  # Cache for 2 hours
    
    if analysis_result.success:
        analysis = analysis_result.data
        print(f"Analysis confidence: {analysis_result.confidence_score:.2f}")
        print(f"Cached: {analysis_result.cached}")
        
        # Display structured analysis
        print("\n=== Product Analysis ===")
        print(f"Name: {analysis.get('name', 'Unknown')}")
        print(f"Category: {analysis.get('category', 'Unknown')}")
        print(f"Description: {analysis.get('description', '')[:100]}...")
        
        features = analysis.get('features', [])
        print(f"Key Features ({len(features)}):")
        for i, feature in enumerate(features[:5], 1):
            print(f"  {i}. {feature}")
        
        pricing = analysis.get('pricing', {})
        if pricing:
            print(f"Pricing Model: {pricing.get('model', 'Unknown')}")
            tiers = pricing.get('tiers', [])
            for tier in tiers[:3]:
                print(f"  - {tier.get('name', 'Tier')}: {tier.get('price', 'N/A')}")
        
        business_metrics = analysis.get('business_metrics', {})
        if business_metrics:
            print(f"Funding Stage: {business_metrics.get('funding_stage', 'Unknown')}")
            print(f"Team Size: {business_metrics.get('team_size', 'Unknown')}")
            print(f"Founded: {business_metrics.get('founded_year', 'Unknown')}")
        
        market_analysis = analysis.get('market_analysis', {})
        if market_analysis:
            print(f"Target Market: {market_analysis.get('target_market', 'Unknown')}")
            print(f"Market Size: {market_analysis.get('market_size', 'Unknown')}")
    
    else:
        print(f"Analysis failed: {analysis_result.error_message}")
    
    # Show cache performance
    cache_stats = cache_service.get_stats()
    print(f"\nCache Performance: {cache_stats.hit_rate:.1%} hit rate, {cache_stats.total_entries} entries")

if __name__ == "__main__":
    analyze_product_comprehensive()
"""Example of comprehensive product analysis."""

from services.product_analyzer import ProductAnalyzer
from utils.config import Config

def analyze_product_comprehensively():
    """Demonstrate comprehensive product analysis."""
    config = Config.from_env()
    analyzer = ProductAnalyzer(config)
    
    # Analyze a product from ProductHunt
    product_url = "https://www.producthunt.com/posts/example-product"
    company_website = "https://example-company.com"
    
    try:
        analysis = analyzer.analyze_product(product_url, company_website)
        
        print("=== PRODUCT ANALYSIS RESULTS ===")
        print(f"Product: {analysis.basic_info.name}")
        print(f"Description: {analysis.basic_info.description}")
        
        print(f"\nFeatures ({len(analysis.features)}):")
        for feature in analysis.features[:5]:
            print(f"  - {feature.name}: {feature.description}")
        
        print(f"\nPricing Model: {analysis.pricing.model}")
        if analysis.pricing.tiers:
            print("Pricing Tiers:")
            for tier in analysis.pricing.tiers:
                print(f"  - {tier.get('name', 'Unknown')}: {tier.get('price', 'N/A')}")
        
        print(f"\nTarget Market: {analysis.market_analysis.target_market}")
        print(f"Competitors: {', '.join(analysis.market_analysis.competitors[:3])}")
        
        if analysis.funding_info:
            print(f"Funding: {analysis.funding_info.get('status', 'Unknown')}")
        
        if analysis.team_size:
            print(f"Team Size: ~{analysis.team_size}")
        
    except Exception as e:
        print(f"Analysis failed: {e}")

if __name__ == "__main__":
    analyze_product_comprehensively()
```

### OpenAI Client Manager Usage

The system now includes a centralized OpenAI Client Manager for all AI operations.

#### Direct Client Manager Usage

```python
#!/usr/bin/env python3
"""Example of using the OpenAI Client Manager directly."""

from services.openai_client_manager import (
    get_client_manager, 
    configure_default_client,
    CompletionRequest,
    CompletionResponse
)
from utils.config import Config

def demonstrate_client_manager():
    """Demonstrate OpenAI Client Manager capabilities."""
    
    # Initialize client manager
    config = Config.from_env()
    configure_default_client(config)
    manager = get_client_manager()
    
    print("=== OpenAI Client Manager Demo ===")
    
    # Get client information
    client_info = manager.get_client_info()
    print(f"Client Type: {client_info['client_type']}")
    print(f"Model: {client_info['model_name']}")
    print(f"Endpoint: {client_info['endpoint']}")
    
    # Simple completion
    try:
        simple_response = manager.make_simple_completion([
            {"role": "user", "content": "Generate a professional email subject line for a job inquiry"}
        ])
        print(f"\nSimple Completion: {simple_response}")
    except Exception as e:
        print(f"Simple completion failed: {e}")
    
    # Structured completion request
    try:
        request = CompletionRequest(
            messages=[
                {"role": "system", "content": "You are a professional email writer."},
                {"role": "user", "content": "Write a brief, professional email introduction for a software engineer reaching out to a startup CEO."}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        response = manager.make_completion(request)
        
        if response.success:
            print(f"\nStructured Completion:")
            print(f"Content: {response.content}")
            print(f"Model Used: {response.model}")
            print(f"Tokens Used: {response.usage}")
            print(f"Finish Reason: {response.finish_reason}")
        else:
            print(f"Structured completion failed: {response.error_message}")
            
    except Exception as e:
        print(f"Structured completion error: {e}")
    
    # Multiple client configurations (advanced)
    try:
        # Configure a second client for parsing operations
        parsing_config = Config.from_env()
        manager.configure(parsing_config, "parsing_client")
        
        # Use specific client
        parsing_response = manager.make_simple_completion(
            messages=[{"role": "user", "content": "Parse this data: John Smith, Software Engineer"}],
            client_id="parsing_client"
        )
        print(f"\nParsing Client Response: {parsing_response}")
        
        # List all configured clients
        clients = manager.list_clients()
        print(f"Configured Clients: {clients}")
        
    except Exception as e:
        print(f"Multi-client configuration failed: {e}")

if __name__ == "__main__":
    demonstrate_client_manager()
```

### Advanced Caching System

The system includes a comprehensive caching service that significantly improves performance and reduces API costs.

#### Caching Features

1. **Multi-Tier Architecture**: In-memory and persistent file-based caching
2. **Automatic Cache Management**: LRU eviction and TTL-based expiration
3. **Cache Warming**: Pre-populate cache with frequently accessed data
4. **Pattern-Based Invalidation**: Bulk invalidation using wildcards
5. **Performance Monitoring**: Detailed cache statistics and hit rates

#### Basic Caching Usage

```python
#!/usr/bin/env python3
"""Example of using the caching service."""

from services.caching_service import CachingService
from utils.config import Config

def demonstrate_caching():
    """Demonstrate caching service capabilities."""
    config = Config.from_env()
    cache = CachingService(config)
    
    # Basic cache operations
    cache.set("user_profile_123", {"name": "John Doe", "role": "Engineer"}, ttl=3600)
    
    # Retrieve cached data
    profile = cache.get("user_profile_123")
    if profile:
        print(f"Cached profile: {profile['name']}")
    
    # Get-or-set pattern for expensive operations
    def expensive_operation():
        print("Performing expensive LinkedIn scraping...")
        return {"name": "Jane Smith", "skills": ["Python", "AI"]}
    
    profile = cache.get_or_set(
        "linkedin_profile_456",
        expensive_operation,
        ttl=7200  # Cache for 2 hours
    )
    
    # Cache statistics
    stats = cache.get_stats()
    print(f"Cache hit rate: {stats.hit_rate:.2%}")
    print(f"Memory usage: {stats.memory_usage_mb:.1f} MB")
    print(f"Total entries: {stats.total_entries}")

if __name__ == "__main__":
    demonstrate_caching()
```

#### Cache Warming Example

```python
#!/usr/bin/env python3
"""Example of cache warming for improved performance."""

from services.caching_service import CachingService
from utils.config import Config

def warm_cache_example():
    """Demonstrate cache warming capabilities."""
    config = Config.from_env()
    cache = CachingService(config)
    
    # Define warming configuration
    warming_config = {
        "frequent_companies": {
            "factory": lambda: load_popular_companies(),
            "ttl": 7200,  # 2 hours
            "priority": 10
        },
        "common_profiles": {
            "factory": lambda: load_common_linkedin_profiles(),
            "ttl": 3600,  # 1 hour
            "priority": 8
        },
        "email_templates": {
            "factory": lambda: load_email_templates(),
            "ttl": 86400,  # 24 hours
            "priority": 5
        }
    }
    
    # Warm the cache (runs in background threads)
    print("Starting cache warming...")
    cache.warm_cache(warming_config)
    print("Cache warming completed!")
    
    # Check results
    stats = cache.get_stats()
    print(f"Cache now contains {stats.total_entries} entries")

def load_popular_companies():
    """Mock function to load popular companies."""
    return ["TechCorp", "StartupXYZ", "InnovateCo"]

def load_common_linkedin_profiles():
    """Mock function to load common profiles."""
    return [{"name": "John Doe", "role": "Engineer"}]

def load_email_templates():
    """Mock function to load email templates."""
    return {"cold_outreach": "Hi {name}, I found your company..."}

if __name__ == "__main__":
    warm_cache_example()
```

#### Cache Management and Monitoring

```python
#!/usr/bin/env python3
"""Example of advanced cache management."""

from services.caching_service import CachingService
from utils.config import Config

def manage_cache():
    """Demonstrate cache management capabilities."""
    config = Config.from_env()
    cache = CachingService(config)
    
    # Add some test data
    cache.set("linkedin_profile_1", {"name": "John"}, ttl=3600)
    cache.set("linkedin_profile_2", {"name": "Jane"}, ttl=3600)
    cache.set("company_data_1", {"name": "TechCorp"}, ttl=7200)
    
    # Pattern-based invalidation
    print("Invalidating LinkedIn profiles...")
    cache.invalidate_pattern("linkedin_profile_*")
    
    # Check what remains
    remaining = cache.get("company_data_1")
    print(f"Company data still cached: {remaining is not None}")
    
    # Clean up expired entries
    cache.cleanup_expired()
    
    # Get detailed statistics
    stats = cache.get_stats()
    print(f"Final cache statistics:")
    print(f"  Hit rate: {stats.hit_rate:.2%}")
    print(f"  Memory usage: {stats.memory_usage_mb:.1f} MB")
    print(f"  Total entries: {stats.total_entries}")
    print(f"  Evictions: {stats.eviction_count}")

if __name__ == "__main__":
    manage_cache()
```

### Enhanced Email Personalization

The system now uses AI-structured data to create highly personalized emails.

#### Enhanced Personalization Features

1. **AI-Structured Context**: Uses processed data optimized for personalization
2. **Product Insights**: Incorporates detailed product analysis
3. **Business Context**: Includes funding, growth stage, and market position
4. **LinkedIn Insights**: Uses structured professional background
5. **Centralized AI Processing**: All AI operations use the unified client manager
6. **Intelligent Caching**: Expensive AI operations are cached for improved performance

#### Enhanced Email Generation Example

```python
#!/usr/bin/env python3
"""Example of enhanced email generation with AI-structured data."""

from services.email_generator import EmailGenerator, EmailTemplate
from services.notion_manager import NotionDataManager
from utils.config import Config

def generate_enhanced_emails():
    """Demonstrate enhanced email generation."""
    config = Config.from_env()
    email_generator = EmailGenerator(config)
    notion_manager = NotionDataManager(config)
    
    # Get prospect ID from Notion (this would be a real prospect ID)
    prospect_id = "example-prospect-id"
    
    try:
        # Generate enhanced email using AI-structured data from Notion
        email_content = email_generator.generate_enhanced_outreach_email(
            prospect_id=prospect_id,
            notion_manager=notion_manager,
            template_type=EmailTemplate.COLD_OUTREACH,
            additional_context={
                "referral_source": "ProductHunt discovery",
                "specific_interest": "AI-powered automation tools"
            }
        )
        
        print("=== ENHANCED EMAIL GENERATED ===")
        print(f"Subject: {email_content.subject}")
        print(f"Personalization Score: {email_content.personalization_score:.2f}")
        print(f"\nBody:\n{email_content.body}")
        
        # The email now includes:
        # - AI-structured product summary
        # - Business insights (funding, growth stage)
        # - LinkedIn professional summary
        # - Personalized talking points
        
    except Exception as e:
        print(f"Enhanced email generation failed: {e}")
        print("💡 Tip: Run 'python debug_email_generation.py' to diagnose email generation issues")

if __name__ == "__main__":
    generate_enhanced_emails()
```

## 🔧 Azure OpenAI Configuration

### Setting Up Azure OpenAI

Azure OpenAI provides enterprise-grade AI services with better reliability and security.

#### Basic Azure OpenAI Setup

```bash
# Azure OpenAI environment variables
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

#### Advanced Azure OpenAI Configuration

```python
#!/usr/bin/env python3
"""Advanced Azure OpenAI configuration example."""

from utils.config import Config
from services.email_generator import EmailGenerator
from services.ai_parser import AIParser

def configure_azure_openai():
    """Configure Azure OpenAI for different services."""
    
    # Load configuration
    config = Config.from_env()
    
    # Verify Azure OpenAI is configured
    if not config.use_azure_openai:
        print("Azure OpenAI not enabled. Set USE_AZURE_OPENAI=true")
        return
    
    print("Azure OpenAI Configuration:")
    print(f"Endpoint: {config.azure_openai_endpoint}")
    print(f"Deployment: {config.azure_openai_deployment_name}")
    print(f"API Version: {config.azure_openai_api_version}")
    
    # Test email generation with Azure OpenAI
    try:
        email_generator = EmailGenerator(config)
        print("✅ Email Generator initialized with Azure OpenAI")
    except Exception as e:
        print(f"❌ Email Generator failed: {e}")
    
    # Test AI parsing with Azure OpenAI
    try:
        ai_parser = AIParser(config)
        print("✅ AI Parser initialized with Azure OpenAI")
    except Exception as e:
        print(f"❌ AI Parser failed: {e}")

if __name__ == "__main__":
    configure_azure_openai()
```

#### Model Selection for Different Tasks

```bash
# Optimize models for different tasks
EMAIL_GENERATION_MODEL=gpt-4          # Best quality for emails
AI_PARSING_MODEL=gpt-4               # Best accuracy for parsing
PRODUCT_ANALYSIS_MODEL=gpt-3.5-turbo # Cost-effective for analysis

# Alternative cost-optimized setup
EMAIL_GENERATION_MODEL=gpt-3.5-turbo
AI_PARSING_MODEL=gpt-3.5-turbo
PRODUCT_ANALYSIS_MODEL=gpt-3.5-turbo
```

## 📧 Email Sending with Resend

### Setting Up Resend for Email Delivery

Resend provides reliable email delivery with tracking and analytics.

#### Basic Resend Configuration

```bash
# Resend API configuration
RESEND_API_KEY=re_your_resend_api_key
SENDER_EMAIL=your-name@yourdomain.com
SENDER_NAME=Your Name
REPLY_TO_EMAIL=your-name@yourdomain.com

# Email sending settings
RESEND_REQUESTS_PER_MINUTE=100
AUTO_SEND_EMAILS=false
EMAIL_REVIEW_REQUIRED=true
```

#### Email Sending Example

```python
#!/usr/bin/env python3
"""Example of email sending with Resend."""

from services.email_sender import EmailSender
from services.notion_manager import NotionDataManager
from utils.config import Config

def send_emails_with_resend():
    """Demonstrate email sending with Resend."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    email_sender = EmailSender(config, notion_manager)
    
    # Send a single email
    result = email_sender.send_email(
        recipient_email="prospect@example.com",
        subject="Discovered your product on ProductHunt",
        html_body="""
        <html>
        <body>
            <p>Hi John,</p>
            <p>I discovered your innovative AI tool on ProductHunt and was impressed by your approach to automation...</p>
            <p>Best regards,<br>Your Name</p>
        </body>
        </html>
        """,
        text_body="Hi John,\n\nI discovered your innovative AI tool on ProductHunt...",
        tags=["job-prospect", "cold-outreach"],
        prospect_id="notion-prospect-id"
    )
    
    if result.status == "sent":
        print(f"✅ Email sent successfully! ID: {result.email_id}")
    else:
        print(f"❌ Email failed: {result.error_message}")
    
    # Get sending statistics
    stats = email_sender.get_sending_stats()
    print(f"\nSending Statistics:")
    print(f"Total Sent: {stats.total_sent}")
    print(f"Delivery Rate: {stats.delivery_rate:.2%}")
    print(f"Open Rate: {stats.open_rate:.2%}")

if __name__ == "__main__":
    send_emails_with_resend()
```

#### Bulk Email Sending with Rate Limiting

```python
#!/usr/bin/env python3
"""Example of bulk email sending with proper rate limiting."""

from services.email_generator import EmailGenerator, EmailTemplate
from services.email_sender import EmailSender
from services.notion_manager import NotionDataManager
from utils.config import Config
import time

def send_bulk_emails():
    """Send emails to multiple prospects with rate limiting."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    email_generator = EmailGenerator(config)
    email_sender = EmailSender(config, notion_manager)
    
    # Get prospect IDs from Notion (example)
    prospect_ids = [
        "prospect-id-1",
        "prospect-id-2", 
        "prospect-id-3"
    ]
    
    # Generate and send emails with rate limiting
    results = email_generator.generate_and_send_bulk_emails(
        prospect_ids=prospect_ids,
        notion_manager=notion_manager,
        email_sender=email_sender,
        template_type=EmailTemplate.COLD_OUTREACH,
        delay_between_emails=2.0,  # 2 second delay between emails
        additional_context={
            "discovery_source": "ProductHunt",
            "outreach_goal": "job opportunities"
        }
    )
    
    # Process results
    successful_sends = [r for r in results if r.get("sent", False)]
    failed_sends = [r for r in results if not r.get("sent", False)]
    
    print(f"Bulk Email Results:")
    print(f"✅ Successful: {len(successful_sends)}")
    print(f"❌ Failed: {len(failed_sends)}")
    
    # Show detailed results
    for result in results:
        prospect_id = result["prospect_id"]
        if result.get("sent"):
            email_id = result["send_result"]["email_id"]
            print(f"  {prospect_id}: Sent (ID: {email_id})")
        else:
            error = result.get("error", "Unknown error")
            print(f"  {prospect_id}: Failed ({error})")

if __name__ == "__main__":
    send_bulk_emails()
```

#### Sending Already Generated Emails

```python
#!/usr/bin/env python3
"""Example of sending already generated emails in batches."""

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def send_generated_emails():
    """Send emails that have already been generated and stored in Notion."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Get prospects with generated but unsent emails
    unsent_prospect_data = controller.notion_manager.get_prospects_by_email_status(
        generation_status="Generated",
        delivery_status="Not Sent"
    )
    
    if not unsent_prospect_data:
        print("No prospects with generated but unsent emails found")
        return
    
    # Extract prospect IDs
    prospect_ids = [data['id'] for data in unsent_prospect_data if data.get('email')]
    
    print(f"Found {len(prospect_ids)} prospects with generated emails to send")
    
    # Send emails in batches with rate limiting
    results = controller.send_prospect_emails(
        prospect_ids=prospect_ids,
        batch_size=3,    # Send 3 emails per batch
        delay=30         # Wait 30 seconds between batches
    )
    
    # Display results
    print(f"\nEmail Sending Results:")
    print(f"✅ Successfully sent: {results['total_sent']}")
    print(f"❌ Failed to send: {results['total_failed']}")
    
    # Show details of successful sends
    if results['successful']:
        print(f"\nSuccessful sends:")
        for result in results['successful']:
            print(f"  • {result['prospect_name']} at {result['email']} - ID: {result['email_id']}")
    
    # Show details of failed sends
    if results['failed']:
        print(f"\nFailed sends:")
        for result in results['failed']:
            print(f"  • {result['prospect_name']}: {result['error']}")

if __name__ == "__main__":
    send_generated_emails()
```

#### Email Delivery Tracking

```python
#!/usr/bin/env python3
"""Example of email delivery tracking."""

from services.email_sender import EmailSender
from services.notion_manager import NotionDataManager
from utils.config import Config
import time

def track_email_delivery():
    """Track email delivery status."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    email_sender = EmailSender(config, notion_manager)
    
    # Send an email
    result = email_sender.send_email(
        recipient_email="test@example.com",
        subject="Test Email with Tracking",
        html_body="<p>This is a test email with delivery tracking.</p>",
        prospect_id="test-prospect-id"
    )
    
    if result.status == "sent":
        email_id = result.email_id
        print(f"Email sent with ID: {email_id}")
        
        # Track delivery status
        print("Tracking delivery status...")
        for i in range(10):  # Check for 10 iterations
            time.sleep(5)  # Wait 5 seconds
            
            delivery_status = email_sender.track_delivery(email_id)
            if delivery_status:
                print(f"Status: {delivery_status.status} at {delivery_status.timestamp}")
                
                if delivery_status.status in ["delivered", "opened", "clicked"]:
                    print("✅ Email successfully delivered!")
                    break
                elif delivery_status.status in ["bounced", "complained"]:
                    print("❌ Email delivery failed!")
                    break
            else:
                print("No delivery status available yet...")
    
    # Get comprehensive delivery report
    report = email_sender.get_delivery_report()
    print(f"\nDelivery Report:")
    print(f"Total Tracked Emails: {report['total_tracked_emails']}")
    print(f"Status Breakdown: {report['status_breakdown']}")

if __name__ == "__main__":
    track_email_delivery()
```

## 🔔 Notification System Examples

### Setting Up Automated Notifications

```python
#!/usr/bin/env python3
"""Example of setting up automated notifications for campaign monitoring."""

from services.notification_manager import NotificationManager
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def setup_notifications():
    """Set up automated notification system."""
    config = Config.from_env()
    
    # Enable notifications in configuration
    config.enable_notifications = True
    config.notification_methods = ['notion']  # Available: notion, email, webhook
    
    # Optional: User mention settings for enhanced notifications (future feature)
    config.notion_user_id = 'your-notion-user-id'  # For @mentions in notifications
    config.user_email = 'your-email@domain.com'    # For @remind notifications
    
    controller = ProspectAutomationController(config)
    
    # The controller automatically initializes notification manager
    if controller.notification_manager:
        print("✅ Notification manager initialized successfully")
        
        # Test campaign completion notification
        campaign_data = {
            'name': 'Test Campaign',
            'companies_processed': 10,
            'prospects_found': 25,
            'success_rate': 0.85,
            'duration_minutes': 15.5,
            'status': 'Completed'
        }
        
        success = controller.notification_manager.send_campaign_completion_notification(campaign_data)
        print(f"Campaign completion notification sent: {success}")
        
        # Test error alert
        error_data = {
            'component': 'Test Component',
            'error_message': 'This is a test error',
            'campaign_name': 'Test Campaign',
            'company_name': 'Test Company'
        }
        
        success = controller.notification_manager.send_error_alert(error_data)
        print(f"Error alert notification sent: {success}")
        
    else:
        print("❌ Notification manager not available")

if __name__ == "__main__":
    setup_notifications()
```

### Campaign Monitoring with Notifications

```python
#!/usr/bin/env python3
"""Example of running campaigns with automated notification alerts."""

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from datetime import datetime

def run_monitored_campaign():
    """Run a campaign with comprehensive notification monitoring."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    campaign_name = f"Monitored Campaign - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    try:
        print(f"Starting monitored campaign: {campaign_name}")
        
        # Run discovery with automatic notifications
        results = controller.run_discovery_pipeline(
            limit=10,
            campaign_name=campaign_name
        )
        
        # Campaign completion notification is sent automatically by the controller
        print("✅ Campaign completed successfully with notifications")
        
        # Display results
        summary = results['summary']
        print(f"Companies processed: {summary['companies_processed']}")
        print(f"Prospects found: {summary['prospects_found']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        # Manual daily summary notification
        if controller.notification_manager:
            daily_stats = {
                'campaigns_run': 1,
                'companies_processed': summary['companies_processed'],
                'prospects_found': summary['prospects_found'],
                'emails_generated': summary.get('emails_generated', 0),
                'success_rate': summary['success_rate'],
                'processing_time_minutes': summary.get('duration_seconds', 0) / 60,
                'api_calls': summary.get('total_tokens', 0) // 10,
                'top_campaign': campaign_name
            }
            
            success = controller.notification_manager.send_daily_summary_notification(daily_stats)
            print(f"Daily summary notification sent: {success}")
        
        return results
        
    except Exception as e:
        print(f"Campaign failed: {e}")
        
        # Error notification is sent automatically by the controller
        # Additional manual error notification if needed
        if controller.notification_manager:
            error_data = {
                'component': 'Campaign Runner',
                'error_message': str(e),
                'campaign_name': campaign_name,
                'company_name': 'N/A'
            }
            controller.notification_manager.send_error_alert(error_data)
        
        raise

if __name__ == "__main__":
    run_monitored_campaign()
```

### Weekly Report Generation

```python
#!/usr/bin/env python3
"""Example of generating weekly performance reports with notifications."""

from services.notification_manager import NotificationManager
from services.notion_manager import NotionDataManager
from utils.config import Config
from datetime import datetime, timedelta

def generate_weekly_report():
    """Generate and send weekly performance report."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    notification_manager = NotificationManager(config, notion_manager)
    
    # Calculate weekly statistics (this would typically query your databases)
    weekly_stats = {
        'total_campaigns': 15,
        'total_companies': 150,
        'total_prospects': 450,
        'total_emails': 380,
        'avg_success_rate': 0.87,
        'total_processing_time': 12.5,  # hours
        'total_api_calls': 15000,
        'best_day': 'Wednesday',
        'most_active_campaign': 'ProductHunt Discovery - Daily'
    }
    
    # Send weekly report notification
    success = notification_manager.send_weekly_report(weekly_stats)
    
    if success:
        print("✅ Weekly report sent successfully")
        print(f"Report covers {weekly_stats['total_campaigns']} campaigns")
        print(f"Total prospects found: {weekly_stats['total_prospects']}")
        print(f"Average success rate: {weekly_stats['avg_success_rate']:.1%}")
    else:
        print("❌ Failed to send weekly report")

if __name__ == "__main__":
    generate_weekly_report()
```

### Custom Notification Integration

```python
#!/usr/bin/env python3
"""Example of extending the notification system with custom methods."""

from services.notification_manager import NotificationManager, NotificationData, NotificationType
from utils.config import Config
from datetime import datetime

class CustomNotificationManager(NotificationManager):
    """Extended notification manager with custom delivery methods."""
    
    def __init__(self, config, notion_manager=None):
        super().__init__(config, notion_manager)
        # Add custom notification methods
        self.notification_methods.extend(['slack', 'discord'])
    
    def _send_slack_notification(self, notification: NotificationData) -> bool:
        """Send notification to Slack (example implementation)."""
        try:
            # Example Slack webhook integration
            import requests
            
            slack_webhook_url = getattr(self.config, 'slack_webhook_url', None)
            if not slack_webhook_url:
                return False
            
            payload = {
                "text": f"{notification.title}\n{notification.message}",
                "username": "Job Prospect Bot",
                "icon_emoji": ":robot_face:"
            }
            
            response = requests.post(slack_webhook_url, json=payload)
            
            if response.status_code == 200:
                self.logger.info(f"Sent Slack notification: {notification.title}")
                return True
            else:
                self.logger.error(f"Failed to send Slack notification: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def _send_discord_notification(self, notification: NotificationData) -> bool:
        """Send notification to Discord (example implementation)."""
        try:
            # Example Discord webhook integration
            import requests
            
            discord_webhook_url = getattr(self.config, 'discord_webhook_url', None)
            if not discord_webhook_url:
                return False
            
            payload = {
                "content": f"**{notification.title}**\n```\n{notification.message}\n```"
            }
            
            response = requests.post(discord_webhook_url, json=payload)
            
            if response.status_code == 204:
                self.logger.info(f"Sent Discord notification: {notification.title}")
                return True
            else:
                self.logger.error(f"Failed to send Discord notification: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send Discord notification: {str(e)}")
            return False
    
    def _send_notification(self, notification: NotificationData) -> bool:
        """Override to include custom notification methods."""
        success = False
        
        for method in self.notification_methods:
            if method == 'notion':
                success |= self._send_notion_notification(notification)
            elif method == 'email':
                success |= self._send_email_notification(notification)
            elif method == 'webhook':
                success |= self._send_webhook_notification(notification)
            elif method == 'slack':
                success |= self._send_slack_notification(notification)
            elif method == 'discord':
                success |= self._send_discord_notification(notification)
        
        return success

def test_custom_notifications():
    """Test custom notification methods."""
    config = Config.from_env()
    
    # Add custom webhook URLs to config
    config.slack_webhook_url = "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    config.discord_webhook_url = "https://discord.com/api/webhooks/YOUR/DISCORD/WEBHOOK"
    
    # Initialize custom notification manager
    custom_manager = CustomNotificationManager(config)
    
    # Test campaign completion with multiple delivery methods
    campaign_data = {
        'name': 'Multi-Channel Test Campaign',
        'companies_processed': 5,
        'prospects_found': 15,
        'success_rate': 0.90,
        'duration_minutes': 8.5,
        'status': 'Completed'
    }
    
    success = custom_manager.send_campaign_completion_notification(campaign_data)
    print(f"Multi-channel notification sent: {success}")

if __name__ == "__main__":
    test_custom_notifications()
```

## 📊 Dashboard and Monitoring Examples

### Setting Up Campaign Monitoring

```python
#!/usr/bin/env python3
"""Example of setting up campaign monitoring with dashboard tracking."""

from services.notion_manager import NotionDataManager, CampaignProgress, CampaignStatus
from utils.config import Config
from datetime import datetime

def setup_campaign_monitoring():
    """Set up campaign monitoring dashboard."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    
    # Create dashboard (run once)
    dashboard_info = notion_manager.create_campaign_dashboard()
    
    print("Dashboard created successfully!")
    print(f"Dashboard ID: {dashboard_info['dashboard_id']}")
    print(f"Campaigns DB: {dashboard_info['campaigns_db']}")
    print(f"Logs DB: {dashboard_info['logs_db']}")
    print(f"Status DB: {dashboard_info['status_db']}")
    
    # Create a new campaign
    campaign_data = CampaignProgress(
        campaign_id="campaign-001",
        name="ProductHunt Discovery - Week 1",
        status=CampaignStatus.RUNNING,
        start_time=datetime.now(),
        current_step="Discovering companies",
        companies_target=50,
        companies_processed=0,
        prospects_found=0,
        emails_generated=0,
        success_rate=0.0
    )
    
    # Track campaign in dashboard
    campaign_page_id = notion_manager.create_campaign(
        campaign_data=campaign_data,
        campaigns_db_id=dashboard_info['campaigns_db']
    )
    
    print(f"Campaign created: {campaign_page_id}")
    return dashboard_info, campaign_page_id

if __name__ == "__main__":
    setup_campaign_monitoring()
```

### Real-Time Progress Tracking

```python
#!/usr/bin/env python3
"""Example of real-time progress tracking during discovery."""

from controllers.prospect_automation_controller import ProspectAutomationController
from services.notion_manager import CampaignProgress, CampaignStatus
from utils.config import Config
from datetime import datetime
import time

def run_monitored_discovery():
    """Run discovery with real-time progress tracking."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # The controller now handles campaign tracking automatically
    # Just run the discovery pipeline with a campaign name
    campaign_name = f"Monitored Discovery - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    try:
        # Run discovery with automatic progress tracking
        results = controller.run_discovery_pipeline(
            limit=5,
            campaign_name=campaign_name
        )
        
        # Display results
        summary = results['summary']
        print(f"Campaign completed successfully!")
        print(f"Companies processed: {summary['companies_processed']}")
        print(f"Prospects found: {summary['prospects_found']}")
        print(f"Emails found: {summary['emails_found']}")
        print(f"Success rate: {summary['success_rate']:.1%}")
        
        # Get current campaign progress
        progress = controller.get_campaign_progress()
        if progress:
            print(f"Campaign: {progress['name']}")
            print(f"Status: {progress['status']}")
            print(f"Progress: {progress['progress_percentage']:.1f}%")
            print(f"Current step: {progress['current_step']}")
            print(f"Error count: {progress['error_count']}")
        
        return results
        
    except Exception as e:
        print(f"Campaign failed: {e}")
        
        # The controller automatically handles campaign failure tracking
        # when exceptions occur in run_discovery_pipeline

if __name__ == "__main__":
    run_monitored_discovery()
```

### System Health Monitoring

```python
#!/usr/bin/env python3
"""Example of system health monitoring and status updates."""

from services.notion_manager import NotionDataManager
from utils.config import Config
import time
import random

def monitor_system_health():
    """Monitor and update system component health."""
    config = Config.from_env()
    notion_manager = NotionDataManager(config)
    
    components = [
        "ProductHunt Scraper",
        "AI Parser",
        "Email Finder", 
        "LinkedIn Scraper",
        "Email Generator",
        "Email Sender",
        "Notion Manager"
    ]
    
    print("Starting system health monitoring...")
    
    for component in components:
        # Simulate health check
        is_healthy = random.choice([True, True, True, False])  # 75% healthy
        api_quota = random.uniform(0.1, 0.9)  # Random quota usage
        error_count = random.randint(0, 5) if not is_healthy else 0
        success_rate = random.uniform(0.8, 1.0) if is_healthy else random.uniform(0.3, 0.7)
        
        status = "Healthy" if is_healthy else "Warning" if error_count < 3 else "Error"
        
        details = f"Health check completed. "
        if not is_healthy:
            details += f"Detected {error_count} errors. "
        details += f"API quota: {api_quota:.1%}"
        
        # Update system status
        success = notion_manager.update_system_status(
            status_db_id=config.status_db_id,
            component=component,
            status=status,
            details=details,
            api_quota_used=api_quota,
            error_count=error_count,
            success_rate=success_rate
        )
        
        if success:
            print(f"✓ {component}: {status} (Success rate: {success_rate:.1%})")
        else:
            print(f"✗ Failed to update {component} status")
        
        time.sleep(1)  # Brief delay between updates
    
    print("System health monitoring completed!")

if __name__ == "__main__":
    monitor_system_health()
```

### API Usage Analytics

```python
#!/usr/bin/env python3
"""Example of API usage analytics and cost estimation."""

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def analyze_api_usage():
    """Analyze API usage and cost estimation."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Get daily stats which now include API call estimation
    daily_stats = controller._calculate_daily_stats()
    
    print("API Usage Analytics:")
    print(f"Estimated API calls today: {daily_stats.get('api_calls', 0)}")
    print(f"Campaigns run: {daily_stats.get('campaigns_run', 0)}")
    print(f"Companies processed: {daily_stats.get('companies_processed', 0)}")
    print(f"Prospects found: {daily_stats.get('prospects_found', 0)}")
    print(f"Emails generated: {daily_stats.get('emails_generated', 0)}")
    
    # API call breakdown (based on the estimation logic)
    campaigns = daily_stats.get('campaigns_run', 0)
    companies = daily_stats.get('companies_processed', 0)
    prospects = daily_stats.get('prospects_found', 0)
    emails = daily_stats.get('emails_generated', 0)
    
    print("\nAPI Call Breakdown:")
    print(f"Campaign setup: {campaigns * 5} calls")
    print(f"Company processing: {companies * 15} calls")
    print(f"Prospect processing: {prospects * 8} calls")
    print(f"Email generation: {emails * 3} calls")
    
    # Estimated cost (assuming $0.002 per 1K tokens, ~10 tokens per API call)
    estimated_tokens = daily_stats.get('api_calls', 0) * 10
    estimated_cost = (estimated_tokens / 1000) * 0.002
    print(f"\nEstimated cost: ${estimated_cost:.4f}")

if __name__ == "__main__":
    analyze_api_usage()
```

## 🔄 Common Workflows

### Workflow 1: Complete Discovery Pipeline

```python
#!/usr/bin/env python3
"""Complete discovery workflow with error handling."""

import sys
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging, get_logger

def main():
    # Setup logging
    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    
    try:
        # Initialize system
        config = Config.from_env()
        config.validate()
        controller = ProspectAutomationController(config)
        
        logger.info("Starting complete discovery pipeline")
        
        # Run discovery with progress tracking
        results = controller.run_discovery_pipeline(limit=25)
        
        # Process results
        summary = results['summary']
        logger.info(f"Discovery completed:")
        logger.info(f"  Companies processed: {summary['companies_processed']}")
        logger.info(f"  Prospects found: {summary['prospects_found']}")
        logger.info(f"  Emails discovered: {summary['emails_found']}")
        logger.info(f"  Success rate: {summary['success_rate']:.1f}%")
        
        # Generate summary report
        with open('discovery_report.txt', 'w') as f:
            f.write(f"Discovery Report - {results['timestamp']}\n")
            f.write("=" * 50 + "\n")
            f.write(f"Companies Processed: {summary['companies_processed']}\n")
            f.write(f"Prospects Found: {summary['prospects_found']}\n")
            f.write(f"Emails Found: {summary['emails_found']}\n")
            f.write(f"LinkedIn Profiles: {summary['linkedin_profiles_extracted']}\n")
            f.write(f"Success Rate: {summary['success_rate']:.1f}%\n")
            f.write(f"Duration: {summary['duration_seconds']:.1f} seconds\n")
        
        logger.info("Discovery report saved to discovery_report.txt")
        
    except Exception as e:
        logger.error(f"Discovery pipeline failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Workflow 2: Targeted Company Research

```python
#!/usr/bin/env python3
"""Research specific companies of interest."""

from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData
from utils.config import Config
from datetime import datetime

def research_companies(company_list):
    """Research a list of specific companies."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    results = []
    
    for company_info in company_list:
        print(f"\nResearching {company_info['name']}...")
        
        # Create company data object
        company_data = CompanyData(
            name=company_info['name'],
            domain=company_info['domain'],
            product_url=company_info.get('product_url', ''),
            description=f"Targeted research for {company_info['name']}",
            launch_date=datetime.now()
        )
        
        try:
            # Process the company
            prospects = controller.process_company(company_data)
            
            result = {
                'company': company_info['name'],
                'prospects_found': len(prospects),
                'prospects': prospects,
                'success': True
            }
            
            print(f"  ✅ Found {len(prospects)} prospects")
            
        except Exception as e:
            result = {
                'company': company_info['name'],
                'prospects_found': 0,
                'prospects': [],
                'success': False,
                'error': str(e)
            }
            
            print(f"  ❌ Error: {e}")
        
        results.append(result)
    
    return results

def main():
    # Define companies to research
    target_companies = [
        {
            'name': 'Acme Corporation',
            'domain': 'acme.com',
            'product_url': 'https://producthunt.com/posts/acme-product'
        },
        {
            'name': 'TechStart Inc',
            'domain': 'techstart.io'
        },
        {
            'name': 'Innovation Labs',
            'domain': 'innovationlabs.com'
        }
    ]
    
    print("Starting targeted company research...")
    results = research_companies(target_companies)
    
    # Summary
    total_prospects = sum(r['prospects_found'] for r in results)
    successful_companies = sum(1 for r in results if r['success'])
    
    print(f"\n{'='*50}")
    print("Research Summary:")
    print(f"Companies researched: {len(results)}")
    print(f"Successful: {successful_companies}")
    print(f"Total prospects found: {total_prospects}")
    print(f"Success rate: {(successful_companies/len(results)*100):.1f}%")

if __name__ == "__main__":
    main()
```

### Workflow 3: Batch Processing with Monitoring

```python
#!/usr/bin/env python3
"""Batch processing with comprehensive monitoring."""

import time
from datetime import datetime
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData
from utils.config import Config

class BatchMonitor:
    """Monitor batch processing progress."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_prospects = 0
    
    def progress_callback(self, batch_progress):
        """Handle progress updates."""
        self.processed_count = batch_progress.processed_companies
        self.success_count = batch_progress.successful_companies
        self.error_count = batch_progress.processed_companies - batch_progress.successful_companies
        self.total_prospects = batch_progress.total_prospects
        
        # Calculate metrics
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = self.processed_count / elapsed if elapsed > 0 else 0
        eta_seconds = (batch_progress.total_companies - self.processed_count) / rate if rate > 0 else 0
        
        # Display progress
        print(f"\n{'='*60}")
        print(f"Batch Progress Update - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Batch ID: {batch_progress.batch_id}")
        print(f"Status: {batch_progress.status.value}")
        print(f"Progress: {self.processed_count}/{batch_progress.total_companies} companies")
        print(f"Success Rate: {(self.success_count/max(1, self.processed_count)*100):.1f}%")
        print(f"Total Prospects: {self.total_prospects}")
        print(f"Processing Rate: {rate:.2f} companies/second")
        if eta_seconds > 0:
            print(f"ETA: {eta_seconds/60:.1f} minutes")
        if batch_progress.current_company:
            print(f"Currently Processing: {batch_progress.current_company}")
        print(f"Elapsed Time: {elapsed/60:.1f} minutes")
        print(f"{'='*60}")

def main():
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    monitor = BatchMonitor()
    
    # Create sample companies (in real use, these would come from ProductHunt discovery)
    companies = []
    for i in range(10):
        companies.append(CompanyData(
            name=f"Sample Company {i+1}",
            domain=f"company{i+1}.com",
            product_url=f"https://producthunt.com/posts/product{i+1}",
            description=f"Sample company {i+1} for batch processing",
            launch_date=datetime.now()
        ))
    
    print(f"Starting batch processing of {len(companies)} companies...")
    
    # Run batch processing with monitoring
    results = controller.run_batch_processing(
        companies=companies,
        batch_size=3,  # Process 3 companies at a time
        progress_callback=monitor.progress_callback
    )
    
    # Final results
    print(f"\n{'='*60}")
    print("BATCH PROCESSING COMPLETED")
    print(f"{'='*60}")
    
    summary = results['summary']
    timeline = results['timeline']
    
    print(f"Batch ID: {results['batch_id']}")
    print(f"Final Status: {results['status']}")
    print(f"Total Companies: {summary['total_companies']}")
    print(f"Processed: {summary['processed_companies']}")
    print(f"Successful: {summary['successful_companies']}")
    print(f"Failed: {summary['failed_companies']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Total Prospects: {summary['total_prospects']}")
    print(f"Processing Time: {summary['total_processing_time']:.2f} seconds")
    print(f"Average Time per Company: {summary['average_processing_time']:.2f} seconds")
    print(f"Started: {timeline['start_time']}")
    print(f"Completed: {timeline['end_time']}")
    print(f"Duration: {timeline['duration_seconds']:.1f} seconds")

if __name__ == "__main__":
    main()
```

## 🎯 Advanced Usage Patterns

### Pattern 1: Multi-Stage Pipeline

```python
#!/usr/bin/env python3
"""Multi-stage processing pipeline."""

from controllers.prospect_automation_controller import ProspectAutomationController
from services.email_generator import EmailTemplate
from utils.config import Config
import json

class ProspectPipeline:
    """Multi-stage prospect processing pipeline."""
    
    def __init__(self, config):
        self.controller = ProspectAutomationController(config)
        self.results = {}
    
    def stage1_discovery(self, limit=20):
        """Stage 1: Discover companies and prospects."""
        print("Stage 1: Running discovery...")
        results = self.controller.run_discovery_pipeline(limit=limit)
        self.results['discovery'] = results
        return results
    
    def stage2_enrichment(self, prospect_ids):
        """Stage 2: Enrich prospect data."""
        print("Stage 2: Enriching prospect data...")
        # Additional enrichment logic would go here
        # For now, we'll simulate this
        enriched_data = {
            'enriched_prospects': len(prospect_ids),
            'additional_data_points': len(prospect_ids) * 3
        }
        self.results['enrichment'] = enriched_data
        return enriched_data
    
    def stage3_email_generation(self, prospect_ids, template=EmailTemplate.COLD_OUTREACH):
        """Stage 3: Generate personalized emails."""
        print("Stage 3: Generating emails...")
        email_results = self.controller.generate_outreach_emails(prospect_ids, template)
        self.results['emails'] = email_results
        return email_results
    
    def stage4_quality_check(self, email_results):
        """Stage 4: Quality check generated emails."""
        print("Stage 4: Quality checking emails...")
        
        quality_metrics = {
            'total_emails': len(email_results.get('emails', [])),
            'avg_length': 0,
            'personalization_score': 0,
            'spam_score': 0
        }
        
        emails = email_results.get('emails', [])
        if emails:
            total_length = sum(len(email.get('body', '')) for email in emails)
            quality_metrics['avg_length'] = total_length / len(emails)
            
            # Calculate average personalization score
            total_personalization = sum(email.get('personalization_score', 0) for email in emails)
            quality_metrics['personalization_score'] = total_personalization / len(emails)
        
        self.results['quality_check'] = quality_metrics
        return quality_metrics
    
    def run_full_pipeline(self, discovery_limit=20):
        """Run the complete pipeline."""
        print("Starting full prospect pipeline...")
        
        # Stage 1: Discovery
        discovery_results = self.stage1_discovery(discovery_limit)
        
        # Extract prospect IDs (this would be implemented based on your data structure)
        # For demo purposes, we'll simulate this
        prospect_ids = [f"prospect_{i}" for i in range(min(10, discovery_results['summary']['prospects_found']))]
        
        if not prospect_ids:
            print("No prospects found, pipeline stopped.")
            return self.results
        
        # Stage 2: Enrichment
        enrichment_results = self.stage2_enrichment(prospect_ids)
        
        # Stage 3: Email Generation
        email_results = self.stage3_email_generation(prospect_ids)
        
        # Stage 4: Quality Check
        quality_results = self.stage4_quality_check(email_results)
        
        # Final summary
        print(f"\n{'='*60}")
        print("PIPELINE COMPLETED")
        print(f"{'='*60}")
        print(f"Companies processed: {discovery_results['summary']['companies_processed']}")
        print(f"Prospects found: {discovery_results['summary']['prospects_found']}")
        print(f"Prospects enriched: {enrichment_results['enriched_prospects']}")
        print(f"Emails generated: {quality_results['total_emails']}")
        print(f"Average email length: {quality_results['avg_length']:.0f} characters")
        print(f"Average personalization score: {quality_results['personalization_score']:.2f}")
        
        return self.results

def main():
    config = Config.from_env()
    pipeline = ProspectPipeline(config)
    
    # Run full pipeline
    results = pipeline.run_full_pipeline(discovery_limit=15)
    
    # Save results
    with open('pipeline_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("Pipeline results saved to pipeline_results.json")

if __name__ == "__main__":
    main()
```

### Pattern 2: Scheduled Automation

```python
#!/usr/bin/env python3
"""Scheduled automation with cron-like functionality."""

import schedule
import time
import logging
from datetime import datetime
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging

class ScheduledProspector:
    """Scheduled prospect automation."""
    
    def __init__(self):
        setup_logging(log_level="INFO")
        self.logger = logging.getLogger(__name__)
        self.config = Config.from_env()
        self.controller = ProspectAutomationController(self.config)
    
    def daily_discovery(self):
        """Daily discovery job."""
        self.logger.info("Starting daily discovery job")
        
        try:
            results = self.controller.run_discovery_pipeline(limit=15)
            summary = results['summary']
            
            self.logger.info(f"Daily discovery completed:")
            self.logger.info(f"  Companies: {summary['companies_processed']}")
            self.logger.info(f"  Prospects: {summary['prospects_found']}")
            self.logger.info(f"  Success rate: {summary['success_rate']:.1f}%")
            
            # Send daily summary notification
            if hasattr(self, 'notification_manager') and self.notification_manager:
                daily_stats = {
                    'campaigns_run': 1,
                    'companies_processed': summary['companies_processed'],
                    'prospects_found': summary['prospects_found'],
                    'emails_generated': summary.get('emails_generated', 0),
                    'success_rate': summary['success_rate'],
                    'processing_time_minutes': summary.get('duration_seconds', 0) / 60,
                    'api_calls': summary.get('total_tokens', 0) // 10,  # Estimate
                    'top_campaign': 'Daily Discovery'
                }
                self.notification_manager.send_daily_summary_notification(daily_stats)
            
        except Exception as e:
            self.logger.error(f"Daily discovery failed: {e}")
            # Send error alert notification
            if hasattr(self, 'notification_manager') and self.notification_manager:
                error_data = {
                    'component': 'Daily Discovery',
                    'error_message': str(e),
                    'campaign_name': 'Daily Discovery',
                    'company_name': 'N/A'
                }
                self.notification_manager.send_error_alert(error_data)
    
    def weekly_cleanup(self):
        """Weekly cleanup and maintenance."""
        self.logger.info("Starting weekly cleanup")
        
        try:
            # Cleanup old logs
            import glob
            import os
            
            log_files = glob.glob("logs/*.log")
            week_old = time.time() - (7 * 24 * 60 * 60)
            
            for log_file in log_files:
                if os.path.getmtime(log_file) < week_old:
                    os.remove(log_file)
                    self.logger.info(f"Removed old log file: {log_file}")
            
            # Generate weekly report
            self._generate_weekly_report()
            
        except Exception as e:
            self.logger.error(f"Weekly cleanup failed: {e}")
    
    def _initialize_notification_manager(self):
        """Initialize notification manager for automated alerts."""
        try:
            from services.notification_manager import NotificationManager
            self.notification_manager = NotificationManager(self.config, self.notion_manager)
            self.logger.info("Notification manager initialized successfully")
        except Exception as e:
            self.logger.warning(f"Failed to initialize notification manager: {str(e)}")
            self.notification_manager = None
    
    def _generate_weekly_report(self):
        """Generate weekly summary report."""
        # Implement weekly reporting logic
        report = f"Weekly Report - {datetime.now().strftime('%Y-%m-%d')}\n"
        report += "=" * 50 + "\n"
        report += "Summary of this week's prospect automation activities\n"
        
        with open(f"weekly_report_{datetime.now().strftime('%Y%m%d')}.txt", 'w') as f:
            f.write(report)
        
        self.logger.info("Weekly report generated")
    
    def run_scheduler(self):
        """Run the scheduler."""
        # Schedule jobs
        schedule.every().day.at("09:00").do(self.daily_discovery)
        schedule.every().monday.at("08:00").do(self.weekly_cleanup)
        
        self.logger.info("Scheduler started")
        self.logger.info("Daily discovery: 09:00")
        self.logger.info("Weekly cleanup: Monday 08:00")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    scheduler = ScheduledProspector()
    
    print("Starting scheduled prospect automation...")
    print("Press Ctrl+C to stop")
    
    try:
        scheduler.run_scheduler()
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")

if __name__ == "__main__":
    main()
```

## 💡 Best Practices

### Configuration Management

```python
# config_manager.py
"""Configuration management best practices."""

import os
from dataclasses import dataclass
from typing import Optional
import yaml

@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    name: str
    api_limits: dict
    rate_limits: dict
    processing_limits: dict

class ConfigManager:
    """Manage configurations for different environments."""
    
    ENVIRONMENTS = {
        'development': EnvironmentConfig(
            name='development',
            api_limits={'hunter_monthly': 25, 'openai_monthly': 100},
            rate_limits={'scraping_delay': 5.0, 'hunter_per_minute': 5},
            processing_limits={'max_products': 10, 'max_prospects': 5}
        ),
        'production': EnvironmentConfig(
            name='production',
            api_limits={'hunter_monthly': 1000, 'openai_monthly': 1000},
            rate_limits={'scraping_delay': 2.0, 'hunter_per_minute': 10},
            processing_limits={'max_products': 50, 'max_prospects': 10}
        )
    }
    
    @classmethod
    def get_config(cls, environment: str = None):
        """Get configuration for specified environment."""
        if not environment:
            environment = os.getenv('ENVIRONMENT', 'development')
        
        return cls.ENVIRONMENTS.get(environment, cls.ENVIRONMENTS['development'])
    
    @classmethod
    def validate_environment(cls, environment: str):
        """Validate environment configuration."""
        config = cls.get_config(environment)
        
        # Check API keys exist
        required_keys = ['NOTION_TOKEN', 'HUNTER_API_KEY', 'OPENAI_API_KEY']
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        
        if missing_keys:
            raise ValueError(f"Missing API keys for {environment}: {missing_keys}")
        
        return True

# Usage example
def main():
    env = os.getenv('ENVIRONMENT', 'development')
    config = ConfigManager.get_config(env)
    
    print(f"Running in {config.name} environment")
    print(f"API limits: {config.api_limits}")
    print(f"Rate limits: {config.rate_limits}")
```

### Error Handling Patterns

```python
# error_handling_patterns.py
"""Error handling best practices."""

import functools
import time
import logging
from typing import Callable, Any

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator for retrying failed operations."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        wait_time = delay * (backoff ** attempt)
                        logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logging.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator

def safe_api_call(func: Callable) -> Callable:
    """Decorator for safe API calls with comprehensive error handling."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except ConnectionError as e:
            logging.error(f"Network error in {func.__name__}: {e}")
            raise
        except TimeoutError as e:
            logging.error(f"Timeout error in {func.__name__}: {e}")
            raise
        except ValueError as e:
            logging.error(f"Validation error in {func.__name__}: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in {func.__name__}: {e}")
            raise
    
    return wrapper

# Usage examples
@retry_on_failure(max_retries=3, delay=2.0)
@safe_api_call
def unreliable_api_call():
    """Example of API call with retry and error handling."""
    # Your API call here
    pass
```

### Data Validation Patterns

```python
# validation_patterns.py
"""Data validation best practices."""

from typing import List, Optional
from dataclasses import dataclass
import re

@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ProspectValidator:
    """Validate prospect data."""
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    LINKEDIN_PATTERN = re.compile(r'^https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+/?$')
    
    @classmethod
    def validate_prospect(cls, prospect_data: dict) -> ValidationResult:
        """Validate prospect data."""
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['name', 'company']
        for field in required_fields:
            if not prospect_data.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Email validation
        email = prospect_data.get('email')
        if email and not cls.EMAIL_PATTERN.match(email):
            errors.append(f"Invalid email format: {email}")
        
        # LinkedIn URL validation
        linkedin_url = prospect_data.get('linkedin_url')
        if linkedin_url and not cls.LINKEDIN_PATTERN.match(linkedin_url):
            warnings.append(f"LinkedIn URL format may be incorrect: {linkedin_url}")
        
        # Name validation
        name = prospect_data.get('name', '')
        if len(name) < 2:
            errors.append("Name too short")
        elif len(name) > 100:
            warnings.append("Name unusually long")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

# Usage example
def validate_and_process_prospects(prospects: List[dict]) -> List[dict]:
    """Validate and process a list of prospects."""
    valid_prospects = []
    
    for prospect in prospects:
        validation = ProspectValidator.validate_prospect(prospect)
        
        if validation.is_valid:
            valid_prospects.append(prospect)
        else:
            logging.error(f"Invalid prospect {prospect.get('name', 'Unknown')}: {validation.errors}")
        
        if validation.warnings:
            logging.warning(f"Prospect {prospect.get('name', 'Unknown')} warnings: {validation.warnings}")
    
    return valid_prospects
```

## ⚡ Performance Optimization

### Parallel Processing with ParallelProcessor

The system now includes built-in parallel processing capabilities for significant performance improvements.

```python
#!/usr/bin/env python3
"""Example of using the built-in parallel processing system."""

from services.parallel_processor import ParallelProcessor, AsyncParallelProcessor
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData
from utils.config import Config

def demonstrate_parallel_processing():
    """Demonstrate parallel processing capabilities."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Sample companies to process
    companies = [
        CompanyData(name="Company A", domain="companya.com", product_url="https://producthunt.com/posts/company-a"),
        CompanyData(name="Company B", domain="companyb.com", product_url="https://producthunt.com/posts/company-b"),
        CompanyData(name="Company C", domain="companyc.com", product_url="https://producthunt.com/posts/company-c"),
    ]
    
    # Initialize parallel processor with 3 workers
    parallel_processor = ParallelProcessor(max_workers=3)
    
    # Define progress callback
    def progress_callback(company_name: str, completed: int, total: int):
        print(f"Progress: {completed}/{total} - Currently processing: {company_name}")
    
    # Process companies in parallel
    results = parallel_processor.process_companies_parallel(
        companies=companies,
        process_function=controller.process_company,
        progress_callback=progress_callback
    )
    
    # Display results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"\nResults:")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    # Get processing statistics
    stats = parallel_processor.get_processing_stats()
    print(f"\nPerformance:")
    print(f"Total Duration: {stats['total_duration']:.1f}s")
    print(f"Processing Rate: {(stats['successful_companies'] / stats['total_duration']) * 60:.1f} companies/min")
    print(f"Workers Used: {parallel_processor.max_workers}")

def demonstrate_batch_processing():
    """Demonstrate batch processing with rate limiting."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    parallel_processor = ParallelProcessor(max_workers=3)
    
    # Large list of companies
    companies = [
        CompanyData(name=f"Company {i}", domain=f"company{i}.com", product_url=f"https://producthunt.com/posts/company-{i}")
        for i in range(1, 21)  # 20 companies
    ]
    
    # Process in batches of 5 with 30-second delays
    results = parallel_processor.process_companies_with_batching(
        companies=companies,
        process_function=controller.process_company,
        batch_size=5,
        delay_between_batches=30.0
    )
    
    print(f"Processed {len(companies)} companies in {len(results)} results")

async def demonstrate_async_processing():
    """Demonstrate async processing for maximum performance."""
    async_processor = AsyncParallelProcessor(max_concurrent=5)
    
    # Note: This requires async-compatible process functions
    # The current system uses ThreadPoolExecutor which is more suitable
    # for the I/O-bound operations (API calls, web scraping)
    
    print("Async processing requires async-compatible functions")
    print("Current implementation uses ThreadPoolExecutor for I/O-bound operations")

if __name__ == "__main__":
    print("🚀 Demonstrating Parallel Processing")
    demonstrate_parallel_processing()
    
    print("\n📦 Demonstrating Batch Processing")
    demonstrate_batch_processing()
```

### Performance Comparison

```python
#!/usr/bin/env python3
"""Performance comparison between sequential and parallel processing."""

import time
from services.parallel_processor import ParallelProcessor
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def compare_processing_performance():
    """Compare sequential vs parallel processing performance."""
    config = Config.from_env()
    controller = ProspectAutomationController(config)
    
    # Get sample companies (you would get these from ProductHunt scraper)
    companies = controller.product_hunt_scraper.get_latest_products(limit=6)
    
    print(f"Testing with {len(companies)} companies")
    
    # Sequential processing (simulated)
    print("\n🐌 Sequential Processing:")
    start_time = time.time()
    sequential_results = []
    for i, company in enumerate(companies):
        print(f"Processing {i+1}/{len(companies)}: {company.name}")
        try:
            prospects = controller.process_company(company)
            sequential_results.append(len(prospects))
        except Exception as e:
            print(f"Failed: {e}")
            sequential_results.append(0)
    
    sequential_duration = time.time() - start_time
    sequential_prospects = sum(sequential_results)
    
    # Parallel processing
    print("\n🚀 Parallel Processing:")
    parallel_processor = ParallelProcessor(max_workers=3)
    start_time = time.time()
    
    results = parallel_processor.process_companies_parallel(
        companies=companies,
        process_function=controller.process_company
    )
    
    parallel_duration = time.time() - start_time
    parallel_prospects = sum(len(r.prospects) for r in results if r.success)
    
    # Results comparison
    print(f"\n📊 Performance Comparison:")
    print(f"Sequential: {sequential_duration:.1f}s, {sequential_prospects} prospects")
    print(f"Parallel:   {parallel_duration:.1f}s, {parallel_prospects} prospects")
    print(f"Speedup:    {sequential_duration / parallel_duration:.1f}x faster")
    print(f"Rate:       {len(companies) / parallel_duration * 60:.1f} companies/min")

if __name__ == "__main__":
    compare_processing_performance()
```

### Advanced Parallel Processing Configuration

```python
#!/usr/bin/env python3
"""Advanced parallel processing configuration examples."""

from services.parallel_processor import ParallelProcessor
from utils.config import Config

def configure_optimal_workers():
    """Configure optimal number of workers based on system resources."""
    import os
    
    # Get CPU count
    cpu_count = os.cpu_count()
    
    # For I/O-bound operations (API calls), we can use more workers than CPU cores
    # Rule of thumb: 2-3x CPU cores for I/O-bound tasks
    optimal_workers = min(cpu_count * 2, 5)  # Cap at 5 to respect API limits
    
    print(f"CPU cores: {cpu_count}")
    print(f"Optimal workers for I/O-bound tasks: {optimal_workers}")
    
    return optimal_workers

def configure_rate_limited_processing():
    """Configure processing with strict rate limiting."""
    config = Config.from_env()
    
    # Conservative settings for rate-limited APIs
    processor = ParallelProcessor(
        max_workers=2,  # Fewer workers
        respect_rate_limits=True
    )
    
    # Use batch processing with longer delays
    batch_size = 3
    delay_between_batches = 60.0  # 1 minute between batches
    
    print(f"Rate-limited configuration:")
    print(f"Workers: {processor.max_workers}")
    print(f"Batch size: {batch_size}")
    print(f"Batch delay: {delay_between_batches}s")
    
    return processor, batch_size, delay_between_batches

if __name__ == "__main__":
    optimal_workers = configure_optimal_workers()
    processor, batch_size, delay = configure_rate_limited_processing()
```
    companies = [f"Company {i}" for i in range(20)]
    
    def process_company(company_name):
        """Process a single company."""
        # Simulate processing time
        time.sleep(2)
        return f"Processed {company_name}"
    
    # Process in batches of 5 with 3 parallel workers
    results = processor.process_in_batches(
        items=companies,
        batch_size=5,
        processor_func=process_company
    )
    
    print(f"Processed {len(results)} companies")
```

### Memory Management

```python
# memory_management.py
"""Memory management best practices."""

import gc
import psutil
import logging
from typing import Generator, Any

class MemoryManager:
    """Manage memory usage during processing."""
    
    def __init__(self, memory_threshold_mb: int = 1000):
        self.memory_threshold_mb = memory_threshold_mb
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def check_memory_usage(self) -> bool:
        """Check if memory usage is within threshold."""
        current_usage = self.get_memory_usage()
        
        if current_usage > self.memory_threshold_mb:
            logging.warning(f"High memory usage: {current_usage:.1f}MB")
            return False
        
        return True
    
    def cleanup_memory(self):
        """Force garbage collection."""
        gc.collect()
        logging.info(f"Memory cleanup completed. Current usage: {self.get_memory_usage():.1f}MB")
    
    def process_with_memory_management(self, items: list, processor_func) -> Generator[Any, None, None]:
        """Process items with automatic memory management."""
        
        for i, item in enumerate(items):
            # Process item
            result = processor_func(item)
            yield result
            
            # Check memory every 10 items
            if i % 10 == 0:
                if not self.check_memory_usage():
                    self.cleanup_memory()

# Usage example
def memory_efficient_processing():
    """Example of memory-efficient processing."""
    
    memory_manager = MemoryManager(memory_threshold_mb=500)
    
    # Large dataset
    large_dataset = [f"Item {i}" for i in range(1000)]
    
    def process_item(item):
        # Simulate processing that uses memory
        return f"Processed {item}"
    
    # Process with memory management
    results = []
    for result in memory_manager.process_with_memory_management(large_dataset, process_item):
        results.append(result)
    
    print(f"Processed {len(results)} items with memory management")
```

## 🔍 Troubleshooting Scenarios

### Scenario 1: API Rate Limits

```python
# rate_limit_handling.py
"""Handle API rate limits gracefully."""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional

class RateLimitManager:
    """Manage API rate limits across services."""
    
    def __init__(self):
        self.last_calls: Dict[str, datetime] = {}
        self.call_counts: Dict[str, int] = {}
        self.rate_limits = {
            'hunter_io': {'calls_per_minute': 10, 'delay_seconds': 6},
            'linkedin': {'calls_per_minute': 5, 'delay_seconds': 12},
            'producthunt': {'calls_per_minute': 10, 'delay_seconds': 6}
        }
    
    def can_make_call(self, service: str) -> bool:
        """Check if we can make a call to the service."""
        now = datetime.now()
        
        if service not in self.last_calls:
            return True
        
        time_since_last = (now - self.last_calls[service]).total_seconds()
        required_delay = self.rate_limits.get(service, {}).get('delay_seconds', 1)
        
        return time_since_last >= required_delay
    
    def wait_if_needed(self, service: str):
        """Wait if needed before making API call."""
        if not self.can_make_call(service):
            required_delay = self.rate_limits.get(service, {}).get('delay_seconds', 1)
            time_since_last = (datetime.now() - self.last_calls[service]).total_seconds()
            wait_time = required_delay - time_since_last
            
            if wait_time > 0:
                logging.info(f"Rate limit: waiting {wait_time:.1f}s for {service}")
                time.sleep(wait_time)
    
    def record_call(self, service: str):
        """Record that we made a call to the service."""
        self.last_calls[service] = datetime.now()
        self.call_counts[service] = self.call_counts.get(service, 0) + 1

# Usage example
rate_manager = RateLimitManager()

def make_api_call(service: str, api_func):
    """Make API call with rate limit management."""
    rate_manager.wait_if_needed(service)
    
    try:
        result = api_func()
        rate_manager.record_call(service)
        return result
    except Exception as e:
        if "rate limit" in str(e).lower():
            logging.warning(f"Rate limit hit for {service}: {e}")
            time.sleep(60)  # Wait 1 minute
            return make_api_call(service, api_func)  # Retry
        raise
```

### Scenario 2: Data Quality Issues

```python
# data_quality_management.py
"""Manage data quality issues."""

from typing import List, Dict, Any
import logging

class DataQualityManager:
    """Manage data quality and cleanup."""
    
    def __init__(self):
        self.quality_metrics = {
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'duplicate_records': 0,
            'missing_email_records': 0
        }
    
    def clean_prospect_data(self, prospects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Clean and validate prospect data."""
        cleaned_prospects = []
        seen_prospects = set()
        
        for prospect in prospects:
            self.quality_metrics['total_records'] += 1
            
            # Clean data
            cleaned_prospect = self._clean_single_prospect(prospect)
            
            # Check for duplicates
            prospect_key = (cleaned_prospect.get('name', '').lower(), 
                          cleaned_prospect.get('company', '').lower())
            
            if prospect_key in seen_prospects:
                self.quality_metrics['duplicate_records'] += 1
                logging.warning(f"Duplicate prospect: {prospect_key}")
                continue
            
            seen_prospects.add(prospect_key)
            
            # Validate
            if self._is_valid_prospect(cleaned_prospect):
                cleaned_prospects.append(cleaned_prospect)
                self.quality_metrics['valid_records'] += 1
            else:
                self.quality_metrics['invalid_records'] += 1
                logging.warning(f"Invalid prospect: {cleaned_prospect}")
        
        return cleaned_prospects
    
    def _clean_single_prospect(self, prospect: Dict[str, Any]) -> Dict[str, Any]:
        """Clean a single prospect record."""
        cleaned = {}
        
        # Clean name
        name = prospect.get('name', '').strip()
        if name:
            # Remove extra whitespace, fix capitalization
            cleaned['name'] = ' '.join(word.capitalize() for word in name.split())
        
        # Clean company
        company = prospect.get('company', '').strip()
        if company:
            cleaned['company'] = company
        
        # Clean email
        email = prospect.get('email', '').strip().lower()
        if email and '@' in email:
            cleaned['email'] = email
        else:
            self.quality_metrics['missing_email_records'] += 1
        
        # Clean LinkedIn URL
        linkedin_url = prospect.get('linkedin_url', '').strip()
        if linkedin_url and 'linkedin.com' in linkedin_url:
            cleaned['linkedin_url'] = linkedin_url
        
        # Clean role
        role = prospect.get('role', '').strip()
        if role:
            cleaned['role'] = role
        
        return cleaned
    
    def _is_valid_prospect(self, prospect: Dict[str, Any]) -> bool:
        """Check if prospect is valid."""
        required_fields = ['name', 'company']
        
        for field in required_fields:
            if not prospect.get(field):
                return False
        
        # Additional validation rules
        if len(prospect.get('name', '')) < 2:
            return False
        
        if len(prospect.get('company', '')) < 2:
            return False
        
        return True
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Get data quality report."""
        total = self.quality_metrics['total_records']
        
        if total == 0:
            return self.quality_metrics
        
        report = self.quality_metrics.copy()
        report['quality_score'] = (self.quality_metrics['valid_records'] / total) * 100
        report['duplicate_rate'] = (self.quality_metrics['duplicate_records'] / total) * 100
        report['missing_email_rate'] = (self.quality_metrics['missing_email_records'] / total) * 100
        
        return report

# Usage example
def process_with_quality_management(raw_prospects):
    """Process prospects with quality management."""
    quality_manager = DataQualityManager()
    
    # Clean and validate data
    cleaned_prospects = quality_manager.clean_prospect_data(raw_prospects)
    
    # Get quality report
    quality_report = quality_manager.get_quality_report()
    
    logging.info(f"Data quality report:")
    logging.info(f"  Total records: {quality_report['total_records']}")
    logging.info(f"  Valid records: {quality_report['valid_records']}")
    logging.info(f"  Quality score: {quality_report['quality_score']:.1f}%")
    logging.info(f"  Duplicate rate: {quality_report['duplicate_rate']:.1f}%")
    
    return cleaned_prospects
```

---

This comprehensive usage guide provides practical examples and best practices for effectively using the Job Prospect Automation system. Start with the basic examples and gradually move to more advanced patterns as you become comfortable with the system.