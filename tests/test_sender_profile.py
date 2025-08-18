"""
Unit tests for SenderProfile data model and validation.
"""
import pytest
from datetime import datetime
from models.data_models import SenderProfile, ValidationError


class TestSenderProfile:
    """Test cases for SenderProfile data model."""
    
    def test_valid_sender_profile_creation(self):
        """Test creating a valid sender profile."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React"],
            experience_summary="Experienced full-stack developer with 5 years in web development",
            education=["BS Computer Science - MIT"],
            certifications=["AWS Certified Developer"],
            value_proposition="I build scalable web applications that drive business growth",
            target_roles=["Senior Developer", "Tech Lead"],
            industries_of_interest=["FinTech", "Healthcare"],
            notable_achievements=["Led team of 5 developers", "Reduced API response time by 40%"],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
            preferred_contact_method="email",
            availability="Available immediately",
            location="San Francisco, CA",
            remote_preference="hybrid",
            salary_expectations="$120k-$150k",
            additional_context={"timezone": "PST"}
        )
        
        assert profile.name == "John Doe"
        assert profile.current_role == "Senior Software Engineer"
        assert profile.years_experience == 5
        assert len(profile.key_skills) == 3
        assert profile.is_complete() is True
    
    def test_minimal_valid_profile(self):
        """Test creating a minimal valid profile."""
        profile = SenderProfile(
            name="Jane Smith",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            experience_summary="Junior developer with Python experience",
            value_proposition="I write clean, maintainable code",
            target_roles=["Software Engineer"]
        )
        
        assert profile.name == "Jane Smith"
        assert profile.is_complete() is True
    
    def test_empty_name_validation(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValidationError, match="Sender name cannot be empty"):
            SenderProfile(
                name="",
                current_role="Developer",
                years_experience=2
            )
    
    def test_empty_current_role_validation(self):
        """Test validation fails for empty current role."""
        with pytest.raises(ValidationError, match="Current role cannot be empty"):
            SenderProfile(
                name="John Doe",
                current_role="",
                years_experience=2
            )
    
    def test_negative_years_experience_validation(self):
        """Test validation fails for negative years of experience."""
        with pytest.raises(ValidationError, match="Years of experience must be a non-negative integer"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=-1
            )
    
    def test_unrealistic_years_experience_validation(self):
        """Test validation fails for unrealistic years of experience."""
        with pytest.raises(ValidationError, match="Years of experience seems unrealistic"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=80
            )
    
    def test_invalid_portfolio_url_validation(self):
        """Test validation fails for invalid portfolio URLs."""
        with pytest.raises(ValidationError, match="Invalid portfolio URL format"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                portfolio_links=["not-a-valid-url"]
            )
    
    def test_invalid_contact_method_validation(self):
        """Test validation fails for invalid contact method."""
        with pytest.raises(ValidationError, match="Preferred contact method must be one of"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                preferred_contact_method="invalid_method"
            )
    
    def test_invalid_remote_preference_validation(self):
        """Test validation fails for invalid remote preference."""
        with pytest.raises(ValidationError, match="Remote preference must be one of"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                remote_preference="invalid_preference"
            )
    
    def test_list_field_validation(self):
        """Test validation of list fields."""
        # Test that non-list values raise errors
        with pytest.raises(ValidationError, match="key_skills must be a list"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                key_skills="not a list"
            )
    
    def test_list_field_cleanup(self):
        """Test that empty strings are cleaned from list fields."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python", "", "JavaScript", "   ", "React"],
            education=["", "BS Computer Science", ""]
        )
        
        assert profile.key_skills == ["Python", "JavaScript", "React"]
        assert profile.education == ["BS Computer Science"]
    
    def test_is_complete_method(self):
        """Test the is_complete method."""
        # Complete profile
        complete_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            experience_summary="Experienced developer",
            value_proposition="I build great software",
            target_roles=["Senior Developer"]
        )
        assert complete_profile.is_complete() is True
        
        # Incomplete profile - missing experience summary
        incomplete_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            value_proposition="I build great software",
            target_roles=["Senior Developer"]
        )
        assert incomplete_profile.is_complete() is False
        
        # Incomplete profile - no skills
        incomplete_profile2 = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            experience_summary="Experienced developer",
            value_proposition="I build great software",
            target_roles=["Senior Developer"]
        )
        assert incomplete_profile2.is_complete() is False
    
    def test_completeness_score(self):
        """Test the completeness score calculation."""
        # Minimal profile
        minimal_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2
        )
        score = minimal_profile.get_completeness_score()
        assert 0.0 <= score <= 1.0
        assert score < 0.5  # Should be low for minimal profile
        
        # Complete profile
        complete_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "JavaScript"],
            experience_summary="Experienced full-stack developer",
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
        score = complete_profile.get_completeness_score()
        assert score > 0.8  # Should be high for complete profile
    
    def test_missing_fields_method(self):
        """Test the get_missing_fields method."""
        incomplete_profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2
        )
        
        missing = incomplete_profile.get_missing_fields()
        expected_missing = ["experience_summary", "value_proposition", "key_skills", "target_roles"]
        
        for field in expected_missing:
            assert field in missing
    
    def test_relevant_experience_method(self):
        """Test the get_relevant_experience method."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Python Developer",
            years_experience=5,
            key_skills=["Python", "Django", "React", "AWS"],
            experience_summary="Full-stack developer with Python expertise",
            notable_achievements=[
                "Built scalable Python API serving 1M+ requests",
                "Led Django migration project",
                "Implemented React frontend for fintech app"
            ]
        )
        
        # Test role matching
        relevant = profile.get_relevant_experience("Python Developer")
        assert any("Python" in item for item in relevant)
        
        # Test company matching
        relevant_company = profile.get_relevant_experience("Developer", "fintech")
        assert any("fintech" in item.lower() for item in relevant_company)
    
    def test_to_dict_serialization(self):
        """Test serialization to dictionary."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Developer",
            years_experience=2,
            key_skills=["Python"],
            additional_context={"test": "value"}
        )
        
        data = profile.to_dict()
        
        assert isinstance(data, dict)
        assert data["name"] == "John Doe"
        assert data["current_role"] == "Developer"
        assert data["years_experience"] == 2
        assert data["key_skills"] == ["Python"]
        assert data["additional_context"] == {"test": "value"}
    
    def test_from_dict_deserialization(self):
        """Test deserialization from dictionary."""
        data = {
            "name": "Jane Smith",
            "current_role": "Senior Engineer",
            "years_experience": 7,
            "key_skills": ["Java", "Spring"],
            "experience_summary": "Backend developer",
            "value_proposition": "I build robust systems",
            "target_roles": ["Tech Lead"]
        }
        
        profile = SenderProfile.from_dict(data)
        
        assert profile.name == "Jane Smith"
        assert profile.current_role == "Senior Engineer"
        assert profile.years_experience == 7
        assert profile.key_skills == ["Java", "Spring"]
        assert profile.is_complete() is True
    
    def test_from_dict_with_missing_fields(self):
        """Test deserialization with missing fields uses defaults."""
        data = {
            "name": "John Doe",
            "current_role": "Developer"
        }
        
        profile = SenderProfile.from_dict(data)
        
        assert profile.name == "John Doe"
        assert profile.current_role == "Developer"
        assert profile.years_experience == 0
        assert profile.key_skills == []
        assert profile.preferred_contact_method == "email"
    
    def test_valid_remote_preferences(self):
        """Test all valid remote preferences are accepted."""
        valid_prefs = ["remote", "hybrid", "on-site", "flexible"]
        
        for pref in valid_prefs:
            profile = SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                remote_preference=pref
            )
            assert profile.remote_preference == pref
    
    def test_valid_contact_methods(self):
        """Test all valid contact methods are accepted."""
        valid_methods = ["email", "linkedin", "phone", "other"]
        
        for method in valid_methods:
            profile = SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                preferred_contact_method=method
            )
            assert profile.preferred_contact_method == method
    
    def test_additional_context_validation(self):
        """Test additional context must be a dictionary."""
        with pytest.raises(ValidationError, match="Additional context must be a dictionary"):
            SenderProfile(
                name="John Doe",
                current_role="Developer",
                years_experience=2,
                additional_context="not a dict"
            )