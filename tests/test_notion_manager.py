"""
Unit tests for NotionDataManager class.
"""
import pytest
from tests.test_utilities import TestUtilities
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from notion_client.errors import APIResponseError

from services.notion_manager import NotionDataManager
from models.data_models import Prospect, ProspectStatus, ValidationError
from utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.notion_token = "test_token"
    config.notion_database_id = "test_database_id"
    return config


@pytest.fixture
def sample_prospect():
    """Create a sample prospect for testing."""
    return Prospect(
        name="John Doe",
        role="Software Engineer",
        company="Test Company",
        linkedin_url="https://linkedin.com/in/johndoe",
        email="john@testcompany.com",
        source_url="https://producthunt.com/posts/test-product"
    )


@pytest.fixture
def notion_manager(mock_config):
    """Create NotionDataManager instance with mocked client."""
    with patch('services.notion_manager.Client') as mock_client:
        manager = NotionDataManager(mock_config)
        manager.client = mock_client.return_value
        return manager


class TestNotionDataManager:
    """Test cases for NotionDataManager class."""
    
    def test_init(self, mock_config):
        """Test NotionDataManager initialization."""
        with patch('services.notion_manager.Client') as mock_client:
            manager = NotionDataManager(mock_config)
            
            assert manager.config == mock_config
            assert manager.database_id == "test_database_id"
            mock_client.assert_called_once_with(auth="test_token")
    
    def test_create_prospect_database_success(self, notion_manager):
        """Test successful database creation."""
        # Mock the API response
        mock_response = {"id": "new_database_id"}
        notion_manager.client.databases.create.return_value = mock_response
        
        # Mock parent page search
        notion_manager.client.search.return_value = {
            "results": [{"id": "parent_page_id"}]
        }
        
        result = notion_manager.create_prospect_database()
        
        assert result == "new_database_id"
        assert notion_manager.database_id == "new_database_id"
        notion_manager.client.databases.create.assert_called_once()
    
    def test_create_prospect_database_api_error(self, notion_manager):
        """Test database creation with API error."""
        notion_manager.client.databases.create.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="invalid_request"
        )
        
        with pytest.raises(APIResponseError):
            notion_manager.create_prospect_database()
    
    def test_store_prospect_success(self, notion_manager, sample_prospect):
        """Test successful prospect storage."""
        # Mock duplicate check
        notion_manager.check_duplicate = Mock(return_value=False)
        
        # Mock API response
        mock_response = {"id": "page_id_123"}
        notion_manager.client.pages.create.return_value = mock_response
        
        result = notion_manager.store_prospect(sample_prospect)
        
        assert result == "page_id_123"
        assert sample_prospect.id == "page_id_123"
        notion_manager.client.pages.create.assert_called_once()
    
    def test_store_prospect_duplicate(self, notion_manager, sample_prospect):
        """Test prospect storage with duplicate detection."""
        # Mock duplicate check to return True
        notion_manager.check_duplicate = Mock(return_value=True)
        
        result = notion_manager.store_prospect(sample_prospect)
        
        assert result == ""
        notion_manager.client.pages.create.assert_not_called()
    
    def test_store_prospect_no_database_id(self, notion_manager, sample_prospect):
        """Test prospect storage without database ID."""
        notion_manager.database_id = None
        
        with pytest.raises(ValueError, match="Database ID not set"):
            notion_manager.store_prospect(sample_prospect)
    
    def test_store_prospect_validation_error(self, notion_manager):
        """Test prospect storage with invalid data."""
        # Create prospect with valid data first, then modify to invalid
        with pytest.raises(ValidationError):
            Prospect(
                name="",  # Invalid empty name
                role="Engineer",
                company="Test Company"
            )
    
    def test_store_prospects_multiple(self, notion_manager):
        """Test storing multiple prospects."""
        prospects = [
            Prospect(name="John Doe", role="Engineer", company="Company A"),
            Prospect(name="Jane Smith", role="Designer", company="Company B")
        ]
        
        # Mock store_prospect to return page IDs
        notion_manager.store_prospect = Mock(side_effect=["page_1", "page_2"])
        
        result = notion_manager.store_prospects(prospects)
        
        assert result == ["page_1", "page_2"]
        assert notion_manager.store_prospect.call_count == 2
    
    def test_store_prospects_with_errors(self, notion_manager):
        """Test storing multiple prospects with some errors."""
        prospects = [
            Prospect(name="John Doe", role="Engineer", company="Company A"),
            Prospect(name="Jane Smith", role="Designer", company="Company B")
        ]
        
        # Mock store_prospect to raise error for second prospect
        notion_manager.store_prospect = Mock(side_effect=["page_1", Exception("API Error")])
        
        result = notion_manager.store_prospects(prospects)
        
        assert result == ["page_1"]
        assert notion_manager.store_prospect.call_count == 2
    
    def test_get_prospects_success(self, notion_manager):
        """Test successful prospect retrieval."""
        # Mock API response
        mock_response = {
            "results": [
                {
                    "id": "page_1",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "John Doe"}}]},
                        "Role": {"rich_text": [{"text": {"content": "Engineer"}}]},
                        "Company": {"rich_text": [{"text": {"content": "Test Company"}}]},
                        "Status": {"select": {"name": "Not Contacted"}},
                        "Contacted": {"checkbox": False},
                        "Added Date": {"date": {"start": "2024-01-01T00:00:00"}}
                    }
                }
            ]
        }
        notion_manager.client.databases.query.return_value = mock_response
        
        result = notion_manager.get_prospects()
        
        assert len(result) == 1
        assert result[0].name == "John Doe"
        assert result[0].role == "Engineer"
        assert result[0].company == "Test Company"
        notion_manager.client.databases.query.assert_called_once()
    
    def test_get_prospects_with_filters(self, notion_manager):
        """Test prospect retrieval with filters."""
        filters = {"company": "Test Company", "status": "Not Contacted"}
        
        notion_manager.client.databases.query.return_value = {"results": []}
        
        notion_manager.get_prospects(filters)
        
        # Verify that filters were applied
        call_args = notion_manager.client.databases.query.call_args
        assert "filter" in call_args[1]
    
    def test_get_prospects_no_database_id(self, notion_manager):
        """Test prospect retrieval without database ID."""
        notion_manager.database_id = None
        
        with pytest.raises(ValueError, match="Database ID not set"):
            notion_manager.get_prospects()
    
    def test_update_prospect_status_success(self, notion_manager):
        """Test successful prospect status update."""
        notion_manager.client.pages.update.return_value = {}
        
        result = notion_manager.update_prospect_status(
            "page_123", 
            ProspectStatus.CONTACTED,
            contacted=True,
            notes="Sent initial email"
        )
        
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify the update payload
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        assert properties["Status"]["select"]["name"] == "Contacted"
        assert properties["Contacted"]["checkbox"] is True
        assert properties["Notes"]["rich_text"][0]["text"]["content"] == "Sent initial email"
    
    def test_update_prospect_status_api_error(self, notion_manager):
        """Test prospect status update with API error."""
        notion_manager.client.pages.update.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="invalid_request"
        )
        
        with pytest.raises(APIResponseError):
            notion_manager.update_prospect_status("page_123", ProspectStatus.CONTACTED)
    
    def test_check_duplicate_exists(self, notion_manager, sample_prospect):
        """Test duplicate check when duplicate exists."""
        # Mock API response with results
        mock_response = {"results": [{"id": "existing_page"}]}
        notion_manager.client.databases.query.return_value = mock_response
        
        result = notion_manager.check_duplicate(sample_prospect)
        
        assert result is True
        notion_manager.client.databases.query.assert_called_once()
    
    def test_check_duplicate_not_exists(self, notion_manager, sample_prospect):
        """Test duplicate check when no duplicate exists."""
        # Mock API response with no results
        mock_response = {"results": []}
        notion_manager.client.databases.query.return_value = mock_response
        
        result = notion_manager.check_duplicate(sample_prospect)
        
        assert result is False
        notion_manager.client.databases.query.assert_called_once()
    
    def test_check_duplicate_api_error(self, notion_manager, sample_prospect):
        """Test duplicate check with API error."""
        notion_manager.client.databases.query.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="invalid_request"
        )
        
        result = notion_manager.check_duplicate(sample_prospect)
        
        # Should return False on error to avoid blocking storage
        assert result is False
    
    def test_build_notion_filter(self, notion_manager):
        """Test Notion filter building."""
        filters = {
            "company": "Test Company",
            "status": "Contacted",
            "contacted": True
        }
        
        result = notion_manager._build_notion_filter(filters)
        
        assert "and" in result
        assert len(result["and"]) == 3
        
        # Check company filter
        company_filter = next(f for f in result["and"] if f["property"] == "Company")
        assert company_filter["rich_text"]["equals"] == "Test Company"
        
        # Check status filter
        status_filter = next(f for f in result["and"] if f["property"] == "Status")
        assert status_filter["select"]["equals"] == "Contacted"
        
        # Check contacted filter
        contacted_filter = next(f for f in result["and"] if f["property"] == "Contacted")
        assert contacted_filter["checkbox"]["equals"] is True
    
    def test_page_to_prospect_conversion(self, notion_manager):
        """Test conversion from Notion page to Prospect object."""
        page_data = {
            "id": "page_123",
            "properties": {
                "Name": {"title": [{"text": {"content": "John Doe"}}]},
                "Role": {"rich_text": [{"text": {"content": "Software Engineer"}}]},
                "Company": {"rich_text": [{"text": {"content": "Test Company"}}]},
                "LinkedIn": {"url": "https://linkedin.com/in/johndoe"},
                "Email": {"email": "john@testcompany.com"},
                "Contacted": {"checkbox": True},
                "Status": {"select": {"name": "Contacted"}},
                "Notes": {"rich_text": [{"text": {"content": "Great candidate"}}]},
                "Source": {"url": "https://producthunt.com/posts/test"},
                "Added Date": {"date": {"start": "2024-01-01T10:00:00Z"}}
            }
        }
        
        result = notion_manager._page_to_prospect(page_data)
        
        assert result.id == "page_123"
        assert result.name == "John Doe"
        assert result.role == "Software Engineer"
        assert result.company == "Test Company"
        assert result.linkedin_url == "https://linkedin.com/in/johndoe"
        assert result.email == "john@testcompany.com"
        assert result.contacted is True
        assert result.status == ProspectStatus.CONTACTED
        assert result.notes == "Great candidate"
        assert result.source_url == "https://producthunt.com/posts/test"
        assert isinstance(result.created_at, datetime)
    
    def test_extract_methods(self, notion_manager):
        """Test various property extraction methods."""
        # Test title extraction
        title_prop = {"title": [{"text": {"content": "Test Title"}}]}
        assert notion_manager._extract_title(title_prop) == "Test Title"
        assert notion_manager._extract_title({}) == ""
        
        # Test rich text extraction
        rich_text_prop = {"rich_text": [{"text": {"content": "Test Text"}}]}
        assert notion_manager._extract_rich_text(rich_text_prop) == "Test Text"
        assert notion_manager._extract_rich_text({}) == ""
        
        # Test URL extraction
        url_prop = {"url": "https://example.com"}
        assert notion_manager._extract_url(url_prop) == "https://example.com"
        assert notion_manager._extract_url({}) is None
        
        # Test email extraction
        email_prop = {"email": "test@example.com"}
        assert notion_manager._extract_email(email_prop) == "test@example.com"
        assert notion_manager._extract_email({}) is None
        
        # Test checkbox extraction
        checkbox_prop = {"checkbox": True}
        assert notion_manager._extract_checkbox(checkbox_prop) is True
        assert notion_manager._extract_checkbox({}) is False
        
        # Test select extraction
        select_prop = {"select": {"name": "Option 1"}}
        assert notion_manager._extract_select(select_prop) == "Option 1"
        assert notion_manager._extract_select({}) == ""
        
        # Test date extraction
        date_prop = {"date": {"start": "2024-01-01T10:00:00Z"}}
        result_date = notion_manager._extract_date(date_prop)
        assert isinstance(result_date, datetime)
        assert notion_manager._extract_date({}) is None
    
    def test_update_prospect_with_linkedin_data_success(self, notion_manager):
        """Test successful LinkedIn data update."""
        from services.linkedin_scraper import LinkedInProfile
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            company="Tech Corp",
            location="San Francisco, CA",
            summary="Experienced software engineer with 5+ years in web development",
            experience=["Software Engineer at StartupCo", "Junior Developer at WebDev Inc"],
            skills=["Python", "JavaScript", "React"],
            education=["BS Computer Science, University of California"]
        )
        
        notion_manager.client.pages.update.return_value = {}
        
        result = notion_manager.update_prospect_with_linkedin_data("page_123", linkedin_profile)
        
        assert result is True
        notion_manager.client.pages.update.assert_called_once()
        
        # Verify the update payload contains LinkedIn data
        call_args = notion_manager.client.pages.update.call_args
        properties = call_args[1]["properties"]
        
        assert "LinkedIn Summary" in properties
        assert properties["LinkedIn Summary"]["rich_text"][0]["text"]["content"] == linkedin_profile.summary
        
        assert "Experience" in properties
        assert "Software Engineer at StartupCo" in properties["Experience"]["rich_text"][0]["text"]["content"]
        
        assert "Skills" in properties
        assert "Python, JavaScript, React" == properties["Skills"]["rich_text"][0]["text"]["content"]
        
        assert "Education" in properties
        assert linkedin_profile.education[0] in properties["Education"]["rich_text"][0]["text"]["content"]
        
        assert "Location" in properties
        assert properties["Location"]["rich_text"][0]["text"]["content"] == linkedin_profile.location
    
    def test_update_prospect_with_linkedin_data_empty_profile(self, notion_manager):
        """Test LinkedIn data update with empty profile."""
        from services.linkedin_scraper import LinkedInProfile
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="",
            experience=[],
            skills=[],
            summary=""
        )
        
        result = notion_manager.update_prospect_with_linkedin_data("page_123", linkedin_profile)
        
        assert result is False
        notion_manager.client.pages.update.assert_not_called()
    
    def test_update_prospect_with_linkedin_data_api_error(self, notion_manager):
        """Test LinkedIn data update with API error."""
        from services.linkedin_scraper import LinkedInProfile
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="Engineer",
            experience=[],
            skills=[],
            summary="Test summary"
        )
        
        notion_manager.client.pages.update.side_effect = APIResponseError(
            response=Mock(), message="API Error", code="invalid_request"
        )
        
        with pytest.raises(APIResponseError):
            notion_manager.update_prospect_with_linkedin_data("page_123", linkedin_profile)
    
    def test_store_prospect_with_linkedin_data_success(self, notion_manager, sample_prospect):
        """Test successful prospect storage with LinkedIn data."""
        from services.linkedin_scraper import LinkedInProfile
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            company="Tech Corp",
            location="San Francisco, CA",
            summary="Experienced software engineer",
            experience=["Previous role at StartupCo"],
            skills=["Python", "JavaScript"],
            education=["BS Computer Science"]
        )
        
        # Mock duplicate check
        notion_manager.check_duplicate = Mock(return_value=False)
        
        # Mock API response
        mock_response = {"id": "page_id_123"}
        notion_manager.client.pages.create.return_value = mock_response
        
        result = notion_manager.store_prospect_with_linkedin_data(sample_prospect, linkedin_profile)
        
        assert result == "page_id_123"
        assert sample_prospect.id == "page_id_123"
        notion_manager.client.pages.create.assert_called_once()
        
        # Verify the creation payload contains LinkedIn data
        call_args = notion_manager.client.pages.create.call_args
        properties = call_args[1]["properties"]
        
        assert "LinkedIn Summary" in properties
        assert properties["LinkedIn Summary"]["rich_text"][0]["text"]["content"] == linkedin_profile.summary
        
        assert "Skills" in properties
        assert "Python, JavaScript" == properties["Skills"]["rich_text"][0]["text"]["content"]
        
        # Verify LinkedIn data overrides basic prospect data
        assert properties["Company"]["rich_text"][0]["text"]["content"] == "Tech Corp"
        assert properties["Role"]["rich_text"][0]["text"]["content"] == "Senior Software Engineer"
    
    def test_store_prospect_with_linkedin_data_no_linkedin_data(self, notion_manager, sample_prospect):
        """Test prospect storage with None LinkedIn data."""
        # Mock duplicate check
        notion_manager.check_duplicate = Mock(return_value=False)
        
        # Mock API response
        mock_response = {"id": "page_id_123"}
        notion_manager.client.pages.create.return_value = mock_response
        
        result = notion_manager.store_prospect_with_linkedin_data(sample_prospect, None)
        
        assert result == "page_id_123"
        notion_manager.client.pages.create.assert_called_once()
        
        # Verify no LinkedIn-specific fields are added
        call_args = notion_manager.client.pages.create.call_args
        properties = call_args[1]["properties"]
        
        assert "LinkedIn Summary" not in properties
        assert "Experience" not in properties
        assert "Skills" not in properties
    
    def test_store_prospect_with_linkedin_data_duplicate(self, notion_manager, sample_prospect):
        """Test prospect storage with LinkedIn data when duplicate exists."""
        from services.linkedin_scraper import LinkedInProfile
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="Engineer",
            experience=[],
            skills=[],
            summary="Test"
        )
        
        # Mock duplicate check to return True
        notion_manager.check_duplicate = Mock(return_value=True)
        
        result = notion_manager.store_prospect_with_linkedin_data(sample_prospect, linkedin_profile)
        
        assert result == ""
        notion_manager.client.pages.create.assert_not_called()