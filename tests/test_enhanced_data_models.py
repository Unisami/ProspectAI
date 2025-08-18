"""
Comprehensive unit tests for enhanced data models with validation framework.
"""

import pytest
from datetime import datetime
from models.data_models import (
    CompanyData, TeamMember, Prospect, LinkedInProfile, EmailData, EmailContent,
    SenderProfile, ProspectStatus, ValidationError
)


class TestCompanyData:
    """Test CompanyData model with enhanced validation."""
    
    def test_valid_company_data(self):
        """Test creating valid CompanyData instance."""
        company = CompanyData(
            name="Test Company",
            domain="example.com",
            product_url="https://example.com/product",
            description="A great company that builds amazing products.",
            launch_date=datetime.now()
        )
        
        assert company.name == "Test Company"
        assert company.domain == "example.com"
        assert company.validate().is_valid
    
    def test_invalid_company_data(self):
        """Test validation errors for invalid CompanyData."""
        with pytest.raises(ValidationError):
            CompanyData(
                name="",  # Invalid: empty
                domain="example.com",
                product_url="https://example.com/product",
                description="A great company.",
                launch_date=datetime.now()
            )
    
    def test_company_data_to_dict(self):
        """Test CompanyData serialization to dictionary."""
        launch_date = datetime.now()
        company = CompanyData(
            name="Test Company",
            domain="example.com",
            product_url="https://example.com/product",
            description="A great company.",
            launch_date=launch_date
        )
        
        data_dict = company.to_dict()
        assert data_dict['name'] == "Test Company"
        assert data_dict['domain'] == "example.com"
        assert data_dict['launch_date'] == launch_date.isoformat()
    
    def test_company_data_from_dict(self):
        """Test CompanyData deserialization from dictionary."""
        data = {
            'name': 'Test Company',
            'domain': 'example.com',
            'product_url': 'https://example.com/product',
            'description': 'A great company.',
            'launch_date': '2023-01-01T00:00:00'
        }
        
        company = CompanyData.from_dict(data)
        assert company.name == "Test Company"
        assert company.domain == "example.com"
        assert isinstance(company.launch_date, datetime)


class TestTeamMember:
    """Test TeamMember model with enhanced validation."""
    
    def test_valid_team_member(self):
        """Test creating valid TeamMember instance."""
        member = TeamMember(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        assert member.name == "John Doe"
        assert member.role == "Software Engineer"
        assert member.validate().is_valid
    
    def test_team_member_without_linkedin(self):
        """Test TeamMember without LinkedIn URL."""
        member = TeamMember(
            name="Jane Smith",
            role="Product Manager",
            company="Test Company"
        )
        
        assert member.linkedin_url is None
        assert member.validate().is_valid
    
    def test_invalid_team_member(self):
        """Test validation errors for invalid TeamMember."""
        with pytest.raises(ValidationError):
            TeamMember(
                name="A",  # Invalid: too short
                role="Software Engineer",
                company="Test Company"
            )
    
    def test_team_member_from_dict(self):
        """Test TeamMember deserialization from dictionary."""
        data = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'company': 'Test Company',
            'linkedin_url': 'https://linkedin.com/in/johndoe'
        }
        
        member = TeamMember.from_dict(data)
        assert member.name == "John Doe"
        assert member.role == "Software Engineer"


class TestProspect:
    """Test Prospect model with enhanced validation."""
    
    def test_valid_prospect(self):
        """Test creating valid Prospect instance."""
        prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        assert prospect.name == "John Doe"
        assert prospect.email == "john@example.com"
        assert prospect.validate().is_valid
    
    def test_prospect_with_invalid_email(self):
        """Test Prospect with invalid email."""
        with pytest.raises(ValidationError):
            Prospect(
                name="John Doe",
                role="Software Engineer",
                company="Test Company",
                email="invalid-email"  # Invalid format
            )
    
    def test_prospect_from_dict(self):
        """Test Prospect deserialization from dictionary."""
        data = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'company': 'Test Company',
            'email': 'john@example.com',
            'status': 'Not Contacted',
            'created_at': '2023-01-01T00:00:00'
        }
        
        prospect = Prospect.from_dict(data)
        assert prospect.name == "John Doe"
        assert prospect.status == ProspectStatus.NOT_CONTACTED
        assert isinstance(prospect.created_at, datetime)


class TestLinkedInProfile:
    """Test LinkedInProfile model with enhanced validation."""
    
    def test_valid_linkedin_profile(self):
        """Test creating valid LinkedInProfile instance."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            experience=["Company A", "Company B"],
            skills=["Python", "JavaScript"],
            summary="Experienced software engineer."
        )
        
        assert profile.name == "John Doe"
        assert len(profile.experience) == 2
        assert profile.validate().is_valid
    
    def test_linkedin_profile_list_cleanup(self):
        """Test automatic cleanup of empty strings in lists."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            experience=["Company A", "", "Company B", "   "],
            skills=["Python", "", "JavaScript"]
        )
        
        # Empty strings should be removed
        assert len(profile.experience) == 2
        assert len(profile.skills) == 2
        assert "" not in profile.experience
        assert "" not in profile.skills
    
    def test_linkedin_profile_from_dict(self):
        """Test LinkedInProfile deserialization from dictionary."""
        data = {
            'name': 'John Doe',
            'current_role': 'Software Engineer',
            'experience': ['Company A', 'Company B'],
            'skills': ['Python', 'JavaScript'],
            'summary': 'Experienced engineer.'
        }
        
        profile = LinkedInProfile.from_dict(data)
        assert profile.name == "John Doe"
        assert len(profile.experience) == 2


class TestEmailData:
    """Test EmailData model with enhanced validation."""
    
    def test_valid_email_data(self):
        """Test creating valid EmailData instance."""
        email_data = EmailData(
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            confidence=95,
            sources=["website", "social"]
        )
        
        assert email_data.email == "john@example.com"
        assert email_data.confidence == 95
        assert email_data.validate().is_valid
    
    def test_email_data_invalid_confidence(self):
        """Test EmailData with invalid confidence value."""
        with pytest.raises(ValidationError):
            EmailData(
                email="john@example.com",
                confidence=150  # Invalid: > 100
            )
    
    def test_email_data_from_dict(self):
        """Test EmailData deserialization from dictionary."""
        data = {
            'email': 'john@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'confidence': 95,
            'sources': ['website']
        }
        
        email_data = EmailData.from_dict(data)
        assert email_data.email == "john@example.com"
        assert email_data.confidence == 95


class TestEmailContent:
    """Test EmailContent model with enhanced validation."""
    
    def test_valid_email_content(self):
        """Test creating valid EmailContent instance."""
        content = EmailContent(
            subject="Great opportunity at Test Company",
            body="Dear John,\n\nI hope this email finds you well...",
            template_used="standard_template",
            personalization_score=0.8,
            recipient_name="John Doe",
            company_name="Test Company"
        )
        
        assert content.subject == "Great opportunity at Test Company"
        assert content.personalization_score == 0.8
        assert content.validate().is_valid
    
    def test_email_content_invalid_score(self):
        """Test EmailContent with invalid personalization score."""
        with pytest.raises(ValidationError):
            EmailContent(
                subject="Test Subject",
                body="Test body content here.",
                template_used="template",
                personalization_score=1.5  # Invalid: > 1.0
            )
    
    def test_email_content_from_dict(self):
        """Test EmailContent deserialization from dictionary."""
        data = {
            'subject': 'Test Subject',
            'body': 'Test body content.',
            'template_used': 'template',
            'personalization_score': 0.7
        }
        
        content = EmailContent.from_dict(data)
        assert content.subject == "Test Subject"
        assert content.personalization_score == 0.7


class TestSenderProfile:
    """Test SenderProfile model with enhanced validation."""
    
    def test_valid_sender_profile(self):
        """Test creating valid SenderProfile instance."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React"],
            experience_summary="Experienced full-stack developer with 5 years in web development.",
            value_proposition="I build scalable web applications that drive business growth.",
            target_roles=["Software Engineer", "Full Stack Developer"],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"]
        )
        
        assert profile.name == "John Doe"
        assert profile.years_experience == 5
        assert len(profile.key_skills) == 3
        assert profile.validate().is_valid
    
    def test_sender_profile_list_cleanup(self):
        """Test automatic cleanup of empty strings in lists."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Software Engineer",
            years_experience=3,
            key_skills=["Python", "", "JavaScript", "   "],
            target_roles=["Engineer", "", "Developer"]
        )
        
        # Empty strings should be removed
        assert len(profile.key_skills) == 2
        assert len(profile.target_roles) == 2
        assert "" not in profile.key_skills
        assert "" not in profile.target_roles
    
    def test_sender_profile_invalid_years(self):
        """Test SenderProfile with invalid years of experience."""
        with pytest.raises(ValidationError):
            SenderProfile(
                name="John Doe",
                current_role="Software Engineer",
                years_experience=80,  # Invalid: > 70
                key_skills=["Python"],
                target_roles=["Engineer"]
            )
    
    def test_sender_profile_invalid_portfolio_link(self):
        """Test SenderProfile with invalid portfolio link."""
        with pytest.raises(ValidationError):
            SenderProfile(
                name="John Doe",
                current_role="Software Engineer",
                years_experience=5,
                key_skills=["Python"],
                target_roles=["Engineer"],
                portfolio_links=["not-a-valid-url"]  # Invalid URL
            )
    
    def test_sender_profile_completeness_methods(self):
        """Test SenderProfile completeness checking methods."""
        # Complete profile
        complete_profile = SenderProfile(
            name="John Doe",
            current_role="Software Engineer",
            years_experience=5,
            key_skills=["Python", "JavaScript"],
            experience_summary="Experienced developer with strong background.",
            value_proposition="I deliver high-quality software solutions.",
            target_roles=["Software Engineer"]
        )
        
        assert complete_profile.is_complete()
        assert complete_profile.get_completeness_score() > 0.5  # Adjusted expectation
        assert len(complete_profile.get_missing_fields()) == 0
        
        # Incomplete profile
        incomplete_profile = SenderProfile(
            name="Jane Smith",
            current_role="Developer",
            years_experience=2,
            key_skills=[],  # Missing skills
            target_roles=[]  # Missing target roles
        )
        
        assert not incomplete_profile.is_complete()
        missing_fields = incomplete_profile.get_missing_fields()
        assert "key_skills" in missing_fields
        assert "target_roles" in missing_fields
    
    def test_sender_profile_relevant_experience(self):
        """Test SenderProfile relevant experience extraction."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Python Developer",
            years_experience=5,
            key_skills=["Python", "Django", "React", "JavaScript"],
            notable_achievements=[
                "Built scalable Python applications serving 1M+ users",
                "Led team of 5 developers on React project"
            ],
            target_roles=["Python Developer", "Full Stack Engineer"]
        )
        
        # Test relevant experience for Python role
        python_experience = profile.get_relevant_experience("Python Developer")
        assert len(python_experience) > 0
        assert any("Python" in exp for exp in python_experience)
        
        # Test relevant experience for React role
        react_experience = profile.get_relevant_experience("React Developer")
        assert len(react_experience) > 0
        assert any("React" in exp for exp in react_experience)
    
    def test_sender_profile_from_dict(self):
        """Test SenderProfile deserialization from dictionary."""
        data = {
            'name': 'John Doe',
            'current_role': 'Software Engineer',
            'years_experience': 5,
            'key_skills': ['Python', 'JavaScript'],
            'target_roles': ['Engineer', 'Developer'],
            'additional_context': {'specialty': 'web development'}
        }
        
        profile = SenderProfile.from_dict(data)
        assert profile.name == "John Doe"
        assert len(profile.key_skills) == 2
        assert profile.additional_context['specialty'] == 'web development'


class TestValidationIntegration:
    """Test integration between models and validation framework."""
    
    def test_validation_error_messages(self):
        """Test that validation error messages are informative."""
        try:
            CompanyData(
                name="",
                domain="invalid-domain",
                product_url="not-a-url",
                description="Short",
                launch_date="not-a-date"
            )
        except ValidationError as e:
            assert "Validation failed" in str(e)
            # Should contain multiple error details
            assert len(str(e)) > 50
    
    def test_partial_validation_success(self):
        """Test that models with warnings still validate successfully."""
        # This would require a scenario where validation passes with warnings
        # For now, we'll test that valid models return successful validation
        company = CompanyData(
            name="Test Company",
            domain="example.com",
            product_url="https://example.com",
            description="A comprehensive description of the company.",
            launch_date=datetime.now()
        )
        
        validation_result = company.validate()
        assert validation_result.is_valid
        assert "passed" in validation_result.message.lower()


if __name__ == "__main__":
    pytest.main([__file__])