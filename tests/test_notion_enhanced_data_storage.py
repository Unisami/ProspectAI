"""
Unit tests for enhanced Notion data storage functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.notion_manager import NotionDataManager
from models.data_models import Prospect, ProspectStatus
from utils.config import Config
from notion_client.errors import APIResponseError


class TestNotionEnhancedDataStorage:
    """Test cases for enhanced Notion data storage methods."""
    
    @pytest.fixture
    def notion_manager(self, mock_config):
        """Create a NotionDataManager instance with mocked client."""
        with patch('services.notion_manager.Client') as mock_client:
            manager = NotionDataManager(mock_config)
            manager.client = mock_client.return_value
            return manager
    
    def test_store_ai_structured_data_success(self, notion_manager):
        """Test successful storage of AI-structured data."""
        # Arrange
        prospect_id = "test_prospect_id"
        product_summary = "AI-generated product summary for email personalization"
        business_insights = "Company metrics and growth indicators"
        linkedin_summary = "Structured LinkedIn profile insights"
        personalization_data = "Key points for email customization"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act
        result = notion_manager.store_ai_structured_data(
            prospect_id=prospect_id,
            product_summary=product_summary,
            business_insights=business_insights,
            linkedin_summary=linkedin_summary,
            personalization_data=personalization_data
        )
        
        # Assert
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify the properties passed to the update call
        call_args = notion_manager.client.pages.update.call_args
        assert call_args[1]["page_id"] == prospect_id
        
        properties = call_args[1]["properties"]
        assert properties["Product Summary"]["rich_text"][0]["text"]["content"] == product_summary
        assert properties["Business Insights"]["rich_text"][0]["text"]["content"] == business_insights
        assert properties["LinkedIn Summary"]["rich_text"][0]["text"]["content"] == linkedin_summary
        assert properties["Personalization Data"]["rich_text"][0]["text"]["content"] == personalization_data
        assert properties["AI Processing Status"]["select"]["name"] == "Completed"
        assert "AI Processing Date" in properties
    
    def test_store_ai_structured_data_partial(self, notion_manager):
        """Test storage of AI-structured data with only some fields."""
        # Arrange
        prospect_id = "test_prospect_id"
        product_summary = "AI-generated product summary"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act
        result = notion_manager.store_ai_structured_data(
            prospect_id=prospect_id,
            product_summary=product_summary
        )
        
        # Assert
        assert result is True
        
        # Verify only provided fields are included
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["Product Summary"]["rich_text"][0]["text"]["content"] == product_summary
        assert "Business Insights" not in properties
        assert "LinkedIn Summary" not in properties
        assert "Personalization Data" not in properties
        assert properties["AI Processing Status"]["select"]["name"] == "Completed"
    
    def test_store_ai_structured_data_no_data(self, notion_manager):
        """Test storage with no AI-structured data provided."""
        # Arrange
        prospect_id = "test_prospect_id"
        
        # Act
        result = notion_manager.store_ai_structured_data(prospect_id=prospect_id)
        
        # Assert
        assert result is False
        notion_manager.client.pages.update.assert_not_called()
    
    def test_store_ai_structured_data_api_error(self, notion_manager):
        """Test handling of API errors during AI data storage."""
        # Arrange
        prospect_id = "test_prospect_id"
        product_summary = "Test summary"
        
        notion_manager.client.pages.update.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="test_error"
        )
        
        # Act & Assert
        with pytest.raises(APIResponseError):
            notion_manager.store_ai_structured_data(
                prospect_id=prospect_id,
                product_summary=product_summary
            )
        
        # Verify error status update was attempted
        assert notion_manager.client.pages.update.call_count >= 1
    
    def test_get_prospect_data_for_email_success(self, notion_manager):
        """Test successful retrieval of prospect data for email generation."""
        # Arrange
        prospect_id = "test_prospect_id"
        mock_response = {
            "properties": {
                "Name": {"title": [{"text": {"content": "John Doe"}}]},
                "Role": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
                "Company": {"rich_text": [{"text": {"content": "TechCorp"}}]},
                "LinkedIn": {"url": "https://linkedin.com/in/johndoe"},
                "Email": {"email": "john@techcorp.com"},
                "Source": {"url": "https://producthunt.com/posts/techcorp"},
                "Product Summary": {"rich_text": [{"text": {"content": "AI product summary"}}]},
                "Business Insights": {"rich_text": [{"text": {"content": "Growth metrics"}}]},
                "LinkedIn Summary": {"rich_text": [{"text": {"content": "Profile insights"}}]},
                "Personalization Data": {"rich_text": [{"text": {"content": "Key points"}}]},
                "Market Analysis": {"rich_text": [{"text": {"content": "Market position"}}]},
                "Product Features": {"rich_text": [{"text": {"content": "Feature list"}}]},
                "Pricing Model": {"rich_text": [{"text": {"content": "Subscription"}}]},
                "Competitors": {"rich_text": [{"text": {"content": "Competitor list"}}]},
                "Experience": {"rich_text": [{"text": {"content": "Work experience"}}]},
                "Skills": {"rich_text": [{"text": {"content": "Technical skills"}}]},
                "Location": {"rich_text": [{"text": {"content": "San Francisco"}}]},
                "Notes": {"rich_text": [{"text": {"content": "Additional notes"}}]},
                "AI Processing Status": {"select": {"name": "Completed"}},
                "AI Processing Date": {"date": {"start": "2024-01-01T00:00:00"}}
            }
        }
        
        notion_manager.client.pages.retrieve.return_value = mock_response
        
        # Act
        result = notion_manager.get_prospect_data_for_email(prospect_id)
        
        # Assert
        assert result["name"] == "John Doe"
        assert result["role"] == "Software Engineer"
        assert result["company"] == "TechCorp"
        assert result["linkedin_url"] == "https://linkedin.com/in/johndoe"
        assert result["email"] == "john@techcorp.com"
        assert result["source_url"] == "https://producthunt.com/posts/techcorp"
        assert result["product_summary"] == "AI product summary"
        assert result["business_insights"] == "Growth metrics"
        assert result["linkedin_summary"] == "Profile insights"
        assert result["personalization_data"] == "Key points"
        assert result["market_analysis"] == "Market position"
        assert result["product_features"] == "Feature list"
        assert result["pricing_model"] == "Subscription"
        assert result["competitors"] == "Competitor list"
        assert result["experience"] == "Work experience"
        assert result["skills"] == "Technical skills"
        assert result["location"] == "San Francisco"
        assert result["notes"] == "Additional notes"
        assert result["ai_processing_status"] == "Completed"
        
        notion_manager.client.pages.retrieve.assert_called_once_with(page_id=prospect_id)
    
    def test_get_prospect_data_for_email_missing_fields(self, notion_manager):
        """Test retrieval with missing optional fields."""
        # Arrange
        prospect_id = "test_prospect_id"
        mock_response = {
            "properties": {
                "Name": {"title": [{"text": {"content": "Jane Smith"}}]},
                "Role": {"rich_text": [{"text": {"content": "Product Manager"}}]},
                "Company": {"rich_text": [{"text": {"content": "StartupCo"}}]},
                # Missing optional fields
            }
        }
        
        notion_manager.client.pages.retrieve.return_value = mock_response
        
        # Act
        result = notion_manager.get_prospect_data_for_email(prospect_id)
        
        # Assert
        assert result["name"] == "Jane Smith"
        assert result["role"] == "Product Manager"
        assert result["company"] == "StartupCo"
        assert result["linkedin_url"] == ""
        assert result["email"] == ""
        assert result["product_summary"] == ""
        assert result["business_insights"] == ""
        assert result["linkedin_summary"] == ""
        assert result["personalization_data"] == ""
    
    def test_get_prospect_data_for_email_api_error(self, notion_manager):
        """Test handling of API errors during data retrieval."""
        # Arrange
        prospect_id = "test_prospect_id"
        notion_manager.client.pages.retrieve.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="test_error"
        )
        
        # Act & Assert
        with pytest.raises(APIResponseError):
            notion_manager.get_prospect_data_for_email(prospect_id)
    
    def test_update_ai_processing_status_success(self, notion_manager):
        """Test successful update of AI processing status."""
        # Arrange
        prospect_id = "test_prospect_id"
        status = "Processing"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act
        result = notion_manager.update_ai_processing_status(prospect_id, status)
        
        # Assert
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["AI Processing Status"]["select"]["name"] == status
        assert "AI Processing Date" in properties
    
    def test_update_ai_processing_status_completed(self, notion_manager):
        """Test update to Completed status includes processing date."""
        # Arrange
        prospect_id = "test_prospect_id"
        status = "Completed"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act
        result = notion_manager.update_ai_processing_status(prospect_id, status)
        
        # Assert
        assert result is True
        
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["AI Processing Status"]["select"]["name"] == status
        assert "AI Processing Date" in properties
        assert "start" in properties["AI Processing Date"]["date"]
    
    def test_update_ai_processing_status_failed(self, notion_manager):
        """Test update to Failed status without processing date."""
        # Arrange
        prospect_id = "test_prospect_id"
        status = "Failed"
        
        notion_manager.client.pages.update.return_value = {"id": prospect_id}
        
        # Act
        result = notion_manager.update_ai_processing_status(prospect_id, status)
        
        # Assert
        assert result is True
        
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["AI Processing Status"]["select"]["name"] == status
        assert "AI Processing Date" not in properties
    
    def test_update_ai_processing_status_api_error(self, notion_manager):
        """Test handling of API errors during status update."""
        # Arrange
        prospect_id = "test_prospect_id"
        status = "Processing"
        
        notion_manager.client.pages.update.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="test_error"
        )
        
        # Act & Assert
        with pytest.raises(APIResponseError):
            notion_manager.update_ai_processing_status(prospect_id, status)
    
    def test_enhanced_database_schema_creation(self, notion_manager):
        """Test that enhanced database schema includes new AI fields."""
        # Arrange
        mock_response = {"id": "test_database_id"}
        notion_manager.client.databases.create.return_value = mock_response
        
        with patch.object(notion_manager, '_get_parent_page_id', return_value="parent_id"):
            # Act
            database_id = notion_manager.create_prospect_database()
            
            # Assert
            assert database_id == "test_database_id"
            
            call_args = notion_manager.client.databases.create.call_args
            properties = call_args[1]["properties"]
            
            # Verify enhanced fields are included
            assert "Personalization Data" in properties
            assert "AI Processing Status" in properties
            assert properties["AI Processing Status"]["select"]["options"] == [
                {"name": "Not Processed", "color": "gray"},
                {"name": "Processing", "color": "yellow"},
                {"name": "Completed", "color": "green"},
                {"name": "Failed", "color": "red"}
            ]
            
            # Verify existing AI fields are still present
            assert "Product Summary" in properties
            assert "Business Insights" in properties
            assert "LinkedIn Summary" in properties
            assert "AI Processing Date" in properties


if __name__ == "__main__":
    pytest.main([__file__])