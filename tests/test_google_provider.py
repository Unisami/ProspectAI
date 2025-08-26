"""
Tests for Google Gemini Provider

Comprehensive tests for the Google provider implementation including
configuration validation, completion requests, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

from services.providers.google_provider import GoogleProvider
from services.providers.base_provider import ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class TestGoogleProvider:
    """Test suite for Google Gemini provider"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = {
            'api_key': 'test_google_api_key_12345678901234567890',
            'model': 'gemini-2.0-flash',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
    def test_provider_initialization(self):
        """Test provider initialization with valid config"""
        with patch('google.generativeai.configure') as mock_configure:
            provider = GoogleProvider(self.config)
            
            assert provider.provider_name == 'google'
            assert provider.config == self.config
            mock_configure.assert_called_once_with(api_key=self.config['api_key'])
            assert provider.client_configured is True
    
    def test_provider_initialization_no_api_key(self):
        """Test provider initialization without API key"""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = GoogleProvider(config_no_key)
            assert provider.client_configured is False
    
    def test_provider_initialization_from_env(self):
        """Test provider initialization with API key from environment"""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'env_api_key'}):
            with patch('google.generativeai.configure') as mock_configure:
                provider = GoogleProvider(config_no_key)
                mock_configure.assert_called_once_with(api_key='env_api_key')
                assert provider.client_configured is True
    
    def test_convert_messages_to_gemini_format(self):
        """Test message format conversion"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
                {"role": "user", "content": "How are you?"}
            ]
            
            system_instruction, conversation_history = provider._convert_messages_to_gemini_format(messages)
            
            assert system_instruction == "You are a helpful assistant"
            assert len(conversation_history) == 3
            assert conversation_history[0] == {"role": "user", "parts": ["Hello"]}
            assert conversation_history[1] == {"role": "model", "parts": ["Hi there!"]}
            assert conversation_history[2] == {"role": "user", "parts": ["How are you?"]}
    
    def test_make_completion_success(self):
        """Test successful completion request"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            # Mock the response
            mock_response = Mock()
            mock_response.text = "Hello! How can I help you today?"
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 10
            mock_response.usage_metadata.candidates_token_count = 15
            mock_response.usage_metadata.total_token_count = 25
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].finish_reason = "STOP"
            
            # Mock the model
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=100,
                    temperature=0.7
                )
                
                response = provider.make_completion(request)
                
                assert response.success is True
                assert response.content == "Hello! How can I help you today?"
                assert response.model == "gemini-2.5-flash"
                assert response.usage["prompt_tokens"] == 10
                assert response.usage["completion_tokens"] == 15
                assert response.usage["total_tokens"] == 25
                assert response.finish_reason == "stop"
    
    def test_make_completion_with_conversation_history(self):
        """Test completion with multi-turn conversation"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            # Mock the response
            mock_response = Mock()
            mock_response.text = "I'm doing well, thank you!"
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 20
            mock_response.usage_metadata.candidates_token_count = 10
            mock_response.usage_metadata.total_token_count = 30
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].finish_reason = "STOP"
            
            # Mock the chat
            mock_chat = Mock()
            mock_chat.send_message.return_value = mock_response
            
            # Mock the model
            mock_model = Mock()
            mock_model.start_chat.return_value = mock_chat
            
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                request = CompletionRequest(
                    messages=[
                        {"role": "user", "content": "Hello"},
                        {"role": "assistant", "content": "Hi there!"},
                        {"role": "user", "content": "How are you?"}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
                
                response = provider.make_completion(request)
                
                assert response.success is True
                assert response.content == "I'm doing well, thank you!"
                mock_model.start_chat.assert_called_once()
                mock_chat.send_message.assert_called_once_with("How are you?")
    
    def test_make_completion_client_not_configured(self):
        """Test completion when client is not configured"""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = GoogleProvider(config_no_key)
            
            request = CompletionRequest(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=100,
                temperature=0.7
            )
            
            response = provider.make_completion(request)
            
            assert response.success is False
            assert "not configured" in response.error_message
    
    def test_make_completion_authentication_error(self):
        """Test completion with authentication error"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            from google.api_core import exceptions as google_exceptions
            
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                mock_model.generate_content.side_effect = google_exceptions.Unauthenticated("Invalid API key")
                mock_model_class.return_value = mock_model
                
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=100,
                    temperature=0.7
                )
                
                response = provider.make_completion(request)
                
                assert response.success is False
                assert "Authentication error" in response.error_message
    
    def test_make_completion_rate_limit_error(self):
        """Test completion with rate limit error"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            from google.api_core import exceptions as google_exceptions
            
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                mock_model.generate_content.side_effect = google_exceptions.ResourceExhausted("Rate limit exceeded")
                mock_model_class.return_value = mock_model
                
                request = CompletionRequest(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=100,
                    temperature=0.7
                )
                
                response = provider.make_completion(request)
                
                assert response.success is False
                assert "Rate limit exceeded" in response.error_message
    
    def test_validate_config_success(self):
        """Test successful configuration validation"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.SUCCESS
            assert "valid" in result.message.lower()
            assert result.details["api_key_present"] is True
            assert result.details["model"] == "gemini-2.5-flash"
            assert result.details["provider"] == "google"
    
    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key"""
        config_no_key = self.config.copy()
        del config_no_key['api_key']
        
        with patch.dict(os.environ, {}, clear=True):
            provider = GoogleProvider(config_no_key)
            
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.ERROR
            assert "API key is required" in result.message
            assert "api_key" in result.details["missing_config"]
    
    def test_validate_config_short_api_key(self):
        """Test configuration validation with short API key"""
        config_short_key = self.config.copy()
        config_short_key['api_key'] = 'short_key'
        
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(config_short_key)
            
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.WARNING
            assert "too short" in result.message
    
    def test_validate_config_invalid_model(self):
        """Test configuration validation with invalid model"""
        config_invalid_model = self.config.copy()
        config_invalid_model['model'] = 'invalid-model'
        
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(config_invalid_model)
            
            result = provider.validate_config()
            
            assert result.status == ValidationStatus.WARNING
            assert "may not be available" in result.message
    
    def test_get_model_info(self):
        """Test getting model information"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            model_info = provider.get_model_info()
            
            assert model_info["provider"] == "google"
            assert "available_models" in model_info
            assert len(model_info["available_models"]) > 0
            assert model_info["default_model"] == "gemini-2.5-flash"
            assert model_info["supports_streaming"] is True
            assert model_info["supports_function_calling"] is True
            assert model_info["supports_vision"] is True
            
            # Check that all models have required fields
            for model in model_info["available_models"]:
                assert "name" in model
                assert "description" in model
                assert "context_length" in model
                assert "training_data" in model
    
    def test_get_provider_name(self):
        """Test getting provider name"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            assert provider.get_provider_name() == "google"
    
    def test_get_config_masks_sensitive_data(self):
        """Test that get_config masks sensitive information"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            safe_config = provider.get_config()
            
            assert safe_config['api_key'] == '***'
            assert safe_config['model'] == 'gemini-2.5-flash'
            assert safe_config['temperature'] == 0.7
    
    def test_test_connection_success(self):
        """Test successful connection test"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            # Mock successful completion
            mock_response = Mock()
            mock_response.text = "Hello"
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.prompt_token_count = 5
            mock_response.usage_metadata.candidates_token_count = 5
            mock_response.usage_metadata.total_token_count = 10
            mock_response.candidates = [Mock()]
            mock_response.candidates[0].finish_reason = "STOP"
            
            mock_model = Mock()
            mock_model.generate_content.return_value = mock_response
            
            with patch('google.generativeai.GenerativeModel', return_value=mock_model):
                result = provider.test_connection()
                
                assert result.status == ValidationStatus.SUCCESS
                assert "successful" in result.message.lower()
    
    def test_test_connection_failure(self):
        """Test connection test failure"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                mock_model = Mock()
                mock_model.generate_content.side_effect = Exception("Connection failed")
                mock_model_class.return_value = mock_model
                
                result = provider.test_connection()
                
                assert result.status == ValidationStatus.ERROR
                assert "Connection test failed" in result.message
    
    def test_safety_settings(self):
        """Test that safety settings are properly configured"""
        with patch('google.generativeai.configure'):
            provider = GoogleProvider(self.config)
            
            safety_settings = provider._get_safety_settings()
            
            assert len(safety_settings) == 4
            
            # Check that all required categories are present
            categories = [setting["category"] for setting in safety_settings]
            from google.generativeai.types import HarmCategory
            
            assert HarmCategory.HARM_CATEGORY_HARASSMENT in categories
            assert HarmCategory.HARM_CATEGORY_HATE_SPEECH in categories
            assert HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT in categories
            assert HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT in categories


if __name__ == "__main__":
    pytest.main([__file__])