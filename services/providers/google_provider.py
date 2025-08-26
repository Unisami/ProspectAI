"""
Google Gemini Provider Implementation

Provides integration with Google's Gemini API through the new provider system.
Supports Gemini Pro and other Google AI models with proper request/response mapping and error handling.
"""

import logging
import os
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

from .base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse


class GoogleProvider(BaseAIProvider):
    """
    Google Gemini provider implementation.
    
    This provider integrates with Google's Gemini API, supporting Gemini Pro models
    with proper request/response mapping and comprehensive error handling.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Google provider.
        
        Args:
            config: Configuration dictionary with Google settings
                   Expected keys: api_key, model, temperature, max_tokens
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client_configured = False
        
        # Configure the Google Generative AI client
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure the Google Generative AI client with provider settings."""
        try:
            # Get API key from config or environment
            api_key = self.config.get('api_key') or os.getenv('GOOGLE_API_KEY')
            
            if api_key:
                genai.configure(api_key=api_key)
                self.client_configured = True
                self.logger.info("Google provider configured successfully")
            else:
                self.logger.warning("Google provider not configured - missing API key")
                self.client_configured = False
                
        except Exception as e:
            self.logger.error(f"Failed to configure Google provider: {str(e)}")
            self.client_configured = False
    
    def _convert_messages_to_gemini_format(self, messages: List[Dict[str, str]]) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Convert OpenAI-style messages to Gemini format.
        
        Gemini expects a different conversation format with system instructions
        and user/model roles instead of user/assistant.
        
        Based on official API docs:
        - contents: [{"role": "user", "parts": [{"text": "content"}]}]
        - systemInstruction: {"parts": [{"text": "system message"}]}
        
        Args:
            messages: OpenAI-style messages list
            
        Returns:
            Tuple of (system_instruction_dict, conversation_history)
        """
        system_instruction = None
        conversation_history = []
        
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            if role == "system":
                # Gemini uses systemInstruction parameter with proper structure
                system_instruction = {
                    "parts": [{"text": content}]
                }
            elif role == "user":
                conversation_history.append({
                    "role": "user",
                    "parts": [{"text": content}]  # Proper parts structure with text field
                })
            elif role == "assistant":
                # Gemini uses 'model' instead of 'assistant'
                conversation_history.append({
                    "role": "model", 
                    "parts": [{"text": content}]  # Proper parts structure with text field
                })
            else:
                # Convert unknown roles to user messages
                conversation_history.append({
                    "role": "user",
                    "parts": [{"text": content}]  # Proper parts structure with text field
                })
        
        return system_instruction, conversation_history
    
    def _get_safety_settings(self) -> List[Dict[str, Any]]:
        """
        Get safety settings for Gemini API.
        
        Returns:
            List of safety settings to allow most content for business use
        """
        return [
            {
                "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
            },
            {
                "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
            },
            {
                "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
            },
            {
                "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
            }
        ]
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request using the Google Gemini API.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Response from Gemini
        """
        if not self.client_configured:
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message="Google client not configured"
            )
        
        try:
            # Convert messages to Gemini format
            system_instruction, conversation_history = self._convert_messages_to_gemini_format(request.messages)
            
            # Debug logging
            self.logger.debug(f"System instruction: {system_instruction}")
            self.logger.debug(f"Conversation history: {conversation_history}")
            self.logger.debug(f"Original messages: {request.messages}")
            
            # Use configured model or default (updated to current model names)
            model_name = request.model or self.config.get('model', 'gemini-2.0-flash')
            
            # Create the model instance with proper generation config
            generation_config = genai.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )
            
            # Initialize model with system instruction if present
            # System instruction should be passed as structured object per API docs
            if system_instruction:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    safety_settings=self._get_safety_settings(),
                    system_instruction=system_instruction  # Now properly structured
                )
            else:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    safety_settings=self._get_safety_settings()
                )
            
            # Handle conversation history with proper API structure
            if len(conversation_history) > 1:
                # Multi-turn conversation - use chat interface
                chat = model.start_chat(history=conversation_history[:-1])
                last_message = conversation_history[-1]
                # Extract text from parts structure
                message_text = last_message["parts"][0]["text"]
                response = chat.send_message(message_text)
            else:
                # Single message - use generate_content with proper contents structure
                if conversation_history:
                    # Use the structured conversation format
                    response = model.generate_content(conversation_history)
                else:
                    # Fallback to direct message content
                    message_content = request.messages[-1].get("content", "")
                    response = model.generate_content(message_content)
            
            # Extract content from response with improved error handling
            content = ""
            finish_reason = "stop"
            
            # First, try to get the finish reason for debugging
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason_value = candidate.finish_reason
                    self.logger.debug(f"Google response finish_reason: {finish_reason_value}")
                    
                    # Map finish reasons (based on Google's FinishReason enum)
                    finish_reason_map = {
                        0: "FINISH_REASON_UNSPECIFIED",
                        1: "STOP",  # Normal completion
                        2: "MAX_TOKENS",  # Hit token limit
                        3: "SAFETY",  # Blocked by safety filters
                        4: "RECITATION",  # Blocked due to recitation
                        5: "OTHER"  # Other reasons
                    }
                    
                    finish_reason_name = finish_reason_map.get(finish_reason_value, f"UNKNOWN_{finish_reason_value}")
                    self.logger.debug(f"Finish reason: {finish_reason_name}")
                    
                    # Handle different finish reasons
                    if finish_reason_value == 1:  # STOP - normal completion
                        # Try to extract content from candidate
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        content += part.text
                    elif finish_reason_value == 2:  # MAX_TOKENS
                        content = "[Response truncated due to token limit]"
                    elif finish_reason_value == 3:  # SAFETY
                        content = "[Response blocked by safety filters]"
                    elif finish_reason_value == 4:  # RECITATION
                        content = "[Response blocked due to recitation]"
                    elif finish_reason_value == 5:  # OTHER
                        content = "[Response blocked for other reasons]"
                    else:
                        content = f"[Response blocked - finish reason: {finish_reason_value}]"
            
            # Fallback: try the quick accessor if we still don't have content
            if not content:
                try:
                    if hasattr(response, 'text') and response.text:
                        content = response.text
                except Exception as e:
                    self.logger.warning(f"Failed to access response.text: {str(e)}")
                    content = "[Failed to extract response content]"
            
            # Build usage information
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "completion_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0)
                }
            
            # Get finish reason
            finish_reason = "stop"
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    finish_reason = str(candidate.finish_reason).lower()
            
            self.logger.debug(f"Google completion successful. Model: {model_name}, Tokens: {usage}")
            
            return CompletionResponse(
                content=content,
                model=model_name,
                usage=usage,
                finish_reason=finish_reason,
                success=True
            )
            
        except google_exceptions.Unauthenticated as e:
            self.logger.error(f"Google authentication error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Authentication error: {str(e)}"
            )
        except google_exceptions.ResourceExhausted as e:
            self.logger.error(f"Google rate limit exceeded: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Rate limit exceeded: {str(e)}"
            )
        except google_exceptions.InvalidArgument as e:
            self.logger.error(f"Google API invalid argument: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Invalid argument: {str(e)}"
            )
        except google_exceptions.GoogleAPIError as e:
            self.logger.error(f"Google API error: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Google API error: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"Google completion failed: {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('model', 'gemini-2.0-flash'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> ValidationResult:
        """
        Validate the Google provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        try:
            # Check for required API key
            api_key = self.config.get('api_key') or os.getenv('GOOGLE_API_KEY')
            if not api_key:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="Google API key is required",
                    details={"missing_config": ["api_key"]}
                )
            
            # Validate API key format (Google API keys are typically 39 characters)
            if len(api_key) < 30:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message="Google API key format may be invalid (too short)",
                    details={"api_key_length": len(api_key)}
                )
            
            # Check model configuration (updated to current available models)
            model = self.config.get('model', 'gemini-2.5-flash')
            valid_models = [
                'gemini-2.5-pro',
                'gemini-2.5-flash',
                'gemini-2.5-flash-lite',
                'gemini-1.5-pro',
                'gemini-1.5-flash',
                'gemini-1.0-pro',
                'gemini-pro',
                'gemini-pro-vision'
            ]
            
            if model not in valid_models:
                return ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Model '{model}' may not be available",
                    details={"model": model, "valid_models": valid_models}
                )
            
            # Check if client was configured successfully
            if not self.client_configured:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message="Failed to initialize Google client",
                    details={"client_configured": False}
                )
            
            return ValidationResult(
                status=ValidationStatus.SUCCESS,
                message="Google configuration is valid",
                details={
                    "api_key_present": True,
                    "model": model,
                    "provider": "google",
                    "client_configured": True
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
        Get information about available Google Gemini models.
        
        Returns:
            Dict containing model information and capabilities
        """
        return {
            "provider": "google",
            "available_models": [
                {
                    "name": "gemini-2.0-flash",
                    "description": "Latest Gemini 2.0 Flash - fast and multimodal",
                    "context_length": 1048576,
                    "training_data": "Up to Dec 2024"
                },
                {
                    "name": "gemini-1.5-pro",
                    "description": "Gemini 1.5 Pro - most capable model",
                    "context_length": 2097152,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "gemini-1.5-flash",
                    "description": "Gemini 1.5 Flash - fast and efficient",
                    "context_length": 1048576,
                    "training_data": "Up to Apr 2024"
                },
                {
                    "name": "gemini-1.0-pro",
                    "description": "Gemini 1.0 Pro - stable and reliable",
                    "context_length": 32768,
                    "training_data": "Up to Feb 2024"
                },
                {
                    "name": "gemini-pro",
                    "description": "Gemini Pro - general purpose model",
                    "context_length": 32768,
                    "training_data": "Up to Feb 2024"
                },
                {
                    "name": "gemini-pro-vision",
                    "description": "Gemini Pro Vision - multimodal capabilities",
                    "context_length": 16384,
                    "training_data": "Up to Feb 2024"
                }
            ],
            "default_model": self.config.get('model', 'gemini-2.0-flash'),
            "supports_streaming": True,
            "supports_function_calling": True,
            "supports_vision": True,
            "max_tokens_limit": 8192,
            "features": [
                "Multimodal capabilities",
                "Long context understanding",
                "Function calling",
                "Code generation and analysis",
                "Vision and image understanding",
                "Safety filtering"
            ]
        }