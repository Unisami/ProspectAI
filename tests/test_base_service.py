"""
Unit tests for BaseService class and common utilities.
"""

import time
import pytest
from tests.test_utilities import TestUtilities
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from utils.base_service import BaseService, ServiceConfig, service_operation
from utils.config import Config
from utils.error_handling import ErrorCategory


class MockService(BaseService):
    """Test service implementation for testing BaseService functionality."""
    
    def _initialize_service(self) -> None:
        """Initialize test service."""
        self.initialized = True
    
    def _perform_health_check(self) -> bool:
        """Test health check implementation."""
        return hasattr(self, 'initialized') and self.initialized
    
    def test_operation(self, data: str) -> str:
        """Test operation for testing."""
        self._validate_input(data, "test_operation")
        return f"processed: {data}"
    
    @service_operation("decorated_operation", ErrorCategory.NETWORK)
    def decorated_test_operation(self, data: str) -> str:
        """Test operation with decorator."""
        return f"decorated: {data}"
    
    def failing_operation(self) -> None:
        """Operation that always fails for testing error handling."""
        raise ValueError("Test error")


class TestBaseService:
    """Test cases for BaseService class."""
    
    @pytest.fixture
    def service_config(self):
        """Create test service configuration."""
        return ServiceConfig(
            name="MockService",
            rate_limit_delay=0.1,  # Short delay for testing
            max_retries=2,
            timeout=5
        )
    
    @pytest.fixture
    def test_service(self, mock_config, service_config):
        """Create test service instance."""
        with patch('utils.base_service.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            service = MockService(mock_config, service_config)
            return service
    
    def test_service_initialization(self, mock_config, service_config):
        """Test service initialization."""
        with patch('utils.base_service.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            
            service = MockService(mock_config, service_config)
            
            assert service.config == mock_config
            assert service.service_config == service_config
            assert hasattr(service, 'error_handler')
            assert hasattr(service, 'logger')
            assert service.initialized is True
            
            # Check that logger was called
            mock_logger.assert_called_once_with('MockService')
    
    def test_default_service_config(self, mock_config):
        """Test service initialization with default config."""
        with patch('utils.base_service.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            
            service = MockService(mock_config)
            
            assert service.service_config.name == "MockService"
            assert service.service_config.rate_limit_delay == 1.0
            assert service.service_config.max_retries == 3
    
    def test_rate_limiting(self, test_service):
        """Test rate limiting functionality."""
        # First call should not be delayed
        start_time = time.time()
        test_service._apply_rate_limit("test_op")
        first_duration = time.time() - start_time
        
        # Second call should be delayed
        start_time = time.time()
        test_service._apply_rate_limit("test_op")
        second_duration = time.time() - start_time
        
        # Second call should take longer due to rate limiting
        assert second_duration >= test_service.service_config.rate_limit_delay
        assert second_duration > first_duration
    
    def test_operation_tracking(self, test_service):
        """Test operation performance tracking."""
        # Perform some operations
        test_service._track_operation("test_op", 1.5)
        test_service._track_operation("test_op", 2.0)
        test_service._track_operation("other_op", 0.5)
        
        metrics = test_service.get_performance_metrics()
        
        assert metrics['service_name'] == 'MockService'
        assert metrics['total_operations'] == 3
        assert 'test_op' in metrics['operations']
        assert 'other_op' in metrics['operations']
        
        test_op_metrics = metrics['operations']['test_op']
        assert test_op_metrics['count'] == 2
        assert test_op_metrics['total_time'] == 3.5
        assert test_op_metrics['average_time'] == 1.75
    
    def test_slow_operation_warning(self, test_service):
        """Test warning for slow operations."""
        with patch.object(test_service.logger, 'warning') as mock_warning:
            # Track a slow operation (>10 seconds)
            test_service._track_operation("slow_op", 15.0)
            
            # Should log a warning
            mock_warning.assert_called_once()
            warning_call = mock_warning.call_args[0][0]
            assert "Slow operation detected" in warning_call
            assert "slow_op" in warning_call
    
    def test_api_call_success(self, test_service):
        """Test successful API call."""
        mock_func = Mock(return_value="success")
        
        result = test_service._make_api_call(
            mock_func, 
            "arg1", 
            "arg2", 
            operation="test_api",
            kwarg1="value1"
        )
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        
        # Check that operation was tracked
        metrics = test_service.get_performance_metrics()
        assert "test_api" in metrics['operations']
    
    def test_api_call_with_error_handling(self, test_service):
        """Test API call with error handling and retry."""
        mock_func = Mock(side_effect=[ValueError("Test error"), "success"])
        
        with patch.object(test_service.error_handler, 'retry_with_backoff') as mock_retry:
            mock_retry.return_value = "success"
            
            result = test_service._make_api_call(mock_func, operation="test_api")
            
            assert result == "success"
            mock_retry.assert_called_once()
    
    def test_input_validation(self, test_service):
        """Test input validation."""
        # Valid input should not raise
        test_service._validate_input("valid_data", "test_op")
        
        # None input should raise ValueError
        with pytest.raises(ValueError, match="Input data cannot be None"):
            test_service._validate_input(None, "test_op")
    
    def test_health_check_healthy(self, test_service):
        """Test health check when service is healthy."""
        health = test_service.health_check()
        
        assert health['service'] == 'MockService'
        assert health['status'] == 'healthy'
        assert 'timestamp' in health
        assert 'metrics' in health
    
    def test_health_check_unhealthy(self, test_service):
        """Test health check when service is unhealthy."""
        # Make service unhealthy
        test_service.initialized = False
        
        health = test_service.health_check()
        
        assert health['service'] == 'MockService'
        assert health['status'] == 'unhealthy'
    
    def test_health_check_with_exception(self, test_service):
        """Test health check when exception occurs."""
        with patch.object(test_service, '_perform_health_check', side_effect=Exception("Health check error")):
            health = test_service.health_check()
            
            assert health['service'] == 'MockService'
            assert health['status'] == 'unhealthy'
            assert 'error' in health
            assert health['error'] == "Health check error"
    
    def test_metrics_reset(self, test_service):
        """Test metrics reset functionality."""
        # Add some metrics
        test_service._track_operation("test_op", 1.0)
        test_service._apply_rate_limit("test_op")
        
        # Verify metrics exist
        metrics = test_service.get_performance_metrics()
        assert metrics['total_operations'] > 0
        
        # Reset metrics
        test_service.reset_metrics()
        
        # Verify metrics are cleared
        metrics = test_service.get_performance_metrics()
        assert metrics['total_operations'] == 0
        assert len(metrics['operations']) == 0
    
    def test_shutdown(self, test_service):
        """Test service shutdown."""
        # Add some operations for metrics
        test_service._track_operation("test_op", 1.0)
        
        with patch.object(test_service, '_cleanup') as mock_cleanup:
            test_service.shutdown()
            
            # Should call cleanup
            mock_cleanup.assert_called_once()
            
            # Should log shutdown message
            test_service.logger.info.assert_called()


class TestServiceOperationDecorator:
    """Test cases for service_operation decorator."""
    
    @pytest.fixture
    def test_service(self):
        """Create test service for decorator testing."""
        config = Mock(spec=Config)
        service_config = ServiceConfig(name="MockService", rate_limit_delay=0.1)
        
        with patch('utils.base_service.get_logger') as mock_logger:
            mock_logger.return_value = Mock()
            return MockService(config, service_config)
    
    def test_decorator_success(self, test_service):
        """Test successful operation with decorator."""
        result = test_service.decorated_test_operation("test_data")
        
        assert result == "decorated: test_data"
        
        # Check that operation was tracked
        metrics = test_service.get_performance_metrics()
        assert "decorated_operation" in metrics['operations']
    
    def test_decorator_with_error(self, test_service):
        """Test operation with decorator when error occurs."""
        # Create a method that will fail
        @service_operation("failing_op", ErrorCategory.NETWORK)
        def failing_method(self):
            raise ValueError("Test error")
        
        # Bind method to service instance
        failing_method.__get__(test_service, MockService)
        
        with patch.object(test_service.error_handler, 'handle_error') as mock_handle:
            with pytest.raises(ValueError):
                failing_method(test_service)
            
            # Should handle the error
            mock_handle.assert_called_once()
    
    def test_decorator_on_non_service_class(self):
        """Test decorator raises error when used on non-BaseService class."""
        class NonService:
            @service_operation("test_op")
            def test_method(self):
                return "test"
        
        non_service = NonService()
        
        with pytest.raises(TypeError, match="service_operation decorator can only be used on BaseService methods"):
            non_service.test_method()


class TestRetryDecorators:
    """Test cases for retry decorators."""
    
    def test_retry_on_network_error(self):
        """Test retry_on_network_error decorator."""
        from utils.base_service import retry_on_network_error
        
        call_count = 0
        
        @retry_on_network_error
        def network_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        with patch('utils.base_service.get_error_handler') as mock_get_handler:
            mock_handler = Mock()
            mock_handler.retry_with_backoff.return_value = "success"
            mock_get_handler.return_value = mock_handler
            
            result = network_operation()
            assert result == "success"
    
    def test_retry_on_rate_limit(self):
        """Test retry_on_rate_limit decorator."""
        from utils.base_service import retry_on_rate_limit
        
        @retry_on_rate_limit
        def rate_limited_operation():
            return "success"
        
        with patch('utils.base_service.get_error_handler') as mock_get_handler:
            mock_handler = Mock()
            mock_handler.retry_with_backoff.return_value = "success"
            mock_get_handler.return_value = mock_handler
            
            result = rate_limited_operation()
            assert result == "success"


class TestServiceConfig:
    """Test cases for ServiceConfig dataclass."""
    
    def test_default_values(self):
        """Test ServiceConfig default values."""
        config = ServiceConfig(name="MockService")
        
        assert config.name == "MockService"
        assert config.rate_limit_delay == 1.0
        assert config.max_retries == 3
        assert config.timeout == 30
        assert config.enable_caching is False
        assert config.cache_ttl == 3600
    
    def test_custom_values(self):
        """Test ServiceConfig with custom values."""
        config = ServiceConfig(
            name="CustomService",
            rate_limit_delay=2.5,
            max_retries=5,
            timeout=60,
            enable_caching=True,
            cache_ttl=7200
        )
        
        assert config.name == "CustomService"
        assert config.rate_limit_delay == 2.5
        assert config.max_retries == 5
        assert config.timeout == 60
        assert config.enable_caching is True
        assert config.cache_ttl == 7200


if __name__ == "__main__":
    pytest.main([__file__])