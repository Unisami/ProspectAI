"""
Integration tests for enhanced validation in services.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from services.ai_service import AIService
from services.ai_parser import AIParser
from services.sender_profile_manager import SenderProfileManager
from services.notion_manager import OptimizedNotionDataManager
from models.data_models import (
    TeamMember, Prospect, SenderProfile, ValidationError, ProspectStatus
)
from utils.validation_framework import ValidationResult, ValidationSeverity
from utils.configuration_service import get_configuration_service


class TestAIServiceValidation:
    """Test enhanced validation in AIService."""
    
    @pytest.fixture
    def ai_service(self):
        """Create AIService instance for testing."""
        config_service = get_configuration_service()
        return AIService(config_service.get_config())
    
    def test_validate_team_member_data_valid(self, ai_service):
        """Test validation of valid team member data."""
        member_data = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'linkedin_url': 'https://linkedin.com/in/johndoe'
        }
        
        result = ai_service._validate_team_member_data(member_data, 'Test Company')
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_validate_team_member_data_invalid_name(self, ai_service):
        """Test validation with invalid name."""
        member_data = {
            'name': 'A',  # Too short
            'role': 'Software Engineer'
        }
        
        result = ai_service._validate_team_member_data(member_data, 'Test Company')
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert 'too short' in result.message.lower()
    
    def test_validate_team_member_data_invalid_linkedin(self, ai_service):
        """Test validation with invalid LinkedIn URL."""
        member_data = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'linkedin_url': 'not-a-valid-url'
        }
        
        result = ai_service._validate_team_member_data(member_data, 'Test Company')
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert 'url' in result.message.lower()
    
    def test_validate_team_member_data_empty_company(self, ai_service):
        """Test validation with empty company name."""
        member_data = {
            'name': 'John Doe',
            'role': 'Software Engineer'
        }
        
        result = ai_service._validate_team_member_data(member_data, '')
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert 'company' in result.message.lower()


class TestAIParserValidation:
    """Test enhanced validation in AIParser."""
    
    @pytest.fixture
    def ai_parser(self):
        """Create AIParser instance for testing."""
        config_service = get_configuration_service()
        return AIParser(config_service.get_config())
    
    def test_validate_team_member_data_valid(self, ai_parser):
        """Test validation of valid team member data."""
        member_data = {
            'name': 'Jane Smith',
            'role': 'Product Manager',
            'linkedin_url': 'https://linkedin.com/in/janesmith'
        }
        
        result = ai_parser._validate_team_member_data(member_data, 'Test Company')
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_validate_team_member_data_missing_role(self, ai_parser):
        """Test validation with missing role."""
        member_data = {
            'name': 'Jane Smith',
            'role': ''  # Empty role
        }
        
        result = ai_parser._validate_team_member_data(member_data, 'Test Company')
        assert not result.is_valid
        assert result.severity == ValidationSeverity.ERROR
        assert 'role' in result.message.lower()
    
    def test_validate_team_member_data_optional_linkedin(self, ai_parser):
        """Test validation without LinkedIn URL (should be valid)."""
        member_data = {
            'name': 'Jane Smith',
            'role': 'Product Manager'
        }
        
        result = ai_parser._validate_team_member_data(member_data, 'Test Company')
        assert result.is_valid


class TestSenderProfileManagerValidation:
    """Test enhanced validation in SenderProfileManager."""
    
    @pytest.fixture
    def profile_manager(self):
        """Create SenderProfileManager instance for testing."""
        return SenderProfileManager()
    
    def test_validate_complete_profile(self, profile_manager):
        """Test validation of complete profile."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React", "Node.js"],
            experience_summary="Experienced full-stack developer with 5 years in web development, specializing in scalable applications.",
            education=["BS Computer Science - MIT"],
            certifications=["AWS Certified Developer"],
            value_proposition="I build scalable web applications that drive business growth and improve user experience.",
            target_roles=["Software Engineer", "Full Stack Developer", "Senior Developer"],
            industries_of_interest=["Technology", "Fintech"],
            notable_achievements=["Led team of 5 developers", "Built system serving 1M+ users"],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
            location="San Francisco, CA",
            remote_preference="hybrid"
        )
        
        is_valid, issues = profile_manager.validate_profile(profile)
        # Should be valid or have only minor completeness warnings
        if not is_valid:
            # Allow for minor completeness warnings
            assert all("completeness" in issue.lower() for issue in issues)
        else:
            assert len(issues) == 0
    
    def test_validate_incomplete_profile(self, profile_manager):
        """Test validation of incomplete profile."""
        profile = SenderProfile(
            name="Jane Smith",
            current_role="Developer",
            years_experience=2,
            key_skills=[],  # Missing skills
            target_roles=[]  # Missing target roles
        )
        
        is_valid, issues = profile_manager.validate_profile(profile)
        assert not is_valid
        assert len(issues) > 0
        # Check for completeness-related issues
        issues_text = ' '.join(issues).lower()
        assert "skill" in issues_text
        assert "target" in issues_text
    
    def test_validate_profile_invalid_portfolio_link(self, profile_manager):
        """Test validation with invalid portfolio link."""
        # The validation happens at creation time, so we expect ValidationError
        with pytest.raises(ValidationError) as exc_info:
            profile = SenderProfile(
                name="John Doe",
                current_role="Software Engineer",
                years_experience=3,
                key_skills=["Python"],
                experience_summary="Experienced developer.",
                value_proposition="I deliver quality software.",
                target_roles=["Engineer"],
                portfolio_links=["not-a-valid-url"]
            )
        
        assert "url" in str(exc_info.value).lower()
    
    def test_validate_profile_low_completeness(self, profile_manager):
        """Test validation with low completeness score."""
        profile = SenderProfile(
            name="John Doe",
            current_role="Engineer",
            years_experience=1,
            key_skills=["Python"],
            target_roles=["Engineer"]
            # Missing many optional fields
        )
        
        is_valid, issues = profile_manager.validate_profile(profile)
        # Should be valid but with completeness warning
        completeness_issues = [issue for issue in issues if "completeness" in issue.lower()]
        assert len(completeness_issues) > 0


class TestNotionManagerValidation:
    """Test enhanced validation in NotionManager."""
    
    @pytest.fixture
    def notion_manager(self):
        """Create OptimizedNotionDataManager instance for testing."""
        config_service = get_configuration_service()
        return OptimizedNotionDataManager(config_service.get_config())
    
    def test_validate_prospect_data_valid(self, notion_manager):
        """Test validation of valid prospect data."""
        prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="john@example.com",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        result = notion_manager._validate_prospect_data(prospect)
        assert result.is_valid
        assert result.severity == ValidationSeverity.INFO
    
    def test_validate_prospect_data_invalid_email(self, notion_manager):
        """Test validation with invalid email."""
        # The validation happens at creation time, so we expect ValidationError
        with pytest.raises(ValidationError) as exc_info:
            prospect = Prospect(
                name="John Doe",
                role="Software Engineer",
                company="Test Company",
                email="invalid-email"  # Invalid format
            )
        
        assert "email" in str(exc_info.value).lower()
    
    def test_validate_prospect_batch_mixed_validity(self, notion_manager):
        """Test batch validation with mixed valid/invalid prospects."""
        valid_prospect = Prospect(
            name="John Doe",
            role="Software Engineer",
            company="Test Company",
            email="john@example.com"
        )
        
        # Create invalid prospect by bypassing validation
        invalid_prospect = Prospect.__new__(Prospect)
        invalid_prospect.name = ""  # Invalid
        invalid_prospect.role = "Engineer"
        invalid_prospect.company = "Test"
        invalid_prospect.id = ""
        invalid_prospect.linkedin_url = None
        invalid_prospect.email = None
        invalid_prospect.contacted = False
        invalid_prospect.status = ProspectStatus.NOT_CONTACTED
        invalid_prospect.notes = ""
        invalid_prospect.source_url = ""
        invalid_prospect.created_at = datetime.now()
        
        prospects = [valid_prospect, invalid_prospect]
        results = notion_manager._validate_prospect_batch(prospects)
        
        assert len(results) == 2
        assert results[0].is_valid  # First prospect should be valid
        assert not results[1].is_valid  # Second prospect should be invalid


class TestValidationIntegration:
    """Test integration between services and validation framework."""
    
    def test_validation_error_consistency(self):
        """Test that validation errors are consistent across services."""
        # Test data that should fail validation consistently
        invalid_member_data = {
            'name': 'A',  # Too short
            'role': 'Engineer'
        }
        
        # Test with AIService
        config_service = get_configuration_service()
        ai_service = AIService(config_service.get_config())
        ai_result = ai_service._validate_team_member_data(invalid_member_data, 'Company')
        
        # Test with AIParser
        ai_parser = AIParser(config_service.get_config())
        parser_result = ai_parser._validate_team_member_data(invalid_member_data, 'Company')
        
        # Both should fail validation with similar messages
        assert not ai_result.is_valid
        assert not parser_result.is_valid
        assert 'name' in ai_result.message.lower()
        assert 'name' in parser_result.message.lower()
    
    def test_validation_framework_error_codes(self):
        """Test that validation framework provides consistent error codes."""
        config_service = get_configuration_service()
        ai_service = AIService(config_service.get_config())
        
        # Test with empty name
        result = ai_service._validate_team_member_data({'name': '', 'role': 'Engineer'}, 'Company')
        assert not result.is_valid
        assert result.error_code is not None
        assert 'VALIDATION' in result.error_code or 'ERROR' in result.error_code
    
    def test_validation_performance(self):
        """Test that validation doesn't significantly impact performance."""
        import time
        
        config_service = get_configuration_service()
        ai_service = AIService(config_service.get_config())
        
        # Test validation performance with multiple data points
        member_data = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'linkedin_url': 'https://linkedin.com/in/johndoe'
        }
        
        start_time = time.time()
        for _ in range(100):
            ai_service._validate_team_member_data(member_data, 'Test Company')
        end_time = time.time()
        
        # Validation should be fast (less than 1 second for 100 validations)
        assert (end_time - start_time) < 1.0
    
    @patch('utils.validation_framework.ValidationFramework.validate_email')
    def test_validation_framework_integration(self, mock_validate_email):
        """Test that services properly integrate with ValidationFramework."""
        # Mock the validation framework to return invalid result
        mock_validate_email.return_value = ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            message="Mocked validation error",
            error_code="MOCK_ERROR"
        )
        
        # Test that the mock is used - validation should fail during prospect creation
        with pytest.raises(ValidationError) as exc_info:
            prospect = Prospect(
                name="John Doe",
                role="Engineer",
                company="Test Company",
                email="test@example.com"
            )
        
        # Verify the mocked validation was used
        assert "mocked validation error" in str(exc_info.value).lower()
        mock_validate_email.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])