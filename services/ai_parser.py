"""
AI-powered data parsing service using Azure OpenAI for structuring scraped data.
"""
import json
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from models.data_models import LinkedInProfile, TeamMember, ValidationError
from services.ai_provider_manager import get_provider_manager, configure_provider_manager
from services.openai_client_manager import CompletionRequest, CompletionResponse
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.validation_framework import ValidationFramework, ValidationResult


class ParseType(Enum):
    """Types of data parsing supported by the AI Parser."""
    LINKEDIN_PROFILE = "linkedin_profile"
    PRODUCT_INFO = "product_info"
    TEAM_DATA = "team_data"
    COMPANY_DATA = "company_data"
    BUSINESS_METRICS = "business_metrics"


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
class ParseResult:
    """Result of AI parsing operation."""
    success: bool
    data: Optional[Union[LinkedInProfile, ProductInfo, List[TeamMember], BusinessMetrics]]
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    raw_response: Optional[str] = None


class AIParser:
    """Service for parsing and structuring scraped data using Azure OpenAI."""
    
    def __init__(self, config: Optional[Config] = None, client_id: str = "ai_parser"):
        """
        Initialize the AI Parser.
        
        Args:
            config: Configuration object with AI provider settings (deprecated, use ConfigurationService)
            client_id: Deprecated parameter for backward compatibility (ignored)
        """
        self.logger = logging.getLogger(__name__)
        
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            self.logger.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            actual_config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            actual_config = config_service.get_config()
        
        # Configure AI provider manager instead of OpenAI client manager
        try:
            configure_provider_manager(actual_config)
            self.provider_manager = get_provider_manager()
            active_provider = self.provider_manager.get_active_provider_name()
            self.logger.info(f"Initialized AI Parser with provider: {active_provider}")
        except Exception as e:
            self.logger.error(f"Failed to configure AI provider: {str(e)}")
            raise
    
    def parse_linkedin_profile(self, raw_html: str, fallback_data: Optional[Dict] = None) -> ParseResult:
        """
        Parse LinkedIn profile HTML into structured LinkedInProfile object.
        
        Args:
            raw_html: Raw HTML content from LinkedIn profile page
            fallback_data: Optional fallback data if parsing fails
            
        Returns:
            ParseResult with LinkedInProfile data or error information
        """
        try:
            self.logger.info("Parsing LinkedIn profile data using AI")
            
            system_prompt = self._get_linkedin_parsing_prompt()
            user_prompt = f"""
            Parse the following LinkedIn profile HTML and extract structured information:
            
            HTML Content:
            {raw_html[:6000]}  # Reduced from 12000 to 6000 for faster processing
            
            Return ONLY the JSON object, no additional text.
            """
            
            # Create completion request with optimized settings
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,  # Reduced from 0.1 for faster processing
                max_tokens=1500   # Reduced from 2500 for faster processing
            )
            
            # Make completion request using provider manager
            response = self.provider_manager.make_completion(request)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            
            # Extract JSON from response (handle cases where AI adds extra text)
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Validate required fields before creating LinkedInProfile object
            name = parsed_data.get('name', '').strip()
            current_role = parsed_data.get('current_role', '').strip()
            
            # If critical fields are empty, try fallback data or raise error
            if not name or not current_role:
                if fallback_data:
                    name = fallback_data.get('name', name).strip()
                    current_role = fallback_data.get('current_role', current_role).strip()
                
                # If still empty, provide meaningful defaults
                if not name:
                    name = "Unknown Profile"
                if not current_role:
                    current_role = "Unknown Role"
            
            # Create LinkedInProfile object
            linkedin_profile = LinkedInProfile(
                name=name,
                current_role=current_role,
                experience=parsed_data.get('experience', []),
                skills=parsed_data.get('skills', []),
                summary=parsed_data.get('summary', '')
            )
            
            # Calculate confidence score based on data completeness
            confidence_score = self._calculate_confidence_score(parsed_data, ParseType.LINKEDIN_PROFILE)
            
            self.logger.info(f"Successfully parsed LinkedIn profile with confidence: {confidence_score:.2f}")
            
            return ParseResult(
                success=True,
                data=linkedin_profile,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON from AI response: {str(e)}")
            return self._handle_parsing_fallback(fallback_data, ParseType.LINKEDIN_PROFILE, str(e))
        
        except Exception as e:
            self.logger.error(f"Failed to parse LinkedIn profile: {str(e)}")
            return self._handle_parsing_fallback(fallback_data, ParseType.LINKEDIN_PROFILE, str(e))
    
    def parse_product_info(self, raw_content: str, product_url: str = "") -> ParseResult:
        """
        Parse product information from raw content into structured ProductInfo object.
        
        Args:
            raw_content: Raw content from product page or ProductHunt
            product_url: Optional product URL for context
            
        Returns:
            ParseResult with ProductInfo data or error information
        """
        try:
            self.logger.info("Parsing product information using AI")
            
            system_prompt = self._get_product_parsing_prompt()
            user_prompt = f"""
            Parse the following product information and extract structured data:
            
            Product URL: {product_url}
            
            Content:
            {raw_content[:12000]}  # Increased limit for better data extraction
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=3000  # Increased for more complete product info
            )
            
            # Make completion request using provider manager
            response = self.provider_manager.make_completion(request)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
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
            
            confidence_score = self._calculate_confidence_score(parsed_data, ParseType.PRODUCT_INFO)
            
            self.logger.info(f"Successfully parsed product info with confidence: {confidence_score:.2f}")
            
            return ParseResult(
                success=True,
                data=product_info,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse product info: {str(e)}")
            return ParseResult(
                success=False,
                data=None,
                error_message=str(e)
            )
    
    def structure_team_data(self, raw_team_info: str, company_name: str = "") -> ParseResult:
        """
        Parse and structure team member information from raw content.
        
        Args:
            raw_team_info: Raw content containing team member information
            company_name: Company name for context
            
        Returns:
            ParseResult with List[TeamMember] data or error information
        """
        try:
            self.logger.info("Structuring team data using AI")
            
            system_prompt = self._get_team_parsing_prompt()
            user_prompt = f"""
            Parse the following team information and extract structured data:
            
            Company: {company_name}
            
            Team Information:
            {raw_team_info[:10000]}  # Increased limit for better team extraction
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2500  # Increased for more complete team data
            )
            
            # Make completion request using provider manager
            response = self.provider_manager.make_completion(request)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('[')
            json_end = response_content.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON array found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
            # Create TeamMember objects
            team_members = []
            for member_data in parsed_data:
                try:
                    # Pre-validate data using ValidationFramework
                    validation_result = self._validate_team_member_data(member_data, company_name)
                    if not validation_result.is_valid:
                        self.logger.warning(f"Skipping invalid team member data: {validation_result.message}")
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
            
            self.logger.info(f"Successfully structured {len(team_members)} team members with confidence: {confidence_score:.2f}")
            
            return ParseResult(
                success=True,
                data=team_members,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to structure team data: {str(e)}")
            return ParseResult(
                success=False,
                data=None,
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
    
    def extract_business_metrics(self, company_data: str, company_name: str = "") -> ParseResult:
        """
        Extract business metrics and insights from company data.
        
        Args:
            company_data: Raw content about the company
            company_name: Company name for context
            
        Returns:
            ParseResult with BusinessMetrics data or error information
        """
        try:
            self.logger.info("Extracting business metrics using AI")
            
            system_prompt = self._get_business_metrics_prompt()
            user_prompt = f"""
            Analyze the following company information and extract business metrics:
            
            Company: {company_name}
            
            Company Data:
            {company_data[:12000]}  # Increased limit for better business metrics extraction
            
            Return the data in the exact JSON format specified in the system prompt.
            """
            
            # Create completion request
            request = CompletionRequest(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=2500  # Increased for more complete business metrics
            )
            
            # Make completion request
            response = self.provider_manager.make_completion(request)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse the JSON response
            response_content = response.content
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No valid JSON found in AI response")
            
            json_content = response_content[json_start:json_end]
            parsed_data = json.loads(json_content)
            
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
            
            confidence_score = self._calculate_confidence_score(parsed_data, ParseType.BUSINESS_METRICS)
            
            self.logger.info(f"Successfully extracted business metrics with confidence: {confidence_score:.2f}")
            
            return ParseResult(
                success=True,
                data=business_metrics,
                confidence_score=confidence_score,
                raw_response=response.content
            )
            
        except Exception as e:
            self.logger.error(f"Failed to extract business metrics: {str(e)}")
            return ParseResult(
                success=False,
                data=None,
                error_message=str(e)
            )  
  
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

    def _calculate_confidence_score(self, parsed_data: Dict[str, Any], parse_type: ParseType) -> float:
        """Calculate confidence score based on data completeness and quality."""
        if not parsed_data:
            return 0.0
        
        if parse_type == ParseType.LINKEDIN_PROFILE:
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
        
        elif parse_type == ParseType.PRODUCT_INFO:
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
        
        elif parse_type == ParseType.BUSINESS_METRICS:
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

    def _handle_parsing_fallback(self, fallback_data: Optional[Dict], parse_type: ParseType, error_message: str) -> ParseResult:
        """Handle parsing failures with fallback data if available."""
        if fallback_data and parse_type == ParseType.LINKEDIN_PROFILE:
            try:
                # Validate and clean fallback data
                name = fallback_data.get('name', '').strip()
                current_role = fallback_data.get('current_role', '').strip()
                
                # Provide meaningful defaults if still empty
                if not name:
                    name = "Unknown Profile"
                if not current_role:
                    current_role = "Unknown Role"
                
                # Try to create LinkedInProfile from fallback data
                linkedin_profile = LinkedInProfile(
                    name=name,
                    current_role=current_role,
                    experience=fallback_data.get('experience', []),
                    skills=fallback_data.get('skills', []),
                    summary=fallback_data.get('summary', '')
                )
                
                self.logger.info("Using fallback data for LinkedIn profile")
                return ParseResult(
                    success=True,
                    data=linkedin_profile,
                    confidence_score=0.3,  # Lower confidence for fallback
                    error_message=f"AI parsing failed, used fallback: {error_message}"
                )
            except Exception as e:
                self.logger.error(f"Fallback data also invalid: {str(e)}")
        
        # If no fallback or fallback failed, create minimal valid profile for LinkedIn
        if parse_type == ParseType.LINKEDIN_PROFILE:
            try:
                minimal_profile = LinkedInProfile(
                    name="Profile Extraction Failed",
                    current_role="Role Not Available",
                    experience=[],
                    skills=[],
                    summary="Profile data could not be extracted"
                )
                
                self.logger.warning("Created minimal LinkedIn profile due to parsing failure")
                return ParseResult(
                    success=True,
                    data=minimal_profile,
                    confidence_score=0.1,  # Very low confidence
                    error_message=f"Created minimal profile: {error_message}"
                )
            except Exception as e:
                self.logger.error(f"Failed to create minimal profile: {str(e)}")
        
        return ParseResult(
            success=False,
            data=None,
            error_message=error_message
        )

    def parse_with_retry(self, parse_function, *args, max_retries: int = 2, **kwargs) -> ParseResult:
        """
        Execute parsing function with retry logic for handling transient failures.
        
        Args:
            parse_function: The parsing function to execute
            *args: Arguments for the parsing function
            max_retries: Maximum number of retry attempts
            **kwargs: Keyword arguments for the parsing function
            
        Returns:
            ParseResult from the parsing function
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = parse_function(*args, **kwargs)
                if result.success:
                    return result
                else:
                    last_error = result.error_message
                    if attempt < max_retries:
                        self.logger.warning(f"Parse attempt {attempt + 1} failed: {last_error}. Retrying...")
                        continue
                    else:
                        return result
                        
            except Exception as e:
                error_str = str(e).lower()
                last_error = str(e)
                
                # Check if it's a rate limit error and apply exponential backoff
                if "rate limit" in error_str:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                        self.logger.warning(f"Rate limit hit on attempt {attempt + 1}. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        break
                else:
                    # For other errors, retry with shorter delay
                    if attempt < max_retries:
                        self.logger.warning(f"Parse attempt {attempt + 1} failed: {last_error}. Retrying...")
                        continue
                    else:
                        break
        
        return ParseResult(
            success=False,
            data=None,
            error_message=f"All parsing attempts failed. Last error: {last_error}"
        )

    def get_parsing_stats(self) -> Dict[str, Any]:
        """
        Get statistics about parsing operations (placeholder for future implementation).
        
        Returns:
            Dictionary with parsing statistics
        """
        # This could be extended to track parsing success rates, confidence scores, etc.
        return {
            "total_parses": 0,
            "successful_parses": 0,
            "average_confidence": 0.0,
            "parse_types": {
                "linkedin_profile": 0,
                "product_info": 0,
                "team_data": 0,
                "business_metrics": 0
            }
        }