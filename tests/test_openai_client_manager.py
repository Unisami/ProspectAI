"""
Unit tests for OpenAI Client Manager.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any

from services.openai_client_manager import (
    OpenAIClientManager,
    CompletionRequest,
    CompletionResponse,
    ClientType,
    get_client_manager,
    configure_default_client,
    get_default_client,
    make_completion
)
from utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config(
        notion_token="test_notion_token",
        hunter_api_key="test_hunter_key",
        openai_api_key="test_openai_key",
        use_azure_openai=False
    )


@pytest.fixture
def mock_azure_config():
    """Create a mock Azure OpenAI configuration for testing."""
    return Config(
        notion_token="test_notion_token",
        hunter_api_key="test_hunter_key",
        azure_openai_api_key="test_azure_key",
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_deployment_name="gpt-4",
        azure_openai_api_version="2024-02-15-preview",
        use_azure_openai=True
    )


@pytest.fixture
def client_manager():
    """Create a fresh client manager instance for testing."""
    # Reset singleton
    OpenAIClientManager._instance = None
    manager = OpenAIClientManager()
    yield manager
    # Cleanup
    manager.close_all_clients()


class TestOpenAIClientManager:
    """Test cases for OpenAI Client Manager."""
    
    def test_singleton_pattern(self):
        """Test that OpenAIClientManager follows singleton pattern."""
        # Reset singleton
        OpenAIClientManager._instance = None
        
        manager1 = OpenAIClientManager()
        manager2 = OpenAIClientManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_configure_openai_client(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test configuring a regular OpenAI client."""
        mock_http_client = Mock()
        mock_httpx_client.return_value = mock_http_client
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        client_manager.configure(mock_config, "test_client")
        
        # Verify HTTP client creation
        mock_httpx_client.assert_called_once()
        
        # Verify OpenAI client creation
        mock_openai.assert_called_once_with(
            api_key="test_openai_key",
            http_client=mock_http_client
        )
        
        # Verify client is stored
        assert "test_client" in client_manager._clients
        assert client_manager._clients["test_client"] == mock_openai_instance
        assert "test_client" in client_manager._configs
        assert client_manager._configs["test_client"] == mock_config
    
    @patch('services.openai_client_manager.AzureOpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_configure_azure_openai_client(self, mock_httpx_client, mock_azure_openai, client_manager, mock_azure_config):
        """Test configuring an Azure OpenAI client."""
        mock_http_client = Mock()
        mock_httpx_client.return_value = mock_http_client
        mock_azure_instance = Mock()
        mock_azure_openai.return_value = mock_azure_instance
        
        client_manager.configure(mock_azure_config, "azure_client")
        
        # Verify HTTP client creation
        mock_httpx_client.assert_called_once()
        
        # Verify Azure OpenAI client creation
        mock_azure_openai.assert_called_once_with(
            api_key="test_azure_key",
            azure_endpoint="https://test.openai.azure.com/",
            api_version="2024-02-15-preview",
            http_client=mock_http_client
        )
        
        # Verify client is stored
        assert "azure_client" in client_manager._clients
        assert client_manager._clients["azure_client"] == mock_azure_instance
    
    def test_configure_missing_openai_key(self, client_manager, mock_config):
        """Test configuration fails with missing OpenAI API key."""
        mock_config.openai_api_key = None
        
        # Keep PATH in environment to avoid httpx import issues
        with patch.dict(os.environ, {'PATH': os.environ.get('PATH', '')}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                client_manager.configure(mock_config, "test_client")
    
    def test_configure_missing_azure_key(self, client_manager, mock_azure_config):
        """Test configuration fails with missing Azure OpenAI API key."""
        mock_azure_config.azure_openai_api_key = None
        
        with pytest.raises(ValueError, match="Azure OpenAI API key is required"):
            client_manager.configure(mock_azure_config, "azure_client")
    
    def test_configure_missing_azure_endpoint(self, client_manager, mock_azure_config):
        """Test configuration fails with missing Azure OpenAI endpoint."""
        mock_azure_config.azure_openai_endpoint = None
        
        with pytest.raises(ValueError, match="Azure OpenAI endpoint is required"):
            client_manager.configure(mock_azure_config, "azure_client")
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_client(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test getting a configured client."""
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        client_manager.configure(mock_config, "test_client")
        retrieved_client = client_manager.get_client("test_client")
        
        assert retrieved_client == mock_openai_instance
    
    def test_get_unconfigured_client(self, client_manager):
        """Test getting an unconfigured client raises error."""
        with pytest.raises(ValueError, match="Client 'nonexistent' not configured"):
            client_manager.get_client("nonexistent")
    
    @patch('services.openai_client_manager.Config.from_env')
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_default_client_auto_configure(self, mock_httpx_client, mock_openai, mock_config_from_env, client_manager, mock_config):
        """Test auto-configuration of default client."""
        mock_config_from_env.return_value = mock_config
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        retrieved_client = client_manager.get_client("default")
        
        mock_config_from_env.assert_called_once()
        assert retrieved_client == mock_openai_instance
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_model_name_openai(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test getting model name for regular OpenAI client."""
        client_manager.configure(mock_config, "test_client")
        model_name = client_manager.get_model_name("test_client")
        
        assert model_name == "gpt-3.5-turbo"
    
    @patch('services.openai_client_manager.AzureOpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_model_name_azure(self, mock_httpx_client, mock_azure_openai, client_manager, mock_azure_config):
        """Test getting model name for Azure OpenAI client."""
        client_manager.configure(mock_azure_config, "azure_client")
        model_name = client_manager.get_model_name("azure_client")
        
        assert model_name == "gpt-4"
    
    def test_get_model_name_unconfigured(self, client_manager):
        """Test getting model name for unconfigured client raises error."""
        with pytest.raises(ValueError, match="Client 'nonexistent' not configured"):
            client_manager.get_model_name("nonexistent")
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_make_completion_success(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test successful completion request."""
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock response
        mock_choice = Mock()
        mock_choice.message.content = "Test response content"
        mock_choice.finish_reason = "stop"
        
        mock_usage = Mock()
        mock_usage.model_dump.return_value = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = mock_usage
        
        mock_openai_instance.chat.completions.create.return_value = mock_response
        
        # Configure client
        client_manager.configure(mock_config, "test_client")
        
        # Make completion request
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test message"}],
            temperature=0.5,
            max_tokens=100
        )
        
        response = client_manager.make_completion(request, "test_client")
        
        # Verify response
        assert response.success is True
        assert response.content == "Test response content"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        assert response.finish_reason == "stop"
        assert response.error_message is None
        
        # Verify API call
        mock_openai_instance.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test message"}],
            temperature=0.5,
            max_tokens=100,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_make_completion_rate_limit_error(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test completion request with rate limit error."""
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock rate limit error
        from openai import RateLimitError
        mock_openai_instance.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=Mock(),
            body={}
        )
        
        # Configure client
        client_manager.configure(mock_config, "test_client")
        
        # Make completion request
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test message"}]
        )
        
        response = client_manager.make_completion(request, "test_client")
        
        # Verify error response
        assert response.success is False
        assert response.content == ""
        assert response.finish_reason == "rate_limit_error"
        assert "Rate limit exceeded" in response.error_message
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_make_simple_completion(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test simple completion method."""
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock response
        mock_choice = Mock()
        mock_choice.message.content = "Simple response"
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = Mock()
        mock_response.usage.model_dump.return_value = {}
        
        mock_openai_instance.chat.completions.create.return_value = mock_response
        
        # Configure client
        client_manager.configure(mock_config, "test_client")
        
        # Make simple completion
        content = client_manager.make_simple_completion(
            messages=[{"role": "user", "content": "Test"}],
            client_id="test_client"
        )
        
        assert content == "Simple response"
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_make_simple_completion_error(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test simple completion method with error."""
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock error
        from openai import APIConnectionError
        mock_openai_instance.chat.completions.create.side_effect = APIConnectionError(
            message="Connection failed",
            request=Mock()
        )
        
        # Configure client
        client_manager.configure(mock_config, "test_client")
        
        # Make simple completion - should raise exception
        with pytest.raises(Exception, match="API connection error"):
            client_manager.make_simple_completion(
                messages=[{"role": "user", "content": "Test"}],
                client_id="test_client"
            )
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_list_clients(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test listing configured clients."""
        client_manager.configure(mock_config, "client1")
        client_manager.configure(mock_config, "client2")
        
        clients = client_manager.list_clients()
        
        assert "client1" in clients
        assert "client2" in clients
        assert len(clients) == 2
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_client_info_openai(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test getting client info for regular OpenAI client."""
        client_manager.configure(mock_config, "test_client")
        
        info = client_manager.get_client_info("test_client")
        
        assert info["client_id"] == "test_client"
        assert info["client_type"] == ClientType.OPENAI.value
        assert info["model_name"] == "gpt-3.5-turbo"
        assert info["endpoint"] == "https://api.openai.com"
        assert info["api_version"] == "v1"
        assert info["configured"] is True
    
    @patch('services.openai_client_manager.AzureOpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_client_info_azure(self, mock_httpx_client, mock_azure_openai, client_manager, mock_azure_config):
        """Test getting client info for Azure OpenAI client."""
        client_manager.configure(mock_azure_config, "azure_client")
        
        info = client_manager.get_client_info("azure_client")
        
        assert info["client_id"] == "azure_client"
        assert info["client_type"] == ClientType.AZURE_OPENAI.value
        assert info["model_name"] == "gpt-4"
        assert info["endpoint"] == "https://test.openai.azure.com/"
        assert info["api_version"] == "2024-02-15-preview"
        assert info["configured"] is True
    
    def test_get_client_info_unconfigured(self, client_manager):
        """Test getting client info for unconfigured client raises error."""
        with pytest.raises(ValueError, match="Client 'nonexistent' not configured"):
            client_manager.get_client_info("nonexistent")
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_close_client(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test closing a specific client."""
        mock_http_client = Mock()
        mock_httpx_client.return_value = mock_http_client
        
        client_manager.configure(mock_config, "test_client")
        
        # Verify client exists
        assert "test_client" in client_manager._clients
        assert "test_client" in client_manager._http_clients
        assert "test_client" in client_manager._configs
        
        # Close client
        client_manager.close_client("test_client")
        
        # Verify client is removed
        assert "test_client" not in client_manager._clients
        assert "test_client" not in client_manager._http_clients
        assert "test_client" not in client_manager._configs
        
        # Verify HTTP client was closed
        mock_http_client.close.assert_called_once()
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_close_all_clients(self, mock_httpx_client, mock_openai, client_manager, mock_config):
        """Test closing all clients."""
        mock_http_client1 = Mock()
        mock_http_client2 = Mock()
        mock_httpx_client.side_effect = [mock_http_client1, mock_http_client2]
        
        client_manager.configure(mock_config, "client1")
        client_manager.configure(mock_config, "client2")
        
        # Verify clients exist
        assert len(client_manager._clients) == 2
        
        # Close all clients
        client_manager.close_all_clients()
        
        # Verify all clients are removed
        assert len(client_manager._clients) == 0
        assert len(client_manager._http_clients) == 0
        assert len(client_manager._configs) == 0
        
        # Verify HTTP clients were closed
        mock_http_client1.close.assert_called_once()
        mock_http_client2.close.assert_called_once()


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    def test_get_client_manager_singleton(self):
        """Test that get_client_manager returns singleton."""
        # Reset global instance
        import services.openai_client_manager
        services.openai_client_manager._client_manager = None
        
        manager1 = get_client_manager()
        manager2 = get_client_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, OpenAIClientManager)
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_configure_default_client(self, mock_httpx_client, mock_openai, mock_config):
        """Test configuring default client via global function."""
        # Reset global instance
        import services.openai_client_manager
        services.openai_client_manager._client_manager = None
        
        configure_default_client(mock_config)
        
        manager = get_client_manager()
        assert "default" in manager._clients
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_get_default_client(self, mock_httpx_client, mock_openai, mock_config):
        """Test getting default client via global function."""
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Reset global instance
        import services.openai_client_manager
        services.openai_client_manager._client_manager = None
        
        configure_default_client(mock_config)
        client = get_default_client()
        
        assert client == mock_openai_instance
    
    @patch('services.openai_client_manager.OpenAI')
    @patch('services.openai_client_manager.httpx.Client')
    def test_make_completion_global(self, mock_httpx_client, mock_openai, mock_config):
        """Test making completion via global function."""
        # Setup mocks
        mock_openai_instance = Mock()
        mock_openai.return_value = mock_openai_instance
        
        # Mock response
        mock_choice = Mock()
        mock_choice.message.content = "Global response"
        mock_choice.finish_reason = "stop"
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        mock_response.model = "gpt-3.5-turbo"
        mock_response.usage = Mock()
        mock_response.usage.model_dump.return_value = {}
        
        mock_openai_instance.chat.completions.create.return_value = mock_response
        
        # Reset global instance
        import services.openai_client_manager
        services.openai_client_manager._client_manager = None
        
        configure_default_client(mock_config)
        
        content = make_completion(
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.8
        )
        
        assert content == "Global response"


class TestCompletionRequest:
    """Test cases for CompletionRequest dataclass."""
    
    def test_completion_request_defaults(self):
        """Test CompletionRequest with default values."""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test"}]
        )
        
        assert request.messages == [{"role": "user", "content": "Test"}]
        assert request.model is None
        assert request.temperature == 0.7
        assert request.max_tokens == 1000
        assert request.top_p == 1.0
        assert request.frequency_penalty == 0.0
        assert request.presence_penalty == 0.0
    
    def test_completion_request_custom_values(self):
        """Test CompletionRequest with custom values."""
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Test"}],
            model="gpt-4",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.2
        )
        
        assert request.model == "gpt-4"
        assert request.temperature == 0.5
        assert request.max_tokens == 500
        assert request.top_p == 0.9
        assert request.frequency_penalty == 0.1
        assert request.presence_penalty == 0.2


class TestCompletionResponse:
    """Test cases for CompletionResponse dataclass."""
    
    def test_completion_response_success(self):
        """Test CompletionResponse for successful completion."""
        response = CompletionResponse(
            content="Test response",
            model="gpt-3.5-turbo",
            usage={"total_tokens": 50},
            finish_reason="stop"
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-3.5-turbo"
        assert response.usage == {"total_tokens": 50}
        assert response.finish_reason == "stop"
        assert response.success is True
        assert response.error_message is None
    
    def test_completion_response_error(self):
        """Test CompletionResponse for failed completion."""
        response = CompletionResponse(
            content="",
            model="gpt-3.5-turbo",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API error occurred"
        )
        
        assert response.content == ""
        assert response.success is False
        assert response.error_message == "API error occurred"
        assert response.finish_reason == "error"