"""
Integration tests for enhanced Notion data storage functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.notion_manager import NotionDataManager
from models.data_models import Prospect, ProspectStatus
from utils.config import Config
from notion_client.errors import APIResponseError


class TestNotionIntegrationEnhanced:
    """Integration test cases for enhanced Notion data storage workflow."""
    
    @pytest.fixture
    def notion_manager(self, mock_config):
        """Create a NotionDataManager instance with mocked client."""
        with patch('services.notion_manager.Client') as mock_client:
            manager = NotionDataManager(mock_config)
            manager.client = mock_client.return_value
            return manager
    
    @pytest.fixture
    def sample_prospect(self):
        """Create a sample prospect for testing."""
        return Prospect(
            name="John Doe",
            role="Software Engineer",
            company="TechCorp",
            linkedin_url="https://linkedin.com/in/johndoe",
            email="john@techcorp.com",
            source_url="https://producthunt.com/posts/techcorp"
        )
    
    def test_complete_workflow_prospect_to_email_data(self, notion_manager, sample_prospect):
        """Test complete workflow from storing prospect to retrieving email data."""
        # Arrange
        prospect_id = "test_prospect_id"
        
        # Mock prospect storage
        notion_manager.client.pages.create.return_value = {"id": prospect_id}
        notion_manager.client.databases.query.return_value = {"results": []}  # No duplicates
        
        # Mock AI data storage
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Mock data retrieval for email
        mock_response = {
            "properties": {
                "Name": {"title": [{"text": {"content": "John Doe"}}]},
                "Role": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
                "Company": {"rich_text": [{"text": {"content": "TechCorp"}}]},
                "LinkedIn": {"url": "https://linkedin.com/in/johndoe"},
                "Email": {"email": "john@techcorp.com"},
                "Source": {"url": "https://producthunt.com/posts/techcorp"},
                "Product Summary": {"rich_text": [{"text": {"content": "AI-generated product summary"}}]},
                "Business Insights": {"rich_text": [{"text": {"content": "Growth metrics and funding info"}}]},
                "LinkedIn Summary": {"rich_text": [{"text": {"content": "Profile insights for personalization"}}]},
                "Personalization Data": {"rich_text": [{"text": {"content": "Key talking points"}}]},
                "AI Processing Status": {"select": {"name": "Completed"}},
                "AI Processing Date": {"date": {"start": "2024-01-01T00:00:00"}}
            }
        }
        notion_manager.client.pages.retrieve.return_value = mock_response
        
        # Act - Step 1: Store prospect
        stored_id = notion_manager.store_prospect(sample_prospect)
        
        # Act - Step 2: Store AI-structured data
        ai_result = notion_manager.store_ai_structured_data(
            prospect_id=stored_id,
            product_summary="AI-generated product summary",
            business_insights="Growth metrics and funding info",
            linkedin_summary="Profile insights for personalization",
            personalization_data="Key talking points"
        )
        
        # Act - Step 3: Retrieve data for email generation
        email_data = notion_manager.get_prospect_data_for_email(stored_id)
        
        # Assert
        assert stored_id == prospect_id
        assert ai_result is True
        assert email_data["name"] == "John Doe"
        assert email_data["role"] == "Software Engineer"
        assert email_data["company"] == "TechCorp"
        assert email_data["product_summary"] == "AI-generated product summary"
        assert email_data["business_insights"] == "Growth metrics and funding info"
        assert email_data["linkedin_summary"] == "Profile insights for personalization"
        assert email_data["personalization_data"] == "Key talking points"
        assert email_data["ai_processing_status"] == "Completed"
        
        # Verify method calls
        notion_manager.client.pages.create.assert_called_once()
        notion_manager.client.pages.update.assert_called_once()
        notion_manager.client.pages.retrieve.assert_called_once_with(page_id=prospect_id)
        
        # Verify prospect creation includes new fields
        create_call_args = notion_manager.client.pages.create.call_args
        properties = create_call_args[1]["properties"]
        assert properties["AI Processing Status"]["select"]["name"] == "Not Processed"
        assert properties["Email Status"]["select"]["name"] == "Not Sent"
    
    def test_ai_processing_status_workflow(self, notion_manager):
        """Test AI processing status workflow from start to completion."""
        # Arrange
        prospect_id = "test_prospect_id"
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act - Step 1: Set status to Processing
        result1 = notion_manager.update_ai_processing_status(prospect_id, "Processing")
        
        # Act - Step 2: Store AI data (should set to Completed)
        result2 = notion_manager.store_ai_structured_data(
            prospect_id=prospect_id,
            product_summary="Test summary"
        )
        
        # Assert
        assert result1 is True
        assert result2 is True
        
        # Verify status updates
        assert notion_manager.client.pages.update.call_count == 2
        
        # Check first call (Processing status)
        first_call = notion_manager.client.pages.update.call_args_list[0]
        first_properties = first_call[1]["properties"]
        assert first_properties["AI Processing Status"]["select"]["name"] == "Processing"
        assert "AI Processing Date" in first_properties
        
        # Check second call (Completed status via store_ai_structured_data)
        second_call = notion_manager.client.pages.update.call_args_list[1]
        second_properties = second_call[1]["properties"]
        assert second_properties["AI Processing Status"]["select"]["name"] == "Completed"
        assert second_properties["Product Summary"]["rich_text"][0]["text"]["content"] == "Test summary"
    
    def test_email_status_tracking_integration(self, notion_manager):
        """Test email status tracking integration with prospect data."""
        # Arrange
        prospect_id = "test_prospect_id"
        email_id = "email_123"
        email_subject = "Exciting opportunity at TechCorp"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        notion_manager.client.databases.query.return_value = {
            "results": [{"id": prospect_id}]
        }
        
        # Act - Update email status to Sent
        result1 = notion_manager.update_email_status(
            prospect_id=prospect_id,
            email_status="Sent",
            email_id=email_id,
            email_subject=email_subject
        )
        
        # Act - Find prospect by email ID
        found_id = notion_manager.get_prospect_by_email_id(email_id)
        
        # Assert
        assert result1 is True
        assert found_id == prospect_id
        
        # Verify email status update
        update_call_args = notion_manager.client.pages.update.call_args
        properties = update_call_args[1]["properties"]
        assert properties["Email Status"]["select"]["name"] == "Sent"
        assert properties["Email ID"]["rich_text"][0]["text"]["content"] == email_id
        assert properties["Email Subject"]["rich_text"][0]["text"]["content"] == email_subject
        assert properties["Contacted"]["checkbox"] is True
        assert properties["Status"]["select"]["name"] == "Contacted"
        assert "Email Sent Date" in properties
        
        # Verify search by email ID
        query_call_args = notion_manager.client.databases.query.call_args
        filter_conditions = query_call_args[1]["filter"]
        assert filter_conditions["property"] == "Email ID"
        assert filter_conditions["rich_text"]["equals"] == email_id
    
    def test_error_handling_in_workflow(self, notion_manager, sample_prospect):
        """Test error handling throughout the enhanced workflow."""
        # Arrange
        prospect_id = "test_prospect_id"
        
        # Mock successful prospect creation
        notion_manager.client.pages.create.return_value = {"id": prospect_id}
        notion_manager.client.databases.query.return_value = {"results": []}
        
        # Mock API error during AI data storage
        notion_manager.client.pages.update.side_effect = [
            APIResponseError(response=Mock(), message="API Error", code="test_error"),
            {"id": prospect_id}  # Second call for error status update
        ]
        
        # Act - Store prospect (should succeed)
        stored_id = notion_manager.store_prospect(sample_prospect)
        
        # Act - Try to store AI data (should fail and update status)
        with pytest.raises(APIResponseError):
            notion_manager.store_ai_structured_data(
                prospect_id=stored_id,
                product_summary="Test summary"
            )
        
        # Assert
        assert stored_id == prospect_id
        
        # Verify error status was attempted to be set
        assert notion_manager.client.pages.update.call_count == 2
        
        # Check that error status update was attempted
        error_status_call = notion_manager.client.pages.update.call_args_list[1]
        error_properties = error_status_call[1]["properties"]
        assert error_properties["AI Processing Status"]["select"]["name"] == "Failed"
    
    def test_data_consistency_across_operations(self, notion_manager):
        """Test data consistency across multiple operations."""
        # Arrange
        prospect_id = "test_prospect_id"
        
        # Mock all operations
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Mock retrieval with comprehensive data
        mock_response = {
            "properties": {
                "Name": {"title": [{"text": {"content": "Jane Smith"}}]},
                "Role": {"rich_text": [{"text": {"content": "Product Manager"}}]},
                "Company": {"rich_text": [{"text": {"content": "StartupCo"}}]},
                "Product Summary": {"rich_text": [{"text": {"content": "Innovative SaaS platform"}}]},
                "Business Insights": {"rich_text": [{"text": {"content": "Series A funded, 50+ employees"}}]},
                "LinkedIn Summary": {"rich_text": [{"text": {"content": "5+ years PM experience"}}]},
                "Personalization Data": {"rich_text": [{"text": {"content": "Focus on product-market fit"}}]},
                "AI Processing Status": {"select": {"name": "Completed"}},
                "Email Status": {"select": {"name": "Sent"}}
            }
        }
        notion_manager.client.pages.retrieve.return_value = mock_response
        
        # Act - Perform multiple operations
        ai_result = notion_manager.store_ai_structured_data(
            prospect_id=prospect_id,
            product_summary="Innovative SaaS platform",
            business_insights="Series A funded, 50+ employees",
            linkedin_summary="5+ years PM experience",
            personalization_data="Focus on product-market fit"
        )
        
        email_result = notion_manager.update_email_status(
            prospect_id=prospect_id,
            email_status="Sent",
            email_id="email_456"
        )
        
        email_data = notion_manager.get_prospect_data_for_email(prospect_id)
        
        # Assert
        assert ai_result is True
        assert email_result is True
        assert email_data["name"] == "Jane Smith"
        assert email_data["product_summary"] == "Innovative SaaS platform"
        assert email_data["business_insights"] == "Series A funded, 50+ employees"
        assert email_data["linkedin_summary"] == "5+ years PM experience"
        assert email_data["personalization_data"] == "Focus on product-market fit"
        assert email_data["ai_processing_status"] == "Completed"
        
        # Verify all operations were called
        assert notion_manager.client.pages.update.call_count == 2
        notion_manager.client.pages.retrieve.assert_called_once_with(page_id=prospect_id)
    
    def test_enhanced_database_schema_workflow(self, notion_manager):
        """Test that enhanced database schema supports the complete workflow."""
        # Arrange
        mock_response = {"id": "test_database_id"}
        notion_manager.client.databases.create.return_value = mock_response
        
        with patch.object(notion_manager, '_get_parent_page_id', return_value="parent_id"):
            # Act
            database_id = notion_manager.create_prospect_database()
            
            # Assert
            assert database_id == "test_database_id"
            
            # Verify enhanced schema includes all required fields
            call_args = notion_manager.client.databases.create.call_args
            properties = call_args[1]["properties"]
            
            # Check core fields
            assert "Name" in properties
            assert "Role" in properties
            assert "Company" in properties
            assert "Email" in properties
            assert "LinkedIn" in properties
            
            # Check AI-structured data fields
            assert "Product Summary" in properties
            assert "Business Insights" in properties
            assert "LinkedIn Summary" in properties
            assert "Personalization Data" in properties
            
            # Check status tracking fields
            assert "AI Processing Status" in properties
            assert "AI Processing Date" in properties
            assert "Email Status" in properties
            assert "Email ID" in properties
            assert "Email Sent Date" in properties
            assert "Email Subject" in properties
            
            # Verify status options
            ai_status_options = properties["AI Processing Status"]["select"]["options"]
            ai_status_names = [opt["name"] for opt in ai_status_options]
            assert "Not Processed" in ai_status_names
            assert "Processing" in ai_status_names
            assert "Completed" in ai_status_names
            assert "Failed" in ai_status_names
            
            email_status_options = properties["Email Status"]["select"]["options"]
            email_status_names = [opt["name"] for opt in email_status_options]
            assert "Not Sent" in email_status_names
            assert "Sent" in email_status_names
            assert "Delivered" in email_status_names
            assert "Opened" in email_status_names


if __name__ == "__main__":
    pytest.main([__file__])