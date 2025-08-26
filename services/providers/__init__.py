"""
AI Provider abstraction layer for multi-model support.

This package provides a unified interface for different AI providers
including OpenAI, Azure OpenAI, Anthropic Claude, Google Gemini, and DeepSeek.
"""

from .base_provider import BaseAIProvider, ValidationResult, ValidationStatus
from services.openai_client_manager import CompletionRequest, CompletionResponse

__all__ = [
    'BaseAIProvider',
    'CompletionRequest', 
    'CompletionResponse',
    'ValidationResult',
    'ValidationStatus'
]