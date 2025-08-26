"""
Base AI Provider Interface

Defines the common interface and data structures for all AI providers
to ensure consistent behavior across different AI services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum

# Import existing data structures for compatibility
from services.openai_client_manager import CompletionRequest, CompletionResponse


class ValidationStatus(Enum):
    """Status of provider validation"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """Result of provider configuration validation"""
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class BaseAIProvider(ABC):
    """
    Base interface for all AI providers.
    
    All provider implementations must inherit from this class and implement
    the required abstract methods to ensure consistent behavior.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('provider', '')
    
    @abstractmethod
    def make_completion(self, request: CompletionRequest) -> CompletionResponse:
        """
        Make a completion request to the AI provider.
        
        Args:
            request: Standardized completion request
            
        Returns:
            CompletionResponse: Standardized response
            
        Raises:
            Exception: Provider-specific errors
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> ValidationResult:
        """
        Validate the provider configuration.
        
        Returns:
            ValidationResult: Result of configuration validation
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about available models for this provider.
        
        Returns:
            Dict containing model information and capabilities
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return self.provider_name
    
    def get_config(self) -> Dict[str, Any]:
        """Get the provider configuration (without sensitive data)"""
        # Return config without API keys for security
        safe_config = self.config.copy()
        for key in safe_config:
            if 'key' in key.lower() or 'token' in key.lower():
                safe_config[key] = '***'
        return safe_config
    
    def test_connection(self) -> ValidationResult:
        """
        Test the connection to the provider with a simple request.
        
        Returns:
            ValidationResult: Result of connection test
        """
        try:
            test_request = CompletionRequest(
                messages=[{"role": "user", "content": "Say 'Hello World'"}],
                max_tokens=10,
                temperature=0.0
            )
            response = self.make_completion(test_request)
            
            if response.content:
                return ValidationResult(
                    status=ValidationStatus.SUCCESS,
                    message=f"Connection to {self.provider_name} successful",
                    details={"model": response.model, "usage": response.usage}
                )
            else:
                return ValidationResult(
                    status=ValidationStatus.ERROR,
                    message=f"Connection test failed: Empty response from {self.provider_name}"
                )
                
        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.ERROR,
                message=f"Connection test failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )