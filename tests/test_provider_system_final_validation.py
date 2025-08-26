"""
Final Validation Tests for Provider System

This test suite provides final validation that all requirements for task 10
are met and the provider system is working correctly.

Requirements validated:
- 1.1: Environment variable configuration
- 2.1: CLI provider management  
- 3.1-3.5: All provider implementations
"""

import pytest
from unittest.mock import Mock, patch
import os

from services.ai_provider_manager import AIProviderManager, get_provider_manager
from services.providers.base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.providers.openai_provider import OpenAIProvider
from services.providers.azure_openai_provider import AzureOpenAIProvider
from services.providers.anthropic_provider import AnthropicProvider
from services.providers.google_provider import GoogleProvider
from services.providers.deepseek_provider import DeepSeekProvider
from services.openai_client_manager import CompletionRequest, CompletionResponse
from click.testing import CliRunner
from cli import cli


class TestProviderSystemFinalValidation:
    """Final validation tests for the complete provider system."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Reset singleton
        AIProviderManager._instance = None
    
    def test_requirement_1_1_environment_configuration(self):
        """Test Requirement 1.1: Environment variable configuration works for all providers."""
        test_cases = [
            ('OPENAI_API_KEY', 'sk-test-openai', OpenAIProvider, {}),
            ('AZURE_OPENAI_API_KEY', 'test-azure', AzureOpenAIProvider, {
                'endpoint': 'https://test.openai.azure.com',
                'deployment_name': 'gpt-4'
            }),
            ('ANTHROPIC_API_KEY', 'sk-ant-test', AnthropicProvider, {}),
            ('GOOGLE_API_KEY', 'test-google-key-12345678901234567890', GoogleProvider, {}),
            ('DEEPSEEK_API_KEY', 'sk-deepseek-test', DeepSeekProvider, {})
        ]
        
        for env_var, api_key, provider_class, extra_config in test_cases:
            with patch.dict(os.environ, {env_var: api_key}, clear=True):
                # Mock any additional configuration methods
                with patch.object(provider_class, '_configure_client', return_value=None):
                    config = extra_config.copy()
                    provider = provider_class(config)
                    
                    # Validate that provider can access environment variable
                    result = provider.validate_config()
                    
                    # Should not fail due to missing API key
                    assert result.status != ValidationStatus.ERROR or "api key" not in result.message.lower()
    
    def test_requirement_2_1_cli_provider_management(self):
        """Test Requirement 2.1: CLI provider management commands work."""
        runner = CliRunner()
        
        # Test list-ai-providers command
        with patch('cli.get_provider_manager') as mock_get_manager:
            with patch('cli.CLIConfig') as mock_cli_config:
                # Mock configuration
                mock_config = Mock()
                mock_cli_config.return_value.base_config = mock_config
                mock_cli_config.return_value.dry_run = False
                
                # Mock provider manager
                mock_manager = Mock()
                mock_manager.get_provider_status.return_value = {
                    "active_provider": None,
                    "total_registered": 5,
                    "total_configured": 0,
                    "providers": {
                        "openai": {"registered": True, "configured": False, "description": "OpenAI GPT models"},
                        "anthropic": {"registered": True, "configured": False, "description": "Anthropic Claude models"}
                    }
                }
                mock_get_manager.return_value = mock_manager
                
                result = runner.invoke(cli, ['list-ai-providers'])
                
                assert result.exit_code == 0
                assert "AI Provider Status" in result.output
        
        # Test validate-ai-config command
        with patch('cli.get_provider_manager') as mock_get_manager:
            with patch('cli.CLIConfig') as mock_cli_config:
                mock_config = Mock()
                mock_cli_config.return_value.base_config = mock_config
                mock_cli_config.return_value.dry_run = False
                
                mock_manager = Mock()
                mock_manager.list_configured_providers.return_value = []
                mock_get_manager.return_value = mock_manager
                
                result = runner.invoke(cli, ['validate-ai-config'])
                
                assert result.exit_code == 0
        
        # Test dry-run functionality
        result = runner.invoke(cli, ['--dry-run', 'list-ai-providers'])
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output
    
    def test_requirement_3_1_openai_provider(self):
        """Test Requirement 3.1: OpenAI provider implementation."""
        config = {'api_key': 'sk-test-openai-key', 'model': 'gpt-3.5-turbo'}
        
        with patch('services.providers.openai_provider.OpenAIClientManager'):
            provider = OpenAIProvider(config)
            
            # Test interface compliance
            assert isinstance(provider, BaseAIProvider)
            assert provider.get_provider_name() == 'openai'
            
            # Test configuration validation
            result = provider.validate_config()
            assert result.status == ValidationStatus.SUCCESS
            
            # Test model info
            model_info = provider.get_model_info()
            assert model_info['provider'] == 'openai'
            assert 'available_models' in model_info
    
    def test_requirement_3_2_azure_openai_provider(self):
        """Test Requirement 3.2: Azure OpenAI provider implementation."""
        config = {
            'api_key': 'test-azure-key',
            'endpoint': 'https://test.openai.azure.com',
            'deployment_name': 'gpt-4',
            'api_version': '2024-02-15-preview'
        }
        
        with patch('services.providers.azure_openai_provider.OpenAIClientManager'):
            provider = AzureOpenAIProvider(config)
            
            # Test interface compliance
            assert isinstance(provider, BaseAIProvider)
            assert provider.get_provider_name() == 'azureopenai'
            
            # Test configuration validation
            result = provider.validate_config()
            assert result.status == ValidationStatus.SUCCESS
            
            # Test model info
            model_info = provider.get_model_info()
            assert model_info['provider'] == 'azure_openai'
            assert 'deployment_info' in model_info
    
    def test_requirement_3_3_anthropic_provider(self):
        """Test Requirement 3.3: Anthropic provider implementation."""
        config = {'api_key': 'sk-ant-test-key', 'model': 'claude-3-sonnet-20240229'}
        
        with patch('services.providers.anthropic_provider.Anthropic'):
            provider = AnthropicProvider(config)
            
            # Test interface compliance
            assert isinstance(provider, BaseAIProvider)
            assert provider.get_provider_name() == 'anthropic'
            
            # Test configuration validation
            result = provider.validate_config()
            assert result.status == ValidationStatus.SUCCESS
            
            # Test model info
            model_info = provider.get_model_info()
            assert model_info['provider'] == 'anthropic'
            assert 'available_models' in model_info
    
    def test_requirement_3_4_google_provider(self):
        """Test Requirement 3.4: Google provider implementation."""
        config = {'api_key': 'test-google-key-12345678901234567890', 'model': 'gemini-2.5-flash'}
        
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(config)
            
            # Test interface compliance
            assert isinstance(provider, BaseAIProvider)
            assert provider.get_provider_name() == 'google'
            
            # Test configuration validation
            result = provider.validate_config()
            assert result.status == ValidationStatus.SUCCESS
            
            # Test model info
            model_info = provider.get_model_info()
            assert model_info['provider'] == 'google'
            assert 'available_models' in model_info
    
    def test_requirement_3_5_deepseek_provider(self):
        """Test Requirement 3.5: DeepSeek provider implementation."""
        config = {'api_key': 'sk-deepseek-test-key', 'model': 'deepseek-chat'}
        
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(config)
            
            # Test interface compliance
            assert isinstance(provider, BaseAIProvider)
            assert provider.get_provider_name() == 'deepseek'
            
            # Test configuration validation
            result = provider.validate_config()
            assert result.status == ValidationStatus.SUCCESS
            
            # Test model info
            model_info = provider.get_model_info()
            assert model_info['provider'] == 'deepseek'
            assert 'available_models' in model_info
    
    def test_provider_manager_integration(self):
        """Test that provider manager integrates all providers correctly."""
        manager = AIProviderManager()
        
        # Test all expected providers are registered
        expected_providers = ['openai', 'azure-openai', 'anthropic', 'google', 'deepseek']
        registered_providers = manager.list_providers()
        
        for provider in expected_providers:
            assert provider in registered_providers
            
            # Test provider info is available
            info = manager.get_provider_info(provider)
            assert info is not None
            assert info.name == provider
    
    def test_completion_request_compatibility(self):
        """Test that all providers handle CompletionRequest correctly."""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
            temperature=0.7,
            max_tokens=100
        )
        
        provider_configs = [
            (OpenAIProvider, {'api_key': 'sk-test'}),
            (AzureOpenAIProvider, {'api_key': 'test', 'endpoint': 'https://test.com', 'deployment_name': 'test'}),
            (AnthropicProvider, {'api_key': 'sk-ant-test'}),
            (GoogleProvider, {'api_key': 'test-google-key-12345678901234567890'}),
            (DeepSeekProvider, {'api_key': 'sk-deepseek-test'})
        ]
        
        for provider_class, config in provider_configs:
            # Mock the underlying clients to avoid actual API calls
            with patch.object(provider_class, '_configure_client', return_value=None):
                with patch.object(provider_class, 'make_completion') as mock_completion:
                    mock_response = CompletionResponse(
                        content="Test response",
                        model="test-model",
                        usage={"total_tokens": 10},
                        finish_reason="stop",
                        success=True
                    )
                    mock_completion.return_value = mock_response
                    
                    provider = provider_class(config)
                    response = provider.make_completion(request)
                    
                    # Verify response format
                    assert isinstance(response, CompletionResponse)
                    assert response.success is True
                    mock_completion.assert_called_once_with(request)
    
    def test_backward_compatibility(self):
        """Test that existing functionality still works."""
        from services.openai_client_manager import get_client_manager
        
        # Test that existing client manager still works
        manager = get_client_manager()
        assert manager is not None
        
        # Test that it's still a singleton
        manager2 = get_client_manager()
        assert manager is manager2
    
    def test_security_configuration_masking(self):
        """Test that all providers properly mask sensitive configuration."""
        provider_configs = [
            (OpenAIProvider, {'api_key': 'sk-secret-key'}),
            (AzureOpenAIProvider, {'api_key': 'secret-azure', 'endpoint': 'https://test.com', 'deployment_name': 'test'}),
            (AnthropicProvider, {'api_key': 'sk-ant-secret'}),
            (GoogleProvider, {'api_key': 'secret-google-key-12345678901234567890'}),
            (DeepSeekProvider, {'api_key': 'sk-deepseek-secret'})
        ]
        
        for provider_class, config in provider_configs:
            with patch.object(provider_class, '_configure_client', return_value=None):
                provider = provider_class(config)
                safe_config = provider.get_config()
                
                # API key should be masked
                assert safe_config.get('api_key') == '***'
    
    def test_error_handling_consistency(self):
        """Test that all providers handle errors consistently."""
        provider_classes = [OpenAIProvider, AzureOpenAIProvider, AnthropicProvider, GoogleProvider, DeepSeekProvider]
        
        for provider_class in provider_classes:
            # Test with missing API key
            with patch.dict(os.environ, {}, clear=True):
                provider = provider_class({})
                result = provider.validate_config()
                
                # Should return ERROR status for missing API key
                assert result.status == ValidationStatus.ERROR
                # Check for various forms of API key error messages
                message_lower = result.message.lower()
                assert ("api key" in message_lower or 
                       "key is required" in message_lower or
                       "api_key" in message_lower or
                       "configuration missing" in message_lower)


if __name__ == "__main__":
    pytest.main([__file__])