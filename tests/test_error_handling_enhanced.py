"""
Unit tests for enhanced error handling framework.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Any

from utils.error_handling_enhanced import (
    ErrorHandlingService, ErrorResponse, ErrorPattern, RecoveryStrategy,
    get_enhanced_error_handler, handle_error_enhanced, execute_with_recovery
)
from utils.error_handling import ErrorCategory, ErrorSeverity


class TestErrorResponse:
    """Test cases for ErrorResponse dataclass."""
    
    def test_error_response_creation(self):
        """Test ErrorResponse creation with all fields."""
        response = ErrorResponse(
            error_id="test_error_123",
            timestamp=datetime.now(),
            service="test_service",
            operation="test_operation",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            technical_details="Technical details here",
            should_retry=True,
            retry_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            retry_delay=2.0,
            max_retries=3,
            fallback_available=True,
            user_message="User-friendly message",
            suggested_actions=["Action 1", "Action 2"]
        )
        
        assert response.error_id == "test_error_123"
        assert response.service == "test_service"
        assert response.operation == "test_operation"
        assert response.category == ErrorCategory.NETWORK
        assert response.severity == ErrorSeverity.MEDIUM
        assert response.should_retry is True
        assert response.retry_strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert response.fallback_available is True
        assert len(response.suggested_actions) == 2
    
    def test_error_response_to_dict(self):
        """Test ErrorResponse conversion to dictionary."""
        timestamp = datetime.now()
        response = ErrorResponse(
            error_id="test_error_123",
            timestamp=timestamp,
            service="test_service",
            operation="test_operation",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Test error message",
            technical_details="Technical details",
            should_retry=True,
            retry_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            retry_delay=2.0,
            max_retries=3,
            fallback_available=False,
            user_message="User message"
        )
        
        result_dict = response.to_dict()
        
        assert result_dict['error_id'] == "test_error_123"
        assert result_dict['timestamp'] == timestamp.isoformat()
        assert result_dict['service'] == "test_service"
        assert result_dict['category'] == "network"
        assert result_dict['severity'] == "medium"
        assert result_dict['retry_strategy'] == "retry_with_backoff"
        assert result_dict['should_retry'] is True
        assert result_dict['fallback_available'] is False


class TestErrorPattern:
    """Test cases for ErrorPattern dataclass."""
    
    def test_error_pattern_creation(self):
        """Test ErrorPattern creation."""
        pattern = ErrorPattern(
            name="test_pattern",
            error_types=[ValueError, TypeError],
            message_patterns=["invalid", "malformed"],
            category=ErrorCategory.DATA_VALIDATION,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.SKIP_AND_CONTINUE,
            max_retries=2,
            retry_delay=1.5,
            user_message="Data validation failed",
            suggested_actions=["Check data format"]
        )
        
        assert pattern.name == "test_pattern"
        assert ValueError in pattern.error_types
        assert "invalid" in pattern.message_patterns
        assert pattern.category == ErrorCategory.DATA_VALIDATION
        assert pattern.recovery_strategy == RecoveryStrategy.SKIP_AND_CONTINUE
        assert pattern.max_retries == 2
        assert pattern.retry_delay == 1.5


class TestErrorHandlingService:
    """Test cases for ErrorHandlingService class."""
    
    @pytest.fixture
    def error_service(self):
        """Create ErrorHandlingService instance for testing."""
        with patch('utils.error_handling_enhanced.ErrorHandler') as mock_handler:
            mock_handler.return_value = Mock()
            service = ErrorHandlingService()
            return service
    
    def test_service_initialization(self, error_service):
        """Test service initialization."""
        assert error_service.logger is not None
        assert error_service.base_handler is not None
        assert len(error_service.error_patterns) > 0
        assert len(error_service.recovery_handlers) == 7
        assert isinstance(error_service.circuit_breakers, dict)
    
    def test_error_pattern_initialization(self, error_service):
        """Test that error patterns are properly initialized."""
        patterns = error_service.error_patterns
        
        # Check that we have expected patterns
        pattern_names = [p.name for p in patterns]
        expected_patterns = [
            "connection_timeout",
            "rate_limit_exceeded", 
            "authentication_failed",
            "validation_error",
            "scraping_failed",
            "storage_error"
        ]
        
        for expected in expected_patterns:
            assert expected in pattern_names
    
    def test_match_error_pattern_by_type(self, error_service):
        """Test error pattern matching by exception type."""
        # Test ValueError matching validation pattern
        error = ValueError("Invalid data format")
        pattern = error_service._match_error_pattern(error)
        
        assert pattern is not None
        assert pattern.name == "validation_error"
        assert pattern.category == ErrorCategory.DATA_VALIDATION
    
    def test_match_error_pattern_by_message(self, error_service):
        """Test error pattern matching by message content."""
        # Test rate limit message matching
        error = Exception("Rate limit exceeded - too many requests")
        pattern = error_service._match_error_pattern(error)
        
        assert pattern is not None
        assert pattern.name == "rate_limit_exceeded"
        assert pattern.category == ErrorCategory.API_RATE_LIMIT
    
    def test_match_error_pattern_no_match(self, error_service):
        """Test error pattern matching when no pattern matches."""
        error = Exception("Some unknown error")
        pattern = error_service._match_error_pattern(error)
        
        assert pattern is None
    
    def test_handle_error_with_pattern_match(self, error_service):
        """Test error handling when pattern matches."""
        error = ValueError("Invalid input data")
        
        with patch.object(error_service.base_handler, 'handle_error') as mock_handle:
            mock_handle.return_value = Mock()
            
            response = error_service.handle_error(
                error=error,
                service="test_service",
                operation="test_operation"
            )
            
            assert isinstance(response, ErrorResponse)
            assert response.service == "test_service"
            assert response.operation == "test_operation"
            assert response.category == ErrorCategory.DATA_VALIDATION
            assert response.severity == ErrorSeverity.HIGH
            assert response.retry_strategy == RecoveryStrategy.SKIP_AND_CONTINUE
    
    def test_handle_error_without_pattern_match(self, error_service):
        """Test error handling when no pattern matches."""
        error = Exception("Unknown error")
        
        with patch.object(error_service.base_handler, 'handle_error') as mock_handle:
            mock_handle.return_value = Mock()
            
            with patch.object(error_service, '_categorize_error') as mock_categorize:
                mock_categorize.return_value = ErrorCategory.UNKNOWN
                
                with patch.object(error_service, '_assess_severity') as mock_assess:
                    mock_assess.return_value = ErrorSeverity.MEDIUM
                    
                    response = error_service.handle_error(
                        error=error,
                        service="test_service",
                        operation="test_operation"
                    )
                    
                    assert isinstance(response, ErrorResponse)
                    assert response.category == ErrorCategory.UNKNOWN
                    assert response.severity == ErrorSeverity.MEDIUM
    
    def test_should_retry_with_pattern(self, error_service):
        """Test retry decision with pattern."""
        pattern = ErrorPattern(
            name="test_pattern",
            error_types=[],
            message_patterns=[],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF
        )
        
        error = Exception("Test error")
        should_retry = error_service._should_retry(error, pattern)
        
        assert should_retry is True
    
    def test_should_retry_without_pattern(self, error_service):
        """Test retry decision without pattern."""
        error = Exception("Test error")
        should_retry = error_service._should_retry(error, None)
        
        assert should_retry is True
        
        # Test non-retryable errors
        non_retryable = KeyboardInterrupt()
        should_retry = error_service._should_retry(non_retryable, None)
        
        assert should_retry is False
    
    def test_has_fallback(self, error_service):
        """Test fallback availability check."""
        # Test service with fallback
        has_fallback = error_service._has_fallback("ai_parser", "parse_linkedin_profile")
        assert has_fallback is True
        
        # Test service without fallback
        has_fallback = error_service._has_fallback("unknown_service", "unknown_operation")
        assert has_fallback is False
    
    def test_generate_user_message_with_pattern(self, error_service):
        """Test user message generation with pattern."""
        pattern = ErrorPattern(
            name="test_pattern",
            error_types=[],
            message_patterns=[],
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            user_message="Custom user message"
        )
        
        error = Exception("Test error")
        message = error_service._generate_user_message(error, pattern)
        
        assert message == "Custom user message"
    
    def test_generate_user_message_without_pattern(self, error_service):
        """Test user message generation without pattern."""
        # Test network error
        error = Exception("Connection timeout occurred")
        message = error_service._generate_user_message(error, None)
        
        assert "Network connectivity issue" in message
        
        # Test rate limit error
        error = Exception("Rate limit exceeded")
        message = error_service._generate_user_message(error, None)
        
        assert "rate limit" in message.lower()
    
    def test_generate_suggested_actions(self, error_service):
        """Test suggested actions generation."""
        # Test network error
        error = Exception("Network connection failed")
        actions = error_service._generate_suggested_actions(error)
        
        assert len(actions) > 0
        assert any("internet connection" in action.lower() for action in actions)
        
        # Test auth error
        error = Exception("Unauthorized access")
        actions = error_service._generate_suggested_actions(error)
        
        assert any("credentials" in action.lower() for action in actions)
    
    def test_circuit_breaker_functionality(self, error_service):
        """Test circuit breaker functionality."""
        service = "test_service"
        operation = "test_operation"
        
        # Initially circuit should be closed
        assert not error_service._is_circuit_open(service, operation)
        
        # Simulate multiple failures
        for i in range(5):
            error_response = ErrorResponse(
                error_id=f"error_{i}",
                timestamp=datetime.now(),
                service=service,
                operation=operation,
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                message="Test error",
                technical_details="Details",
                should_retry=True,
                retry_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
                retry_delay=1.0,
                max_retries=3,
                fallback_available=False,
                user_message="Test message"
            )
            error_service._update_circuit_breaker(service, operation, error_response)
        
        # Circuit should now be open
        assert error_service._is_circuit_open(service, operation)
        
        # Reset circuit breaker
        error_service._reset_circuit_breaker(service, operation)
        assert not error_service._is_circuit_open(service, operation)
    
    def test_execute_with_recovery_success(self, error_service):
        """Test execute_with_recovery with successful operation."""
        def successful_func():
            return "success"
        
        result = error_service.execute_with_recovery(
            successful_func,
            "test_service",
            "test_operation"
        )
        
        assert result == "success"
    
    def test_execute_with_recovery_with_retry(self, error_service):
        """Test execute_with_recovery with retry."""
        call_count = 0
        
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"
        
        with patch.object(error_service, '_apply_recovery_strategy') as mock_strategy:
            mock_strategy.return_value = None  # Let retry happen
            
            result = error_service.execute_with_recovery(
                failing_then_success,
                "test_service",
                "test_operation"
            )
            
            assert result == "success"
            assert call_count == 3
    
    def test_execute_with_recovery_with_fallback(self, error_service):
        """Test execute_with_recovery with fallback."""
        def failing_func():
            raise Exception("Always fails")
        
        def fallback_func():
            return "fallback_success"
        
        with patch.object(error_service, '_has_fallback', return_value=True):
            result = error_service.execute_with_recovery(
                failing_func,
                "test_service",
                "test_operation",
                fallback_func=fallback_func
            )
            
            assert result == "fallback_success"
    
    def test_execute_with_recovery_circuit_breaker_open(self, error_service):
        """Test execute_with_recovery when circuit breaker is open."""
        with patch.object(error_service, '_is_circuit_open', return_value=True):
            with pytest.raises(RuntimeError, match="Circuit breaker open"):
                error_service.execute_with_recovery(
                    lambda: "test",
                    "test_service",
                    "test_operation"
                )
    
    def test_get_error_statistics(self, error_service):
        """Test error statistics retrieval."""
        with patch.object(error_service.base_handler, 'get_error_summary') as mock_summary:
            mock_summary.return_value = {
                'total_errors': 5,
                'by_category': {'network': 3, 'api_rate_limit': 2}
            }
            
            stats = error_service.get_error_statistics(24)
            
            assert 'total_errors' in stats
            assert 'circuit_breakers' in stats
            assert 'recovery_strategies' in stats
            assert 'error_patterns' in stats
            assert stats['total_errors'] == 5


class TestRecoveryStrategies:
    """Test cases for recovery strategy handlers."""
    
    @pytest.fixture
    def error_service(self):
        """Create ErrorHandlingService instance for testing."""
        with patch('utils.error_handling_enhanced.ErrorHandler') as mock_handler:
            mock_handler.return_value = Mock()
            return ErrorHandlingService()
    
    @pytest.fixture
    def sample_error_response(self):
        """Create sample error response for testing."""
        return ErrorResponse(
            error_id="test_error",
            timestamp=datetime.now(),
            service="test_service",
            operation="test_operation",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Test error",
            technical_details="Details",
            should_retry=True,
            retry_strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            retry_delay=0.1,  # Short delay for testing
            max_retries=3,
            fallback_available=False,
            user_message="Test message"
        )
    
    def test_handle_retry_immediate(self, error_service, sample_error_response):
        """Test immediate retry strategy."""
        result = error_service._handle_retry_immediate(
            sample_error_response, lambda: "test", (), {}, 1
        )
        
        assert result is None  # Should return None to let main loop handle retry
    
    def test_handle_retry_with_backoff(self, error_service, sample_error_response):
        """Test retry with backoff strategy."""
        start_time = time.time()
        
        result = error_service._handle_retry_with_backoff(
            sample_error_response, lambda: "test", (), {}, 2
        )
        
        end_time = time.time()
        
        assert result is None
        # Should have waited for backoff delay
        assert end_time - start_time >= sample_error_response.retry_delay
    
    def test_handle_retry_after_delay(self, error_service, sample_error_response):
        """Test retry after fixed delay strategy."""
        start_time = time.time()
        
        result = error_service._handle_retry_after_delay(
            sample_error_response, lambda: "test", (), {}, 1
        )
        
        end_time = time.time()
        
        assert result is None
        # Should have waited for fixed delay
        assert end_time - start_time >= sample_error_response.retry_delay
    
    def test_handle_skip_and_continue(self, error_service, sample_error_response):
        """Test skip and continue strategy."""
        result = error_service._handle_skip_and_continue(
            sample_error_response, lambda: "test", (), {}, 1
        )
        
        assert result is None
    
    def test_handle_fail_fast(self, error_service, sample_error_response):
        """Test fail fast strategy."""
        with pytest.raises(RuntimeError):
            error_service._handle_fail_fast(
                sample_error_response, lambda: "test", (), {}, 1
            )
    
    def test_handle_user_intervention(self, error_service, sample_error_response):
        """Test user intervention strategy."""
        with pytest.raises(RuntimeError, match="User intervention required"):
            error_service._handle_user_intervention(
                sample_error_response, lambda: "test", (), {}, 1
            )


class TestGlobalFunctions:
    """Test cases for global convenience functions."""
    
    def test_get_enhanced_error_handler(self):
        """Test global error handler getter."""
        handler1 = get_enhanced_error_handler()
        handler2 = get_enhanced_error_handler()
        
        # Should return the same instance (singleton)
        assert handler1 is handler2
        assert isinstance(handler1, ErrorHandlingService)
    
    def test_handle_error_enhanced(self):
        """Test global error handling function."""
        with patch('utils.error_handling_enhanced.get_enhanced_error_handler') as mock_get:
            mock_handler = Mock()
            mock_response = Mock(spec=ErrorResponse)
            mock_handler.handle_error.return_value = mock_response
            mock_get.return_value = mock_handler
            
            error = Exception("Test error")
            result = handle_error_enhanced(error, "test_service", "test_operation")
            
            assert result == mock_response
            mock_handler.handle_error.assert_called_once_with(
                error, "test_service", "test_operation", None
            )
    
    def test_execute_with_recovery_global(self):
        """Test global execute with recovery function."""
        with patch('utils.error_handling_enhanced.get_enhanced_error_handler') as mock_get:
            mock_handler = Mock()
            mock_handler.execute_with_recovery.return_value = "success"
            mock_get.return_value = mock_handler
            
            def test_func():
                return "test"
            
            result = execute_with_recovery(test_func, "test_service", "test_operation")
            
            assert result == "success"
            mock_handler.execute_with_recovery.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])