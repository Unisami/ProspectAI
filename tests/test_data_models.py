"""
Unit tests for data models and validation.
"""
import pytest
from datetime import datetime
from models.data_models import (
    CompanyData, TeamMember, Prospect, LinkedInProfile, EmailContent,
    EmailData, EmailVerification, ProspectStatus, ValidationError
)


class TestCompanyData:
    """Test cases for CompanyData model."""
    
    def test_valid_company_data(self):
        """Test creating valid company data."""
        company = CompanyData(
            name="Test Company",
            domain="testcompany.com",
            product_url="https://producthunt.com/posts/test-product",
            description="A test company description",
            launch_date=datetime.now()
        )
        assert company.name == "Test Company"
        assert company.domain == "testcompany.com"
        
    def test_empty_name_validation(self):
        """Test validation fails for empty company name."""
        with pytest.raises(ValidationError, match="Company name cannot be empty"):
            CompanyData(
                name="",
                domain="testcompany.com",
                product_url="https://producthunt.com/posts/test-product",
                description="A test company description",
                launch_date=datetime.now()
            )
    
    def test_empty_domain_validation(self):
        """Test validation fails for empty domain."""
        with pytest.raises(ValidationError, match="Company domain cannot be empty"):
            CompanyData(
                name="Test Company",
                domain="",
                product_url="https://producthunt.com/posts/test-product",
                description="A test company description",
                launch_date=datetime.now()
            )
    
    def test_invalid_domain_format(self):
        """Test validation fails for invalid domain format."""
        with pytest.raises(ValidationError, match="Invalid domain format"):
            CompanyData(
                name="Test Company",
                domain="invalid-domain",
                product_url="https://producthunt.com/posts/test-product",
                description="A test company description",
                launch_date=datetime.now()
            )
    
    def test_invalid_url_format(self):
        """Test validation fails for invalid URL format."""
        with pytest.raises(ValidationError, match="Invalid product URL format"):
            CompanyData(
                name="Test Company",
                domain="testcompany.com",
                product_url="not-a-url",
                description="A test company description",
                launch_date=datetime.now()
            )
    
    def test_empty_description_validation(self):
        """Test validation fails for empty description."""
        with pytest.raises(ValidationError, match="Company description cannot be empty"):
            CompanyData(
                name="Test Company",
                domain="testcompany.com",
                product_url="https://producthunt.com/posts/test-product",
                description="",
                launch_date=datetime.now()
            )
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        launch_date = datetime.now()
        company = CompanyData(
            name="Test Company",
            domain="testcompany.com",
            product_url="https://producthunt.com/posts/test-product",
            description="A test company description",
            launch_date=launch_date
        )
        
        result = company.to_dict()
        expected = {
            'name': "Test Company",
            'domain': "testcompany.com",
            'product_url': "https://producthunt.com/posts/test-product",
            'description': "A test company description",
            'launch_date': launch_date.isoformat()
        }
        assert result == expected


class TestTeamMember:
    """Test cases for TeamMember model."""
    
    def test_valid_team_member(self):
        """Test creating valid team member."""
        member = TeamMember(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        assert member.name == "John Doe"
        assert member.role == "Software Engineer"
        assert member.company == "Test Company"
        assert member.linkedin_url == "https://linkedin.com/in/johndoe"
    
    def test_team_member_without_linkedin(self):
        """Test creating team member without LinkedIn URL."""
        member = TeamMember(
            name="Jane Smith",
            role="Product Manager",
            company="Test Company"
        )
        assert member.linkedin_url is None
    
    def test_empty_name_validation(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValidationError, match="Team member name cannot be empty"):
            TeamMember(
                name="",
                role="Software Engineer",
                company="Test Company"
            )
    
    def test_empty_role_validation(self):
        """Test validation fails for empty role."""
        with pytest.raises(ValidationError, match="Team member role cannot be empty"):
            TeamMember(
                name="John Doe",
                role="",
                company="Test Company"
            )
    
    def test_empty_company_validation(self):
        """Test validation fails for empty company."""
        with pytest.raises(ValidationError, match="Company name cannot be empty"):
            TeamMember(
                name="John Doe",
                role="Software Engineer",
                company=""
            )
    
    def test_invalid_linkedin_url(self):
        """Test validation fails for invalid LinkedIn URL."""
        with pytest.raises(ValidationError, match="Invalid LinkedIn URL format"):
            TeamMember(
                name="John Doe",
                role="Software Engineer",
                company="Test Company",
                linkedin_url="https://twitter.com/johndoe"
            )
    
    def test_empty_linkedin_url_cleanup(self):
        """Test empty LinkedIn URL is cleaned up to None."""
        member = TeamMember(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            linkedin_url="   "
        )
        assert member.linkedin_url is None
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        member = TeamMember(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        result = member.to_dict()
        expected = {
            'name': "John Doe",
            'role': "Software Engineer",
            'company': "Test Company",
            'linkedin_url': "https://linkedin.com/in/johndoe"
        }
        assert result == expected


class TestProspect:
    """Test cases for Prospect model."""
    
    def test_valid_prospect(self):
        """Test creating valid prospect."""
        prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="john@testcompany.com",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        assert prospect.name == "John Doe"
        assert prospect.role == "Software Engineer"
        assert prospect.company == "Test Company"
        assert prospect.email == "john@testcompany.com"
        assert prospect.contacted is False
        assert prospect.status == ProspectStatus.NOT_CONTACTED
    
    def test_prospect_with_minimal_data(self):
        """Test creating prospect with minimal required data."""
        prospect = Prospect(
            name="Jane Smith",
            role="Product Manager",
            company="Test Company"
        )
        assert prospect.email is None
        assert prospect.linkedin_url is None
        assert prospect.notes == ""
    
    def test_empty_name_validation(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValidationError, match="Prospect name cannot be empty"):
            Prospect(
                name="",
                role="Software Engineer",
                company="Test Company"
            )
    
    def test_invalid_email_format(self):
        """Test validation fails for invalid email format."""
        with pytest.raises(ValidationError, match="Invalid email format"):
            Prospect(
                name="John Doe",
                role="Software Engineer",
                company="Test Company",
                email="invalid-email"
            )
    
    def test_empty_email_cleanup(self):
        """Test empty email is cleaned up to None."""
        prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="   "
        )
        assert prospect.email is None
    
    def test_invalid_linkedin_url(self):
        """Test validation fails for invalid LinkedIn URL."""
        with pytest.raises(ValidationError, match="Invalid LinkedIn URL format"):
            Prospect(
                name="John Doe",
                role="Software Engineer",
                company="Test Company",
                linkedin_url="https://twitter.com/johndoe"
            )
    
    def test_prospect_status_enum(self):
        """Test prospect status enum values."""
        prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            status=ProspectStatus.CONTACTED
        )
        assert prospect.status == ProspectStatus.CONTACTED
        assert prospect.status.value == "Contacted"
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        created_at = datetime.now()
        prospect = Prospect(
            id="test-id",
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="john@testcompany.com",
            linkedin_url="https://linkedin.com/in/johndoe",
            contacted=True,
            status=ProspectStatus.CONTACTED,
            notes="Test notes",
            source_url="https://producthunt.com/posts/test-product",
            created_at=created_at
        )
        
        result = prospect.to_dict()
        expected = {
            'id': "test-id",
            'name': "John Doe",
            'role': "Software Engineer",
            'company': "Test Company",
            'linkedin_url': "https://linkedin.com/in/johndoe",
            'email': "john@testcompany.com",
            'contacted': True,
            'status': "Contacted",
            'notes': "Test notes",
            'source_url': "https://producthunt.com/posts/test-product",
            'created_at': created_at.isoformat()
        }
        assert result == expected


class TestLinkedInProfile:
    """Test cases for LinkedInProfile model."""
    
    def test_valid_linkedin_profile(self):
        """Test creating valid LinkedIn profile."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            experience=["Software Engineer at Company A", "Intern at Company B"],
            skills=["Python", "JavaScript", "React"],
            summary="Experienced software engineer"
        )
        assert profile.name == "John Doe"
        assert profile.current_role == "Software Engineer"
        assert len(profile.experience) == 2
        assert len(profile.skills) == 3
    
    def test_linkedin_profile_with_minimal_data(self):
        """Test creating LinkedIn profile with minimal data."""
        profile = LinkedInProfile(
            name="Jane Smith",
            current_role="Product Manager"
        )
        assert profile.experience == []
        assert profile.skills == []
        assert profile.summary == ""
    
    def test_empty_name_validation(self):
        """Test validation fails for empty name."""
        with pytest.raises(ValidationError, match="LinkedIn profile name cannot be empty"):
            LinkedInProfile(
                name="",
                current_role="Software Engineer"
            )
    
    def test_empty_role_validation(self):
        """Test validation fails for empty current role."""
        with pytest.raises(ValidationError, match="Current role cannot be empty"):
            LinkedInProfile(
                name="John Doe",
                current_role=""
            )
    
    def test_experience_list_cleanup(self):
        """Test experience list cleanup removes empty strings."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            experience=["Valid experience", "", "   ", "Another valid experience"]
        )
        assert len(profile.experience) == 2
        assert "Valid experience" in profile.experience
        assert "Another valid experience" in profile.experience
    
    def test_skills_list_cleanup(self):
        """Test skills list cleanup removes empty strings."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            skills=["Python", "", "   ", "JavaScript"]
        )
        assert len(profile.skills) == 2
        assert "Python" in profile.skills
        assert "JavaScript" in profile.skills
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        profile = LinkedInProfile(
            name="John Doe",
            current_role="Software Engineer",
            experience=["Software Engineer at Company A"],
            skills=["Python", "JavaScript"],
            summary="Experienced software engineer"
        )
        
        result = profile.to_dict()
        expected = {
            'name': "John Doe",
            'current_role': "Software Engineer",
            'experience': ["Software Engineer at Company A"],
            'skills': ["Python", "JavaScript"],
            'summary': "Experienced software engineer"
        }
        assert result == expected


class TestEmailContent:
    """Test cases for EmailContent model."""
    
    def test_valid_email_content(self):
        """Test creating valid email content."""
        email = EmailContent(
            subject="Job Opportunity at Your Company",
            body="Hello, I'm interested in opportunities at your company...",
            template_used="professional",
            personalization_score=0.8,
            recipient_name="John Doe",
            company_name="Test Company"
        )
        assert email.subject == "Job Opportunity at Your Company"
        assert email.personalization_score == 0.8
        assert email.recipient_name == "John Doe"
    
    def test_email_content_with_minimal_data(self):
        """Test creating email content with minimal data."""
        email = EmailContent(
            subject="Test Subject",
            body="Test body content",
            template_used="basic"
        )
        assert email.personalization_score == 0.0
        assert email.recipient_name == ""
        assert email.company_name == ""
    
    def test_empty_subject_validation(self):
        """Test validation fails for empty subject."""
        with pytest.raises(ValidationError, match="Email subject cannot be empty"):
            EmailContent(
                subject="",
                body="Test body content",
                template_used="basic"
            )
    
    def test_empty_body_validation(self):
        """Test validation fails for empty body."""
        with pytest.raises(ValidationError, match="Email body cannot be empty"):
            EmailContent(
                subject="Test Subject",
                body="",
                template_used="basic"
            )
    
    def test_empty_template_validation(self):
        """Test validation fails for empty template."""
        with pytest.raises(ValidationError, match="Template used cannot be empty"):
            EmailContent(
                subject="Test Subject",
                body="Test body content",
                template_used=""
            )
    
    def test_invalid_personalization_score_type(self):
        """Test validation fails for invalid personalization score type."""
        with pytest.raises(ValidationError, match="Personalization score must be a number"):
            EmailContent(
                subject="Test Subject",
                body="Test body content",
                template_used="basic",
                personalization_score="invalid"
            )
    
    def test_personalization_score_range_validation(self):
        """Test validation fails for personalization score out of range."""
        with pytest.raises(ValidationError, match="Personalization score must be between 0 and 1"):
            EmailContent(
                subject="Test Subject",
                body="Test body content",
                template_used="basic",
                personalization_score=1.5
            )
    
    def test_subject_length_validation(self):
        """Test validation fails for subject too long."""
        long_subject = "x" * 201
        with pytest.raises(ValidationError, match="Email subject too long"):
            EmailContent(
                subject=long_subject,
                body="Test body content",
                template_used="basic"
            )
    
    def test_body_length_validation(self):
        """Test validation fails for body too long."""
        long_body = "x" * 5001
        with pytest.raises(ValidationError, match="Email body too long"):
            EmailContent(
                subject="Test Subject",
                body=long_body,
                template_used="basic"
            )
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        email = EmailContent(
            subject="Job Opportunity at Your Company",
            body="Hello, I'm interested in opportunities at your company...",
            template_used="professional",
            personalization_score=0.8,
            recipient_name="John Doe",
            company_name="Test Company"
        )
        
        result = email.to_dict()
        expected = {
            'subject': "Job Opportunity at Your Company",
            'body': "Hello, I'm interested in opportunities at your company...",
            'template_used': "professional",
            'personalization_score': 0.8,
            'recipient_name': "John Doe",
            'company_name': "Test Company"
        }
        assert result == expected


class TestProspectStatus:
    """Test cases for ProspectStatus enum."""
    
    def test_prospect_status_values(self):
        """Test ProspectStatus enum values."""
        assert ProspectStatus.NOT_CONTACTED.value == "Not Contacted"
        assert ProspectStatus.CONTACTED.value == "Contacted"
        assert ProspectStatus.RESPONDED.value == "Responded"
        assert ProspectStatus.REJECTED.value == "Rejected"
    
    def test_prospect_status_enum_members(self):
        """Test ProspectStatus enum has all expected members."""
        expected_members = {"NOT_CONTACTED", "CONTACTED", "RESPONDED", "REJECTED"}
        actual_members = {member.name for member in ProspectStatus}
        assert actual_members == expected_members


class TestEmailData:
    """Test cases for EmailData model."""
    
    def test_valid_email_data(self):
        """Test creating valid EmailData."""
        email_data = EmailData(
            email='john@example.com',
            first_name='John',
            last_name='Doe',
            position='CEO',
            department='Executive',
            confidence=95,
            sources=['website', 'linkedin']
        )
        
        assert email_data.email == 'john@example.com'
        assert email_data.first_name == 'John'
        assert email_data.last_name == 'Doe'
        assert email_data.position == 'CEO'
        assert email_data.department == 'Executive'
        assert email_data.confidence == 95
        assert email_data.sources == ['website', 'linkedin']
    
    def test_email_data_with_minimal_data(self):
        """Test creating EmailData with minimal required data."""
        email_data = EmailData(email='john@example.com')
        
        assert email_data.email == 'john@example.com'
        assert email_data.first_name is None
        assert email_data.last_name is None
        assert email_data.position is None
        assert email_data.department is None
        assert email_data.confidence is None
        assert email_data.sources == []
    
    def test_empty_email_validation(self):
        """Test EmailData validation with empty email."""
        with pytest.raises(ValidationError):
            EmailData(email='')
        
        with pytest.raises(ValidationError):
            EmailData(email='   ')
    
    def test_invalid_email_format(self):
        """Test EmailData validation with invalid email format."""
        with pytest.raises(ValidationError):
            EmailData(email='invalid-email')
        
        with pytest.raises(ValidationError):
            EmailData(email='@example.com')
        
        with pytest.raises(ValidationError):
            EmailData(email='john@')
    
    def test_invalid_confidence_validation(self):
        """Test EmailData validation with invalid confidence."""
        with pytest.raises(ValidationError):
            EmailData(email='john@example.com', confidence=150)
        
        with pytest.raises(ValidationError):
            EmailData(email='john@example.com', confidence=-10)
        
        with pytest.raises(ValidationError):
            EmailData(email='john@example.com', confidence='high')
    
    def test_invalid_sources_validation(self):
        """Test EmailData validation with invalid sources."""
        with pytest.raises(ValidationError):
            EmailData(email='john@example.com', sources='website')
    
    def test_to_dict_serialization(self):
        """Test EmailData to_dict serialization."""
        email_data = EmailData(
            email='john@example.com',
            first_name='John',
            last_name='Doe',
            position='CEO',
            confidence=95,
            sources=['website']
        )
        
        result = email_data.to_dict()
        expected = {
            'email': 'john@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'position': 'CEO',
            'department': None,
            'confidence': 95,
            'sources': ['website']
        }
        
        assert result == expected


class TestEmailVerification:
    """Test cases for EmailVerification model."""
    
    def test_valid_email_verification(self):
        """Test creating valid EmailVerification."""
        verification = EmailVerification(
            email='john@example.com',
            result='deliverable',
            score=95,
            regexp=True,
            gibberish=False,
            disposable=False,
            webmail=False,
            mx_records=True,
            smtp_server=True,
            smtp_check=True,
            accept_all=False,
            block=False
        )
        
        assert verification.email == 'john@example.com'
        assert verification.result == 'deliverable'
        assert verification.score == 95
        assert verification.regexp is True
        assert verification.gibberish is False
    
    def test_email_verification_with_minimal_data(self):
        """Test creating EmailVerification with minimal required data."""
        verification = EmailVerification(
            email='john@example.com',
            result='unknown'
        )
        
        assert verification.email == 'john@example.com'
        assert verification.result == 'unknown'
        assert verification.score is None
        assert verification.regexp is None
    
    def test_empty_email_validation(self):
        """Test EmailVerification validation with empty email."""
        with pytest.raises(ValidationError):
            EmailVerification(email='', result='deliverable')
        
        with pytest.raises(ValidationError):
            EmailVerification(email='   ', result='deliverable')
    
    def test_invalid_email_format(self):
        """Test EmailVerification validation with invalid email format."""
        with pytest.raises(ValidationError):
            EmailVerification(email='invalid-email', result='deliverable')
    
    def test_invalid_result_validation(self):
        """Test EmailVerification validation with invalid result."""
        with pytest.raises(ValidationError):
            EmailVerification(email='john@example.com', result='invalid')
        
        with pytest.raises(ValidationError):
            EmailVerification(email='john@example.com', result='')
    
    def test_valid_result_values(self):
        """Test EmailVerification with all valid result values."""
        valid_results = ['deliverable', 'undeliverable', 'risky', 'unknown']
        
        for result in valid_results:
            verification = EmailVerification(email='john@example.com', result=result)
            assert verification.result == result
    
    def test_invalid_score_validation(self):
        """Test EmailVerification validation with invalid score."""
        with pytest.raises(ValidationError):
            EmailVerification(email='john@example.com', result='deliverable', score=150)
        
        with pytest.raises(ValidationError):
            EmailVerification(email='john@example.com', result='deliverable', score=-10)
        
        with pytest.raises(ValidationError):
            EmailVerification(email='john@example.com', result='deliverable', score='high')
    
    def test_to_dict_serialization(self):
        """Test EmailVerification to_dict serialization."""
        verification = EmailVerification(
            email='john@example.com',
            result='deliverable',
            score=95,
            regexp=True,
            gibberish=False
        )
        
        result = verification.to_dict()
        expected = {
            'email': 'john@example.com',
            'result': 'deliverable',
            'score': 95,
            'regexp': True,
            'gibberish': False,
            'disposable': None,
            'webmail': None,
            'mx_records': None,
            'smtp_server': None,
            'smtp_check': None,
            'accept_all': None,
            'block': None
        }
        
        assert result == expected