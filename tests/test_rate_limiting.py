"""
Unit tests for centralized rate limiting service.
"""

import time
import pytest
from tests.test_utilities import TestUtilities
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile

from utils.rate_limiting import (
    RateLimitingService, RateLimitConfig, RateLimitStatus, RateLimitStrategy,
    TokenBucket, SlidingWindowCounter, get_rate_limiter, wait_for_service, can_make_request
)
from utils.config import Config


class TestRateLimitConfig:
    """Test cases for RateLimitConfig dataclass."""
    
    def test_valid_config_creation(self):
        """Test creating valid rate limit configuration."""
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=60,
            requests_per_hour=3600,
            requests_per_day=86400,
            burst_limit=10,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            enabled=True
        )
        
        assert config.service_name == "test_service"
        assert config.operation == "test_operation"
        assert config.requests_per_minute == 60
        assert config.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert config.enabled is True
    
    def test_default_values(self):
        """Test default values in rate limit configuration."""
        config = RateLimitConfig(service_name="test_service")
        
        assert config.operation == "default"
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 3600
        assert config.requests_per_day == 86400
        assert config.burst_limit == 10
        assert config.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert config.enabled is True
    
    def test_invalid_config_validation(self):
        """Test validation of invalid configurations."""
        with pytest.raises(ValueError, match="requests_per_minute must be positive"):
            RateLimitConfig(service_name="test", requests_per_minute=0)
        
        with pytest.raises(ValueError, match="requests_per_hour must be positive"):
            RateLimitConfig(service_name="test", requests_per_hour=0)
        
        with pytest.raises(ValueError, match="requests_per_day must be positive"):
            RateLimitConfig(service_name="test", requests_per_day=0)
        
        with pytest.raises(ValueError, match="burst_limit must be positive"):
            RateLimitConfig(service_name="test", burst_limit=0)


class TestRateLimitStatus:
    """Test cases for RateLimitStatus dataclass."""
    
    def test_status_creation(self):
        """Test creating rate limit status."""
        status = RateLimitStatus(
            service_name="test_service",
            operation="test_operation",
            current_minute_count=5,
            current_hour_count=100,
            is_limited=True,
            remaining_requests=55
        )
        
        assert status.service_name == "test_service"
        assert status.operation == "test_operation"
        assert status.current_minute_count == 5
        assert status.current_hour_count == 100
        assert status.is_limited is True
        assert status.remaining_requests == 55
    
    def test_status_to_dict(self):
        """Test converting status to dictionary."""
        timestamp = datetime.now()
        status = RateLimitStatus(
            service_name="test_service",
            operation="test_operation",
            last_request_time=timestamp,
            is_limited=True
        )
        
        result_dict = status.to_dict()
        
        assert result_dict['service_name'] == "test_service"
        assert result_dict['operation'] == "test_operation"
        assert result_dict['last_request_time'] == timestamp.isoformat()
        assert result_dict['is_limited'] is True


class TestTokenBucket:
    """Test cases for TokenBucket implementation."""
    
    def test_token_bucket_creation(self):
        """Test creating token bucket."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10
    
    def test_token_consumption_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Should be able to consume tokens
        assert bucket.consume(5) is True
        assert bucket.tokens == 5
        
        # Should be able to consume remaining tokens
        assert bucket.consume(5) is True
        assert bucket.tokens < 0.1  # Allow for floating point precision
    
    def test_token_consumption_failure(self):
        """Test failed token consumption when not enough tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        # Consume all tokens
        bucket.consume(10)
        
        # Should fail to consume more tokens
        assert bucket.consume(1) is False
        assert bucket.tokens < 0.1  # Allow for floating point precision
    
    def test_token_refill(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        bucket.consume(10)
        assert bucket.tokens == 0
        
        # Wait for refill
        time.sleep(1.1)  # Wait slightly more than 1 second
        
        # Should have refilled some tokens
        assert bucket.consume(2) is True
    
    def test_get_wait_time(self):
        """Test calculating wait time for tokens."""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens per second
        
        # Consume all tokens
        bucket.consume(10)
        
        # Should need to wait for tokens
        wait_time = bucket.get_wait_time(4)
        assert wait_time == 2.0  # 4 tokens / 2 tokens per second
        
        # Should not need to wait if tokens available
        bucket.tokens = 5
        wait_time = bucket.get_wait_time(3)
        assert wait_time == 0.0
    
    def test_thread_safety(self):
        """Test thread safety of token bucket."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        results = []
        
        def consume_tokens():
            for _ in range(10):
                results.append(bucket.consume(1))
        
        # Start multiple threads
        threads = [threading.Thread(target=consume_tokens) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have consumed exactly 50 tokens (all successful)
        assert sum(results) == 50
        assert abs(bucket.tokens - 50) < 1  # Allow for floating point precision and timing


class TestSlidingWindowCounter:
    """Test cases for SlidingWindowCounter implementation."""
    
    def test_sliding_window_creation(self):
        """Test creating sliding window counter."""
        window = SlidingWindowCounter(window_size=60, max_requests=10)
        
        assert window.window_size == 60
        assert window.max_requests == 10
        assert len(window.requests) == 0
    
    def test_can_proceed_within_limit(self):
        """Test can_proceed when within limits."""
        window = SlidingWindowCounter(window_size=60, max_requests=5)
        
        # Should be able to proceed initially
        assert window.can_proceed() is True
        
        # Record some requests
        for _ in range(4):
            window.record_request()
        
        # Should still be able to proceed
        assert window.can_proceed() is True
    
    def test_can_proceed_at_limit(self):
        """Test can_proceed when at limit."""
        window = SlidingWindowCounter(window_size=60, max_requests=3)
        
        # Record requests up to limit
        for _ in range(3):
            window.record_request()
        
        # Should not be able to proceed
        assert window.can_proceed() is False
    
    def test_window_sliding(self):
        """Test that old requests are removed from window."""
        window = SlidingWindowCounter(window_size=1, max_requests=2)  # 1 second window
        
        # Record requests
        window.record_request()
        window.record_request()
        
        # Should be at limit
        assert window.can_proceed() is False
        
        # Wait for window to slide
        time.sleep(1.1)
        
        # Should be able to proceed again
        assert window.can_proceed() is True
    
    def test_get_wait_time(self):
        """Test calculating wait time for sliding window."""
        window = SlidingWindowCounter(window_size=2, max_requests=2)  # 2 second window
        
        # Should not need to wait initially
        assert window.get_wait_time() == 0.0
        
        # Record requests to fill window
        window.record_request()
        window.record_request()
        
        # Should need to wait
        wait_time = window.get_wait_time()
        assert wait_time > 0
        assert wait_time <= 2.0
    
    def test_thread_safety(self):
        """Test thread safety of sliding window counter."""
        window = SlidingWindowCounter(window_size=60, max_requests=50)
        results = []
        
        def check_and_record():
            for _ in range(10):
                if window.can_proceed():
                    window.record_request()
                    results.append(True)
                else:
                    results.append(False)
        
        # Start multiple threads
        threads = [threading.Thread(target=check_and_record) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have recorded exactly 50 requests (within limit)
        assert sum(results) == 50


class TestRateLimitingService:
    """Test cases for RateLimitingService class."""
    
    @pytest.fixture
    def rate_limiter(self, mock_config):
        """Create rate limiting service for testing."""
        with patch('utils.rate_limiting.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            return RateLimitingService(mock_config)
    
    def test_service_initialization(self, rate_limiter):
        """Test service initialization."""
        assert rate_limiter.config is not None
        assert rate_limiter.logger is not None
        assert len(rate_limiter.rate_limits) > 0
        assert len(rate_limiter.rate_limit_status) > 0
    
    def test_default_limits_initialization(self, rate_limiter):
        """Test that default rate limits are properly initialized."""
        # Check that expected services have rate limits
        expected_services = ["openai", "hunter", "linkedin", "producthunt", "notion", "resend"]
        
        for service in expected_services:
            # Find rate limit for this service
            service_limits = [key for key in rate_limiter.rate_limits.keys() if key.startswith(service)]
            assert len(service_limits) > 0, f"No rate limits found for {service}"
    
    def test_add_rate_limit(self, rate_limiter):
        """Test adding new rate limit."""
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=30,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        
        rate_limiter.add_rate_limit(config)
        
        key = "test_service.test_operation"
        assert key in rate_limiter.rate_limits
        assert key in rate_limiter.rate_limit_status
        assert key in rate_limiter.token_buckets
    
    def test_wait_for_service_no_limit(self, rate_limiter):
        """Test waiting for service with no rate limit configured."""
        # Should not wait for unknown service
        start_time = time.time()
        rate_limiter.wait_for_service("unknown_service", "unknown_operation")
        end_time = time.time()
        
        # Should return immediately
        assert end_time - start_time < 0.1
    
    def test_wait_for_service_with_limit(self, rate_limiter):
        """Test waiting for service with rate limit."""
        # Add a strict rate limit
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=1,  # Very low limit
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        rate_limiter.add_rate_limit(config)
        
        # First request should not wait
        start_time = time.time()
        rate_limiter.wait_for_service("test_service", "test_operation")
        first_duration = time.time() - start_time
        
        # Second request should wait
        start_time = time.time()
        rate_limiter.wait_for_service("test_service", "test_operation")
        second_duration = time.time() - start_time
        
        assert first_duration < 0.1
        assert second_duration > 0.5  # Should have waited
    
    def test_can_make_request(self, rate_limiter):
        """Test checking if request can be made."""
        # Add rate limit
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=2,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        rate_limiter.add_rate_limit(config)
        
        # Should be able to make requests initially
        assert rate_limiter.can_make_request("test_service", "test_operation") is True
        
        # Make requests to reach limit
        rate_limiter.wait_for_service("test_service", "test_operation")
        rate_limiter.wait_for_service("test_service", "test_operation")
        
        # Should not be able to make more requests
        assert rate_limiter.can_make_request("test_service", "test_operation") is False
    
    def test_get_wait_time(self, rate_limiter):
        """Test getting wait time for service."""
        # Add rate limit
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=1,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )
        rate_limiter.add_rate_limit(config)
        
        # Should not need to wait initially
        assert rate_limiter.get_wait_time("test_service", "test_operation") == 0.0
        
        # Make a request
        rate_limiter.wait_for_service("test_service", "test_operation")
        
        # Should need to wait for next request
        wait_time = rate_limiter.get_wait_time("test_service", "test_operation")
        assert wait_time > 0
    
    def test_get_status(self, rate_limiter):
        """Test getting rate limit status."""
        # Get all statuses
        all_status = rate_limiter.get_status()
        assert len(all_status) > 0
        
        # Get status for specific service
        hunter_status = rate_limiter.get_status("hunter")
        assert len(hunter_status) > 0
        
        # All returned statuses should be for hunter service
        for status in hunter_status.values():
            assert status.service_name == "hunter"
    
    def test_get_statistics(self, rate_limiter):
        """Test getting rate limiting statistics."""
        stats = rate_limiter.get_statistics()
        
        assert 'total_services' in stats
        assert 'total_rate_limits' in stats
        assert 'services' in stats
        assert 'strategies' in stats
        
        assert stats['total_services'] > 0
        assert stats['total_rate_limits'] > 0
        assert len(stats['services']) > 0
        assert len(stats['strategies']) > 0
    
    def test_update_rate_limit(self, rate_limiter):
        """Test updating existing rate limit."""
        # Add initial rate limit
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=30
        )
        rate_limiter.add_rate_limit(config)
        
        # Update the rate limit
        rate_limiter.update_rate_limit("test_service", "test_operation", requests_per_minute=60)
        
        # Verify update
        key = "test_service.test_operation"
        assert rate_limiter.rate_limits[key].requests_per_minute == 60
    
    def test_update_nonexistent_rate_limit(self, rate_limiter):
        """Test updating non-existent rate limit raises error."""
        with pytest.raises(ValueError, match="Rate limit .* does not exist"):
            rate_limiter.update_rate_limit("nonexistent", "operation", requests_per_minute=60)
    
    def test_disable_enable_rate_limit(self, rate_limiter):
        """Test disabling and enabling rate limits."""
        # Add rate limit
        config = RateLimitConfig(
            service_name="test_service",
            operation="test_operation",
            requests_per_minute=1
        )
        rate_limiter.add_rate_limit(config)
        
        # Disable rate limit
        rate_limiter.disable_rate_limit("test_service", "test_operation")
        
        # Should be able to make requests without waiting
        assert rate_limiter.can_make_request("test_service", "test_operation") is True
        
        # Enable rate limit
        rate_limiter.enable_rate_limit("test_service", "test_operation")
        
        # Should respect rate limit again
        rate_limiter.wait_for_service("test_service", "test_operation")
        # After one request, should need to wait for very low limit
        assert rate_limiter.can_make_request("test_service", "test_operation") is False
    
    def test_configuration_save_load(self, rate_limiter):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            # Set config path and save
            rate_limiter.config_path = config_path
            rate_limiter.save_configuration()
            
            # Verify file was created
            assert Path(config_path).exists()
            
            # Load configuration in new service
            new_service = RateLimitingService(rate_limiter.config, config_path)
            
            # Should have same number of rate limits
            assert len(new_service.rate_limits) >= len(rate_limiter.rate_limits)
            
        finally:
            # Clean up
            Path(config_path).unlink(missing_ok=True)


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    def test_get_rate_limiter_singleton(self):
        """Test that get_rate_limiter returns singleton instance."""
        # Reset global instance
        import utils.rate_limiting
        utils.rate_limiting._global_rate_limiter = None
        
        config = Mock(spec=Config)
        config.hunter_requests_per_minute = 10
        config.scraping_delay = 2.0
        config.resend_requests_per_minute = 100
        
        with patch('utils.rate_limiting.get_logger'):
            limiter1 = get_rate_limiter(config)
            limiter2 = get_rate_limiter()
            
            # Should return same instance
            assert limiter1 is limiter2
    
    def test_get_rate_limiter_no_config_error(self):
        """Test that get_rate_limiter raises error when no config provided initially."""
        # Reset global instance
        import utils.rate_limiting
        utils.rate_limiting._global_rate_limiter = None
        
        with pytest.raises(ValueError, match="Config must be provided for first initialization"):
            get_rate_limiter()
    
    def test_wait_for_service_global(self):
        """Test global wait_for_service function."""
        config = Mock(spec=Config)
        config.hunter_requests_per_minute = 10
        config.scraping_delay = 2.0
        
        with patch('utils.rate_limiting.get_logger'):
            with patch('utils.rate_limiting.get_rate_limiter') as mock_get:
                mock_limiter = Mock()
                mock_get.return_value = mock_limiter
                
                wait_for_service("test_service", "test_operation", config)
                
                mock_limiter.wait_for_service.assert_called_once_with("test_service", "test_operation")
    
    def test_can_make_request_global(self):
        """Test global can_make_request function."""
        config = Mock(spec=Config)
        
        with patch('utils.rate_limiting.get_rate_limiter') as mock_get:
            mock_limiter = Mock()
            mock_limiter.can_make_request.return_value = True
            mock_get.return_value = mock_limiter
            
            result = can_make_request("test_service", "test_operation", config)
            
            assert result is True
            mock_limiter.can_make_request.assert_called_once_with("test_service", "test_operation")


class TestRateLimitStrategies:
    """Test cases for different rate limiting strategies."""
    
    @pytest.fixture
    # Using shared mock_config fixture from conftest.py
    def test_token_bucket_strategy(self, mock_config):
        """Test token bucket rate limiting strategy."""
        with patch('utils.rate_limiting.get_logger'):
            rate_limiter = RateLimitingService(mock_config)
            
            # Add token bucket rate limit
            config = RateLimitConfig(
                service_name="test_service",
                operation="test_operation",
                requests_per_minute=60,
                burst_limit=5,
                strategy=RateLimitStrategy.TOKEN_BUCKET
            )
            rate_limiter.add_rate_limit(config)
            
            # Should be able to make burst requests quickly
            for _ in range(5):
                assert rate_limiter.can_make_request("test_service", "test_operation") is True
                rate_limiter.wait_for_service("test_service", "test_operation")
            
            # Should need to wait after burst
            assert rate_limiter.can_make_request("test_service", "test_operation") is False
    
    def test_sliding_window_strategy(self, mock_config):
        """Test sliding window rate limiting strategy."""
        with patch('utils.rate_limiting.get_logger'):
            rate_limiter = RateLimitingService(mock_config)
            
            # Add sliding window rate limit
            config = RateLimitConfig(
                service_name="test_service",
                operation="test_operation",
                requests_per_minute=2,  # Very low for testing
                strategy=RateLimitStrategy.SLIDING_WINDOW
            )
            rate_limiter.add_rate_limit(config)
            
            # Should be able to make initial requests
            assert rate_limiter.can_make_request("test_service", "test_operation") is True
            rate_limiter.wait_for_service("test_service", "test_operation")
            
            assert rate_limiter.can_make_request("test_service", "test_operation") is True
            rate_limiter.wait_for_service("test_service", "test_operation")
            
            # Should need to wait after reaching limit
            assert rate_limiter.can_make_request("test_service", "test_operation") is False


if __name__ == "__main__":
    pytest.main([__file__])