"""
Integration tests for provider system with existing OpenAI client manager.

Tests that the new provider system maintains backward compatibility with the existing
OpenAI client manager and works correctly in real scenarios.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.openai_provider import OpenAIProvider
from services.providers.azure_openai_provider import AzureOpenAIProvider
from services.openai_client_manager import CompletionRequest, CompletionResponse, get_client_manager


class TestProviderIntegration:
    """Integration tests for provider system."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.openai_config = {
            'api_key': 'sk-test-key-123',
            'model': 'gpt-3.5-turbo'
        }
        
        self.azure_config = {
            'api_key': 'test-azure-key-123',
            'endpoint': 'https://test-resource.openai.azure.com/',
            'deployment_name': 'gpt-35-turbo',
            'api_version': '2024-02-15-preview'
        }
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_openai_provider_integration(self, mock_client_manager_class):
        """Test OpenAI provider integration with client manager."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Mock successful response
        mock_response = CompletionResponse(
            content="Hello! This is a test response.",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 5, "completion_tokens": 8, "total_tokens": 13},
            finish_reason="stop",
            success=True
        )
        mock_manager.make_completion.return_value = mock_response
        
        # Create provider and test
        provider = OpenAIProvider(self.openai_config)
        
        # Verify client manager was configured
        mock_manager.configure.assert_called_once()
        
        # Test completion request
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.7,
            max_tokens=100
        )
        
        response = provider.make_completion(request)
        
        # Verify response
        assert response.success is True
        assert response.content == "Hello! This is a test response."
        assert response.model == "gpt-3.5-turbo"
        assert response.usage["total_tokens"] == 13
        
        # Verify client manager was called correctly
        mock_manager.make_completion.assert_called_once()
        call_args = mock_manager.make_completion.call_args
        assert call_args[0][0] == request  # First argument is the request
        assert call_args[0][1] == provider.client_id  # Second argument is client_id
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_azure_provider_integration(self, mock_client_manager_class):
        """Test Azure OpenAI provider integration with client manager."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Mock successful response
        mock_response = CompletionResponse(
            content="Azure OpenAI response",
            model="gpt-35-turbo",
            usage={"prompt_tokens": 4, "completion_tokens": 6, "total_tokens": 10},
            finish_reason="stop",
            success=True
        )
        mock_manager.make_completion.return_value = mock_response
        
        # Create provider and test
        provider = AzureOpenAIProvider(self.azure_config)
        
        # Verify client manager was configured
        mock_manager.configure.assert_called_once()
        
        # Test completion request
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.5,
            max_tokens=50
        )
        
        response = provider.make_completion(request)
        
        # Verify response
        assert response.success is True
        assert response.content == "Azure OpenAI response"
        assert response.model == "gpt-35-turbo"
        assert response.usage["total_tokens"] == 10
        
        # Verify client manager was called correctly
        mock_manager.make_completion.assert_called_once()
        call_args = mock_manager.make_completion.call_args
        assert call_args[0][0] == request  # First argument is the request
        assert call_args[0][1] == provider.client_id  # Second argument is client_id
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_provider_config_validation_integration(self, mock_client_manager_class):
        """Test that provider validation works correctly."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Test valid configuration
        provider = OpenAIProvider(self.openai_config)
        result = provider.validate_config()
        
        assert result.status.value == "success"
        assert "valid" in result.message.lower()
        
        # Test connection test
        mock_response = CompletionResponse(
            content="Test",
            model="gpt-3.5-turbo",
            usage={"total_tokens": 3},
            finish_reason="stop",
            success=True
        )
        mock_manager.make_completion.return_value = mock_response
        
        connection_result = provider.test_connection()
        assert connection_result.status.value == "success"
        assert "successful" in connection_result.message.lower()
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_azure_provider_config_validation_integration(self, mock_client_manager_class):
        """Test that Azure provider validation works correctly."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Test valid configuration
        provider = AzureOpenAIProvider(self.azure_config)
        result = provider.validate_config()
        
        assert result.status.value == "success"
        assert "valid" in result.message.lower()
        assert result.details["endpoint"] == self.azure_config['endpoint']
        assert result.details["deployment_name"] == self.azure_config['deployment_name']
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_provider_model_info_integration(self, mock_client_manager_class):
        """Test that provider model info works correctly."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Test OpenAI provider
        provider = OpenAIProvider(self.openai_config)
        model_info = provider.get_model_info()
        
        assert model_info["provider"] == "openai"
        assert "available_models" in model_info
        assert len(model_info["available_models"]) > 0
        assert model_info["default_model"] == "gpt-3.5-turbo"
        
        # Verify GPT models are available
        model_names = [model["name"] for model in model_info["available_models"]]
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_azure_provider_model_info_integration(self, mock_client_manager_class):
        """Test that Azure provider model info works correctly."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Test Azure provider
        provider = AzureOpenAIProvider(self.azure_config)
        model_info = provider.get_model_info()
        
        assert model_info["provider"] == "azure_openai"
        assert "deployment_info" in model_info
        assert model_info["deployment_info"]["deployment_name"] == "gpt-35-turbo"
        assert model_info["deployment_info"]["endpoint"] == self.azure_config['endpoint']
        assert model_info["default_model"] == "gpt-35-turbo"
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_multiple_providers_isolation(self, mock_azure_manager_class, mock_openai_manager_class):
        """Test that multiple providers can coexist without interference."""
        # Setup mocks
        mock_openai_manager = Mock()
        mock_azure_manager = Mock()
        mock_openai_manager_class.return_value = mock_openai_manager
        mock_azure_manager_class.return_value = mock_azure_manager
        
        # Create both providers
        openai_provider = OpenAIProvider(self.openai_config)
        azure_provider = AzureOpenAIProvider(self.azure_config)
        
        # Verify both were configured independently
        mock_openai_manager.configure.assert_called_once()
        mock_azure_manager.configure.assert_called_once()
        
        # Verify they have different client IDs
        assert openai_provider.client_id != azure_provider.client_id
        assert "openai_provider" in openai_provider.client_id
        assert "azure_openai_provider" in azure_provider.client_id
        
        # Test that they use different provider names
        assert openai_provider.get_provider_name() == "openai"
        assert azure_provider.get_provider_name() == "azureopenai"
    
    def test_backward_compatibility_with_existing_client_manager(self):
        """Test that providers don't break existing client manager usage."""
        # This test verifies that the existing client manager can still be used
        # independently of the new provider system
        
        # Get the global client manager (this should work as before)
        manager = get_client_manager()
        assert manager is not None
        
        # Verify it's the same singleton instance
        manager2 = get_client_manager()
        assert manager is manager2
        
        # Test that we can still list clients (should be empty initially)
        clients = manager.list_clients()
        assert isinstance(clients, list)
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_provider_cleanup_integration(self, mock_client_manager_class):
        """Test that provider cleanup works correctly."""
        # Setup mock
        mock_manager = Mock()
        mock_client_manager_class.return_value = mock_manager
        
        # Create provider
        provider = OpenAIProvider(self.openai_config)
        client_id = provider.client_id
        
        # Verify it was configured
        mock_manager.configure.assert_called_once()
        
        # Test cleanup
        provider.__del__()
        
        # Verify cleanup was called
        mock_manager.close_client.assert_called_once_with(client_id)