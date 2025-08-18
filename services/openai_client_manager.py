"""
OpenAI Client Manager for unified OpenAI client management.

This module provides a centralized singleton manager for OpenAI client instances,
supporting both regular OpenAI and Azure OpenAI configurations with connection
pooling and reuse functionality.
"""

import os
import logging
import threading
from typing import (
    Dict,
    List,
    Optional,
    Union,
    Any
)
from dataclasses import dataclass
from enum import Enum

import openai
from openai import (
    OpenAI,
    AzureOpenAI
)
import httpx

from utils.config import Config



class ClientType(Enum):
    """Types of OpenAI clients supported."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


@dataclass
class CompletionRequest:
    """Request parameters for OpenAI completion."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0


@dataclass
class CompletionResponse:
    """Response from OpenAI completion."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    success: bool = True
    error_message: Optional[str] = None


class OpenAIClientManager:
    """
    Singleton manager for OpenAI client instances with connection pooling and reuse.
    
    This class provides centralized management of OpenAI clients, supporting both
    regular OpenAI and Azure OpenAI configurations. It implements connection pooling
    and client reuse for better performance.
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
        """Initialize the OpenAI client manager."""
        if hasattr(self, '_initialized'):
            return
            
        self.logger = logging.getLogger(__name__)
        self._clients: Dict[str, Union[OpenAI, AzureOpenAI]] = {}
        self._http_clients: Dict[str, httpx.Client] = {}
        self._configs: Dict[str, Config] = {}
        self._default_config: Optional[Config] = None
        self._initialized = True
        
        self.logger.info("OpenAI Client Manager initialized")
    
    def configure(self, config: Config, client_id: str = "default") -> None:
        """
        Configure a client with the given configuration.
        
        Args:
            config: Configuration object with OpenAI settings
            client_id: Unique identifier for this client configuration
        """
        try:
            self.logger.info(f"Configuring OpenAI client '{client_id}'")
            
            # Store configuration
            self._configs[client_id] = config
            if client_id == "default":
                self._default_config = config
            
            # Create HTTP client for connection pooling
            http_client = httpx.Client(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
            self._http_clients[client_id] = http_client
            
            # Create OpenAI client based on configuration
            if config.use_azure_openai:
                if not config.azure_openai_api_key:
                    raise ValueError("Azure OpenAI API key is required when use_azure_openai is True")
                if not config.azure_openai_endpoint:
                    raise ValueError("Azure OpenAI endpoint is required when use_azure_openai is True")
                
                client = AzureOpenAI(
                    api_key=config.azure_openai_api_key,
                    azure_endpoint=config.azure_openai_endpoint,
                    api_version=config.azure_openai_api_version,
                    http_client=http_client
                )
                self.logger.info(f"Created Azure OpenAI client '{client_id}' with endpoint: {config.azure_openai_endpoint}")
            else:
                openai_api_key = config.openai_api_key or os.getenv('OPENAI_API_KEY')
                if not openai_api_key:
                    raise ValueError("OpenAI API key is required when Azure OpenAI is not configured")
                
                client = OpenAI(
                    api_key=openai_api_key,
                    http_client=http_client
                )
                self.logger.info(f"Created regular OpenAI client '{client_id}'")
            
            self._clients[client_id] = client
            
        except Exception as e:
            self.logger.error(f"Failed to configure OpenAI client '{client_id}': {str(e)}")
            raise
    
    def get_client(self, client_id: str = "default") -> Union[OpenAI, AzureOpenAI]:
        """
        Get configured OpenAI client instance.
        
        Args:
            client_id: Identifier for the client configuration
            
        Returns:
            OpenAI or AzureOpenAI client instance
            
        Raises:
            ValueError: If client is not configured
        """
        if client_id not in self._clients:
            if client_id == "default" and self._default_config is None:
                # Auto-configure default client from environment
                try:
                    config = Config.from_env()
                    self.configure(config, "default")
                except Exception as e:
                    raise ValueError(f"Client '{client_id}' not configured and auto-configuration failed: {str(e)}")
            else:
                raise ValueError(f"Client '{client_id}' not configured. Call configure() first.")
        
        return self._clients[client_id]
    
    def get_model_name(self, client_id: str = "default") -> str:
        """
        Get the model name for the specified client.
        
        Args:
            client_id: Identifier for the client configuration
            
        Returns:
            Model name string
        """
        if client_id not in self._configs:
            raise ValueError(f"Client '{client_id}' not configured")
        
        config = self._configs[client_id]
        if config.use_azure_openai:
            return config.azure_openai_deployment_name
        else:
            # Default model for regular OpenAI
            return "gpt-3.5-turbo"
    
    def make_completion(
        self,
        request: CompletionRequest,
        client_id: str = "default"
    ) -> CompletionResponse:
        """
        Make a completion request with standardized error handling.
        
        Args:
            request: Completion request parameters
            client_id: Identifier for the client to use
            
        Returns:
            CompletionResponse with result or error information
        """
        try:
            client = self.get_client(client_id)
            model_name = request.model or self.get_model_name(client_id)
            
            self.logger.debug(f"Making completion request with client '{client_id}' and model '{model_name}'")
            
            response = client.chat.completions.create(
                model=model_name,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty
            )
            
            # Extract response content
            content = response.choices[0].message.content.strip()
            
            # Create response object
            completion_response = CompletionResponse(
                content=content,
                model=response.model,
                usage=response.usage.model_dump() if response.usage else {},
                finish_reason=response.choices[0].finish_reason,
                success=True
            )
            
            self.logger.debug(f"Completion successful. Tokens used: {completion_response.usage}")
            return completion_response
            
        except openai.RateLimitError as e:
            self.logger.error(f"Rate limit exceeded for client '{client_id}': {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.get_model_name(client_id),
                usage={},
                finish_reason="rate_limit_error",
                success=False,
                error_message=f"Rate limit exceeded: {str(e)}"
            )
        
        except openai.APIConnectionError as e:
            self.logger.error(f"API connection error for client '{client_id}': {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.get_model_name(client_id),
                usage={},
                finish_reason="connection_error",
                success=False,
                error_message=f"API connection error: {str(e)}"
            )
        
        except openai.AuthenticationError as e:
            self.logger.error(f"Authentication error for client '{client_id}': {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.get_model_name(client_id),
                usage={},
                finish_reason="auth_error",
                success=False,
                error_message=f"Authentication error: {str(e)}"
            )
        
        except openai.BadRequestError as e:
            self.logger.error(f"Bad request error for client '{client_id}': {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.get_model_name(client_id),
                usage={},
                finish_reason="bad_request",
                success=False,
                error_message=f"Bad request: {str(e)}"
            )
        
        except Exception as e:
            self.logger.error(f"Unexpected error for client '{client_id}': {str(e)}")
            return CompletionResponse(
                content="",
                model=request.model or self.get_model_name(client_id),
                usage={},
                finish_reason="error",
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def make_simple_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        client_id: str = "default"
    ) -> str:
        """
        Make a simple completion request and return just the content.
        
        Args:
            messages: List of message dictionaries
            model: Optional model name override
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            client_id: Identifier for the client to use
            
        Returns:
            Generated content string
            
        Raises:
            Exception: If completion fails
        """
        request = CompletionRequest(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        response = self.make_completion(request, client_id)
        
        if not response.success:
            raise Exception(response.error_message)
        
        return response.content
    
    def list_clients(self) -> List[str]:
        """
        List all configured client IDs.
        
        Returns:
            List of client ID strings
        """
        return list(self._clients.keys())
    
    def get_client_info(self, client_id: str = "default") -> Dict[str, Any]:
        """
        Get information about a configured client.
        
        Args:
            client_id: Identifier for the client
            
        Returns:
            Dictionary with client information
        """
        if client_id not in self._configs:
            raise ValueError(f"Client '{client_id}' not configured")
        
        config = self._configs[client_id]
        
        return {
            "client_id": client_id,
            "client_type": ClientType.AZURE_OPENAI.value if config.use_azure_openai else ClientType.OPENAI.value,
            "model_name": self.get_model_name(client_id),
            "endpoint": config.azure_openai_endpoint if config.use_azure_openai else "https://api.openai.com",
            "api_version": config.azure_openai_api_version if config.use_azure_openai else "v1",
            "configured": client_id in self._clients
        }
    
    def close_client(self, client_id: str) -> None:
        """
        Close and remove a specific client.
        
        Args:
            client_id: Identifier for the client to close
        """
        if client_id in self._http_clients:
            self._http_clients[client_id].close()
            del self._http_clients[client_id]
        
        if client_id in self._clients:
            del self._clients[client_id]
        
        if client_id in self._configs:
            del self._configs[client_id]
        
        self.logger.info(f"Closed OpenAI client '{client_id}'")
    
    def close_all_clients(self) -> None:
        """Close all configured clients and clean up resources."""
        for client_id in list(self._clients.keys()):
            self.close_client(client_id)
        
        self.logger.info("Closed all OpenAI clients")
    
    def __del__(self):
        """Cleanup when manager is destroyed."""
        try:
            self.close_all_clients()
        except Exception:
            pass  # Ignore errors during cleanup


# Global instance for easy access
_client_manager = None


def get_client_manager() -> OpenAIClientManager:
    """
    Get the global OpenAI client manager instance.
    
    Returns:
        OpenAIClientManager singleton instance
    """
    global _client_manager
    if _client_manager is None:
        _client_manager = OpenAIClientManager()
    return _client_manager


def configure_default_client(config: Config) -> None:
    """
    Configure the default OpenAI client.
    
    Args:
        config: Configuration object with OpenAI settings
    """
    manager = get_client_manager()
    manager.configure(config, "default")


def get_default_client() -> Union[OpenAI, AzureOpenAI]:
    """
    Get the default configured OpenAI client.
    
    Returns:
        OpenAI or AzureOpenAI client instance
    """
    manager = get_client_manager()
    return manager.get_client("default")


def make_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    client_id: str = "default"
) -> str:
    """
    Convenience function for making simple completions.
    
    Args:
        messages: List of message dictionaries
        model: Optional model name override
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        client_id: Identifier for the client to use
        
    Returns:
        Generated content string
    """
    manager = get_client_manager()
    return manager.make_simple_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        client_id=client_id
    )
