"""
Tests for OpenAI Provider Implementation

Tests the OpenAI provider wrapper to ensure it works correctly with the existing
OpenAI client manager while maintaining backward compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.openai_provider import OpenAIProvider
from services.providers.base_provider import ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class TestOpenAIProvider:
    """Test cases for OpenAI provider implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'api_key': 'sk-test-key-123',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 1000
        }
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_provider_initialization(self, mock_client_manager):
        """Test that the provider initializes correctly."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Create provider
        provider = OpenAIProvider(self.config)
        
        # Verify initialization
        assert provider.provider_name == 'openai'
        assert provider.config == self.config
        assert provider.client_manager == mock_manager_instance
        
        # Verify client manager was configured
        mock_manager_instance.configure.assert_called_once()
        
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_make_completion_success(self, mock_client_manager):
        """Test successful completion request."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock successful response
        mock_response = CompletionResponse(
            content="Hello! How can I help you?",
            model="gpt-3.5-turbo",
            usage={"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request
        provider = OpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-3.5-turbo"
        )
        
        response = provider.make_completion(request)
        
        # Verify response
        assert response.success is True
        assert response.content == "Hello! How can I help you?"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage["total_tokens"] == 18
        
        # Verify client manager was called correctly
        mock_manager_instance.make_completion.assert_called_once()
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_make_completion_with_default_model(self, mock_client_manager):
        """Test completion request uses default model when none specified."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        mock_response = CompletionResponse(
            content="Response",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request without model
        provider = OpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        # Verify default model was used
        assert request.model == "gpt-3.5-turbo"
        assert response.success is True
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_make_completion_error_handling(self, mock_client_manager):
        """Test error handling in completion requests."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock error response
        mock_response = CompletionResponse(
            content="",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API rate limit exceeded"
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and make request
        provider = OpenAIProvider(self.config)
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        # Verify error response
        assert response.success is False
        assert response.error_message == "API rate limit exceeded"
        assert response.content == ""
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        provider = OpenAIProvider(self.config)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "valid" in result.message.lower()
        assert result.details["api_key_present"] is True
        assert result.details["model"] == "gpt-3.5-turbo"
    
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key."""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider(config_no_key)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "api key is required" in result.message.lower()
            assert "api_key" in result.details["missing_config"]
    
    def test_validate_config_invalid_api_key_format(self):
        """Test validation with invalid API key format."""
        config_invalid_key = self.config.copy()
        config_invalid_key['api_key'] = 'invalid-key-format'
        
        provider = OpenAIProvider(config_invalid_key)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.WARNING
        assert "format may be invalid" in result.message.lower()
    
    def test_validate_config_unknown_model(self):
        """Test validation with unknown model."""
        config_unknown_model = self.config.copy()
        config_unknown_model['model'] = 'unknown-model'
        
        provider = OpenAIProvider(config_unknown_model)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.WARNING
        assert "may not be available" in result.message.lower()
    
    def test_get_model_info(self):
        """Test getting model information."""
        provider = OpenAIProvider(self.config)
        model_info = provider.get_model_info()
        
        assert model_info["provider"] == "openai"
        assert "available_models" in model_info
        assert len(model_info["available_models"]) > 0
        assert model_info["default_model"] == "gpt-3.5-turbo"
        assert model_info["supports_streaming"] is True
        assert model_info["supports_function_calling"] is True
        
        # Check that GPT-4 and GPT-3.5-turbo are in available models
        model_names = [model["name"] for model in model_info["available_models"]]
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_get_client_info(self, mock_client_manager):
        """Test getting client information."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        mock_client_info = {
            "client_id": "test_client",
            "client_type": "openai",
            "model_name": "gpt-3.5-turbo",
            "configured": True
        }
        mock_manager_instance.get_client_info.return_value = mock_client_info
        
        # Create provider and get client info
        provider = OpenAIProvider(self.config)
        client_info = provider.get_client_info()
        
        assert client_info == mock_client_info
        mock_manager_instance.get_client_info.assert_called_once()
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_get_client_info_error(self, mock_client_manager):
        """Test error handling when getting client info."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        mock_manager_instance.get_client_info.side_effect = Exception("Client not found")
        
        # Create provider and get client info
        provider = OpenAIProvider(self.config)
        client_info = provider.get_client_info()
        
        assert "error" in client_info
        assert "Client not found" in client_info["error"]
        assert client_info["provider"] == "openai"
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_provider_cleanup(self, mock_client_manager):
        """Test that provider cleans up resources properly."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Create and destroy provider
        provider = OpenAIProvider(self.config)
        client_id = provider.client_id
        
        # Manually call cleanup (normally called by __del__)
        provider.__del__()
        
        # Verify cleanup was called
        mock_manager_instance.close_client.assert_called_once_with(client_id)
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-env-key-456'})
    def test_api_key_from_environment(self):
        """Test that API key can be loaded from environment variables."""
        config_no_key = {
            'model': 'gpt-3.5-turbo'
        }
        
        provider = OpenAIProvider(config_no_key)
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.SUCCESS
        assert result.details["api_key_present"] is True
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_connection_test_success(self, mock_client_manager):
        """Test successful connection test."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        
        # Mock successful test response
        mock_response = CompletionResponse(
            content="Hello",
            model="gpt-3.5-turbo",
            usage={"total_tokens": 5},
            finish_reason="stop",
            success=True
        )
        mock_manager_instance.make_completion.return_value = mock_response
        
        # Create provider and test connection
        provider = OpenAIProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "successful" in result.message.lower()
        assert result.details["model"] == "gpt-3.5-turbo"
        assert result.details["usage"]["total_tokens"] == 5
    
    @patch('services.providers.openai_provider.OpenAIClientManager')
    def test_connection_test_failure(self, mock_client_manager):
        """Test connection test failure."""
        # Setup mock
        mock_manager_instance = Mock()
        mock_client_manager.return_value = mock_manager_instance
        mock_manager_instance.make_completion.side_effect = Exception("Connection failed")
        
        # Create provider and test connection
        provider = OpenAIProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.ERROR
        assert "failed" in result.message.lower()
        assert "Connection failed" in result.message or "Empty response" in result.message