"""
Example demonstrating the comprehensive error handling and monitoring system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from utils.error_handling import (
    get_error_handler, ErrorCategory, ErrorSeverity, retry_with_backoff
)
from utils.api_monitor import get_api_monitor
from utils.error_reporting import get_error_reporter, NotificationConfig, NotificationChannel
from utils.logging_config import setup_logging


def main():
    """Demonstrate error handling and monitoring capabilities."""
    
    # Set up logging
    logger = setup_logging(log_level="INFO")
    
    # Get global instances
    error_handler = get_error_handler()
    api_monitor = get_api_monitor()
    
    # Configure error reporting
    notification_config = NotificationConfig(
        enabled=True,
        channels=[NotificationChannel.LOG, NotificationChannel.FILE],
        file_path="logs/error_notifications.json",
        severity_threshold=ErrorSeverity.MEDIUM
    )
    error_reporter = get_error_reporter()
    error_reporter.config = notification_config
    
    print("=== Error Handling and Monitoring System Demo ===\n")
    
    # 1. Demonstrate basic error handling
    print("1. Basic Error Handling:")
    try:
        raise ValueError("This is a test validation error")
    except Exception as e:
        error_info = error_handler.handle_error(
            error=e,
            service="demo_service",
            operation="validation_test",
            context={"input_data": "invalid_format"},
            category=ErrorCategory.DATA_VALIDATION,
            severity=ErrorSeverity.MEDIUM
        )
        print(f"   Error handled: {error_info.error_id}")
        
        # Send notification
        notification_sent = error_reporter.send_error_notification(error_info)
        print(f"   Notification sent: {notification_sent}")
    
    print()
    
    # 2. Demonstrate retry mechanism
    print("2. Retry Mechanism:")
    
    @retry_with_backoff(category=ErrorCategory.NETWORK)
    def unreliable_network_call():
        """Simulate an unreliable network call."""
        import random
        if random.random() < 0.7:  # 70% chance of failure
            raise ConnectionError("Network timeout")
        return "Success!"
    
    try:
        result = unreliable_network_call()
        print(f"   Network call result: {result}")
    except Exception as e:
        print(f"   Network call failed after retries: {e}")
    
    print()
    
    # 3. Demonstrate API monitoring
    print("3. API Monitoring:")
    
    # Simulate some API calls
    api_calls = [
        ("hunter_io", "domain-search", 1.2, 200, True),
        ("hunter_io", "email-finder", 0.8, 200, True),
        ("hunter_io", "email-verifier", 2.1, 429, False),  # Rate limit hit
        ("linkedin", "profile_extraction", 5.3, 200, True),
        ("notion", "create_page", 1.5, 200, True),
        ("notion", "update_page", 0.9, 500, False),  # Server error
    ]
    
    for service, endpoint, response_time, status_code, success in api_calls:
        api_monitor.record_api_call(
            service=service,
            endpoint=endpoint,
            response_time=response_time,
            status_code=status_code,
            success=success,
            error_message="Rate limit exceeded" if status_code == 429 else None
        )
    
    # Update quota information
    api_monitor.update_quota_usage(
        service="hunter_io",
        quota_type="monthly_requests",
        used=85,
        limit=100,
        reset_time=datetime.now() + timedelta(days=30)
    )
    
    print("   API calls recorded and quota updated")
    
    # Get API metrics
    metrics = api_monitor.get_api_metrics(hours=24)
    print(f"   Total API calls: {metrics['total_calls']}")
    print(f"   Success rate: {metrics['success_rate']:.1f}%")
    print(f"   Average response time: {metrics['avg_response_time']:.2f}s")
    print(f"   Rate limit hits: {metrics['rate_limit_hits']}")
    
    print()
    
    # 4. Demonstrate service health monitoring
    print("4. Service Health Monitoring:")
    
    service_health = api_monitor.get_service_health()
    for service, health in service_health.items():
        print(f"   {service}: {health.status.value} "
              f"(Success: {health.success_rate:.1f}%, "
              f"Avg time: {health.avg_response_time:.2f}s)")
    
    print()
    
    # 5. Demonstrate quota monitoring
    print("5. Quota Monitoring:")
    
    quota_status = error_handler.get_quota_status()
    for quota_key, quota in quota_status.items():
        print(f"   {quota.service_name} {quota.quota_type}: "
              f"{quota.used}/{quota.limit} ({quota.usage_percentage:.1f}%)")
        if quota.is_near_limit:
            print(f"     WARNING: Near quota limit!")
    
    print()
    
    # 6. Demonstrate error summary
    print("6. Error Summary:")
    
    error_summary = error_handler.get_error_summary(hours=24)
    print(f"   Total errors in last 24h: {error_summary['total_errors']}")
    print("   By category:")
    for category, count in error_summary['by_category'].items():
        print(f"     {category}: {count}")
    print("   By severity:")
    for severity, count in error_summary['by_severity'].items():
        print(f"     {severity}: {count}")
    
    print()
    
    # 7. Demonstrate monitoring report
    print("7. Comprehensive Monitoring Report:")
    
    monitoring_report = api_monitor.get_monitoring_report()
    print(f"   Overall health: {monitoring_report['overall_health']}")
    print(f"   Active alerts: {len(monitoring_report['alerts'])}")
    for alert in monitoring_report['alerts']:
        print(f"     - {alert}")
    
    print()
    
    # 8. Demonstrate health report
    print("8. Health Report:")
    
    health_report_sent = error_reporter.send_health_report(force=True)
    print(f"   Health report sent: {health_report_sent}")
    
    print("\n=== Demo Complete ===")
    print("Check the logs/ directory for detailed error and monitoring data.")


if __name__ == "__main__":
    main()