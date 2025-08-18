"""
Tests for LinkedIn scraper functionality.
"""

import pytest
from tests.test_utilities import TestUtilities
from unittest.mock import Mock, patch, MagicMock
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException, NoSuchElementException

from services.linkedin_scraper import LinkedInScraper, LinkedInProfile
from utils.config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.linkedin_scraping_delay = 1.0  # Shorter delay for tests
    return config


@pytest.fixture
@patch('services.linkedin_scraper.get_webdriver_manager')
@patch('services.linkedin_scraper.AIParser')
def linkedin_scraper(mock_ai_parser, mock_get_webdriver_manager, mock_config):
    """Create a LinkedInScraper instance for testing."""
    mock_webdriver_manager = Mock()
    mock_get_webdriver_manager.return_value = mock_webdriver_manager
    
    # Mock AI parser to fail initialization so we use traditional parsing
    mock_ai_parser.side_effect = Exception("AI parser disabled for tests")
    
    return LinkedInScraper(mock_config)


@pytest.fixture
def sample_linkedin_profile():
    """Create a sample LinkedIn profile for testing."""
    return LinkedInProfile(
        name="John Doe",
        current_role="Senior Software Engineer",
        company="Tech Corp",
        location="San Francisco, CA",
        summary="Experienced software engineer with 5+ years in web development",
        experience=[
            "Software Engineer at StartupCo (2020-2023)",
            "Junior Developer at WebDev Inc (2018-2020)"
        ],
        skills=["Python", "JavaScript", "React", "Node.js", "AWS"],
        education=["BS Computer Science, University of California"]
    )


class TestLinkedInProfile:
    """Test LinkedInProfile data model."""
    
    def test_linkedin_profile_creation(self):
        """Test creating a LinkedInProfile instance."""
        profile = LinkedInProfile(
            name="Test User",
            current_role="Developer",
            experience=["Previous role"],
            skills=["Python"],
            summary="Test summary"
        )
        
        assert profile.name == "Test User"
        assert profile.current_role == "Developer"
        assert profile.experience == ["Previous role"]
        assert profile.skills == ["Python"]
        assert profile.summary == "Test summary"
        assert profile.education == []  # Should default to empty list
    
    def test_linkedin_profile_with_optional_fields(self):
        """Test LinkedInProfile with optional fields."""
        profile = LinkedInProfile(
            name="Test User",
            current_role="Developer",
            experience=[],
            skills=[],
            summary="",
            company="Test Company",
            location="Test City",
            education=["Test Education"]
        )
        
        assert profile.company == "Test Company"
        assert profile.location == "Test City"
        assert profile.education == ["Test Education"]


class TestLinkedInScraper:
    """Test LinkedInScraper functionality."""
    
    @patch('services.linkedin_scraper.get_webdriver_manager')
    def test_initialization(self, mock_get_webdriver_manager, mock_config):
        """Test LinkedInScraper initialization."""
        mock_webdriver_manager = Mock()
        mock_get_webdriver_manager.return_value = mock_webdriver_manager
        
        scraper = LinkedInScraper(mock_config)
        
        assert scraper.config == mock_config
        assert scraper.min_delay == 1.0
        assert scraper.last_request_time == 0
        assert scraper.webdriver_manager == mock_webdriver_manager
    
    def test_is_valid_linkedin_url(self, linkedin_scraper):
        """Test LinkedIn URL validation."""
        # Valid URLs
        assert linkedin_scraper._is_valid_linkedin_url("https://linkedin.com/in/johndoe")
        assert linkedin_scraper._is_valid_linkedin_url("https://www.linkedin.com/in/jane-smith")
        assert linkedin_scraper._is_valid_linkedin_url("http://linkedin.com/in/test-user-123")
        
        # Invalid URLs
        assert not linkedin_scraper._is_valid_linkedin_url("https://facebook.com/johndoe")
        assert not linkedin_scraper._is_valid_linkedin_url("https://linkedin.com/company/test")
        assert not linkedin_scraper._is_valid_linkedin_url("https://linkedin.com")
        assert not linkedin_scraper._is_valid_linkedin_url("invalid-url")
        assert not linkedin_scraper._is_valid_linkedin_url("")
    
    def test_enforce_rate_limit(self, linkedin_scraper):
        """Test rate limiting functionality."""
        import time
        
        # First call should not sleep
        start_time = time.time()
        linkedin_scraper._enforce_rate_limit()
        first_call_time = time.time() - start_time
        
        # Should be very quick (no sleep)
        assert first_call_time < 0.1
        
        # Second call immediately should sleep
        start_time = time.time()
        linkedin_scraper._enforce_rate_limit()
        second_call_time = time.time() - start_time
        
        # Should sleep for approximately the min_delay
        assert second_call_time >= 0.9  # Allow some tolerance
    
    def test_extract_profile_data_invalid_url(self, linkedin_scraper):
        """Test extraction with invalid URL."""
        result = linkedin_scraper.extract_profile_data("https://invalid-url.com")
        assert result is None
    
    def test_extract_profile_data_success(self, linkedin_scraper):
        """Test successful profile data extraction."""
        # Mock the webdriver context manager
        mock_driver = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_driver
        mock_context_manager.__exit__.return_value = None
        linkedin_scraper.webdriver_manager.get_driver.return_value = mock_context_manager
        
        # Mock WebDriverWait
        with patch('services.linkedin_scraper.WebDriverWait'):
            # Mock find_element calls for different selectors
            mock_name_element = MagicMock()
            mock_name_element.text = "John Doe"
            
            mock_role_element = MagicMock()
            mock_role_element.text = "Software Engineer at Tech Corp"
            
            mock_location_element = MagicMock()
            mock_location_element.text = "San Francisco, CA"
            
            mock_summary_element = MagicMock()
            mock_summary_element.text = "Experienced software engineer"
            
            # Configure find_element to return appropriate mocks based on selector
            def mock_find_element(by, selector):
                if "h1" in selector or "text-heading-xlarge" in selector:
                    return mock_name_element
                elif "text-body-medium" in selector:
                    return mock_role_element
                elif "text-body-small" in selector:
                    return mock_location_element
                elif "pv-shared-text" in selector:
                    return mock_summary_element
                else:
                    raise NoSuchElementException()
            
            mock_driver.find_element.side_effect = mock_find_element
            mock_driver.find_elements.return_value = []  # Empty lists for experience, skills, education
            
            result = linkedin_scraper.extract_profile_data("https://linkedin.com/in/johndoe")
            
            assert result is not None
            assert result.name == "John Doe"
            assert result.current_role == "Software Engineer"
            assert result.company == "Tech Corp"
            assert result.location == "San Francisco, CA"
            assert result.summary == "Experienced software engineer"
    
    def test_extract_profile_data_webdriver_exception(self, linkedin_scraper):
        """Test extraction when webdriver fails."""
        linkedin_scraper.webdriver_manager.get_driver.side_effect = WebDriverException("WebDriver failed")
        
        result = linkedin_scraper.extract_profile_data("https://linkedin.com/in/johndoe")
        assert result is None
    
    def test_extract_profile_data_no_name_found(self, linkedin_scraper):
        """Test extraction when no name is found."""
        mock_driver = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_driver
        mock_context_manager.__exit__.return_value = None
        linkedin_scraper.webdriver_manager.get_driver.return_value = mock_context_manager
        
        with patch('services.linkedin_scraper.WebDriverWait'):
            # Mock find_element to raise exception for name selectors
            mock_driver.find_element.side_effect = NoSuchElementException()
            mock_driver.find_elements.return_value = []
            
            result = linkedin_scraper.extract_profile_data("https://linkedin.com/in/johndoe")
            assert result is None
    
    def test_get_experience_summary(self, linkedin_scraper, sample_linkedin_profile):
        """Test experience summary generation."""
        summary = linkedin_scraper.get_experience_summary(sample_linkedin_profile)
        
        expected = "Currently Senior Software Engineer at Tech Corp. Previous experience includes: Software Engineer at StartupCo (2020-2023), Junior Developer at WebDev Inc (2018-2020)"
        assert summary == expected
    
    def test_get_experience_summary_no_previous_experience(self, linkedin_scraper):
        """Test experience summary with no previous experience."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            company="Tech Corp",
            experience=[],
            skills=[],
            summary=""
        )
        
        summary = linkedin_scraper.get_experience_summary(profile)
        assert summary == "Currently Software Engineer at Tech Corp"
    
    def test_get_experience_summary_no_company(self, linkedin_scraper):
        """Test experience summary without company."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Freelance Developer",
            experience=["Previous role"],
            skills=[],
            summary=""
        )
        
        summary = linkedin_scraper.get_experience_summary(profile)
        assert "Currently Freelance Developer" in summary
        assert "Previous experience includes: Previous role" in summary
    
    def test_get_skills(self, linkedin_scraper, sample_linkedin_profile):
        """Test skills extraction."""
        skills = linkedin_scraper.get_skills(sample_linkedin_profile)
        
        assert skills == ["Python", "JavaScript", "React", "Node.js", "AWS"]
        assert len(skills) <= 10  # Should limit to 10 skills
    
    def test_get_skills_more_than_ten(self, linkedin_scraper):
        """Test skills extraction with more than 10 skills."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Developer",
            experience=[],
            skills=[f"Skill{i}" for i in range(15)],  # 15 skills
            summary=""
        )
        
        skills = linkedin_scraper.get_skills(profile)
        assert len(skills) == 10  # Should limit to 10
        assert skills == [f"Skill{i}" for i in range(10)]
    
    def test_extract_multiple_profiles(self, linkedin_scraper):
        """Test extracting multiple profiles."""
        mock_driver = MagicMock()
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_driver
        mock_context_manager.__exit__.return_value = None
        linkedin_scraper.webdriver_manager.get_driver.return_value = mock_context_manager
        
        with patch('services.linkedin_scraper.WebDriverWait'):
            # Mock successful extraction
            mock_name_element = MagicMock()
            mock_name_element.text = "Test User"
            
            mock_role_element = MagicMock()
            mock_role_element.text = "Developer"
            
            def mock_find_element(by, selector):
                if "h1" in selector:
                    return mock_name_element
                elif "text-body-medium" in selector:
                    return mock_role_element
                else:
                    raise NoSuchElementException()
            
            mock_driver.find_element.side_effect = mock_find_element
            mock_driver.find_elements.return_value = []
            
            urls = [
                "https://linkedin.com/in/user1",
                "https://linkedin.com/in/user2"
            ]
            
            results = linkedin_scraper.extract_multiple_profiles(urls)
            
            assert len(results) == 2
            assert all(url in results for url in urls)
            assert all(isinstance(profile, LinkedInProfile) for profile in results.values() if profile)
    
    def test_extract_text_safely(self, linkedin_scraper):
        """Test safe text extraction method."""
        mock_driver = MagicMock()
        
        # Test single element extraction
        mock_element = MagicMock()
        mock_element.text = "Test Text"
        mock_driver.find_element.return_value = mock_element
        
        result = linkedin_scraper._extract_text_safely(mock_driver, "test-selector")
        assert result == "Test Text"
        
        # Test multiple elements extraction
        mock_elements = [MagicMock(), MagicMock()]
        mock_elements[0].text = "Text 1"
        mock_elements[1].text = "Text 2"
        mock_driver.find_elements.return_value = mock_elements
        
        result = linkedin_scraper._extract_text_safely(mock_driver, "test-selector", multiple=True)
        assert result == ["Text 1", "Text 2"]
        
        # Test exception handling
        mock_driver.find_element.side_effect = NoSuchElementException()
        result = linkedin_scraper._extract_text_safely(mock_driver, "test-selector")
        assert result == ""
        
        mock_driver.find_elements.side_effect = NoSuchElementException()
        result = linkedin_scraper._extract_text_safely(mock_driver, "test-selector", multiple=True)
        assert result == []


class TestIntegration:
    """Integration tests for LinkedIn scraper."""
    
    @pytest.mark.integration
    def test_real_linkedin_extraction(self):
        """
        Integration test with real LinkedIn profile (requires valid config).
        This test is marked as integration and should be run separately.
        """
        # This test would require real setup and should be run manually
        # with proper LinkedIn URLs for testing
        pytest.skip("Integration test - requires real setup and LinkedIn URLs")
    
    def test_error_handling_robustness(self, linkedin_scraper):
        """Test that the scraper handles various error conditions gracefully."""
        # Test with None URL - this should cause an exception in _is_valid_linkedin_url
        result = linkedin_scraper.extract_profile_data(None)
        assert result is None
        
        # Test with empty string
        result = linkedin_scraper.extract_profile_data("")
        assert result is None
        
        # Test with malformed URL
        result = linkedin_scraper.extract_profile_data("not-a-url")
        assert result is None