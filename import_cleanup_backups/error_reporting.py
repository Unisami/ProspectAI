"""
Error reporting and notification system for the job prospect automation system.
"""

import json
import smtplib
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from enum import Enum

from utils.logging_config import get_logger
from utils.error_handling import ErrorInfo, ErrorSeverity, ErrorCategory, get_error_handler
from utils.api_monitor import get_api_monitor, ServiceStatus


class NotificationChannel(Enum):
    """Available notification channels."""
    EMAIL = "email"
    LOG = "log"
    FILE = "file"
    WEBHOOK = "webhook"


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    enabled: bool = True
    channels: List[NotificationChannel] = None
    email_config: Optional[Dict[str, str]] = None
    webhook_url: Optional[str] = None
    file_path: Optional[str] = None
    severity_threshold: ErrorSeverity = ErrorSeverity.MEDIUM
    
    def __post_init__(self):
        if self.channels is None:
            self.channels = [NotificationChannel.LOG]


@dataclass
class ErrorReport:
    """Comprehensive error report."""
    report_id: str
    timestamp: datetime
    summary: Dict[str, Any]
    recent_errors: List[ErrorInfo]
    service_health: Dict[str, Any]
    api_metrics: Dict[str, Any]
    recommendations: List[str]


class ErrorReporter:
    """Error reporting and notification system."""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.logger = get_logger(__name__)
        self.error_handler = get_error_handler()
        self.api_monitor = get_api_monitor()
        self.config = config or NotificationConfig()
        
        # Notification handlers
        self.notification_handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.LOG: self._send_log_notification,
            NotificationChannel.FILE: self._send_file_notification,
            NotificationChannel.WEBHOOK: self._send_webhook_notification
        }
        
        # Track last notification times to avoid spam
        self.last_notifications: Dict[str, datetime] = {}
        self.notification_cooldown = timedelta(minutes=30)  # 30 minute cooldown
    
    def generate_error_report(self, hours: int = 24) -> ErrorReport:
        """
        Generate a comprehensive error report.
        
        Args:
            hours: Number of hours to include in the report
            
        Returns:
            ErrorReport object
        """
        report_id = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Get error summary
        error_summary = self.error_handler.get_error_summary(hours)
        
        # Get recent critical/high severity errors
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [
            error for error in self.error_handler.errors
            if error.timestamp >= cutoff_time and 
               error.severity in [ErrorSeverity.CRITICAL, ErrorSeverity.HIGH]
        ]
        
        # Get service health
        service_health = {}
        for service, health in self.api_monitor.get_service_health().items():
            service_health[service] = {
                'status': health.status.value,
                'success_rate': health.success_rate,
                'avg_response_time': health.avg_response_time,
                'total_calls': health.total_calls,
                'failed_calls': health.failed_calls,
                'rate_limit_hits': health.rate_limit_hits
            }
        
        # Get API metrics
        api_metrics = self.api_monitor.get_api_metrics(hours=hours)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(error_summary, service_health, api_metrics)
        
        return ErrorReport(
            report_id=report_id,
            timestamp=datetime.now(),
            summary=error_summary,
            recent_errors=recent_errors,
            service_health=service_health,
            api_metrics=api_metrics,
            recommendations=recommendations
        )
    
    def send_error_notification(self, 
                              error_info: ErrorInfo,
                              force: bool = False) -> bool:
        """
        Send error notification based on configuration.
        
        Args:
            error_info: Error information to report
            force: Force sending notification even if cooldown is active
            
        Returns:
            True if notification was sent, False otherwise
        """
        # Check severity threshold - compare enum values properly
        severity_levels = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        
        if severity_levels.get(error_info.severity, 0) < severity_levels.get(self.config.severity_threshold, 0):
            return False
        
        # Check cooldown (unless forced)
        if not force:
            notification_key = f"{error_info.service}_{error_info.category.value}"
            last_notification = self.last_notifications.get(notification_key)
            
            if last_notification and datetime.now() - last_notification < self.notification_cooldown:
                self.logger.debug(f"Skipping notification due to cooldown: {notification_key}")
                return False
        
        # Send notifications through configured channels
        success = False
        for channel in self.config.channels:
            try:
                handler = self.notification_handlers.get(channel)
                if handler:
                    handler(error_info)
                    success = True
                    self.logger.info(f"Sent error notification via {channel.value}")
                else:
                    self.logger.warning(f"No handler for notification channel: {channel.value}")
            except Exception as e:
                self.logger.error(f"Failed to send notification via {channel.value}: {e}")
        
        # Update last notification time
        if success:
            notification_key = f"{error_info.service}_{error_info.category.value}"
            self.last_notifications[notification_key] = datetime.now()
        
        return success
    
    def send_health_report(self, force: bool = False) -> bool:
        """
        Send periodic health report.
        
        Args:
            force: Force sending report even if cooldown is active
            
        Returns:
            True if report was sent, False otherwise
        """
        # Check cooldown (unless forced)
        if not force:
            last_report = self.last_notifications.get('health_report')
            if last_report and datetime.now() - last_report < timedelta(hours=6):  # 6 hour cooldown
                return False
        
        # Generate monitoring report
        monitoring_report = self.api_monitor.get_monitoring_report()
        
        # Only send if there are issues or it's been a while
        has_issues = (
            monitoring_report['overall_health'] != ServiceStatus.HEALTHY.value or
            len(monitoring_report['alerts']) > 0
        )
        
        last_report = self.last_notifications.get('health_report')
        been_a_while = not last_report or datetime.now() - last_report > timedelta(hours=24)
        
        if not has_issues and not been_a_while and not force:
            return False
        
        # Send health report
        success = False
        for channel in self.config.channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    self._send_health_email(monitoring_report)
                elif channel == NotificationChannel.LOG:
                    self._send_health_log(monitoring_report)
                elif channel == NotificationChannel.FILE:
                    self._send_health_file(monitoring_report)
                elif channel == NotificationChannel.WEBHOOK:
                    self._send_health_webhook(monitoring_report)
                
                success = True
                self.logger.info(f"Sent health report via {channel.value}")
                
            except Exception as e:
                self.logger.error(f"Failed to send health report via {channel.value}: {e}")
        
        if success:
            self.last_notifications['health_report'] = datetime.now()
        
        return success
    
    def _generate_recommendations(self, 
                                error_summary: Dict[str, Any],
                                service_health: Dict[str, Any],
                                api_metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on error patterns and metrics."""
        recommendations = []
        
        # Check error patterns
        if error_summary['total_errors'] > 50:
            recommendations.append("High error rate detected. Consider reviewing system stability.")
        
        # Check by category
        by_category = error_summary.get('by_category', {})
        
        if by_category.get('api_rate_limit', 0) > 10:
            recommendations.append("Multiple rate limit hits. Consider implementing better rate limiting or upgrading API plans.")
        
        if by_category.get('network', 0) > 20:
            recommendations.append("High number of network errors. Check internet connectivity and service availability.")
        
        if by_category.get('authentication', 0) > 0:
            recommendations.append("Authentication errors detected. Verify API keys and credentials.")
        
        if by_category.get('scraping', 0) > 15:
            recommendations.append("Scraping errors detected. Websites may have changed or implemented anti-bot measures.")
        
        # Check service health
        unhealthy_services = [
            service for service, health in service_health.items()
            if health['status'] == 'unhealthy'
        ]
        
        if unhealthy_services:
            recommendations.append(f"Unhealthy services detected: {', '.join(unhealthy_services)}. Check service status and configuration.")
        
        # Check API metrics
        if api_metrics.get('success_rate', 100) < 80:
            recommendations.append("Low API success rate. Review error patterns and implement better error handling.")
        
        if api_metrics.get('avg_response_time', 0) > 5:
            recommendations.append("High average response times. Consider optimizing requests or checking service performance.")
        
        return recommendations
    
    def _send_email_notification(self, error_info: ErrorInfo) -> None:
        """Send error notification via email."""
        if not self.config.email_config:
            raise ValueError("Email configuration not provided")
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.config.email_config['from']
        msg['To'] = self.config.email_config['to']
        msg['Subject'] = f"[{error_info.severity.value.upper()}] Error in {error_info.service}"
        
        # Create email body
        body = f"""
Error Alert - Job Prospect Automation System

Error ID: {error_info.error_id}
Timestamp: {error_info.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Service: {error_info.service}
Operation: {error_info.operation}
Category: {error_info.category.value}
Severity: {error_info.severity.value}

Error Message:
{error_info.error_message}

Context:
{json.dumps(error_info.context, indent=2)}

Please investigate and resolve this issue.
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(self.config.email_config['smtp_server'], 
                         int(self.config.email_config.get('smtp_port', 587))) as server:
            if self.config.email_config.get('use_tls', True):
                server.starttls()
            
            if 'username' in self.config.email_config:
                server.login(self.config.email_config['username'], 
                           self.config.email_config['password'])
            
            server.send_message(msg)
    
    def _send_log_notification(self, error_info: ErrorInfo) -> None:
        """Send error notification via logging."""
        self.logger.error(f"ERROR NOTIFICATION: [{error_info.error_id}] {error_info.service}.{error_info.operation} - {error_info.error_message}")
    
    def _send_file_notification(self, error_info: ErrorInfo) -> None:
        """Send error notification to file."""
        file_path = self.config.file_path or "logs/error_notifications.json"
        
        notification = {
            'timestamp': datetime.now().isoformat(),
            'error_id': error_info.error_id,
            'service': error_info.service,
            'operation': error_info.operation,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.error_message,
            'context': error_info.context
        }
        
        # Append to file
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(notification) + '\n')
    
    def _send_webhook_notification(self, error_info: ErrorInfo) -> None:
        """Send error notification via webhook."""
        if not self.config.webhook_url:
            raise ValueError("Webhook URL not configured")
        
        import requests
        
        payload = {
            'timestamp': error_info.timestamp.isoformat(),
            'error_id': error_info.error_id,
            'service': error_info.service,
            'operation': error_info.operation,
            'category': error_info.category.value,
            'severity': error_info.severity.value,
            'message': error_info.error_message,
            'context': error_info.context
        }
        
        response = requests.post(self.config.webhook_url, json=payload, timeout=10)
        response.raise_for_status()
    
    def _send_health_email(self, monitoring_report: Dict[str, Any]) -> None:
        """Send health report via email."""
        if not self.config.email_config:
            raise ValueError("Email configuration not provided")
        
        msg = MIMEMultipart()
        msg['From'] = self.config.email_config['from']
        msg['To'] = self.config.email_config['to']
        msg['Subject'] = f"Health Report - Job Prospect Automation ({monitoring_report['overall_health']})"
        
        # Create email body
        body = f"""
Health Report - Job Prospect Automation System

Overall Health: {monitoring_report['overall_health'].upper()}
Report Time: {monitoring_report['timestamp']}

Alerts:
{chr(10).join(f"- {alert}" for alert in monitoring_report['alerts']) if monitoring_report['alerts'] else "No alerts"}

Service Status:
"""
        
        for service, data in monitoring_report['services'].items():
            body += f"""
{service}:
  - Health: {data['health']}
  - Success Rate: {data['metrics'].get('success_rate', 0):.1f}%
  - Total Calls: {data['metrics'].get('total_calls', 0)}
  - Avg Response Time: {data['metrics'].get('avg_response_time', 0):.2f}s
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(self.config.email_config['smtp_server'], 
                         int(self.config.email_config.get('smtp_port', 587))) as server:
            if self.config.email_config.get('use_tls', True):
                server.starttls()
            
            if 'username' in self.config.email_config:
                server.login(self.config.email_config['username'], 
                           self.config.email_config['password'])
            
            server.send_message(msg)
    
    def _send_health_log(self, monitoring_report: Dict[str, Any]) -> None:
        """Send health report via logging."""
        self.logger.info(f"HEALTH REPORT: Overall health: {monitoring_report['overall_health']}")
        
        if monitoring_report['alerts']:
            for alert in monitoring_report['alerts']:
                self.logger.warning(f"HEALTH ALERT: {alert}")
    
    def _send_health_file(self, monitoring_report: Dict[str, Any]) -> None:
        """Send health report to file."""
        file_path = self.config.file_path or "logs/health_reports.json"
        
        # Append to file
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'a') as f:
            f.write(json.dumps(monitoring_report) + '\n')
    
    def _send_health_webhook(self, monitoring_report: Dict[str, Any]) -> None:
        """Send health report via webhook."""
        if not self.config.webhook_url:
            raise ValueError("Webhook URL not configured")
        
        import requests
        
        response = requests.post(self.config.webhook_url, json=monitoring_report, timeout=10)
        response.raise_for_status()


# Global reporter instance
_global_error_reporter = None


def get_error_reporter() -> ErrorReporter:
    """Get the global error reporter instance."""
    global _global_error_reporter
    if _global_error_reporter is None:
        _global_error_reporter = ErrorReporter()
    return _global_error_reporter


def send_error_notification(error_info: ErrorInfo, force: bool = False) -> bool:
    """Convenience function to send error notifications."""
    return get_error_reporter().send_error_notification(error_info, force)