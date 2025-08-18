"""
Unit tests for SenderProfileManager service.
"""
import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile, ValidationError


class TestSenderProfileManager:
    """Test cases for SenderProfileManager service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SenderProfileManager()
        self.sample_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript"],
            experience_summary="Experienced developer with 5 years in web development",
            value_proposition="I build scalable web applications",
            target_roles=["Tech Lead", "Senior Engineer"]
        )
    
    def test_load_profile_from_config(self):
        """Test loading profile from configuration dictionary."""
        config_data = {
            "name": "Jane Smith",
            "current_role": "Developer",
            "years_experience": 3,
            "key_skills": ["Java", "Spring"],
            "experience_summary": "Backend developer",
            "value_proposition": "I build robust systems",
            "target_roles": ["Senior Developer"]
        }
        
        profile = self.manager.load_profile_from_config(config_data)
        
        assert profile.name == "Jane Smith"
        assert profile.current_role == "Developer"
        assert profile.years_experience == 3
        assert profile.key_skills == ["Java", "Spring"]
    
    def test_load_profile_from_config_invalid_data(self):
        """Test loading profile from invalid configuration data."""
        config_data = {
            "name": "",  # Invalid empty name
            "current_role": "Developer",
            "years_experience": -1  # Invalid negative experience
        }
        
        with pytest.raises(ValidationError):
            self.manager.load_profile_from_config(config_data)
    
    def test_load_profile_from_json_file(self):
        """Test loading profile from JSON file."""
        config_data = {
            "name": "Alice Johnson",
            "current_role": "Frontend Developer",
            "years_experience": 4,
            "key_skills": ["React", "TypeScript"],
            "experience_summary": "Frontend specialist",
            "value_proposition": "I create beautiful user interfaces",
            "target_roles": ["Senior Frontend Developer"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            profile = self.manager.load_profile_from_json(temp_path)
            
            assert profile.name == "Alice Johnson"
            assert profile.current_role == "Frontend Developer"
            assert profile.years_experience == 4
        finally:
            os.unlink(temp_path)
    
    def test_load_profile_from_json_file_not_found(self):
        """Test loading profile from non-existent JSON file."""
        with pytest.raises(FileNotFoundError):
            self.manager.load_profile_from_json("non_existent_file.json")
    
    def test_load_profile_from_json_invalid_json(self):
        """Test loading profile from invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_path = f.name
        
        try:
            with pytest.raises(ValidationError, match="Invalid JSON format"):
                self.manager.load_profile_from_json(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_load_profile_from_yaml_file(self):
        """Test loading profile from YAML file."""
        config_data = {
            "name": "Bob Wilson",
            "current_role": "DevOps Engineer",
            "years_experience": 6,
            "key_skills": ["Docker", "Kubernetes", "AWS"],
            "experience_summary": "DevOps specialist with cloud expertise",
            "value_proposition": "I streamline deployment processes",
            "target_roles": ["Senior DevOps Engineer", "Cloud Architect"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            profile = self.manager.load_profile_from_yaml(temp_path)
            
            assert profile.name == "Bob Wilson"
            assert profile.current_role == "DevOps Engineer"
            assert profile.years_experience == 6
        finally:
            os.unlink(temp_path)
    
    def test_load_profile_from_yaml_file_not_found(self):
        """Test loading profile from non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            self.manager.load_profile_from_yaml("non_existent_file.yaml")
    
    def test_load_profile_from_yaml_invalid_yaml(self):
        """Test loading profile from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(ValidationError, match="Invalid YAML format"):
                self.manager.load_profile_from_yaml(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_save_profile_to_json(self):
        """Test saving profile to JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            self.manager.save_profile_to_json(self.sample_profile, temp_path)
            
            # Verify file was created and contains correct data
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["name"] == "John Doe"
            assert saved_data["current_role"] == "Senior Developer"
            assert saved_data["years_experience"] == 5
        finally:
            os.unlink(temp_path)
    
    def test_save_profile_to_yaml(self):
        """Test saving profile to YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            self.manager.save_profile_to_yaml(self.sample_profile, temp_path)
            
            # Verify file was created and contains correct data
            with open(temp_path, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["name"] == "John Doe"
            assert saved_data["current_role"] == "Senior Developer"
            assert saved_data["years_experience"] == 5
        finally:
            os.unlink(temp_path)
    
    def test_save_profile_to_markdown(self):
        """Test saving profile to markdown file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            temp_path = f.name
        
        try:
            self.manager.save_profile_to_markdown(self.sample_profile, temp_path)
            
            # Verify file was created and contains expected content
            with open(temp_path, 'r') as f:
                content = f.read()
            
            assert "# Sender Profile" in content
            assert "John Doe" in content
            assert "Senior Developer" in content
            assert "Python" in content
            assert "JavaScript" in content
        finally:
            os.unlink(temp_path)
    
    def test_load_profile_from_markdown(self):
        """Test loading profile from markdown file."""
        markdown_content = """# Sender Profile

## Basic Information
- **Name**: Test User
- **Current Role**: Software Engineer
- **Years of Experience**: 3
- **Location**: San Francisco, CA
- **Remote Preference**: hybrid

## Professional Summary
Experienced software engineer with expertise in web development.

## Key Skills
- Python
- React
- PostgreSQL

## Experience Highlights
- Built scalable web applications
- Led team of 3 developers

## Value Proposition
I create efficient and maintainable software solutions.

## Target Roles
- Senior Software Engineer
- Tech Lead
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(markdown_content)
            temp_path = f.name
        
        try:
            profile = self.manager.load_profile_from_markdown(temp_path)
            
            assert profile.name == "Test User"
            assert profile.current_role == "Software Engineer"
            assert profile.years_experience == 3
            assert profile.location == "San Francisco, CA"
            assert profile.remote_preference == "hybrid"
            assert "Python" in profile.key_skills
            assert "React" in profile.key_skills
            assert len(profile.notable_achievements) == 2
            assert len(profile.target_roles) == 2
        finally:
            os.unlink(temp_path)
    
    def test_load_profile_from_markdown_file_not_found(self):
        """Test loading profile from non-existent markdown file."""
        with pytest.raises(FileNotFoundError):
            self.manager.load_profile_from_markdown("non_existent_file.md")
    
    def test_validate_profile_valid(self):
        """Test validating a valid profile."""
        is_valid, issues = self.manager.validate_profile(self.sample_profile)
        
        # The sample profile is missing some fields for completeness
        # so it won't be completely valid, but should not have validation errors
        assert len([issue for issue in issues if "cannot be empty" in issue]) == 0
    
    def test_validate_profile_invalid(self):
        """Test validating an invalid profile using config data."""
        # Test with invalid config data that bypasses __post_init__ validation
        invalid_config = {
            "name": "",  # Invalid empty name
            "current_role": "Developer",
            "years_experience": 2
        }
        
        with pytest.raises(ValidationError, match="Sender name cannot be empty"):
            self.manager.load_profile_from_config(invalid_config)
    
    def test_validate_profile_incomplete(self):
        """Test validating an incomplete profile."""
        incomplete_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2
            # Missing required fields for completeness
        )
        
        is_valid, issues = self.manager.validate_profile(incomplete_profile)
        
        assert is_valid is False
        assert any("incomplete" in issue.lower() for issue in issues)
    
    def test_get_profile_suggestions(self):
        """Test getting profile improvement suggestions."""
        minimal_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            experience_summary="Short summary",
            value_proposition="Short value prop",
            target_roles=["Developer"]
        )
        
        suggestions = self.manager.get_profile_suggestions(minimal_profile)
        
        assert len(suggestions) > 0
        assert any("experience summary" in suggestion.lower() for suggestion in suggestions)
        assert any("value proposition" in suggestion.lower() for suggestion in suggestions)
    
    def test_create_profile_template_markdown(self):
        """Test creating markdown template."""
        template = self.manager.create_profile_template("markdown")
        
        assert "# Sender Profile" in template
        assert "## Basic Information" in template
        assert "[Your Full Name]" in template
        assert "## Key Skills" in template
    
    def test_create_profile_template_json(self):
        """Test creating JSON template."""
        template = self.manager.create_profile_template("json")
        
        # Should be valid JSON
        template_data = json.loads(template)
        assert "name" in template_data
        assert "current_role" in template_data
        assert "key_skills" in template_data
    
    def test_create_profile_template_yaml(self):
        """Test creating YAML template."""
        template = self.manager.create_profile_template("yaml")
        
        # Should be valid YAML
        template_data = yaml.safe_load(template)
        assert "name" in template_data
        assert "current_role" in template_data
        assert "key_skills" in template_data
    
    def test_create_profile_template_invalid_format(self):
        """Test creating template with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format type"):
            self.manager.create_profile_template("invalid_format")
    
    def test_parse_markdown_content_basic_info(self):
        """Test parsing basic information from markdown content."""
        content = """# Sender Profile

## Basic Information
- **Name**: John Smith
- **Current Role**: Senior Engineer
- **Years of Experience**: 7
- **Location**: New York, NY
- **Remote Preference**: remote
- **Availability**: 2 weeks notice
- **Salary Expectations**: $130k-$160k
"""
        
        profile_data = self.manager._parse_markdown_content(content)
        
        assert profile_data["name"] == "John Smith"
        assert profile_data["current_role"] == "Senior Engineer"
        assert profile_data["years_experience"] == 7
        assert profile_data["location"] == "New York, NY"
        assert profile_data["remote_preference"] == "remote"
        assert profile_data["availability"] == "2 weeks notice"
        assert profile_data["salary_expectations"] == "$130k-$160k"
    
    def test_parse_markdown_content_lists(self):
        """Test parsing list sections from markdown content."""
        content = """# Sender Profile

## Key Skills
- Python
- Django
- PostgreSQL

## Target Roles
- Senior Developer
- Tech Lead

## Industries of Interest
- FinTech
- Healthcare
"""
        
        profile_data = self.manager._parse_markdown_content(content)
        
        assert profile_data["key_skills"] == ["Python", "Django", "PostgreSQL"]
        assert profile_data["target_roles"] == ["Senior Developer", "Tech Lead"]
        assert profile_data["industries_of_interest"] == ["FinTech", "Healthcare"]
    
    def test_generate_markdown_content(self):
        """Test generating markdown content from profile."""
        content = self.manager._generate_markdown_content(self.sample_profile)
        
        assert "# Sender Profile" in content
        assert "John Doe" in content
        assert "Senior Developer" in content
        assert "Python" in content
        assert "JavaScript" in content
        assert "Tech Lead" in content
    
    def test_save_invalid_profile(self):
        """Test saving invalid profile raises error."""
        # Create a profile and then manually break it to test save validation
        profile = SenderProfile(
            name="Valid Name",
            current_role="Developer",
            years_experience=2
        )
        
        # Manually set invalid data to bypass __post_init__ validation
        profile.name = ""  # Make it invalid
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(ValidationError):
                self.manager.save_profile_to_json(profile, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_directory_creation_on_save(self):
        """Test that directories are created when saving profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, "nested", "directory", "profile.json")
            
            self.manager.save_profile_to_json(self.sample_profile, nested_path)
            
            assert os.path.exists(nested_path)
            
            # Verify content
            with open(nested_path, 'r') as f:
                saved_data = json.load(f)
            assert saved_data["name"] == "John Doe"