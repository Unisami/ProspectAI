"""
Enhanced error handling framework with comprehensive error categorization,
recovery strategies, and standardized error responses.

This module extends the existing error handling with more sophisticated
error categorization, recovery strategies, and standardized responses.
"""

import time
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union
)
from functools import wraps
from dataclasses import (
    dataclass,
    field
)
from datetime import (
    datetime,
    timedelta
)
from enum import Enum

from utils.logging_config import get_logger
from utils.error_handling import (
    ErrorHandler,
    ErrorCategory,
    ErrorSeverity
)




class RecoveryStrategy(Enum):
    """Recovery strategies for different types of errors."""
    RETRY_IMMEDIATE = "retry_immediate"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    RETRY_AFTER_DELAY = "retry_after_delay"
    FALLBACK_METHOD = "fallback_method"
    SKIP_AND_CONTINUE = "skip_and_continue"
    FAIL_FAST = "fail_fast"
    USER_INTERVENTION = "user_intervention"


@dataclass
class ErrorResponse:
    """Standardized error response with recovery actions."""
    error_id: str
    timestamp: datetime
    service: str
    operation: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    technical_details: str
    
    # Recovery information
    should_retry: bool
    retry_strategy: RecoveryStrategy
    retry_delay: float
    max_retries: int
    fallback_available: bool
    
    # User-facing information
    user_message: str
    suggested_actions: List[str] = field(default_factory=list)
    
    # Context and metadata
    context: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary."""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp.isoformat(),
            'service': self.service,
            'operation': self.operation,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'technical_details': self.technical_details,
            'should_retry': self.should_retry,
            'retry_strategy': self.retry_strategy.value,
            'retry_delay': self.retry_delay,
            'max_retries': self.max_retries,
            'fallback_available': self.fallback_available,
            'user_message': self.user_message,
            'suggested_actions': self.suggested_actions,
            'context': self.context,
            'stack_trace': self.stack_trace
        }


@dataclass
class ErrorPattern:
    """Pattern for matching and handling specific error types."""
    name: str
    error_types: List[Type[Exception]]
    message_patterns: List[str]
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay: float = 1.0
    user_message: str = ""
    suggested_actions: List[str] = field(default_factory=list)


class ErrorHandlingService:
    """
    Enhanced error handling service with comprehensive error categorization,
    recovery strategies, and standardized error responses.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.base_handler = ErrorHandler(config_path)
        
        # Error patterns for sophisticated matching
        self.error_patterns = self._initialize_error_patterns()
        
        # Recovery strategies
        self.recovery_handlers = {
            RecoveryStrategy.RETRY_IMMEDIATE: self._handle_retry_immediate,
            RecoveryStrategy.RETRY_WITH_BACKOFF: self._handle_retry_with_backoff,
            RecoveryStrategy.RETRY_AFTER_DELAY: self._handle_retry_after_delay,
            RecoveryStrategy.FALLBACK_METHOD: self._handle_fallback_method,
            RecoveryStrategy.SKIP_AND_CONTINUE: self._handle_skip_and_continue,
            RecoveryStrategy.FAIL_FAST: self._handle_fail_fast,
            RecoveryStrategy.USER_INTERVENTION: self._handle_user_intervention
        }
        
        # Circuit breaker state
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Enhanced error handling service initialized")
    
    def handle_error(self, 
                    error: Exception,
                    service: str,
                    operation: str,
                    context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
        """
        Handle an error with enhanced categorization and recovery strategies.
        
        Args:
            error: The exception that occurred
            service: Name of the service where error occurred
            operation: Operation being performed when error occurred
            context: Additional context information
            
        Returns:
            ErrorResponse with detailed error information and recovery strategy
        """
        # Match error against patterns
        pattern = self._match_error_pattern(error)
        
        # Generate error ID
        error_id = f"{service}_{operation}_{int(time.time())}"
        
        # Create base error info using existing handler
        base_error = self.base_handler.handle_error(
            error=error,
            service=service,
            operation=operation,
            context=context,
            category=pattern.category if pattern else None,
            severity=pattern.severity if pattern else None
        )
        
        # Create enhanced error response
        error_response = ErrorResponse(
            error_id=error_id,
            timestamp=datetime.now(),
            service=service,
            operation=operation,
            category=pattern.category if pattern else self._categorize_error(error),
            severity=pattern.severity if pattern else self._assess_severity(error),
            message=str(error),
            technical_details=self._extract_technical_details(error),
            should_retry=self._should_retry(error, pattern),
            retry_strategy=pattern.recovery_strategy if pattern else RecoveryStrategy.RETRY_WITH_BACKOFF,
            retry_delay=pattern.retry_delay if pattern else 1.0,
            max_retries=pattern.max_retries if pattern else 3,
            fallback_available=self._has_fallback(service, operation),
            user_message=self._generate_user_message(error, pattern),
            suggested_actions=pattern.suggested_actions if pattern else self._generate_suggested_actions(error),
            context=context or {},
            stack_trace=traceback.format_exc()
        )
        
        # Check circuit breaker
        self._update_circuit_breaker(service, operation, error_response)
        
        # Log error response
        self._log_error_response(error_response)
        
        return error_response
    
    def execute_with_recovery(self,
                            func: Callable,
                            service: str,
                            operation: str,
                            *args,
                            context: Optional[Dict[str, Any]] = None,
                            fallback_func: Optional[Callable] = None,
                            **kwargs) -> Any:
        """
        Execute a function with automatic error handling and recovery.
        
        Args:
            func: Function to execute
            service: Service name
            operation: Operation name
            *args: Function arguments
            context: Additional context
            fallback_func: Optional fallback function
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
            
        Raises:
            Exception: If all recovery attempts fail
        """
        # Check circuit breaker
        if self._is_circuit_open(service, operation):
            raise RuntimeError(f"Circuit breaker open for {service}.{operation}")
        
        last_error_response = None
        
        for attempt in range(1, 4):  # Default max attempts
            try:
                result = func(*args, **kwargs)
                
                # Reset circuit breaker on success
                self._reset_circuit_breaker(service, operation)
                
                return result
                
            except Exception as error:
                error_response = self.handle_error(error, service, operation, context)
                last_error_response = error_response
                
                # Apply recovery strategy
                if error_response.should_retry and attempt < error_response.max_retries:
                    recovery_result = self._apply_recovery_strategy(
                        error_response, func, args, kwargs, attempt
                    )
                    
                    if recovery_result is not None:
                        return recovery_result
                else:
                    break
        
        # All attempts failed, try fallback if available
        if fallback_func and last_error_response.fallback_available:
            try:
                self.logger.info(f"Attempting fallback for {service}.{operation}")
                return fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                self.logger.error(f"Fallback also failed: {fallback_error}")
        
        # No recovery possible
        raise last_error_response.message if last_error_response else error
    
    def get_error_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive error statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error statistics
        """
        base_stats = self.base_handler.get_error_summary(hours)
        
        # Add enhanced statistics
        enhanced_stats = {
            **base_stats,
            'circuit_breakers': {
                service_op: {
                    'state': cb['state'],
                    'failure_count': cb['failure_count'],
                    'last_failure': cb['last_failure'].isoformat() if cb['last_failure'] else None
                }
                for service_op, cb in self.circuit_breakers.items()
            },
            'recovery_strategies': self._get_recovery_strategy_stats(),
            'error_patterns': self._get_error_pattern_stats()
        }
        
        return enhanced_stats
    
    def _initialize_error_patterns(self) -> List[ErrorPattern]:
        """Initialize predefined error patterns."""
        return [
            # Network errors
            ErrorPattern(
                name="connection_timeout",
                error_types=[ConnectionError, TimeoutError],
                message_patterns=["timeout", "connection", "unreachable"],
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                max_retries=3,
                retry_delay=2.0,
                user_message="Network connection issue. Retrying automatically.",
                suggested_actions=["Check internet connection", "Verify service availability"]
            ),
            
            # Rate limiting
            ErrorPattern(
                name="rate_limit_exceeded",
                error_types=[],
                message_patterns=["rate limit", "too many requests", "429"],
                category=ErrorCategory.API_RATE_LIMIT,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_AFTER_DELAY,
                max_retries=5,
                retry_delay=60.0,
                user_message="API rate limit reached. Waiting before retry.",
                suggested_actions=["Wait for rate limit reset", "Consider upgrading API plan"]
            ),
            
            # Authentication errors
            ErrorPattern(
                name="authentication_failed",
                error_types=[],
                message_patterns=["unauthorized", "401", "forbidden", "403", "invalid token"],
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.CRITICAL,
                recovery_strategy=RecoveryStrategy.USER_INTERVENTION,
                max_retries=1,
                user_message="Authentication failed. Please check your credentials.",
                suggested_actions=["Verify API keys", "Check token expiration", "Update credentials"]
            ),
            
            # Data validation errors
            ErrorPattern(
                name="validation_error",
                error_types=[ValueError, TypeError],
                message_patterns=["invalid", "malformed", "validation"],
                category=ErrorCategory.DATA_VALIDATION,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
                max_retries=1,
                user_message="Data validation failed. Skipping invalid data.",
                suggested_actions=["Check data format", "Verify input requirements"]
            ),
            
            # Scraping errors
            ErrorPattern(
                name="scraping_failed",
                error_types=[],
                message_patterns=["element not found", "selenium", "webdriver", "page load"],
                category=ErrorCategory.SCRAPING,
                severity=ErrorSeverity.MEDIUM,
                recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                max_retries=2,
                retry_delay=3.0,
                user_message="Web scraping issue. Retrying with different approach.",
                suggested_actions=["Check website availability", "Verify page structure"]
            ),
            
            # Storage errors
            ErrorPattern(
                name="storage_error",
                error_types=[],
                message_patterns=["database", "storage", "notion", "save failed"],
                category=ErrorCategory.STORAGE,
                severity=ErrorSeverity.HIGH,
                recovery_strategy=RecoveryStrategy.FALLBACK_METHOD,
                max_retries=3,
                retry_delay=1.0,
                user_message="Storage operation failed. Trying alternative method.",
                suggested_actions=["Check storage service status", "Verify permissions"]
            )
        ]
    
    def _match_error_pattern(self, error: Exception) -> Optional[ErrorPattern]:
        """Match an error against predefined patterns."""
        error_str = str(error).lower()
        error_type = type(error)
        
        for pattern in self.error_patterns:
            # Check error type match
            if error_type in pattern.error_types:
                return pattern
            
            # Check message pattern match
            if any(msg_pattern in error_str for msg_pattern in pattern.message_patterns):
                return pattern
        
        return None
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Fallback error categorization."""
        return self.base_handler._categorize_error(error)
    
    def _assess_severity(self, error: Exception) -> ErrorSeverity:
        """Fallback severity assessment."""
        return self.base_handler._assess_severity(error, self._categorize_error(error))
    
    def _extract_technical_details(self, error: Exception) -> str:
        """Extract technical details from error."""
        details = [
            f"Error Type: {type(error).__name__}",
            f"Error Message: {str(error)}"
        ]
        
        # Add specific details based on error type
        if hasattr(error, 'response'):
            details.append(f"HTTP Status: {getattr(error.response, 'status_code', 'Unknown')}")
        
        if hasattr(error, 'code'):
            details.append(f"Error Code: {error.code}")
        
        return " | ".join(details)
    
    def _should_retry(self, error: Exception, pattern: Optional[ErrorPattern]) -> bool:
        """Determine if error should be retried."""
        if pattern:
            return pattern.recovery_strategy in [
                RecoveryStrategy.RETRY_IMMEDIATE,
                RecoveryStrategy.RETRY_WITH_BACKOFF,
                RecoveryStrategy.RETRY_AFTER_DELAY
            ]
        
        # Default retry logic
        non_retryable_errors = [KeyboardInterrupt, SystemExit, MemoryError]
        return not any(isinstance(error, err_type) for err_type in non_retryable_errors)
    
    def _has_fallback(self, service: str, operation: str) -> bool:
        """Check if fallback is available for service/operation."""
        # This would be configured based on actual service capabilities
        fallback_operations = {
            'ai_parser': ['parse_linkedin_profile'],
            'email_finder': ['find_email'],
            'scraping_service': ['scrape_linkedin_profile']
        }
        
        return operation in fallback_operations.get(service, [])
    
    def _generate_user_message(self, error: Exception, pattern: Optional[ErrorPattern]) -> str:
        """Generate user-friendly error message."""
        if pattern and pattern.user_message:
            return pattern.user_message
        
        # Default user messages based on error type
        error_str = str(error).lower()
        
        if "network" in error_str or "connection" in error_str:
            return "Network connectivity issue. Please check your internet connection."
        elif "rate limit" in error_str:
            return "API rate limit reached. The system will automatically retry."
        elif "unauthorized" in error_str or "forbidden" in error_str:
            return "Authentication issue. Please check your API credentials."
        else:
            return "An unexpected error occurred. The system will attempt to recover."
    
    def _generate_suggested_actions(self, error: Exception) -> List[str]:
        """Generate suggested actions for error recovery."""
        error_str = str(error).lower()
        actions = []
        
        if "network" in error_str or "connection" in error_str:
            actions.extend([
                "Check internet connection",
                "Verify service endpoint availability",
                "Try again in a few minutes"
            ])
        elif "rate limit" in error_str:
            actions.extend([
                "Wait for rate limit reset",
                "Consider reducing request frequency",
                "Upgrade API plan if needed"
            ])
        elif "auth" in error_str:
            actions.extend([
                "Verify API credentials",
                "Check token expiration",
                "Update configuration"
            ])
        else:
            actions.append("Contact support if issue persists")
        
        return actions
    
    def _apply_recovery_strategy(self,
                               error_response: ErrorResponse,
                               func: Callable,
                               args: tuple,
                               kwargs: dict,
                               attempt: int) -> Optional[Any]:
        """Apply the appropriate recovery strategy."""
        strategy = error_response.retry_strategy
        
        if strategy in self.recovery_handlers:
            return self.recovery_handlers[strategy](error_response, func, args, kwargs, attempt)
        
        return None
    
    def _handle_retry_immediate(self, error_response: ErrorResponse, func: Callable, 
                              args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle immediate retry strategy."""
        self.logger.info(f"Immediate retry for {error_response.service}.{error_response.operation}")
        return None  # Let the main loop handle the retry
    
    def _handle_retry_with_backoff(self, error_response: ErrorResponse, func: Callable,
                                 args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle retry with exponential backoff strategy."""
        delay = error_response.retry_delay * (2 ** (attempt - 1))
        self.logger.info(f"Retry with backoff: waiting {delay}s for {error_response.service}.{error_response.operation}")
        time.sleep(delay)
        return None  # Let the main loop handle the retry
    
    def _handle_retry_after_delay(self, error_response: ErrorResponse, func: Callable,
                                args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle retry after fixed delay strategy."""
        self.logger.info(f"Retry after delay: waiting {error_response.retry_delay}s")
        time.sleep(error_response.retry_delay)
        return None  # Let the main loop handle the retry
    
    def _handle_fallback_method(self, error_response: ErrorResponse, func: Callable,
                              args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle fallback method strategy."""
        self.logger.info(f"Attempting fallback method for {error_response.service}.{error_response.operation}")
        # This would need to be implemented based on specific service fallbacks
        return None
    
    def _handle_skip_and_continue(self, error_response: ErrorResponse, func: Callable,
                                args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle skip and continue strategy."""
        self.logger.warning(f"Skipping failed operation: {error_response.service}.{error_response.operation}")
        return None  # Return None to indicate skipping
    
    def _handle_fail_fast(self, error_response: ErrorResponse, func: Callable,
                        args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle fail fast strategy."""
        self.logger.error(f"Failing fast for {error_response.service}.{error_response.operation}")
        raise RuntimeError(error_response.message)
    
    def _handle_user_intervention(self, error_response: ErrorResponse, func: Callable,
                                args: tuple, kwargs: dict, attempt: int) -> Optional[Any]:
        """Handle user intervention strategy."""
        self.logger.critical(f"User intervention required for {error_response.service}.{error_response.operation}")
        # This would typically trigger notifications or alerts
        raise RuntimeError(f"User intervention required: {error_response.user_message}")
    
    def _update_circuit_breaker(self, service: str, operation: str, error_response: ErrorResponse) -> None:
        """Update circuit breaker state."""
        key = f"{service}.{operation}"
        
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {
                'state': 'closed',
                'failure_count': 0,
                'last_failure': None,
                'next_attempt': None
            }
        
        cb = self.circuit_breakers[key]
        
        if error_response.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            cb['failure_count'] += 1
            cb['last_failure'] = datetime.now()
            
            # Open circuit after 5 consecutive failures
            if cb['failure_count'] >= 5:
                cb['state'] = 'open'
                cb['next_attempt'] = datetime.now() + timedelta(minutes=5)
                self.logger.warning(f"Circuit breaker opened for {key}")
    
    def _is_circuit_open(self, service: str, operation: str) -> bool:
        """Check if circuit breaker is open."""
        key = f"{service}.{operation}"
        cb = self.circuit_breakers.get(key)
        
        if not cb or cb['state'] != 'open':
            return False
        
        # Check if it's time to try again
        if cb['next_attempt'] and datetime.now() >= cb['next_attempt']:
            cb['state'] = 'half-open'
            return False
        
        return True
    
    def _reset_circuit_breaker(self, service: str, operation: str) -> None:
        """Reset circuit breaker on successful operation."""
        key = f"{service}.{operation}"
        if key in self.circuit_breakers:
            self.circuit_breakers[key] = {
                'state': 'closed',
                'failure_count': 0,
                'last_failure': None,
                'next_attempt': None
            }
    
    def _log_error_response(self, error_response: ErrorResponse) -> None:
        """Log error response based on severity."""
        log_message = f"[{error_response.error_id}] {error_response.service}.{error_response.operation}: {error_response.message}"
        
        if error_response.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_response.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_response.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
    
    def _get_recovery_strategy_stats(self) -> Dict[str, int]:
        """Get statistics on recovery strategy usage."""
        # This would track which strategies are used most often
        return {}
    
    def _get_error_pattern_stats(self) -> Dict[str, int]:
        """Get statistics on error pattern matches."""
        # This would track which patterns are matched most often
        return {}


# Global enhanced error handler instance
_global_enhanced_handler = None


def get_enhanced_error_handler() -> ErrorHandlingService:
    """Get the global enhanced error handler instance."""
    global _global_enhanced_handler
    if _global_enhanced_handler is None:
        _global_enhanced_handler = ErrorHandlingService()
    return _global_enhanced_handler


def handle_error_enhanced(error: Exception,
                        service: str,
                        operation: str,
                        context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Convenience function to handle errors using the enhanced error handler."""
    return get_enhanced_error_handler().handle_error(error, service, operation, context)


def execute_with_recovery(func: Callable,
                        service: str,
                        operation: str,
                        *args,
                        context: Optional[Dict[str, Any]] = None,
                        fallback_func: Optional[Callable] = None,
                        **kwargs) -> Any:
    """Convenience function to execute with recovery using the enhanced error handler."""
    return get_enhanced_error_handler().execute_with_recovery(
        func, service, operation, *args, context=context, fallback_func=fallback_func, **kwargs
    )
