"""
Integration tests for interactive sender profile setup system.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile, ValidationError


class TestSenderProfileInteractive:
    """Test cases for interactive sender profile setup."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SenderProfileManager()
    
    @patch('builtins.input')
    def test_create_profile_interactively_complete(self, mock_input):
        """Test creating a complete profile interactively."""
        # Mock user inputs for a complete profile
        inputs = [
            "John Doe",  # name
            "Senior Developer",  # current_role
            "5",  # years_experience
            "San Francisco, CA",  # location
            "hybrid",  # remote_preference
            "Available immediately",  # availability
            "$120k-$150k",  # salary_expectations
            "Experienced full-stack developer with 5 years in web development.",  # experience_summary (multiline)
            "",  # end multiline
            "I build scalable web applications that drive business growth.",  # value_proposition (multiline)
            "",  # end multiline
            "Python",  # skill 1
            "JavaScript",  # skill 2
            "React",  # skill 3
            "",  # end skills
            "Senior Developer",  # target role 1
            "Tech Lead",  # target role 2
            "",  # end target roles
            "Led team of 5 developers",  # achievement 1
            "Reduced API response time by 40%",  # achievement 2
            "",  # end achievements
            "BS Computer Science - MIT",  # education 1
            "",  # end education
            "AWS Certified Developer",  # certification 1
            "",  # end certifications
            "FinTech",  # industry 1
            "Healthcare",  # industry 2
            "",  # end industries
            "https://johndoe.dev",  # portfolio link 1
            "https://github.com/johndoe",  # portfolio link 2
            "",  # end portfolio links
            "email"  # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        profile = self.manager.create_profile_interactively()
        
        assert profile.name == "John Doe"
        assert profile.current_role == "Senior Developer"
        assert profile.years_experience == 5
        assert profile.location == "San Francisco, CA"
        assert profile.remote_preference == "hybrid"
        assert profile.availability == "Available immediately"
        assert profile.salary_expectations == "$120k-$150k"
        assert "full-stack developer" in profile.experience_summary
        assert "scalable web applications" in profile.value_proposition
        assert "Python" in profile.key_skills
        assert "JavaScript" in profile.key_skills
        assert "React" in profile.key_skills
        assert "Senior Developer" in profile.target_roles
        assert "Tech Lead" in profile.target_roles
        assert len(profile.notable_achievements) == 2
        assert len(profile.education) == 1
        assert len(profile.certifications) == 1
        assert len(profile.industries_of_interest) == 2
        assert len(profile.portfolio_links) == 2
        assert profile.preferred_contact_method == "email"
        assert profile.is_complete() is True
    
    @patch('builtins.input')
    def test_create_profile_interactively_minimal(self, mock_input):
        """Test creating a minimal profile interactively."""
        # Mock user inputs for a minimal profile
        inputs = [
            "Jane Smith",  # name
            "Developer",  # current_role
            "2",  # years_experience
            "",  # location (empty)
            "",  # remote_preference (empty)
            "",  # availability (empty)
            "",  # salary_expectations (empty)
            "Junior developer with Python experience.",  # experience_summary
            "",  # end multiline
            "I write clean, maintainable code.",  # value_proposition
            "",  # end multiline
            "Python",  # skill 1
            "",  # end skills
            "Software Engineer",  # target role 1
            "",  # end target roles
            "",  # end achievements (empty)
            "",  # end education (empty)
            "",  # end certifications (empty)
            "",  # end industries (empty)
            "",  # end portfolio links (empty)
            "email"  # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        profile = self.manager.create_profile_interactively()
        
        assert profile.name == "Jane Smith"
        assert profile.current_role == "Developer"
        assert profile.years_experience == 2
        assert profile.location == ""
        assert profile.remote_preference == ""
        assert profile.availability == ""
        assert profile.salary_expectations is None
        assert len(profile.key_skills) == 1
        assert len(profile.target_roles) == 1
        assert profile.is_complete() is True
    
    @patch('builtins.input')
    def test_create_profile_interactively_invalid_years(self, mock_input):
        """Test handling invalid years of experience input."""
        inputs = [
            "John Doe",  # name
            "Developer",  # current_role
            "invalid",  # invalid years_experience
            "5",  # valid years_experience
            "",  # location
            "",  # remote_preference
            "",  # availability
            "",  # salary_expectations
            "Developer with experience.",  # experience_summary
            "",  # end multiline
            "I build software.",  # value_proposition
            "",  # end multiline
            "Python",  # skill
            "",  # end skills
            "Developer",  # target role
            "",  # end target roles
            "",  # end achievements
            "",  # end education
            "",  # end certifications
            "",  # end industries
            "",  # end portfolio links
            "email"  # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        profile = self.manager.create_profile_interactively()
        
        assert profile.years_experience == 5
    
    @patch('builtins.input')
    def test_create_profile_interactively_invalid_remote_preference(self, mock_input):
        """Test handling invalid remote preference input."""
        inputs = [
            "John Doe",  # name
            "Developer",  # current_role
            "3",  # years_experience
            "",  # location
            "invalid_preference",  # invalid remote_preference
            "",  # availability
            "",  # salary_expectations
            "Developer with experience.",  # experience_summary
            "",  # end multiline
            "I build software.",  # value_proposition
            "",  # end multiline
            "Python",  # skill
            "",  # end skills
            "Developer",  # target role
            "",  # end target roles
            "",  # end achievements
            "",  # end education
            "",  # end certifications
            "",  # end industries
            "",  # end portfolio links
            "email"  # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        profile = self.manager.create_profile_interactively()
        
        # Should default to "flexible" for invalid input
        assert profile.remote_preference == "flexible"
    
    @patch('builtins.input')
    def test_create_profile_interactively_invalid_url(self, mock_input):
        """Test handling invalid URL input for portfolio links."""
        inputs = [
            "John Doe",  # name
            "Developer",  # current_role
            "3",  # years_experience
            "",  # location
            "",  # remote_preference
            "",  # availability
            "",  # salary_expectations
            "Developer with experience.",  # experience_summary
            "",  # end multiline
            "I build software.",  # value_proposition
            "",  # end multiline
            "Python",  # skill
            "",  # end skills
            "Developer",  # target role
            "",  # end target roles
            "",  # end achievements
            "",  # end education
            "",  # end certifications
            "",  # end industries
            "invalid-url",  # invalid URL
            "https://valid-url.com",  # valid URL
            "",  # end portfolio links
            "email"  # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        profile = self.manager.create_profile_interactively()
        
        # Should only include the valid URL
        assert len(profile.portfolio_links) == 1
        assert profile.portfolio_links[0] == "https://valid-url.com"
    
    @patch('builtins.input')
    def test_edit_profile_interactively_basic_info(self, mock_input):
        """Test editing basic information interactively."""
        # Create initial profile
        initial_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=3,
            key_skills=["Python"],
            experience_summary="Developer with experience",
            value_proposition="I build software",
            target_roles=["Senior Developer"]
        )
        
        inputs = [
            "1",  # Choose basic information
            "Jane Doe",  # new name
            "Senior Developer",  # new current_role
            "5",  # new years_experience
            "New York, NY",  # new location
            "remote",  # new remote_preference
            "Available now"  # new availability
        ]
        mock_input.side_effect = inputs
        
        updated_profile = self.manager.edit_profile_interactively(initial_profile)
        
        assert updated_profile.name == "Jane Doe"
        assert updated_profile.current_role == "Senior Developer"
        assert updated_profile.years_experience == 5
        assert updated_profile.location == "New York, NY"
        assert updated_profile.remote_preference == "remote"
        assert updated_profile.availability == "Available now"
    
    @patch('builtins.input')
    def test_edit_profile_interactively_skills(self, mock_input):
        """Test editing skills interactively."""
        initial_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=3,
            key_skills=["Python"],
            experience_summary="Developer with experience",
            value_proposition="I build software",
            target_roles=["Senior Developer"]
        )
        
        inputs = [
            "3",  # Choose skills
            "JavaScript",  # new skill 1
            "React",  # new skill 2
            "Node.js",  # new skill 3
            ""  # end skills
        ]
        mock_input.side_effect = inputs
        
        updated_profile = self.manager.edit_profile_interactively(initial_profile)
        
        assert "JavaScript" in updated_profile.key_skills
        assert "React" in updated_profile.key_skills
        assert "Node.js" in updated_profile.key_skills
        assert len(updated_profile.key_skills) == 3
    
    @patch('builtins.input')
    def test_edit_profile_interactively_cancel(self, mock_input):
        """Test cancelling profile edit."""
        initial_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=3,
            key_skills=["Python"],
            experience_summary="Developer with experience",
            value_proposition="I build software",
            target_roles=["Senior Developer"]
        )
        
        inputs = ["0"]  # Choose cancel
        mock_input.side_effect = inputs
        
        updated_profile = self.manager.edit_profile_interactively(initial_profile)
        
        # Profile should remain unchanged
        assert updated_profile.name == "John Doe"
        assert updated_profile.current_role == "Developer"
        assert updated_profile.years_experience == 3
    
    @patch('builtins.input')
    def test_get_input_with_default(self, mock_input):
        """Test _get_input method with default value."""
        mock_input.return_value = ""  # User presses Enter
        
        result = self.manager._get_input("Test prompt", default="default_value")
        
        assert result == "default_value"
    
    @patch('builtins.input')
    def test_get_input_required_field(self, mock_input):
        """Test _get_input method with required field."""
        mock_input.side_effect = ["", "", "valid_input"]  # Empty inputs then valid
        
        result = self.manager._get_input("Test prompt", required=True)
        
        assert result == "valid_input"
    
    @patch('builtins.input')
    def test_get_list_input(self, mock_input):
        """Test _get_list_input method."""
        mock_input.side_effect = ["item1", "item2", "item3", ""]  # Items then empty to finish
        
        result = self.manager._get_list_input("test item")
        
        assert result == ["item1", "item2", "item3"]
    
    @patch('builtins.input')
    def test_get_list_input_with_url_validation(self, mock_input):
        """Test _get_list_input method with URL validation."""
        mock_input.side_effect = [
            "invalid-url",  # Invalid URL
            "https://valid-url.com",  # Valid URL
            ""  # End input
        ]
        
        result = self.manager._get_list_input("link", validate_url=True)
        
        # Should only include valid URL
        assert result == ["https://valid-url.com"]
    
    def test_show_profile_preview(self, capsys):
        """Test _show_profile_preview method."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React", "Node.js", "AWS", "Docker"],
            target_roles=["Tech Lead", "Senior Engineer", "Principal Developer", "Architect"],
            experience_summary="Experienced developer",
            value_proposition="I build great software"
        )
        
        self.manager._show_profile_preview(profile)
        
        captured = capsys.readouterr()
        assert "John Doe" in captured.out
        assert "Senior Developer" in captured.out
        assert "5 years" in captured.out
        assert "Python" in captured.out
        assert "... and 1 more" in captured.out  # Should show truncated skills
        assert "... and 1 more" in captured.out  # Should show truncated roles
        assert "Profile Completeness:" in captured.out
    
    @patch('builtins.input')
    def test_get_multiline_input(self, mock_input):
        """Test _get_multiline_input method."""
        mock_input.side_effect = [
            "First line of text",
            "Second line of text",
            ""  # Empty line to finish
        ]
        
        result = self.manager._get_multiline_input("Test prompt")
        
        assert result == "First line of text Second line of text"
    
    @patch('builtins.input')
    def test_get_multiline_input_required(self, mock_input):
        """Test _get_multiline_input method with required field."""
        mock_input.side_effect = [
            "",  # Empty line (should prompt for required)
            "Required text",
            ""  # Empty line to finish
        ]
        
        result = self.manager._get_multiline_input("Test prompt", required=True)
        
        assert result == "Required text"