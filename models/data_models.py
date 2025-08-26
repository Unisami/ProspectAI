"""
Core data models for the job prospect automation system.
"""

from dataclasses import (
    dataclass,
    field
)
from datetime import datetime
from typing import (
    List,
    Optional,
    Dict,
    Any,
    Union
)
from enum import Enum
import re

from utils.validation_framework import (
    ValidationFramework,
    ValidationResult,
    ValidationSeverity
)



class ProspectStatus(Enum):
    """Status enum for prospect tracking."""
    NOT_CONTACTED = "Not Contacted"
    CONTACTED = "Contacted"
    RESPONDED = "Responded"
    REJECTED = "Rejected"


class EmailTemplate(Enum):
    """Available email templates for different outreach scenarios."""
    COLD_OUTREACH = "cold_outreach"
    REFERRAL_FOLLOWUP = "referral_followup"
    PRODUCT_INTEREST = "product_interest"
    NETWORKING = "networking"


class IssueCategory(Enum):
    """Categories for user-reported issues."""
    BUG = "Bug"
    IMPROVEMENT = "Improvement"
    QUESTION = "Question"
    SETUP = "Setup"


class IssueStatus(Enum):
    """Status enum for issue tracking."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class ValidationError(Exception):
    """Custom exception for data validation errors."""
    pass


@dataclass
class CompanyData:
    """Data model for company information scraped from ProductHunt."""
    name: str
    domain: str
    product_url: str
    description: str
    launch_date: datetime
    
    def __post_init__(self):
        """Validate company data after initialization."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate company data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        company_dict = {
            'name': self.name,
            'domain': self.domain,
            'product_url': self.product_url,
            'description': self.description,
            'launch_date': self.launch_date
        }
        
        results = ValidationFramework.validate_company_data(company_dict)
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'domain': self.domain,
            'product_url': self.product_url,
            'description': self.description,
            'launch_date': self.launch_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompanyData':
        """
        Create CompanyData instance from dictionary.
        
        Args:
            data: Dictionary containing company data
            
        Returns:
            CompanyData instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Handle datetime conversion
        launch_date = data.get('launch_date')
        if isinstance(launch_date, str):
            try:
                launch_date = datetime.fromisoformat(launch_date.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(f"Invalid launch_date format: {launch_date}")
        elif not isinstance(launch_date, datetime):
            raise ValidationError("launch_date must be a datetime object or ISO string")
        
        return cls(
            name=data.get('name', ''),
            domain=data.get('domain', ''),
            product_url=data.get('product_url', ''),
            description=data.get('description', ''),
            launch_date=launch_date
        )


@dataclass
class TeamMember:
    """Data model for team member information."""
    name: str
    role: str
    company: str
    linkedin_url: Optional[str] = None
    
    def __post_init__(self):
        """Validate team member data after initialization."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate team member data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate name
        results.append(ValidationFramework.validate_string_field(
            self.name, 'name', min_length=2, max_length=100
        ))
        
        # Validate role
        results.append(ValidationFramework.validate_string_field(
            self.role, 'role', min_length=2, max_length=200
        ))
        
        # Validate company
        results.append(ValidationFramework.validate_string_field(
            self.company, 'company', min_length=1, max_length=200
        ))
        
        # Validate LinkedIn URL if provided
        if self.linkedin_url:
            if self.linkedin_url.strip():
                results.append(ValidationFramework.validate_linkedin_url(self.linkedin_url))
            else:
                self.linkedin_url = None
        
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'role': self.role,
            'company': self.company,
            'linkedin_url': self.linkedin_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamMember':
        """
        Create TeamMember instance from dictionary.
        
        Args:
            data: Dictionary containing team member data
            
        Returns:
            TeamMember instance
            
        Raises:
            ValidationError: If data is invalid
        """
        return cls(
            name=data.get('name', ''),
            role=data.get('role', ''),
            company=data.get('company', ''),
            linkedin_url=data.get('linkedin_url')
        )


@dataclass
class Prospect:
    """Data model for prospect information stored in Notion."""
    name: str
    role: str
    company: str
    id: str = field(default_factory=lambda: "")
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    contacted: bool = False
    status: ProspectStatus = ProspectStatus.NOT_CONTACTED
    notes: str = ""
    source_url: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    # Email-related fields
    email_generation_status: str = "Not Generated"
    email_delivery_status: str = "Not Sent"
    email_subject: str = ""
    email_content: str = ""
    email_generated_date: Optional[datetime] = None
    email_sent_date: Optional[datetime] = None
    
    # AI-structured data fields for enhanced personalization
    product_summary: str = ""
    business_insights: str = ""
    linkedin_summary: str = ""
    personalization_data: str = ""
    
    def __post_init__(self):
        """Validate prospect data after initialization."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate prospect data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate name
        results.append(ValidationFramework.validate_string_field(
            self.name, 'name', min_length=2, max_length=100
        ))
        
        # Validate role
        results.append(ValidationFramework.validate_string_field(
            self.role, 'role', min_length=2, max_length=200
        ))
        
        # Validate company
        results.append(ValidationFramework.validate_string_field(
            self.company, 'company', min_length=1, max_length=200
        ))
        
        # Validate email if provided
        if self.email:
            if self.email.strip():
                results.append(ValidationFramework.validate_email(self.email))
            else:
                self.email = None
        
        # Validate LinkedIn URL if provided
        if self.linkedin_url:
            if self.linkedin_url.strip():
                results.append(ValidationFramework.validate_linkedin_url(self.linkedin_url))
            else:
                self.linkedin_url = None
        
        # Validate status
        if not isinstance(self.status, ProspectStatus):
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Status must be a ProspectStatus enum value",
                field_name="status",
                error_code="STATUS_INVALID_TYPE"
            ))
        
        # Validate created_at
        results.append(ValidationFramework.validate_datetime_field(self.created_at, 'created_at'))
        
        # Validate notes (optional)
        if self.notes:
            results.append(ValidationFramework.validate_string_field(
                self.notes, 'notes', min_length=0, max_length=5000, allow_empty=True
            ))
        
        # Validate source_url (optional)
        if self.source_url:
            results.append(ValidationFramework.validate_url(self.source_url))
        
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'company': self.company,
            'linkedin_url': self.linkedin_url,
            'email': self.email,
            'contacted': self.contacted,
            'status': self.status.value,
            'notes': self.notes,
            'source_url': self.source_url,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prospect':
        """
        Create Prospect instance from dictionary.
        
        Args:
            data: Dictionary containing prospect data
            
        Returns:
            Prospect instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        # Handle status conversion
        status = data.get('status', ProspectStatus.NOT_CONTACTED)
        if isinstance(status, str):
            try:
                status = ProspectStatus(status)
            except ValueError:
                status = ProspectStatus.NOT_CONTACTED
        
        return cls(
            name=data.get('name', ''),
            role=data.get('role', ''),
            company=data.get('company', ''),
            id=data.get('id', ''),
            linkedin_url=data.get('linkedin_url'),
            email=data.get('email'),
            contacted=data.get('contacted', False),
            status=status,
            notes=data.get('notes', ''),
            source_url=data.get('source_url', ''),
            created_at=created_at
        )


@dataclass
class LinkedInProfile:
    """Data model for LinkedIn profile information."""
    name: str
    current_role: str
    experience: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    summary: str = ""
    
    def __post_init__(self):
        """Validate LinkedIn profile data after initialization."""
        # Clean up empty strings in lists before validation
        self.experience = [exp.strip() for exp in self.experience if exp and str(exp).strip()]
        self.skills = [skill.strip() for skill in self.skills if skill and str(skill).strip()]
        
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate LinkedIn profile data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        profile_dict = {
            'name': self.name,
            'current_role': self.current_role,
            'experience': self.experience,
            'skills': self.skills,
            'summary': self.summary
        }
        
        results = ValidationFramework.validate_linkedin_profile(profile_dict)
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'current_role': self.current_role,
            'experience': self.experience,
            'skills': self.skills,
            'summary': self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LinkedInProfile':
        """
        Create LinkedInProfile instance from dictionary.
        
        Args:
            data: Dictionary containing LinkedIn profile data
            
        Returns:
            LinkedInProfile instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Ensure lists are properly handled
        experience = data.get('experience', [])
        if not isinstance(experience, list):
            experience = []
        
        skills = data.get('skills', [])
        if not isinstance(skills, list):
            skills = []
        
        return cls(
            name=data.get('name', ''),
            current_role=data.get('current_role', ''),
            experience=experience,
            skills=skills,
            summary=data.get('summary', '')
        )


@dataclass
class EmailData:
    """Data model for email information from Hunter.io."""
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    confidence: Optional[int] = None
    sources: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate email data after initialization."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate email data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate email (required)
        results.append(ValidationFramework.validate_email(self.email))
        
        # Validate optional string fields
        if self.first_name:
            results.append(ValidationFramework.validate_string_field(
                self.first_name, 'first_name', min_length=1, max_length=50, allow_empty=True
            ))
        
        if self.last_name:
            results.append(ValidationFramework.validate_string_field(
                self.last_name, 'last_name', min_length=1, max_length=50, allow_empty=True
            ))
        
        if self.position:
            results.append(ValidationFramework.validate_string_field(
                self.position, 'position', min_length=1, max_length=200, allow_empty=True
            ))
        
        if self.department:
            results.append(ValidationFramework.validate_string_field(
                self.department, 'department', min_length=1, max_length=100, allow_empty=True
            ))
        
        # Validate confidence if provided
        if self.confidence is not None:
            results.append(ValidationFramework.validate_integer_field(
                self.confidence, 'confidence', min_value=0, max_value=100
            ))
        
        # Validate sources list
        results.append(ValidationFramework.validate_list_field(
            self.sources, 'sources', min_items=0, max_items=20
        ))
        
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'position': self.position,
            'department': self.department,
            'confidence': self.confidence,
            'sources': self.sources
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailData':
        """
        Create EmailData instance from dictionary.
        
        Args:
            data: Dictionary containing email data
            
        Returns:
            EmailData instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Ensure sources is a list
        sources = data.get('sources', [])
        if not isinstance(sources, list):
            sources = []
        
        return cls(
            email=data.get('email', ''),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            position=data.get('position'),
            department=data.get('department'),
            confidence=data.get('confidence'),
            sources=sources
        )


@dataclass
class EmailVerification:
    """Data model for email verification results from Hunter.io."""
    email: str
    result: str  # "deliverable", "undeliverable", "risky", "unknown"
    score: Optional[int] = None
    regexp: Optional[bool] = None
    gibberish: Optional[bool] = None
    disposable: Optional[bool] = None
    webmail: Optional[bool] = None
    mx_records: Optional[bool] = None
    smtp_server: Optional[bool] = None
    smtp_check: Optional[bool] = None
    accept_all: Optional[bool] = None
    block: Optional[bool] = None
    
    def __post_init__(self):
        """Validate email verification data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate email verification data fields."""
        if not self.email or not self.email.strip():
            raise ValidationError("Email cannot be empty")
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.email.strip()):
            raise ValidationError(f"Invalid email format: {self.email}")
        
        # Validate result
        valid_results = ["deliverable", "undeliverable", "risky", "unknown"]
        if self.result not in valid_results:
            raise ValidationError(f"Result must be one of: {valid_results}")
        
        # Validate score if provided
        if self.score is not None:
            if not isinstance(self.score, int) or not 0 <= self.score <= 100:
                raise ValidationError("Score must be an integer between 0 and 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'email': self.email,
            'result': self.result,
            'score': self.score,
            'regexp': self.regexp,
            'gibberish': self.gibberish,
            'disposable': self.disposable,
            'webmail': self.webmail,
            'mx_records': self.mx_records,
            'smtp_server': self.smtp_server,
            'smtp_check': self.smtp_check,
            'accept_all': self.accept_all,
            'block': self.block
        }


@dataclass
class EmailContent:
    """Data model for generated email content."""
    subject: str
    body: str
    template_used: str
    personalization_score: float = 0.0
    recipient_name: str = ""
    company_name: str = ""
    
    def __post_init__(self):
        """Validate email content data after initialization."""
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate email content data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate subject
        results.append(ValidationFramework.validate_string_field(
            self.subject, 'subject', min_length=5, max_length=200
        ))
        
        # Validate body
        results.append(ValidationFramework.validate_string_field(
            self.body, 'body', min_length=10, max_length=15000
        ))
        
        # Validate template_used
        results.append(ValidationFramework.validate_string_field(
            self.template_used, 'template_used', min_length=1, max_length=100
        ))
        
        # Validate personalization_score
        results.append(ValidationFramework.validate_float_field(
            self.personalization_score, 'personalization_score', min_value=0.0, max_value=1.0
        ))
        
        # Validate optional fields
        if self.recipient_name:
            results.append(ValidationFramework.validate_string_field(
                self.recipient_name, 'recipient_name', min_length=1, max_length=100, allow_empty=True
            ))
        
        if self.company_name:
            results.append(ValidationFramework.validate_string_field(
                self.company_name, 'company_name', min_length=1, max_length=200, allow_empty=True
            ))
        
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'subject': self.subject,
            'body': self.body,
            'template_used': self.template_used,
            'personalization_score': self.personalization_score,
            'recipient_name': self.recipient_name,
            'company_name': self.company_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailContent':
        """
        Create EmailContent instance from dictionary.
        
        Args:
            data: Dictionary containing email content data
            
        Returns:
            EmailContent instance
            
        Raises:
            ValidationError: If data is invalid
        """
        return cls(
            subject=data.get('subject', ''),
            body=data.get('body', ''),
            template_used=data.get('template_used', ''),
            personalization_score=data.get('personalization_score', 0.0),
            recipient_name=data.get('recipient_name', ''),
            company_name=data.get('company_name', '')
        )


@dataclass
class SendResult:
    """Data model for email sending results."""
    email_id: str
    status: str
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    recipient_email: str = ""
    subject: str = ""
    
    def __post_init__(self):
        """Validate send result data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate send result data fields."""
        if not self.email_id or not self.email_id.strip():
            raise ValidationError("Email ID cannot be empty")
        
        if not self.status or not self.status.strip():
            raise ValidationError("Status cannot be empty")
        
        # Validate status values
        valid_statuses = ["sent", "delivered", "failed", "queued", "bounced"]
        if self.status not in valid_statuses:
            raise ValidationError(f"Status must be one of: {valid_statuses}")
        
        # Validate delivered_at if provided
        if self.delivered_at is not None and not isinstance(self.delivered_at, datetime):
            raise ValidationError("Delivered date must be a datetime object")
        
        # Validate recipient email if provided
        if self.recipient_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.recipient_email.strip()):
                raise ValidationError(f"Invalid recipient email format: {self.recipient_email}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'email_id': self.email_id,
            'status': self.status,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'error_message': self.error_message,
            'recipient_email': self.recipient_email,
            'subject': self.subject
        }


@dataclass
class DeliveryStatus:
    """Data model for email delivery status tracking."""
    email_id: str
    status: str  # sent, delivered, opened, clicked, bounced, complained
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate delivery status data after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate delivery status data fields."""
        if not self.email_id or not self.email_id.strip():
            raise ValidationError("Email ID cannot be empty")
        
        if not self.status or not self.status.strip():
            raise ValidationError("Status cannot be empty")
        
        # Validate status values
        valid_statuses = ["sent", "delivered", "opened", "clicked", "bounced", "complained", "failed"]
        if self.status not in valid_statuses:
            raise ValidationError(f"Status must be one of: {valid_statuses}")
        
        if not isinstance(self.timestamp, datetime):
            raise ValidationError("Timestamp must be a datetime object")
        
        if not isinstance(self.details, dict):
            raise ValidationError("Details must be a dictionary")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'email_id': self.email_id,
            'status': self.status,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details
        }


@dataclass
class SendingStats:
    """Data model for email sending statistics."""
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    total_complained: int = 0
    total_failed: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    
    def __post_init__(self):
        """Calculate rates after initialization."""
        self.calculate_rates()
    
    def calculate_rates(self) -> None:
        """Calculate delivery, open, click, and bounce rates."""
        if self.total_sent > 0:
            self.delivery_rate = self.total_delivered / self.total_sent
            self.bounce_rate = self.total_bounced / self.total_sent
        
        if self.total_delivered > 0:
            self.open_rate = self.total_opened / self.total_delivered
            
        if self.total_opened > 0:
            self.click_rate = self.total_clicked / self.total_opened
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_sent': self.total_sent,
            'total_delivered': self.total_delivered,
            'total_opened': self.total_opened,
            'total_clicked': self.total_clicked,
            'total_bounced': self.total_bounced,
            'total_complained': self.total_complained,
            'total_failed': self.total_failed,
            'delivery_rate': self.delivery_rate,
            'open_rate': self.open_rate,
            'click_rate': self.click_rate,
            'bounce_rate': self.bounce_rate
        }


@dataclass
class SenderProfile:
    """Data model for sender's professional context and background information."""
    name: str
    current_role: str
    years_experience: int
    key_skills: List[str] = field(default_factory=list)
    experience_summary: str = ""
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    value_proposition: str = ""
    target_roles: List[str] = field(default_factory=list)
    industries_of_interest: List[str] = field(default_factory=list)
    notable_achievements: List[str] = field(default_factory=list)
    portfolio_links: List[str] = field(default_factory=list)
    preferred_contact_method: str = "email"
    availability: str = ""
    location: str = ""
    remote_preference: str = ""
    salary_expectations: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate sender profile data after initialization."""
        # Clean up list fields before validation
        list_fields = [
            'key_skills', 'education', 'certifications', 'target_roles',
            'industries_of_interest', 'notable_achievements', 'portfolio_links'
        ]
        
        for field_name in list_fields:
            field_value = getattr(self, field_name)
            if isinstance(field_value, list):
                cleaned_list = [item.strip() for item in field_value if item and str(item).strip()]
                setattr(self, field_name, cleaned_list)
        
        validation_result = self.validate()
        if not validation_result.is_valid:
            raise ValidationError(validation_result.message)
    
    def validate(self) -> ValidationResult:
        """
        Validate sender profile data fields using ValidationFramework.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate name
        results.append(ValidationFramework.validate_string_field(
            self.name, 'name', min_length=2, max_length=100
        ))
        
        # Validate current_role
        results.append(ValidationFramework.validate_string_field(
            self.current_role, 'current_role', min_length=2, max_length=200
        ))
        
        # Validate years_experience
        results.append(ValidationFramework.validate_integer_field(
            self.years_experience, 'years_experience', min_value=0, max_value=70
        ))
        
        # Validate list fields - allow empty lists for validation but check completeness separately
        list_validations = [
            ('key_skills', self.key_skills, 0, 50),  # Allow empty for validation
            ('education', self.education, 0, 10),
            ('certifications', self.certifications, 0, 20),
            ('target_roles', self.target_roles, 0, 20),  # Allow empty for validation
            ('industries_of_interest', self.industries_of_interest, 0, 20),
            ('notable_achievements', self.notable_achievements, 0, 20),
            ('portfolio_links', self.portfolio_links, 0, 10)
        ]
        
        for field_name, field_value, min_items, max_items in list_validations:
            results.append(ValidationFramework.validate_list_field(
                field_value, field_name, min_items=min_items, max_items=max_items
            ))
        
        # Validate portfolio links individually
        for i, link in enumerate(self.portfolio_links):
            if link:
                url_result = ValidationFramework.validate_url(link)
                if not url_result.is_valid:
                    results.append(ValidationResult(
                        is_valid=False,
                        severity=ValidationSeverity.ERROR,
                        message=f"portfolio_links[{i}]: {url_result.message}",
                        field_name="portfolio_links",
                        error_code="PORTFOLIO_LINK_INVALID"
                    ))
        
        # Validate optional string fields
        optional_fields = [
            ('experience_summary', self.experience_summary, 10, 2000),
            ('value_proposition', self.value_proposition, 10, 1000),
            ('availability', self.availability, 0, 200),
            ('location', self.location, 0, 100),
            ('salary_expectations', self.salary_expectations, 0, 100)
        ]
        
        for field_name, field_value, min_len, max_len in optional_fields:
            if field_value:
                results.append(ValidationFramework.validate_string_field(
                    field_value, field_name, min_length=min_len, max_length=max_len, allow_empty=True
                ))
        
        # Validate preferred contact method
        valid_contact_methods = ["email", "linkedin", "phone", "other"]
        if self.preferred_contact_method not in valid_contact_methods:
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message=f"Preferred contact method must be one of: {valid_contact_methods}",
                field_name="preferred_contact_method",
                error_code="CONTACT_METHOD_INVALID"
            ))
        
        # Validate remote preference
        if self.remote_preference:
            valid_remote_prefs = ["remote", "hybrid", "on-site", "flexible"]
            if self.remote_preference.lower() not in valid_remote_prefs:
                results.append(ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Remote preference must be one of: {valid_remote_prefs}",
                    field_name="remote_preference",
                    error_code="REMOTE_PREFERENCE_INVALID"
                ))
        
        # Validate additional_context
        if not isinstance(self.additional_context, dict):
            results.append(ValidationResult(
                is_valid=False,
                severity=ValidationSeverity.ERROR,
                message="Additional context must be a dictionary",
                field_name="additional_context",
                error_code="ADDITIONAL_CONTEXT_INVALID_TYPE"
            ))
        
        return ValidationFramework.validate_multiple_results(results)
    
    def is_complete(self) -> bool:
        """Check if the profile has all essential information for effective email generation."""
        required_fields = [
            self.name,
            self.current_role,
            self.experience_summary,
            self.value_proposition
        ]
        
        # Check required fields are not empty
        if not all(field and field.strip() for field in required_fields):
            return False
        
        # Check minimum years of experience
        if self.years_experience < 0:
            return False
        
        # Check at least some skills are provided
        if not self.key_skills:
            return False
        
        # Check at least some target roles are specified
        if not self.target_roles:
            return False
        
        return True
    
    def get_completeness_score(self) -> float:
        """Calculate a completeness score (0.0 to 1.0) based on filled fields."""
        total_fields = 0
        filled_fields = 0
        
        # Required fields (weight: 2)
        required_fields = [
            (self.name, 2),
            (self.current_role, 2),
            (self.experience_summary, 2),
            (self.value_proposition, 2)
        ]
        
        for field, weight in required_fields:
            total_fields += weight
            if field and field.strip():
                filled_fields += weight
        
        # Important fields (weight: 1.5)
        important_fields = [
            (self.key_skills, 1.5),
            (self.target_roles, 1.5),
            (self.notable_achievements, 1.5)
        ]
        
        for field, weight in important_fields:
            total_fields += weight
            if field:
                filled_fields += weight
        
        # Optional fields (weight: 1)
        optional_fields = [
            (self.education, 1),
            (self.certifications, 1),
            (self.industries_of_interest, 1),
            (self.portfolio_links, 1),
            (self.availability, 1),
            (self.location, 1),
            (self.remote_preference, 1)
        ]
        
        for field, weight in optional_fields:
            total_fields += weight
            if field:
                filled_fields += weight
        
        # Years of experience (weight: 1)
        total_fields += 1
        if self.years_experience >= 0:
            filled_fields += 1
        
        return filled_fields / total_fields if total_fields > 0 else 0.0
    
    def get_missing_fields(self) -> List[str]:
        """Get a list of important missing fields for profile completion."""
        missing = []
        
        if not self.name or not self.name.strip():
            missing.append("name")
        
        if not self.current_role or not self.current_role.strip():
            missing.append("current_role")
        
        if not self.experience_summary or not self.experience_summary.strip():
            missing.append("experience_summary")
        
        if not self.value_proposition or not self.value_proposition.strip():
            missing.append("value_proposition")
        
        if not self.key_skills:
            missing.append("key_skills")
        
        if not self.target_roles:
            missing.append("target_roles")
        
        if self.years_experience < 0:
            missing.append("years_experience")
        
        return missing
    
    def get_relevant_experience(self, target_role: str, target_company: str = "") -> List[str]:
        """Get relevant experience and achievements for a specific target role and company."""
        relevant_items = []
        
        # Convert to lowercase for matching
        target_role_lower = target_role.lower()
        target_company_lower = target_company.lower() if target_company else ""
        
        # Check if current role is relevant
        if any(keyword in self.current_role.lower() for keyword in target_role_lower.split()):
            relevant_items.append(f"Current role: {self.current_role}")
        
        # Find relevant skills
        relevant_skills = []
        for skill in self.key_skills:
            if any(keyword in skill.lower() for keyword in target_role_lower.split()):
                relevant_skills.append(skill)
        
        if relevant_skills:
            relevant_items.append(f"Relevant skills: {', '.join(relevant_skills[:5])}")
        
        # Find relevant achievements
        relevant_achievements = []
        for achievement in self.notable_achievements:
            achievement_lower = achievement.lower()
            if (any(keyword in achievement_lower for keyword in target_role_lower.split()) or
                (target_company_lower and target_company_lower in achievement_lower)):
                relevant_achievements.append(achievement)
        
        if relevant_achievements:
            relevant_items.extend(relevant_achievements[:3])
        
        # Add experience summary if no specific matches found
        if not relevant_items and self.experience_summary:
            relevant_items.append(self.experience_summary)
        
        return relevant_items
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'current_role': self.current_role,
            'years_experience': self.years_experience,
            'key_skills': self.key_skills,
            'experience_summary': self.experience_summary,
            'education': self.education,
            'certifications': self.certifications,
            'value_proposition': self.value_proposition,
            'target_roles': self.target_roles,
            'industries_of_interest': self.industries_of_interest,
            'notable_achievements': self.notable_achievements,
            'portfolio_links': self.portfolio_links,
            'preferred_contact_method': self.preferred_contact_method,
            'availability': self.availability,
            'location': self.location,
            'remote_preference': self.remote_preference,
            'salary_expectations': self.salary_expectations,
            'additional_context': self.additional_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SenderProfile':
        """
        Create SenderProfile instance from dictionary.
        
        Args:
            data: Dictionary containing sender profile data
            
        Returns:
            SenderProfile instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Ensure list fields are properly handled
        list_fields = [
            'key_skills', 'education', 'certifications', 'target_roles',
            'industries_of_interest', 'notable_achievements', 'portfolio_links'
        ]
        
        for field_name in list_fields:
            field_value = data.get(field_name, [])
            if not isinstance(field_value, list):
                data[field_name] = []
        
        # Ensure additional_context is a dict
        additional_context = data.get('additional_context', {})
        if not isinstance(additional_context, dict):
            additional_context = {}
        
        return cls(
            name=data.get('name', ''),
            current_role=data.get('current_role', ''),
            years_experience=data.get('years_experience', 0),
            key_skills=data.get('key_skills', []),
            experience_summary=data.get('experience_summary', ''),
            education=data.get('education', []),
            certifications=data.get('certifications', []),
            value_proposition=data.get('value_proposition', ''),
            target_roles=data.get('target_roles', []),
            industries_of_interest=data.get('industries_of_interest', []),
            notable_achievements=data.get('notable_achievements', []),
            portfolio_links=data.get('portfolio_links', []),
            preferred_contact_method=data.get('preferred_contact_method', 'email'),
            availability=data.get('availability', ''),
            location=data.get('location', ''),
            remote_preference=data.get('remote_preference', ''),
            salary_expectations=data.get('salary_expectations'),
            additional_context=additional_context
        )


@dataclass
class Issue:
    """Data model for user-reported issues."""
    title: str
    description: str
    category: IssueCategory = IssueCategory.BUG
    status: IssueStatus = IssueStatus.OPEN
    created_at: datetime = field(default_factory=datetime.now)
    context: Optional[Dict[str, Any]] = field(default_factory=dict)
    issue_id: Optional[str] = None
    
    def __post_init__(self):
        """Generate issue ID if not provided."""
        if not self.issue_id:
            # Create simple issue ID based on timestamp
            timestamp = int(self.created_at.timestamp())
            self.issue_id = f"#{timestamp % 100000}"  # Last 5 digits for readability
    
    def validate(self) -> ValidationResult:
        """
        Validate issue data fields.
        
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate title
        results.append(ValidationFramework.validate_string_field(
            self.title, 'title', min_length=5, max_length=200
        ))
        
        # Validate description
        results.append(ValidationFramework.validate_string_field(
            self.description, 'description', min_length=10, max_length=5000
        ))
        
        return ValidationFramework.validate_multiple_results(results)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'issue_id': self.issue_id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'context': self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Issue':
        """
        Create Issue instance from dictionary.
        
        Args:
            data: Dictionary containing issue data
            
        Returns:
            Issue instance
            
        Raises:
            ValidationError: If data is invalid
        """
        # Handle datetime conversion
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except ValueError:
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        # Handle enum conversion
        category = data.get('category', IssueCategory.BUG.value)
        if isinstance(category, str):
            category = IssueCategory(category)
        
        status = data.get('status', IssueStatus.OPEN.value)
        if isinstance(status, str):
            status = IssueStatus(status)
        
        return cls(
            issue_id=data.get('issue_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            category=category,
            status=status,
            created_at=created_at,
            context=data.get('context', {})
        )
