"""
Centralized rate limiting service for managing API call rates across all services.

This module provides a unified rate limiting system that consolidates rate limiting
logic from multiple services and implements service-specific rate limits with
configuration support.
"""

import time
import threading
from typing import (
    Dict,
    Optional,
    Any,
    List
)
from dataclasses import (
    dataclass,
    field
)
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

from utils.config import Config
from utils.logging_config import get_logger




class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for a specific rate limit."""
    service_name: str
    operation: str = "default"
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    requests_per_day: int = 86400
    burst_limit: int = 10
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    enabled: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.requests_per_hour <= 0:
            raise ValueError("requests_per_hour must be positive")
        if self.requests_per_day <= 0:
            raise ValueError("requests_per_day must be positive")
        if self.burst_limit <= 0:
            raise ValueError("burst_limit must be positive")


@dataclass
class RateLimitStatus:
    """Current status of a rate limit."""
    service_name: str
    operation: str
    current_minute_count: int = 0
    current_hour_count: int = 0
    current_day_count: int = 0
    last_request_time: Optional[datetime] = None
    next_available_time: Optional[datetime] = None
    is_limited: bool = False
    remaining_requests: int = 0
    reset_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary."""
        return {
            'service_name': self.service_name,
            'operation': self.operation,
            'current_minute_count': self.current_minute_count,
            'current_hour_count': self.current_hour_count,
            'current_day_count': self.current_day_count,
            'last_request_time': self.last_request_time.isoformat() if self.last_request_time else None,
            'next_available_time': self.next_available_time.isoformat() if self.next_available_time else None,
            'is_limited': self.is_limited,
            'remaining_requests': self.remaining_requests,
            'reset_time': self.reset_time.isoformat() if self.reset_time else None
        }


class TokenBucket:
    """Token bucket implementation for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens
        """
        with self._lock:
            now = time.time()
            
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Wait time in seconds
        """
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate


class SlidingWindowCounter:
    """Sliding window counter for rate limiting."""
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Initialize sliding window counter.
        
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests in window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests: List[float] = []
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    def can_proceed(self) -> bool:
        """
        Check if request can proceed.
        
        Returns:
            True if request can proceed, False otherwise
        """
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            cutoff_time = now - self.window_size
            self.requests = [req_time for req_time in self.requests if req_time > cutoff_time]
            
            result = len(self.requests) < self.max_requests
            self.logger.info(f"SlidingWindowCounter.can_proceed: {result}, requests={len(self.requests)}, max={self.max_requests}, cutoff_time={cutoff_time:.2f}")
            return result
    
    def record_request(self) -> None:
        """Record a new request."""
        with self._lock:
            now = time.time()
            # Remove old requests outside the window before adding new one
            cutoff_time = now - self.window_size
            self.requests = [req_time for req_time in self.requests if req_time > cutoff_time]
            self.requests.append(now)
            self.logger.info(f"SlidingWindowCounter.record_request: requests={len(self.requests)}, times={[f'{req-now:.2f}' for req in self.requests]}")
    
    def get_wait_time(self) -> float:
        """
        Get time to wait until next request can proceed.
        
        Returns:
            Wait time in seconds
        """
        with self._lock:
            now = time.time()
            
            # Remove old requests outside the window
            cutoff_time = now - self.window_size
            self.requests = [req_time for req_time in self.requests if req_time > cutoff_time]
            
            if len(self.requests) < self.max_requests:
                self.logger.info(f"SlidingWindowCounter.get_wait_time: 0.0, requests={len(self.requests)}, max={self.max_requests}")
                return 0.0
            
            # Find the oldest request that needs to expire
            if self.requests:
                oldest_request = min(self.requests)
                wait_time = (oldest_request + self.window_size) - now
                self.logger.info(f"SlidingWindowCounter.get_wait_time: {wait_time:.2f}, requests={len(self.requests)}, max={self.max_requests}, oldest={oldest_request:.2f}, now={now:.2f}")
                return max(0.0, wait_time)
            self.logger.info(f"SlidingWindowCounter.get_wait_time: 0.0 (no requests)")
            return 0.0


class RateLimitingService:
    """
    Centralized rate limiting service for all external API calls.
    
    Features:
    - Service-specific rate limits
    - Multiple rate limiting strategies
    - Burst handling
    - Rate limit monitoring and reporting
    - Configuration-driven limits
    - Thread-safe operations
    """
    
    def __init__(self, config: Config, config_path: Optional[str] = None):
        """
        Initialize rate limiting service.
        
        Args:
            config: Global configuration object
            config_path: Optional path to rate limit configuration file
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.config_path = config_path or "logs/rate_limiting.json"
        
        # Rate limit configurations
        self.rate_limits: Dict[str, RateLimitConfig] = {}
        self.rate_limit_status: Dict[str, RateLimitStatus] = {}
        
        # Rate limiting implementations
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.sliding_windows: Dict[str, SlidingWindowCounter] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Initialize default rate limits
        self._initialize_default_limits()
        
        # Load custom configuration if available
        self._load_configuration()
        
        self.logger.info("Rate limiting service initialized")
    
    def _initialize_default_limits(self) -> None:
        """Initialize default rate limits based on global configuration."""
        # OpenAI rate limits - increased for better performance
        openai_rpm = 120  # Increased from 60 to 120
        if hasattr(self.config, 'openai_requests_per_minute'):
            openai_rpm = self.config.openai_requests_per_minute
        
        self.add_rate_limit(RateLimitConfig(
            service_name="openai",
            operation="completion",
            requests_per_minute=openai_rpm,
            requests_per_hour=openai_rpm * 60,
            burst_limit=5,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ))
        
        # Hunter.io rate limits - using safer default
        hunter_rpm = getattr(self.config, 'hunter_requests_per_minute', 10)  # Safer default of 10
        # Add rate limits for both domain search and email finder endpoints
        self.add_rate_limit(RateLimitConfig(
            service_name="hunter",
            operation="domain-search",  # Match the actual API endpoint
            requests_per_minute=hunter_rpm,
            requests_per_hour=hunter_rpm * 60,
            burst_limit=3,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        self.add_rate_limit(RateLimitConfig(
            service_name="hunter",
            operation="email-finder",  # Match the actual API endpoint
            requests_per_minute=hunter_rpm,
            requests_per_hour=hunter_rpm * 60,
            burst_limit=3,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        self.add_rate_limit(RateLimitConfig(
            service_name="hunter",
            operation="email-verifier",  # Match the actual API endpoint
            requests_per_minute=hunter_rpm,
            requests_per_hour=hunter_rpm * 60,
            burst_limit=3,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        # LinkedIn scraping rate limits
        linkedin_delay = getattr(self.config, 'scraping_delay', 2.0)
        linkedin_rpm = int(60 / linkedin_delay) if linkedin_delay > 0 else 30
        self.add_rate_limit(RateLimitConfig(
            service_name="linkedin",
            operation="scraping",
            requests_per_minute=linkedin_rpm,
            requests_per_hour=linkedin_rpm * 60,
            burst_limit=2,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        # ProductHunt scraping rate limits
        scraping_delay = getattr(self.config, 'scraping_delay', 2.0)
        scraping_rpm = int(60 / scraping_delay) if scraping_delay > 0 else 30
        self.add_rate_limit(RateLimitConfig(
            service_name="producthunt",
            operation="scraping",
            requests_per_minute=scraping_rpm,
            requests_per_hour=scraping_rpm * 60,
            burst_limit=2,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        ))
        
        # Notion API rate limits
        self.add_rate_limit(RateLimitConfig(
            service_name="notion",
            operation="api_call",
            requests_per_minute=100,  # Notion's limit is quite high
            requests_per_hour=6000,
            burst_limit=10,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ))
        
        # Resend API rate limits
        resend_rpm = getattr(self.config, 'resend_requests_per_minute', 100)
        self.add_rate_limit(RateLimitConfig(
            service_name="resend",
            operation="email_send",
            requests_per_minute=resend_rpm,
            requests_per_hour=resend_rpm * 60,
            burst_limit=5,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        ))
    
    def add_rate_limit(self, rate_limit_config: RateLimitConfig) -> None:
        """
        Add a new rate limit configuration.
        
        Args:
            rate_limit_config: Rate limit configuration
        """
        key = f"{rate_limit_config.service_name}.{rate_limit_config.operation}"
        
        with self._lock:
            self.rate_limits[key] = rate_limit_config
            self.rate_limit_status[key] = RateLimitStatus(
                service_name=rate_limit_config.service_name,
                operation=rate_limit_config.operation,
                remaining_requests=rate_limit_config.requests_per_minute
            )
            
            # Initialize rate limiting implementation
            if rate_limit_config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                self.token_buckets[key] = TokenBucket(
                    capacity=rate_limit_config.burst_limit,
                    refill_rate=rate_limit_config.requests_per_minute / 60.0
                )
            elif rate_limit_config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                window = SlidingWindowCounter(
                    window_size=60,  # 1 minute window
                    max_requests=rate_limit_config.requests_per_minute
                )
                self.sliding_windows[key] = window
                self.logger.info(f"Initialized sliding window for {key}: max_requests={window.max_requests}")
        
        self.logger.info(f"Added rate limit for {key}: {rate_limit_config.requests_per_minute} RPM")
    
    def wait_for_service(self, service_name: str, operation: str = "default") -> None:
        """
        Wait for rate limit if necessary before making a request.
        
        Args:
            service_name: Name of the service
            operation: Operation name
        """
        key = f"{service_name}.{operation}"
        
        self.logger.info(f"wait_for_service called for {key}")
        
        # Check if rate limit exists
        if key not in self.rate_limits:
            self.logger.debug(f"No rate limit configured for {key}")
            return
        
        rate_limit = self.rate_limits[key]
        
        # Skip if rate limiting is disabled
        if not rate_limit.enabled:
            self.logger.debug(f"Rate limiting disabled for {key}")
            return
        
        # Check if we can proceed immediately
        can_proceed = self.can_make_request(service_name, operation)
        self.logger.info(f"Can proceed immediately for {key}: {can_proceed}")
        
        if can_proceed:
            # Record the request immediately
            self._record_request(key)
            self.logger.info(f"Request recorded immediately for {key}")
            return
        
        # If we can't proceed, wait until we can
        wait_time = self._get_wait_time(key)
        
        self.logger.info(f"Rate limit check for {key}: wait_time={wait_time:.2f}s, RPM={rate_limit.requests_per_minute}")
        
        if wait_time > 0:
            self.logger.info(f"Rate limiting {key}: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        # Record the request after waiting
        self._record_request(key)
        self.logger.info(f"Request recorded for {key} after waiting")
    
    def _get_wait_time(self, key: str) -> float:
        """
        Get wait time for a specific rate limit key.
        
        Args:
            key: Rate limit key
            
        Returns:
            Wait time in seconds
        """
        if key not in self.rate_limits:
            self.logger.debug(f"_get_wait_time: No rate limit for {key}")
            return 0.0
        
        rate_limit = self.rate_limits[key]
        self.logger.debug(f"_get_wait_time: {key} strategy={rate_limit.strategy.value}")
        
        if rate_limit.strategy == RateLimitStrategy.TOKEN_BUCKET:
            bucket = self.token_buckets.get(key)
            wait_time = bucket.get_wait_time() if bucket else 0.0
            self.logger.debug(f"_get_wait_time: token bucket wait_time={wait_time:.2f}")
            return wait_time
        
        elif rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
            window = self.sliding_windows.get(key)
            wait_time = window.get_wait_time() if window else 0.0
            self.logger.debug(f"_get_wait_time: sliding window wait_time={wait_time:.2f}")
            return wait_time
        
        self.logger.debug(f"_get_wait_time: default 0.0")
        return 0.0
    
    def can_make_request(self, service_name: str, operation: str = "default") -> bool:
        """
        Check if a request can be made without waiting.
        
        Args:
            service_name: Name of the service
            operation: Operation name
            
        Returns:
            True if request can be made immediately, False otherwise
        """
        key = f"{service_name}.{operation}"
        
        if key not in self.rate_limits:
            self.logger.debug(f"can_make_request: No rate limit for {key}, allowing request")
            return True
        
        if not self.rate_limits[key].enabled:
            self.logger.debug(f"can_make_request: Rate limit disabled for {key}, allowing request")
            return True
        
        # Check if the sliding window allows immediate execution
        window_result = self.sliding_windows.get(key, SlidingWindowCounter(60, 1000)).can_proceed()
        self.logger.debug(f"can_make_request: {key} sliding window result={window_result}")
        return window_result
    
    def get_wait_time(self, service_name: str, operation: str = "default") -> float:
        """
        Get the wait time before next request can be made.
        
        Args:
            service_name: Name of the service
            operation: Operation name
            
        Returns:
            Wait time in seconds
        """
        key = f"{service_name}.{operation}"
        return self._get_wait_time(key)
    
    def _record_request(self, key: str) -> None:
        """
        Record a request for rate limiting purposes.
        
        Args:
            key: Rate limit key
        """
        if key not in self.rate_limits:
            return
        
        rate_limit = self.rate_limits[key]
        status = self.rate_limit_status[key]
        
        now = datetime.now()
        
        with self._lock:
            # Update status
            status.last_request_time = now
            status.current_minute_count += 1
            status.current_hour_count += 1
            status.current_day_count += 1
            
            # Record in appropriate rate limiter
            if rate_limit.strategy == RateLimitStrategy.TOKEN_BUCKET:
                bucket = self.token_buckets.get(key)
                if bucket:
                    bucket.consume()
            
            elif rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
                window = self.sliding_windows.get(key)
                if window:
                    window.record_request()
        
        # Reset counters if needed
        self._reset_counters_if_needed(key, now)
    
    def _reset_counters_if_needed(self, key: str, now: datetime) -> None:
        """
        Reset counters if time windows have passed.
        
        Args:
            key: Rate limit key
            now: Current datetime
        """
        status = self.rate_limit_status[key]
        
        if not status.last_request_time:
            return
        
        # Reset minute counter
        if (now - status.last_request_time).total_seconds() >= 60:
            status.current_minute_count = 0
        
        # Reset hour counter
        if (now - status.last_request_time).total_seconds() >= 3600:
            status.current_hour_count = 0
        
        # Reset day counter
        if (now - status.last_request_time).total_seconds() >= 86400:
            status.current_day_count = 0
    
    def get_status(self, service_name: Optional[str] = None) -> Dict[str, RateLimitStatus]:
        """
        Get rate limiting status for services.
        
        Args:
            service_name: Optional service name to filter by
            
        Returns:
            Dictionary of rate limit statuses
        """
        with self._lock:
            if service_name:
                return {
                    k: v for k, v in self.rate_limit_status.items()
                    if v.service_name == service_name
                }
            return self.rate_limit_status.copy()
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive rate limiting statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_services': len(set(rl.service_name for rl in self.rate_limits.values())),
            'total_rate_limits': len(self.rate_limits),
            'services': {},
            'strategies': {}
        }
        
        # Service-specific stats
        for key, status in self.rate_limit_status.items():
            service = status.service_name
            if service not in stats['services']:
                stats['services'][service] = {
                    'operations': 0,
                    'total_requests_minute': 0,
                    'total_requests_hour': 0,
                    'total_requests_day': 0
                }
            
            stats['services'][service]['operations'] += 1
            stats['services'][service]['total_requests_minute'] += status.current_minute_count
            stats['services'][service]['total_requests_hour'] += status.current_hour_count
            stats['services'][service]['total_requests_day'] += status.current_day_count
        
        # Strategy stats
        for rate_limit in self.rate_limits.values():
            strategy = rate_limit.strategy.value
            if strategy not in stats['strategies']:
                stats['strategies'][strategy] = 0
            stats['strategies'][strategy] += 1
        
        return stats
    
    def update_rate_limit(self, service_name: str, operation: str, **kwargs) -> None:
        """
        Update an existing rate limit configuration.
        
        Args:
            service_name: Service name
            operation: Operation name
            **kwargs: Configuration parameters to update
        """
        key = f"{service_name}.{operation}"
        
        if key not in self.rate_limits:
            raise ValueError(f"Rate limit {key} does not exist")
        
        with self._lock:
            rate_limit = self.rate_limits[key]
            
            # Update configuration
            for attr, value in kwargs.items():
                if hasattr(rate_limit, attr):
                    setattr(rate_limit, attr, value)
            
            # Reinitialize rate limiter if strategy changed
            if 'strategy' in kwargs or 'requests_per_minute' in kwargs or 'burst_limit' in kwargs:
                if rate_limit.strategy == RateLimitStrategy.TOKEN_BUCKET:
                    self.token_buckets[key] = TokenBucket(
                        capacity=rate_limit.burst_limit,
                        refill_rate=rate_limit.requests_per_minute / 60.0
                    )
                elif rate_limit.strategy == RateLimitStrategy.SLIDING_WINDOW:
                    self.sliding_windows[key] = SlidingWindowCounter(
                        window_size=60,
                        max_requests=rate_limit.requests_per_minute
                    )
        
        self.logger.info(f"Updated rate limit for {key}")
    
    def disable_rate_limit(self, service_name: str, operation: str = "default") -> None:
        """
        Disable rate limiting for a service/operation.
        
        Args:
            service_name: Service name
            operation: Operation name
        """
        key = f"{service_name}.{operation}"
        
        if key in self.rate_limits:
            self.rate_limits[key].enabled = False
            self.logger.info(f"Disabled rate limiting for {key}")
    
    def enable_rate_limit(self, service_name: str, operation: str = "default") -> None:
        """
        Enable rate limiting for a service/operation.
        
        Args:
            service_name: Service name
            operation: Operation name
        """
        key = f"{service_name}.{operation}"
        
        if key in self.rate_limits:
            self.rate_limits[key].enabled = True
            self.logger.info(f"Enabled rate limiting for {key}")
    
    def _load_configuration(self) -> None:
        """Load rate limiting configuration from file."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                for key, config_data in data.get('rate_limits', {}).items():
                    service_name, operation = key.split('.', 1)
                    rate_limit_config = RateLimitConfig(
                        service_name=service_name,
                        operation=operation,
                        requests_per_minute=config_data.get('requests_per_minute', 60),
                        requests_per_hour=config_data.get('requests_per_hour', 3600),
                        requests_per_day=config_data.get('requests_per_day', 86400),
                        burst_limit=config_data.get('burst_limit', 10),
                        strategy=RateLimitStrategy(config_data.get('strategy', 'sliding_window')),
                        enabled=config_data.get('enabled', True)
                    )
                    self.add_rate_limit(rate_limit_config)
                
                self.logger.info(f"Loaded rate limiting configuration from {self.config_path}")
                
        except Exception as e:
            self.logger.warning(f"Failed to load rate limiting configuration: {e}")
    
    def save_configuration(self) -> None:
        """Save current rate limiting configuration to file."""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'rate_limits': {},
                'last_updated': datetime.now().isoformat()
            }
            
            for key, rate_limit in self.rate_limits.items():
                data['rate_limits'][key] = {
                    'requests_per_minute': rate_limit.requests_per_minute,
                    'requests_per_hour': rate_limit.requests_per_hour,
                    'requests_per_day': rate_limit.requests_per_day,
                    'burst_limit': rate_limit.burst_limit,
                    'strategy': rate_limit.strategy.value,
                    'enabled': rate_limit.enabled
                }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info(f"Saved rate limiting configuration to {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save rate limiting configuration: {e}")


# Global rate limiting service instance
_global_rate_limiter = None


def get_rate_limiter(config: Optional[Config] = None) -> RateLimitingService:
    """Get the global rate limiting service instance."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        if config is None:
            raise ValueError("Config must be provided for first initialization")
        _global_rate_limiter = RateLimitingService(config)
    return _global_rate_limiter


def wait_for_service(service_name: str, operation: str = "default", config: Optional[Config] = None) -> None:
    """Convenience function to wait for service rate limit."""
    rate_limiter = get_rate_limiter(config)
    rate_limiter.wait_for_service(service_name, operation)


def can_make_request(service_name: str, operation: str = "default", config: Optional[Config] = None) -> bool:
    """Convenience function to check if request can be made."""
    rate_limiter = get_rate_limiter(config)
    return rate_limiter.can_make_request(service_name, operation)
