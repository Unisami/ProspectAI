"""
AI Provider Manager

Central manager for all AI providers, handling registration, discovery,
instantiation, and provider switching functionality.
"""

import os
import logging
import threading
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
from enum import Enum

from services.providers.base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse
from utils.config import Config


class ProviderType(Enum):
    """Supported AI provider types"""
    OPENAI = "openai"
    AZURE_OPENAI = "azure-openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"


@dataclass
class ProviderInfo:
    """Information about a registered provider"""
    name: str
    provider_type: ProviderType
    provider_class: Type[BaseAIProvider]
    description: str
    required_config: List[str]
    optional_config: List[str] = None


class AIProviderManager:
    """
    Central manager for all AI providers.
    
    Handles provider registration, discovery, instantiation, and switching
    functionality with thread-safe operations.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the AI provider manager."""
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        self._providers: Dict[str, BaseAIProvider] = {}
        self._provider_registry: Dict[str, ProviderInfo] = {}
        self._active_provider: Optional[str] = None
        self._config: Optional[Config] = None
        self._initialized = True
        
        # Register built-in providers
        self._register_builtin_providers()
        
        self.logger.info("AI Provider Manager initialized")
    
    def _register_builtin_providers(self) -> None:
        """Register built-in AI providers."""
        # Note: Provider classes will be imported dynamically when needed
        # to avoid circular imports and missing dependencies
        
        self._provider_registry["openai"] = ProviderInfo(
            name="openai",
            provider_type=ProviderType.OPENAI,
            provider_class=None,  # Will be loaded dynamically
            description="OpenAI GPT models (GPT-3.5, GPT-4, etc.)",
            required_config=["openai_api_key"],
            optional_config=["model", "temperature", "max_tokens"]
        )
        
        self._provider_registry["azure-openai"] = ProviderInfo(
            name="azure-openai",
            provider_type=ProviderType.AZURE_OPENAI,
            provider_class=None,  # Will be loaded dynamically
            description="Azure OpenAI Service with custom deployments",
            required_config=["azure_openai_api_key", "azure_openai_endpoint", "azure_openai_deployment_name"],
            optional_config=["azure_openai_api_version", "temperature", "max_tokens"]
        )
        
        self._provider_registry["anthropic"] = ProviderInfo(
            name="anthropic",
            provider_type=ProviderType.ANTHROPIC,
            provider_class=None,  # Will be loaded dynamically
            description="Anthropic Claude models with constitutional AI",
            required_config=["anthropic_api_key"],
            optional_config=["model", "temperature", "max_tokens"]
        )
        
        self._provider_registry["google"] = ProviderInfo(
            name="google",
            provider_type=ProviderType.GOOGLE,
            provider_class=None,  # Will be loaded dynamically
            description="Google Gemini models with multimodal capabilities",
            required_config=["google_api_key"],
            optional_config=["model", "temperature", "max_tokens"]
        )
        
        self._provider_registry["deepseek"] = ProviderInfo(
            name="deepseek",
            provider_type=ProviderType.DEEPSEEK,
            provider_class=None,  # Will be loaded dynamically
            description="DeepSeek models specialized for code and reasoning",
            required_config=["deepseek_api_key"],
            optional_config=["model", "temperature", "max_tokens"]
        )
        
        self.logger.debug(f"Registered {len(self._provider_registry)} built-in providers")
    
    def _load_provider_class(self, provider_name: str) -> Type[BaseAIProvider]:
        """
        Dynamically load provider class to avoid import issues.
        
        Args:
            provider_name: Name of the provider to load
            
        Returns:
            Provider class
            
        Raises:
            ImportError: If provider class cannot be loaded
        """
        # First check if this is a custom registered provider
        if provider_name in self._provider_registry:
            provider_info = self._provider_registry[provider_name]
            if provider_info.provider_class is not None:
                return provider_info.provider_class
        
        # Then try to load built-in providers
        try:
            if provider_name == "openai":
                from services.providers.openai_provider import OpenAIProvider
                return OpenAIProvider
            elif provider_name == "azure-openai":
                from services.providers.azure_openai_provider import AzureOpenAIProvider
                return AzureOpenAIProvider
            elif provider_name == "anthropic":
                from services.providers.anthropic_provider import AnthropicProvider
                return AnthropicProvider
            elif provider_name == "google":
                from services.providers.google_provider import GoogleProvider
                return GoogleProvider
            elif provider_name == "deepseek":
                from services.providers.deepseek_provider import DeepSeekProvider
                return DeepSeekProvider
            else:
                raise ImportError(f"Unknown provider: {provider_name}")
                
        except ImportError as e:
            self.logger.error(f"Failed to load provider class for '{provider_name}': {str(e)}")
            raise ImportError(f"Provider '{provider_name}' is not available. {str(e)}")
    
    def configure(self, config: Config) -> None:
        """
        Configure the provider manager with system configuration.
        
        Args:
            config: System configuration object
        """
        self._config = config
        self.logger.info("AI Provider Manager configured")
        
        # Auto-detect and configure available providers
        self._auto_configure_providers()
    
    def _auto_configure_providers(self) -> None:
        """Automatically configure providers based on available credentials."""
        if not self._config:
            return
        
        configured_count = 0
        
        # Check each registered provider for available configuration
        for provider_name, provider_info in self._provider_registry.items():
            try:
                provider_config = self._extract_provider_config(provider_name, provider_info)
                if self._has_required_config(provider_config, provider_info.required_config):
                    self._configure_provider(provider_name, provider_config)
                    configured_count += 1
                    self.logger.debug(f"Auto-configured provider: {provider_name}")
            except Exception as e:
                self.logger.debug(f"Could not auto-configure provider '{provider_name}': {str(e)}")
        
        self.logger.info(f"Auto-configured {configured_count} providers")
        
        # Set active provider based on configuration or default
        self._set_default_active_provider()
    
    def _extract_provider_config(self, provider_name: str, provider_info: ProviderInfo) -> Dict[str, Any]:
        """
        Extract provider-specific configuration from system config.
        
        Args:
            provider_name: Name of the provider
            provider_info: Provider information
            
        Returns:
            Provider-specific configuration dictionary
        """
        config_dict = {}
        
        # Map configuration fields based on provider type
        if provider_name == "openai":
            config_dict = {
                "api_key": self._config.openai_api_key,
                "model": getattr(self._config, 'ai_model', None) or "gpt-3.5-turbo",
                "temperature": getattr(self._config, 'ai_temperature', 0.7),
                "max_tokens": getattr(self._config, 'ai_max_tokens', 1000)
            }
        elif provider_name == "azure-openai":
            config_dict = {
                "api_key": self._config.azure_openai_api_key,
                "endpoint": self._config.azure_openai_endpoint,
                "deployment_name": self._config.azure_openai_deployment_name,
                "api_version": self._config.azure_openai_api_version,
                "model": getattr(self._config, 'ai_model', None) or self._config.azure_openai_deployment_name,
                "temperature": getattr(self._config, 'ai_temperature', 0.7),
                "max_tokens": getattr(self._config, 'ai_max_tokens', 1000)
            }
        elif provider_name == "anthropic":
            config_dict = {
                "api_key": getattr(self._config, 'anthropic_api_key', None),
                "model": getattr(self._config, 'ai_model', None) or "claude-3-sonnet-20240229",
                "temperature": getattr(self._config, 'ai_temperature', 0.7),
                "max_tokens": getattr(self._config, 'ai_max_tokens', 1000)
            }
        elif provider_name == "google":
            config_dict = {
                "api_key": getattr(self._config, 'google_api_key', None),
                "model": getattr(self._config, 'ai_model', None) or "gemini-pro",
                "temperature": getattr(self._config, 'ai_temperature', 0.7),
                "max_tokens": getattr(self._config, 'ai_max_tokens', 1000)
            }
        elif provider_name == "deepseek":
            config_dict = {
                "api_key": getattr(self._config, 'deepseek_api_key', None),
                "model": getattr(self._config, 'ai_model', None) or "deepseek-chat",
                "temperature": getattr(self._config, 'ai_temperature', 0.7),
                "max_tokens": getattr(self._config, 'ai_max_tokens', 1000)
            }
        
        # Filter out None values
        return {k: v for k, v in config_dict.items() if v is not None}
    
    def _has_required_config(self, config: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Check if configuration has all required fields.
        
        Args:
            config: Configuration dictionary
            required_fields: List of required field names
            
        Returns:
            True if all required fields are present and non-empty
        """
        for field in required_fields:
            # Map field names to config keys
            config_key = field
            if field == "openai_api_key":
                config_key = "api_key"
            elif field == "azure_openai_api_key":
                config_key = "api_key"
            elif field == "azure_openai_endpoint":
                config_key = "endpoint"
            elif field == "azure_openai_deployment_name":
                config_key = "deployment_name"
            elif field == "anthropic_api_key":
                config_key = "api_key"
            elif field == "google_api_key":
                config_key = "api_key"
            elif field == "deepseek_api_key":
                config_key = "api_key"
            
            if config_key not in config or not config[config_key]:
                return False
        
        return True
    
    def _configure_provider(self, provider_name: str, config: Dict[str, Any]) -> None:
        """
        Configure a specific provider instance.
        
        Args:
            provider_name: Name of the provider
            config: Provider configuration
        """
        try:
            provider_class = self._load_provider_class(provider_name)
            provider_instance = provider_class(config)
            self._providers[provider_name] = provider_instance
            
        except Exception as e:
            self.logger.error(f"Failed to configure provider '{provider_name}': {str(e)}")
            raise
    
    def _set_default_active_provider(self) -> None:
        """Set the default active provider based on configuration or availability."""
        # Check if AI_PROVIDER is set in environment
        env_provider = os.getenv("AI_PROVIDER")
        if env_provider and env_provider in self._providers:
            self._active_provider = env_provider
            self.logger.info(f"Set active provider from environment: {env_provider}")
            return
        
        # Check config for Azure OpenAI preference
        if self._config and self._config.use_azure_openai and "azure-openai" in self._providers:
            self._active_provider = "azure-openai"
            self.logger.info("Set active provider to azure-openai based on config")
            return
        
        # Default to OpenAI if available
        if "openai" in self._providers:
            self._active_provider = "openai"
            self.logger.info("Set active provider to openai as default")
            return
        
        # Use first available provider
        if self._providers:
            self._active_provider = list(self._providers.keys())[0]
            self.logger.info(f"Set active provider to first available: {self._active_provider}")
        else:
            self.logger.warning("No providers configured")
    
    def register_provider(
        self,
        name: str,
        provider_class: Type[BaseAIProvider],
        description: str,
        required_config: List[str],
        optional_config: List[str] = None
    ) -> None:
        """
        Register a custom AI provider.
        
        Args:
            name: Unique name for the provider
            provider_class: Provider class implementing BaseAIProvider
            description: Human-readable description
            required_config: List of required configuration fields
            optional_config: List of optional configuration fields
        """
        if not issubclass(provider_class, BaseAIProvider):
            raise ValueError("Provider class must inherit from BaseAIProvider")
        
        provider_info = ProviderInfo(
            name=name,
            provider_type=ProviderType.OPENAI,  # Default type for custom providers
            provider_class=provider_class,
            description=description,
            required_config=required_config,
            optional_config=optional_config or []
        )
        
        self._provider_registry[name] = provider_info
        self.logger.info(f"Registered custom provider: {name}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> BaseAIProvider:
        """
        Get a configured provider instance.
        
        Args:
            provider_name: Name of the provider (uses active provider if None)
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not configured or available
        """
        if provider_name is None:
            provider_name = self._active_provider
        
        if not provider_name:
            raise ValueError("No active provider set and no provider specified")
        
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' is not configured")
        
        return self._providers[provider_name]
    
    def list_providers(self) -> List[str]:
        """
        List all registered provider names.
        
        Returns:
            List of provider names
        """
        return list(self._provider_registry.keys())
    
    def list_configured_providers(self) -> List[str]:
        """
        List configured (instantiated) provider names.
        
        Returns:
            List of configured provider names
        """
        return list(self._providers.keys())
    
    def get_provider_info(self, provider_name: str) -> ProviderInfo:
        """
        Get information about a registered provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider information
            
        Raises:
            ValueError: If provider is not registered
        """
        if provider_name not in self._provider_registry:
            raise ValueError(f"Provider '{provider_name}' is not registered")
        
        return self._provider_registry[provider_name]
    
    def get_active_provider_name(self) -> Optional[str]:
        """
        Get the name of the currently active provider.
        
        Returns:
            Active provider name or None if no provider is active
        """
        return self._active_provider
    
    def set_active_provider(self, provider_name: str) -> None:
        """
        Set the active provider.
        
        Args:
            provider_name: Name of the provider to set as active
            
        Raises:
            ValueError: If provider is not configured
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' is not configured")
        
        self._active_provider = provider_name
        self.logger.info(f"Set active provider to: {provider_name}")
    
    def validate_provider(self, provider_name: str) -> ValidationResult:
        """
        Validate a provider's configuration and connection.
        
        Args:
            provider_name: Name of the provider to validate
            
        Returns:
            Validation result
        """
        try:
            if provider_name not in self._provider_registry:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=f"Provider '{provider_name}' is not registered"
                )
            
            if provider_name not in self._providers:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=f"Provider '{provider_name}' is not configured"
                )
            
            provider = self._providers[provider_name]
            
            # Validate configuration
            config_result = provider.validate_config()
            if config_result.status == ValidationStatus.ERROR:
                return config_result
            
            # Test connection
            connection_result = provider.test_connection()
            return connection_result
            
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Validation failed for provider '{provider_name}': {str(e)}"
            )
    
    def validate_all_providers(self) -> Dict[str, ValidationResult]:
        """
        Validate all configured providers.
        
        Returns:
            Dictionary mapping provider names to validation results
        """
        results = {}
        
        for provider_name in self._providers:
            results[provider_name] = self.validate_provider(provider_name)
        
        return results
    
    def make_completion(
        self,
        request: CompletionRequest,
        provider_name: Optional[str] = None
    ) -> CompletionResponse:
        """
        Make a completion request using the specified or active provider.
        
        Args:
            request: Completion request
            provider_name: Provider to use (uses active provider if None)
            
        Returns:
            Completion response
            
        Raises:
            ValueError: If no provider is available
        """
        provider = self.get_provider(provider_name)
        return provider.make_completion(request)
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get status information for all providers.
        
        Returns:
            Dictionary with provider status information
        """
        status = {
            "active_provider": self._active_provider,
            "total_registered": len(self._provider_registry),
            "total_configured": len(self._providers),
            "providers": {}
        }
        
        for provider_name in self._provider_registry:
            provider_info = self._provider_registry[provider_name]
            is_configured = provider_name in self._providers
            
            provider_status = {
                "registered": True,
                "configured": is_configured,
                "description": provider_info.description,
                "required_config": provider_info.required_config,
                "optional_config": provider_info.optional_config or []
            }
            
            if is_configured:
                provider = self._providers[provider_name]
                provider_status["config"] = provider.get_config()
                
                # Quick validation check
                try:
                    validation_result = provider.validate_config()
                    provider_status["config_valid"] = validation_result.status == ValidationStatus.SUCCESS
                    provider_status["validation_message"] = validation_result.message
                except Exception as e:
                    provider_status["config_valid"] = False
                    provider_status["validation_message"] = str(e)
            
            status["providers"][provider_name] = provider_status
        
        return status


# Global instance for easy access
_provider_manager = None


def get_provider_manager() -> AIProviderManager:
    """
    Get the global AI provider manager instance.
    
    Returns:
        AIProviderManager singleton instance
    """
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = AIProviderManager()
    return _provider_manager


def configure_provider_manager(config: Config) -> None:
    """
    Configure the global AI provider manager.
    
    Args:
        config: System configuration
    """
    manager = get_provider_manager()
    manager.configure(config)


def get_active_provider() -> BaseAIProvider:
    """
    Get the currently active AI provider.
    
    Returns:
        Active provider instance
    """
    manager = get_provider_manager()
    return manager.get_provider()


def make_completion(
    request: CompletionRequest,
    provider_name: Optional[str] = None
) -> CompletionResponse:
    """
    Convenience function for making completions with the provider manager.
    
    Args:
        request: Completion request
        provider_name: Provider to use (uses active provider if None)
        
    Returns:
        Completion response
    """
    manager = get_provider_manager()
    return manager.make_completion(request, provider_name)