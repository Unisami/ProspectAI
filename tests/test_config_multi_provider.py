"""Tests for multi-provider AI configuration support."""

import os
import pytest
from unittest.mock import patch
from utils.config import Config


class TestMultiProviderConfig:
    """Test multi-provider AI configuration."""
    
    def test_openai_provider_config(self):
        """Test OpenAI provider configuration."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_openai_key',
            'AI_MODEL': 'gpt-4',
            'AI_TEMPERATURE': '0.8',
            'AI_MAX_TOKENS': '2000'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'openai'
            assert config.openai_api_key == 'test_openai_key'
            assert config.ai_model == 'gpt-4'
            assert config.ai_temperature == 0.8
            assert config.ai_max_tokens == 2000
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_openai_key'
            assert provider_config['model'] == 'gpt-4'
            assert provider_config['temperature'] == 0.8
            assert provider_config['max_tokens'] == 2000
    
    def test_azure_openai_provider_config(self):
        """Test Azure OpenAI provider configuration."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'azure-openai',
            'AZURE_OPENAI_API_KEY': 'test_azure_key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'gpt-4-deployment',
            'AI_TEMPERATURE': '0.5'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'azure-openai'
            assert config.azure_openai_api_key == 'test_azure_key'
            assert config.azure_openai_endpoint == 'https://test.openai.azure.com'
            assert config.azure_openai_deployment_name == 'gpt-4-deployment'
            assert config.ai_temperature == 0.5
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_azure_key'
            assert provider_config['endpoint'] == 'https://test.openai.azure.com'
            assert provider_config['deployment_name'] == 'gpt-4-deployment'
            assert provider_config['temperature'] == 0.5
    
    def test_anthropic_provider_config(self):
        """Test Anthropic provider configuration."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'anthropic',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'AI_MODEL': 'claude-3-sonnet-20240229'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'anthropic'
            assert config.anthropic_api_key == 'test_anthropic_key'
            assert config.ai_model == 'claude-3-sonnet-20240229'
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_anthropic_key'
            assert provider_config['model'] == 'claude-3-sonnet-20240229'
    
    def test_google_provider_config(self):
        """Test Google provider configuration."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'google',
            'GOOGLE_API_KEY': 'test_google_key',
            'AI_MODEL': 'gemini-pro'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'google'
            assert config.google_api_key == 'test_google_key'
            assert config.ai_model == 'gemini-pro'
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_google_key'
            assert provider_config['model'] == 'gemini-pro'
    
    def test_deepseek_provider_config(self):
        """Test DeepSeek provider configuration."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'deepseek',
            'DEEPSEEK_API_KEY': 'test_deepseek_key',
            'AI_MODEL': 'deepseek-chat'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'deepseek'
            assert config.deepseek_api_key == 'test_deepseek_key'
            assert config.ai_model == 'deepseek-chat'
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_deepseek_key'
            assert provider_config['model'] == 'deepseek-chat'
    
    def test_backward_compatibility_use_azure_openai(self):
        """Test backward compatibility with USE_AZURE_OPENAI flag."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'USE_AZURE_OPENAI': 'true',
            'AZURE_OPENAI_API_KEY': 'test_azure_key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'azure-openai'
            assert config.use_azure_openai is True
    
    def test_missing_provider_credentials(self):
        """Test validation when provider credentials are missing."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'openai'
            # Missing OPENAI_API_KEY
        }):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                Config.from_env()
    
    def test_unsupported_provider(self):
        """Test validation with unsupported provider."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'unsupported_provider'
        }):
            with pytest.raises(ValueError, match="Unsupported AI provider"):
                Config.from_env()
    
    def test_get_supported_providers(self):
        """Test getting list of supported providers."""
        providers = Config.get_supported_providers()
        expected = ["openai", "azure-openai", "anthropic", "google", "deepseek"]
        assert providers == expected
    
    def test_get_available_models(self):
        """Test getting available models for each provider."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_key'
        }):
            config = Config.from_env()
            models = config.get_available_models()
            assert "gpt-4" in models
            assert "gpt-3.5-turbo" in models
    
    def test_validate_api_keys_multi_provider(self):
        """Test API key validation for different providers."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'anthropic',
            'ANTHROPIC_API_KEY': 'test_anthropic_key_12345'
        }):
            config = Config.from_env()
            validation_results = config.validate_api_keys()
            
            assert validation_results['notion_token'] is True
            assert validation_results['hunter_api_key'] is True
            assert validation_results['anthropic_api_key'] is True
    
    def test_get_missing_config_multi_provider(self):
        """Test getting missing configuration for different providers."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'google'
            # Missing GOOGLE_API_KEY
        }):
            config = Config(
                notion_token='test_notion_token',
                hunter_api_key='test_hunter_key',
                ai_provider='google'
            )
            missing = config.get_missing_config()
            assert 'GOOGLE_API_KEY' in missing
    
    def test_model_validation_for_provider(self):
        """Test model validation for different providers."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_key',
            'AI_PARSING_MODEL': 'invalid-model'
        }):
            config = Config.from_env()
            with pytest.raises(ValueError, match="AI parsing model must be a valid OpenAI model"):
                config.validate()
    
    def test_temperature_validation(self):
        """Test AI temperature validation."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_key',
            'AI_TEMPERATURE': '3.0'  # Invalid temperature
        }):
            config = Config.from_env()
            with pytest.raises(ValueError, match="AI temperature must be between 0 and 2"):
                config.validate()
    
    def test_to_dict_includes_new_fields(self):
        """Test that to_dict includes new multi-provider fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'AI_PROVIDER': 'anthropic',
            'ANTHROPIC_API_KEY': 'test_anthropic_key',
            'AI_MODEL': 'claude-3-sonnet-20240229',
            'AI_TEMPERATURE': '0.8'
        }):
            config = Config.from_env()
            config_dict = config.to_dict()
            
            assert config_dict['ai_provider'] == 'anthropic'
            assert config_dict['anthropic_api_key'] == 'test_anthropic_key'
            assert config_dict['ai_model'] == 'claude-3-sonnet-20240229'
            assert config_dict['ai_temperature'] == 0.8
    
    def test_from_dict_handles_new_fields(self):
        """Test that from_dict handles new multi-provider fields."""
        config_dict = {
            'notion_token': 'test_notion_token',
            'hunter_api_key': 'test_hunter_key',
            'ai_provider': 'google',
            'google_api_key': 'test_google_key',
            'ai_model': 'gemini-pro',
            'ai_temperature': 0.5,
            'ai_max_tokens': 1500
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.ai_provider == 'google'
        assert config.google_api_key == 'test_google_key'
        assert config.ai_model == 'gemini-pro'
        assert config.ai_temperature == 0.5
        assert config.ai_max_tokens == 1500