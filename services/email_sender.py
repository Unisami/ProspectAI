"""
Email sending service using Resend API for the job prospect automation system.
"""

import time
import logging
from datetime import (
    datetime,
    timedelta
)
from typing import (
    Dict,
    List,
    Optional,
    Any
)
from dataclasses import (
    asdict,
    dataclass,
    field
)
import re

import resend

from utils.config import Config

@dataclass
class SendResult:
    """Data model for email sending results."""
    email_id: str
    status: str
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    recipient_email: str = ""
    subject: str = ""


@dataclass
class DeliveryStatus:
    """Data model for email delivery status tracking."""
    email_id: str
    status: str  # sent, delivered, opened, clicked, bounced, complained
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SendingStats:
    """Data model for email sending statistics."""
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    total_complained: int = 0
    total_failed: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    
    def __post_init__(self):
        """Calculate rates after initialization."""
        self.calculate_rates()
    
    def calculate_rates(self) -> None:
        """Calculate delivery, open, click, and bounce rates."""
        if self.total_sent > 0:
            self.delivery_rate = self.total_delivered / self.total_sent
            self.bounce_rate = self.total_bounced / self.total_sent
        
        if self.total_delivered > 0:
            self.open_rate = self.total_opened / self.total_delivered
            
        if self.total_opened > 0:
            self.click_rate = self.total_clicked / self.total_opened


class EmailSenderError(Exception):
    """Custom exception for email sending errors."""
    pass


class EmailSender:
    """
    Email sending service using Resend API.
    
    Handles email sending, delivery tracking, bounce handling, and statistics.
    Implements rate limiting and retry mechanisms for reliable email delivery.
    """
    
    def __init__(self, config: Config, notion_manager=None):
        """
        Initialize the EmailSender with configuration.
        
        Args:
            config: Configuration object containing Resend API settings
            notion_manager: Optional NotionDataManager for email status tracking
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.notion_manager = notion_manager
        
        # Validate required configuration
        if not config.resend_api_key:
            raise EmailSenderError("Resend API key is required")
        if not config.sender_email:
            raise EmailSenderError("Sender email is required")
        if not config.sender_name:
            raise EmailSenderError("Sender name is required")
        
        # Initialize Resend client
        resend.api_key = config.resend_api_key
        
        # Rate limiting
        self.requests_per_minute = config.resend_requests_per_minute
        self.request_times: List[datetime] = []
        
        # Statistics tracking
        self.stats = SendingStats()
        self.delivery_statuses: Dict[str, DeliveryStatus] = {}
        
        self.logger.info("EmailSender initialized successfully")
    
    def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting for Resend API calls."""
        now = datetime.now()
        
        # Remove requests older than 1 minute
        self.request_times = [
            req_time for req_time in self.request_times 
            if now - req_time < timedelta(minutes=1)
        ]
        
        # Check if we're at the rate limit
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = min(self.request_times)
            wait_time = 60 - (now - oldest_request).total_seconds()
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                # Clean up old requests after waiting
                self.request_times = [
                    req_time for req_time in self.request_times 
                    if datetime.now() - req_time < timedelta(minutes=1)
                ]
        
        # Record this request
        self.request_times.append(now)
    
    def test_connection(self) -> bool:
        """
        Test the Resend API connection.
        
        Returns:
            True if connection is successful
            
        Raises:
            Exception if connection fails
        """
        try:
            # Test by getting API key info (this is a lightweight test)
            # Since Resend doesn't have a dedicated test endpoint, we'll try to send a test email
            # to a non-existent domain to test API connectivity without actually sending
            test_params = {
                "from": self.config.sender_email,
                "to": ["test@nonexistent-domain-for-testing.com"],
                "subject": "Connection Test",
                "text": "This is a connection test"
            }
            
            # This will fail due to invalid recipient, but will test API connectivity
            try:
                resend.Emails.send(test_params)
            except Exception as e:
                # If it's an API connectivity issue, re-raise
                if "api" in str(e).lower() or "auth" in str(e).lower() or "key" in str(e).lower():
                    raise Exception(f"Resend API connection failed: {str(e)}")
                # If it's just the invalid email (expected), connection is working
                return True
            
            return True
            
        except Exception as e:
            if "connection" in str(e).lower() or "network" in str(e).lower():
                raise Exception(f"Resend API connection failed: {str(e)}")
            # Re-raise if it's an authentication or API key issue
            raise
    
    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        tags: Optional[List[str]] = None,
        prospect_id: Optional[str] = None
    ) -> SendResult:
        """Send an email using Resend API."""
        try:
            # Check rate limiting
            self._check_rate_limit()
            
            # Validate inputs
            if not recipient_email or not recipient_email.strip():
                raise EmailSenderError("Recipient email cannot be empty")
            if not subject or not subject.strip():
                raise EmailSenderError("Subject cannot be empty")
            if not html_body or not html_body.strip():
                raise EmailSenderError("Email body cannot be empty")
            
            # Prepare email data
            email_params = {
                "from": f"{self.config.sender_name} <{self.config.sender_email}>",
                "to": [recipient_email],
                "subject": subject,
                "html": html_body,
            }
            
            # Add optional fields
            if text_body:
                email_params["text"] = text_body
            
            if self.config.reply_to_email:
                email_params["reply_to"] = [self.config.reply_to_email]
            
            # Note: Tags parameter causes validation error with current Resend API version
            # if tags:
            #     email_params["tags"] = tags
            
            # Send email via Resend
            self.logger.info(f"Sending email to {recipient_email} with subject: {subject}")
            self.logger.info(f"Email params keys: {list(email_params.keys())}")
            self.logger.info(f"From: {email_params.get('from')}")
            self.logger.info(f"To: {email_params.get('to')}")
            self.logger.info(f"Subject: {repr(email_params.get('subject'))}")
            self.logger.info(f"HTML length: {len(email_params.get('html', ''))}")
            
            try:
                response = resend.Emails.send(email_params)
                self.logger.info(f"Resend response: {response}")
                self.logger.info(f"Response type: {type(response)}")
                if hasattr(response, 'id'):
                    self.logger.info(f"Response ID: {response.id}")
                elif isinstance(response, dict):
                    self.logger.info(f"Response dict keys: {list(response.keys())}")
                    self.logger.info(f"Response dict: {response}")
            except Exception as e:
                self.logger.error(f"Resend API error: {str(e)}")
                self.logger.error(f"Error type: {type(e)}")
                raise
            
            # Create send result - handle both dict and object response formats
            if isinstance(response, dict):
                email_id = response.get('id', '')
            else:
                email_id = getattr(response, 'id', '')
            
            send_result = SendResult(
                email_id=email_id,
                status="sent",
                delivered_at=datetime.now(),
                recipient_email=recipient_email,
                subject=subject
            )
            
            # Update statistics
            self.stats.total_sent += 1
            
            # Track delivery status
            delivery_status = DeliveryStatus(
                email_id=email_id,
                status="sent",
                timestamp=datetime.now(),
                details={"recipient": recipient_email, "subject": subject}
            )
            self.delivery_statuses[email_id] = delivery_status
            
            # Update Notion database if notion_manager is available and prospect_id is provided
            if self.notion_manager and prospect_id:
                try:
                    # Update both old and new email status fields for compatibility
                    self.notion_manager.update_email_status(
                        prospect_id=prospect_id,
                        email_status="Sent",
                        email_id=email_id,
                        email_subject=subject
                    )
                    
                    # Update new delivery status tracking
                    self.notion_manager.update_email_delivery_status(
                        prospect_id=prospect_id,
                        delivery_status="Sent",
                        provider_id=email_id,
                        delivery_metadata={
                            'sent_at': datetime.now().isoformat(),
                            'recipient': recipient_email,
                            'subject': subject,
                            'provider': 'resend'
                        }
                    )
                    
                    self.logger.info(f"Updated Notion prospect {prospect_id} with email delivery status")
                except Exception as e:
                    self.logger.error(f"Failed to update Notion with email delivery info: {str(e)}")
            
            self.logger.info(f"Email sent successfully to {recipient_email}, ID: {email_id}")
            return send_result
            
        except Exception as e:
            error_msg = f"Failed to send email to {recipient_email}: {str(e)}"
            self.logger.error(error_msg)
            
            # Update failure statistics
            self.stats.total_failed += 1
            
            # Return failed result
            return SendResult(
                email_id="",
                status="failed",
                error_message=error_msg,
                recipient_email=recipient_email,
                subject=subject
            )
    
    def track_delivery(self, email_id: str) -> Optional[DeliveryStatus]:
        """Track delivery status of a sent email."""
        return self.delivery_statuses.get(email_id)
    
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """Handle webhook data from Resend for delivery status updates."""
        try:
            event_type = webhook_data.get("type")
            email_data = webhook_data.get("data", {})
            email_id = email_data.get("email_id")
            
            if not email_id:
                self.logger.warning("Webhook received without email_id")
                return
            
            # Map Resend webhook events to our status values
            status_mapping = {
                "email.sent": "sent",
                "email.delivered": "delivered",
                "email.delivery_delayed": "delayed",
                "email.complained": "complained",
                "email.bounced": "bounced",
                "email.opened": "opened",
                "email.clicked": "clicked"
            }
            
            status = status_mapping.get(event_type, "unknown")
            
            # Map to Notion status values
            notion_status_mapping = {
                "sent": "Sent",
                "delivered": "Delivered",
                "delayed": "Sent",  # Keep as Sent for delayed
                "complained": "Complained",
                "bounced": "Bounced",
                "opened": "Opened",
                "clicked": "Clicked"
            }
            
            notion_status = notion_status_mapping.get(status, "Sent")
            
            # Update delivery status
            delivery_status = DeliveryStatus(
                email_id=email_id,
                status=status,
                timestamp=datetime.now(),
                details=email_data
            )
            self.delivery_statuses[email_id] = delivery_status
            
            # Update Notion database if notion_manager is available
            if self.notion_manager:
                try:
                    prospect_id = self.notion_manager.get_prospect_by_email_id(email_id)
                    if prospect_id:
                        self.notion_manager.update_email_status(
                            prospect_id=prospect_id,
                            email_status=notion_status
                        )
                        self.logger.info(f"Updated Notion prospect {prospect_id} email status to {notion_status}")
                    else:
                        self.logger.warning(f"No prospect found for email ID {email_id}")
                except Exception as e:
                    self.logger.error(f"Failed to update Notion email status: {str(e)}")
            
            # Update statistics based on event type
            if event_type == "email.delivered":
                self.stats.total_delivered += 1
            elif event_type == "email.opened":
                self.stats.total_opened += 1
            elif event_type == "email.clicked":
                self.stats.total_clicked += 1
            elif event_type == "email.bounced":
                self.stats.total_bounced += 1
            elif event_type == "email.complained":
                self.stats.total_complained += 1
            
            # Recalculate rates
            self.stats.calculate_rates()
            
            self.logger.info(f"Updated delivery status for email {email_id}: {status}")
            
        except Exception as e:
            self.logger.error(f"Error handling webhook: {str(e)}")
    
    def handle_bounces(self, bounce_data: Dict[str, Any]) -> None:
        """Handle bounce notifications from Resend webhooks."""
        try:
            email_id = bounce_data.get("email_id")
            bounce_type = bounce_data.get("bounce_type", "unknown")
            recipient = bounce_data.get("recipient")
            
            self.logger.warning(
                f"Email bounce detected - ID: {email_id}, "
                f"Type: {bounce_type}, Recipient: {recipient}"
            )
            
            # Update delivery status
            if email_id:
                delivery_status = DeliveryStatus(
                    email_id=email_id,
                    status="bounced",
                    timestamp=datetime.now(),
                    details=bounce_data
                )
                self.delivery_statuses[email_id] = delivery_status
            
            # Update statistics
            self.stats.total_bounced += 1
            self.stats.calculate_rates()
            
        except Exception as e:
            self.logger.error(f"Error handling bounce: {str(e)}")
    
    def get_sending_stats(self) -> SendingStats:
        """Get current email sending statistics."""
        # Recalculate rates to ensure they're up to date
        self.stats.calculate_rates()
        return self.stats
    
    def reset_stats(self) -> None:
        """Reset email sending statistics."""
        self.stats = SendingStats()
        self.delivery_statuses.clear()
        self.logger.info("Email sending statistics reset")
    
    def get_delivery_report(self) -> Dict[str, Any]:
        """Get a comprehensive delivery report."""
        stats = self.get_sending_stats()
        
        # Get recent delivery statuses (last 100)
        recent_statuses = list(self.delivery_statuses.values())[-100:]
        
        # Calculate additional metrics
        status_breakdown = self._get_status_breakdown()
        performance_metrics = self._calculate_performance_metrics()
        
        return {
            "statistics": asdict(stats),
            "recent_deliveries": [asdict(status) for status in recent_statuses],
            "status_breakdown": status_breakdown,
            "performance_metrics": performance_metrics,
            "total_tracked_emails": len(self.delivery_statuses),
            "report_generated_at": datetime.now().isoformat()
        }
    
    def _get_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of email statuses."""
        breakdown = {}
        for status in self.delivery_statuses.values():
            breakdown[status.status] = breakdown.get(status.status, 0) + 1
        return breakdown
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate additional performance metrics."""
        if not self.delivery_statuses:
            return {}
        
        # Calculate average time to delivery (for delivered emails)
        delivered_emails = [
            status for status in self.delivery_statuses.values() 
            if status.status == "delivered"
        ]
        
        avg_delivery_time = None
        if delivered_emails:
            # This would require storing send time vs delivery time
            # For now, we'll just track the count
            avg_delivery_time = "Not available - requires send time tracking"
        
        # Calculate engagement metrics
        total_emails = len(self.delivery_statuses)
        engagement_rate = 0.0
        if total_emails > 0:
            engaged_emails = len([
                status for status in self.delivery_statuses.values()
                if status.status in ["opened", "clicked"]
            ])
            engagement_rate = engaged_emails / total_emails
        
        return {
            "average_delivery_time": avg_delivery_time,
            "engagement_rate": engagement_rate,
            "total_unique_recipients": len(set(
                status.details.get("recipient", "") 
                for status in self.delivery_statuses.values()
                if status.details.get("recipient")
            ))
        }
    
    def get_email_performance_by_prospect(self, prospect_id: str) -> Dict[str, Any]:
        """Get email performance metrics for a specific prospect."""
        if not self.notion_manager:
            return {"error": "Notion manager not available"}
        
        try:
            # Get prospect data from Notion
            prospect_data = self.notion_manager.get_prospect_data_for_email(prospect_id)
            if not prospect_data:
                return {"error": "Prospect not found"}
            
            # Find email statuses for this prospect
            prospect_emails = []
            for status in self.delivery_statuses.values():
                if status.details.get("prospect_id") == prospect_id:
                    prospect_emails.append(status)
            
            return {
                "prospect_name": prospect_data.get("name", "Unknown"),
                "prospect_email": prospect_data.get("email", "Unknown"),
                "total_emails_sent": len(prospect_emails),
                "email_statuses": [asdict(status) for status in prospect_emails],
                "latest_status": prospect_emails[-1].status if prospect_emails else "No emails sent"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting prospect email performance: {str(e)}")
            return {"error": str(e)}
    
    def validate_email_address(self, email: str) -> bool:
        """Validate email address format."""
        
        
        # Comprehensive email validation pattern
        email_pattern = (
            r'^[a-zA-Z0-9]'                           # Start with alphanumeric
            r'(?:[a-zA-Z0-9._%+-]*[a-zA-Z0-9])?'     # Local part (includes + character)
            r'@'                                      # @ symbol
            r'[a-zA-Z0-9]'                           # Domain must start with alphanumeric
            r'(?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?'        # Domain part with hyphens and dots
            r'\.[a-zA-Z]{2,}$'                       # TLD (at least 2 characters)
        )
        
        email = email.strip()
        
        # Check for consecutive dots anywhere in the email
        if '..' in email:
            return False
        
        # Check for dots at start or end of local part
        local_part = email.split('@')[0] if '@' in email else email
        if local_part.startswith('.') or local_part.endswith('.'):
            return False
        
        # Additional validation for @ symbol count
        if email.count('@') != 1:
            return False
        
        # Check if domain part exists and has proper structure
        if '@' in email:
            domain_part = email.split('@')[1]
            if domain_part.startswith('.') or domain_part.endswith('.') or domain_part.startswith('-') or domain_part.endswith('-'):
                return False
        
        return bool(re.match(email_pattern, email))
    def send_bulk_emails(
        self,
        email_list: List[Dict[str, str]],
        delay_between_emails: float = 1.0
    ) -> List[SendResult]:
        """Send multiple emails with rate limiting and delay."""
        results = []
        
        for i, email_data in enumerate(email_list):
            try:
                result = self.send_email(
                    recipient_email=email_data["recipient_email"],
                    subject=email_data["subject"],
                    html_body=email_data["html_body"],
                    text_body=email_data.get("text_body"),
                    tags=email_data.get("tags"),
                    prospect_id=email_data.get("prospect_id")
                )
                results.append(result)
                
                # Add delay between emails (except for the last one)
                if i < len(email_list) - 1:
                    time.sleep(delay_between_emails)
                    
            except Exception as e:
                self.logger.error(f"Error sending bulk email {i+1}: {str(e)}")
                results.append(SendResult(
                    email_id="",
                    status="failed",
                    error_message=str(e),
                    recipient_email=email_data.get("recipient_email", ""),
                    subject=email_data.get("subject", "")
                ))
        
        self.logger.info(f"Bulk email sending completed: {len(results)} emails processed")
        return results
