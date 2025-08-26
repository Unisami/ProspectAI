"""
Tests for DeepSeek Provider Implementation

Comprehensive tests for the DeepSeek provider including configuration validation,
completion requests, error handling, and model information retrieval.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.deepseek_provider import DeepSeekProvider
from services.providers.base_provider import ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class TestDeepSeekProvider:
    """Test suite for DeepSeek provider implementation."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.config = {
            'api_key': 'sk-test-deepseek-key',
            'model': 'deepseek-chat',
            'temperature': 0.7,
            'max_tokens': 1000,
            'base_url': 'https://api.deepseek.com'
        }
        
        self.test_request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello, how are you?"}],
            max_tokens=100,
            temperature=0.7
        )
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_provider_initialization_success(self, mock_openai):
        """Test successful provider initialization."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        
        assert provider.client == mock_client
        assert provider.provider_name == "deepseek"
        mock_openai.assert_called_once_with(
            api_key='sk-test-deepseek-key',
            base_url='https://api.deepseek.com'
        )
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_provider_initialization_no_api_key(self, mock_openai):
        """Test provider initialization without API key."""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = DeepSeekProvider(config_no_key)
            
            assert provider.client is None
            mock_openai.assert_not_called()
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_provider_initialization_from_env(self, mock_openai):
        """Test provider initialization using environment variable."""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'sk-env-key'}):
            provider = DeepSeekProvider(config_no_key)
            
            assert provider.client == mock_client
            mock_openai.assert_called_once_with(
                api_key='sk-env-key',
                base_url='https://api.deepseek.com'
            )
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_make_completion_success(self, mock_openai):
        """Test successful completion request."""
        # Setup mock response
        mock_choice = Mock()
        mock_choice.message.content = "Hello! I'm doing well, thank you for asking."
        mock_choice.finish_reason = "stop"
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 15
        mock_usage.total_tokens = 25
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        response = provider.make_completion(self.test_request)
        
        assert response.success is True
        assert response.content == "Hello! I'm doing well, thank you for asking."
        assert response.model == "deepseek-chat"
        assert response.usage["prompt_tokens"] == 10
        assert response.usage["completion_tokens"] == 15
        assert response.usage["total_tokens"] == 25
        assert response.finish_reason == "stop"
        
        # Verify API call parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "deepseek-chat"
        assert call_args["messages"] == self.test_request.messages
        assert call_args["max_tokens"] == 100
        assert call_args["temperature"] == 0.7
        assert call_args["stream"] is False
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_make_completion_custom_model(self, mock_openai):
        """Test completion request with custom model."""
        mock_choice = Mock()
        mock_choice.message.content = "Code generated successfully."
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock()
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        
        # Test with custom model in request
        custom_request = CompletionRequest(
            messages=[{"role": "user", "content": "Write a Python function"}],
            max_tokens=200,
            temperature=0.3,
            model="deepseek-coder"
        )
        
        response = provider.make_completion(custom_request)
        
        assert response.success is True
        assert response.model == "deepseek-coder"
        
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["model"] == "deepseek-coder"
    
    def test_make_completion_no_client(self):
        """Test completion request when client is not configured."""
        provider = DeepSeekProvider({})  # No API key
        response = provider.make_completion(self.test_request)
        
        assert response.success is False
        assert response.error_message == "DeepSeek client not configured"
        assert response.content == ""
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_make_completion_authentication_error(self, mock_openai):
        """Test handling of authentication errors."""
        from openai import AuthenticationError
        
        mock_client = Mock()
        # Create proper AuthenticationError with required parameters
        mock_response = Mock()
        mock_response.status_code = 401
        auth_error = AuthenticationError(
            message="Invalid API key",
            response=mock_response,
            body={"error": {"message": "Invalid API key"}}
        )
        mock_client.chat.completions.create.side_effect = auth_error
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        response = provider.make_completion(self.test_request)
        
        assert response.success is False
        assert "Authentication error" in response.error_message
        assert response.finish_reason == "error"
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_make_completion_rate_limit_error(self, mock_openai):
        """Test handling of rate limit errors."""
        from openai import RateLimitError
        
        mock_client = Mock()
        # Create proper RateLimitError with required parameters
        mock_response = Mock()
        mock_response.status_code = 429
        rate_error = RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body={"error": {"message": "Rate limit exceeded"}}
        )
        mock_client.chat.completions.create.side_effect = rate_error
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        response = provider.make_completion(self.test_request)
        
        assert response.success is False
        assert "Rate limit exceeded" in response.error_message
        assert response.finish_reason == "error"
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_make_completion_api_error(self, mock_openai):
        """Test handling of general API errors."""
        from openai import APIError
        
        mock_client = Mock()
        # Create proper APIError with required parameters
        mock_request = Mock()
        api_error = APIError(
            message="Server error",
            request=mock_request,
            body={"error": {"message": "Server error"}}
        )
        mock_client.chat.completions.create.side_effect = api_error
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        response = provider.make_completion(self.test_request)
        
        assert response.success is False
        assert "DeepSeek API error" in response.error_message
        assert response.finish_reason == "error"
    
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(self.config)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.SUCCESS
            assert "DeepSeek configuration is valid" in result.message
            assert result.details["api_key_present"] is True
            assert result.details["model"] == "deepseek-chat"
            assert result.details["provider"] == "deepseek"
    
    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = DeepSeekProvider(config_no_key)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "DeepSeek API key is required" in result.message
            assert "api_key" in result.details["missing_config"]
    
    def test_validate_config_invalid_api_key_format(self):
        """Test configuration validation with invalid API key format."""
        config_invalid_key = self.config.copy()
        config_invalid_key['api_key'] = 'invalid-key-format'
        
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(config_invalid_key)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.WARNING
            assert "API key format may be invalid" in result.message
    
    def test_validate_config_unknown_model(self):
        """Test configuration validation with unknown model."""
        config_unknown_model = self.config.copy()
        config_unknown_model['model'] = 'unknown-model'
        
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(config_unknown_model)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.WARNING
            assert "may not be available" in result.message
            assert result.details["model"] == "unknown-model"
    
    def test_validate_config_insecure_base_url(self):
        """Test configuration validation with insecure base URL."""
        config_insecure = self.config.copy()
        config_insecure['base_url'] = 'http://api.deepseek.com'
        
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(config_insecure)
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.WARNING
            assert "should use HTTPS" in result.message
    
    def test_get_model_info(self):
        """Test model information retrieval."""
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(self.config)
            model_info = provider.get_model_info()
            
            assert model_info["provider"] == "deepseek"
            assert model_info["default_model"] == "deepseek-chat"
            assert model_info["supports_streaming"] is True
            assert model_info["supports_function_calling"] is False
            assert model_info["base_url"] == "https://api.deepseek.com"
            
            # Check available models
            models = model_info["available_models"]
            model_names = [model["name"] for model in models]
            assert "deepseek-chat" in model_names
            assert "deepseek-coder" in model_names
            assert "deepseek-math" in model_names
            assert "deepseek-reasoner" in model_names
            
            # Check features
            features = model_info["features"]
            assert "Code generation and analysis" in features
            assert "Mathematical reasoning" in features
            assert "Cost-effective pricing" in features
            assert "OpenAI-compatible API" in features
    
    def test_get_provider_name(self):
        """Test provider name retrieval."""
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(self.config)
            assert provider.get_provider_name() == "deepseek"
    
    def test_get_config_security(self):
        """Test that sensitive configuration is masked."""
        with patch('services.providers.deepseek_provider.OpenAI'):
            provider = DeepSeekProvider(self.config)
            safe_config = provider.get_config()
            
            assert safe_config["api_key"] == "***"
            assert safe_config["model"] == "deepseek-chat"
            assert safe_config["base_url"] == "https://api.deepseek.com"
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_test_connection_success(self, mock_openai):
        """Test successful connection test."""
        # Setup mock response for connection test
        mock_choice = Mock()
        mock_choice.message.content = "Hello"
        mock_choice.finish_reason = "stop"
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 1
        mock_usage.total_tokens = 6
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "Connection to deepseek successful" in result.message
        assert result.details["model"] == "deepseek-chat"
        assert result.details["usage"]["total_tokens"] == 6
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_test_connection_failure(self, mock_openai):
        """Test connection test failure."""
        from openai import AuthenticationError
        
        mock_client = Mock()
        # Create proper AuthenticationError with required parameters
        mock_response = Mock()
        mock_response.status_code = 401
        auth_error = AuthenticationError(
            message="Invalid key",
            response=mock_response,
            body={"error": {"message": "Invalid key"}}
        )
        mock_client.chat.completions.create.side_effect = auth_error
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.ERROR
        assert "Connection test failed" in result.message
        # The test_connection method catches exceptions and includes error_type in details
        if result.details:
            assert result.details["error_type"] == "AuthenticationError"
    
    @patch('services.providers.deepseek_provider.OpenAI')
    def test_completion_with_optional_parameters(self, mock_openai):
        """Test completion request with optional parameters."""
        mock_choice = Mock()
        mock_choice.message.content = "Response with parameters"
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.usage = Mock()
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = DeepSeekProvider(self.config)
        
        # Create request with optional parameters
        request_with_params = CompletionRequest(
            messages=[{"role": "user", "content": "Test"}],
            max_tokens=100,
            temperature=0.5
        )
        # Add optional parameters
        request_with_params.top_p = 0.9
        request_with_params.frequency_penalty = 0.1
        request_with_params.presence_penalty = 0.2
        
        response = provider.make_completion(request_with_params)
        
        assert response.success is True
        
        # Verify optional parameters were passed
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["top_p"] == 0.9
        assert call_args["frequency_penalty"] == 0.1
        assert call_args["presence_penalty"] == 0.2


if __name__ == "__main__":
    pytest.main([__file__])