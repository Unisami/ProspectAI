"""Integration tests for multi-provider configuration system."""

import os
import tempfile
import pytest
from unittest.mock import patch
from utils.config import Config


class TestConfigIntegration:
    """Integration tests for configuration system."""
    
    def test_full_openai_configuration_flow(self):
        """Test complete OpenAI configuration flow."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_openai_key_12345',
            'AI_MODEL': 'gpt-4',
            'AI_TEMPERATURE': '0.8',
            'AI_MAX_TOKENS': '2000'
        }):
            # Create config from environment
            config = Config.from_env()
            
            # Verify basic configuration
            assert config.ai_provider == 'openai'
            assert config.openai_api_key == 'test_openai_key_12345'
            assert config.ai_model == 'gpt-4'
            assert config.ai_temperature == 0.8
            assert config.ai_max_tokens == 2000
            
            # Test provider configuration
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_openai_key_12345'
            assert provider_config['model'] == 'gpt-4'
            assert provider_config['temperature'] == 0.8
            assert provider_config['max_tokens'] == 2000
            
            # Test validation
            config.validate()  # Should not raise
            
            # Test API key validation
            api_validation = config.validate_api_keys()
            assert api_validation['notion_token'] is True
            assert api_validation['hunter_api_key'] is True
            assert api_validation['openai_api_key'] is True
            
            # Test missing config check
            missing = config.get_missing_config()
            assert len(missing) == 0
    
    def test_full_anthropic_configuration_flow(self):
        """Test complete Anthropic configuration flow."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'anthropic',
            'ANTHROPIC_API_KEY': 'test_anthropic_key_12345',
            'AI_MODEL': 'claude-3-sonnet-20240229',
            'AI_TEMPERATURE': '0.5',
            'AI_PARSING_MODEL': 'claude-3-sonnet-20240229',
            'PRODUCT_ANALYSIS_MODEL': 'claude-3-sonnet-20240229',
            'EMAIL_GENERATION_MODEL': 'claude-3-sonnet-20240229'
        }):
            config = Config.from_env()
            
            assert config.ai_provider == 'anthropic'
            assert config.anthropic_api_key == 'test_anthropic_key_12345'
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_anthropic_key_12345'
            assert provider_config['model'] == 'claude-3-sonnet-20240229'
            
            config.validate()  # Should not raise
            
            api_validation = config.validate_api_keys()
            assert api_validation['anthropic_api_key'] is True
    
    def test_backward_compatibility_azure_openai(self):
        """Test backward compatibility with USE_AZURE_OPENAI flag."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'USE_AZURE_OPENAI': 'true',
            'AZURE_OPENAI_API_KEY': 'test_azure_key_12345',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'gpt-4-deployment'
        }):
            config = Config.from_env()
            
            # Should automatically set provider to azure-openai
            assert config.ai_provider == 'azure-openai'
            assert config.use_azure_openai is True
            assert config.azure_openai_api_key == 'test_azure_key_12345'
            
            provider_config = config.get_provider_config()
            assert provider_config['api_key'] == 'test_azure_key_12345'
            assert provider_config['endpoint'] == 'https://test.openai.azure.com'
            
            config.validate()  # Should not raise
    
    def test_configuration_serialization_deserialization(self):
        """Test configuration can be serialized and deserialized."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'google',
            'GOOGLE_API_KEY': 'test_google_key_12345',
            'AI_MODEL': 'gemini-pro',
            'AI_TEMPERATURE': '0.3'
        }):
            # Create original config
            original_config = Config.from_env()
            
            # Convert to dict
            config_dict = original_config.to_dict()
            
            # Create new config from dict
            new_config = Config.from_dict(config_dict)
            
            # Verify they match
            assert new_config.ai_provider == original_config.ai_provider
            assert new_config.google_api_key == original_config.google_api_key
            assert new_config.ai_model == original_config.ai_model
            assert new_config.ai_temperature == original_config.ai_temperature
            
            # Verify provider config matches
            original_provider_config = original_config.get_provider_config()
            new_provider_config = new_config.get_provider_config()
            assert original_provider_config == new_provider_config
    
    def test_configuration_file_operations(self):
        """Test saving and loading configuration files."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'deepseek',
            'DEEPSEEK_API_KEY': 'test_deepseek_key_12345',
            'AI_MODEL': 'deepseek-chat'
        }):
            config = Config.from_env()
            
            # Test YAML file operations
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml_path = f.name
            
            try:
                # Save to YAML (without secrets)
                config.save_to_file(yaml_path, include_secrets=False)
                
                # Load from YAML
                loaded_config = Config.from_file(yaml_path)
                
                # Verify structure matches (secrets will be masked)
                assert loaded_config.ai_provider == config.ai_provider
                assert loaded_config.ai_model == config.ai_model
                
            finally:
                os.unlink(yaml_path)
    
    def test_provider_switching(self):
        """Test switching between different providers."""
        base_env = {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'OPENAI_API_KEY': 'test_openai_key_12345',
            'ANTHROPIC_API_KEY': 'test_anthropic_key_12345',
            'GOOGLE_API_KEY': 'test_google_key_12345'
        }
        
        # Test OpenAI
        with patch.dict(os.environ, {**base_env, 'AI_PROVIDER': 'openai'}):
            config = Config.from_env()
            assert config.ai_provider == 'openai'
            assert 'gpt-4' in config.get_available_models()
        
        # Test Anthropic
        with patch.dict(os.environ, {**base_env, 'AI_PROVIDER': 'anthropic'}):
            config = Config.from_env()
            assert config.ai_provider == 'anthropic'
            assert 'claude-3-sonnet-20240229' in config.get_available_models()
        
        # Test Google
        with patch.dict(os.environ, {**base_env, 'AI_PROVIDER': 'google'}):
            config = Config.from_env()
            assert config.ai_provider == 'google'
            assert 'gemini-pro' in config.get_available_models()
    
    def test_error_handling_and_validation(self):
        """Test comprehensive error handling and validation."""
        # Test unsupported provider
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'unsupported_provider'
        }):
            with pytest.raises(ValueError, match="Unsupported AI provider"):
                Config.from_env()
        
        # Test missing credentials
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'openai'
            # Missing OPENAI_API_KEY
        }):
            with pytest.raises(ValueError, match="OPENAI_API_KEY environment variable is required"):
                Config.from_env()
        
        # Test invalid temperature
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'openai',
            'OPENAI_API_KEY': 'test_openai_key_12345',
            'AI_TEMPERATURE': '3.0'  # Invalid
        }):
            config = Config.from_env()
            with pytest.raises(ValueError, match="AI temperature must be between 0 and 2"):
                config.validate()
        
        # Test invalid model for provider
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token_12345',
            'HUNTER_API_KEY': 'test_hunter_key_12345',
            'AI_PROVIDER': 'anthropic',
            'ANTHROPIC_API_KEY': 'test_anthropic_key_12345',
            'AI_PARSING_MODEL': 'gpt-4'  # OpenAI model for Anthropic provider
        }):
            config = Config.from_env()
            with pytest.raises(ValueError, match="AI parsing model must be a valid Anthropic model"):
                config.validate()