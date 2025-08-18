"""
Comprehensive unit tests for sender profile functionality.
"""
import pytest
import json
import yaml
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from models.data_models import SenderProfile, ValidationError
from services.sender_profile_manager import SenderProfileManager
from services.email_generator import EmailGenerator


class TestSenderProfileModel:
    """Test cases for SenderProfile data model validation and serialization."""
    
    def test_serialization_deserialization_roundtrip(self):
        """Test that serialization and deserialization preserves all profile data."""
        # Create a complete profile with all fields populated
        original_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=8,
            key_skills=["Python", "JavaScript", "React", "AWS", "Docker"],
            experience_summary="Experienced full-stack developer with 8 years in web development",
            education=["BS Computer Science - MIT", "MS Software Engineering - Stanford"],
            certifications=["AWS Certified Developer", "Certified Scrum Master"],
            value_proposition="I build scalable web applications that drive business growth",
            target_roles=["Senior Developer", "Tech Lead", "Engineering Manager"],
            industries_of_interest=["FinTech", "Healthcare", "EdTech"],
            notable_achievements=[
                "Led team of 5 developers to deliver major platform upgrade",
                "Reduced API response time by 40% through optimization",
                "Implemented CI/CD pipeline reducing deployment time by 60%"
            ],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
            preferred_contact_method="email",
            availability="Available with 2 weeks notice",
            location="San Francisco, CA",
            remote_preference="hybrid",
            salary_expectations="$150k-$180k",
            additional_context={"timezone": "PST", "interests": "Open source contribution"}
        )
        
        # Convert to dictionary
        profile_dict = original_profile.to_dict()
        
        # Convert back to SenderProfile
        recreated_profile = SenderProfile.from_dict(profile_dict)
        
        # Verify all fields match
        assert recreated_profile.name == original_profile.name
        assert recreated_profile.current_role == original_profile.current_role
        assert recreated_profile.years_experience == original_profile.years_experience
        assert recreated_profile.key_skills == original_profile.key_skills
        assert recreated_profile.experience_summary == original_profile.experience_summary
        assert recreated_profile.education == original_profile.education
        assert recreated_profile.certifications == original_profile.certifications
        assert recreated_profile.value_proposition == original_profile.value_proposition
        assert recreated_profile.target_roles == original_profile.target_roles
        assert recreated_profile.industries_of_interest == original_profile.industries_of_interest
        assert recreated_profile.notable_achievements == original_profile.notable_achievements
        assert recreated_profile.portfolio_links == original_profile.portfolio_links
        assert recreated_profile.preferred_contact_method == original_profile.preferred_contact_method
        assert recreated_profile.availability == original_profile.availability
        assert recreated_profile.location == original_profile.location
        assert recreated_profile.remote_preference == original_profile.remote_preference
        assert recreated_profile.salary_expectations == original_profile.salary_expectations
        assert recreated_profile.additional_context == original_profile.additional_context
    
    def test_completeness_score_calculation_accuracy(self):
        """Test that completeness score calculation is accurate and consistent."""
        # Create profiles with different levels of completeness
        minimal_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2
        )
        
        partial_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python", "JavaScript"],
            experience_summary="Developer with 2 years experience",
            value_proposition="I write clean code",
            target_roles=["Software Engineer"]
        )
        
        complete_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React"],
            experience_summary="Experienced developer with 5 years in web development",
            education=["BS Computer Science"],
            certifications=["AWS Certified"],
            value_proposition="I build scalable applications",
            target_roles=["Tech Lead", "Senior Engineer"],
            industries_of_interest=["FinTech"],
            notable_achievements=["Led successful project"],
            portfolio_links=["https://example.com"],
            availability="Available now",
            location="San Francisco",
            remote_preference="hybrid"
        )
        
        # Calculate scores
        minimal_score = minimal_profile.get_completeness_score()
        partial_score = partial_profile.get_completeness_score()
        complete_score = complete_profile.get_completeness_score()
        
        # Verify scores are in ascending order
        assert minimal_score < partial_score < complete_score
        
        # Verify score ranges
        assert 0.0 <= minimal_score <= 0.3  # Minimal should be low
        assert 0.3 < partial_score <= 0.7   # Partial should be medium
        assert 0.7 < complete_score <= 1.0  # Complete should be high
    
    def test_get_relevant_experience_context_matching(self):
        """Test that get_relevant_experience returns context-appropriate experience."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Full Stack Developer",
            years_experience=5,
            key_skills=["Python", "React", "AWS", "Machine Learning", "Docker"],
            notable_achievements=[
                "Built machine learning pipeline for fintech startup",
                "Developed React dashboard for healthcare analytics",
                "Led AWS migration for e-commerce platform",
                "Created Docker-based deployment system"
            ]
        )
        
        # Test matching by role keywords
        ml_experience = profile.get_relevant_experience("Machine Learning Engineer", "AI Company")
        assert any("machine learning" in exp.lower() for exp in ml_experience)
        
        # Test matching by company/industry keywords
        fintech_experience = profile.get_relevant_experience("Developer", "FinTech Startup")
        assert any("fintech" in exp.lower() for exp in fintech_experience)
        
        # Test matching by both role and company
        healthcare_react_experience = profile.get_relevant_experience("React Developer", "Healthcare")
        assert any("react" in exp.lower() and "healthcare" in exp.lower() for exp in healthcare_react_experience)
    
    def test_validation_edge_cases(self):
        """Test validation edge cases for SenderProfile."""
        # Test validation with empty lists instead of None
        profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=[],
            education=[],
            certifications=[],
            target_roles=[],
            industries_of_interest=[],
            notable_achievements=[],
            portfolio_links=[]
        )
        
        # Should not raise exceptions for empty lists
        profile.validate()
        
        # Test with exactly max years (70)
        profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=70
        )
        profile.validate()  # Should not raise exception
        
        # Test with just over max years (71)
        with pytest.raises(ValidationError, match="Years of experience seems unrealistic"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=71
            )
        
        # Test with mixed case remote preference
        profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            remote_preference="HyBrId"  # Mixed case
        )
        profile.validate()  # Should not raise exception
        assert profile.remote_preference.lower() == "hybrid"  # Should be normalized in validation
    
    def test_is_complete_edge_cases(self):
        """Test edge cases for is_complete method."""
        # Test with minimal required fields
        minimal_complete = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=0,  # Zero experience is valid
            key_skills=["Python"],  # Just one skill
            experience_summary="New developer",
            value_proposition="Learning quickly",
            target_roles=["Junior Developer"]
        )
        assert minimal_complete.is_complete() is True
        
        # Test with missing value proposition
        missing_value_prop = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            experience_summary="Developer with experience",
            target_roles=["Developer"]
        )
        assert missing_value_prop.is_complete() is False
        
        # Test with empty key skills
        empty_skills = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=[],
            experience_summary="Developer with experience",
            value_proposition="I write code",
            target_roles=["Developer"]
        )
        assert empty_skills.is_complete() is False


class TestSenderProfileManagerOperations:
    """Test cases for SenderProfileManager operations with different formats."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SenderProfileManager()
        self.sample_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React"],
            experience_summary="Experienced developer with 5 years in web development",
            value_proposition="I build scalable web applications",
            target_roles=["Tech Lead", "Senior Engineer"]
        )
    
    def test_format_conversion_markdown_to_json(self):
        """Test converting profile from markdown to JSON format."""
        # Create a temporary markdown file
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
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as md_file:
            md_file.write(markdown_content)
            md_path = md_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as json_file:
            json_path = json_file.name
        
        try:
            # Load from markdown
            profile = self.manager.load_profile_from_markdown(md_path)
            
            # Save to JSON
            self.manager.save_profile_to_json(profile, json_path)
            
            # Load from JSON to verify
            json_profile = self.manager.load_profile_from_json(json_path)
            
            # Verify data is preserved
            assert json_profile.name == "Test User"
            assert json_profile.current_role == "Software Engineer"
            assert json_profile.years_experience == 3
            assert json_profile.location == "San Francisco, CA"
            assert json_profile.remote_preference == "hybrid"
            assert "Python" in json_profile.key_skills
            assert "React" in json_profile.key_skills
            assert len(json_profile.notable_achievements) == 2
            assert len(json_profile.target_roles) == 2
            
        finally:
            # Clean up
            os.unlink(md_path)
            os.unlink(json_path)
    
    def test_format_conversion_json_to_yaml(self):
        """Test converting profile from JSON to YAML format."""
        # Create a temporary JSON file
        json_data = {
            "name": "Alice Johnson",
            "current_role": "Frontend Developer",
            "years_experience": 4,
            "key_skills": ["React", "TypeScript", "CSS"],
            "experience_summary": "Frontend specialist with 4 years experience",
            "value_proposition": "I create beautiful user interfaces",
            "target_roles": ["Senior Frontend Developer", "UI Lead"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
            json.dump(json_data, json_file)
            json_path = json_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as yaml_file:
            yaml_path = yaml_file.name
        
        try:
            # Load from JSON
            profile = self.manager.load_profile_from_json(json_path)
            
            # Save to YAML
            self.manager.save_profile_to_yaml(profile, yaml_path)
            
            # Load from YAML to verify
            yaml_profile = self.manager.load_profile_from_yaml(yaml_path)
            
            # Verify data is preserved
            assert yaml_profile.name == "Alice Johnson"
            assert yaml_profile.current_role == "Frontend Developer"
            assert yaml_profile.years_experience == 4
            assert "React" in yaml_profile.key_skills
            assert "TypeScript" in yaml_profile.key_skills
            assert yaml_profile.experience_summary == "Frontend specialist with 4 years experience"
            assert yaml_profile.value_proposition == "I create beautiful user interfaces"
            assert len(yaml_profile.target_roles) == 2
            
        finally:
            # Clean up
            os.unlink(json_path)
            os.unlink(yaml_path)
    
    def test_format_conversion_yaml_to_markdown(self):
        """Test converting profile from YAML to markdown format."""
        # Create a temporary YAML file
        yaml_data = {
            "name": "Bob Wilson",
            "current_role": "DevOps Engineer",
            "years_experience": 6,
            "key_skills": ["Docker", "Kubernetes", "AWS"],
            "experience_summary": "DevOps specialist with cloud expertise",
            "value_proposition": "I streamline deployment processes",
            "target_roles": ["Senior DevOps Engineer", "Cloud Architect"],
            "notable_achievements": ["Reduced deployment time by 70%", "Implemented Kubernetes cluster"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_file:
            yaml.dump(yaml_data, yaml_file)
            yaml_path = yaml_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as md_file:
            md_path = md_file.name
        
        try:
            # Load from YAML
            profile = self.manager.load_profile_from_yaml(yaml_path)
            
            # Save to markdown
            self.manager.save_profile_to_markdown(profile, md_path)
            
            # Load from markdown to verify
            md_profile = self.manager.load_profile_from_markdown(md_path)
            
            # Verify data is preserved
            assert md_profile.name == "Bob Wilson"
            assert md_profile.current_role == "DevOps Engineer"
            assert md_profile.years_experience == 6
            assert "Docker" in md_profile.key_skills
            assert "Kubernetes" in md_profile.key_skills
            assert "AWS" in md_profile.key_skills
            assert md_profile.experience_summary == "DevOps specialist with cloud expertise"
            assert md_profile.value_proposition == "I streamline deployment processes"
            assert len(md_profile.target_roles) == 2
            assert len(md_profile.notable_achievements) == 2
            
        finally:
            # Clean up
            os.unlink(yaml_path)
            os.unlink(md_path)
    
    def test_markdown_parsing_complex_sections(self):
        """Test parsing complex markdown sections with varied formatting."""
        # Create markdown with complex formatting
        markdown_content = """# Sender Profile

## Basic Information
- **Name**: Complex User
- **Current Role**: Senior Architect
- **Years of Experience**: 10
- **Location**: Remote
- **Remote Preference**: remote

## Professional Summary
Multi-line summary with
line breaks and special characters: @#$%^&*()
Should be preserved correctly.

## Key Skills
- Skill with: colons
- Skill with, commas
- Skill with (parentheses)
- Skill with [brackets]

## Experience Highlights
- Achievement with **bold** text
- Achievement with *italic* text
- Achievement with `code` blocks
- Achievement with [links](https://example.com)

## Value Proposition
Value proposition with multiple
lines and formatting: **bold**, *italic*, `code`

## Target Roles
- Role with: special formatting
- Another role with (details)

## Additional Context
This is free-form text that should be captured
in the additional_context dictionary.
Multiple lines should be preserved.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as md_file:
            md_file.write(markdown_content)
            md_path = md_file.name
        
        try:
            # Load from markdown
            profile = self.manager.load_profile_from_markdown(md_path)
            
            # Verify complex formatting is preserved
            assert profile.name == "Complex User"
            assert profile.current_role == "Senior Architect"
            assert profile.years_experience == 10
            assert profile.location == "Remote"
            assert profile.remote_preference == "remote"
            
            # Check multi-line text
            assert "Multi-line summary with" in profile.experience_summary
            assert "line breaks and special characters" in profile.experience_summary
            
            # Check skills with special characters
            assert any("colons" in skill for skill in profile.key_skills)
            assert any("commas" in skill for skill in profile.key_skills)
            assert any("parentheses" in skill for skill in profile.key_skills)
            assert any("brackets" in skill for skill in profile.key_skills)
            
            # Check achievements with formatting
            assert any("bold" in achievement for achievement in profile.notable_achievements)
            assert any("italic" in achievement for achievement in profile.notable_achievements)
            assert any("code" in achievement for achievement in profile.notable_achievements)
            assert any("links" in achievement for achievement in profile.notable_achievements)
            
            # Check multi-line value proposition
            assert "Value proposition with multiple" in profile.value_proposition
            assert "lines and formatting" in profile.value_proposition
            
            # Check roles with special formatting
            assert any("special formatting" in role for role in profile.target_roles)
            assert any("details" in role for role in profile.target_roles)
            
            # Check additional context
            assert "additional_context" in profile.to_dict()
            assert isinstance(profile.additional_context, dict)
            assert "notes" in profile.additional_context
            assert "This is free-form text" in profile.additional_context["notes"]
            
        finally:
            # Clean up
            os.unlink(md_path)
    
    def test_profile_validation_and_suggestions(self):
        """Test profile validation and improvement suggestions."""
        # Create an incomplete profile
        incomplete_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            experience_summary="Short summary",  # Too short
            value_proposition="Short value",     # Too short
            target_roles=["Developer"]
        )
        
        # Validate profile
        is_valid, issues = self.manager.validate_profile(incomplete_profile)
        
        # Should be valid for basic validation but have completeness issues
        assert is_valid is False
        assert any("incomplete" in issue.lower() for issue in issues)
        
        # Get improvement suggestions
        suggestions = self.manager.get_profile_suggestions(incomplete_profile)
        
        # Should have suggestions for improvement
        assert len(suggestions) > 0
        assert any("experience summary" in suggestion.lower() for suggestion in suggestions)
        assert any("value proposition" in suggestion.lower() for suggestion in suggestions)
        assert any("notable achievements" in suggestion.lower() for suggestion in suggestions)
        
        # Create a more complete profile
        complete_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React", "AWS", "Docker"],
            experience_summary="Experienced developer with 5 years in web development and cloud infrastructure",
            value_proposition="I build scalable web applications that drive business growth through efficient architecture",
            target_roles=["Tech Lead", "Senior Engineer", "Cloud Architect"],
            notable_achievements=["Led team of 5 developers", "Reduced API response time by 40%"],
            portfolio_links=["https://example.com"],
            location="San Francisco",
            remote_preference="hybrid"
        )
        
        # Validate complete profile
        is_valid, issues = self.manager.validate_profile(complete_profile)
        
        # Should be valid with no issues
        assert is_valid is True
        assert len(issues) == 0
        
        # Get suggestions for complete profile
        suggestions = self.manager.get_profile_suggestions(complete_profile)
        
        # Should have fewer suggestions
        assert len(suggestions) < len(self.manager.get_profile_suggestions(incomplete_profile))


class TestSenderProfileInteractiveSetup:
    """Test cases for interactive profile setup with various input scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = SenderProfileManager()
    
    @patch('builtins.input')
    def test_interactive_setup_with_minimal_inputs(self, mock_input):
        """Test interactive setup with minimal required inputs."""
        # Mock minimal user inputs
        inputs = [
            "John Doe",                # name
            "Developer",               # current_role
            "2",                       # years_experience
            "",                        # location (empty)
            "",                        # remote_preference (empty)
            "",                        # availability (empty)
            "",                        # salary_expectations (empty)
            "Junior developer",        # experience_summary
            "",                        # end multiline
            "I write clean code",      # value_proposition
            "",                        # end multiline
            "Python",                  # skill 1
            "",                        # end skills
            "Software Engineer",       # target role 1
            "",                        # end target roles
            "",                        # end achievements (empty)
            "",                        # end education (empty)
            "",                        # end certifications (empty)
            "",                        # end industries (empty)
            "",                        # end portfolio links (empty)
            ""                         # preferred_contact_method (default)
        ]
        mock_input.side_effect = inputs
        
        # Create profile interactively
        profile = self.manager.create_profile_interactively()
        
        # Verify minimal profile
        assert profile.name == "John Doe"
        assert profile.current_role == "Developer"
        assert profile.years_experience == 2
        assert profile.experience_summary == "Junior developer"
        assert profile.value_proposition == "I write clean code"
        assert len(profile.key_skills) == 1
        assert profile.key_skills[0] == "Python"
        assert len(profile.target_roles) == 1
        assert profile.target_roles[0] == "Software Engineer"
        assert profile.preferred_contact_method == "email"  # Default
        
        # Verify profile is complete despite being minimal
        assert profile.is_complete() is True
    
    @patch('builtins.input')
    def test_interactive_setup_with_invalid_inputs(self, mock_input):
        """Test interactive setup with invalid inputs that require correction."""
        # Mock inputs with invalid values that need correction
        inputs = [
            "",                        # empty name (invalid)
            "John Doe",                # valid name
            "Developer",               # current_role
            "invalid",                 # invalid years_experience
            "-1",                      # negative years (invalid)
            "2",                       # valid years
            "",                        # location (empty)
            "invalid_preference",      # invalid remote_preference
            "",                        # skip remote preference
            "",                        # availability (empty)
            "",                        # salary_expectations (empty)
            "Junior developer",        # experience_summary
            "",                        # end multiline
            "I write clean code",      # value_proposition
            "",                        # end multiline
            "Python",                  # skill 1
            "",                        # end skills
            "Software Engineer",       # target role 1
            "",                        # end target roles
            "",                        # end achievements (empty)
            "",                        # end education (empty)
            "",                        # end certifications (empty)
            "",                        # end industries (empty)
            "invalid-url",             # invalid portfolio URL
            "https://example.com",     # valid URL
            "",                        # end portfolio links
            "invalid_method",          # invalid contact method
            "email"                    # valid contact method
        ]
        mock_input.side_effect = inputs
        
        # Create profile interactively
        profile = self.manager.create_profile_interactively()
        
        # Verify profile with corrected inputs
        assert profile.name == "John Doe"
        assert profile.current_role == "Developer"
        assert profile.years_experience == 2
        assert profile.remote_preference == ""  # Should be empty after invalid input
        assert len(profile.portfolio_links) == 1
        assert profile.portfolio_links[0] == "https://example.com"
        assert profile.preferred_contact_method == "email"
    
    @patch('builtins.input')
    def test_interactive_setup_with_comprehensive_inputs(self, mock_input):
        """Test interactive setup with comprehensive inputs for all fields."""
        # Mock comprehensive user inputs
        inputs = [
            "Jane Smith",              # name
            "Senior Engineer",         # current_role
            "8",                       # years_experience
            "New York, NY",            # location
            "hybrid",                  # remote_preference
            "Available in 4 weeks",    # availability
            "$130k-$160k",             # salary_expectations
            "Experienced engineer with focus on scalable systems.",  # experience_summary
            "Led multiple teams and projects to successful delivery.",
            "",                        # end multiline
            "I build robust, maintainable systems that scale.",  # value_proposition
            "",                        # end multiline
            "Python",                  # skill 1
            "Java",                    # skill 2
            "Kubernetes",              # skill 3
            "AWS",                     # skill 4
            "System Design",           # skill 5
            "",                        # end skills
            "Engineering Manager",     # target role 1
            "Technical Lead",          # target role 2
            "Senior Backend Engineer", # target role 3
            "",                        # end target roles
            "Reduced infrastructure costs by 30%",  # achievement 1
            "Led migration to microservices architecture",  # achievement 2
            "Mentored 5 junior engineers to promotion",  # achievement 3
            "",                        # end achievements
            "MS Computer Science - Columbia University",  # education 1
            "BS Computer Engineering - MIT",  # education 2
            "",                        # end education
            "AWS Certified Solutions Architect",  # certification 1
            "Certified Kubernetes Administrator",  # certification 2
            "",                        # end certifications
            "FinTech",                 # industry 1
            "Healthcare",              # industry 2
            "E-commerce",              # industry 3
            "",                        # end industries
            "https://janesmith.dev",   # portfolio link 1
            "https://github.com/janesmith",  # portfolio link 2
            "https://linkedin.com/in/janesmith",  # portfolio link 3
            "",                        # end portfolio links
            "linkedin"                 # preferred_contact_method
        ]
        mock_input.side_effect = inputs
        
        # Create profile interactively
        profile = self.manager.create_profile_interactively()
        
        # Verify comprehensive profile
        assert profile.name == "Jane Smith"
        assert profile.current_role == "Senior Engineer"
        assert profile.years_experience == 8
        assert profile.location == "New York, NY"
        assert profile.remote_preference == "hybrid"
        assert profile.availability == "Available in 4 weeks"
        assert profile.salary_expectations == "$130k-$160k"
        assert "Experienced engineer" in profile.experience_summary
        assert "Led multiple teams" in profile.experience_summary
        assert "build robust, maintainable systems" in profile.value_proposition
        assert len(profile.key_skills) == 5
        assert "Python" in profile.key_skills
        assert "Kubernetes" in profile.key_skills
        assert len(profile.target_roles) == 3
        assert "Engineering Manager" in profile.target_roles
        assert "Technical Lead" in profile.target_roles
        assert len(profile.notable_achievements) == 3
        assert any("infrastructure costs" in achievement for achievement in profile.notable_achievements)
        assert len(profile.education) == 2
        assert any("Columbia" in edu for edu in profile.education)
        assert len(profile.certifications) == 2
        assert any("Kubernetes" in cert for cert in profile.certifications)
        assert len(profile.industries_of_interest) == 3
        assert "FinTech" in profile.industries_of_interest
        assert len(profile.portfolio_links) == 3
        assert any("github.com" in link for link in profile.portfolio_links)
        assert profile.preferred_contact_method == "linkedin"
        
        # Verify profile is complete
        assert profile.is_complete() is True
        assert profile.get_completeness_score() > 0.9  # Should be very complete


class TestSenderContextMatching:
    """Test cases for sender context matching and relevance scoring."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.email_generator = EmailGenerator()
        
        # Create a comprehensive sender profile
        self.sender_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=8,
            key_skills=["Python", "JavaScript", "React", "AWS", "Machine Learning", "Docker"],
            experience_summary="Experienced full-stack developer with 8 years in web development and cloud infrastructure",
            education=["BS Computer Science - MIT"],
            certifications=["AWS Certified Developer", "Certified Scrum Master"],
            value_proposition="I build scalable web applications that drive business growth",
            target_roles=["Senior Developer", "Tech Lead", "Engineering Manager"],
            industries_of_interest=["FinTech", "Healthcare", "EdTech"],
            notable_achievements=[
                "Led team of 5 developers to deliver major platform upgrade",
                "Reduced API response time by 40% through optimization",
                "Implemented machine learning pipeline for fintech startup",
                "Built React dashboard for healthcare analytics",
                "Led AWS migration for e-commerce platform"
            ],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
            preferred_contact_method="email",
            availability="Available with 2 weeks notice",
            location="San Francisco, CA",
            remote_preference="hybrid"
        )
        
        # Create mock prospects for different industries/roles
        self.fintech_prospect = MagicMock()
        self.fintech_prospect.name = "Jane Smith"
        self.fintech_prospect.role = "CTO"
        self.fintech_prospect.company = "FinTech Startup"
        
        self.healthcare_prospect = MagicMock()
        self.healthcare_prospect.name = "Bob Johnson"
        self.healthcare_prospect.role = "Lead Frontend Developer"
        self.healthcare_prospect.company = "Healthcare Analytics"
        
        self.ecommerce_prospect = MagicMock()
        self.ecommerce_prospect.name = "Alice Brown"
        self.ecommerce_prospect.role = "DevOps Engineer"
        self.ecommerce_prospect.company = "E-commerce Platform"
    
    def test_get_relevant_sender_experience(self):
        """Test _get_relevant_sender_experience method."""
        # Test with fintech prospect
        fintech_experience = self.email_generator._get_relevant_sender_experience(
            self.sender_profile, self.fintech_prospect
        )
        assert fintech_experience
        assert "fintech" in fintech_experience.lower()
        
        # Test with healthcare prospect
        healthcare_experience = self.email_generator._get_relevant_sender_experience(
            self.sender_profile, self.healthcare_prospect
        )
        assert healthcare_experience
        assert "healthcare" in healthcare_experience.lower()
        assert "react" in healthcare_experience.lower()
        
        # Test with ecommerce prospect
        ecommerce_experience = self.email_generator._get_relevant_sender_experience(
            self.sender_profile, self.ecommerce_prospect
        )
        assert ecommerce_experience
        assert "aws" in ecommerce_experience.lower() or "e-commerce" in ecommerce_experience.lower()
    
    def test_get_sender_industry_match(self):
        """Test _get_sender_industry_match method."""
        # Test with fintech prospect
        fintech_match = self.email_generator._get_sender_industry_match(
            self.sender_profile, self.fintech_prospect
        )
        assert fintech_match
        assert "fintech" in fintech_match.lower()
        
        # Test with healthcare prospect
        healthcare_match = self.email_generator._get_sender_industry_match(
            self.sender_profile, self.healthcare_prospect
        )
        assert healthcare_match
        assert "healthcare" in healthcare_match.lower()
        
        # Test with industry not in interests
        retail_prospect = MagicMock()
        retail_prospect.company = "Retail Company"
        retail_prospect.role = "Developer"
        
        retail_match = self.email_generator._get_sender_industry_match(
            self.sender_profile, retail_prospect
        )
        assert not retail_match  # Should be empty since retail is not in interests
    
    def test_get_sender_skill_match(self):
        """Test _get_sender_skill_match method."""
        # Test with frontend developer prospect
        frontend_match = self.email_generator._get_sender_skill_match(
            self.sender_profile, self.healthcare_prospect
        )
        assert frontend_match
        assert "react" in frontend_match.lower() or "javascript" in frontend_match.lower()
        
        # Test with DevOps prospect
        devops_match = self.email_generator._get_sender_skill_match(
            self.sender_profile, self.ecommerce_prospect
        )
        assert devops_match
        assert "aws" in devops_match.lower() or "docker" in devops_match.lower()
        
        # Test with role that doesn't match skills
        marketing_prospect = MagicMock()
        marketing_prospect.role = "Marketing Manager"
        marketing_prospect.company = "Tech Company"
        
        marketing_match = self.email_generator._get_sender_skill_match(
            self.sender_profile, marketing_prospect
        )
        assert not marketing_match  # Should be empty or generic since no direct skill match
    
    def test_match_sender_achievements_to_company_needs(self):
        """Test match_sender_achievements_to_company_needs method."""
        # Test with fintech prospect
        fintech_achievements = self.email_generator.match_sender_achievements_to_company_needs(
            self.sender_profile, self.fintech_prospect
        )
        assert fintech_achievements
        assert any("fintech" in achievement.lower() for achievement in fintech_achievements)
        
        # Test with healthcare prospect
        healthcare_achievements = self.email_generator.match_sender_achievements_to_company_needs(
            self.sender_profile, self.healthcare_prospect
        )
        assert healthcare_achievements
        assert any("healthcare" in achievement.lower() for achievement in healthcare_achievements)
        
        # Test with product context
        product_context = {
            "business_insights": "Early-stage startup looking to scale",
            "product_features": "Machine learning, API optimization"
        }
        
        context_achievements = self.email_generator.match_sender_achievements_to_company_needs(
            self.sender_profile, self.fintech_prospect, product_context
        )
        assert context_achievements
        assert any("api" in achievement.lower() for achievement in context_achievements) or \
               any("machine learning" in achievement.lower() for achievement in context_achievements)
    
    def test_get_dynamic_sender_highlights(self):
        """Test get_dynamic_sender_highlights method."""
        # Test with senior role prospect
        senior_highlights = self.email_generator.get_dynamic_sender_highlights(
            self.sender_profile, self.fintech_prospect
        )
        assert senior_highlights
        assert "primary_introduction" in senior_highlights
        assert "key_achievement" in senior_highlights
        assert "value_connection" in senior_highlights
        assert "availability_note" in senior_highlights
        
        # Verify leadership emphasis for senior role
        assert "led" in senior_highlights["primary_introduction"].lower() or \
               "senior" in senior_highlights["primary_introduction"].lower()
        
        # Test with frontend role prospect
        frontend_highlights = self.email_generator.get_dynamic_sender_highlights(
            self.sender_profile, self.healthcare_prospect
        )
        assert frontend_highlights
        
        # Verify frontend skills emphasis
        assert "react" in frontend_highlights["primary_introduction"].lower() or \
               "javascript" in frontend_highlights["primary_introduction"].lower() or \
               "frontend" in frontend_highlights["primary_introduction"].lower()
        
        # Test with product context
        product_context = {
            "business_insights": "Early-stage startup looking to scale",
            "product_features": "Cloud infrastructure, API optimization"
        }
        
        context_highlights = self.email_generator.get_dynamic_sender_highlights(
            self.sender_profile, self.ecommerce_prospect, product_context
        )
        assert context_highlights
        
        # Verify context-specific value connection
        assert "scale" in context_highlights["value_connection"].lower() or \
               "cloud" in context_highlights["value_connection"].lower() or \
               "api" in context_highlights["value_connection"].lower()
    
    def test_create_contextual_email_sections(self):
        """Test create_contextual_email_sections method."""
        # Test with fintech prospect
        fintech_sections = self.email_generator.create_contextual_email_sections(
            self.sender_profile, self.fintech_prospect
        )
        assert fintech_sections
        assert "sender_introduction" in fintech_sections
        assert "skill_connection" in fintech_sections
        assert "value_proposition" in fintech_sections
        
        # Verify fintech-specific content
        assert "fintech" in ' '.join(fintech_sections.values()).lower() or \
               "financial" in ' '.join(fintech_sections.values()).lower()
        
        # Test with product context
        product_context = {
            "business_insights": "Series A startup with machine learning focus",
            "product_features": "AI-powered analytics"
        }
        
        context_sections = self.email_generator.create_contextual_email_sections(
            self.sender_profile, self.healthcare_prospect, product_context
        )
        assert context_sections
        
        # Verify context-specific content
        combined_sections = ' '.join(context_sections.values()).lower()
        assert "machine learning" in combined_sections or \
               "ai" in combined_sections or \
               "analytics" in combined_sections