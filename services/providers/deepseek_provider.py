"""
DeepSeek Provider Implementation

Provides integration with DeepSeek's API through the new provider system.
Supports DeepSeek models with proper request/response mapping and error handling.
DeepSeek uses an OpenAI-compatible API, making integration straightforward.
"""

import logging
import os
from typing import Dict, Any, Optional, List

import openai
import httpx
from openai import OpenAI

from .base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class DeepSeekProvider(BaseAIProvider):
    """
    DeepSeek provider implementation.
    
    This provider integrates with DeepSeek's API, which is OpenAI-compatible.
    Supports DeepSeek models including DeepSeek-Chat and DeepSeek-Coder with
    proper request/response mapping and comprehensive error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize DeepSeek provider.
        
        Args:
            config: Configuration dictionary with DeepSeek settings
                   Expected keys: api_key, model, temperature, max_tokens, base_url
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client: Optional[OpenAI] = None
        self.http_client: Optional[httpx.Client] = None
        
        # Configure the DeepSeek client
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure the DeepSeek client with provider settings."""
        try:
            # Get API key from config or environment
            api_key = self.config.get('api_key') or os.getenv('DEEPSEEK_API_KEY')
            
            # DeepSeek API base URL
            base_url = self.config.get('base_url', 'https://api.deepseek.com')
            
            if api_key:
                # Create httpx client manually to avoid proxy parameter issues
                self.http_client = httpx.Client(
                    timeout=httpx.Timeout(30.0),
                    limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
                )
                
                self.client = OpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    http_client=self.http_client
                )
                self.logger.info("DeepSeek provider configured successfully")
            else:
                self.logger.warning("DeepSeek provider not configured - missing API key")
                
        except Exception as e:
            self.logger.error(f"Failed to configure DeepSeek provider: {str(e)}")
            self.client = None
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request using the DeepSeek API.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Response from DeepSeek
        """
        if not self.client:
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'deepseek-chat'),
                usage={},
                finish_reason="error",
                success=False,
                error_message="DeepSeek client not configured"
            )
        
        try:
            # Use configured model or default
            model = request.model or self.config.get('model', 'deepseek-chat')
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": False
            }
            
            # Add optional parameters if present
            if hasattr(request, 'top_p') and request.top_p is not None:
                request_params["top_p"] = request.top_p
            if hasattr(request, 'frequency_penalty') and request.frequency_penalty is not None:
                request_params["frequency_penalty"] = request.frequency_penalty
            if hasattr(request, 'presence_penalty') and request.presence_penalty is not None:
                request_params["presence_penalty"] = request.presence_penalty
            
            # Make the API call
            response = self.client.chat.completions.create(**request_params)
            
            # Extract content from response
            content = ""
            if response.choices and len(response.choices) > 0:
                choice = response.choices[0]
                if choice.message and choice.message.content:
                    content = choice.message.content
            
            # Build usage information
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
            # Get finish reason
            finish_reason = "stop"
            if response.choices and len(response.choices) > 0:
                finish_reason = response.choices[0].finish_reason or "stop"
            
            self.logger.debug(f"DeepSeek completion successful. Model: {model}, Tokens: {usage}")
            
            return CompletionResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                success=True
            )
            
        except openai.AuthenticationError as e:
            self.logger.error(f"DeepSeek authentication error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'deepseek-chat'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Authentication error: {str(e)}"
            )
        except openai.RateLimitError as e:
            self.logger.error(f"DeepSeek rate limit exceeded: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'deepseek-chat'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Rate limit exceeded: {str(e)}"
            )
        except openai.APIError as e:
            self.logger.error(f"DeepSeek API error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'deepseek-chat'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"DeepSeek API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"DeepSeek completion failed: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'deepseek-chat'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> ValidationResult:
        """
        Validate the DeepSeek provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        try:
            # Check for required API key
            api_key = self.config.get('api_key') or os.getenv('DEEPSEEK_API_KEY')
            if not api_key:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="DeepSeek API key is required",
                    details={"missing_config": ["api_key"]}
                )
            
            # Validate API key format (DeepSeek keys typically start with 'sk-')
            if not api_key.startswith('sk-'):
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message="DeepSeek API key format may be invalid (should start with 'sk-')",
                    details={"api_key_format": "unexpected"}
                )
            
            # Check model configuration
            model = self.config.get('model', 'deepseek-chat')
            valid_models = [
                'deepseek-chat',
                'deepseek-coder',
                'deepseek-math',
                'deepseek-reasoner'
            ]
            
            if model not in valid_models:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Model '{model}' may not be available",
                    details={"model": model, "valid_models": valid_models}
                )
            
            # Check base URL configuration
            base_url = self.config.get('base_url', 'https://api.deepseek.com')
            if not base_url.startswith('https://'):
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message="Base URL should use HTTPS for security",
                    details={"base_url": base_url}
                )
            
            # Check if client was configured successfully
            if not self.client:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="Failed to initialize DeepSeek client",
                    details={"client_initialized": False}
                )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                message="DeepSeek configuration is valid",
                details={
                    "api_key_present": True,
                    "model": model,
                    "base_url": base_url,
                    "provider": "deepseek",
                    "client_initialized": True
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
        Get information about available DeepSeek models.
        
        Returns:
            Dict containing model information and capabilities
        """
        return {
            "provider": "deepseek",
            "available_models": [
                {
                    "name": "deepseek-chat",
                    "description": "General-purpose conversational AI model",
                    "context_length": 32768,
                    "training_data": "Up to 2024",
                    "specialization": "General conversation and reasoning"
                },
                {
                    "name": "deepseek-coder",
                    "description": "Code-specialized model for programming tasks",
                    "context_length": 16384,
                    "training_data": "Up to 2024",
                    "specialization": "Code generation, debugging, and analysis"
                },
                {
                    "name": "deepseek-math",
                    "description": "Mathematics and reasoning specialized model",
                    "context_length": 4096,
                    "training_data": "Up to 2024",
                    "specialization": "Mathematical reasoning and problem solving"
                },
                {
                    "name": "deepseek-reasoner",
                    "description": "Advanced reasoning and logic model",
                    "context_length": 8192,
                    "training_data": "Up to 2024",
                    "specialization": "Complex reasoning and logical analysis"
                }
            ],
            "default_model": self.config.get('model', 'deepseek-chat'),
            "supports_streaming": True,
            "supports_function_calling": False,
            "max_tokens_limit": 4096,
            "base_url": self.config.get('base_url', 'https://api.deepseek.com'),
            "features": [
                "Code generation and analysis",
                "Mathematical reasoning",
                "Cost-effective pricing",
                "OpenAI-compatible API",
                "Specialized domain models",
                "Fast inference speed"
            ]
        }
    
    def __del__(self):
        """Cleanup when provider is destroyed."""
        try:
            if self.http_client:
                self.http_client.close()
        except Exception:
            pass  # Ignore errors during cleanup