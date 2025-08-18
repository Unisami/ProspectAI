"""
API monitoring system for tracking rate limits, quotas, and service health.
"""

import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

from utils.logging_config import get_logger
from utils.error_handling import get_error_handler, ErrorCategory


class ServiceStatus(Enum):
    """Service health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class APICall:
    """Record of an API call."""
    service: str
    endpoint: str
    timestamp: datetime
    response_time: float
    status_code: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class RateLimitInfo:
    """Rate limit information for an API."""
    service: str
    limit: int
    remaining: int
    reset_time: datetime
    window_seconds: int
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage."""
        used = self.limit - self.remaining
        return (used / self.limit) * 100 if self.limit > 0 else 0
    
    @property
    def is_near_limit(self) -> bool:
        """Check if we're near the rate limit."""
        return self.usage_percentage >= 80


@dataclass
class ServiceHealth:
    """Health metrics for a service."""
    service: str
    status: ServiceStatus
    last_check: datetime
    success_rate: float
    avg_response_time: float
    total_calls: int
    failed_calls: int
    rate_limit_hits: int
    quota_exhausted: bool = False


class APIMonitor:
    """Monitor API usage, rate limits, and service health."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.error_handler = get_error_handler()
        self.config_path = config_path or "logs/api_monitoring.json"
        
        # Storage for monitoring data
        self.api_calls: List[APICall] = []
        self.rate_limits: Dict[str, RateLimitInfo] = {}
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Configuration
        self.max_calls_to_store = 1000  # Keep last 1000 calls
        self.health_check_window = timedelta(hours=1)  # 1 hour window for health checks
        
        # Load existing data
        self._load_monitoring_data()
    
    def record_api_call(self, 
                       service: str,
                       endpoint: str,
                       response_time: float,
                       status_code: int,
                       success: bool,
                       error_message: Optional[str] = None,
                       rate_limit_headers: Optional[Dict[str, str]] = None) -> None:
        """
        Record an API call for monitoring.
        
        Args:
            service: Name of the service (e.g., 'hunter_io', 'notion')
            endpoint: API endpoint called
            response_time: Response time in seconds
            status_code: HTTP status code
            success: Whether the call was successful
            error_message: Error message if call failed
            rate_limit_headers: Rate limit headers from response
        """
        # Record the API call
        api_call = APICall(
            service=service,
            endpoint=endpoint,
            timestamp=datetime.now(),
            response_time=response_time,
            status_code=status_code,
            success=success,
            error_message=error_message
        )
        
        self.api_calls.append(api_call)
        
        # Keep only recent calls
        if len(self.api_calls) > self.max_calls_to_store:
            self.api_calls = self.api_calls[-self.max_calls_to_store:]
        
        # Update rate limit information if provided
        if rate_limit_headers:
            self._update_rate_limit_info(service, rate_limit_headers)
        
        # Update service health
        self._update_service_health(service)
        
        # Check for rate limit issues
        if status_code == 429:
            self.logger.warning(f"Rate limit hit for {service} on {endpoint}")
            self.error_handler.handle_error(
                Exception(f"Rate limit exceeded for {service}"),
                service=service,
                operation=endpoint,
                category=ErrorCategory.API_RATE_LIMIT
            )
        
        # Log slow responses
        if response_time > 10.0:  # Responses slower than 10 seconds
            self.logger.warning(f"Slow API response: {service}.{endpoint} took {response_time:.2f}s")
        
        # Save monitoring data periodically
        if len(self.api_calls) % 10 == 0:  # Save every 10 calls
            self._save_monitoring_data()
    
    def update_quota_usage(self, 
                          service: str,
                          quota_type: str,
                          used: int,
                          limit: int,
                          reset_time: datetime) -> None:
        """
        Update quota usage information.
        
        Args:
            service: Service name
            quota_type: Type of quota (e.g., 'monthly_requests', 'credits')
            used: Current usage
            limit: Quota limit
            reset_time: When quota resets
        """
        self.error_handler.update_service_quota(service, quota_type, used, limit, reset_time)
        
        # Update service health if quota is exhausted
        if used >= limit:
            if service in self.service_health:
                self.service_health[service].quota_exhausted = True
                self.service_health[service].status = ServiceStatus.UNHEALTHY
            
            self.logger.error(f"{service} quota exhausted: {used}/{limit} {quota_type}")
    
    def get_service_health(self, service: Optional[str] = None) -> Dict[str, ServiceHealth]:
        """
        Get health status for services.
        
        Args:
            service: Optional service name to filter by
            
        Returns:
            Dictionary of service health information
        """
        if service:
            return {service: self.service_health[service]} if service in self.service_health else {}
        return self.service_health.copy()
    
    def get_rate_limit_status(self, service: Optional[str] = None) -> Dict[str, RateLimitInfo]:
        """
        Get rate limit status for services.
        
        Args:
            service: Optional service name to filter by
            
        Returns:
            Dictionary of rate limit information
        """
        if service:
            return {k: v for k, v in self.rate_limits.items() if v.service == service}
        return self.rate_limits.copy()
    
    def get_api_metrics(self, service: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get API usage metrics for the specified time period.
        
        Args:
            service: Optional service name to filter by
            hours: Number of hours to look back
            
        Returns:
            Dictionary with API metrics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_calls = [call for call in self.api_calls if call.timestamp >= cutoff_time]
        
        if service:
            recent_calls = [call for call in recent_calls if call.service == service]
        
        if not recent_calls:
            return {
                'total_calls': 0,
                'success_rate': 0,
                'avg_response_time': 0,
                'error_rate': 0,
                'rate_limit_hits': 0
            }
        
        successful_calls = [call for call in recent_calls if call.success]
        failed_calls = [call for call in recent_calls if not call.success]
        rate_limit_hits = [call for call in recent_calls if call.status_code == 429]
        
        # Calculate metrics
        total_calls = len(recent_calls)
        success_rate = (len(successful_calls) / total_calls) * 100
        avg_response_time = sum(call.response_time for call in recent_calls) / total_calls
        error_rate = (len(failed_calls) / total_calls) * 100
        
        # Group by endpoint
        by_endpoint = {}
        for call in recent_calls:
            endpoint = call.endpoint
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = {'calls': 0, 'success': 0, 'avg_time': 0}
            
            by_endpoint[endpoint]['calls'] += 1
            if call.success:
                by_endpoint[endpoint]['success'] += 1
            by_endpoint[endpoint]['avg_time'] += call.response_time
        
        # Calculate averages for endpoints
        for endpoint_data in by_endpoint.values():
            endpoint_data['success_rate'] = (endpoint_data['success'] / endpoint_data['calls']) * 100
            endpoint_data['avg_time'] /= endpoint_data['calls']
        
        return {
            'total_calls': total_calls,
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'error_rate': error_rate,
            'rate_limit_hits': len(rate_limit_hits),
            'by_endpoint': by_endpoint,
            'time_period_hours': hours
        }
    
    def check_service_availability(self, service: str) -> ServiceStatus:
        """
        Check if a service is available based on recent API calls.
        
        Args:
            service: Service name to check
            
        Returns:
            ServiceStatus indicating availability
        """
        # Get recent calls for this service
        cutoff_time = datetime.now() - self.health_check_window
        recent_calls = [
            call for call in self.api_calls 
            if call.service == service and call.timestamp >= cutoff_time
        ]
        
        if not recent_calls:
            return ServiceStatus.UNKNOWN
        
        # Calculate success rate
        successful_calls = [call for call in recent_calls if call.success]
        success_rate = (len(successful_calls) / len(recent_calls)) * 100
        
        # Check for rate limit issues
        rate_limit_calls = [call for call in recent_calls if call.status_code == 429]
        rate_limit_percentage = (len(rate_limit_calls) / len(recent_calls)) * 100
        
        # Determine status
        if success_rate >= 95 and rate_limit_percentage < 5:
            return ServiceStatus.HEALTHY
        elif success_rate >= 80 and rate_limit_percentage < 20:
            return ServiceStatus.DEGRADED
        else:
            return ServiceStatus.UNHEALTHY
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive monitoring report.
        
        Returns:
            Dictionary with monitoring report
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'services': {},
            'overall_health': ServiceStatus.HEALTHY.value,
            'alerts': []
        }
        
        # Get metrics for each service
        services = set(call.service for call in self.api_calls[-100:])  # Last 100 calls
        
        for service in services:
            service_metrics = self.get_api_metrics(service, hours=24)
            service_health = self.get_service_health(service)
            rate_limits = self.get_rate_limit_status(service)
            quotas = self.error_handler.get_quota_status(service)
            
            report['services'][service] = {
                'metrics': service_metrics,
                'health': service_health.get(service, {}).status.value if service in service_health else 'unknown',
                'rate_limits': {k: asdict(v) for k, v in rate_limits.items()},
                'quotas': {k: asdict(v) for k, v in quotas.items()}
            }
            
            # Check for alerts
            if service in service_health:
                health = service_health[service]
                if health.status == ServiceStatus.UNHEALTHY:
                    report['alerts'].append(f"{service} is unhealthy")
                    report['overall_health'] = ServiceStatus.UNHEALTHY.value
                elif health.status == ServiceStatus.DEGRADED and report['overall_health'] == ServiceStatus.HEALTHY.value:
                    report['overall_health'] = ServiceStatus.DEGRADED.value
            
            # Check rate limits
            for rate_limit in rate_limits.values():
                if rate_limit.is_near_limit:
                    report['alerts'].append(f"{service} rate limit at {rate_limit.usage_percentage:.1f}%")
            
            # Check quotas
            for quota in quotas.values():
                if quota.is_exhausted:
                    report['alerts'].append(f"{service} quota exhausted")
                elif quota.is_near_limit:
                    report['alerts'].append(f"{service} quota at {quota.usage_percentage:.1f}%")
        
        return report
    
    def _update_rate_limit_info(self, service: str, headers: Dict[str, str]) -> None:
        """Update rate limit information from API response headers."""
        try:
            # Common rate limit header patterns
            limit = None
            remaining = None
            reset_time = None
            window_seconds = 3600  # Default 1 hour window
            
            # Try different header formats
            for limit_header in ['X-RateLimit-Limit', 'X-Rate-Limit-Limit', 'RateLimit-Limit']:
                if limit_header in headers:
                    limit = int(headers[limit_header])
                    break
            
            for remaining_header in ['X-RateLimit-Remaining', 'X-Rate-Limit-Remaining', 'RateLimit-Remaining']:
                if remaining_header in headers:
                    remaining = int(headers[remaining_header])
                    break
            
            for reset_header in ['X-RateLimit-Reset', 'X-Rate-Limit-Reset', 'RateLimit-Reset']:
                if reset_header in headers:
                    reset_timestamp = int(headers[reset_header])
                    reset_time = datetime.fromtimestamp(reset_timestamp)
                    break
            
            # If we have the necessary information, update rate limit
            if limit is not None and remaining is not None:
                if reset_time is None:
                    reset_time = datetime.now() + timedelta(seconds=window_seconds)
                
                rate_limit = RateLimitInfo(
                    service=service,
                    limit=limit,
                    remaining=remaining,
                    reset_time=reset_time,
                    window_seconds=window_seconds
                )
                
                self.rate_limits[service] = rate_limit
                
                if rate_limit.is_near_limit:
                    self.logger.warning(f"{service} rate limit at {rate_limit.usage_percentage:.1f}%")
                    
        except (ValueError, KeyError) as e:
            self.logger.debug(f"Could not parse rate limit headers for {service}: {e}")
    
    def _update_service_health(self, service: str) -> None:
        """Update service health based on recent API calls."""
        # Get recent calls for this service
        cutoff_time = datetime.now() - self.health_check_window
        recent_calls = [
            call for call in self.api_calls 
            if call.service == service and call.timestamp >= cutoff_time
        ]
        
        if not recent_calls:
            return
        
        # Calculate metrics
        total_calls = len(recent_calls)
        successful_calls = [call for call in recent_calls if call.success]
        failed_calls = [call for call in recent_calls if not call.success]
        rate_limit_hits = [call for call in recent_calls if call.status_code == 429]
        
        success_rate = (len(successful_calls) / total_calls) * 100
        avg_response_time = sum(call.response_time for call in recent_calls) / total_calls
        
        # Determine status
        status = self.check_service_availability(service)
        
        # Update or create service health record
        self.service_health[service] = ServiceHealth(
            service=service,
            status=status,
            last_check=datetime.now(),
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            total_calls=total_calls,
            failed_calls=len(failed_calls),
            rate_limit_hits=len(rate_limit_hits)
        )
    
    def _load_monitoring_data(self) -> None:
        """Load monitoring data from persistent storage."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Load recent API calls (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                for call_data in data.get('api_calls', []):
                    call_time = datetime.fromisoformat(call_data['timestamp'])
                    if call_time >= cutoff_time:
                        api_call = APICall(
                            service=call_data['service'],
                            endpoint=call_data['endpoint'],
                            timestamp=call_time,
                            response_time=call_data['response_time'],
                            status_code=call_data['status_code'],
                            success=call_data['success'],
                            error_message=call_data.get('error_message')
                        )
                        self.api_calls.append(api_call)
                
        except Exception as e:
            self.logger.warning(f"Failed to load monitoring data: {e}")
    
    def _save_monitoring_data(self) -> None:
        """Save monitoring data to persistent storage."""
        try:
            # Ensure directory exists
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Keep only recent calls (last 24 hours)
            cutoff_time = datetime.now() - timedelta(hours=24)
            recent_calls = [call for call in self.api_calls if call.timestamp >= cutoff_time]
            
            data = {
                'api_calls': [
                    {
                        'service': call.service,
                        'endpoint': call.endpoint,
                        'timestamp': call.timestamp.isoformat(),
                        'response_time': call.response_time,
                        'status_code': call.status_code,
                        'success': call.success,
                        'error_message': call.error_message
                    }
                    for call in recent_calls
                ],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Failed to save monitoring data: {e}")


# Global monitor instance
_global_api_monitor = None


def get_api_monitor() -> APIMonitor:
    """Get the global API monitor instance."""
    global _global_api_monitor
    if _global_api_monitor is None:
        _global_api_monitor = APIMonitor()
    return _global_api_monitor


def record_api_call(service: str,
                   endpoint: str,
                   response_time: float,
                   status_code: int,
                   success: bool,
                   error_message: Optional[str] = None,
                   rate_limit_headers: Optional[Dict[str, str]] = None) -> None:
    """Convenience function to record API calls using the global monitor."""
    get_api_monitor().record_api_call(
        service, endpoint, response_time, status_code, success, error_message, rate_limit_headers
    )