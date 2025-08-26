"""
Azure OpenAI Provider Implementation

Wraps the existing Azure OpenAI client functionality to work with the new provider system
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
    AzureOpenAI
)
from utils.config import Config


class AzureOpenAIProvider(BaseAIProvider):
    """
    Azure OpenAI provider implementation using the existing OpenAI client manager.
    
    This provider wraps the existing Azure OpenAI functionality to work with the new
    provider system while maintaining full backward compatibility.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure OpenAI provider.
        
        Args:
            config: Configuration dictionary with Azure OpenAI settings
                   Expected keys: api_key, endpoint, deployment_name, api_version, model
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.client_manager = OpenAIClientManager()
        self.client_id = f"azure_openai_provider_{id(self)}"
        
        # Configure the client manager with our settings
        self._configure_client()
    
    def _configure_client(self) -> None:
        """Configure the Azure OpenAI client manager with provider settings."""
        try:
            # Get configuration values
            api_key = self.config.get('api_key') or os.getenv('AZURE_OPENAI_API_KEY')
            endpoint = self.config.get('endpoint') or os.getenv('AZURE_OPENAI_ENDPOINT')
            deployment_name = self.config.get('deployment_name') or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
            
            # Create a minimal Config object with required fields
            # We'll use dummy values for required fields that aren't needed for Azure OpenAI client
            provider_config = Config(
                notion_token="dummy",  # Not used by Azure OpenAI client
                hunter_api_key="dummy",  # Not used by Azure OpenAI client
                use_azure_openai=True,
                azure_openai_api_key=api_key or "dummy",  # Use dummy if no key to avoid client manager errors
                azure_openai_endpoint=endpoint or "https://dummy.openai.azure.com/",
                azure_openai_deployment_name=deployment_name or "dummy",
                azure_openai_api_version=self.config.get('api_version', '2024-02-15-preview')
            )
            
            # Only configure if we have valid configuration
            if api_key and endpoint and deployment_name:
                # Configure the client manager
                self.client_manager.configure(provider_config, self.client_id)
                self.logger.info(f"Azure OpenAI provider configured with client ID: {self.client_id}")
            else:
                self.logger.warning(f"Azure OpenAI provider not configured - missing required configuration")
            
        except Exception as e:
            self.logger.error(f"Failed to configure Azure OpenAI provider: {str(e)}")
            # Don't raise here - let validation catch configuration issues
            pass
    
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request using the Azure OpenAI client manager.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Response from Azure OpenAI
        """
        try:
            # For Azure OpenAI, the model is the deployment name
            if not request.model:
                request.model = self.config.get('deployment_name') or self.config.get('model')
            
            # Make the completion request through the client manager
            response = self.client_manager.make_completion(request, self.client_id)
            
            self.logger.debug(f"Azure OpenAI completion successful. Model: {response.model}, Tokens: {response.usage}")
            return response
            
        except Exception as e:
            self.logger.error(f"Azure OpenAI completion failed: {str(e)}")
            # Return error response
            return CompletionResponse(
                content="",
                model=request.model or self.config.get('deployment_name', 'unknown'),
                usage={},
                finish_reason="error",
                success=False,
                error_message=str(e)
            )
    
    def validate_config(self) -> ValidationResult:
        """
        Validate the Azure OpenAI provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        try:
            missing_configs = []
            warnings = []
            
            # Check for required API key
            api_key = self.config.get('api_key') or os.getenv('AZURE_OPENAI_API_KEY')
            if not api_key:
                missing_configs.append('api_key')
            
            # Check for required endpoint
            endpoint = self.config.get('endpoint') or os.getenv('AZURE_OPENAI_ENDPOINT')
            if not endpoint:
                missing_configs.append('endpoint')
            elif not endpoint.startswith('https://'):
                warnings.append("Endpoint should use HTTPS")
            
            # Check for required deployment name
            deployment_name = self.config.get('deployment_name') or os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
            if not deployment_name:
                missing_configs.append('deployment_name')
            
            # Check API version
            api_version = self.config.get('api_version', '2024-02-15-preview')
            if not api_version:
                warnings.append("API version not specified, using default")
            
            if missing_configs:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=f"Required Azure OpenAI configuration missing: {', '.join(missing_configs)}",
                    details={"missing_config": missing_configs}
                )
            
            status = ValidationStatus.WARNING if warnings else ValidationStatus.SUCCESS
            message = "Azure OpenAI configuration is valid"
            if warnings:
                message += f" (warnings: {', '.join(warnings)})"
            
            return ValidationResult(
                status=status,
                message=message,
                details={
                    "api_key_present": True,
                    "endpoint": endpoint,
                    "deployment_name": deployment_name,
                    "api_version": api_version,
                    "provider": "azure_openai",
                    "warnings": warnings
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
        Get information about the Azure OpenAI deployment.
        
        Returns:
            Dict containing model information and capabilities
        """
        deployment_name = self.config.get('deployment_name') or self.config.get('model', 'unknown')
        endpoint = self.config.get('endpoint', 'unknown')
        api_version = self.config.get('api_version', '2024-02-15-preview')
        
        return {
            "provider": "azure_openai",
            "deployment_info": {
                "deployment_name": deployment_name,
                "endpoint": endpoint,
                "api_version": api_version
            },
            "available_models": [
                {
                    "name": deployment_name,
                    "description": f"Azure OpenAI deployment: {deployment_name}",
                    "deployment_name": deployment_name,
                    "endpoint": endpoint
                }
            ],
            "default_model": deployment_name,
            "supports_streaming": True,
            "supports_function_calling": True,
            "max_tokens_limit": 4096,
            "notes": [
                "Model capabilities depend on the underlying model deployed",
                "Contact your Azure administrator for deployment details"
            ]
        }
    
    def get_client_info(self) -> Dict[str, Any]:
        """
        Get information about the underlying Azure OpenAI client.
        
        Returns:
            Dict with client information
        """
        try:
            return self.client_manager.get_client_info(self.client_id)
        except Exception as e:
            return {
                "error": f"Failed to get client info: {str(e)}",
                "client_id": self.client_id,
                "provider": "azure_openai"
            }
    
    def get_deployment_name(self) -> str:
        """
        Get the Azure OpenAI deployment name.
        
        Returns:
            Deployment name string
        """
        return self.config.get('deployment_name') or self.config.get('model', 'unknown')
    
    def get_endpoint(self) -> str:
        """
        Get the Azure OpenAI endpoint.
        
        Returns:
            Endpoint URL string
        """
        return self.config.get('endpoint', 'unknown')
    
    def __del__(self):
        """Cleanup when provider is destroyed."""
        try:
            if hasattr(self, 'client_manager') and hasattr(self, 'client_id'):
                self.client_manager.close_client(self.client_id)
        except Exception:
            pass  # Ignore cleanup errors