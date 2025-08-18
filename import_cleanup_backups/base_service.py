"""
Base service class with common functionality for all services.

This module provides a base class that all services should inherit from,
providing standardized logging, error handling, rate limiting, and retry logic.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, TypeVar, Union
from functools import wraps
from dataclasses import dataclass

from utils.config import Config
from utils.logging_config import get_logger
from utils.error_handling import ErrorHandler, ErrorCategory, handle_error, retry_with_backoff, get_error_handler

T = TypeVar('T')


@dataclass
class ServiceConfig:
    """Configuration for service-specific settings."""
    name: str
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    enable_caching: bool = False
    cache_ttl: int = 3600


class BaseService(ABC):
    """
    Base class for all services providing common functionality.
    
    Features:
    - Standardized logging
    - Error handling and monitoring
    - Rate limiting
    - Retry logic with exponential backoff
    - Configuration management
    - Performance monitoring
    """
    
    def __init__(self, 
                 config: Config, 
                 service_config: Optional[ServiceConfig] = None,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize base service.
        
        Args:
            config: Global configuration object
            service_config: Service-specific configuration
            logger: Optional logger instance
        """
        self.config = config
        self.service_config = service_config or ServiceConfig(name=self.__class__.__name__)
        self.logger = logger or get_logger(self.__class__.__name__)
        self.error_handler = ErrorHandler()
        
        # Performance tracking
        self._operation_counts: Dict[str, int] = {}
        self._operation_times: Dict[str, float] = {}
        self._last_operation_time: Dict[str, float] = {}
        
        # Initialize service
        self._initialize_service()
        
        self.logger.info(f"Initialized {self.__class__.__name__} service")
    
    @abstractmethod
    def _initialize_service(self) -> None:
        """Initialize service-specific components. Must be implemented by subclasses."""
        pass
    
    def _apply_rate_limit(self, operation: str = "default") -> None:
        """
        Apply rate limiting for the specified operation.
        
        Args:
            operation: Operation name for rate limiting
        """
        current_time = time.time()
        last_time = self._last_operation_time.get(operation, 0)
        
        time_since_last = current_time - last_time
        if time_since_last < self.service_config.rate_limit_delay:
            sleep_time = self.service_config.rate_limit_delay - time_since_last
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self._last_operation_time[operation] = time.time()
    
    def _track_operation(self, operation: str, duration: float) -> None:
        """
        Track operation performance metrics.
        
        Args:
            operation: Operation name
            duration: Operation duration in seconds
        """
        self._operation_counts[operation] = self._operation_counts.get(operation, 0) + 1
        self._operation_times[operation] = self._operation_times.get(operation, 0) + duration
        
        # Log slow operations
        if duration > 10.0:  # Log operations taking more than 10 seconds
            avg_time = self._operation_times[operation] / self._operation_counts[operation]
            self.logger.warning(
                f"Slow operation detected: {operation} took {duration:.2f}s "
                f"(avg: {avg_time:.2f}s, count: {self._operation_counts[operation]})"
            )
    
    def _make_api_call(self, 
                      func: Callable[..., T], 
                      *args, 
                      operation: str = "api_call",
                      category: ErrorCategory = ErrorCategory.NETWORK,
                      apply_rate_limit: bool = True,
                      **kwargs) -> T:
        """
        Make an API call with standardized error handling and rate limiting.
        
        Args:
            func: Function to call
            *args: Function arguments
            operation: Operation name for tracking
            category: Error category for retry logic
            apply_rate_limit: Whether to apply rate limiting
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        if apply_rate_limit:
            self._apply_rate_limit(operation)
        
        start_time = time.time()
        
        try:
            result = self.error_handler.retry_with_backoff(
                func,
                *args,
                category=category,
                context={
                    'service': self.__class__.__name__,
                    'operation': operation,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                },
                **kwargs
            )
            
            duration = time.time() - start_time
            self._track_operation(operation, duration)
            
            self.logger.debug(f"API call {operation} completed in {duration:.2f}s")
            return result
            
        except Exception as error:
            duration = time.time() - start_time
            self._track_operation(f"{operation}_failed", duration)
            
            # Handle the error through our error handler
            self.error_handler.handle_error(
                error=error,
                service=self.__class__.__name__,
                operation=operation,
                context={
                    'duration': duration,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                },
                category=category
            )
            
            raise
    
    def _validate_input(self, data: Any, operation: str) -> None:
        """
        Validate input data for an operation.
        
        Args:
            data: Data to validate
            operation: Operation name for error context
            
        Raises:
            ValueError: If validation fails
        """
        if data is None:
            raise ValueError(f"Input data cannot be None for operation: {operation}")
        
        # Subclasses can override this method for specific validation
        self._custom_validation(data, operation)
    
    def _custom_validation(self, data: Any, operation: str) -> None:
        """
        Custom validation logic to be implemented by subclasses.
        
        Args:
            data: Data to validate
            operation: Operation name for error context
        """
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this service.
        
        Returns:
            Dictionary with performance metrics
        """
        metrics = {
            'service_name': self.__class__.__name__,
            'total_operations': sum(self._operation_counts.values()),
            'operations': {}
        }
        
        for operation, count in self._operation_counts.items():
            total_time = self._operation_times.get(operation, 0)
            avg_time = total_time / count if count > 0 else 0
            
            metrics['operations'][operation] = {
                'count': count,
                'total_time': total_time,
                'average_time': avg_time
            }
        
        return metrics
    
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        self._operation_counts.clear()
        self._operation_times.clear()
        self._last_operation_time.clear()
        self.logger.info(f"Reset performance metrics for {self.__class__.__name__}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check of the service.
        
        Returns:
            Dictionary with health status
        """
        try:
            # Basic health check - subclasses can override
            status = self._perform_health_check()
            
            return {
                'service': self.__class__.__name__,
                'status': 'healthy' if status else 'unhealthy',
                'timestamp': time.time(),
                'metrics': self.get_performance_metrics()
            }
            
        except Exception as error:
            self.logger.error(f"Health check failed: {error}")
            return {
                'service': self.__class__.__name__,
                'status': 'unhealthy',
                'error': str(error),
                'timestamp': time.time()
            }
    
    def _perform_health_check(self) -> bool:
        """
        Perform service-specific health check.
        
        Returns:
            True if healthy, False otherwise
        """
        # Default implementation - subclasses should override
        return True
    
    def shutdown(self) -> None:
        """Gracefully shutdown the service."""
        self.logger.info(f"Shutting down {self.__class__.__name__} service")
        
        # Log final metrics
        metrics = self.get_performance_metrics()
        if metrics['total_operations'] > 0:
            self.logger.info(f"Final metrics: {metrics}")
        
        # Perform service-specific cleanup
        self._cleanup()
    
    def _cleanup(self) -> None:
        """Perform service-specific cleanup. Can be overridden by subclasses."""
        pass


def service_operation(operation_name: str = None, 
                     category: ErrorCategory = ErrorCategory.UNKNOWN,
                     apply_rate_limit: bool = True):
    """
    Decorator for service operations with automatic error handling and rate limiting.
    
    Args:
        operation_name: Name of the operation (defaults to function name)
        category: Error category for retry logic
        apply_rate_limit: Whether to apply rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not isinstance(self, BaseService):
                raise TypeError("service_operation decorator can only be used on BaseService methods")
            
            op_name = operation_name or func.__name__
            
            # Apply rate limiting if enabled
            if apply_rate_limit:
                self._apply_rate_limit(op_name)
            
            # Track operation timing
            start_time = time.time()
            
            try:
                result = func(self, *args, **kwargs)
                duration = time.time() - start_time
                self._track_operation(op_name, duration)
                
                self.logger.debug(f"Operation {op_name} completed in {duration:.2f}s")
                return result
                
            except Exception as error:
                duration = time.time() - start_time
                self._track_operation(f"{op_name}_failed", duration)
                
                # Handle error
                self.error_handler.handle_error(
                    error=error,
                    service=self.__class__.__name__,
                    operation=op_name,
                    context={
                        'duration': duration,
                        'function': func.__name__,
                        'args_count': len(args),
                        'kwargs_keys': list(kwargs.keys())
                    },
                    category=category
                )
                
                raise
        
        return wrapper
    return decorator


# Utility functions for common retry patterns
def retry_on_network_error(func: Callable) -> Callable:
    """Decorator for retrying on network errors."""
    return retry_with_backoff(category=ErrorCategory.NETWORK)(func)


def retry_on_rate_limit(func: Callable) -> Callable:
    """Decorator for retrying on rate limit errors."""
    return retry_with_backoff(category=ErrorCategory.API_RATE_LIMIT)(func)


def retry_on_api_error(func: Callable) -> Callable:
    """Decorator for retrying on general API errors."""
    return retry_with_backoff(category=ErrorCategory.NETWORK)(func)