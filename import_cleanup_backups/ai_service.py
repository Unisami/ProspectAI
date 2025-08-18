"""
Unified AI Service for all OpenAI operations.

This service consolidates AI-related functionality from multiple services into a single
AIService class, providing standardized AI processing patterns, error handling, and
caching for expensive AI operations.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from models.data_models import (
    LinkedInProfile, TeamMember, Prospect, EmailContent, 
    SenderProfile, ValidationError
)
from utils.validation_framework import ValidationFramework, ValidationResult, ValidationSeverity
from utils.base_service import BaseService, ServiceConfig, service_operation
from utils.config import Config
from utils.error_handling import ErrorCategory
from services.openai_client_manager import (
    get_client_manager, CompletionRequest, CompletionResponse
)


class AIOperationType(Enum):
    """Types of AI operations supported."""
    LINKEDIN_PARSING = "linkedin_parsing"
    EMAIL_GENERATION = "email_generation"
    PRODUCT_ANALYSIS = "product_analysis"
    TEAM_EXTRACTION = "team_extraction"
    BUSINESS_METRICS = "business_metrics"


class EmailTemplate(Enum):
    """Available email templates for different outreach scenarios."""
    COLD_OUTREACH = "cold_outreach"
    REFERRAL_FOLLOWUP = "referral_followup"
    PRODUCT_INTEREST = "product_interest"
    NETWORKING = "networking"


@dataclass
class ProductInfo:
    """Data model for structured product information."""
    name: str
    description: str
    features: List[str]
    pricing_model: str
    target_market: str
    competitors: List[str]
    funding_status: Optional[str] = None
    market_analysis: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'description': self.description,
            'features': self.features,
            'pricing_model': self.pricing_model,
            'target_market': self.target_market,
            'competitors': self.competitors,
            'funding_status': self.funding_status,
            'market_analysis': self.market_analysis
        }


@dataclass
class BusinessMetrics:
    """Data model for business metrics and insights."""
    employee_count: Optional[int] = None
    funding_amount: Optional[str] = None
    growth_stage: Optional[str] = None
    key_metrics: Dict[str, Any] = None
    business_model: Optional[str] = None
    revenue_model: Optional[str] = None
    market_position: Optional[str] = None
    
    def __post_init__(self):
        if self.key_metrics is None:
            self.key_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'employee_count': self.employee_count,
            'funding_amount': self.funding_amount,
            'growth_stage': self.growth_stage,
            'key_metrics': self.key_metrics,
            'business_model': self.business_model,
            'revenue_model': self.revenue_model,
            'market_position': self.market_position
        }


@dataclass
class AIResult:
    """Result of AI operation."""
    success: bool
    data: Optional[Union[LinkedInProfile, ProductInfo, List[TeamMember], BusinessMetrics, EmailContent]]
    operation_type: AIOperationType
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    raw_response: Optional[str] = None
    cached: bool = False


@dataclass
class ValidationResult:
    """Result of email content validation."""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    spam_score: float


class AIService(BaseService):
    """
    Unified AI service for all OpenAI operations.
    
    This service consolidates AI functionality from multiple services:
    - LinkedIn profile parsing (from ai_parser.py)
    - Email generation (from email_generator.py) 
    - Product analysis (from product_analyzer.py)
    - Team data extraction
    - Business metrics analysis
    
    Features:
    - Standardized AI processing patterns
    - Result caching for expensive operations
    - Comprehensive error handling
    - Performance monitoring
    """
    
    def __init__(self, config: Config, client_id: str = "ai_service"):
        """
        Initialize the AI Service.
        
        Args:
            config: Configuration object with OpenAI settings
            client_id: Identifier for the OpenAI client to use
        """
        service_config = ServiceConfig(
            name="AIService",
            rate_limit_delay=config.openai_delay if hasattr(config, 'openai_delay') else 1.0,
            max_retries=3,
            timeout=60,
            enable_caching=True,
            cache_ttl=3600
        )
        
        self.client_id = client_id
        self.client_manager = get_client_manager()
        
        super().__init__(config, service_config)
        
        # Result cache for expensive operations
        self._result_cache: Dict[str, Dict[str, Any]] = {}
        
        # Email templates
        self._email_templates = {
            EmailTemplate.COLD_OUTREACH: {
                "system_prompt": self._get_cold_outreach_system_prompt(),
                "user_template": self._get_cold_outreach_user_template()
            },
            EmailTemplate.REFERRAL_FOLLOWUP: {
                "system_prompt": self._get_referral_system_prompt(),
                "user_template": self._get_referral_user_template()
            },
            EmailTemplate.PRODUCT_INTEREST: {
                "system_prompt": self._get_product_interest_system_prompt(),
                "user_template": self._get_product_interest_user_template()
            },
            EmailTemplate.NETWORKING: {
                "system_prompt": self._get_networking_system_prompt(),
                "user_template": self._get_networking_user_template()
            }
        }
    
    def _initialize_service(self) -> None:
        """Initialize AI service-specific components."""
        try:
            self.client_manager.configure(self.config, self.client_id)
            self.logger.info(f"Configured OpenAI client '{self.client_id}' for AI Service")
        except Exception as e:
            self.logger.error(f"Failed to configure OpenAI client: {str(e)}")
            raise
    
    def _generate_cache_key(self, operation: AIOperationType, content: str, **kwargs) -> str:
        """Generate cache key for AI operation."""
        # Create a hash of the content and parameters for caching
        import hashlib
        
        key_data = f"{operation.value}:{content[:500]}"  # Use first 500 chars
        for k, v in sorted(kwargs.items()):
            key_data += f":{k}={str(v)}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[AIResult]:
        """Get cached result if available and not expired."""
        if not self.service_config.enable_caching:
            return None
        
        cached_data = self._result_cache.get(cache_key)
        if not cached_data:
            return None
        
        # Check if cache is expired
        cache_time = cached_data.get('timestamp', 0)
        if time.time() - cache_time > self.service_config.cache_ttl:
            del self._result_cache[cache_key]
            return None
        
        # Return cached result
        result = cached_data['result']
        result.cached = True
        return result
    
    def _cache_result(self, cache_key: str, result: AIResult) -> None:
        """Cache AI operation result."""
        if not self.service_config.enable_caching:
            return
        
        self._result_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    @service_operation("parse_linkedin_profile", ErrorCategory.NETWORK)
    def parse_linkedin_profile(
        self, 
        raw_html: str, 
        fallback_data: Optional[Dict] = None
    ) -> AIResult:
        """
        Parse LinkedIn profile HTML into structured LinkedInProfile object.
        
        Args:
            raw_html: Raw HTML content from LinkedIn profile page
            fallback_data: Optional fallback data if parsing fails
            
        Returns:
            AIResult with LinkedInProfile data or error information
        """
        cache_key = self._generate_cache_key(
            AIOperationType.LINKEDIN_PARSING, 
            raw_html,
            has_fallback=fallback_data is not None
        )
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("Returning cached LinkedIn parsing result")
            return cached_result
        
        try:
            self.logger.info("Parsing LinkedIn profile data using AI")
            
            system_prompt = self._get_linkedin_parsing_prompt()
            user_prompt = f"""
            Parse the following LinkedIn profile HTML and extract structured information:
            
            HTML Content:
            {raw_html[:12000]}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            # Make completion request
            response = self.client_manager.make_completion(request, self.client_id)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            parsed_data = self._extract_json_from_response(response.content)
            
            # Create LinkedInProfile object
            linkedin_profile = LinkedInProfile(
                name=parsed_data.get('name', ''),
                current_role=parsed_data.get('current_role', ''),
                experience=parsed_data.get('experience', []),
                skills=parsed_data.get('skills', []),
                summary=parsed_data.get('summary', '')
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                parsed_data, AIOperationType.LINKEDIN_PARSING
            )
            
            result = AIResult(
                success=True,
                data=linkedin_profile,
                operation_type=AIOperationType.LINKEDIN_PARSING,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Successfully parsed LinkedIn profile with confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to parse LinkedIn profile: {str(e)}")
            
            # Try fallback if available
            if fallback_data:
                return self._handle_linkedin_fallback(fallback_data, str(e))
            
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.LINKEDIN_PARSING,
                error_message=str(e)
            )
    
    @service_operation("generate_email", ErrorCategory.NETWORK)
    def generate_email(
        self,
        prospect: Prospect,
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        linkedin_profile: Optional[LinkedInProfile] = None,
        product_analysis: Optional[Any] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        ai_structured_data: Optional[Dict[str, str]] = None,
        sender_profile: Optional[SenderProfile] = None
    ) -> AIResult:
        """
        Generate a personalized outreach email for a prospect.
        
        Args:
            prospect: The prospect to generate email for
            template_type: Type of email template to use
            linkedin_profile: Optional LinkedIn profile data for personalization
            product_analysis: Optional product analysis data
            additional_context: Additional context for personalization
            ai_structured_data: AI-structured data from Notion for enhanced personalization
            sender_profile: Optional sender profile for personalization
            
        Returns:
            AIResult with EmailContent data or error information
        """
        cache_key = self._generate_cache_key(
            AIOperationType.EMAIL_GENERATION,
            f"{prospect.name}:{prospect.company}:{template_type.value}",
            has_linkedin=linkedin_profile is not None,
            has_product=product_analysis is not None,
            has_sender=sender_profile is not None
        )
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("Returning cached email generation result")
            return cached_result
        
        try:
            self.logger.info(f"Generating {template_type.value} email for {prospect.name}")
            
            # Get template configuration
            template_config = self._email_templates[template_type]
            
            # Prepare personalization data
            personalization_data = self._prepare_personalization_data(
                prospect, linkedin_profile, product_analysis, 
                additional_context, ai_structured_data, sender_profile
            )
            
            # Generate user prompt from template
            user_prompt = template_config["user_template"].format(**personalization_data)
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": template_config["system_prompt"]},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            # Make completion request
            response = self.client_manager.make_completion(request, self.client_id)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse response
            subject, body = self._parse_generated_email_content(response.content)
            
            # Calculate personalization score
            personalization_score = self._calculate_personalization_score(
                body, personalization_data
            )
            
            # Create EmailContent object
            email_content = EmailContent(
                subject=subject,
                body=body,
                template_used=template_type.value,
                personalization_score=personalization_score,
                recipient_name=prospect.name,
                company_name=prospect.company
            )
            
            result = AIResult(
                success=True,
                data=email_content,
                operation_type=AIOperationType.EMAIL_GENERATION,
                confidence_score=personalization_score,
                raw_response=response.content
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Successfully generated email for {prospect.name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate email for {prospect.name}: {str(e)}")
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.EMAIL_GENERATION,
                error_message=str(e)
            )
    
    @service_operation("analyze_product", ErrorCategory.NETWORK)
    def analyze_product(self, raw_content: str, product_url: str = "") -> AIResult:
        """
        Parse product information from raw content into structured ProductInfo object.
        
        Args:
            raw_content: Raw content from product page or ProductHunt
            product_url: Optional product URL for context
            
        Returns:
            AIResult with ProductInfo data or error information
        """
        cache_key = self._generate_cache_key(
            AIOperationType.PRODUCT_ANALYSIS,
            raw_content,
            product_url=product_url
        )
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("Returning cached product analysis result")
            return cached_result
        
        try:
            self.logger.info("Analyzing product information using AI")
            
            system_prompt = self._get_product_parsing_prompt()
            user_prompt = f"""
            Parse the following product information and extract structured data:
            
            Product URL: {product_url}
            
            Content:
            {raw_content[:12000]}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            
            # Make completion request
            response = self.client_manager.make_completion(request, self.client_id)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            parsed_data = self._extract_json_from_response(response.content)
            
            # Create ProductInfo object
            product_info = ProductInfo(
                name=parsed_data.get('name', ''),
                description=parsed_data.get('description', ''),
                features=parsed_data.get('features', []),
                pricing_model=parsed_data.get('pricing_model', ''),
                target_market=parsed_data.get('target_market', ''),
                competitors=parsed_data.get('competitors', []),
                funding_status=parsed_data.get('funding_status'),
                market_analysis=parsed_data.get('market_analysis', '')
            )
            
            confidence_score = self._calculate_confidence_score(
                parsed_data, AIOperationType.PRODUCT_ANALYSIS
            )
            
            result = AIResult(
                success=True,
                data=product_info,
                operation_type=AIOperationType.PRODUCT_ANALYSIS,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Successfully analyzed product with confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to analyze product: {str(e)}")
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.PRODUCT_ANALYSIS,
                error_message=str(e)
            )
    
    @service_operation("extract_team_data", ErrorCategory.NETWORK)
    def extract_team_data(self, raw_team_info: str, company_name: str = "") -> AIResult:
        """
        Parse and structure team member information from raw content.
        
        Args:
            raw_team_info: Raw content containing team member information
            company_name: Company name for context
            
        Returns:
            AIResult with List[TeamMember] data or error information
        """
        cache_key = self._generate_cache_key(
            AIOperationType.TEAM_EXTRACTION,
            raw_team_info,
            company_name=company_name
        )
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("Returning cached team extraction result")
            return cached_result
        
        try:
            self.logger.info("Extracting team data using AI")
            
            system_prompt = self._get_team_parsing_prompt()
            user_prompt = f"""
            Parse the following team information and extract structured data:
            
            Company: {company_name}
            
            Team Information:
            {raw_team_info[:10000]}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            # Make completion request
            response = self.client_manager.make_completion(request, self.client_id)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            parsed_data = self._extract_json_array_from_response(response.content)
            
            # Create TeamMember objects
            team_members = []
            for member_data in parsed_data:
                try:
                    # Validate team member data before creating instance
                    member_validation = self._validate_team_member_data(member_data, company_name)
                    if not member_validation.is_valid:
                        self.logger.warning(f"Skipping invalid team member data: {member_validation.message}")
                        continue
                    
                    team_member = TeamMember(
                        name=member_data.get('name', ''),
                        role=member_data.get('role', ''),
                        company=company_name or member_data.get('company', ''),
                        linkedin_url=member_data.get('linkedin_url')
                    )
                    team_members.append(team_member)
                except ValidationError as e:
                    self.logger.warning(f"Skipping invalid team member data: {str(e)}")
                    continue
            
            confidence_score = len(team_members) / max(len(parsed_data), 1) if parsed_data else 0
            
            result = AIResult(
                success=True,
                data=team_members,
                operation_type=AIOperationType.TEAM_EXTRACTION,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Successfully extracted {len(team_members)} team members with confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to extract team data: {str(e)}")
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.TEAM_EXTRACTION,
                error_message=str(e)
            )
    
    def _validate_team_member_data(self, member_data: Dict[str, Any], company_name: str) -> ValidationResult:
        """
        Validate team member data using ValidationFramework.
        
        Args:
            member_data: Dictionary containing team member data
            company_name: Company name for the team member
            
        Returns:
            ValidationResult with validation details
        """
        results = []
        
        # Validate name
        results.append(ValidationFramework.validate_string_field(
            member_data.get('name', ''), 'name', min_length=2, max_length=100
        ))
        
        # Validate role
        results.append(ValidationFramework.validate_string_field(
            member_data.get('role', ''), 'role', min_length=2, max_length=200
        ))
        
        # Validate company (use provided company_name or from data)
        company = company_name or member_data.get('company', '')
        results.append(ValidationFramework.validate_string_field(
            company, 'company', min_length=1, max_length=200
        ))
        
        # Validate LinkedIn URL if provided
        linkedin_url = member_data.get('linkedin_url')
        if linkedin_url and linkedin_url.strip():
            results.append(ValidationFramework.validate_linkedin_url(linkedin_url))
        
        return ValidationFramework.validate_multiple_results(results)
    
    @service_operation("extract_business_metrics", ErrorCategory.NETWORK)
    def extract_business_metrics(self, company_data: str, company_name: str = "") -> AIResult:
        """
        Extract business metrics and insights from company data.
        
        Args:
            company_data: Raw content about the company
            company_name: Company name for context
            
        Returns:
            AIResult with BusinessMetrics data or error information
        """
        cache_key = self._generate_cache_key(
            AIOperationType.BUSINESS_METRICS,
            company_data,
            company_name=company_name
        )
        
        # Check cache first
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            self.logger.debug("Returning cached business metrics result")
            return cached_result
        
        try:
            self.logger.info("Extracting business metrics using AI")
            
            system_prompt = self._get_business_metrics_prompt()
            user_prompt = f"""
            Analyze the following company information and extract business metrics:
            
            Company: {company_name}
            
            Company Data:
            {company_data[:12000]}
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2500
            )
            
            # Make completion request
            response = self.client_manager.make_completion(request, self.client_id)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            parsed_data = self._extract_json_from_response(response.content)
            
            # Create BusinessMetrics object
            business_metrics = BusinessMetrics(
                employee_count=parsed_data.get('employee_count'),
                funding_amount=parsed_data.get('funding_amount'),
                growth_stage=parsed_data.get('growth_stage'),
                key_metrics=parsed_data.get('key_metrics', {}),
                business_model=parsed_data.get('business_model'),
                revenue_model=parsed_data.get('revenue_model'),
                market_position=parsed_data.get('market_position')
            )
            
            confidence_score = self._calculate_confidence_score(
                parsed_data, AIOperationType.BUSINESS_METRICS
            )
            
            result = AIResult(
                success=True,
                data=business_metrics,
                operation_type=AIOperationType.BUSINESS_METRICS,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
            # Cache the result
            self._cache_result(cache_key, result)
            
            self.logger.info(f"Successfully extracted business metrics with confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to extract business metrics: {str(e)}")
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.BUSINESS_METRICS,
                error_message=str(e)
            )
    
    def validate_email_content(self, content: str) -> ValidationResult:
        """
        Validate generated email content for quality and spam indicators.
        
        Args:
            content: Email content to validate
            
        Returns:
            ValidationResult with validation details
        """
        issues = []
        suggestions = []
        spam_indicators = 0
        
        # Check length
        word_count = len(content.split())
        if len(content) < 50:
            issues.append("Email content is too short")
            suggestions.append("Add more personalized content")
        elif len(content) > 2000 or word_count > 300:
            issues.append("Email content is too long")
            suggestions.append("Keep emails concise and focused")
        
        # Check for spam indicators
        spam_words = [
            'urgent', 'act now', 'limited time', 'free money', 'guaranteed',
            'no obligation', 'risk free', 'call now', 'click here', 'buy now'
        ]
        
        content_lower = content.lower()
        for word in spam_words:
            if word in content_lower:
                spam_indicators += 1
        
        # Check for excessive capitalization
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if caps_ratio > 0.3:
            spam_indicators += 2
            issues.append("Too much capitalization")
            suggestions.append("Use normal capitalization")
        
        # Check for excessive exclamation marks
        exclamation_count = content.count('!')
        if exclamation_count > 3:
            spam_indicators += 1
            issues.append("Too many exclamation marks")
            suggestions.append("Use exclamation marks sparingly")
        
        # Check for ProductHunt mention (requirement)
        if 'producthunt' not in content_lower and 'product hunt' not in content_lower:
            issues.append("Missing ProductHunt discovery source mention")
            suggestions.append("Mention how you discovered them through ProductHunt")
        
        # Calculate spam score (0-1, where 1 is very spammy)
        spam_score = min(spam_indicators / 10, 1.0)
        
        # Overall validation
        is_valid = len(issues) == 0 and spam_score < 0.3
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            suggestions=suggestions,
            spam_score=spam_score
        )
    
    def clear_cache(self) -> None:
        """Clear the result cache."""
        self._result_cache.clear()
        self.logger.info("Cleared AI service result cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._result_cache)
        cache_size_mb = sum(
            len(str(data)) for data in self._result_cache.values()
        ) / (1024 * 1024)
        
        return {
            'total_entries': total_entries,
            'cache_size_mb': round(cache_size_mb, 2),
            'cache_enabled': self.service_config.enable_caching,
            'cache_ttl': self.service_config.cache_ttl
        }
    
    def _extract_json_from_response(self, response_content: str) -> Dict[str, Any]:
        """Extract JSON object from AI response."""
        json_start = response_content.find('{')
        json_end = response_content.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON found in AI response")
        
        json_content = response_content[json_start:json_end]
        return json.loads(json_content)
    
    def _extract_json_array_from_response(self, response_content: str) -> List[Dict[str, Any]]:
        """Extract JSON array from AI response."""
        json_start = response_content.find('[')
        json_end = response_content.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No valid JSON array found in AI response")
        
        json_content = response_content[json_start:json_end]
        return json.loads(json_content)
    
    def _calculate_confidence_score(self, parsed_data: Dict[str, Any], operation_type: AIOperationType) -> float:
        """Calculate confidence score based on data completeness and quality."""
        if not parsed_data:
            return 0.0
        
        if operation_type == AIOperationType.LINKEDIN_PARSING:
            required_fields = ['name', 'current_role']
            optional_fields = ['experience', 'skills', 'summary']
            
            score = 0.0
            # Required fields (60% of score)
            for field in required_fields:
                if parsed_data.get(field) and len(str(parsed_data[field]).strip()) > 0:
                    score += 0.3
            
            # Optional fields (40% of score)
            for field in optional_fields:
                field_data = parsed_data.get(field)
                if field_data:
                    if isinstance(field_data, list) and len(field_data) > 0:
                        score += 0.133
                    elif isinstance(field_data, str) and len(field_data.strip()) > 0:
                        score += 0.133
            
            return min(score, 1.0)
        
        elif operation_type == AIOperationType.PRODUCT_ANALYSIS:
            required_fields = ['name', 'description']
            optional_fields = ['features', 'pricing_model', 'target_market', 'competitors']
            
            score = 0.0
            # Required fields (50% of score)
            for field in required_fields:
                if parsed_data.get(field) and len(str(parsed_data[field]).strip()) > 0:
                    score += 0.25
            
            # Optional fields (50% of score)
            for field in optional_fields:
                field_data = parsed_data.get(field)
                if field_data:
                    if isinstance(field_data, list) and len(field_data) > 0:
                        score += 0.125
                    elif isinstance(field_data, str) and len(field_data.strip()) > 0:
                        score += 0.125
            
            return min(score, 1.0)
        
        elif operation_type == AIOperationType.BUSINESS_METRICS:
            all_fields = ['employee_count', 'funding_amount', 'growth_stage', 'business_model', 'revenue_model']
            
            score = 0.0
            for field in all_fields:
                if parsed_data.get(field) is not None:
                    score += 0.2
            
            # Bonus for key_metrics
            if parsed_data.get('key_metrics') and len(parsed_data['key_metrics']) > 0:
                score += 0.1
            
            return min(score, 1.0)
        
        return 0.5  # Default confidence for unknown types
    
    def _handle_linkedin_fallback(self, fallback_data: Dict, error_message: str) -> AIResult:
        """Handle LinkedIn parsing failures with fallback data."""
        try:
            linkedin_profile = LinkedInProfile(
                name=fallback_data.get('name', ''),
                current_role=fallback_data.get('current_role', ''),
                experience=fallback_data.get('experience', []),
                skills=fallback_data.get('skills', []),
                summary=fallback_data.get('summary', '')
            )
            
            self.logger.info("Using fallback data for LinkedIn profile")
            return AIResult(
                success=True,
                data=linkedin_profile,
                operation_type=AIOperationType.LINKEDIN_PARSING,
                confidence_score=0.3,  # Lower confidence for fallback
                error_message=f"AI parsing failed, used fallback: {error_message}"
            )
        except Exception as e:
            self.logger.error(f"Fallback data also invalid: {str(e)}")
            return AIResult(
                success=False,
                data=None,
                operation_type=AIOperationType.LINKEDIN_PARSING,
                error_message=error_message
            )
    
    def _prepare_personalization_data(
        self, 
        prospect: Prospect, 
        linkedin_profile: Optional[LinkedInProfile] = None,
        product_analysis: Optional[Any] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        ai_structured_data: Optional[Dict[str, str]] = None,
        sender_profile: Optional[SenderProfile] = None
    ) -> Dict[str, str]:
        """Prepare personalization data for email generation."""
        data = {
            'name': prospect.name,
            'role': prospect.role,
            'company': prospect.company,
            'linkedin_url': prospect.linkedin_url or '',
            'source_url': prospect.source_url or '',
            'notes': prospect.notes or '',
            'skills': '',
            'experience': '',
            'summary': '',
            'mutual_connection': '',
            'specific_interest': '',
            'product_name': '',
            'product_description': '',
            'product_features': '',
            'pricing_model': '',
            'target_market': '',
            'competitors': '',
            'business_insights': '',
            'market_position': '',
            'personalization_points': '',
            'product_summary': '',
            'linkedin_summary': '',
            'market_analysis': '',
            # Sender profile fields
            'sender_name': '',
            'sender_role': '',
            'sender_experience_years': '',
            'sender_skills': '',
            'sender_experience_summary': '',
            'sender_education': '',
            'sender_certifications': '',
            'sender_value_proposition': '',
            'sender_achievements': '',
            'sender_portfolio': '',
            'sender_location': '',
            'sender_availability': '',
            'sender_remote_preference': '',
            'sender_relevant_experience': '',
            'sender_industry_match': '',
            'sender_skill_match': ''
        }
        
        # Add LinkedIn profile data if available
        if linkedin_profile:
            data['skills'] = ', '.join(linkedin_profile.skills[:5])  # Top 5 skills
            data['experience'] = '; '.join(linkedin_profile.experience[:3])  # Top 3 experiences
            data['summary'] = linkedin_profile.summary[:300]  # First 300 chars
        
        # Add product analysis data if available
        if product_analysis:
            if hasattr(product_analysis, 'name'):
                # ProductInfo object
                data['product_name'] = product_analysis.name or ''
                data['product_description'] = product_analysis.description or ''
                data['product_features'] = ', '.join(product_analysis.features[:3])
                data['pricing_model'] = product_analysis.pricing_model or ''
                data['target_market'] = product_analysis.target_market or ''
                data['competitors'] = ', '.join(product_analysis.competitors[:3])
                data['market_analysis'] = product_analysis.market_analysis[:600]
            elif isinstance(product_analysis, dict):
                # Dictionary format
                data['product_name'] = product_analysis.get('name', '')
                data['product_description'] = product_analysis.get('description', '')
                data['product_features'] = ', '.join(product_analysis.get('features', [])[:3])
                data['pricing_model'] = product_analysis.get('pricing_model', '')
                data['target_market'] = product_analysis.get('target_market', '')
                data['competitors'] = ', '.join(product_analysis.get('competitors', [])[:3])
                data['market_analysis'] = product_analysis.get('market_analysis', '')[:600]
        
        # Add AI-structured data from Notion (prioritize over raw data)
        if ai_structured_data:
            if ai_structured_data.get('product_summary'):
                data['product_summary'] = ai_structured_data['product_summary'][:800]
            
            if ai_structured_data.get('business_insights'):
                data['business_insights'] = ai_structured_data['business_insights'][:600]
            
            if ai_structured_data.get('linkedin_summary'):
                data['linkedin_summary'] = ai_structured_data['linkedin_summary'][:500]
                data['summary'] = ai_structured_data['linkedin_summary'][:300]
            
            if ai_structured_data.get('personalization_data'):
                data['personalization_points'] = ai_structured_data['personalization_data'][:400]
            elif ai_structured_data.get('personalization_points'):
                data['personalization_points'] = ai_structured_data['personalization_points'][:400]
        
        # Add sender profile data if available
        if sender_profile:
            data['sender_name'] = sender_profile.name or ''
            data['sender_role'] = sender_profile.current_role or ''
            data['sender_experience_years'] = str(sender_profile.years_experience) if sender_profile.years_experience else ''
            data['sender_skills'] = ', '.join(sender_profile.key_skills[:5])
            data['sender_experience_summary'] = sender_profile.experience_summary[:300] if sender_profile.experience_summary else ''
            data['sender_education'] = ', '.join(sender_profile.education[:2]) if sender_profile.education else ''
            data['sender_certifications'] = ', '.join(sender_profile.certifications[:3]) if sender_profile.certifications else ''
            data['sender_value_proposition'] = sender_profile.value_proposition[:200] if sender_profile.value_proposition else ''
            data['sender_achievements'] = ', '.join(sender_profile.notable_achievements[:3]) if sender_profile.notable_achievements else ''
            data['sender_portfolio'] = ', '.join(sender_profile.portfolio_links[:1]) if sender_profile.portfolio_links else ''
            data['sender_location'] = sender_profile.location or ''
            data['sender_availability'] = sender_profile.availability or ''
            data['sender_remote_preference'] = sender_profile.remote_preference or ''
        
        # Add additional context if provided
        if additional_context:
            for key, value in additional_context.items():
                if key not in data and isinstance(value, str):
                    data[key] = value[:200]  # Limit length
        
        return data
    
    def _parse_generated_email_content(self, generated_content: str) -> tuple[str, str]:
        """Parse generated email content to extract subject and body."""
        lines = generated_content.strip().split('\n')
        
        subject = ""
        body = ""
        
        # Look for subject line
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if line_lower.startswith('subject:'):
                subject = line[8:].strip()  # Remove "Subject:" prefix
                body = '\n'.join(lines[i+1:]).strip()
                break
            elif line_lower.startswith('subject line:'):
                subject = line[13:].strip()  # Remove "Subject line:" prefix
                body = '\n'.join(lines[i+1:]).strip()
                break
        
        # If no subject found, use first line as subject
        if not subject and lines:
            subject = lines[0].strip()
            body = '\n'.join(lines[1:]).strip()
        
        # Clean up subject (remove quotes if present)
        subject = subject.strip('"\'')
        
        # If body is empty, use the whole content as body
        if not body:
            body = generated_content.strip()
        
        return subject, body
    
    def _calculate_personalization_score(self, body: str, personalization_data: Dict[str, str]) -> float:
        """Calculate personalization score based on how much personalization data is used."""
        if not body or not personalization_data:
            return 0.0
        
        body_lower = body.lower()
        used_fields = 0
        total_fields = 0
        
        # Check which personalization fields are actually used in the email
        for key, value in personalization_data.items():
            if value and len(value.strip()) > 0:
                total_fields += 1
                # Check if the value (or part of it) appears in the email body
                if len(value) > 10:  # For longer values, check if part of it is used
                    words = value.split()[:3]  # Check first 3 words
                    if any(word.lower() in body_lower for word in words if len(word) > 3):
                        used_fields += 1
                elif value.lower() in body_lower:
                    used_fields += 1
        
        # Calculate score (0.0 to 1.0)
        if total_fields == 0:
            return 0.0
        
        base_score = used_fields / total_fields
        
        # Bonus for mentioning specific details
        bonus = 0.0
        if 'producthunt' in body_lower or 'product hunt' in body_lower:
            bonus += 0.1
        if personalization_data.get('company', '').lower() in body_lower:
            bonus += 0.1
        if personalization_data.get('name', '').lower() in body_lower:
            bonus += 0.1
        
        return min(base_score + bonus, 1.0)
    
    def _perform_health_check(self) -> bool:
        """Perform AI service-specific health check."""
        try:
            # Test OpenAI client connectivity
            test_request = CompletionRequest(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.1,
                max_tokens=10
            )
            
            response = self.client_manager.make_completion(test_request, self.client_id)
            return response.success
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    def _cleanup(self) -> None:
        """Perform AI service-specific cleanup."""
        self.clear_cache()
        self.logger.info("AI Service cleanup completed")    
    
# Prompt methods for different AI operations
    def _get_linkedin_parsing_prompt(self) -> str:
        """Get system prompt for LinkedIn profile parsing."""
        return """You are an expert at parsing LinkedIn profile HTML and extracting structured information.

Your task is to analyze LinkedIn profile HTML content and extract the following information in JSON format:

{
    "name": "Full name of the person",
    "current_role": "Current job title and company",
    "experience": ["List of previous roles and companies", "Format: 'Title at Company (Duration)'"],
    "skills": ["List of skills mentioned on the profile"],
    "summary": "Professional summary or about section (first 300 characters)"
}

Guidelines:
- Extract only factual information present in the HTML
- For experience, include the most recent 5-7 positions
- For skills, include the most relevant 10-15 skills
- If information is not available, use empty string or empty array
- Ensure all JSON keys are present even if values are empty
- Clean up any HTML tags or formatting artifacts
- Focus on professional information relevant for job outreach

Return only the JSON object, no additional text or explanation."""

    def _get_product_parsing_prompt(self) -> str:
        """Get system prompt for product information parsing."""
        return """You are an expert at analyzing product information and extracting structured business data.

Your task is to analyze product content and extract the following information in JSON format:

{
    "name": "Product name",
    "description": "Clear product description (2-3 sentences)",
    "features": ["List of key product features", "Focus on main capabilities"],
    "pricing_model": "Pricing strategy (e.g., freemium, subscription, one-time, enterprise)",
    "target_market": "Primary target audience or market segment",
    "competitors": ["List of main competitors mentioned or implied"],
    "funding_status": "Funding stage if mentioned (e.g., seed, series A, bootstrapped)",
    "market_analysis": "Brief analysis of market position and differentiation"
}

Guidelines:
- Extract factual information from the content
- Infer reasonable information based on context when explicit data isn't available
- Keep descriptions concise but informative
- For competitors, include both direct mentions and obvious market competitors
- If information is not available or unclear, use empty string or empty array
- Ensure all JSON keys are present
- Focus on information useful for business outreach and personalization

Return only the JSON object, no additional text or explanation."""

    def _get_team_parsing_prompt(self) -> str:
        """Get system prompt for team data parsing."""
        return """You are an expert at parsing team information and extracting structured member data.

Your task is to analyze team content and extract information about team members in JSON array format:

[
    {
        "name": "Full name of team member (MUST include both first and last name)",
        "role": "Job title or role in the company",
        "company": "Company name",
        "linkedin_url": "LinkedIn profile URL if available (or null)"
    }
]

CRITICAL GUIDELINES FOR NAME EXTRACTION:
- STRONGLY PREFER full names with both first and last names (e.g., "John Smith", "Sarah Johnson")
- AGGRESSIVELY search for full names in ALL sections: team pages, about pages, LinkedIn profiles, bios, contact info, author credits
- If you see "Nityam" mentioned, search for "Nityam [LastName]" elsewhere in the content
- Check for patterns like "Founded by John Smith and Sarah Johnson" or "Team: John Smith (CEO), Sarah Johnson (CTO)"
- Look for LinkedIn profile names which often contain full names
- Search for email signatures, contact pages, or staff directories
- Cross-reference names with roles and LinkedIn URLs to find complete information

FALLBACK STRATEGY:
- If after thorough searching you cannot find a full name, include single names for key team members (founders, executives)
- Single names are acceptable if they appear with important roles like "CEO", "Founder", "Co-founder"
- Always try to find the full name first, but don't skip important team members entirely

PROCESSING RULES:
- Clean up names and roles (remove extra whitespace, fix capitalization)
- For LinkedIn URLs, include full URLs starting with https://
- If LinkedIn URL is not available, use null
- Skip entries that don't have both name and role
- Ensure company name is consistent across all entries
- Focus on key team members (founders, executives, senior roles)
- Limit to maximum 15 team members to avoid overwhelming data

SEARCH PRIORITY:
1. First pass: Look for obvious full names in team sections
2. Second pass: For any single names found, search the entire content for that name + surname
3. Third pass: Check LinkedIn profiles, email addresses, and contact information for full names
4. Fallback: Include single names for key roles if no full name found

Return only the JSON array, no additional text or explanation."""

    def _get_business_metrics_prompt(self) -> str:
        """Get system prompt for business metrics extraction."""
        return """You are an expert at analyzing company information and extracting business metrics and insights.

Your task is to analyze company data and extract the following information in JSON format:

{
    "employee_count": 50,
    "funding_amount": "$2.5M Series A",
    "growth_stage": "early-stage startup",
    "key_metrics": {
        "users": "10K+ active users",
        "revenue": "ARR information if available",
        "growth_rate": "Growth metrics if mentioned"
    },
    "business_model": "B2B SaaS",
    "revenue_model": "subscription-based",
    "market_position": "Brief analysis of competitive position"
}

Guidelines:
- Extract factual metrics when explicitly mentioned
- Make reasonable inferences based on available information
- For employee_count, use integer if known, null if unknown
- For funding_amount, include stage and amount if available
- Growth stage options: "pre-seed", "seed", "early-stage startup", "growth-stage", "mature"
- Business model examples: "B2B SaaS", "B2C marketplace", "e-commerce", "consulting"
- Revenue model examples: "subscription", "transaction-based", "advertising", "freemium"
- Use null for unknown numeric values, empty string for unknown text values
- Key metrics should include any quantitative data mentioned

Return only the JSON object, no additional text or explanation."""

    def _get_cold_outreach_system_prompt(self) -> str:
        """Get system prompt for cold outreach email generation."""
        return """You are an expert at writing personalized cold outreach emails for job seekers.

Your task is to write a professional, personalized email that:
1. Mentions discovering the company through ProductHunt
2. Shows genuine interest in the company and their product
3. Highlights relevant skills and experience from the sender
4. Requests a brief conversation about potential opportunities
5. Maintains a professional but friendly tone

Guidelines:
- Keep the email concise (150-250 words)
- Use specific details about the company and product when available
- Mention relevant skills or experience that match the company's needs
- Include a clear but soft call-to-action
- Avoid being pushy or overly salesy
- Always mention ProductHunt as the discovery source
- Personalize based on the recipient's role and company

Format your response as:
Subject: [Email subject line]

[Email body]"""

    def _get_cold_outreach_user_template(self) -> str:
        """Get user template for cold outreach email generation."""
        return """Write a personalized cold outreach email with the following information:

Recipient: {name}
Role: {role}
Company: {company}
LinkedIn Profile: {linkedin_url}

Company Information:
- Product: {product_name}
- Description: {product_description}
- Key Features: {product_features}
- Target Market: {target_market}
- Business Insights: {business_insights}

LinkedIn Summary: {linkedin_summary}
Product Summary: {product_summary}

Sender Information:
- Name: {sender_name}
- Role: {sender_role}
- Skills: {sender_skills}
- Experience: {sender_experience_summary}
- Value Proposition: {sender_value_proposition}

Personalization Points: {personalization_points}

Additional Context: {notes}"""

    def _get_referral_system_prompt(self) -> str:
        """Get system prompt for referral followup email generation."""
        return """You are an expert at writing referral follow-up emails for job seekers.

Your task is to write a professional email that:
1. References the mutual connection or referral source
2. Mentions discovering the company through ProductHunt
3. Shows specific interest in the company's work
4. Highlights relevant qualifications
5. Requests a conversation about potential opportunities

Guidelines:
- Keep the email concise (150-250 words)
- Lead with the referral connection
- Use specific details about the company
- Show genuine interest in their product/mission
- Include relevant skills and experience
- Professional but warm tone
- Clear call-to-action

Format your response as:
Subject: [Email subject line]

[Email body]"""

    def _get_referral_user_template(self) -> str:
        """Get user template for referral followup email generation."""
        return """Write a referral follow-up email with the following information:

Recipient: {name}
Role: {role}
Company: {company}
Mutual Connection: {mutual_connection}

Company Information:
- Product: {product_name}
- Description: {product_description}
- Business Insights: {business_insights}

Sender Information:
- Name: {sender_name}
- Role: {sender_role}
- Skills: {sender_skills}
- Experience: {sender_experience_summary}

Additional Context: {notes}"""

    def _get_product_interest_system_prompt(self) -> str:
        """Get system prompt for product interest email generation."""
        return """You are an expert at writing product interest emails for job seekers.

Your task is to write a professional email that:
1. Expresses genuine interest in the company's product
2. Mentions discovering them through ProductHunt
3. Shows understanding of their market and challenges
4. Highlights relevant skills that could help their mission
5. Requests a conversation about potential collaboration

Guidelines:
- Keep the email concise (150-250 words)
- Lead with product interest and insights
- Show market understanding
- Connect sender's skills to company needs
- Professional and enthusiastic tone
- Clear call-to-action

Format your response as:
Subject: [Email subject line]

[Email body]"""

    def _get_product_interest_user_template(self) -> str:
        """Get user template for product interest email generation."""
        return """Write a product interest email with the following information:

Recipient: {name}
Role: {role}
Company: {company}

Product Information:
- Name: {product_name}
- Description: {product_description}
- Features: {product_features}
- Target Market: {target_market}
- Market Analysis: {market_analysis}

Sender Information:
- Name: {sender_name}
- Skills: {sender_skills}
- Relevant Experience: {sender_relevant_experience}
- Industry Match: {sender_industry_match}

Specific Interest: {specific_interest}
Additional Context: {notes}"""

    def _get_networking_system_prompt(self) -> str:
        """Get system prompt for networking email generation."""
        return """You are an expert at writing networking emails for job seekers.

Your task is to write a professional networking email that:
1. Focuses on building a professional relationship
2. Mentions discovering the company through ProductHunt
3. Shows interest in their work and industry insights
4. Offers value or mutual benefit
5. Requests a brief networking conversation

Guidelines:
- Keep the email concise (150-250 words)
- Focus on relationship building, not immediate job seeking
- Show genuine interest in their work
- Offer something of value (insights, connections, etc.)
- Professional and respectful tone
- Soft call-to-action for networking

Format your response as:
Subject: [Email subject line]

[Email body]"""

    def _get_networking_user_template(self) -> str:
        """Get user template for networking email generation."""
        return """Write a networking email with the following information:

Recipient: {name}
Role: {role}
Company: {company}

Company Information:
- Product: {product_name}
- Description: {product_description}
- Market Position: {market_position}

Sender Information:
- Name: {sender_name}
- Role: {sender_role}
- Skills: {sender_skills}
- Location: {sender_location}

Networking Value: {sender_value_proposition}
Additional Context: {notes}"""