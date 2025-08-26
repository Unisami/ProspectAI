"""
Provider Demo

Demonstrates how to use all available AI providers including OpenAI, 
Azure OpenAI, Anthropic Claude, and Google Gemini through the unified 
provider system.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from services.providers.openai_provider import OpenAIProvider
from services.providers.azure_openai_provider import AzureOpenAIProvider
from services.providers.anthropic_provider import AnthropicProvider
from services.providers.google_provider import GoogleProvider
from services.openai_client_manager import CompletionRequest


def demo_openai_provider():
    """Demonstrate OpenAI provider usage."""
    print("=== OpenAI Provider Demo ===")
    
    # Configuration for OpenAI provider
    config = {
        'api_key': os.getenv('OPENAI_API_KEY', 'sk-demo-key'),
        'model': 'gpt-3.5-turbo',
        'temperature': 0.7,
        'max_tokens': 100
    }
    
    # Create provider
    provider = OpenAIProvider(config)
    
    # Validate configuration
    validation_result = provider.validate_config()
    print(f"Configuration validation: {validation_result.status.value}")
    print(f"Message: {validation_result.message}")
    
    # Get model information
    model_info = provider.get_model_info()
    print(f"Provider: {model_info['provider']}")
    print(f"Default model: {model_info['default_model']}")
    print(f"Available models: {len(model_info['available_models'])}")
    
    # Test connection (this would make an actual API call if API key is valid)
    if os.getenv('OPENAI_API_KEY'):
        print("\nTesting connection...")
        connection_result = provider.test_connection()
        print(f"Connection test: {connection_result.status.value}")
        print(f"Message: {connection_result.message}")
    else:
        print("\nSkipping connection test (no API key provided)")
    
    print()


def demo_azure_openai_provider():
    """Demonstrate Azure OpenAI provider usage."""
    print("=== Azure OpenAI Provider Demo ===")
    
    # Configuration for Azure OpenAI provider
    config = {
        'api_key': os.getenv('AZURE_OPENAI_API_KEY', 'demo-azure-key'),
        'endpoint': os.getenv('AZURE_OPENAI_ENDPOINT', 'https://demo.openai.azure.com/'),
        'deployment_name': os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-35-turbo'),
        'api_version': '2024-02-15-preview'
    }
    
    # Create provider
    provider = AzureOpenAIProvider(config)
    
    # Validate configuration
    validation_result = provider.validate_config()
    print(f"Configuration validation: {validation_result.status.value}")
    print(f"Message: {validation_result.message}")
    
    # Get model information
    model_info = provider.get_model_info()
    print(f"Provider: {model_info['provider']}")
    print(f"Deployment: {model_info['deployment_info']['deployment_name']}")
    print(f"Endpoint: {model_info['deployment_info']['endpoint']}")
    
    # Get provider-specific information
    print(f"Deployment name: {provider.get_deployment_name()}")
    print(f"Endpoint: {provider.get_endpoint()}")
    
    # Test connection (this would make an actual API call if configuration is valid)
    if all([os.getenv('AZURE_OPENAI_API_KEY'), 
            os.getenv('AZURE_OPENAI_ENDPOINT'), 
            os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')]):
        print("\nTesting connection...")
        connection_result = provider.test_connection()
        print(f"Connection test: {connection_result.status.value}")
        print(f"Message: {connection_result.message}")
    else:
        print("\nSkipping connection test (Azure configuration not provided)")
    
    print()


def demo_anthropic_provider():
    """Demonstrate Anthropic Claude provider usage."""
    print("=== Anthropic Claude Provider Demo ===")
    
    # Configuration for Anthropic provider
    config = {
        'api_key': os.getenv('ANTHROPIC_API_KEY', 'sk-ant-demo-key'),
        'model': 'claude-3-sonnet-20240229',
        'temperature': 0.7,
        'max_tokens': 100
    }
    
    # Create provider
    provider = AnthropicProvider(config)
    
    # Validate configuration
    validation_result = provider.validate_config()
    print(f"Configuration validation: {validation_result.status.value}")
    print(f"Message: {validation_result.message}")
    
    # Get model information
    model_info = provider.get_model_info()
    print(f"Provider: {model_info['provider']}")
    print(f"Default model: {model_info['default_model']}")
    print(f"Available models: {len(model_info['available_models'])}")
    print(f"Features: {', '.join(model_info['features'])}")
    
    # Test connection (this would make an actual API call if API key is valid)
    if os.getenv('ANTHROPIC_API_KEY'):
        print("\nTesting connection...")
        connection_result = provider.test_connection()
        print(f"Connection test: {connection_result.status.value}")
        print(f"Message: {connection_result.message}")
    else:
        print("\nSkipping connection test (no API key provided)")
    
    print()


def demo_google_provider():
    """Demonstrate Google Gemini provider usage."""
    print("=== Google Gemini Provider Demo ===")
    
    # Configuration for Google provider
    config = {
        'api_key': os.getenv('GOOGLE_API_KEY', 'demo-google-key'),
        'model': 'gemini-pro',
        'temperature': 0.7,
        'max_tokens': 100
    }
    
    # Create provider
    provider = GoogleProvider(config)
    
    # Validate configuration
    validation_result = provider.validate_config()
    print(f"Configuration validation: {validation_result.status.value}")
    print(f"Message: {validation_result.message}")
    
    # Get model information
    model_info = provider.get_model_info()
    print(f"Provider: {model_info['provider']}")
    print(f"Default model: {model_info['default_model']}")
    print(f"Available models: {len(model_info['available_models'])}")
    print(f"Supports vision: {model_info['supports_vision']}")
    print(f"Supports function calling: {model_info['supports_function_calling']}")
    print(f"Features: {', '.join(model_info['features'])}")
    
    # Test connection (this would make an actual API call if API key is valid)
    if os.getenv('GOOGLE_API_KEY'):
        print("\nTesting connection...")
        connection_result = provider.test_connection()
        print(f"Connection test: {connection_result.status.value}")
        print(f"Message: {connection_result.message}")
    else:
        print("\nSkipping connection test (no API key provided)")
    
    print()


def demo_completion_request():
    """Demonstrate making completion requests with providers."""
    print("=== Completion Request Demo ===")
    
    # This demo shows how to make completion requests
    # Note: This won't make actual API calls without valid credentials
    
    # OpenAI provider example
    openai_config = {
        'api_key': 'sk-demo-key',  # Replace with real key for actual usage
        'model': 'gpt-3.5-turbo'
    }
    
    openai_provider = OpenAIProvider(openai_config)
    
    # Create a completion request
    request = CompletionRequest(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! How are you?"}
        ],
        temperature=0.7,
        max_tokens=50
    )
    
    print("Sample completion request:")
    print(f"Messages: {request.messages}")
    print(f"Temperature: {request.temperature}")
    print(f"Max tokens: {request.max_tokens}")
    
    # Note: Actual completion would be:
    # response = openai_provider.make_completion(request)
    # print(f"Response: {response.content}")
    
    print("(Actual API call skipped in demo)")
    print()


def demo_provider_comparison():
    """Compare all available providers."""
    print("=== Provider Comparison ===")
    
    # Create all providers
    openai_provider = OpenAIProvider({'api_key': 'sk-demo'})
    azure_provider = AzureOpenAIProvider({
        'api_key': 'demo-key',
        'endpoint': 'https://demo.openai.azure.com/',
        'deployment_name': 'gpt-35-turbo'
    })
    anthropic_provider = AnthropicProvider({'api_key': 'sk-ant-demo'})
    google_provider = GoogleProvider({'api_key': 'demo-google-key'})
    
    providers = [
        ("OpenAI", openai_provider),
        ("Azure OpenAI", azure_provider),
        ("Anthropic Claude", anthropic_provider),
        ("Google Gemini", google_provider)
    ]
    
    for name, provider in providers:
        print(f"{name} Provider:")
        print(f"  Provider name: {provider.get_provider_name()}")
        
        # Get model info
        model_info = provider.get_model_info()
        print(f"  Default model: {model_info['default_model']}")
        print(f"  Available models: {len(model_info['available_models'])}")
        
        # Provider-specific features
        if hasattr(provider, 'client_id'):
            print(f"  Client ID: {provider.client_id}")
        if hasattr(provider, 'get_deployment_name'):
            print(f"  Deployment: {provider.get_deployment_name()}")
        if 'supports_vision' in model_info:
            print(f"  Supports vision: {model_info['supports_vision']}")
        if 'supports_function_calling' in model_info:
            print(f"  Supports function calling: {model_info['supports_function_calling']}")
        
        # Show configuration (without sensitive data)
        print(f"  Config (safe): {provider.get_config()}")
        print()
    
    print()


def main():
    """Run all demos."""
    print("Provider System Demo")
    print("===================")
    print()
    
    demo_openai_provider()
    demo_azure_openai_provider()
    demo_anthropic_provider()
    demo_google_provider()
    demo_completion_request()
    demo_provider_comparison()
    
    print("Demo completed!")
    print()
    print("To use with real API keys, set these environment variables:")
    print("- OPENAI_API_KEY=your_openai_key")
    print("- AZURE_OPENAI_API_KEY=your_azure_key")
    print("- AZURE_OPENAI_ENDPOINT=your_azure_endpoint")
    print("- AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment")
    print("- ANTHROPIC_API_KEY=your_anthropic_key")
    print("- GOOGLE_API_KEY=your_google_key")


if __name__ == "__main__":
    main()