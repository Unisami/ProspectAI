"""
Tests for Anthropic Claude Provider

Comprehensive tests for the Anthropic provider implementation including
configuration validation, completion requests, error handling, and model info.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.anthropic_provider import AnthropicProvider
from services.providers.base_provider import ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class TestAnthropicProvider:
    """Test suite for AnthropicProvider"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'api_key': 'sk-ant-test-key-12345',
            'model': 'claude-3-sonnet-20240229',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
    def test_provider_initialization(self):
        """Test provider initialization with valid config"""
        provider = AnthropicProvider(self.config)
        
        assert provider.provider_name == 'anthropic'
        assert provider.config == self.config
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_client_configuration_success(self, mock_anthropic_class):
        """Test successful client configuration"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        provider = AnthropicProvider(self.config)
        
        mock_anthropic_class.assert_called_once_with(api_key='sk-ant-test-key-12345')
        assert provider.client == mock_client
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_client_configuration_from_env(self, mock_anthropic_class):
        """Test client configuration from environment variable"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-ant-env-key'}):
            provider = AnthropicProvider(config_without_key)
            
        mock_anthropic_class.assert_called_once_with(api_key='sk-ant-env-key')
        
    def test_client_configuration_no_key(self):
        """Test client configuration without API key"""
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider(config_without_key)
            
        assert provider.client is None
        
    def test_convert_messages_to_anthropic_format(self):
        """Test message format conversion"""
        provider = AnthropicProvider(self.config)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        system_msg, conversation_msgs = provider._convert_messages_to_anthropic_format(messages)
        
        assert system_msg == "You are a helpful assistant"
        assert len(conversation_msgs) == 3
        assert conversation_msgs[0] == {"role": "user", "content": "Hello"}
        assert conversation_msgs[1] == {"role": "assistant", "content": "Hi there!"}
        assert conversation_msgs[2] == {"role": "user", "content": "How are you?"}
        
    def test_convert_messages_no_system(self):
        """Test message conversion without system message"""
        provider = AnthropicProvider(self.config)
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        system_msg, conversation_msgs = provider._convert_messages_to_anthropic_format(messages)
        
        assert system_msg == ""
        assert len(conversation_msgs) == 2
        
    def test_convert_messages_unknown_role(self):
        """Test message conversion with unknown role"""
        provider = AnthropicProvider(self.config)
        
        messages = [
            {"role": "unknown", "content": "Test message"}
        ]
        
        system_msg, conversation_msgs = provider._convert_messages_to_anthropic_format(messages)
        
        assert system_msg == ""
        assert len(conversation_msgs) == 1
        assert conversation_msgs[0] == {"role": "user", "content": "Test message"}
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_make_completion_success(self, mock_anthropic_class):
        """Test successful completion request"""
        # Mock the Anthropic client and response
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock response object
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello! How can I help you?")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=8)
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create.return_value = mock_response
        
        provider = AnthropicProvider(self.config)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-3-sonnet-20240229",
            temperature=0.7,
            max_tokens=100
        )
        
        response = provider.make_completion(request)
        
        # Verify the API call
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-sonnet-20240229",
            max_tokens=100,
            temperature=0.7,
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        # Verify the response
        assert response.success is True
        assert response.content == "Hello! How can I help you?"
        assert response.model == "claude-3-sonnet-20240229"
        assert response.usage == {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
        assert response.finish_reason == "end_turn"
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_make_completion_with_system_message(self, mock_anthropic_class):
        """Test completion request with system message"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=3)
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create.return_value = mock_response
        
        provider = AnthropicProvider(self.config)
        
        request = CompletionRequest(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ],
            max_tokens=50
        )
        
        provider.make_completion(request)
        
        # Verify system message is passed separately
        mock_client.messages.create.assert_called_once_with(
            model="claude-3-sonnet-20240229",
            max_tokens=50,
            temperature=0.7,
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful"
        )
        
    def test_make_completion_no_client(self):
        """Test completion request without configured client"""
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider(config_without_key)
            
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        assert response.success is False
        assert response.error_message == "Anthropic client not configured"
        assert response.content == ""
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_make_completion_api_error(self, mock_anthropic_class):
        """Test completion request with API error"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock API error with proper constructor
        from anthropic import APIError
        import httpx
        
        mock_request = Mock(spec=httpx.Request)
        api_error = APIError("API Error", mock_request, body=None)
        mock_client.messages.create.side_effect = api_error
        
        provider = AnthropicProvider(self.config)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        assert response.success is False
        assert "Anthropic API error" in response.error_message
        assert response.content == ""
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_make_completion_rate_limit_error(self, mock_anthropic_class):
        """Test completion request with rate limit error"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock rate limit error with proper constructor
        from anthropic import RateLimitError
        import httpx
        
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"request-id": "test-request-id"}
        rate_limit_error = RateLimitError("Rate limit exceeded", response=mock_response, body=None)
        mock_client.messages.create.side_effect = rate_limit_error
        
        provider = AnthropicProvider(self.config)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        assert response.success is False
        assert "Rate limit exceeded" in response.error_message
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_make_completion_auth_error(self, mock_anthropic_class):
        """Test completion request with authentication error"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock authentication error with proper constructor
        from anthropic import AuthenticationError
        import httpx
        
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.headers = {"request-id": "test-request-id"}
        auth_error = AuthenticationError("Invalid API key", response=mock_response, body=None)
        mock_client.messages.create.side_effect = auth_error
        
        provider = AnthropicProvider(self.config)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}]
        )
        
        response = provider.make_completion(request)
        
        assert response.success is False
        assert "Authentication error" in response.error_message
        
    def test_validate_config_success(self):
        """Test successful configuration validation"""
        with patch('services.providers.anthropic_provider.Anthropic'):
            provider = AnthropicProvider(self.config)
            
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "Anthropic configuration is valid" in result.message
        assert result.details['api_key_present'] is True
        assert result.details['model'] == 'claude-3-sonnet-20240229'
        assert result.details['provider'] == 'anthropic'
        
    def test_validate_config_missing_api_key(self):
        """Test validation with missing API key"""
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider(config_without_key)
            
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.ERROR
        assert "API key is required" in result.message
        assert "api_key" in result.details['missing_config']
        
    def test_validate_config_invalid_key_format(self):
        """Test validation with invalid API key format"""
        invalid_config = {
            'api_key': 'invalid-key-format',
            'model': 'claude-3-sonnet-20240229'
        }
        
        with patch('services.providers.anthropic_provider.Anthropic'):
            provider = AnthropicProvider(invalid_config)
            
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.WARNING
        assert "API key format may be invalid" in result.message
        
    def test_validate_config_invalid_model(self):
        """Test validation with invalid model"""
        invalid_model_config = {
            'api_key': 'sk-ant-test-key',
            'model': 'invalid-model-name'
        }
        
        with patch('services.providers.anthropic_provider.Anthropic'):
            provider = AnthropicProvider(invalid_model_config)
            
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.WARNING
        assert "may not be available" in result.message
        
    def test_validate_config_client_not_initialized(self):
        """Test validation when client initialization fails"""
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider(config_without_key)
            
        result = provider.validate_config()
        
        assert result.status == ValidationStatus.ERROR
        assert "API key is required" in result.message
        
    def test_get_model_info(self):
        """Test getting model information"""
        provider = AnthropicProvider(self.config)
        
        model_info = provider.get_model_info()
        
        assert model_info['provider'] == 'anthropic'
        assert model_info['default_model'] == 'claude-3-sonnet-20240229'
        assert model_info['supports_streaming'] is True
        assert model_info['supports_function_calling'] is False
        assert len(model_info['available_models']) >= 6
        
        # Check specific models are present
        model_names = [model['name'] for model in model_info['available_models']]
        assert 'claude-3-opus-20240229' in model_names
        assert 'claude-3-sonnet-20240229' in model_names
        assert 'claude-3-haiku-20240307' in model_names
        
    def test_get_provider_name(self):
        """Test getting provider name"""
        provider = AnthropicProvider(self.config)
        
        assert provider.get_provider_name() == 'anthropic'
        
    def test_get_config_masks_sensitive_data(self):
        """Test that get_config masks sensitive information"""
        provider = AnthropicProvider(self.config)
        
        safe_config = provider.get_config()
        
        assert safe_config['api_key'] == '***'
        assert safe_config['model'] == 'claude-3-sonnet-20240229'
        
    @patch('services.providers.anthropic_provider.Anthropic')
    def test_test_connection_success(self, mock_anthropic_class):
        """Test successful connection test"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Mock successful response
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello")]
        mock_response.usage = Mock(input_tokens=5, output_tokens=3)
        mock_response.stop_reason = "end_turn"
        
        mock_client.messages.create.return_value = mock_response
        
        provider = AnthropicProvider(self.config)
        
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.SUCCESS
        assert "Connection to anthropic successful" in result.message
        
    def test_test_connection_no_client(self):
        """Test connection test without configured client"""
        config_without_key = {'model': 'claude-3-sonnet-20240229'}
        
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider(config_without_key)
            
        result = provider.test_connection()
        
        assert result.status == ValidationStatus.ERROR
        assert "Connection test failed" in result.message


if __name__ == "__main__":
    pytest.main([__file__])