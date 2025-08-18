"""
Comprehensive validation framework for the job prospect automation system.

This module provides a centralized validation framework with standardized validators
for emails, URLs, LinkedIn profiles, and other data types used throughout the system.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Callable
)
from urllib.parse import urlparse
from enum import Enum

# Optional DNS checking - install dnspython for MX record validation
try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False


class ValidationSeverity(Enum):
    """Severity levels for validation results."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Standardized validation result with detailed information."""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    suggested_fix: Optional[str] = None
    error_code: Optional[str] = None
    
    def __post_init__(self):
        """Set severity based on validity if not explicitly provided."""
        if not self.is_valid and self.severity == ValidationSeverity.INFO:
            self.severity = ValidationSeverity.ERROR


class ValidationFramework:
    """Centralized validation framework with comprehensive validators."""
    
    # Email validation patterns - more strict to avoid false positives
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    )
    
    # LinkedIn URL patterns
    LINKEDIN_PATTERNS = [
        re.compile(r'^https?://(?:www\.)?linkedin\.com/in/[a-zA-Z0-9-]+/?$'),
        re.compile(r'^https?://(?:www\.)?linkedin\.com/pub/[a-zA-Z0-9-]+/[a-zA-Z0-9]+/[a-zA-Z0-9]+/[a-zA-Z0-9]+/?$'),
        re.compile(r'^https?://(?:www\.)?linkedin\.com/profile/view\?id=\d+$')
    ]
    
    # Domain validation pattern
    DOMAIN_PATTERN = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    )
    
    # Common disposable email domains
    DISPOSABLE_DOMAINS = {
        '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
        'tempmail.org', 'yopmail.com', 'throwaway.email'
    }
    
    @classmethod
    def validate_email(cls, email: str, check_mx: bool = False) -> ValidationResult:
        """
        Validate email format and optionally check MX records.
        
        Args:
            email: Email address to validate
            check_mx: Whether to check MX records for domain
            
        Returns:
            ValidationResult with validation details
        """
        if not email or not isinstance(email, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Email cannot be empty or None",
                field_name="email",
                error_code="EMAIL_EMPTY"
            )
        
        email = email.strip().lower()
        
        # Basic format validation
        if not cls.EMAIL_PATTERN.match(email):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid email format: {email}",
                field_name="email",
                suggested_fix="Ensure email follows format: user@domain.com",
                error_code="EMAIL_INVALID_FORMAT"
            )
        
        # Check for disposable email domains
        domain = email.split('@')[1]
        if domain in cls.DISPOSABLE_DOMAINS:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message=f"Disposable email domain detected: {domain}",
                field_name="email",
                suggested_fix="Use a permanent email address",
                error_code="EMAIL_DISPOSABLE"
            )
        
        # Optional MX record check
        if check_mx:
            if not DNS_AVAILABLE:
                return ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    message="DNS checking not available (install dnspython for MX validation)",
                    field_name="email",
                    suggested_fix="Install dnspython: pip install dnspython",
                    error_code="EMAIL_DNS_UNAVAILABLE"
                )
            
            try:
                dns.resolver.resolve(domain, 'MX')
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, Exception):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.WARNING,
                    message=f"No MX records found for domain: {domain}",
                    field_name="email",
                    suggested_fix="Verify the email domain is correct",
                    error_code="EMAIL_NO_MX"
                )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Email format is valid",
            field_name="email"
        )
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate URL format and scheme.
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (default: ['http', 'https'])
            
        Returns:
            ValidationResult with validation details
        """
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="URL cannot be empty or None",
                field_name="url",
                error_code="URL_EMPTY"
            )
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        url = url.strip()
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Failed to parse URL: {str(e)}",
                field_name="url",
                error_code="URL_PARSE_ERROR"
            )
        
        # Check scheme
        if not parsed.scheme:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="URL missing scheme (http/https)",
                field_name="url",
                suggested_fix="Add http:// or https:// to the beginning",
                error_code="URL_NO_SCHEME"
            )
        
        if parsed.scheme.lower() not in allowed_schemes:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid URL scheme: {parsed.scheme}. Allowed: {allowed_schemes}",
                field_name="url",
                suggested_fix=f"Use one of: {', '.join(allowed_schemes)}",
                error_code="URL_INVALID_SCHEME"
            )
        
        # Check netloc (domain)
        if not parsed.netloc:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="URL missing domain",
                field_name="url",
                suggested_fix="Ensure URL includes a valid domain",
                error_code="URL_NO_DOMAIN"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="URL format is valid",
            field_name="url"
        )
    
    @classmethod
    def validate_linkedin_url(cls, url: str) -> ValidationResult:
        """
        Validate LinkedIn profile URL format.
        
        Args:
            url: LinkedIn URL to validate
            
        Returns:
            ValidationResult with validation details
        """
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="LinkedIn URL cannot be empty or None",
                field_name="linkedin_url",
                error_code="LINKEDIN_URL_EMPTY"
            )
        
        url = url.strip()
        
        # First validate as general URL
        url_result = cls.validate_url(url)
        if not url_result.is_valid:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid URL format: {url_result.message}",
                field_name="linkedin_url",
                error_code="LINKEDIN_URL_INVALID"
            )
        
        # Check if it's a LinkedIn URL
        parsed = urlparse(url)
        if 'linkedin.com' not in parsed.netloc.lower():
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="URL is not a LinkedIn profile",
                field_name="linkedin_url",
                suggested_fix="Use a valid LinkedIn profile URL",
                error_code="LINKEDIN_URL_NOT_LINKEDIN"
            )
        
        # Check against known LinkedIn patterns
        is_valid_pattern = any(pattern.match(url) for pattern in cls.LINKEDIN_PATTERNS)
        
        if not is_valid_pattern:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.WARNING,
                message="LinkedIn URL format may not be standard",
                field_name="linkedin_url",
                suggested_fix="Use format: https://linkedin.com/in/username",
                error_code="LINKEDIN_URL_NON_STANDARD"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="LinkedIn URL format is valid",
            field_name="linkedin_url"
        )
    
    @classmethod
    def validate_domain(cls, domain: str) -> ValidationResult:
        """
        Validate domain name format.
        
        Args:
            domain: Domain name to validate
            
        Returns:
            ValidationResult with validation details
        """
        if not domain or not isinstance(domain, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Domain cannot be empty or None",
                field_name="domain",
                error_code="DOMAIN_EMPTY"
            )
        
        domain = domain.strip().lower()
        
        # Remove protocol if present
        if domain.startswith(('http://', 'https://')):
            parsed = urlparse(domain)
            domain = parsed.netloc
        
        # Check length constraints first
        if len(domain) > 253:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Domain name too long (max 253 characters)",
                field_name="domain",
                error_code="DOMAIN_TOO_LONG"
            )
        
        # Basic format validation
        if not cls.DOMAIN_PATTERN.match(domain):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Invalid domain format: {domain}",
                field_name="domain",
                suggested_fix="Use format: example.com",
                error_code="DOMAIN_INVALID_FORMAT"
            )
        
        # Check for valid TLD
        parts = domain.split('.')
        if len(parts) < 2:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Domain must have at least one dot",
                field_name="domain",
                suggested_fix="Use format: example.com",
                error_code="DOMAIN_NO_TLD"
            )
        
        tld = parts[-1]
        if len(tld) < 2:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Top-level domain too short",
                field_name="domain",
                error_code="DOMAIN_INVALID_TLD"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="Domain format is valid",
            field_name="domain"
        )
    
    @classmethod
    def validate_string_field(cls, value: Any, field_name: str, 
                            min_length: int = 1, max_length: Optional[int] = None,
                            allow_empty: bool = False) -> ValidationResult:
        """
        Validate string field with length constraints.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            min_length: Minimum required length
            max_length: Maximum allowed length
            allow_empty: Whether to allow empty strings
            
        Returns:
            ValidationResult with validation details
        """
        if value is None:
            if allow_empty:
                return ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.INFO,
                    message=f"{field_name} is empty (allowed)",
                    field_name=field_name
                )
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be None",
                field_name=field_name,
                error_code="STRING_NONE"
            )
        
        if not isinstance(value, str):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} must be a string, got {type(value).__name__}",
                field_name=field_name,
                error_code="STRING_WRONG_TYPE"
            )
        
        value = value.strip()
        
        if not value and not allow_empty:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be empty",
                field_name=field_name,
                error_code="STRING_EMPTY"
            )
        
        # If empty string is allowed, skip length validation
        if not value and allow_empty:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message=f"{field_name} is empty (allowed)",
                field_name=field_name
            )
        
        if len(value) < min_length:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too short (min {min_length} characters)",
                field_name=field_name,
                error_code="STRING_TOO_SHORT"
            )
        
        if max_length and len(value) > max_length:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too long (max {max_length} characters)",
                field_name=field_name,
                suggested_fix=f"Truncate to {max_length} characters",
                error_code="STRING_TOO_LONG"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"{field_name} is valid",
            field_name=field_name
        )
    
    @classmethod
    def validate_integer_field(cls, value: Any, field_name: str,
                             min_value: Optional[int] = None,
                             max_value: Optional[int] = None) -> ValidationResult:
        """
        Validate integer field with range constraints.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            ValidationResult with validation details
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be None",
                field_name=field_name,
                error_code="INTEGER_NONE"
            )
        
        if not isinstance(value, int):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} must be an integer, got {type(value).__name__}",
                field_name=field_name,
                error_code="INTEGER_WRONG_TYPE"
            )
        
        if min_value is not None and value < min_value:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too small (min {min_value})",
                field_name=field_name,
                error_code="INTEGER_TOO_SMALL"
            )
        
        if max_value is not None and value > max_value:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too large (max {max_value})",
                field_name=field_name,
                error_code="INTEGER_TOO_LARGE"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"{field_name} is valid",
            field_name=field_name
        )
    
    @classmethod
    def validate_float_field(cls, value: Any, field_name: str,
                           min_value: Optional[float] = None,
                           max_value: Optional[float] = None) -> ValidationResult:
        """
        Validate float field with range constraints.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            ValidationResult with validation details
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be None",
                field_name=field_name,
                error_code="FLOAT_NONE"
            )
        
        if not isinstance(value, (int, float)):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} must be a number, got {type(value).__name__}",
                field_name=field_name,
                error_code="FLOAT_WRONG_TYPE"
            )
        
        value = float(value)
        
        if min_value is not None and value < min_value:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too small (min {min_value})",
                field_name=field_name,
                error_code="FLOAT_TOO_SMALL"
            )
        
        if max_value is not None and value > max_value:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} too large (max {max_value})",
                field_name=field_name,
                error_code="FLOAT_TOO_LARGE"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"{field_name} is valid",
            field_name=field_name
        )
    
    @classmethod
    def validate_datetime_field(cls, value: Any, field_name: str) -> ValidationResult:
        """
        Validate datetime field.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            
        Returns:
            ValidationResult with validation details
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be None",
                field_name=field_name,
                error_code="DATETIME_NONE"
            )
        
        if not isinstance(value, datetime):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} must be a datetime object, got {type(value).__name__}",
                field_name=field_name,
                error_code="DATETIME_WRONG_TYPE"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"{field_name} is valid",
            field_name=field_name
        )
    
    @classmethod
    def validate_list_field(cls, value: Any, field_name: str,
                          min_items: int = 0, max_items: Optional[int] = None,
                          item_validator: Optional[Callable] = None) -> ValidationResult:
        """
        Validate list field with item count and optional item validation.
        
        Args:
            value: Value to validate
            field_name: Name of the field being validated
            min_items: Minimum required items
            max_items: Maximum allowed items
            item_validator: Optional function to validate each item
            
        Returns:
            ValidationResult with validation details
        """
        if value is None:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} cannot be None",
                field_name=field_name,
                error_code="LIST_NONE"
            )
        
        if not isinstance(value, list):
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} must be a list, got {type(value).__name__}",
                field_name=field_name,
                error_code="LIST_WRONG_TYPE"
            )
        
        if len(value) < min_items:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} has too few items (min {min_items})",
                field_name=field_name,
                error_code="LIST_TOO_FEW_ITEMS"
            )
        
        if max_items and len(value) > max_items:
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"{field_name} has too many items (max {max_items})",
                field_name=field_name,
                error_code="LIST_TOO_MANY_ITEMS"
            )
        
        # Validate individual items if validator provided
        if item_validator:
            for i, item in enumerate(value):
                try:
                    item_result = item_validator(item)
                    if hasattr(item_result, 'is_valid') and not item_result.is_valid:
                        return ValidationResult(
                            is_valid=False,
                            severity=ValidationSeverity.ERROR,
                            message=f"{field_name}[{i}]: {item_result.message}",
                            field_name=field_name,
                            error_code="LIST_INVALID_ITEM"
                        )
                except Exception as e:
                    return ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"{field_name}[{i}]: Validation error - {str(e)}",
                        field_name=field_name,
                        error_code="LIST_ITEM_VALIDATION_ERROR"
                    )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message=f"{field_name} is valid",
            field_name=field_name
        )
    
    @classmethod
    def validate_linkedin_profile(cls, profile_data: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate LinkedIn profile data comprehensively.
        
        Args:
            profile_data: Dictionary containing LinkedIn profile data
            
        Returns:
            List of ValidationResult objects for each field
        """
        results = []
        
        # Validate name
        results.append(cls.validate_string_field(
            profile_data.get('name'), 'name', min_length=2, max_length=100
        ))
        
        # Validate current role
        results.append(cls.validate_string_field(
            profile_data.get('current_role'), 'current_role', min_length=2, max_length=200
        ))
        
        # Validate experience list
        experience = profile_data.get('experience', [])
        results.append(cls.validate_list_field(
            experience, 'experience', min_items=0, max_items=20
        ))
        
        # Validate skills list
        skills = profile_data.get('skills', [])
        results.append(cls.validate_list_field(
            skills, 'skills', min_items=0, max_items=50
        ))
        
        # Validate summary (optional)
        summary = profile_data.get('summary', '')
        if summary:
            results.append(cls.validate_string_field(
                summary, 'summary', min_length=10, max_length=2000, allow_empty=True
            ))
        
        return results
    
    @classmethod
    def validate_company_data(cls, company_data: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate company data comprehensively.
        
        Args:
            company_data: Dictionary containing company data
            
        Returns:
            List of ValidationResult objects for each field
        """
        results = []
        
        # Validate name
        results.append(cls.validate_string_field(
            company_data.get('name'), 'name', min_length=1, max_length=200
        ))
        
        # Validate domain
        domain = company_data.get('domain')
        if domain:
            results.append(cls.validate_domain(domain))
        else:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Domain is required",
                field_name="domain",
                error_code="DOMAIN_REQUIRED"
            ))
        
        # Validate product URL
        product_url = company_data.get('product_url')
        if product_url:
            results.append(cls.validate_url(product_url))
        else:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Product URL is required",
                field_name="product_url",
                error_code="PRODUCT_URL_REQUIRED"
            ))
        
        # Validate description
        results.append(cls.validate_string_field(
            company_data.get('description'), 'description', min_length=10, max_length=5000
        ))
        
        # Validate launch date
        launch_date = company_data.get('launch_date')
        if launch_date:
            results.append(cls.validate_datetime_field(launch_date, 'launch_date'))
        else:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Launch date is required",
                field_name="launch_date",
                error_code="LAUNCH_DATE_REQUIRED"
            ))
        
        return results
    
    @classmethod
    def validate_multiple_results(cls, results: List[ValidationResult]) -> ValidationResult:
        """
        Combine multiple validation results into a single result.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            Combined ValidationResult
        """
        if not results:
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.INFO,
                message="No validation performed"
            )
        
        errors = [r for r in results if not r.is_valid and r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in results if not r.is_valid and r.severity == ValidationSeverity.WARNING]
        
        if errors:
            error_messages = [r.message for r in errors]
            return ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Validation failed: {'; '.join(error_messages)}",
                error_code="MULTIPLE_VALIDATION_ERRORS"
            )
        
        if warnings:
            warning_messages = [r.message for r in warnings]
            return ValidationResult(
                is_valid=True,
                severity=ValidationSeverity.WARNING,
                message=f"Validation passed with warnings: {'; '.join(warning_messages)}",
                error_code="MULTIPLE_VALIDATION_WARNINGS"
            )
        
        return ValidationResult(
            is_valid=True,
            severity=ValidationSeverity.INFO,
            message="All validations passed"
        )
