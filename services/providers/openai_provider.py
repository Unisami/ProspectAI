"""
OpenAI Provider Implementation

Wraps the existing OpenAI client functionality to work with the new provider system
while maintaining backward compatibility.
"""

import logging
from typing import Dict, Any, Optional, List
import os

from .base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import (
    CompletionRequest, 
    CompletionResponse, 
    OpenAIClientManager,
    OpenAI
)
from utils.config import Config


class OpenAIProvider(BaseAIProvider):
    """
    OpenAI provider implementation using the existing OpenAI client manager.
    
    This provider wraps the existing OpenAI functionality to work with the new
    provider system while maintaining full backward compatibility.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAI provider.
        
        Args:
            config: Configuration dictionary with OpenAI settings
                   Expected keys: api_key, model, temperature, max_tokens
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client_manager = OpenAIClientManager()
        self.client_id = f"openai_provider_{id(self)}"
        
        # Configure the client manager with our settings
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure the OpenAI client manager with provider settings."""
        try:
            # Get API key from config or environment
            api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
            
            # Create a minimal Config object with required fields
            # We'll use dummy values for required fields that aren't needed for OpenAI client
            provider_config = Config(
                notion_token="dummy",  # Not used by OpenAI client
                hunter_api_key="dummy",  # Not used by OpenAI client
                use_azure_openai=False,
                openai_api_key=api_key or "dummy"  # Use dummy if no key to avoid client manager errors
            )
            
            # Only configure if we have a valid API key
            if api_key:
                # Configure the client manager
                self.client_manager.configure(provider_config, self.client_id)
                self.logger.info(f"OpenAI provider configured with client ID: {self.client_id}")
            else:
                self.logger.warning(f"OpenAI provider not configured - missing API key")
            
        except Exception as e:
            self.logger.error(f"Failed to configure OpenAI provider: {str(e)}")
            # Don't raise here - let validation catch configuration issues
            pass
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request using the OpenAI client manager.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Response from OpenAI
        """
        try:
            # Use the configured model or fall back to default
            if not request.model:
                request.model = self.config.get('model', 'gpt-3.5-turbo')
            
            # Make the completion request through the client manager
            response = self.client_manager.make_completion(request, self.client_id)
            
            self.logger.debug(f"OpenAI completion successful. Model: {response.model}, Tokens: {response.usage}")
            return response
            
        except Exception as e:
            self.logger.error(f"OpenAI completion failed: {str(e)}")
            # Return error response
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gpt-3.5-turbo'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> ValidationResult:
        """
        Validate the OpenAI provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        try:
            # Check for required API key
            api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
            if not api_key:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="OpenAI API key is required",
                    details={"missing_config": ["api_key"]}
                )
            
            # Validate API key format (should start with 'sk-')
            if not api_key.startswith('sk-'):
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message="OpenAI API key format may be invalid (should start with 'sk-')",
                    details={"api_key_format": "unexpected"}
                )
            
            # Check model configuration
            model = self.config.get('model', 'gpt-3.5-turbo')
            valid_models = [
                'gpt-4', 'gpt-4-turbo', 'gpt-4-turbo-preview',
                'gpt-3.5-turbo', 'gpt-3.5-turbo-16k'
            ]
            
            if model not in valid_models:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Model '{model}' may not be available",
                    details={"model": model, "valid_models": valid_models}
                )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                message="OpenAI configuration is valid",
                details={
                    "api_key_present": True,
                    "model": model,
                    "provider": "openai"
                }
            )
            
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Configuration validation failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about available OpenAI models.
        
        Returns:
            Dict containing model information and capabilities
        """
        return {
            "provider": "openai",
            "available_models": [
                {
                    "name": "gpt-4",
                    "description": "Most capable GPT-4 model",
                    "context_length": 8192,
                    "training_data": "Up to Sep 2021"
                },
                {
                    "name": "gpt-4-turbo",
                    "description": "Latest GPT-4 Turbo model",
                    "context_length": 128000,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "gpt-4-turbo-preview",
                    "description": "Preview of GPT-4 Turbo",
                    "context_length": 128000,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "gpt-3.5-turbo",
                    "description": "Fast and efficient GPT-3.5 model",
                    "context_length": 4096,
                    "training_data": "Up to Sep 2021"
                },
                {
                    "name": "gpt-3.5-turbo-16k",
                    "description": "GPT-3.5 with extended context",
                    "context_length": 16384,
                    "training_data": "Up to Sep 2021"
                }
            ],
            "default_model": self.config.get('model', 'gpt-3.5-turbo'),
            "supports_streaming": True,
            "supports_function_calling": True,
            "max_tokens_limit": 4096
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the underlying OpenAI client.
        
        Returns:
            Dict with client information
        """
        try:
            return self.client_manager.get_client_info(self.client_id)
        except Exception as e:
            return {
                "error": f"Failed to get client info: {str(e)}",
                "client_id": self.client_id,
                "provider": "openai"
            }
    
    def __del__(self):
        """Cleanup when provider is destroyed."""
        try:
            if hasattr(self, 'client_manager') and hasattr(self, 'client_id'):
                self.client_manager.close_client(self.client_id)
        except Exception:
            pass  # Ignore cleanup errors