"""
Anthropic Claude Provider Implementation

Provides integration with Anthropic's Claude API through the new provider system.
Supports Claude-3 models with proper request/response mapping and error handling.
"""

import logging
import os
from typing import Dict, Any, Optional, List

import anthropic
from anthropic import Anthropic

from .base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class AnthropicProvider(BaseAIProvider):
    """
    Anthropic Claude provider implementation.
    
    This provider integrates with Anthropic's Claude API, supporting Claude-3 models
    with proper request/response mapping and comprehensive error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Anthropic provider.
        
        Args:
            config: Configuration dictionary with Anthropic settings
                   Expected keys: api_key, model, temperature, max_tokens
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client: Optional[Anthropic] = None
        
        # Configure the Anthropic client
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure the Anthropic client with provider settings."""
        try:
            # Get API key from config or environment
            api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
            
            if api_key:
                self.client = Anthropic(api_key=api_key)
                self.logger.info("Anthropic provider configured successfully")
            else:
                self.logger.warning("Anthropic provider not configured - missing API key")
                
        except Exception as e:
            self.logger.error(f"Failed to configure Anthropic provider: {str(e)}")
            self.client = None
    
    def _convert_messages_to_anthropic_format(self, messages: List[Dict[str, str]]) -> tuple[str, List[Dict[str, str]]]:
        """
        Convert OpenAI-style messages to Anthropic format.
        
        Anthropic expects a system message separate from the conversation messages.
        
        Args:
            messages: OpenAI-style messages list
            
        Returns:
            Tuple of (system_message, conversation_messages)
        """
        system_message = ""
        conversation_messages = []
        
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                # Anthropic uses a separate system parameter
                system_message = content
            elif role in ["user", "assistant"]:
                conversation_messages.append({
                    "role": role,
                    "content": content
                })
            else:
                # Convert unknown roles to user messages
                conversation_messages.append({
                    "role": "user", 
                    "content": content
                })
        
        return system_message, conversation_messages
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request using the Anthropic Claude API.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Response from Claude
        """
        if not self.client:
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'claude-3-sonnet-20240229'),
                usage={},
                finish_reason="error",
                success=False,
                error_message="Anthropic client not configured"
            )
        
        try:
            # Convert messages to Anthropic format
            system_message, conversation_messages = self._convert_messages_to_anthropic_format(request.messages)
            
            # Use configured model or default
            model = request.model or self.config.get('model', 'claude-3-sonnet-20240229')
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "messages": conversation_messages
            }
            
            # Add system message if present
            if system_message:
                request_params["system"] = system_message
            
            # Make the API call
            response = self.client.messages.create(**request_params)
            
            # Extract content from response
            content = ""
            if response.content and len(response.content) > 0:
                # Claude returns content as a list of content blocks
                content_blocks = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        content_blocks.append(block.text)
                    elif isinstance(block, dict) and 'text' in block:
                        content_blocks.append(block['text'])
                content = "".join(content_blocks)
            
            # Build usage information
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": getattr(response.usage, 'input_tokens', 0),
                    "completion_tokens": getattr(response.usage, 'output_tokens', 0),
                    "total_tokens": getattr(response.usage, 'input_tokens', 0) + getattr(response.usage, 'output_tokens', 0)
                }
            
            # Get finish reason
            finish_reason = getattr(response, 'stop_reason', 'stop')
            
            self.logger.debug(f"Anthropic completion successful. Model: {model}, Tokens: {usage}")
            
            return CompletionResponse(
                content=content,
                model=model,
                usage=usage,
                finish_reason=finish_reason,
                success=True
            )
            
        except anthropic.AuthenticationError as e:
            self.logger.error(f"Anthropic authentication error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'claude-3-sonnet-20240229'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Authentication error: {str(e)}"
            )
        except anthropic.RateLimitError as e:
            self.logger.error(f"Anthropic rate limit exceeded: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'claude-3-sonnet-20240229'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Rate limit exceeded: {str(e)}"
            )
        except anthropic.APIError as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'claude-3-sonnet-20240229'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Anthropic API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Anthropic completion failed: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'claude-3-sonnet-20240229'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> ValidationResult:
        """
        Validate the Anthropic provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        try:
            # Check for required API key
            api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="Anthropic API key is required",
                    details={"missing_config": ["api_key"]}
                )
            
            # Validate API key format (Anthropic keys start with 'sk-ant-')
            if not api_key.startswith('sk-ant-'):
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message="Anthropic API key format may be invalid (should start with 'sk-ant-')",
                    details={"api_key_format": "unexpected"}
                )
            
            # Check model configuration
            model = self.config.get('model', 'claude-3-sonnet-20240229')
            valid_models = [
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229', 
                'claude-3-haiku-20240307',
                'claude-2.1',
                'claude-2.0',
                'claude-instant-1.2'
            ]
            
            if model not in valid_models:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Model '{model}' may not be available",
                    details={"model": model, "valid_models": valid_models}
                )
            
            # Check if client was configured successfully
            if not self.client:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="Failed to initialize Anthropic client",
                    details={"client_initialized": False}
                )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                message="Anthropic configuration is valid",
                details={
                    "api_key_present": True,
                    "model": model,
                    "provider": "anthropic",
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
        Get information about available Anthropic Claude models.
        
        Returns:
            Dict containing model information and capabilities
        """
        return {
            "provider": "anthropic",
            "available_models": [
                {
                    "name": "claude-3-opus-20240229",
                    "description": "Most powerful Claude-3 model for complex tasks",
                    "context_length": 200000,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "claude-3-sonnet-20240229",
                    "description": "Balanced Claude-3 model for most use cases",
                    "context_length": 200000,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "claude-3-haiku-20240307",
                    "description": "Fastest Claude-3 model for simple tasks",
                    "context_length": 200000,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "claude-2.1",
                    "description": "Previous generation Claude model",
                    "context_length": 200000,
                    "training_data": "Up to early 2023"
                },
                {
                    "name": "claude-2.0",
                    "description": "Earlier Claude-2 model",
                    "context_length": 100000,
                    "training_data": "Up to early 2023"
                },
                {
                    "name": "claude-instant-1.2",
                    "description": "Fast and efficient Claude model",
                    "context_length": 100000,
                    "training_data": "Up to early 2023"
                }
            ],
            "default_model": self.config.get('model', 'claude-3-sonnet-20240229'),
            "supports_streaming": True,
            "supports_function_calling": False,
            "max_tokens_limit": 4096,
            "features": [
                "Constitutional AI",
                "Safety-focused responses", 
                "Long context understanding",
                "Code generation and analysis",
                "Creative writing"
            ]
        }