#!/usr/bin/env python3
"""
Multi-Provider AI Configuration Demo

This script demonstrates how to use the multi-provider AI configuration system
to switch between different AI providers (OpenAI, Azure OpenAI, Anthropic, Google, DeepSeek).
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.config import Config


def demo_provider_configuration(provider_name: str, credentials: dict, model: str = None):
    """Demonstrate configuration for a specific provider."""
    print(f"\n{'='*60}")
    print(f"DEMO: {provider_name.upper()} PROVIDER CONFIGURATION")
    print(f"{'='*60}")
    
    # Set up environment variables
    env_vars = {
        'NOTION_TOKEN': 'demo_notion_token_12345',
        'HUNTER_API_KEY': 'demo_hunter_key_12345',
        'AI_PROVIDER': provider_name,
        **credentials
    }
    
    if model:
        env_vars['AI_MODEL'] = model
    
    # Temporarily set environment variables
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # Create configuration
        config = Config.from_env()
        
        print(f"✓ Provider: {config.ai_provider}")
        print(f"✓ Model: {config.ai_model or 'default'}")
        print(f"✓ Temperature: {config.ai_temperature}")
        print(f"✓ Max Tokens: {config.ai_max_tokens}")
        
        # Get provider-specific configuration
        provider_config = config.get_provider_config()
        print(f"\nProvider Configuration:")
        for key, value in provider_config.items():
            if 'key' in key.lower():
                # Mask API keys for security
                masked_value = value[:10] + '...' if value and len(value) > 10 else '***'
                print(f"  {key}: {masked_value}")
            else:
                print(f"  {key}: {value}")
        
        # Show available models
        available_models = config.get_available_models()
        print(f"\nAvailable Models: {', '.join(available_models)}")
        
        # Validate configuration
        try:
            config.validate()
            print("✓ Configuration validation: PASSED")
        except Exception as e:
            print(f"✗ Configuration validation: FAILED - {e}")
        
        # Check API key validation
        api_validation = config.validate_api_keys()
        print(f"\nAPI Key Validation:")
        for key, is_valid in api_validation.items():
            status = "✓ VALID" if is_valid else "✗ INVALID"
            print(f"  {key}: {status}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    finally:
        # Restore original environment variables
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def main():
    """Run the multi-provider configuration demo."""
    print("Multi-Provider AI Configuration System Demo")
    print("This demo shows how to configure different AI providers.")
    print("\nNote: This demo uses fake API keys for demonstration purposes.")
    
    # Demo OpenAI
    demo_provider_configuration(
        'openai',
        {'OPENAI_API_KEY': 'demo_openai_key_12345'},
        'gpt-4'
    )
    
    # Demo Azure OpenAI
    demo_provider_configuration(
        'azure-openai',
        {
            'AZURE_OPENAI_API_KEY': 'demo_azure_key_12345',
            'AZURE_OPENAI_ENDPOINT': 'https://demo.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'gpt-4-deployment'
        }
    )
    
    # Demo Anthropic
    demo_provider_configuration(
        'anthropic',
        {'ANTHROPIC_API_KEY': 'demo_anthropic_key_12345'},
        'claude-3-sonnet-20240229'
    )
    
    # Demo Google
    demo_provider_configuration(
        'google',
        {'GOOGLE_API_KEY': 'demo_google_key_12345'},
        'gemini-pro'
    )
    
    # Demo DeepSeek
    demo_provider_configuration(
        'deepseek',
        {'DEEPSEEK_API_KEY': 'demo_deepseek_key_12345'},
        'deepseek-chat'
    )
    
    # Demo backward compatibility
    print(f"\n{'='*60}")
    print("DEMO: BACKWARD COMPATIBILITY (USE_AZURE_OPENAI)")
    print(f"{'='*60}")
    
    env_vars = {
        'NOTION_TOKEN': 'demo_notion_token_12345',
        'HUNTER_API_KEY': 'demo_hunter_key_12345',
        'USE_AZURE_OPENAI': 'true',
        'AZURE_OPENAI_API_KEY': 'demo_azure_key_12345',
        'AZURE_OPENAI_ENDPOINT': 'https://demo.openai.azure.com'
    }
    
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        config = Config.from_env()
        print(f"✓ Automatically detected provider: {config.ai_provider}")
        print(f"✓ USE_AZURE_OPENAI flag: {config.use_azure_openai}")
        print("✓ Backward compatibility: WORKING")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
    
    # Show supported providers
    print(f"\n{'='*60}")
    print("SUPPORTED PROVIDERS")
    print(f"{'='*60}")
    supported_providers = Config.get_supported_providers()
    for i, provider in enumerate(supported_providers, 1):
        print(f"{i}. {provider}")
    
    print(f"\n{'='*60}")
    print("DEMO COMPLETED")
    print(f"{'='*60}")
    print("To use the multi-provider system in your application:")
    print("1. Set AI_PROVIDER environment variable to your desired provider")
    print("2. Set the corresponding API key environment variable")
    print("3. Optionally set AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS")
    print("4. Create Config.from_env() and use config.get_provider_config()")


if __name__ == '__main__':
    main()