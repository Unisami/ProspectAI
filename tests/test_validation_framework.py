"""
Comprehensive unit tests for the validation framework.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from utils.validation_framework import (
    ValidationFramework, ValidationResult, ValidationSeverity
)


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test creating ValidationResult instances."""
        result = ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Test message"
        )
        
        assert result.is_valid is True
        assert result.severity == ValidationSeverity.INFO
        assert result.message == "Test message"
        assert result.field_name is None
        assert result.suggested_fix is None
        assert result.error_code is None
    
    def test_validation_result_auto_severity(self):
        """Test automatic severity setting for invalid results."""
        result = ValidationResult(
            is_valid=False,
            severity=ValidationSeverity.INFO,  # Should be changed to ERROR
            message="Test error"
        )
        
        assert result.severity == ValidationSeverity.ERROR


class TestEmailValidation:
    """Test email validation methods."""
    
    def test_valid_emails(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org",
            "123@numbers.com",
            "test_user@example-domain.com"
        ]
        
        for email in valid_emails:
            result = ValidationFramework.validate_email(email)
            assert result.is_valid, f"Email {email} should be valid"
            assert result.severity == ValidationSeverity.INFO
    
    def test_invalid_emails(self):
        """Test validation of invalid email addresses."""
        invalid_emails = [
            "",
            "invalid",
            "@domain.com",
            "user@",
            "user@domain",
            "user.domain.com",
            "user@domain.",
            "user@.domain.com",
            "user name@domain.com"
        ]
        
        for email in invalid_emails:
            result = ValidationFramework.validate_email(email)
            assert not result.is_valid, f"Email {email} should be invalid"
            assert result.severity == ValidationSeverity.ERROR
    
    def test_empty_email(self):
        """Test validation of empty email."""
        result = ValidationFramework.validate_email("")
        assert not result.is_valid
        assert result.error_code == "EMAIL_EMPTY"
        assert "empty" in result.message.lower()
    
    def test_none_email(self):
        """Test validation of None email."""
        result = ValidationFramework.validate_email(None)
        assert not result.is_valid
        assert result.error_code == "EMAIL_EMPTY"
    
    def test_disposable_email_detection(self):
        """Test detection of disposable email domains."""
        disposable_emails = [
            "test@10minutemail.com",
            "user@guerrillamail.com",
            "temp@mailinator.com"
        ]
        
        for email in disposable_emails:
            result = ValidationFramework.validate_email(email)
            assert not result.is_valid
            assert result.severity == ValidationSeverity.WARNING
            assert result.error_code == "EMAIL_DISPOSABLE"
    
    def test_mx_record_check_dns_unavailable(self):
        """Test MX record validation when DNS is unavailable."""
        # Since DNS is not available in this environment, test the fallback behavior
        result = ValidationFramework.validate_email("test@example.com", check_mx=True)
        # Should be valid with warning about DNS unavailability
        assert result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert result.error_code == "EMAIL_DNS_UNAVAILABLE"


class TestURLValidation:
    """Test URL validation methods."""
    
    def test_valid_urls(self):
        """Test validation of valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://subdomain.example.com",
            "https://example.com/path",
            "https://example.com/path?query=value",
            "https://example.com:8080/path"
        ]
        
        for url in valid_urls:
            result = ValidationFramework.validate_url(url)
            assert result.is_valid, f"URL {url} should be valid"
            assert result.severity == ValidationSeverity.INFO
    
    def test_invalid_urls(self):
        """Test validation of invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",  # Invalid scheme
            "https://",  # No domain
            "example.com"  # No scheme
        ]
        
        for url in invalid_urls:
            result = ValidationFramework.validate_url(url)
            assert not result.is_valid, f"URL {url} should be invalid"
    
    def test_custom_allowed_schemes(self):
        """Test URL validation with custom allowed schemes."""
        result = ValidationFramework.validate_url("ftp://example.com", allowed_schemes=['ftp'])
        assert result.is_valid
        
        result = ValidationFramework.validate_url("https://example.com", allowed_schemes=['ftp'])
        assert not result.is_valid
        assert result.error_code == "URL_INVALID_SCHEME"
    
    def test_url_without_scheme(self):
        """Test URL validation without scheme."""
        result = ValidationFramework.validate_url("example.com")
        assert not result.is_valid
        assert result.error_code == "URL_NO_SCHEME"
        assert "http://" in result.suggested_fix


class TestLinkedInURLValidation:
    """Test LinkedIn URL validation methods."""
    
    def test_valid_linkedin_urls(self):
        """Test validation of valid LinkedIn URLs."""
        valid_urls = [
            "https://linkedin.com/in/username",
            "https://www.linkedin.com/in/user-name",
            "http://linkedin.com/in/username123",
            "https://linkedin.com/pub/user/123/456/789"
        ]
        
        for url in valid_urls:
            result = ValidationFramework.validate_linkedin_url(url)
            assert result.is_valid, f"LinkedIn URL {url} should be valid"
    
    def test_invalid_linkedin_urls(self):
        """Test validation of invalid LinkedIn URLs."""
        invalid_urls = [
            "",
            "https://facebook.com/user",
            "https://example.com",
            "not-a-url",
            "https://linkedin.com/invalid-path"
        ]
        
        for url in invalid_urls:
            result = ValidationFramework.validate_linkedin_url(url)
            assert not result.is_valid, f"LinkedIn URL {url} should be invalid"
    
    def test_non_linkedin_domain(self):
        """Test LinkedIn URL validation with non-LinkedIn domain."""
        result = ValidationFramework.validate_linkedin_url("https://facebook.com/user")
        assert not result.is_valid
        assert result.error_code == "LINKEDIN_URL_NOT_LINKEDIN"
    
    def test_non_standard_linkedin_format(self):
        """Test LinkedIn URL with non-standard format."""
        result = ValidationFramework.validate_linkedin_url("https://linkedin.com/company/example")
        assert not result.is_valid
        assert result.severity == ValidationSeverity.WARNING
        assert result.error_code == "LINKEDIN_URL_NON_STANDARD"


class TestDomainValidation:
    """Test domain validation methods."""
    
    def test_valid_domains(self):
        """Test validation of valid domains."""
        valid_domains = [
            "example.com",
            "subdomain.example.com",
            "example-site.co.uk",
            "123domain.org",
            "a.b.c.d.com"
        ]
        
        for domain in valid_domains:
            result = ValidationFramework.validate_domain(domain)
            assert result.is_valid, f"Domain {domain} should be valid"
    
    def test_invalid_domains(self):
        """Test validation of invalid domains."""
        invalid_domains = [
            "",
            "domain",  # No TLD
            ".com",  # No domain
            "domain.",  # Trailing dot
            "-domain.com",  # Leading hyphen
            "domain-.com",  # Trailing hyphen
            "domain..com",  # Double dot
            "a" * 254 + ".com"  # Too long
        ]
        
        for domain in invalid_domains:
            result = ValidationFramework.validate_domain(domain)
            assert not result.is_valid, f"Domain {domain} should be invalid"
    
    def test_domain_with_protocol(self):
        """Test domain validation with protocol prefix."""
        result = ValidationFramework.validate_domain("https://example.com")
        assert result.is_valid  # Should strip protocol
    
    def test_domain_too_long(self):
        """Test domain validation with excessive length."""
        long_domain = "a" * 250 + ".com"
        result = ValidationFramework.validate_domain(long_domain)
        assert not result.is_valid
        assert result.error_code == "DOMAIN_TOO_LONG"


class TestStringFieldValidation:
    """Test string field validation methods."""
    
    def test_valid_string(self):
        """Test validation of valid string."""
        result = ValidationFramework.validate_string_field("test string", "test_field")
        assert result.is_valid
    
    def test_empty_string_not_allowed(self):
        """Test validation of empty string when not allowed."""
        result = ValidationFramework.validate_string_field("", "test_field")
        assert not result.is_valid
        assert result.error_code == "STRING_EMPTY"
    
    def test_empty_string_allowed(self):
        """Test validation of empty string when allowed."""
        result = ValidationFramework.validate_string_field("", "test_field", allow_empty=True)
        assert result.is_valid
    
    def test_none_value(self):
        """Test validation of None value."""
        result = ValidationFramework.validate_string_field(None, "test_field")
        assert not result.is_valid
        assert result.error_code == "STRING_NONE"
    
    def test_wrong_type(self):
        """Test validation of non-string value."""
        result = ValidationFramework.validate_string_field(123, "test_field")
        assert not result.is_valid
        assert result.error_code == "STRING_WRONG_TYPE"
    
    def test_length_constraints(self):
        """Test string length constraints."""
        # Too short
        result = ValidationFramework.validate_string_field("ab", "test_field", min_length=5)
        assert not result.is_valid
        assert result.error_code == "STRING_TOO_SHORT"
        
        # Too long
        result = ValidationFramework.validate_string_field("abcdef", "test_field", max_length=3)
        assert not result.is_valid
        assert result.error_code == "STRING_TOO_LONG"
        
        # Just right
        result = ValidationFramework.validate_string_field("abc", "test_field", min_length=2, max_length=5)
        assert result.is_valid


class TestIntegerFieldValidation:
    """Test integer field validation methods."""
    
    def test_valid_integer(self):
        """Test validation of valid integer."""
        result = ValidationFramework.validate_integer_field(42, "test_field")
        assert result.is_valid
    
    def test_none_value(self):
        """Test validation of None value."""
        result = ValidationFramework.validate_integer_field(None, "test_field")
        assert not result.is_valid
        assert result.error_code == "INTEGER_NONE"
    
    def test_wrong_type(self):
        """Test validation of non-integer value."""
        result = ValidationFramework.validate_integer_field("123", "test_field")
        assert not result.is_valid
        assert result.error_code == "INTEGER_WRONG_TYPE"
    
    def test_range_constraints(self):
        """Test integer range constraints."""
        # Too small
        result = ValidationFramework.validate_integer_field(5, "test_field", min_value=10)
        assert not result.is_valid
        assert result.error_code == "INTEGER_TOO_SMALL"
        
        # Too large
        result = ValidationFramework.validate_integer_field(15, "test_field", max_value=10)
        assert not result.is_valid
        assert result.error_code == "INTEGER_TOO_LARGE"
        
        # Just right
        result = ValidationFramework.validate_integer_field(7, "test_field", min_value=5, max_value=10)
        assert result.is_valid


class TestFloatFieldValidation:
    """Test float field validation methods."""
    
    def test_valid_float(self):
        """Test validation of valid float."""
        result = ValidationFramework.validate_float_field(3.14, "test_field")
        assert result.is_valid
    
    def test_valid_integer_as_float(self):
        """Test validation of integer as float."""
        result = ValidationFramework.validate_float_field(42, "test_field")
        assert result.is_valid
    
    def test_none_value(self):
        """Test validation of None value."""
        result = ValidationFramework.validate_float_field(None, "test_field")
        assert not result.is_valid
        assert result.error_code == "FLOAT_NONE"
    
    def test_wrong_type(self):
        """Test validation of non-numeric value."""
        result = ValidationFramework.validate_float_field("3.14", "test_field")
        assert not result.is_valid
        assert result.error_code == "FLOAT_WRONG_TYPE"
    
    def test_range_constraints(self):
        """Test float range constraints."""
        # Too small
        result = ValidationFramework.validate_float_field(1.5, "test_field", min_value=2.0)
        assert not result.is_valid
        assert result.error_code == "FLOAT_TOO_SMALL"
        
        # Too large
        result = ValidationFramework.validate_float_field(5.5, "test_field", max_value=5.0)
        assert not result.is_valid
        assert result.error_code == "FLOAT_TOO_LARGE"
        
        # Just right
        result = ValidationFramework.validate_float_field(3.5, "test_field", min_value=2.0, max_value=5.0)
        assert result.is_valid


class TestDateTimeFieldValidation:
    """Test datetime field validation methods."""
    
    def test_valid_datetime(self):
        """Test validation of valid datetime."""
        dt = datetime.now()
        result = ValidationFramework.validate_datetime_field(dt, "test_field")
        assert result.is_valid
    
    def test_none_value(self):
        """Test validation of None value."""
        result = ValidationFramework.validate_datetime_field(None, "test_field")
        assert not result.is_valid
        assert result.error_code == "DATETIME_NONE"
    
    def test_wrong_type(self):
        """Test validation of non-datetime value."""
        result = ValidationFramework.validate_datetime_field("2023-01-01", "test_field")
        assert not result.is_valid
        assert result.error_code == "DATETIME_WRONG_TYPE"


class TestListFieldValidation:
    """Test list field validation methods."""
    
    def test_valid_list(self):
        """Test validation of valid list."""
        result = ValidationFramework.validate_list_field([1, 2, 3], "test_field")
        assert result.is_valid
    
    def test_none_value(self):
        """Test validation of None value."""
        result = ValidationFramework.validate_list_field(None, "test_field")
        assert not result.is_valid
        assert result.error_code == "LIST_NONE"
    
    def test_wrong_type(self):
        """Test validation of non-list value."""
        result = ValidationFramework.validate_list_field("not a list", "test_field")
        assert not result.is_valid
        assert result.error_code == "LIST_WRONG_TYPE"
    
    def test_item_count_constraints(self):
        """Test list item count constraints."""
        # Too few items
        result = ValidationFramework.validate_list_field([1], "test_field", min_items=3)
        assert not result.is_valid
        assert result.error_code == "LIST_TOO_FEW_ITEMS"
        
        # Too many items
        result = ValidationFramework.validate_list_field([1, 2, 3, 4], "test_field", max_items=2)
        assert not result.is_valid
        assert result.error_code == "LIST_TOO_MANY_ITEMS"
        
        # Just right
        result = ValidationFramework.validate_list_field([1, 2], "test_field", min_items=1, max_items=3)
        assert result.is_valid
    
    def test_item_validation(self):
        """Test list with item validation."""
        def validate_positive_int(value):
            if not isinstance(value, int) or value <= 0:
                return ValidationResult(False, ValidationSeverity.ERROR, "Must be positive integer")
            return ValidationResult(True, ValidationSeverity.INFO, "Valid")
        
        # Valid items
        result = ValidationFramework.validate_list_field([1, 2, 3], "test_field", item_validator=validate_positive_int)
        assert result.is_valid
        
        # Invalid item
        result = ValidationFramework.validate_list_field([1, -2, 3], "test_field", item_validator=validate_positive_int)
        assert not result.is_valid
        assert result.error_code == "LIST_INVALID_ITEM"


class TestLinkedInProfileValidation:
    """Test LinkedIn profile validation methods."""
    
    def test_valid_profile(self):
        """Test validation of valid LinkedIn profile."""
        profile_data = {
            'name': 'John Doe',
            'current_role': 'Software Engineer',
            'experience': ['Company A', 'Company B'],
            'skills': ['Python', 'JavaScript'],
            'summary': 'Experienced software engineer with expertise in web development.'
        }
        
        results = ValidationFramework.validate_linkedin_profile(profile_data)
        assert all(r.is_valid for r in results)
    
    def test_invalid_profile(self):
        """Test validation of invalid LinkedIn profile."""
        profile_data = {
            'name': '',  # Invalid: empty
            'current_role': 'A',  # Invalid: too short
            'experience': 'not a list',  # Invalid: wrong type
            'skills': ['skill'] * 60,  # Invalid: too many items
            'summary': 'Short'  # Invalid: too short
        }
        
        results = ValidationFramework.validate_linkedin_profile(profile_data)
        invalid_results = [r for r in results if not r.is_valid]
        assert len(invalid_results) > 0


class TestCompanyDataValidation:
    """Test company data validation methods."""
    
    def test_valid_company_data(self):
        """Test validation of valid company data."""
        company_data = {
            'name': 'Example Company',
            'domain': 'example.com',
            'product_url': 'https://example.com/product',
            'description': 'A great company that builds amazing products.',
            'launch_date': datetime.now()
        }
        
        results = ValidationFramework.validate_company_data(company_data)
        assert all(r.is_valid for r in results)
    
    def test_invalid_company_data(self):
        """Test validation of invalid company data."""
        company_data = {
            'name': '',  # Invalid: empty
            'domain': None,  # Invalid: None
            'product_url': None,  # Invalid: None
            'description': 'Short',  # Invalid: too short
            'launch_date': None  # Invalid: None
        }
        
        results = ValidationFramework.validate_company_data(company_data)
        invalid_results = [r for r in results if not r.is_valid]
        assert len(invalid_results) > 0


class TestMultipleResultsValidation:
    """Test multiple validation results combination."""
    
    def test_all_valid_results(self):
        """Test combining all valid results."""
        results = [
            ValidationResult(True, ValidationSeverity.INFO, "Valid 1"),
            ValidationResult(True, ValidationSeverity.INFO, "Valid 2")
        ]
        
        combined = ValidationFramework.validate_multiple_results(results)
        assert combined.is_valid
        assert combined.severity == ValidationSeverity.INFO
    
    def test_results_with_errors(self):
        """Test combining results with errors."""
        results = [
            ValidationResult(True, ValidationSeverity.INFO, "Valid"),
            ValidationResult(False, ValidationSeverity.ERROR, "Error 1"),
            ValidationResult(False, ValidationSeverity.ERROR, "Error 2")
        ]
        
        combined = ValidationFramework.validate_multiple_results(results)
        assert not combined.is_valid
        assert combined.severity == ValidationSeverity.ERROR
        assert "Error 1" in combined.message
        assert "Error 2" in combined.message
    
    def test_results_with_warnings(self):
        """Test combining results with warnings only."""
        results = [
            ValidationResult(True, ValidationSeverity.INFO, "Valid"),
            ValidationResult(False, ValidationSeverity.WARNING, "Warning 1"),
            ValidationResult(False, ValidationSeverity.WARNING, "Warning 2")
        ]
        
        combined = ValidationFramework.validate_multiple_results(results)
        assert combined.is_valid  # Warnings don't make overall result invalid
        assert combined.severity == ValidationSeverity.WARNING
        assert "Warning 1" in combined.message
        assert "Warning 2" in combined.message
    
    def test_empty_results(self):
        """Test combining empty results list."""
        combined = ValidationFramework.validate_multiple_results([])
        assert combined.is_valid
        assert combined.severity == ValidationSeverity.INFO
        assert "No validation performed" in combined.message


if __name__ == "__main__":
    pytest.main([__file__])