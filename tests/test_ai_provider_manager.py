"""
Tests for AI Provider Manager

Comprehensive tests for the AI provider manager functionality including
provider registration, discovery, instantiation, and validation.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from services.ai_provider_manager import (
    AIProviderManager,
    ProviderType,
    ProviderInfo,
    get_provider_manager,
    configure_provider_manager,
    get_active_provider,
    make_completion
)
from services.providers.base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse
from utils.config import Config


class MockProvider(BaseAIProvider):
    """Mock provider for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_name = "mock"
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        return CompletionResponse(
            content="Mock response",
            model="mock-model",
            usage={"total_tokens": 10},
            finish_reason="stop",
            success=True
        )
    
    def validate_config(self) -> ValidationResult:
        if "api_key" in self.config and self.config["api_key"]:
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                message="Configuration is valid"
            )
        else:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message="API key is required"
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "models": ["mock-model"],
            "capabilities": ["text-generation"]
        }


class TestAIProviderManager:
    """Test cases for AI Provider Manager"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Reset singleton instance
        AIProviderManager._instance = None
        
        # Create fresh manager instance
        self.manager = AIProviderManager()
        
        # Create mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.openai_api_key = "test-openai-key"
        self.mock_config.azure_openai_api_key = None
        self.mock_config.azure_openai_endpoint = None
        self.mock_config.azure_openai_deployment_name = "gpt-4"
        self.mock_config.azure_openai_api_version = "2024-02-15-preview"
        self.mock_config.use_azure_openai = False
    
    def test_singleton_pattern(self):
        """Test that AIProviderManager follows singleton pattern"""
        manager1 = AIProviderManager()
        manager2 = AIProviderManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_builtin_providers_registered(self):
        """Test that built-in providers are registered on initialization"""
        providers = self.manager.list_providers()
        
        expected_providers = ["openai", "azure-openai", "anthropic", "google", "deepseek"]
        for provider in expected_providers:
            assert provider in providers
        
        # Check provider info
        openai_info = self.manager.get_provider_info("openai")
        assert openai_info.name == "openai"
        assert openai_info.provider_type == ProviderType.OPENAI
        assert "openai_api_key" in openai_info.required_config
    
    def test_register_custom_provider(self):
        """Test registering a custom provider"""
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider for testing",
            required_config=["api_key"],
            optional_config=["model"]
        )
        
        providers = self.manager.list_providers()
        assert "mock" in providers
        
        mock_info = self.manager.get_provider_info("mock")
        assert mock_info.name == "mock"
        assert mock_info.description == "Mock provider for testing"
        assert mock_info.required_config == ["api_key"]
        assert mock_info.optional_config == ["model"]
    
    def test_register_invalid_provider_class(self):
        """Test that registering invalid provider class raises error"""
        class InvalidProvider:
            pass
        
        with pytest.raises(ValueError, match="Provider class must inherit from BaseAIProvider"):
            self.manager.register_provider(
                name="invalid",
                provider_class=InvalidProvider,
                description="Invalid provider",
                required_config=[]
            )
    
    def test_configure_with_config(self):
        """Test configuring manager with Config object"""
        with patch.object(self.manager, '_auto_configure_providers') as mock_auto_config:
            self.manager.configure(self.mock_config)
            
            assert self.manager._config == self.mock_config
            mock_auto_config.assert_called_once()
    
    def test_extract_provider_config_openai(self):
        """Test extracting OpenAI provider configuration"""
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.ai_model = "gpt-3.5-turbo"
        self.mock_config.ai_temperature = 0.7
        self.mock_config.ai_max_tokens = 1000
        self.manager._config = self.mock_config
        
        provider_info = self.manager.get_provider_info("openai")
        config = self.manager._extract_provider_config("openai", provider_info)
        
        assert config["api_key"] == "test-key"
        assert config["model"] == "gpt-3.5-turbo"
        assert config["temperature"] == 0.7
        assert config["max_tokens"] == 1000
    
    def test_extract_provider_config_azure_openai(self):
        """Test extracting Azure OpenAI provider configuration"""
        self.mock_config.azure_openai_api_key = "test-azure-key"
        self.mock_config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.mock_config.azure_openai_deployment_name = "gpt-4-deployment"
        self.mock_config.ai_model = "gpt-4-deployment"
        self.manager._config = self.mock_config
        
        provider_info = self.manager.get_provider_info("azure-openai")
        config = self.manager._extract_provider_config("azure-openai", provider_info)
        
        assert config["api_key"] == "test-azure-key"
        assert config["endpoint"] == "https://test.openai.azure.com"
        assert config["deployment_name"] == "gpt-4-deployment"
        assert config["model"] == "gpt-4-deployment"
    
    def test_has_required_config(self):
        """Test checking for required configuration fields"""
        config = {"api_key": "test-key", "endpoint": "https://test.com"}
        
        # Test with all required fields present
        assert self.manager._has_required_config(config, ["api_key"])
        assert self.manager._has_required_config(config, ["api_key", "endpoint"])
        
        # Test with missing required fields
        assert not self.manager._has_required_config(config, ["api_key", "missing_field"])
        assert not self.manager._has_required_config({}, ["api_key"])
        
        # Test with empty values
        config_with_empty = {"api_key": "", "endpoint": "https://test.com"}
        assert not self.manager._has_required_config(config_with_empty, ["api_key"])
    
    @patch('services.ai_provider_manager.AIProviderManager._load_provider_class')
    def test_configure_provider(self, mock_load_class):
        """Test configuring a specific provider"""
        mock_load_class.return_value = MockProvider
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        assert "mock" in self.manager._providers
        assert isinstance(self.manager._providers["mock"], MockProvider)
        mock_load_class.assert_called_once_with("mock")
    
    def test_get_provider_with_name(self):
        """Test getting a provider by name"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        provider = self.manager.get_provider("mock")
        assert isinstance(provider, MockProvider)
    
    def test_get_provider_without_name_uses_active(self):
        """Test getting provider without name uses active provider"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        self.manager._active_provider = "mock"
        
        provider = self.manager.get_provider()
        assert isinstance(provider, MockProvider)
    
    def test_get_provider_not_configured_raises_error(self):
        """Test that getting unconfigured provider raises error"""
        with pytest.raises(ValueError, match="Provider 'nonexistent' is not configured"):
            self.manager.get_provider("nonexistent")
    
    def test_get_provider_no_active_raises_error(self):
        """Test that getting provider with no active provider raises error"""
        with pytest.raises(ValueError, match="No active provider set"):
            self.manager.get_provider()
    
    def test_set_active_provider(self):
        """Test setting active provider"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        self.manager.set_active_provider("mock")
        assert self.manager.get_active_provider_name() == "mock"
    
    def test_set_active_provider_not_configured_raises_error(self):
        """Test that setting unconfigured provider as active raises error"""
        with pytest.raises(ValueError, match="Provider 'nonexistent' is not configured"):
            self.manager.set_active_provider("nonexistent")
    
    def test_list_providers(self):
        """Test listing all registered providers"""
        providers = self.manager.list_providers()
        
        # Should include built-in providers
        expected_providers = ["openai", "azure-openai", "anthropic", "google", "deepseek"]
        for provider in expected_providers:
            assert provider in providers
    
    def test_list_configured_providers(self):
        """Test listing configured providers"""
        # Initially no providers configured
        assert self.manager.list_configured_providers() == []
        
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        configured = self.manager.list_configured_providers()
        assert "mock" in configured
    
    def test_validate_provider_success(self):
        """Test successful provider validation"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        result = self.manager.validate_provider("mock")
        assert result.status == ValidationStatus.SUCCESS
    
    def test_validate_provider_not_registered(self):
        """Test validation of unregistered provider"""
        result = self.manager.validate_provider("nonexistent")
        assert result.status == ValidationStatus.ERROR
        assert "not registered" in result.message
    
    def test_validate_provider_not_configured(self):
        """Test validation of registered but unconfigured provider"""
        result = self.manager.validate_provider("openai")
        assert result.status == ValidationStatus.ERROR
        assert "not configured" in result.message
    
    def test_validate_all_providers(self):
        """Test validating all configured providers"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        results = self.manager.validate_all_providers()
        assert "mock" in results
        assert results["mock"].status == ValidationStatus.SUCCESS
    
    def test_make_completion(self):
        """Test making completion request"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        self.manager._active_provider = "mock"
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        response = self.manager.make_completion(request)
        assert response.success
        assert response.content == "Mock response"
        assert response.model == "mock-model"
    
    def test_make_completion_with_specific_provider(self):
        """Test making completion request with specific provider"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        response = self.manager.make_completion(request, "mock")
        assert response.success
        assert response.content == "Mock response"
    
    def test_get_provider_status(self):
        """Test getting provider status information"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        self.manager._active_provider = "mock"
        
        status = self.manager.get_provider_status()
        
        assert status["active_provider"] == "mock"
        assert status["total_registered"] >= 6  # 5 built-in + 1 mock
        assert status["total_configured"] == 1
        assert "mock" in status["providers"]
        
        mock_status = status["providers"]["mock"]
        assert mock_status["registered"] is True
        assert mock_status["configured"] is True
        assert mock_status["description"] == "Mock provider"
        assert mock_status["config_valid"] is True
    
    @patch.dict(os.environ, {"AI_PROVIDER": "mock"})
    def test_set_default_active_provider_from_env(self):
        """Test setting default active provider from environment variable"""
        # Register and configure mock provider
        self.manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("mock", config)
        
        self.manager._set_default_active_provider()
        assert self.manager.get_active_provider_name() == "mock"
    
    def test_set_default_active_provider_azure_preference(self):
        """Test setting default active provider with Azure OpenAI preference"""
        # Mock Azure OpenAI configuration
        self.mock_config.use_azure_openai = True
        self.manager._config = self.mock_config
        
        # Register and configure mock azure provider
        self.manager.register_provider(
            name="azure-openai",
            provider_class=MockProvider,
            description="Mock Azure OpenAI provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        self.manager._configure_provider("azure-openai", config)
        
        self.manager._set_default_active_provider()
        assert self.manager.get_active_provider_name() == "azure-openai"


class TestGlobalFunctions:
    """Test global convenience functions"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Reset singleton
        AIProviderManager._instance = None
    
    def test_get_provider_manager_singleton(self):
        """Test that get_provider_manager returns singleton"""
        manager1 = get_provider_manager()
        manager2 = get_provider_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, AIProviderManager)
    
    def test_configure_provider_manager(self):
        """Test configuring provider manager through global function"""
        mock_config = Mock(spec=Config)
        
        with patch.object(AIProviderManager, 'configure') as mock_configure:
            configure_provider_manager(mock_config)
            mock_configure.assert_called_once_with(mock_config)
    
    def test_get_active_provider(self):
        """Test getting active provider through global function"""
        manager = get_provider_manager()
        
        # Register and configure mock provider
        manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        manager._configure_provider("mock", config)
        manager._active_provider = "mock"
        
        provider = get_active_provider()
        assert isinstance(provider, MockProvider)
    
    def test_make_completion_global(self):
        """Test making completion through global function"""
        manager = get_provider_manager()
        
        # Register and configure mock provider
        manager.register_provider(
            name="mock",
            provider_class=MockProvider,
            description="Mock provider",
            required_config=["api_key"]
        )
        
        config = {"api_key": "test-key"}
        manager._configure_provider("mock", config)
        manager._active_provider = "mock"
        
        request = CompletionRequest(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        
        response = make_completion(request)
        assert response.success
        assert response.content == "Mock response"


if __name__ == "__main__":
    pytest.main([__file__])