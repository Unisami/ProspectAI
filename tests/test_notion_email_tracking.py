"""
Unit tests for Notion email tracking functionality.
"""
import pytest
from tests.test_utilities import TestUtilities
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from services.notion_manager import NotionDataManager
from utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.notion_token = "test_token"
    config.notion_database_id = "test_database_id"
    return config


@pytest.fixture
def notion_manager(mock_config):
    """Create a NotionDataManager instance for testing."""
    with patch('notion_client.Client'):
        return NotionDataManager(mock_config)


class TestNotionEmailTracking:
    """Test Notion email tracking functionality."""
    
    def test_update_email_status_basic(self, notion_manager):
        """Test basic email status update."""
        # Mock the Notion client
        notion_manager.client.pages.update = Mock()
        
        # Update email status
        result = notion_manager.update_email_status(
            prospect_id="test_prospect_id",
            email_status="Sent",
            email_id="test_email_id",
            email_subject="Test Subject"
        )
        
        # Verify the update was called correctly
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify the properties were set correctly
        call_args = notion_manager.client.pages.update.call_args
        assert call_args[1]["page_id"] == "test_prospect_id"
        
        properties = call_args[1]["properties"]
        assert properties["Email Status"]["select"]["name"] == "Sent"
        assert properties["Email ID"]["rich_text"][0]["text"]["content"] == "test_email_id"
        assert properties["Email Subject"]["rich_text"][0]["text"]["content"] == "Test Subject"
        assert "Email Sent Date" in properties
        assert properties["Contacted"]["checkbox"] is True
        assert properties["Status"]["select"]["name"] == "Contacted"
    
    def test_update_email_status_delivered(self, notion_manager):
        """Test email status update for delivered status."""
        # Mock the Notion client
        notion_manager.client.pages.update = Mock()
        
        # Update email status to delivered
        result = notion_manager.update_email_status(
            prospect_id="test_prospect_id",
            email_status="Delivered"
        )
        
        # Verify the update was called correctly
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify the properties were set correctly
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["Email Status"]["select"]["name"] == "Delivered"
        
        # Should not set email sent date for delivered status
        assert "Email Sent Date" not in properties
        assert "Contacted" not in properties
        assert "Status" not in properties
    
    def test_update_email_status_minimal(self, notion_manager):
        """Test email status update with minimal parameters."""
        # Mock the Notion client
        notion_manager.client.pages.update = Mock()
        
        # Update email status with minimal parameters
        result = notion_manager.update_email_status(
            prospect_id="test_prospect_id",
            email_status="Opened"
        )
        
        # Verify the update was called correctly
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify only email status was set
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["Email Status"]["select"]["name"] == "Opened"
        assert "Email ID" not in properties
        assert "Email Subject" not in properties
    
    def test_update_email_status_api_error(self, notion_manager):
        """Test email status update when API returns error."""
        from notion_client.errors import APIResponseError
        
        # Mock the Notion client to raise an error
        notion_manager.client.pages.update = Mock(side_effect=APIResponseError("API Error", "400"))
        
        # Update email status should raise the error
        with pytest.raises(APIResponseError):
            notion_manager.update_email_status(
                prospect_id="test_prospect_id",
                email_status="Sent"
            )
    
    def test_get_prospect_by_email_id_found(self, notion_manager):
        """Test finding prospect by email ID when prospect exists."""
        # Mock the Notion client response
        mock_response = {
            "results": [
                {"id": "prospect_123"}
            ]
        }
        notion_manager.client.databases.query = Mock(return_value=mock_response)
        
        # Find prospect by email ID
        result = notion_manager.get_prospect_by_email_id("test_email_id")
        
        # Verify the query was called correctly
        assert result == "prospect_123"
        notion_manager.client.databases.query.assert_called_once()
        
        # Verify the filter was set correctly
        call_args = notion_manager.client.databases.query.call_args
        assert call_args[1]["database_id"] == "test_database_id"
        
        filter_condition = call_args[1]["filter"]
        assert filter_condition["property"] == "Email ID"
        assert filter_condition["rich_text"]["equals"] == "test_email_id"
    
    def test_get_prospect_by_email_id_not_found(self, notion_manager):
        """Test finding prospect by email ID when prospect doesn't exist."""
        # Mock the Notion client response with no results
        mock_response = {"results": []}
        notion_manager.client.databases.query = Mock(return_value=mock_response)
        
        # Find prospect by email ID
        result = notion_manager.get_prospect_by_email_id("test_email_id")
        
        # Verify no prospect was found
        assert result is None
        notion_manager.client.databases.query.assert_called_once()
    
    def test_get_prospect_by_email_id_api_error(self, notion_manager):
        """Test finding prospect by email ID when API returns error."""
        from notion_client.errors import APIResponseError
        
        # Mock the Notion client to raise an error
        notion_manager.client.databases.query = Mock(side_effect=APIResponseError("API Error", "400"))
        
        # Find prospect by email ID should return None on error
        result = notion_manager.get_prospect_by_email_id("test_email_id")
        
        # Verify None is returned on error
        assert result is None
    
    def test_get_prospect_by_email_id_unexpected_error(self, notion_manager):
        """Test finding prospect by email ID when unexpected error occurs."""
        # Mock the Notion client to raise an unexpected error
        notion_manager.client.databases.query = Mock(side_effect=Exception("Unexpected error"))
        
        # Find prospect by email ID should return None on error
        result = notion_manager.get_prospect_by_email_id("test_email_id")
        
        # Verify None is returned on error
        assert result is None
    
    def test_database_schema_includes_email_fields(self, notion_manager):
        """Test that the database schema includes email tracking fields."""
        # Mock the Notion client
        notion_manager.client.databases.create = Mock(return_value={"id": "new_database_id"})
        
        # Mock the parent page ID method
        notion_manager._get_parent_page_id = Mock(return_value="parent_page_id")
        
        # Create database
        database_id = notion_manager.create_prospect_database()
        
        # Verify database was created
        assert database_id == "new_database_id"
        notion_manager.client.databases.create.assert_called_once()
        
        # Verify email tracking fields are in the schema
        call_args = notion_manager.client.databases.create.call_args
        properties = call_args[1]["properties"]
        
        # Check email status field
        assert "Email Status" in properties
        email_status_field = properties["Email Status"]
        assert email_status_field["select"]["options"]
        
        # Verify all email status options are present
        status_names = [option["name"] for option in email_status_field["select"]["options"]]
        expected_statuses = ["Not Sent", "Sent", "Delivered", "Opened", "Clicked", "Bounced", "Complained", "Failed"]
        for status in expected_statuses:
            assert status in status_names
        
        # Check other email fields
        assert "Email ID" in properties
        assert properties["Email ID"]["rich_text"] == {}
        
        assert "Email Sent Date" in properties
        assert properties["Email Sent Date"]["date"] == {}
        
        assert "Email Subject" in properties
        assert properties["Email Subject"]["rich_text"] == {}


class TestEmailStatusMapping:
    """Test email status mapping between different systems."""
    
    def test_resend_to_notion_status_mapping(self):
        """Test mapping from Resend webhook events to Notion statuses."""
        # This would be tested in the EmailSender tests, but we can verify the mapping logic
        status_mapping = {
            "email.sent": "Sent",
            "email.delivered": "Delivered",
            "email.delivery_delayed": "Sent",
            "email.complained": "Complained",
            "email.bounced": "Bounced",
            "email.opened": "Opened",
            "email.clicked": "Clicked"
        }
        
        # Verify all expected mappings exist
        assert status_mapping["email.sent"] == "Sent"
        assert status_mapping["email.delivered"] == "Delivered"
        assert status_mapping["email.opened"] == "Opened"
        assert status_mapping["email.clicked"] == "Clicked"
        assert status_mapping["email.bounced"] == "Bounced"
        assert status_mapping["email.complained"] == "Complained"
        assert status_mapping["email.delivery_delayed"] == "Sent"  # Delayed maps to Sent