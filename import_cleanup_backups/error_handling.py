"""
Centralized error handling and monitoring system for the job prospect automation system.
"""

import time
import logging
import traceback
from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path

from utils.logging_config import get_logger


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = "network"
    API_RATE_LIMIT = "api_rate_limit"
    API_QUOTA = "api_quota"
    AUTHENTICATION = "authentication"
    DATA_VALIDATION = "data_validation"
    SCRAPING = "scraping"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Detailed error information."""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    service: str
    operation: str
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False
    resolution_time: Optional[datetime] = None


@dataclass
class ServiceQuota:
    """Service quota and usage tracking."""
    service_name: str
    quota_type: str
    limit: int
    used: int
    reset_time: datetime
    warning_threshold: float = 0.8  # Warn at 80% usage
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage."""
        return (self.used / self.limit) * 100 if self.limit > 0 else 0
    
    @property
    def is_near_limit(self) -> bool:
        """Check if usage is near the limit."""
        return self.usage_percentage >= (self.warning_threshold * 100)
    
    @property
    def is_exhausted(self) -> bool:
        """Check if quota is exhausted."""
        return self.used >= self.limit


class RetryConfig:
    """Configuration for retry mechanisms."""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class ErrorHandler:
    """Centralized error handler with monitoring and retry capabilities."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.errors: List[ErrorInfo] = []
        self.service_quotas: Dict[str, ServiceQuota] = {}
        self.error_counts: Dict[str, int] = {}
        self.config_path = config_path or "logs/error_monitoring.json"
        
        # Load existing error data
        self._load_error_data()
        
        # Default retry configurations for different error types
        self.retry_configs = {
            ErrorCategory.NETWORK: RetryConfig(max_attempts=3, base_delay=2.0),
            ErrorCategory.API_RATE_LIMIT: RetryConfig(max_attempts=5, base_delay=5.0, max_delay=300.0),
            ErrorCategory.SCRAPING: RetryConfig(max_attempts=2, base_delay=3.0),
            ErrorCategory.STORAGE: RetryConfig(max_attempts=3, base_delay=1.0),
            ErrorCategory.UNKNOWN: RetryConfig(max_attempts=2, base_delay=1.0)
        }
    
    def handle_error(self, 
                    error: Exception,
                    service: str,
                    operation: str,
                    context: Optional[Dict[str, Any]] = None,
                    category: Optional[ErrorCategory] = None,
                    severity: Optional[ErrorSeverity] = None) -> ErrorInfo:
        """
        Handle and log an error with detailed information.
        
        Args:
            error: The exception that occurred
            service: Name of the service where error occurred
            operation: Operation being performed when error occurred
            context: Additional context information
            category: Error category (auto-detected if not provided)
            severity: Error severity (auto-detected if not provided)
            
        Returns:
            ErrorInfo object with error details
        """
        # Auto-detect category and severity if not provided
        if category is None:
            category = self._categorize_error(error)
        
        if severity is None:
            severity = self._assess_severity(error, category)
        
        # Generate unique error ID
        error_id = f"{service}_{operation}_{int(time.time())}"
        
        # Create error info
        error_info = ErrorInfo(
            error_id=error_id,
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            service=service,
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )
        
        # Store error
        self.errors.append(error_info)
        
        # Update error counts
        error_key = f"{service}_{category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Log error based on severity
        self._log_error(error_info)
        
        # Save error data
        self._save_error_data()
        
        # Check for error patterns
        self._check_error_patterns(error_info)
        
        return error_info
    
    def retry_with_backoff(self, 
                          func: Callable,
                          *args,
                          category: ErrorCategory = ErrorCategory.UNKNOWN,
                          context: Optional[Dict[str, Any]] = None,
                          **kwargs) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Args:
            func: Function to execute
            *args: Function arguments
            category: Error category for retry configuration
            context: Additional context for error handling
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        retry_config = self.retry_configs.get(category, self.retry_configs[ErrorCategory.UNKNOWN])
        last_error = None
        
        for attempt in range(retry_config.max_attempts):
            try:
                result = func(*args, **kwargs)
                
                # If we had previous errors for this operation, mark as resolved
                if attempt > 0:
                    self.logger.info(f"Operation succeeded after {attempt} retries")
                
                return result
                
            except Exception as error:
                last_error = error
                
                # Handle the error
                error_info = self.handle_error(
                    error=error,
                    service=func.__module__ if hasattr(func, '__module__') else 'unknown',
                    operation=func.__name__ if hasattr(func, '__name__') else 'unknown',
                    context={**(context or {}), 'attempt': attempt + 1, 'max_attempts': retry_config.max_attempts},
                    category=category
                )
                
                error_info.retry_count = attempt + 1
                
                # If this is the last attempt, don't wait
                if attempt == retry_config.max_attempts - 1:
                    break
                
                # Calculate delay with exponential backoff
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** attempt),
                    retry_config.max_delay
                )
                
                # Add jitter to prevent thundering herd
                if retry_config.jitter:
                    import random
                    delay *= (0.5 + random.random() * 0.5)
                
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(error)}")
                time.sleep(delay)
        
        # All attempts failed
        self.logger.error(f"All {retry_config.max_attempts} attempts failed for operation")
        raise last_error
    
    def update_service_quota(self, 
                           service_name: str,
                           quota_type: str,
                           used: int,
                           limit: int,
                           reset_time: datetime) -> None:
        """
        Update service quota information.
        
        Args:
            service_name: Name of the service
            quota_type: Type of quota (e.g., 'requests', 'credits')
            used: Current usage
            limit: Quota limit
            reset_time: When quota resets
        """
        quota_key = f"{service_name}_{quota_type}"
        
        quota = ServiceQuota(
            service_name=service_name,
            quota_type=quota_type,
            limit=limit,
            used=used,
            reset_time=reset_time
        )
        
        self.service_quotas[quota_key] = quota
        
        # Log quota warnings
        if quota.is_near_limit:
            self.logger.warning(f"{service_name} {quota_type} quota at {quota.usage_percentage:.1f}% usage")
        
        if quota.is_exhausted:
            self.logger.error(f"{service_name} {quota_type} quota exhausted!")
    
    def get_quota_status(self, service_name: Optional[str] = None) -> Dict[str, ServiceQuota]:
        """
        Get quota status for services.
        
        Args:
            service_name: Optional service name to filter by
            
        Returns:
            Dictionary of quota information
        """
        if service_name:
            return {k: v for k, v in self.service_quotas.items() if v.service_name == service_name}
        return self.service_quotas.copy()
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get error summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error summary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]
        
        # Group by category
        by_category = {}
        by_severity = {}
        by_service = {}
        
        for error in recent_errors:
            # By category
            cat_key = error.category.value
            by_category[cat_key] = by_category.get(cat_key, 0) + 1
            
            # By severity
            sev_key = error.severity.value
            by_severity[sev_key] = by_severity.get(sev_key, 0) + 1
            
            # By service
            by_service[error.service] = by_service.get(error.service, 0) + 1
        
        return {
            'total_errors': len(recent_errors),
            'time_period_hours': hours,
            'by_category': by_category,
            'by_severity': by_severity,
            'by_service': by_service,
            'recent_errors': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'service': e.service,
                    'operation': e.operation,
                    'category': e.category.value,
                    'severity': e.severity.value,
                    'message': e.error_message
                }
                for e in recent_errors[-10:]  # Last 10 errors
            ]
        }
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Automatically categorize an error based on its type and message."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Rate limiting (check first as it's more specific)
        if any(keyword in error_str for keyword in ['rate limit', 'too many requests', '429']):
            return ErrorCategory.API_RATE_LIMIT
        
        # Quota exhausted
        if any(keyword in error_str for keyword in ['quota', 'limit exceeded', 'usage limit']):
            return ErrorCategory.API_QUOTA
        
        # Authentication
        if any(keyword in error_str for keyword in ['auth', 'unauthorized', '401', 'forbidden', '403']):
            return ErrorCategory.AUTHENTICATION
        
        # Data validation
        if any(keyword in error_str for keyword in ['validation', 'invalid', 'malformed']):
            return ErrorCategory.DATA_VALIDATION
        
        # Scraping-related
        if any(keyword in error_str for keyword in ['selenium', 'webdriver', 'element not found', 'scraping']):
            return ErrorCategory.SCRAPING
        
        # Storage-related (check before network to catch database connection errors)
        if any(keyword in error_str for keyword in ['database', 'storage', 'notion', 'save', 'store']):
            return ErrorCategory.STORAGE
        
        # Configuration
        if any(keyword in error_str for keyword in ['config', 'setting', 'environment', 'key not found']):
            return ErrorCategory.CONFIGURATION
        
        # Network-related errors (check last as it's more general)
        if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'dns']):
            return ErrorCategory.NETWORK
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess error severity based on error type and category."""
        error_str = str(error).lower()
        
        # Critical errors
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.CRITICAL
        
        if any(keyword in error_str for keyword in ['critical', 'fatal', 'corruption']):
            return ErrorSeverity.CRITICAL
        
        # High severity
        if category in [ErrorCategory.API_QUOTA, ErrorCategory.CONFIGURATION]:
            return ErrorSeverity.HIGH
        
        if any(keyword in error_str for keyword in ['failed to initialize', 'service unavailable']):
            return ErrorSeverity.HIGH
        
        # Medium severity
        if category in [ErrorCategory.API_RATE_LIMIT, ErrorCategory.STORAGE]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for network and scraping issues (often transient)
        if category in [ErrorCategory.NETWORK, ErrorCategory.SCRAPING]:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error based on its severity."""
        log_message = f"[{error_info.error_id}] {error_info.service}.{error_info.operation}: {error_info.error_message}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_info.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Log context if available
        if error_info.context:
            self.logger.debug(f"Error context: {json.dumps(error_info.context, default=str)}")
    
    def _check_error_patterns(self, error_info: ErrorInfo) -> None:
        """Check for error patterns that might indicate systemic issues."""
        # Check for repeated errors in the same service/operation
        recent_errors = [
            e for e in self.errors[-10:]  # Last 10 errors
            if e.service == error_info.service and e.operation == error_info.operation
        ]
        
        if len(recent_errors) >= 3:
            self.logger.warning(f"Repeated errors detected in {error_info.service}.{error_info.operation}")
        
        # Check for high error rate
        recent_time = datetime.now() - timedelta(minutes=10)
        recent_error_count = len([e for e in self.errors if e.timestamp >= recent_time])
        
        if recent_error_count >= 10:
            self.logger.error(f"High error rate detected: {recent_error_count} errors in last 10 minutes")
    
    def _load_error_data(self) -> None:
        """Load error data from persistent storage."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Load errors (keep only recent ones)
                cutoff_time = datetime.now() - timedelta(days=7)
                for error_data in data.get('errors', []):
                    error_time = datetime.fromisoformat(error_data['timestamp'])
                    if error_time >= cutoff_time:
                        error_info = ErrorInfo(
                            error_id=error_data['error_id'],
                            timestamp=error_time,
                            category=ErrorCategory(error_data['category']),
                            severity=ErrorSeverity(error_data['severity']),
                            service=error_data['service'],
                            operation=error_data['operation'],
                            error_type=error_data['error_type'],
                            error_message=error_data['error_message'],
                            context=error_data.get('context', {}),
                            retry_count=error_data.get('retry_count', 0)
                        )
                        self.errors.append(error_info)
                
                # Load error counts
                self.error_counts = data.get('error_counts', {})
                
        except Exception as e:
            self.logger.warning(f"Failed to load error data: {e}")
    
    def _save_error_data(self) -> None:
        """Save error data to persistent storage."""
        try:
            # Ensure directory exists
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only recent errors (last 7 days)
            cutoff_time = datetime.now() - timedelta(days=7)
            recent_errors = [e for e in self.errors if e.timestamp >= cutoff_time]
            
            data = {
                'errors': [
                    {
                        'error_id': e.error_id,
                        'timestamp': e.timestamp.isoformat(),
                        'category': e.category.value,
                        'severity': e.severity.value,
                        'service': e.service,
                        'operation': e.operation,
                        'error_type': e.error_type,
                        'error_message': e.error_message,
                        'context': e.context,
                        'retry_count': e.retry_count
                    }
                    for e in recent_errors
                ],
                'error_counts': self.error_counts,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save error data: {e}")


# Global error handler instance
_global_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler


def handle_error(error: Exception,
                service: str,
                operation: str,
                context: Optional[Dict[str, Any]] = None,
                category: Optional[ErrorCategory] = None,
                severity: Optional[ErrorSeverity] = None) -> ErrorInfo:
    """Convenience function to handle errors using the global error handler."""
    return get_error_handler().handle_error(error, service, operation, context, category, severity)


def retry_with_backoff(category: ErrorCategory = ErrorCategory.UNKNOWN,
                      context: Optional[Dict[str, Any]] = None):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return get_error_handler().retry_with_backoff(
                func, *args, category=category, context=context, **kwargs
            )
        return wrapper
    return decorator