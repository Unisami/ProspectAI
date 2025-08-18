"""
Unit tests for the EmailSender service.
"""
import pytest
from tests.test_utilities import TestUtilities
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from services.email_sender import EmailSender, EmailSenderError, SendResult, DeliveryStatus, SendingStats
from utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.resend_api_key = "test_api_key"
    config.sender_email = "test@example.com"
    config.sender_name = "Test Sender"
    config.reply_to_email = "reply@example.com"
    config.resend_requests_per_minute = 100
    return config


@pytest.fixture
def email_sender(mock_config):
    """Create an EmailSender instance for testing."""
    with patch('resend.api_key'):
        return EmailSender(mock_config)


class TestEmailSenderInitialization:
    """Test EmailSender initialization."""
    
    def test_init_success(self, mock_config):
        """Test successful initialization."""
        with patch('resend.api_key'):
            sender = EmailSender(mock_config)
            assert sender.config == mock_config
            assert sender.requests_per_minute == 100
            assert isinstance(sender.stats, SendingStats)
    
    def test_init_missing_api_key(self, mock_config):
        """Test initialization fails without API key."""
        mock_config.resend_api_key = None
        with pytest.raises(EmailSenderError, match="Resend API key is required"):
            EmailSender(mock_config)
    
    def test_init_missing_sender_email(self, mock_config):
        """Test initialization fails without sender email."""
        mock_config.sender_email = ""
        with pytest.raises(EmailSenderError, match="Sender email is required"):
            EmailSender(mock_config)
    
    def test_init_missing_sender_name(self, mock_config):
        """Test initialization fails without sender name."""
        mock_config.sender_name = ""
        with pytest.raises(EmailSenderError, match="Sender name is required"):
            EmailSender(mock_config)


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_check_under_limit(self, email_sender):
        """Test rate limiting when under the limit."""
        # Should not raise any exception
        email_sender._check_rate_limit()
        assert len(email_sender.request_times) == 1
    
    def test_rate_limit_check_at_limit(self, email_sender):
        """Test rate limiting when at the limit."""
        # Fill up the rate limit
        email_sender.requests_per_minute = 2
        email_sender.request_times = [datetime.now(), datetime.now()]
        
        # This should trigger a wait
        with patch('time.sleep') as mock_sleep:
            email_sender._check_rate_limit()
            mock_sleep.assert_called_once()
    
    def test_rate_limit_cleanup_old_requests(self, email_sender):
        """Test that old requests are cleaned up."""
        # Add old requests
        old_time = datetime.now() - timedelta(minutes=2)
        email_sender.request_times = [old_time, old_time]
        
        email_sender._check_rate_limit()
        
        # Old requests should be removed, new one added
        assert len(email_sender.request_times) == 1
        assert email_sender.request_times[0] > old_time


class TestEmailSending:
    """Test email sending functionality."""
    
    @patch('resend.Emails.send')
    def test_send_email_success(self, mock_send, email_sender):
        """Test successful email sending."""
        # Mock Resend response
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        result = email_sender.send_email(
            recipient_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>"
        )
        
        assert isinstance(result, SendResult)
        assert result.email_id == "test_email_id"
        assert result.status == "sent"
        assert result.recipient_email == "recipient@example.com"
        assert result.subject == "Test Subject"
        assert email_sender.stats.total_sent == 1
    
    @patch('resend.Emails.send')
    def test_send_email_with_optional_params(self, mock_send, email_sender):
        """Test email sending with optional parameters."""
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        result = email_sender.send_email(
            recipient_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
            text_body="Test Body",
            tags=["test", "automation"]
        )
        
        assert result.status == "sent"
        
        # Verify the call to Resend includes optional parameters
        call_args = mock_send.call_args[0][0]
        assert "text" in call_args
        assert "tags" in call_args
        assert call_args["tags"] == ["test", "automation"]
    
    def test_send_email_validation_errors(self, email_sender):
        """Test email sending validation errors."""
        # Empty recipient email
        result = email_sender.send_email("", "Subject", "<p>Body</p>")
        assert result.status == "failed"
        assert "Recipient email cannot be empty" in result.error_message
        
        # Empty subject
        result = email_sender.send_email("test@example.com", "", "<p>Body</p>")
        assert result.status == "failed"
        assert "Subject cannot be empty" in result.error_message
        
        # Empty body
        result = email_sender.send_email("test@example.com", "Subject", "")
        assert result.status == "failed"
        assert "Email body cannot be empty" in result.error_message
    
    @patch('resend.Emails.send')
    def test_send_email_api_error(self, mock_send, email_sender):
        """Test email sending when API returns error."""
        mock_send.side_effect = Exception("API Error")
        
        result = email_sender.send_email(
            recipient_email="recipient@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>"
        )
        
        assert result.status == "failed"
        assert "API Error" in result.error_message
        assert email_sender.stats.total_failed == 1


class TestDeliveryTracking:
    """Test delivery tracking functionality."""
    
    def test_track_delivery_existing_email(self, email_sender):
        """Test tracking delivery for existing email."""
        # Add a delivery status
        email_id = "test_email_id"
        status = DeliveryStatus(
            email_id=email_id,
            status="delivered",
            timestamp=datetime.now()
        )
        email_sender.delivery_statuses[email_id] = status
        
        result = email_sender.track_delivery(email_id)
        assert result == status
    
    def test_track_delivery_nonexistent_email(self, email_sender):
        """Test tracking delivery for non-existent email."""
        result = email_sender.track_delivery("nonexistent_id")
        assert result is None


class TestWebhookHandling:
    """Test webhook handling functionality."""
    
    def test_handle_webhook_delivered(self, email_sender):
        """Test handling delivered webhook."""
        webhook_data = {
            "type": "email.delivered",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com"
            }
        }
        
        email_sender.handle_webhook(webhook_data)
        
        # Check that delivery status was updated
        status = email_sender.delivery_statuses.get("test_email_id")
        assert status is not None
        assert status.status == "delivered"
        assert email_sender.stats.total_delivered == 1
    
    def test_handle_webhook_opened(self, email_sender):
        """Test handling opened webhook."""
        webhook_data = {
            "type": "email.opened",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com"
            }
        }
        
        email_sender.handle_webhook(webhook_data)
        
        status = email_sender.delivery_statuses.get("test_email_id")
        assert status.status == "opened"
        assert email_sender.stats.total_opened == 1
    
    def test_handle_webhook_bounced(self, email_sender):
        """Test handling bounced webhook."""
        webhook_data = {
            "type": "email.bounced",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com",
                "bounce_type": "hard"
            }
        }
        
        email_sender.handle_webhook(webhook_data)
        
        status = email_sender.delivery_statuses.get("test_email_id")
        assert status.status == "bounced"
        assert email_sender.stats.total_bounced == 1
    
    def test_handle_webhook_invalid_data(self, email_sender):
        """Test handling webhook with invalid data."""
        webhook_data = {
            "type": "email.delivered",
            "data": {}  # Missing email_id
        }
        
        # Should not raise exception, just log warning
        email_sender.handle_webhook(webhook_data)
        assert len(email_sender.delivery_statuses) == 0


class TestBounceHandling:
    """Test bounce handling functionality."""
    
    def test_handle_bounces(self, email_sender):
        """Test bounce handling."""
        bounce_data = {
            "email_id": "test_email_id",
            "bounce_type": "hard",
            "recipient": "test@example.com"
        }
        
        email_sender.handle_bounces(bounce_data)
        
        # Check that delivery status was updated
        status = email_sender.delivery_statuses.get("test_email_id")
        assert status is not None
        assert status.status == "bounced"
        assert email_sender.stats.total_bounced == 1


class TestStatistics:
    """Test statistics functionality."""
    
    def test_get_sending_stats(self, email_sender):
        """Test getting sending statistics."""
        # Manually set some stats
        email_sender.stats.total_sent = 10
        email_sender.stats.total_delivered = 8
        email_sender.stats.total_opened = 5
        email_sender.stats.total_clicked = 2
        
        stats = email_sender.get_sending_stats()
        
        assert stats.total_sent == 10
        assert stats.total_delivered == 8
        assert stats.delivery_rate == 0.8
        assert stats.open_rate == 0.625  # 5/8
        assert stats.click_rate == 0.4   # 2/5
    
    def test_reset_stats(self, email_sender):
        """Test resetting statistics."""
        # Set some stats
        email_sender.stats.total_sent = 10
        email_sender.delivery_statuses["test"] = DeliveryStatus(
            email_id="test",
            status="sent",
            timestamp=datetime.now()
        )
        
        email_sender.reset_stats()
        
        assert email_sender.stats.total_sent == 0
        assert len(email_sender.delivery_statuses) == 0
    
    def test_get_delivery_report(self, email_sender):
        """Test getting delivery report."""
        # Add some data
        email_sender.stats.total_sent = 5
        email_sender.delivery_statuses["test"] = DeliveryStatus(
            email_id="test",
            status="delivered",
            timestamp=datetime.now()
        )
        
        report = email_sender.get_delivery_report()
        
        assert "statistics" in report
        assert "recent_deliveries" in report
        assert "total_tracked_emails" in report
        assert "report_generated_at" in report
        assert report["total_tracked_emails"] == 1


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_validate_email_address_valid(self, email_sender):
        """Test email validation with valid addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        for email in valid_emails:
            assert email_sender.validate_email_address(email)
    
    def test_validate_email_address_invalid(self, email_sender):
        """Test email validation with invalid addresses."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            ""
        ]
        
        for email in invalid_emails:
            assert not email_sender.validate_email_address(email)
    
    @patch('resend.Emails.send')
    def test_send_bulk_emails(self, mock_send, email_sender):
        """Test bulk email sending."""
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        email_list = [
            {
                "recipient_email": "user1@example.com",
                "subject": "Subject 1",
                "html_body": "<p>Body 1</p>"
            },
            {
                "recipient_email": "user2@example.com",
                "subject": "Subject 2",
                "html_body": "<p>Body 2</p>"
            }
        ]
        
        with patch('time.sleep') as mock_sleep:
            results = email_sender.send_bulk_emails(email_list, delay_between_emails=0.5)
        
        assert len(results) == 2
        assert all(result.status == "sent" for result in results)
        mock_sleep.assert_called_once_with(0.5)  # Called once between emails
    
    @patch('resend.Emails.send')
    def test_send_bulk_emails_with_error(self, mock_send, email_sender):
        """Test bulk email sending with some failures."""
        # First email succeeds, second fails
        mock_response = Mock()
        mock_response.id = "test_id"
        mock_send.side_effect = [mock_response, Exception("API Error")]
        
        email_list = [
            {
                "recipient_email": "user1@example.com",
                "subject": "Subject 1",
                "html_body": "<p>Body 1</p>"
            },
            {
                "recipient_email": "user2@example.com",
                "subject": "Subject 2",
                "html_body": "<p>Body 2</p>"
            }
        ]
        
        results = email_sender.send_bulk_emails(email_list)
        
        assert len(results) == 2
        assert results[0].status == "sent"
        assert results[1].status == "failed"
        assert "API Error" in results[1].error_message


class TestSendingStatsCalculation:
    """Test SendingStats calculation methods."""
    
    def test_calculate_rates_with_data(self):
        """Test rate calculation with data."""
        stats = SendingStats(
            total_sent=100,
            total_delivered=90,
            total_opened=45,
            total_clicked=10,
            total_bounced=5
        )
        
        assert stats.delivery_rate == 0.9    # 90/100
        assert stats.open_rate == 0.5        # 45/90
        assert stats.click_rate == 0.22222222222222221  # 10/45 (approximately 0.22)
        assert stats.bounce_rate == 0.05     # 5/100
    
    def test_calculate_rates_with_zeros(self):
        """Test rate calculation with zero values."""
        stats = SendingStats()
        
        assert stats.delivery_rate == 0.0
        assert stats.open_rate == 0.0
        assert stats.click_rate == 0.0
        assert stats.bounce_rate == 0.0


class TestEnhancedDeliveryTracking:
    """Test enhanced delivery tracking functionality."""
    
    def test_get_status_breakdown(self, email_sender):
        """Test status breakdown calculation."""
        # Add some delivery statuses
        statuses = [
            DeliveryStatus("id1", "sent", datetime.now()),
            DeliveryStatus("id2", "delivered", datetime.now()),
            DeliveryStatus("id3", "opened", datetime.now()),
            DeliveryStatus("id4", "delivered", datetime.now()),
            DeliveryStatus("id5", "bounced", datetime.now())
        ]
        
        for status in statuses:
            email_sender.delivery_statuses[status.email_id] = status
        
        breakdown = email_sender._get_status_breakdown()
        
        assert breakdown["sent"] == 1
        assert breakdown["delivered"] == 2
        assert breakdown["opened"] == 1
        assert breakdown["bounced"] == 1
    
    def test_calculate_performance_metrics(self, email_sender):
        """Test performance metrics calculation."""
        # Add some delivery statuses
        statuses = [
            DeliveryStatus("id1", "sent", datetime.now(), {"recipient": "user1@example.com"}),
            DeliveryStatus("id2", "delivered", datetime.now(), {"recipient": "user2@example.com"}),
            DeliveryStatus("id3", "opened", datetime.now(), {"recipient": "user3@example.com"}),
            DeliveryStatus("id4", "clicked", datetime.now(), {"recipient": "user1@example.com"}),
        ]
        
        for status in statuses:
            email_sender.delivery_statuses[status.email_id] = status
        
        metrics = email_sender._calculate_performance_metrics()
        
        assert metrics["engagement_rate"] == 0.5  # 2 engaged out of 4 total
        assert metrics["total_unique_recipients"] == 3  # user1, user2, user3
        assert "average_delivery_time" in metrics
    
    def test_calculate_performance_metrics_empty(self, email_sender):
        """Test performance metrics with no data."""
        metrics = email_sender._calculate_performance_metrics()
        assert metrics == {}
    
    def test_enhanced_delivery_report(self, email_sender):
        """Test enhanced delivery report generation."""
        # Add some delivery statuses
        statuses = [
            DeliveryStatus("id1", "sent", datetime.now()),
            DeliveryStatus("id2", "delivered", datetime.now()),
            DeliveryStatus("id3", "opened", datetime.now())
        ]
        
        for status in statuses:
            email_sender.delivery_statuses[status.email_id] = status
        
        # Update stats
        email_sender.stats.total_sent = 3
        email_sender.stats.total_delivered = 1
        email_sender.stats.total_opened = 1
        
        report = email_sender.get_delivery_report()
        
        assert "statistics" in report
        assert "recent_deliveries" in report
        assert "status_breakdown" in report
        assert "performance_metrics" in report
        assert "total_tracked_emails" in report
        assert "report_generated_at" in report
        
        # Check status breakdown
        assert report["status_breakdown"]["sent"] == 1
        assert report["status_breakdown"]["delivered"] == 1
        assert report["status_breakdown"]["opened"] == 1
        
        assert report["total_tracked_emails"] == 3
    
    def test_get_email_performance_by_prospect_no_notion(self, email_sender):
        """Test prospect performance when Notion manager is not available."""
        result = email_sender.get_email_performance_by_prospect("prospect_123")
        assert result["error"] == "Notion manager not available"
    
    def test_get_email_performance_by_prospect_with_notion(self, mock_config):
        """Test prospect performance with Notion integration."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email = Mock(return_value={
            "name": "John Doe",
            "email": "john@example.com"
        })
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Add some delivery statuses for this prospect
        statuses = [
            DeliveryStatus("id1", "sent", datetime.now(), {"prospect_id": "prospect_123"}),
            DeliveryStatus("id2", "delivered", datetime.now(), {"prospect_id": "prospect_123"}),
            DeliveryStatus("id3", "opened", datetime.now(), {"prospect_id": "other_prospect"})
        ]
        
        for status in statuses:
            email_sender.delivery_statuses[status.email_id] = status
        
        result = email_sender.get_email_performance_by_prospect("prospect_123")
        
        assert result["prospect_name"] == "John Doe"
        assert result["prospect_email"] == "john@example.com"
        assert result["total_emails_sent"] == 2  # Only emails for this prospect
        assert result["latest_status"] == "delivered"
        assert len(result["email_statuses"]) == 2
    
    def test_get_email_performance_prospect_not_found(self, mock_config):
        """Test prospect performance when prospect is not found."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email = Mock(return_value=None)
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        result = email_sender.get_email_performance_by_prospect("nonexistent_prospect")
        assert result["error"] == "Prospect not found"
    
    def test_get_email_performance_notion_error(self, mock_config):
        """Test prospect performance when Notion throws an error."""
        # Mock Notion manager with error
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email = Mock(side_effect=Exception("Notion error"))
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        result = email_sender.get_email_performance_by_prospect("prospect_123")
        assert "error" in result
        assert "Notion error" in result["error"]


class TestEmailDeliveryTracking:
    """Test email delivery tracking with Notion integration."""
    
    @patch('resend.Emails.send')
    def test_send_email_with_notion_integration(self, mock_send, mock_config):
        """Test email sending with Notion integration."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.update_email_status = Mock()
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Mock Resend response
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        # Send email with prospect ID
        result = email_sender.send_email(
            recipient_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
            prospect_id="prospect_123"
        )
        
        # Verify email was sent
        assert result.status == "sent"
        assert result.email_id == "test_email_id"
        
        # Verify Notion was updated
        mock_notion_manager.update_email_status.assert_called_once_with(
            prospect_id="prospect_123",
            email_status="Sent",
            email_id="test_email_id",
            email_subject="Test Subject"
        )
    
    @patch('resend.Emails.send')
    def test_send_email_without_notion_integration(self, mock_send, mock_config):
        """Test email sending without Notion integration."""
        # Create EmailSender without Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config)
        
        # Mock Resend response
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        # Send email with prospect ID (should not fail even without Notion manager)
        result = email_sender.send_email(
            recipient_email="test@example.com",
            subject="Test Subject",
            html_body="<p>Test Body</p>",
            prospect_id="prospect_123"
        )
        
        # Verify email was sent
        assert result.status == "sent"
        assert result.email_id == "test_email_id"
    
    def test_handle_webhook_with_notion_integration(self, mock_config):
        """Test webhook handling with Notion integration."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_by_email_id = Mock(return_value="prospect_123")
        mock_notion_manager.update_email_status = Mock()
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Test webhook data
        webhook_data = {
            "type": "email.delivered",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com"
            }
        }
        
        # Handle webhook
        email_sender.handle_webhook(webhook_data)
        
        # Verify Notion was queried and updated
        mock_notion_manager.get_prospect_by_email_id.assert_called_once_with("test_email_id")
        mock_notion_manager.update_email_status.assert_called_once_with(
            prospect_id="prospect_123",
            email_status="Delivered"
        )
        
        # Verify statistics were updated
        assert email_sender.stats.total_delivered == 1
    
    def test_handle_webhook_prospect_not_found(self, mock_config):
        """Test webhook handling when prospect is not found in Notion."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_by_email_id = Mock(return_value=None)
        mock_notion_manager.update_email_status = Mock()
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Test webhook data
        webhook_data = {
            "type": "email.opened",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com"
            }
        }
        
        # Handle webhook
        email_sender.handle_webhook(webhook_data)
        
        # Verify Notion was queried but not updated
        mock_notion_manager.get_prospect_by_email_id.assert_called_once_with("test_email_id")
        mock_notion_manager.update_email_status.assert_not_called()
        
        # Verify statistics were still updated
        assert email_sender.stats.total_opened == 1
    
    def test_handle_webhook_notion_error(self, mock_config):
        """Test webhook handling when Notion update fails."""
        # Mock Notion manager with error
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_by_email_id = Mock(return_value="prospect_123")
        mock_notion_manager.update_email_status = Mock(side_effect=Exception("Notion error"))
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Test webhook data
        webhook_data = {
            "type": "email.clicked",
            "data": {
                "email_id": "test_email_id",
                "recipient": "test@example.com"
            }
        }
        
        # Handle webhook (should not raise exception)
        email_sender.handle_webhook(webhook_data)
        
        # Verify Notion was attempted to be updated
        mock_notion_manager.get_prospect_by_email_id.assert_called_once_with("test_email_id")
        mock_notion_manager.update_email_status.assert_called_once()
        
        # Verify statistics were still updated despite Notion error
        assert email_sender.stats.total_clicked == 1
    
    def test_webhook_status_mapping(self, mock_config):
        """Test that webhook events are correctly mapped to Notion statuses."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_by_email_id = Mock(return_value="prospect_123")
        mock_notion_manager.update_email_status = Mock()
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Test different webhook events
        test_cases = [
            ("email.sent", "Sent"),
            ("email.delivered", "Delivered"),
            ("email.opened", "Opened"),
            ("email.clicked", "Clicked"),
            ("email.bounced", "Bounced"),
            ("email.complained", "Complained"),
            ("email.delivery_delayed", "Sent")  # Delayed maps to Sent
        ]
        
        for event_type, expected_status in test_cases:
            mock_notion_manager.reset_mock()
            
            webhook_data = {
                "type": event_type,
                "data": {
                    "email_id": f"test_email_id_{event_type}",
                    "recipient": "test@example.com"
                }
            }
            
            email_sender.handle_webhook(webhook_data)
            
            # Verify correct status was used
            mock_notion_manager.update_email_status.assert_called_once_with(
                prospect_id="prospect_123",
                email_status=expected_status
            )
    
    @patch('resend.Emails.send')
    def test_send_bulk_emails_with_prospect_ids(self, mock_send, mock_config):
        """Test bulk email sending with prospect IDs."""
        # Mock Notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.update_email_status = Mock()
        
        # Create EmailSender with Notion manager
        with patch('resend.api_key'):
            email_sender = EmailSender(mock_config, notion_manager=mock_notion_manager)
        
        # Mock Resend response
        mock_response = Mock()
        mock_response.id = "test_email_id"
        mock_send.return_value = mock_response
        
        # Email list with prospect IDs
        email_list = [
            {
                "recipient_email": "user1@example.com",
                "subject": "Subject 1",
                "html_body": "<p>Body 1</p>",
                "prospect_id": "prospect_1"
            },
            {
                "recipient_email": "user2@example.com",
                "subject": "Subject 2",
                "html_body": "<p>Body 2</p>",
                "prospect_id": "prospect_2"
            }
        ]
        
        with patch('time.sleep'):
            results = email_sender.send_bulk_emails(email_list)
        
        # Verify all emails were sent
        assert len(results) == 2
        assert all(result.status == "sent" for result in results)
        
        # Verify Notion was updated for each email
        assert mock_notion_manager.update_email_status.call_count == 2
        
        # Verify correct prospect IDs were used
        calls = mock_notion_manager.update_email_status.call_args_list
        assert calls[0][1]["prospect_id"] == "prospect_1"
        assert calls[1][1]["prospect_id"] == "prospect_2"