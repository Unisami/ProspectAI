"""
Tests for the error handling and monitoring system.
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from utils.error_handling import (
    ErrorHandler, ErrorInfo, ErrorCategory, ErrorSeverity, RetryConfig,
    get_error_handler, handle_error, retry_with_backoff
)
from utils.api_monitor import APIMonitor, APICall, RateLimitInfo, ServiceHealth, ServiceStatus
from utils.error_reporting import ErrorReporter, NotificationConfig, NotificationChannel


class TestErrorHandler:
    """Test cases for ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary config file
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_error_monitoring.json")
        self.error_handler = ErrorHandler(config_path=self.config_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_handle_error_basic(self):
        """Test basic error handling."""
        error = ValueError("Test error message")
        
        error_info = self.error_handler.handle_error(
            error=error,
            service="test_service",
            operation="test_operation"
        )
        
        assert error_info.service == "test_service"
        assert error_info.operation == "test_operation"
        assert error_info.error_type == "ValueError"
        assert error_info.error_message == "Test error message"
        assert error_info.category == ErrorCategory.UNKNOWN
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert len(self.error_handler.errors) == 1
    
    def test_handle_error_with_context(self):
        """Test error handling with context."""
        error = ConnectionError("Network timeout")
        context = {"url": "https://example.com", "timeout": 30}
        
        error_info = self.error_handler.handle_error(
            error=error,
            service="api_service",
            operation="fetch_data",
            context=context,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH
        )
        
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.HIGH
        assert error_info.context == context
    
    def test_error_categorization(self):
        """Test automatic error categorization."""
        test_cases = [
            (ConnectionError("Connection timeout"), ErrorCategory.NETWORK),
            (Exception("Rate limit exceeded"), ErrorCategory.API_RATE_LIMIT),
            (Exception("429 Too Many Requests"), ErrorCategory.API_RATE_LIMIT),
            (Exception("Quota exceeded"), ErrorCategory.API_QUOTA),
            (Exception("Unauthorized access"), ErrorCategory.AUTHENTICATION),
            (Exception("Invalid data format"), ErrorCategory.DATA_VALIDATION),
            (Exception("Selenium WebDriver error"), ErrorCategory.SCRAPING),
            (Exception("Database connection failed"), ErrorCategory.STORAGE),
            (Exception("Config file not found"), ErrorCategory.CONFIGURATION)
        ]
        
        for error, expected_category in test_cases:
            categorized = self.error_handler._categorize_error(error)
            assert categorized == expected_category, f"Error '{error}' should be categorized as {expected_category}"
    
    def test_severity_assessment(self):
        """Test automatic severity assessment."""
        test_cases = [
            (Exception("Authentication failed"), ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL),
            (Exception("Quota exhausted"), ErrorCategory.API_QUOTA, ErrorSeverity.HIGH),
            (Exception("Rate limit hit"), ErrorCategory.API_RATE_LIMIT, ErrorSeverity.MEDIUM),
            (Exception("Network timeout"), ErrorCategory.NETWORK, ErrorSeverity.LOW),
            (Exception("Scraping failed"), ErrorCategory.SCRAPING, ErrorSeverity.LOW)
        ]
        
        for error, category, expected_severity in test_cases:
            severity = self.error_handler._assess_severity(error, category)
            assert severity == expected_severity
    
    def test_retry_with_backoff_success(self):
        """Test retry mechanism with successful retry."""
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = self.error_handler.retry_with_backoff(
            failing_function,
            category=ErrorCategory.NETWORK
        )
        
        assert result == "success"
        assert call_count == 3
    
    def test_retry_with_backoff_failure(self):
        """Test retry mechanism with all attempts failing."""
        call_count = 0
        
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            self.error_handler.retry_with_backoff(
                always_failing_function,
                category=ErrorCategory.NETWORK
            )
        
        # Should have tried the maximum number of attempts
        retry_config = self.error_handler.retry_configs[ErrorCategory.NETWORK]
        assert call_count == retry_config.max_attempts
    
    def test_service_quota_tracking(self):
        """Test service quota tracking."""
        reset_time = datetime.now() + timedelta(hours=1)
        
        self.error_handler.update_service_quota(
            service_name="test_api",
            quota_type="requests",
            used=80,
            limit=100,
            reset_time=reset_time
        )
        
        quotas = self.error_handler.get_quota_status("test_api")
        assert len(quotas) == 1
        
        quota = list(quotas.values())[0]
        assert quota.service_name == "test_api"
        assert quota.used == 80
        assert quota.limit == 100
        assert quota.is_near_limit  # 80% usage
        assert not quota.is_exhausted
    
    def test_error_summary(self):
        """Test error summary generation."""
        # Generate some test errors
        errors = [
            (ValueError("Validation error"), ErrorCategory.DATA_VALIDATION, ErrorSeverity.MEDIUM),
            (ConnectionError("Network error"), ErrorCategory.NETWORK, ErrorSeverity.LOW),
            (Exception("Rate limit"), ErrorCategory.API_RATE_LIMIT, ErrorSeverity.MEDIUM),
            (Exception("Auth error"), ErrorCategory.AUTHENTICATION, ErrorSeverity.CRITICAL)
        ]
        
        for error, category, severity in errors:
            self.error_handler.handle_error(
                error, "test_service", "test_op", category=category, severity=severity
            )
        
        summary = self.error_handler.get_error_summary(hours=24)
        
        assert summary['total_errors'] == 4
        assert summary['by_category']['data_validation'] == 1
        assert summary['by_category']['network'] == 1
        assert summary['by_category']['api_rate_limit'] == 1
        assert summary['by_category']['authentication'] == 1
        assert summary['by_severity']['critical'] == 1
        assert summary['by_severity']['medium'] == 2
        assert summary['by_severity']['low'] == 1
    
    def test_data_persistence(self):
        """Test error data persistence."""
        # Add some errors
        error1 = ValueError("Test error 1")
        error2 = ConnectionError("Test error 2")
        
        self.error_handler.handle_error(error1, "service1", "op1")
        self.error_handler.handle_error(error2, "service2", "op2")
        
        # Force save
        self.error_handler._save_error_data()
        
        # Create new handler with same config path
        new_handler = ErrorHandler(config_path=self.config_path)
        
        # Should load previous errors
        assert len(new_handler.errors) == 2
        assert new_handler.errors[0].error_message == "Test error 1"
        assert new_handler.errors[1].error_message == "Test error 2"


class TestAPIMonitor:
    """Test cases for APIMonitor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_api_monitoring.json")
        self.api_monitor = APIMonitor(config_path=self.config_path)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_record_api_call(self):
        """Test API call recording."""
        self.api_monitor.record_api_call(
            service="test_service",
            endpoint="test_endpoint",
            response_time=1.5,
            status_code=200,
            success=True
        )
        
        assert len(self.api_monitor.api_calls) == 1
        call = self.api_monitor.api_calls[0]
        assert call.service == "test_service"
        assert call.endpoint == "test_endpoint"
        assert call.response_time == 1.5
        assert call.status_code == 200
        assert call.success is True
    
    def test_rate_limit_tracking(self):
        """Test rate limit tracking."""
        headers = {
            'X-RateLimit-Limit': '100',
            'X-RateLimit-Remaining': '20',
            'X-RateLimit-Reset': str(int((datetime.now() + timedelta(hours=1)).timestamp()))
        }
        
        self.api_monitor.record_api_call(
            service="test_api",
            endpoint="test",
            response_time=1.0,
            status_code=200,
            success=True,
            rate_limit_headers=headers
        )
        
        rate_limits = self.api_monitor.get_rate_limit_status("test_api")
        assert len(rate_limits) == 1
        
        rate_limit = list(rate_limits.values())[0]
        assert rate_limit.limit == 100
        assert rate_limit.remaining == 20
        assert rate_limit.is_near_limit  # 80% usage
    
    def test_service_health_tracking(self):
        """Test service health tracking."""
        # Record successful calls
        for i in range(8):
            self.api_monitor.record_api_call(
                service="healthy_service",
                endpoint="test",
                response_time=1.0,
                status_code=200,
                success=True
            )
        
        # Record some failures
        for i in range(2):
            self.api_monitor.record_api_call(
                service="healthy_service",
                endpoint="test",
                response_time=5.0,
                status_code=500,
                success=False
            )
        
        health = self.api_monitor.get_service_health("healthy_service")
        assert "healthy_service" in health
        
        service_health = health["healthy_service"]
        assert service_health.total_calls == 10
        assert service_health.failed_calls == 2
        assert service_health.success_rate == 80.0
        assert service_health.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]
    
    def test_api_metrics(self):
        """Test API metrics calculation."""
        # Record various API calls
        calls_data = [
            ("service1", "endpoint1", 1.0, 200, True),
            ("service1", "endpoint1", 2.0, 200, True),
            ("service1", "endpoint2", 3.0, 500, False),
            ("service2", "endpoint1", 1.5, 429, False),
        ]
        
        for service, endpoint, time, status, success in calls_data:
            self.api_monitor.record_api_call(service, endpoint, time, status, success)
        
        # Test overall metrics
        metrics = self.api_monitor.get_api_metrics(hours=24)
        assert metrics['total_calls'] == 4
        assert metrics['success_rate'] == 50.0  # 2 out of 4 successful
        assert metrics['avg_response_time'] == 1.875  # (1+2+3+1.5)/4
        assert metrics['rate_limit_hits'] == 1
        
        # Test service-specific metrics
        service1_metrics = self.api_monitor.get_api_metrics("service1", hours=24)
        assert service1_metrics['total_calls'] == 3
        assert abs(service1_metrics['success_rate'] - 66.67) < 0.01  # 2 out of 3 successful (rounded)
    
    def test_monitoring_report(self):
        """Test comprehensive monitoring report."""
        # Add some API calls
        self.api_monitor.record_api_call("service1", "endpoint1", 1.0, 200, True)
        self.api_monitor.record_api_call("service1", "endpoint1", 10.0, 500, False)
        
        # Add quota information
        self.api_monitor.update_quota_usage(
            service="service1",
            quota_type="requests",
            used=95,
            limit=100,
            reset_time=datetime.now() + timedelta(hours=1)
        )
        
        report = self.api_monitor.get_monitoring_report()
        
        assert 'timestamp' in report
        assert 'services' in report
        assert 'overall_health' in report
        assert 'alerts' in report
        
        # Should have alerts for quota near limit
        assert len(report['alerts']) > 0
        assert any('quota' in alert.lower() for alert in report['alerts'])


class TestErrorReporter:
    """Test cases for ErrorReporter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = NotificationConfig(
            enabled=True,
            channels=[NotificationChannel.LOG, NotificationChannel.FILE],
            file_path="test_notifications.json",
            severity_threshold=ErrorSeverity.MEDIUM
        )
        self.reporter = ErrorReporter(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists("test_notifications.json"):
            os.remove("test_notifications.json")
    
    def test_error_notification_threshold(self):
        """Test error notification severity threshold."""
        low_severity_error = ErrorInfo(
            error_id="test1",
            timestamp=datetime.now(),
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.LOW,
            service="test_service",
            operation="test_op",
            error_type="TestError",
            error_message="Low severity error"
        )
        
        high_severity_error = ErrorInfo(
            error_id="test2",
            timestamp=datetime.now(),
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            service="test_service",
            operation="test_op",
            error_type="TestError",
            error_message="Critical error"
        )
        
        # Low severity should not trigger notification
        result1 = self.reporter.send_error_notification(low_severity_error)
        assert result1 is False
        
        # High severity should trigger notification
        result2 = self.reporter.send_error_notification(high_severity_error)
        assert result2 is True
    
    def test_notification_cooldown(self):
        """Test notification cooldown mechanism."""
        error_info = ErrorInfo(
            error_id="test",
            timestamp=datetime.now(),
            category=ErrorCategory.API_RATE_LIMIT,
            severity=ErrorSeverity.HIGH,
            service="test_service",
            operation="test_op",
            error_type="TestError",
            error_message="Test error"
        )
        
        # First notification should succeed
        result1 = self.reporter.send_error_notification(error_info)
        assert result1 is True
        
        # Second notification should be blocked by cooldown
        result2 = self.reporter.send_error_notification(error_info)
        assert result2 is False
        
        # Forced notification should succeed
        result3 = self.reporter.send_error_notification(error_info, force=True)
        assert result3 is True
    
    def test_file_notification(self):
        """Test file notification channel."""
        error_info = ErrorInfo(
            error_id="test_file",
            timestamp=datetime.now(),
            category=ErrorCategory.STORAGE,
            severity=ErrorSeverity.HIGH,
            service="test_service",
            operation="test_op",
            error_type="TestError",
            error_message="File notification test"
        )
        
        result = self.reporter.send_error_notification(error_info)
        assert result is True
        
        # Check that file was created and contains notification
        assert os.path.exists("test_notifications.json")
        
        with open("test_notifications.json", 'r') as f:
            content = f.read().strip()
            notification_data = json.loads(content)
            assert notification_data['error_id'] == "test_file"
            assert notification_data['message'] == "File notification test"
    
    def test_recommendation_generation(self):
        """Test recommendation generation."""
        error_summary = {
            'total_errors': 60,
            'by_category': {
                'api_rate_limit': 15,
                'network': 25,
                'authentication': 2,
                'scraping': 18
            }
        }
        
        service_health = {
            'service1': {'status': 'unhealthy'},
            'service2': {'status': 'healthy'}
        }
        
        api_metrics = {
            'success_rate': 75,
            'avg_response_time': 8.5
        }
        
        recommendations = self.reporter._generate_recommendations(
            error_summary, service_health, api_metrics
        )
        
        assert len(recommendations) > 0
        assert any('high error rate' in rec.lower() for rec in recommendations)
        assert any('rate limit' in rec.lower() for rec in recommendations)
        assert any('network errors' in rec.lower() for rec in recommendations)
        assert any('authentication' in rec.lower() for rec in recommendations)
        assert any('scraping' in rec.lower() for rec in recommendations)
        assert any('unhealthy services' in rec.lower() for rec in recommendations)
        assert any('response times' in rec.lower() for rec in recommendations)


class TestRetryDecorator:
    """Test cases for retry decorator."""
    
    def test_retry_decorator_success(self):
        """Test retry decorator with successful retry."""
        call_count = 0
        
        @retry_with_backoff(category=ErrorCategory.NETWORK)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 2
    
    def test_retry_decorator_failure(self):
        """Test retry decorator with all attempts failing."""
        call_count = 0
        
        @retry_with_backoff(category=ErrorCategory.NETWORK)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent failure")
        
        with pytest.raises(ConnectionError, match="Persistent failure"):
            always_failing_function()
        
        # Should have tried multiple times
        assert call_count > 1


class TestIntegration:
    """Integration tests for error handling and monitoring system."""
    
    def test_end_to_end_error_flow(self):
        """Test complete error handling flow."""
        # Create temporary config files
        temp_dir = tempfile.mkdtemp()
        error_config = os.path.join(temp_dir, "error_monitoring.json")
        api_config = os.path.join(temp_dir, "api_monitoring.json")
        
        try:
            # Initialize components
            error_handler = ErrorHandler(config_path=error_config)
            api_monitor = APIMonitor(config_path=api_config)
            reporter = ErrorReporter(NotificationConfig(
                channels=[NotificationChannel.LOG],
                severity_threshold=ErrorSeverity.MEDIUM
            ))
            
            # Simulate API call with error
            start_time = time.time()
            try:
                raise ConnectionError("Network timeout")
            except Exception as e:
                response_time = time.time() - start_time
                
                # Record failed API call
                api_monitor.record_api_call(
                    service="test_service",
                    endpoint="test_endpoint",
                    response_time=response_time,
                    status_code=0,
                    success=False,
                    error_message=str(e)
                )
                
                # Handle error
                error_info = error_handler.handle_error(
                    e, "test_service", "test_endpoint",
                    context={"url": "https://example.com"},
                    category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.HIGH  # Set high severity to trigger notification
                )
                
                # Send notification
                notification_sent = reporter.send_error_notification(error_info)
            
            # Verify error was recorded
            assert len(error_handler.errors) == 1
            assert error_handler.errors[0].error_message == "Network timeout"
            
            # Verify API call was recorded
            assert len(api_monitor.api_calls) == 1
            assert api_monitor.api_calls[0].success is False
            
            # Verify service health was updated
            health = api_monitor.get_service_health("test_service")
            assert "test_service" in health
            
            # Verify notification was sent (for medium+ severity)
            assert notification_sent is True
            
        finally:
            # Clean up
            for file_path in [error_config, api_config]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            os.rmdir(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__])