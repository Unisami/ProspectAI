"""
Tests for Azure OpenAI Provider Implementation

Tests the Azure OpenAI provider wrapper to ensure it works correctly with the existing
OpenAI client manager while maintaining backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.azure_openai_provider import AzureOpenAIProvider
from services.providers.base_provider import ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class TestAzureOpenAIProvider:
    """Test cases for Azure OpenAI provider implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'api_key': 'test-azure-key-123',
            'endpoint': 'https://test-resource.openai.azure.com/',
            'deployment_name': 'gpt-35-turbo',
            'api_version': '2024-02-15-preview',
            'model': 'gpt-35-turbo'
        }
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_provider_initialization(self, mock_client_manager):
        """Test that the provider initializes correctly."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Create provider
        provider = AzureOpenAIProvider(self.config)
        
        # Verify initialization
        assert provider.provider_name == 'azureopenai'
        assert provider.config == self.config
        assert provider.client_manager == mock_manager_instance
        
        # Verify client manager was configured
        mock_manager_instance.configure.assert_called_once()
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_make_completion_success(self, mock_client_manager):
        """Test successful completion request."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock successful response
        mock_response = CompletionResponse(
            content="Hello! How can I help you?",
            model="gpt-35-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request
        provider = AzureOpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-35-turbo"
        )
        
        response = provider.make_completion(request)
        
        # Verify response
        assert response.success is True
        assert response.content == "Hello! How can I help you?"
        assert response.model == "gpt-35-turbo"
        assert response.usage["total_tokens"] == 18
        
        # Verify client manager was called correctly
        mock_manager_instance.make_completion.assert_called_once()
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_make_completion_with_default_deployment(self, mock_client_manager):
        """Test completion request uses default deployment when none specified."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        mock_response = CompletionResponse(
            content="Response",
            model="gpt-35-turbo",
            usage={},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request without model
        provider = AzureOpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        # Verify default deployment was used
        assert request.model == "gpt-35-turbo"
        assert response.success is True
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_make_completion_error_handling(self, mock_client_manager):
        """Test error handling in completion requests."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock error response
        mock_response = CompletionResponse(
            content="",
            model="gpt-35-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="Azure API rate limit exceeded"
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request
        provider = AzureOpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        # Verify error response
        assert response.success is False
        assert response.error_message == "Azure API rate limit exceeded"
        assert response.content == ""
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        provider = AzureOpenAIProvider(self.config)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "valid" in result.message.lower()
        assert result.details["api_key_present"] is True
        assert result.details["endpoint"] == self.config['endpoint']
        assert result.details["deployment_name"] == self.config['deployment_name']
    
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key."""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AzureOpenAIProvider(config_no_key)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "api_key" in result.details["missing_config"]
    
    def test_validate_config_missing_endpoint(self):
        """Test validation with missing endpoint."""
        config_no_endpoint = self.config.copy()
        del config_no_endpoint['endpoint']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AzureOpenAIProvider(config_no_endpoint)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "endpoint" in result.details["missing_config"]
    
    def test_validate_config_missing_deployment_name(self):
        """Test validation with missing deployment name."""
        config_no_deployment = self.config.copy()
        del config_no_deployment['deployment_name']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AzureOpenAIProvider(config_no_deployment)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "deployment_name" in result.details["missing_config"]
    
    def test_validate_config_http_endpoint_warning(self):
        """Test validation warning for HTTP endpoint."""
        config_http = self.config.copy()
        config_http['endpoint'] = 'http://test-resource.openai.azure.com/'
        
        provider = AzureOpenAIProvider(config_http)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.WARNING
        assert "HTTPS" in result.message
        assert any("HTTPS" in warning for warning in result.details["warnings"])
    
    def test_get_model_info(self):
        """Test getting model information."""
        provider = AzureOpenAIProvider(self.config)
        model_info = provider.get_model_info()
        
        assert model_info["provider"] == "azure_openai"
        assert "deployment_info" in model_info
        assert model_info["deployment_info"]["deployment_name"] == "gpt-35-turbo"
        assert model_info["deployment_info"]["endpoint"] == self.config['endpoint']
        assert model_info["deployment_info"]["api_version"] == self.config['api_version']
        assert model_info["default_model"] == "gpt-35-turbo"
        assert model_info["supports_streaming"] is True
        assert model_info["supports_function_calling"] is True
        
        # Check available models contains deployment
        assert len(model_info["available_models"]) == 1
        assert model_info["available_models"][0]["name"] == "gpt-35-turbo"
        assert model_info["available_models"][0]["deployment_name"] == "gpt-35-turbo"
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_get_client_info(self, mock_client_manager):
        """Test getting client information."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        mock_client_info = {
            "client_id": "test_client",
            "client_type": "azure_openai",
            "model_name": "gpt-35-turbo",
            "configured": True
        }
        mock_manager_instance.get_client_info.return_value = mock_client_info
        
        # Create provider and get client info
        provider = AzureOpenAIProvider(self.config)
        client_info = provider.get_client_info()
        
        assert client_info == mock_client_info
        mock_manager_instance.get_client_info.assert_called_once()
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_get_client_info_error(self, mock_client_manager):
        """Test error handling when getting client info."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        mock_manager_instance.get_client_info.side_effect = Exception("Client not found")
        
        # Create provider and get client info
        provider = AzureOpenAIProvider(self.config)
        client_info = provider.get_client_info()
        
        assert "error" in client_info
        assert "Client not found" in client_info["error"]
        assert client_info["provider"] == "azure_openai"
    
    def test_get_deployment_name(self):
        """Test getting deployment name."""
        provider = AzureOpenAIProvider(self.config)
        deployment_name = provider.get_deployment_name()
        
        assert deployment_name == "gpt-35-turbo"
    
    def test_get_endpoint(self):
        """Test getting endpoint."""
        provider = AzureOpenAIProvider(self.config)
        endpoint = provider.get_endpoint()
        
        assert endpoint == "https://test-resource.openai.azure.com/"
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_provider_cleanup(self, mock_client_manager):
        """Test that provider cleans up resources properly."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Create and destroy provider
        provider = AzureOpenAIProvider(self.config)
        client_id = provider.client_id
        
        # Manually call cleanup (normally called by __del__)
        provider.__del__()
        
        # Verify cleanup was called
        mock_manager_instance.close_client.assert_called_once_with(client_id)
    
    @patch.dict(os.environ, {
        'AZURE_OPENAI_API_KEY': 'env-azure-key-456',
        'AZURE_OPENAI_ENDPOINT': 'https://env-resource.openai.azure.com/',
        'AZURE_OPENAI_DEPLOYMENT_NAME': 'env-gpt-4'
    })
    def test_config_from_environment(self):
        """Test that configuration can be loaded from environment variables."""
        config_minimal = {}
        
        provider = AzureOpenAIProvider(config_minimal)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.SUCCESS
        assert result.details["api_key_present"] is True
        assert result.details["endpoint"] == "https://env-resource.openai.azure.com/"
        assert result.details["deployment_name"] == "env-gpt-4"
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_connection_test_success(self, mock_client_manager):
        """Test successful connection test."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock successful test response
        mock_response = CompletionResponse(
            content="Hello",
            model="gpt-35-turbo",
            usage={"total_tokens": 5},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and test connection
        provider = AzureOpenAIProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "successful" in result.message.lower()
        assert result.details["model"] == "gpt-35-turbo"
        assert result.details["usage"]["total_tokens"] == 5
    
    @patch('services.providers.azure_openai_provider.OpenAIClientManager')
    def test_connection_test_failure(self, mock_client_manager):
        """Test connection test failure."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        mock_manager_instance.make_completion.side_effect = Exception("Azure connection failed")
        
        # Create provider and test connection
        provider = AzureOpenAIProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.ERROR
        assert "failed" in result.message.lower()
        assert "Azure connection failed" in result.message or "Empty response" in result.message
    
    def test_default_api_version(self):
        """Test that default API version is used when not specified."""
        config_no_version = self.config.copy()
        del config_no_version['api_version']
        
        provider = AzureOpenAIProvider(config_no_version)
        model_info = provider.get_model_info()
        
        assert model_info["deployment_info"]["api_version"] == "2024-02-15-preview"