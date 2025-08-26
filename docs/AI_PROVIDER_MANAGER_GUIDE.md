# AI Provider Manager Guide

The AI Provider Manager is a centralized system for managing multiple AI providers in the Job Prospect Automation system. It provides a unified interface for provider registration, discovery, instantiation, and switching functionality with thread-safe operations.

## Overview

The AI Provider Manager enables seamless switching between different AI providers (OpenAI, Azure OpenAI, Anthropic Claude, Google Gemini, DeepSeek) through a consistent API interface.

### Key Features

- **Unified Interface**: Single API for all AI providers with consistent request/response handling
- **Automatic Provider Discovery**: Auto-configures providers based on available credentials
- **Thread-Safe Operations**: Singleton pattern with thread-safe provider management
- **Dynamic Provider Loading**: Providers loaded on-demand to avoid import issues
- **Configuration Validation**: Built-in validation for provider-specific requirements
- **Connection Testing**: Test provider connections before use
- **Provider Switching**: Runtime switching between configured providers

## Quick Start

### Basic Usage

```python
from services.ai_provider_manager import get_provider_manager, configure_provider_manager
from services.openai_client_manager import CompletionRequest
from utils.config import Config

# Configure the provider manager
config = Config.from_env()
configure_provider_manager(config)

# Get the provider manager
manager = get_provider_manager()

# Make a completion request
request = CompletionRequest(
    messages=[{"role": "user", "content": "Hello, world!"}],
    model="gpt-4",
    temperature=0.7
)
response = manager.make_completion(request)
```

### Provider Management

```python
# List available providers
providers = manager.list_providers()
print(f"Available providers: {providers}")

# Get active provider
active_provider = manager.get_active_provider_name()
print(f"Active provider: {active_provider}")

# Switch providers at runtime
manager.set_active_provider("anthropic")

# Validate provider configuration
validation_result = manager.validate_provider("openai")
print(f"OpenAI validation: {validation_result.status}")
```

## Configuration

### Environment Variables

Set your preferred AI provider using the `AI_PROVIDER` environment variable:

```env
# Select your AI provider
AI_PROVIDER=openai  # Options: openai, azure-openai, anthropic, google, deepseek

# Global AI configuration (applies to all providers)
AI_MODEL=gpt-4
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=1000
```

### Provider-Specific Configuration

#### OpenAI
```env
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your_openai_key_here
```

#### Azure OpenAI
```env
AI_PROVIDER=azure-openai
USE_AZURE_OPENAI=true
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4-deployment
AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

#### Anthropic Claude (Coming Soon)
```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_anthropic_key
AI_MODEL=claude-3-sonnet-20240229
```

#### Google Gemini (Coming Soon)
```env
AI_PROVIDER=google
GOOGLE_API_KEY=your_google_key
AI_MODEL=gemini-pro
```

#### DeepSeek (Coming Soon)
```env
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=your_deepseek_key
AI_MODEL=deepseek-chat
```

## API Reference

### Core Methods

#### `get_provider_manager() -> AIProviderManager`
Get the global AI provider manager singleton instance.

#### `configure_provider_manager(config: Config) -> None`
Configure the global AI provider manager with system configuration.

#### `get_active_provider() -> BaseAIProvider`
Get the currently active AI provider instance.

#### `make_completion(request: CompletionRequest, provider_name: Optional[str] = None) -> CompletionResponse`
Convenience function for making completions with the provider manager.

### AIProviderManager Methods

#### `list_providers() -> List[str]`
List all registered provider names.

#### `list_configured_providers() -> List[str]`
List configured (instantiated) provider names.

#### `get_active_provider_name() -> Optional[str]`
Get the name of the currently active provider.

#### `set_active_provider(provider_name: str) -> None`
Set the active provider.

#### `validate_provider(provider_name: str) -> ValidationResult`
Validate a provider's configuration and connection.

#### `validate_all_providers() -> Dict[str, ValidationResult]`
Validate all configured providers.

#### `get_provider_status() -> Dict[str, Any]`
Get comprehensive status information for all providers.

## Provider Status and Monitoring

### Check Provider Status

```python
# Get comprehensive provider status
status = manager.get_provider_status()
print(f"Active provider: {status['active_provider']}")
print(f"Total registered: {status['total_registered']}")
print(f"Total configured: {status['total_configured']}")

# Check individual provider status
for provider_name, provider_status in status['providers'].items():
    print(f"{provider_name}:")
    print(f"  Registered: {provider_status['registered']}")
    print(f"  Configured: {provider_status['configured']}")
    print(f"  Description: {provider_status['description']}")
    if provider_status['configured']:
        print(f"  Config Valid: {provider_status['config_valid']}")
```

### Validate All Providers

```python
# Validate all providers
results = manager.validate_all_providers()
for provider_name, result in results.items():
    status_icon = "✅" if result.status == ValidationStatus.SUCCESS else "❌"
    print(f"{status_icon} {provider_name}: {result.message}")
```

## CLI Commands (Coming Soon)

The following CLI commands will be available for provider management:

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

## Error Handling

The AI Provider Manager includes comprehensive error handling:

```python
from services.providers.base_provider import ValidationStatus

try:
    # Make completion request
    response = manager.make_completion(request)
except ValueError as e:
    print(f"Configuration error: {e}")
except ImportError as e:
    print(f"Provider not available: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Check validation status
validation_result = manager.validate_provider("openai")
if validation_result.status == ValidationStatus.ERROR:
    print(f"Validation failed: {validation_result.message}")
elif validation_result.status == ValidationStatus.WARNING:
    print(f"Validation warning: {validation_result.message}")
else:
    print("Validation successful")
```

## Custom Provider Registration

You can register custom AI providers:

```python
from services.providers.base_provider import BaseAIProvider

class CustomProvider(BaseAIProvider):
    def __init__(self, config):
        super().__init__(config)
        # Initialize your custom provider
    
    def make_completion(self, request):
        # Implement completion logic
        pass
    
    def validate_config(self):
        # Implement config validation
        pass
    
    def test_connection(self):
        # Implement connection test
        pass

# Register the custom provider
manager.register_provider(
    name="custom",
    provider_class=CustomProvider,
    description="My custom AI provider",
    required_config=["custom_api_key"],
    optional_config=["custom_model"]
)
```

## Troubleshooting

### Common Issues

1. **Provider not configured**: Ensure all required environment variables are set
2. **Import errors**: Provider dependencies may not be installed
3. **Validation failures**: Check API keys and network connectivity
4. **No active provider**: Set AI_PROVIDER environment variable or call set_active_provider()

### Debug Information

```python
# Get detailed provider information
for provider_name in manager.list_providers():
    try:
        info = manager.get_provider_info(provider_name)
        print(f"{provider_name}:")
        print(f"  Type: {info.provider_type}")
        print(f"  Description: {info.description}")
        print(f"  Required config: {info.required_config}")
        print(f"  Optional config: {info.optional_config}")
    except Exception as e:
        print(f"Error getting info for {provider_name}: {e}")
```

## Best Practices

1. **Environment-based Configuration**: Use environment variables for provider selection
2. **Validation**: Always validate providers before use in production
3. **Error Handling**: Implement proper error handling for provider operations
4. **Monitoring**: Regularly check provider status and validation results
5. **Testing**: Test provider switching in development before production deployment

## Future Enhancements

The AI Provider Manager is designed to be extensible. Future enhancements may include:

- Additional provider implementations (Anthropic, Google, DeepSeek)
- Provider load balancing and failover
- Usage analytics and cost tracking per provider
- Provider-specific optimization settings
- Automatic provider selection based on request type