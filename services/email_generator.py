"""
Email generation service using LLM for personalized outreach emails.
"""

import json
import re
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any

import yaml

from models.data_models import Prospect, EmailContent, LinkedInProfile, SenderProfile, EmailTemplate
from services.ai_provider_manager import get_provider_manager, configure_provider_manager
from services.openai_client_manager import CompletionRequest
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.validation_framework import ValidationResult





@dataclass
class ValidationResult:
    """Result of email content validation."""
    is_valid: bool
    issues: List[str]
    suggestions: List[str]
    spam_score: float


class EmailGenerator:
    """Service for generating personalized outreach emails using LLM."""
    
    def __init__(self, config: Optional[Config] = None, api_key: Optional[str] = None, interactive_mode: bool = False, client_id: str = "email_generator"):
        """
        Initialize the email generator.
        
        Args:
            config: Configuration object with AI provider settings (deprecated, use ConfigurationService)
            api_key: API key (deprecated, use config instead). If None, will try to get from environment.
            interactive_mode: Whether to enable interactive user review and editing.
            client_id: Deprecated parameter for backward compatibility (ignored)
        """
        self.logger = logging.getLogger(__name__)
        self.interactive_mode = interactive_mode
        # Keep client_id for backward compatibility, but it's not used with provider manager
        self.client_id = client_id
        
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
            self.logger.info(f"Initialized Email Generator with provider: {active_provider}")
        except Exception as e:
            self.logger.error(f"Failed to configure AI provider: {str(e)}")
            raise
        
        # Email templates
        self.templates = {
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
    
    def generate_outreach_email(
        self, 
        prospect: Prospect, 
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        linkedin_profile: Optional[LinkedInProfile] = None,
        product_analysis = None,
        additional_context: Optional[Dict[str, Any]] = None,
        ai_structured_data: Optional[Dict[str, str]] = None,
        sender_profile: Optional[SenderProfile] = None
    ) -> EmailContent:
        """
        Generate a personalized outreach email for a prospect.
        
        Args:
            prospect: The prospect to generate email for
            template_type: Type of email template to use
            linkedin_profile: Optional LinkedIn profile data for personalization
            product_analysis: Optional product analysis data
            additional_context: Additional context for personalization
            ai_structured_data: AI-structured data from Notion for enhanced personalization
            
        Returns:
            EmailContent object with generated email
        """
        """
        Generate a personalized outreach email for a prospect.
        
        Args:
            prospect: The prospect to generate email for
            template_type: Type of email template to use
            linkedin_profile: Optional LinkedIn profile data for personalization
            additional_context: Additional context for personalization
            
        Returns:
            EmailContent object with generated email
        """
        try:
            self.logger.info(f"Generating {template_type.value} email for {prospect.name}")
            
            # Get template configuration
            template_config = self.templates[template_type]
            
            # Prepare personalization data
            personalization_data = self._prepare_personalization_data(
                prospect, linkedin_profile, product_analysis, additional_context, ai_structured_data, sender_profile
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
            response = self.provider_manager.make_completion(request)
            
            if not response.success:
                raise Exception(response.error_message)
            
            # Parse response
            generated_content = response.content
            subject, body = self._parse_generated_content(generated_content)
            
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
            
            # Allow user review and editing if in interactive mode
            if self.interactive_mode:
                email_content = self.review_and_edit_email(email_content)
            
            self.logger.info(f"Successfully generated email for {prospect.name}")
            return email_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate email for {prospect.name}: {str(e)}")
            raise
    
    def generate_enhanced_outreach_email(
        self,
        prospect_id: str,
        notion_manager,
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        additional_context: Optional[Dict[str, Any]] = None,
        sender_profile: Optional[SenderProfile] = None
    ) -> EmailContent:
        """
        Generate a personalized outreach email using AI-structured data from Notion.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            notion_manager: NotionDataManager instance to retrieve AI-structured data
            template_type: Type of email template to use
            additional_context: Additional context for personalization
            
        Returns:
            EmailContent object with generated email
        """
        try:
            self.logger.info(f"Generating enhanced email for prospect {prospect_id}")
            
            # Get comprehensive prospect data from Notion
            prospect_data = notion_manager.get_prospect_data_for_email(prospect_id)
            
            # Create Prospect object from Notion data
            prospect = Prospect(
                id=prospect_id,
                name=prospect_data.get('name', ''),
                role=prospect_data.get('role', ''),
                company=prospect_data.get('company', ''),
                linkedin_url=prospect_data.get('linkedin_url'),
                email=prospect_data.get('email'),
                source_url=prospect_data.get('source_url', ''),
                notes=prospect_data.get('notes', '')
            )
            
            # Generate email using AI-structured data
            email_content = self.generate_outreach_email(
                prospect=prospect,
                template_type=template_type,
                ai_structured_data=prospect_data,
                additional_context=additional_context,
                sender_profile=sender_profile
            )
            
            self.logger.info(f"Successfully generated enhanced email for {prospect.name}")
            return email_content
            
        except Exception as e:
            error_msg = f"Failed to generate enhanced email for prospect {prospect_id}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg) from e
    
    def generate_and_send_email(
        self,
        prospect_id: str,
        notion_manager,
        email_sender,
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        additional_context: Optional[Dict[str, Any]] = None,
        send_immediately: bool = True,
        sender_profile: Optional[SenderProfile] = None
    ) -> Dict[str, Any]:
        """
        Generate and optionally send a personalized outreach email using AI-structured data.
        
        Args:
            prospect_id: The Notion page ID of the prospect
            notion_manager: NotionDataManager instance to retrieve AI-structured data
            email_sender: EmailSender instance for sending emails
            template_type: Type of email template to use
            additional_context: Additional context for personalization
            send_immediately: Whether to send the email immediately or just generate it
            
        Returns:
            Dictionary containing email content and send result (if sent)
        """
        try:
            self.logger.info(f"Generating and sending email for prospect {prospect_id}")
            
            # Generate enhanced email using AI-structured data
            email_content = self.generate_enhanced_outreach_email(
                prospect_id=prospect_id,
                notion_manager=notion_manager,
                template_type=template_type,
                additional_context=additional_context,
                sender_profile=sender_profile
            )
            
            result = {
                "email_content": email_content,
                "prospect_id": prospect_id,
                "generated_at": datetime.now().isoformat(),
                "sent": False,
                "send_result": None
            }
            
            # Send email if requested
            if send_immediately:
                # Get prospect data for recipient email
                prospect_data = notion_manager.get_prospect_data_for_email(prospect_id)
                recipient_email = prospect_data.get('email')
                
                if not recipient_email:
                    self.logger.warning(f"No email address found for prospect {prospect_id}")
                    result["error"] = "No email address available for prospect"
                    return result
                
                # Validate email address
                if not email_sender.validate_email_address(recipient_email):
                    self.logger.error(f"Invalid email address for prospect {prospect_id}: {recipient_email}")
                    result["error"] = f"Invalid email address: {recipient_email}"
                    return result
                
                # Convert email body to HTML format for better rendering
                html_body = self._convert_to_html(email_content.body)
                
                # Send the email
                send_result = email_sender.send_email(
                    recipient_email=recipient_email,
                    subject=email_content.subject,
                    html_body=html_body,
                    text_body=email_content.body,  # Plain text version
                    tags=["job-prospect", "outreach", template_type.value],
                    prospect_id=prospect_id
                )
                
                result["sent"] = send_result.status == "sent"
                result["send_result"] = {
                    "email_id": send_result.email_id,
                    "status": send_result.status,
                    "error_message": send_result.error_message,
                    "recipient_email": send_result.recipient_email
                }
                
                if send_result.status == "sent":
                    self.logger.info(f"Successfully generated and sent email to {recipient_email} (ID: {send_result.email_id})")
                else:
                    self.logger.error(f"Failed to send email to {recipient_email}: {send_result.error_message}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate and send email for prospect {prospect_id}: {str(e)}")
            raise
    
    def _convert_to_html(self, text_content: str) -> str:
        """
        Convert plain text email content to HTML format.
        
        Args:
            text_content: Plain text email content
            
        Returns:
            HTML formatted email content
        """
        # Basic HTML conversion
        html_content = text_content.replace('\n\n', '</p><p>')
        html_content = html_content.replace('\n', '<br>')
        
        # Wrap in HTML structure
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <p>{html_content}</p>
        </body>
        </html>
        """
        
        return html_content
    
    def generate_and_send_bulk_emails(
        self,
        prospect_ids: List[str],
        notion_manager,
        email_sender,
        template_type: EmailTemplate = EmailTemplate.COLD_OUTREACH,
        delay_between_emails: float = 2.0,
        additional_context: Optional[Dict[str, Any]] = None,
        sender_profile: Optional[SenderProfile] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate and send emails to multiple prospects with rate limiting.
        
        Args:
            prospect_ids: List of Notion page IDs for prospects
            notion_manager: NotionDataManager instance
            email_sender: EmailSender instance
            template_type: Type of email template to use
            delay_between_emails: Delay in seconds between sending emails
            additional_context: Additional context for personalization
            
        Returns:
            List of results for each prospect
        """
        results = []
        
        for i, prospect_id in enumerate(prospect_ids):
            try:
                self.logger.info(f"Processing prospect {i+1}/{len(prospect_ids)}: {prospect_id}")
                
                # Generate and send email
                result = self.generate_and_send_email(
                    prospect_id=prospect_id,
                    notion_manager=notion_manager,
                    email_sender=email_sender,
                    template_type=template_type,
                    additional_context=additional_context,
                    send_immediately=True,
                    sender_profile=sender_profile
                )
                
                results.append(result)
                
                # Add delay between emails (except for the last one)
                if i < len(prospect_ids) - 1:
                    self.logger.info(f"Waiting {delay_between_emails} seconds before next email...")
                    time.sleep(delay_between_emails)
                
            except Exception as e:
                self.logger.error(f"Failed to process prospect {prospect_id}: {str(e)}")
                results.append({
                    "prospect_id": prospect_id,
                    "error": str(e),
                    "sent": False,
                    "generated_at": datetime.now().isoformat()
                })
        
        # Log summary
        successful_sends = len([r for r in results if r.get("sent", False)])
        self.logger.info(f"Bulk email generation and sending completed: {successful_sends}/{len(prospect_ids)} emails sent successfully")
        
        return results
    
    def personalize_content(self, template: str, prospect_data: Dict[str, Any]) -> str:
        """
        Personalize email content using prospect data.
        
        Args:
            template: Email template string with placeholders
            prospect_data: Dictionary containing prospect information
            
        Returns:
            Personalized email content
        """
        try:
            return template.format(**prospect_data)
        except KeyError as e:
            self.logger.warning(f"Missing personalization data: {e}")
            return template
    
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
    
    def _prepare_personalization_data(
        self, 
        prospect: Prospect, 
        linkedin_profile: Optional[LinkedInProfile] = None,
        product_analysis = None,
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
            data['skills'] = ', '.join(linkedin_profile.skills)  # Top 5 skills
            data['experience'] = '; '.join(linkedin_profile.experience)  # Top 3 experiences
            data['summary'] = linkedin_profile.summary  # Increased for better context
        
        # Add product analysis data if available
        if product_analysis:
            # Handle both object and dictionary formats
            if hasattr(product_analysis, 'basic_info') and product_analysis.basic_info:
                # Object format
                data['product_name'] = product_analysis.basic_info.name or ''
                data['product_description'] = product_analysis.basic_info.description or ''
                data['target_market'] = product_analysis.basic_info.target_market or ''
            elif isinstance(product_analysis, dict):
                # Dictionary format (from Notion)
                data['product_name'] = product_analysis.get('company', '')
                data['product_description'] = product_analysis.get('product_summary', '') if product_analysis.get('product_summary') else ''
                data['target_market'] = product_analysis.get('business_insights', '') if product_analysis.get('business_insights') else ''
                
            if hasattr(product_analysis, 'features') and product_analysis.features:
                # Get top 3 features for personalization
                top_features = [f.name for f in product_analysis.features[:3]]
                data['product_features'] = ', '.join(top_features)
            elif isinstance(product_analysis, dict) and product_analysis.get('product_features'):
                data['product_features'] = product_analysis.get('product_features', '')
                
            if hasattr(product_analysis, 'pricing') and product_analysis.pricing:
                data['pricing_model'] = product_analysis.pricing.model or ''
            elif isinstance(product_analysis, dict):
                data['pricing_model'] = product_analysis.get('pricing_model', '')
                
            # Handle market analysis for both object and dictionary formats
            market_analysis = None
            if hasattr(product_analysis, 'market_analysis') and product_analysis.market_analysis:
                market_analysis = product_analysis.market_analysis
            elif isinstance(product_analysis, dict) and product_analysis.get('market_analysis'):
                market_analysis = product_analysis.get('market_analysis')
                
            if market_analysis:
                if hasattr(market_analysis, 'competitors'):
                    # Object format
                    data['competitors'] = ', '.join(market_analysis.competitors[:3])  # Top 3 competitors
                    data['market_position'] = market_analysis.market_position[:600] or ''  # Increased for full analysis
                    
                    # Create business insights summary
                    insights = []
                    if market_analysis.growth_potential:
                        insights.append(f"Growth potential: {market_analysis.growth_potential}")
                    if market_analysis.competitive_advantages:
                        advantages = ', '.join(market_analysis.competitive_advantages[:2])
                        insights.append(f"Key advantages: {advantages}")
                    data['business_insights'] = '; '.join(insights)
                elif isinstance(market_analysis, str):
                    # String format (from Notion)
                    data['market_analysis'] = market_analysis[:800]
                    data['business_insights'] = market_analysis[:400]  # Use first part as insights
            
            # Add funding and team context
            if hasattr(product_analysis, 'funding_info') and product_analysis.funding_info:
                funding_status = product_analysis.funding_info.get('status', '')
                if funding_status:
                    data['business_insights'] += f"; Funding: {funding_status}" if data['business_insights'] else f"Funding: {funding_status}"
            elif isinstance(product_analysis, dict) and product_analysis.get('funding_info'):
                funding_status = product_analysis.get('funding_info', '')
                if funding_status:
                    data['business_insights'] += f"; Funding: {funding_status}" if data['business_insights'] else f"Funding: {funding_status}"
                    
            if hasattr(product_analysis, 'team_size') and product_analysis.team_size:
                data['business_insights'] += f"; Team size: ~{product_analysis.team_size}" if data['business_insights'] else f"Team size: ~{product_analysis.team_size}"
            elif isinstance(product_analysis, dict) and product_analysis.get('team_size'):
                team_size = product_analysis.get('team_size', '')
                if team_size:
                    data['business_insights'] += f"; Team size: ~{team_size}" if data['business_insights'] else f"Team size: ~{team_size}"
        
        # Add AI-structured data from Notion (prioritize over raw data)
        if ai_structured_data:
            # Use AI-structured product summary if available (increased limits for better personalization)
            if ai_structured_data.get('product_summary'):
                data['product_summary'] = ai_structured_data['product_summary'] # Increased for full context
            
            # Use AI-structured business insights (increased limits)
            if ai_structured_data.get('business_insights'):
                data['business_insights'] = ai_structured_data['business_insights']  # Increased for full insights
            
            # Use AI-structured LinkedIn summary (increased limits)
            if ai_structured_data.get('linkedin_summary'):
                data['linkedin_summary'] = ai_structured_data['linkedin_summary'] # Increased for full profile
                # Override basic LinkedIn data with AI-structured version
                data['summary'] = ai_structured_data['linkedin_summary']  # Increased for better context
            
            # Use AI-generated personalization data (increased limits)
            if ai_structured_data.get('personalization_data'):
                data['personalization_points'] = ai_structured_data['personalization_data']  # Increased for full personalization
            elif ai_structured_data.get('personalization_points'):
                data['personalization_points'] = ai_structured_data['personalization_points']
            
            # Use additional AI-structured fields (increased limits for better context)
            for field in ['market_analysis', 'product_features', 'pricing_model', 'competitors']:
                if ai_structured_data.get(field):
                    data[field] = ai_structured_data[field][:800]  # Increased for full context
        
        # Add sender profile data (populate with empty values if no profile provided)
        if sender_profile:
            data['sender_name'] = sender_profile.name
            data['sender_role'] = sender_profile.current_role
            data['sender_experience_years'] = str(sender_profile.years_experience)
            data['sender_skills'] = ', '.join(sender_profile.key_skills[:5])  # Top 5 skills
            data['sender_experience_summary'] = sender_profile.experience_summary[:800]  # Increased for full context
            data['sender_education'] = '; '.join(sender_profile.education[:3])  # Top 3 education entries
            data['sender_certifications'] = ', '.join(sender_profile.certifications[:3])  # Top 3 certifications
            data['sender_value_proposition'] = sender_profile.value_proposition[:600]  # Increased for full value prop
            data['sender_achievements'] = '; '.join(sender_profile.notable_achievements[:3])  # Top 3 achievements
            data['sender_portfolio'] = ', '.join(sender_profile.portfolio_links[:2])  # Top 2 portfolio links
            data['sender_location'] = sender_profile.location
            data['sender_availability'] = sender_profile.availability
            data['sender_remote_preference'] = sender_profile.remote_preference
            
            # Calculate sender-specific matches for personalization
            data['sender_relevant_experience'] = self._get_relevant_sender_experience(sender_profile, prospect)
            data['sender_industry_match'] = self._get_sender_industry_match(sender_profile, prospect)
            data['sender_skill_match'] = self._get_sender_skill_match(sender_profile, prospect)
            
            # Add dynamic sender highlights and contextual sections
            product_context = {
                'business_insights': data.get('business_insights', ''),
                'product_features': data.get('product_features', ''),
                'market_analysis': data.get('market_analysis', '')
            }
            
            dynamic_highlights = self.get_dynamic_sender_highlights(sender_profile, prospect, product_context)
            contextual_sections = self.create_contextual_email_sections(sender_profile, prospect, product_context)
            
            # Add dynamic highlights to data
            data.update({
                'sender_primary_intro': dynamic_highlights['primary_introduction'],
                'sender_key_achievement': dynamic_highlights['key_achievement'],
                'sender_value_connection': dynamic_highlights['value_connection'],
                'sender_availability_note': dynamic_highlights['availability_note']
            })
            
            # Add contextual sections to data
            data.update({
                'sender_intro_section': contextual_sections.get('sender_introduction', ''),
                'skill_connection_section': contextual_sections.get('skill_connection', ''),
                'achievement_section': contextual_sections.get('achievement_highlight', ''),
                'value_prop_section': contextual_sections.get('value_proposition', ''),
                'availability_section': contextual_sections.get('availability_mention', ''),
                'portfolio_section': contextual_sections.get('portfolio_reference', '')
            })
        else:
            # Populate empty sender fields when no profile is provided
            empty_sender_fields = {
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
                'sender_skill_match': '',
                'sender_primary_intro': '',
                'sender_key_achievement': '',
                'sender_value_connection': '',
                'sender_availability_note': '',
                'sender_intro_section': '',
                'skill_connection_section': '',
                'achievement_section': '',
                'value_prop_section': '',
                'availability_section': '',
                'portfolio_section': ''
            }
            data.update(empty_sender_fields)
        
        # Add additional context
        if additional_context:
            data.update(additional_context)
        
        # Ensure all values are strings
        return {k: str(v) for k, v in data.items()}
    
    def _parse_generated_content(self, content: str) -> tuple[str, str]:
        """Parse generated content to extract subject and body."""
        lines = content.strip().split('\n')
        
        # Look for subject line
        subject = ""
        body_start = 0
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if line_lower.startswith('subject:'):
                subject = line.split(':', 1)[1].strip()
                body_start = i + 1
                break
            elif line_lower.startswith('subject line:'):
                subject = line.split(':', 1)[1].strip()
                body_start = i + 1
                break
        
        # If no subject found, use first line as subject
        if not subject and lines:
            subject = lines[0].strip()
            body_start = 1
        
        # Extract body
        body_lines = lines[body_start:]
        body = '\n'.join(body_lines).strip()
        
        # Clean up
        subject = subject.strip('"\'')
        
        return subject, body
    
    def _calculate_personalization_score(self, content: str, data: Dict[str, str]) -> float:
        """Calculate personalization score based on how much prospect data is used."""
        if not content:
            return 0.0
        
        content_lower = content.lower()
        used_fields = 0
        total_fields = 0
        
        # Check which personalization fields are actually used
        for key, value in data.items():
            if value and len(str(value).strip()) > 0:
                total_fields += 1
                if str(value).lower() in content_lower:
                    used_fields += 1
        
        return used_fields / total_fields if total_fields > 0 else 0.0
    
    def review_and_edit_email(self, email_content: EmailContent) -> EmailContent:
        """
        Allow user to review and edit generated email content.
        
        Args:
            email_content: Generated email content to review
            
        Returns:
            EmailContent object with user modifications (if any)
        """
        print("\n" + "="*60)
        print("EMAIL REVIEW AND EDITING")
        print("="*60)
        print(f"Recipient: {email_content.recipient_name} ({email_content.company_name})")
        print(f"Template: {email_content.template_used}")
        print(f"Personalization Score: {email_content.personalization_score:.2f}")
        print("-"*60)
        
        # Display current email
        print("CURRENT EMAIL:")
        print(f"Subject: {email_content.subject}")
        print(f"\nBody:\n{email_content.body}")
        print("-"*60)
        
        # Validate current content
        validation_result = self.validate_email_content(email_content.body)
        if not validation_result.is_valid:
            print("⚠️  VALIDATION ISSUES FOUND:")
            for issue in validation_result.issues:
                print(f"  • {issue}")
            print("\nSUGGESTIONS:")
            for suggestion in validation_result.suggestions:
                print(f"  • {suggestion}")
            print(f"\nSpam Score: {validation_result.spam_score:.2f}")
            print("-"*60)
        else:
            print("✅ Email validation passed!")
            print("-"*60)
        
        # Get user input
        while True:
            print("\nOptions:")
            print("1. Accept email as is")
            print("2. Edit subject line")
            print("3. Edit email body")
            print("4. Regenerate email")
            print("5. Show validation details")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                print("Email accepted!")
                break
            elif choice == "2":
                new_subject = input(f"Current subject: {email_content.subject}\nNew subject: ").strip()
                if new_subject:
                    email_content.subject = new_subject
                    print("Subject updated!")
            elif choice == "3":
                print("Current body:")
                print(email_content.body)
                print("\nEnter new body (press Enter twice to finish):")
                body_lines = []
                while True:
                    line = input()
                    if line == "" and len(body_lines) > 0 and body_lines[-1] == "":
                        break
                    body_lines.append(line)
                
                if body_lines and body_lines[-1] == "":
                    body_lines.pop()  # Remove last empty line
                
                if body_lines:
                    email_content.body = "\n".join(body_lines)
                    print("Body updated!")
                    
                    # Re-validate after editing
                    validation_result = self.validate_email_content(email_content.body)
                    if not validation_result.is_valid:
                        print("\n⚠️  New validation issues found:")
                        for issue in validation_result.issues:
                            print(f"  • {issue}")
            elif choice == "4":
                print("Regenerating email...")
                return self.generate_outreach_email(
                    Prospect(
                        name=email_content.recipient_name,
                        role="",  # Will be filled from original prospect
                        company=email_content.company_name
                    ),
                    EmailTemplate(email_content.template_used)
                )
            elif choice == "5":
                validation_result = self.validate_email_content(email_content.body)
                print(f"\nValidation Status: {'✅ Valid' if validation_result.is_valid else '❌ Invalid'}")
                print(f"Spam Score: {validation_result.spam_score:.2f}")
                if validation_result.issues:
                    print("Issues:")
                    for issue in validation_result.issues:
                        print(f"  • {issue}")
                if validation_result.suggestions:
                    print("Suggestions:")
                    for suggestion in validation_result.suggestions:
                        print(f"  • {suggestion}")
            else:
                print("Invalid choice. Please enter 1-5.")
        
        return email_content
    
    def customize_email_guidelines(self, guidelines: Dict[str, Any]) -> None:
        """
        Customize email generation guidelines.
        
        Args:
            guidelines: Dictionary containing customization options
        """
        # Update spam word list
        if 'additional_spam_words' in guidelines:
            # This would be used in validate_email_content method
            pass
        
        # Update length limits
        if 'min_length' in guidelines or 'max_length' in guidelines:
            # This would be used in validate_email_content method
            pass
        
        # Update personalization requirements
        if 'required_mentions' in guidelines:
            # This would be used in validation
            pass
        
        self.logger.info("Email guidelines updated")
    
    def get_content_suggestions(self, email_content: EmailContent, prospect: Prospect) -> List[str]:
        """
        Get suggestions for improving email content.
        
        Args:
            email_content: Current email content
            prospect: Prospect information
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check personalization
        if prospect.name.lower() not in email_content.body.lower():
            suggestions.append("Consider mentioning the recipient's name in the email body")
        
        if prospect.company.lower() not in email_content.body.lower():
            suggestions.append("Consider mentioning the company name in the email body")
        
        # Check length
        word_count = len(email_content.body.split())
        if word_count > 150:
            suggestions.append("Consider shortening the email - aim for under 150 words")
        elif word_count < 50:
            suggestions.append("Consider adding more personalized content")
        
        # Check call to action (look for actual CTA phrases, not just words)
        cta_phrases = [
            'would you be open to', 'let\'s chat', 'let\'s discuss', 'let\'s meet',
            'would you like to', 'can we schedule', 'are you available',
            'would love to chat', 'would love to discuss', 'would love to connect',
            'happy to chat', 'happy to discuss', 'open to a conversation'
        ]
        body_lower = email_content.body.lower()
        has_cta = any(phrase in body_lower for phrase in cta_phrases)
        
        # Also check for question marks which often indicate CTAs
        if not has_cta and '?' in email_content.body:
            # Check if the question is likely a CTA
            question_cta_words = ['chat', 'discuss', 'meet', 'connect', 'talk', 'call', 'available', 'interested']
            has_cta = any(word in body_lower for word in question_cta_words if '?' in email_content.body)
        
        if not has_cta:
            suggestions.append("Consider adding a clear call-to-action")
        
        # Check ProductHunt mention
        if 'producthunt' not in email_content.body.lower() and 'product hunt' not in email_content.body.lower():
            suggestions.append("Make sure to mention how you discovered them through ProductHunt")
        
        return suggestions
    
    # Template system prompts and user templates
    def _get_cold_outreach_system_prompt(self) -> str:
        return """You are an expert at writing emotionally resonant, high-converting cold outreach emails for job seekers targeting early-stage startups and fast-moving companies.

CRITICAL: You will be provided with detailed Business Insights, Product Summary, and Personalization Data. You MUST use this specific information rather than leaving placeholders or generic statements. DO NOT write things like "[insert company's mission]" or "[briefly reference a feature]" - use the actual data provided.

Your emails must:
- Be brief (under 150 words) and deeply personal, not generic
- A short, raw **“tl;dr”** section at the top, showing obsessive motivation or alignment in plain words (1–2 lines)
- Open with a clear signal of alignment: emotional, motivational, or vision-based
- Use authentic language to show self-awareness, humility, and passion
- Mention how the sender discovered the company (e.g., via ProductHunt) and why it resonated with them
- Use neuroscience-backed persuasion: reciprocity (praise), relatability (vulnerability), and specificity (concrete skills/impact)
- Describe sender’s relevant experience with actual companies/products (ideally high-growth or lean teams)
- Frame skills in the context of what the recipient’s company is likely struggling with at their stage (e.g., scalability, speed, full-stack ownership, data infra)
- Avoid overused corporate jargon (e.g., "synergy", "proactive", "leverage")—use real language that feels written by a motivated, obsessed builder
- Reference the company's product, team, or mission with at least one specific and meaningful insight
- Include links to work, projects, or relevant proof (if applicable)
- End with a low-pressure CTA that signals availability and openness for a chat—not a demand

Structure:
1. Bold, honest, or emotionally resonant opener that signals alignment
2. One-sentence discovery mention (ProductHunt, etc.) + what hooked the sender
3. Sender intro: focused on relevant achievements in lean/high-growth contexts
4. Specific ways their background can solve this company’s challenges
5. Personal tone throughout—less “professional,” more “driven teammate”
6. Soft CTA with availability and preferred contact method
7. Write it as its ready to send, no extra content like dashes in the start or saying "sure here's an email"

Format as:
Subject: [Compelling subject line that blends emotion + relevance]

[Email body]
"""
    
    def _get_cold_outreach_user_template(self) -> str:
        return """Write a cold outreach email to:

RECIPIENT INFORMATION:
Name: {name}
Role: {role}
Company: {company}
LinkedIn Summary: {linkedin_summary}
Skills: {skills}
Experience: {experience}

COMPANY & PRODUCT CONTEXT:
Product Summary: {product_summary}
Business Insights: {business_insights}
Market Analysis: {market_analysis}
Product Features: {product_features}
Pricing Model: {pricing_model}
Competitors: {competitors}
Key Personalization Points: {personalization_points}

SENDER PROFILE:
Name: {sender_name}
Primary Introduction: {sender_primary_intro}
Core Skills: {sender_skills}
Key Achievement: {sender_key_achievement}
Value Connection: {sender_value_connection}
Availability: {sender_availability_note}
Portfolio: {sender_portfolio}

DYNAMIC SECTIONS (use these for natural integration):
Sender Introduction: {sender_intro_section}
Skill Connection: {skill_connection_section}
Achievement Highlight: {achievement_section}
Value Proposition: {value_prop_section}
Availability Mention: {availability_section}
Portfolio Reference: {portfolio_section}

RELEVANCE MATCHING:
Most Relevant Experience: {sender_relevant_experience}
Industry Alignment: {sender_industry_match}
Skill Relevance: {sender_skill_match}

CONTEXT: I discovered {company} through their ProductHunt launch and am interested in potential opportunities. 

CRITICAL INSTRUCTIONS: Use the specific Business Insights and Personalization Data provided below. DO NOT use placeholders like "[insert company mission]" or "[briefly reference a feature]". Use the actual data to make specific, meaningful references to their product, market position, and growth stage.

INSTRUCTIONS: Create a personalized outreach email that:
1. Opens with how I found them on ProductHunt and genuine interest in their product/mission (use specific details from Product Summary)
2. Introduces me with the most relevant aspects of my background for their specific needs
3. Connects my experience/skills to their company's challenges or growth stage (use Business Insights)
4. References specific product features or business insights to show genuine understanding
5. Presents my value proposition in context of what they're building
6. Includes a natural mention of my availability and location preferences
7. Ends with a soft call-to-action for a brief conversation

Make it feel personal, genuine, and demonstrate that I've done my research on both their company and how I could contribute. Leave nothing to do for me, write a complete email."""
    
    def _get_referral_system_prompt(self) -> str:
        return """You are writing a follow-up email after getting a referral or warm introduction. 

The email should:
- Reference the referral/introduction
- Be brief and professional (under 150 words)
- Show genuine interest in the company using AI-structured insights
- Mention ProductHunt discovery
- Include sender's relevant background and connect to their specific business context
- Use comprehensive product and business insights along with sender profile for personalization
- Highlight relevant sender achievements and value proposition that match the recipient's context
- Include sender's availability and preferred contact method when appropriate
- Have a clear next step

Format as:
Subject: [email subject]

[email body]"""
    
    def _get_referral_user_template(self) -> str:
        return """Write a referral follow-up email to:
Name: {name}
Role: {role}
Company: {company}

Recipient Context:
LinkedIn Profile Summary: {linkedin_summary}
Skills: {skills}
Experience: {experience}

Product Context:
Product Summary: {product_summary}
Business Insights: {business_insights}
Market Analysis: {market_analysis}
Product Features: {product_features}
Pricing Model: {pricing_model}
Competitors: {competitors}

Personalization Points: {personalization_points}

Sender Context:
Sender Name: {sender_name}
Sender Role: {sender_role}
Sender Experience: {sender_experience_years} years
Sender Skills: {sender_skills}
Sender Experience Summary: {sender_experience_summary}
Sender Value Proposition: {sender_value_proposition}
Sender Achievements: {sender_achievements}
Sender Availability: {sender_availability}
Relevant Sender Experience: {sender_relevant_experience}
Industry Match: {sender_industry_match}
Skill Match: {sender_skill_match}

Referral context: {notes}
Mutual connection: {mutual_connection}
Specific interest: {specific_interest}

I was referred to them and discovered their company through ProductHunt. Use the comprehensive product and business context along with my sender profile to create a highly personalized follow-up email that showcases how my background aligns with their needs."""
    
    def _get_product_interest_system_prompt(self) -> str:
        return """You are writing an email expressing genuine interest in the company's product/service from someone with relevant experience.

The email should:
- Open with specific interest in their ProductHunt launch and what caught your attention
- Demonstrate deep understanding of their product using comprehensive product context and AI-structured data
- Connect sender's background and experience to how they could contribute to the product's success
- Be enthusiastic but professional, showing genuine excitement about their mission
- Reference specific product features and how sender's skills could enhance them
- Highlight relevant sender achievements that directly relate to their product challenges
- Show understanding of their market position and competitive landscape
- Position sender as someone who could help them achieve their goals
- Include sender's availability and interest in contributing
- Suggest a conversation about potential collaboration or opportunities
- Keep under 150 words

Email Structure:
1. Enthusiastic opening about their ProductHunt launch and specific product aspects
2. Brief introduction highlighting most relevant sender experience for their product
3. Specific connections between sender's skills/achievements and their product needs
4. Value proposition focused on how sender could help their product succeed
5. Call-to-action expressing interest in learning more and discussing opportunities

Format as:
Subject: [email subject]

[email body]"""
    
    def _get_product_interest_user_template(self) -> str:
        return """Write a product interest email to:
Name: {name}
Role: {role}
Company: {company}

Recipient Context:
LinkedIn Profile Summary: {linkedin_summary}
Skills: {skills}
Experience: {experience}

Product Context:
Product Summary: {product_summary}
Business Insights: {business_insights}
Market Analysis: {market_analysis}
Product Features: {product_features}
Pricing Model: {pricing_model}
Competitors: {competitors}

Personalization Points: {personalization_points}

Sender Context:
Sender Name: {sender_name}
Sender Role: {sender_role}
Sender Experience: {sender_experience_years} years
Sender Skills: {sender_skills}
Sender Experience Summary: {sender_experience_summary}
Sender Value Proposition: {sender_value_proposition}
Sender Achievements: {sender_achievements}
Sender Portfolio: {sender_portfolio}
Sender Availability: {sender_availability}
Relevant Sender Experience: {sender_relevant_experience}
Industry Match: {sender_industry_match}
Skill Match: {sender_skill_match}

Additional Notes: {notes}

I saw their product launch on ProductHunt and am genuinely interested in what they're building. Use the comprehensive product analysis and business insights along with my sender profile to demonstrate deep understanding of their product and market position while showcasing how my background could contribute to their success."""
    
    def _get_networking_system_prompt(self) -> str:
        return """You are writing a networking email to build meaningful professional relationships.

The email should:
- Focus on mutual benefit and shared interests
- Show genuine interest in their work and industry using detailed insights
- Mention ProductHunt discovery as the connection point
- Introduce sender with background that creates natural common ground
- Highlight complementary skills and experience that could benefit both parties
- Reference specific aspects of their product or business that resonate with sender's experience
- Suggest knowledge sharing or collaboration opportunities
- Be authentic about networking intent while showing genuine value
- Position the relationship as mutually beneficial
- Include sender's background in a way that invites reciprocal sharing
- Suggest a brief, low-pressure conversation
- Keep under 150 words

Email Structure:
1. Warm opening mentioning ProductHunt discovery and what impressed you
2. Brief introduction with background that creates natural connection points
3. Specific shared interests or complementary experience
4. Suggestion of mutual value exchange or learning opportunities
5. Casual invitation for a brief conversation or coffee chat

Format as:
Subject: [email subject]

[email body]"""
    
    def _get_networking_user_template(self) -> str:
        return """Write a networking email to:
Name: {name}
Role: {role}
Company: {company}

Recipient Context:
LinkedIn Profile Summary: {linkedin_summary}
Skills: {skills}
Experience: {experience}

Product Context:
Product Summary: {product_summary}
Business Insights: {business_insights}
Market Analysis: {market_analysis}
Product Features: {product_features}
Pricing Model: {pricing_model}
Competitors: {competitors}

Personalization Points: {personalization_points}

Sender Context:
Sender Name: {sender_name}
Sender Role: {sender_role}
Sender Experience: {sender_experience_years} years
Sender Skills: {sender_skills}
Sender Experience Summary: {sender_experience_summary}
Sender Value Proposition: {sender_value_proposition}
Sender Achievements: {sender_achievements}
Sender Portfolio: {sender_portfolio}
Sender Availability: {sender_availability}
Relevant Sender Experience: {sender_relevant_experience}
Industry Match: {sender_industry_match}
Skill Match: {sender_skill_match}

Background: {notes}

I discovered their company on ProductHunt and would like to connect professionally. Use the comprehensive product and business context along with my sender profile to create a meaningful networking connection that demonstrates mutual value and shared interests."""  
  
    def _get_relevant_sender_experience(self, sender_profile: SenderProfile, prospect: Prospect) -> str:
        """
        Get relevant sender experience based on prospect's role and company.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            
        Returns:
            String describing relevant experience for this specific prospect
        """
        relevant_experience = []
        
        # Check if sender's target roles match prospect's role or company needs
        prospect_role_lower = prospect.role.lower()
        role_match_score = 0
        best_role_match = ""
        
        for target_role in sender_profile.target_roles:
            target_role_words = target_role.lower().split()
            matches = sum(1 for word in target_role_words if word in prospect_role_lower)
            score = matches / len(target_role_words) if target_role_words else 0
            
            if score > role_match_score:
                role_match_score = score
                best_role_match = target_role
        
        if role_match_score > 0.3:  # At least 30% word match
            relevant_experience.append(f"Targeting {best_role_match} roles")
        
        # Score and rank achievements based on relevance to prospect's role and company
        scored_achievements = []
        for achievement in sender_profile.notable_achievements:
            score = self._score_achievement_relevance(achievement, prospect)
            if score > 0:
                scored_achievements.append((achievement, score))
        
        # Sort by relevance score and take top achievements
        scored_achievements.sort(key=lambda x: x[1], reverse=True)
        for achievement, score in scored_achievements[:2]:  # Top 2 most relevant
            relevant_experience.append(achievement[:120])  # Limit length for email
        
        # Add experience summary if it's substantial and relevant
        if sender_profile.experience_summary and len(sender_profile.experience_summary.strip()) > 50:
            summary_relevance = self._score_text_relevance(sender_profile.experience_summary, prospect)
            if summary_relevance > 0.2:  # Minimum relevance threshold
                relevant_experience.append(sender_profile.experience_summary[:150])
        
        return '; '.join(relevant_experience[:3])  # Limit to top 3 most relevant items
    
    def _get_sender_industry_match(self, sender_profile: SenderProfile, prospect: Prospect) -> str:
        """
        Determine if sender's industry interests match the prospect's company.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            
        Returns:
            String describing industry alignment
        """
        if not sender_profile.industries_of_interest:
            return ""
        
        # Enhanced industry matching with scoring
        company_lower = prospect.company.lower()
        role_lower = prospect.role.lower()
        
        # Industry keyword mappings for better matching
        industry_keywords = {
            'saas': ['software', 'platform', 'service', 'cloud', 'api'],
            'fintech': ['financial', 'finance', 'payment', 'banking', 'crypto', 'blockchain'],
            'healthtech': ['health', 'medical', 'healthcare', 'wellness', 'pharma', 'biotech'],
            'edtech': ['education', 'learning', 'teaching', 'academic', 'training', 'course'],
            'ecommerce': ['commerce', 'retail', 'shopping', 'marketplace', 'store'],
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'ai', 'data science'],
            'cybersecurity': ['security', 'cyber', 'privacy', 'protection', 'compliance'],
            'gaming': ['game', 'gaming', 'entertainment', 'mobile game'],
            'social': ['social', 'community', 'networking', 'communication'],
            'productivity': ['productivity', 'workflow', 'automation', 'efficiency']
        }
        
        scored_industries = []
        for industry in sender_profile.industries_of_interest:
            industry_lower = industry.lower()
            score = 0
            
            # Direct keyword match
            industry_words = industry_lower.split()
            for word in industry_words:
                if word in company_lower or word in role_lower:
                    score += 2
            
            # Extended keyword match
            if industry_lower in industry_keywords:
                for keyword in industry_keywords[industry_lower]:
                    if keyword in company_lower or keyword in role_lower:
                        score += 1
            
            if score > 0:
                scored_industries.append((industry, score))
        
        # Sort by relevance score
        scored_industries.sort(key=lambda x: x[1], reverse=True)
        
        if scored_industries:
            top_industries = [industry for industry, score in scored_industries[:2]]
            return f"Interested in {', '.join(top_industries)}"
        
        return ""
    
    def _get_sender_skill_match(self, sender_profile: SenderProfile, prospect: Prospect) -> str:
        """
        Find skills that might be relevant to the prospect's role or company.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            
        Returns:
            String describing relevant skills
        """
        if not sender_profile.key_skills:
            return ""
        
        # Enhanced skill matching with scoring
        role_lower = prospect.role.lower()
        company_lower = prospect.company.lower()
        
        # Comprehensive skill-role mappings with weights
        role_skill_mapping = {
            'engineer': {
                'high': ['python', 'javascript', 'react', 'node.js', 'aws', 'docker', 'kubernetes', 'sql', 'git'],
                'medium': ['java', 'c++', 'golang', 'rust', 'mongodb', 'postgresql', 'redis', 'microservices'],
                'low': ['html', 'css', 'linux', 'bash', 'ci/cd', 'terraform', 'ansible']
            },
            'developer': {
                'high': ['python', 'javascript', 'react', 'node.js', 'aws', 'docker', 'kubernetes', 'sql', 'git'],
                'medium': ['java', 'c++', 'golang', 'rust', 'mongodb', 'postgresql', 'redis', 'microservices'],
                'low': ['html', 'css', 'linux', 'bash', 'ci/cd', 'terraform', 'ansible']
            },
            'designer': {
                'high': ['figma', 'sketch', 'adobe', 'ui', 'ux', 'design', 'prototyping'],
                'medium': ['photoshop', 'illustrator', 'user research', 'wireframing', 'design systems'],
                'low': ['html', 'css', 'javascript', 'animation', 'branding']
            },
            'product': {
                'high': ['product management', 'analytics', 'user research', 'agile', 'scrum', 'roadmapping'],
                'medium': ['sql', 'data analysis', 'a/b testing', 'user experience', 'market research'],
                'low': ['jira', 'confluence', 'mixpanel', 'amplitude', 'tableau']
            },
            'marketing': {
                'high': ['marketing', 'seo', 'content', 'social media', 'analytics', 'growth'],
                'medium': ['google ads', 'facebook ads', 'email marketing', 'conversion optimization'],
                'low': ['copywriting', 'brand management', 'pr', 'influencer marketing']
            },
            'sales': {
                'high': ['sales', 'crm', 'business development', 'lead generation', 'negotiation'],
                'medium': ['salesforce', 'hubspot', 'cold outreach', 'account management'],
                'low': ['presentation', 'communication', 'relationship building']
            },
            'data': {
                'high': ['python', 'sql', 'analytics', 'machine learning', 'data science', 'statistics'],
                'medium': ['r', 'tableau', 'power bi', 'spark', 'hadoop', 'tensorflow', 'pytorch'],
                'low': ['excel', 'visualization', 'etl', 'data warehousing']
            },
            'devops': {
                'high': ['aws', 'docker', 'kubernetes', 'ci/cd', 'terraform', 'ansible'],
                'medium': ['jenkins', 'gitlab', 'monitoring', 'logging', 'security', 'automation'],
                'low': ['linux', 'bash', 'networking', 'troubleshooting']
            },
            'security': {
                'high': ['security', 'cybersecurity', 'penetration testing', 'compliance', 'risk assessment'],
                'medium': ['vulnerability assessment', 'incident response', 'security architecture'],
                'low': ['networking', 'encryption', 'authentication', 'authorization']
            },
            'manager': {
                'high': ['leadership', 'team management', 'project management', 'strategic planning'],
                'medium': ['agile', 'scrum', 'budgeting', 'hiring', 'performance management'],
                'low': ['communication', 'mentoring', 'cross-functional collaboration']
            }
        }
        
        # Score skills based on relevance to prospect's role
        scored_skills = []
        for skill in sender_profile.key_skills:
            skill_lower = skill.lower()
            max_score = 0
            
            # Check against role mappings
            for role_keyword, skill_categories in role_skill_mapping.items():
                if role_keyword in role_lower:
                    for category, skills_list in skill_categories.items():
                        weight = {'high': 3, 'medium': 2, 'low': 1}[category]
                        for mapped_skill in skills_list:
                            if mapped_skill in skill_lower or skill_lower in mapped_skill:
                                max_score = max(max_score, weight)
            
            # Direct skill mention in role or company
            if skill_lower in role_lower or skill_lower in company_lower:
                max_score = max(max_score, 4)  # Highest priority for direct mentions
            
            if max_score > 0:
                scored_skills.append((skill, max_score))
        
        # Sort by relevance score
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        
        # If no specific matches found, include top general skills
        if not scored_skills:
            scored_skills = [(skill, 1) for skill in sender_profile.key_skills[:3]]
        
        # Return top relevant skills
        top_skills = [skill for skill, score in scored_skills[:4]]  # Top 4 most relevant
        return ', '.join(top_skills)
    
    def load_sender_profile(self, profile_path: str) -> SenderProfile:
        """
        Load sender profile from file path.
        
        Args:
            profile_path: Path to sender profile file
            
        Returns:
            SenderProfile object
        """
        try:
            from services.sender_profile_manager import SenderProfileManager
            profile_manager = SenderProfileManager()
            
            if profile_path.endswith('.md'):
                return profile_manager.load_profile_from_markdown(profile_path)
            elif profile_path.endswith('.json'):
                with open(profile_path, 'r') as f:
                    config_data = json.load(f)
                return profile_manager.load_profile_from_config(config_data)
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                with open(profile_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                return profile_manager.load_profile_from_config(config_data)
            else:
                raise ValueError(f"Unsupported profile file format: {profile_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to load sender profile from {profile_path}: {str(e)}")
            raise
    
    def create_sender_profile_interactively(self) -> SenderProfile:
        """
        Create sender profile through interactive setup.
        
        Returns:
            SenderProfile object created interactively
        """
        try:
            from services.sender_profile_manager import SenderProfileManager
            profile_manager = SenderProfileManager()
            return profile_manager.create_profile_interactively()
        except Exception as e:
            self.logger.error(f"Failed to create sender profile interactively: {str(e)}")
            raise
    
    def _score_achievement_relevance(self, achievement: str, prospect: Prospect) -> float:
        """
        Score how relevant an achievement is to a specific prospect.
        
        Args:
            achievement: Sender's achievement description
            prospect: Target prospect information
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        achievement_lower = achievement.lower()
        role_lower = prospect.role.lower()
        company_lower = prospect.company.lower()
        
        score = 0.0
        
        # Leadership keywords (valuable for senior roles)
        leadership_keywords = ['led', 'managed', 'directed', 'supervised', 'coordinated', 'headed']
        if any(keyword in achievement_lower for keyword in leadership_keywords):
            if any(senior_word in role_lower for senior_word in ['senior', 'lead', 'manager', 'director', 'head', 'vp', 'cto', 'ceo']):
                score += 0.3
            else:
                score += 0.1
        
        # Technical achievement keywords
        tech_keywords = ['built', 'developed', 'implemented', 'architected', 'designed', 'created', 'launched']
        if any(keyword in achievement_lower for keyword in tech_keywords):
            if any(tech_word in role_lower for tech_word in ['engineer', 'developer', 'architect', 'technical']):
                score += 0.3
            else:
                score += 0.1
        
        # Scale/impact keywords
        scale_keywords = ['scaled', 'grew', 'increased', 'improved', 'optimized', 'reduced']
        if any(keyword in achievement_lower for keyword in scale_keywords):
            score += 0.2
        
        # Quantified results (numbers indicate measurable impact)
        if re.search(r'\d+[%x]|\d+\s*(million|thousand|k|m)', achievement_lower):
            score += 0.2
        
        # Industry-specific relevance
        if 'startup' in achievement_lower and any(startup_word in company_lower for startup_word in ['startup', 'early', 'seed', 'series']):
            score += 0.2
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _score_text_relevance(self, text: str, prospect: Prospect) -> float:
        """
        Score how relevant a text (like experience summary) is to a prospect.
        
        Args:
            text: Text to score for relevance
            prospect: Target prospect information
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        text_lower = text.lower()
        role_lower = prospect.role.lower()
        company_lower = prospect.company.lower()
        
        score = 0.0
        
        # Role keyword matches
        role_keywords = role_lower.split()
        for keyword in role_keywords:
            if len(keyword) > 2 and keyword in text_lower:  # Skip short words
                score += 0.1
        
        # Company name or domain matches
        company_keywords = company_lower.split()
        for keyword in company_keywords:
            if len(keyword) > 2 and keyword in text_lower:
                score += 0.1
        
        # Industry relevance
        industry_indicators = {
            'saas': ['software', 'platform', 'service', 'cloud', 'api', 'subscription'],
            'fintech': ['financial', 'finance', 'payment', 'banking', 'crypto', 'blockchain', 'trading'],
            'healthtech': ['health', 'medical', 'healthcare', 'wellness', 'pharma', 'biotech', 'clinical'],
            'edtech': ['education', 'learning', 'teaching', 'academic', 'training', 'course', 'student'],
            'ecommerce': ['commerce', 'retail', 'shopping', 'marketplace', 'store', 'customer'],
            'ai': ['artificial intelligence', 'machine learning', 'ml', 'ai', 'data science', 'algorithm'],
            'security': ['security', 'cyber', 'privacy', 'protection', 'compliance', 'risk']
        }
        
        for industry, indicators in industry_indicators.items():
            if any(indicator in company_lower or indicator in role_lower for indicator in indicators):
                if any(indicator in text_lower for indicator in indicators):
                    score += 0.15
                    break
        
        return min(score, 1.0)  # Cap at 1.0
    
    def get_sender_portfolio_relevance(self, sender_profile: SenderProfile, prospect: Prospect) -> List[str]:
        """
        Get portfolio links that are most relevant to the prospect.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            
        Returns:
            List of most relevant portfolio links
        """
        if not sender_profile.portfolio_links:
            return []
        
        # For now, return all portfolio links (could be enhanced with relevance scoring)
        # In a more sophisticated implementation, we could:
        # - Parse portfolio content to match with prospect's industry/role
        # - Prioritize GitHub repos with relevant technologies
        # - Score personal websites based on content relevance
        
        return sender_profile.portfolio_links[:2]  # Limit to top 2 links
    
    def match_sender_achievements_to_company_needs(self, sender_profile: SenderProfile, prospect: Prospect, product_context: Dict[str, str] = None) -> List[str]:
        """
        Match sender achievements to specific company needs based on product context.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            product_context: Optional product analysis context
            
        Returns:
            List of most relevant achievements for this specific company
        """
        if not sender_profile.notable_achievements:
            return []
        
        # Score achievements based on multiple factors
        scored_achievements = []
        
        for achievement in sender_profile.notable_achievements:
            score = self._score_achievement_relevance(achievement, prospect)
            
            # Additional scoring based on product context
            if product_context:
                achievement_lower = achievement.lower()
                
                # Match with product features or business insights
                if product_context.get('product_features'):
                    features_lower = product_context['product_features'].lower()
                    if any(word in features_lower for word in achievement_lower.split() if len(word) > 3):
                        score += 0.1
                
                # Match with business insights (funding stage, growth, etc.)
                if product_context.get('business_insights'):
                    insights_lower = product_context['business_insights'].lower()
                    if 'startup' in insights_lower and 'startup' in achievement_lower:
                        score += 0.1
                    if 'scale' in insights_lower and any(scale_word in achievement_lower for scale_word in ['scaled', 'grew', 'growth']):
                        score += 0.1
            
            if score > 0:
                scored_achievements.append((achievement, score))
        
        # Sort by relevance and return top achievements
        scored_achievements.sort(key=lambda x: x[1], reverse=True)
        return [achievement for achievement, score in scored_achievements[:3]]  # Top 3 most relevant 
   
    def get_dynamic_sender_highlights(self, sender_profile: SenderProfile, prospect: Prospect, product_context: Dict[str, str] = None) -> Dict[str, str]:
        """
        Dynamically select the most relevant sender information to highlight for this specific prospect.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            product_context: Optional product analysis context
            
        Returns:
            Dictionary with dynamically selected sender highlights
        """
        highlights = {
            'primary_introduction': '',
            'relevant_skills': '',
            'key_achievement': '',
            'value_connection': '',
            'availability_note': ''
        }
        
        # Primary introduction based on role match
        role_lower = prospect.role.lower()
        if any(senior_word in role_lower for senior_word in ['senior', 'lead', 'manager', 'director', 'head', 'vp', 'cto', 'ceo']):
            # Emphasize leadership experience for senior roles
            if any(leadership_word in sender_profile.experience_summary.lower() for leadership_word in ['led', 'managed', 'directed']):
                highlights['primary_introduction'] = f"{sender_profile.current_role} with {sender_profile.years_experience} years of experience leading technical teams"
            else:
                highlights['primary_introduction'] = f"Senior {sender_profile.current_role} with {sender_profile.years_experience} years of experience"
        else:
            # Emphasize technical skills for individual contributor roles
            highlights['primary_introduction'] = f"{sender_profile.current_role} specializing in {', '.join(sender_profile.key_skills[:3])}"
        
        # Select most relevant skills
        relevant_skills = self._get_sender_skill_match(sender_profile, prospect)
        highlights['relevant_skills'] = relevant_skills if relevant_skills else ', '.join(sender_profile.key_skills[:3])
        
        # Select most relevant achievement
        relevant_achievements = self.match_sender_achievements_to_company_needs(sender_profile, prospect, product_context)
        if relevant_achievements:
            highlights['key_achievement'] = relevant_achievements[0][:100]  # Limit length
        elif sender_profile.notable_achievements:
            highlights['key_achievement'] = sender_profile.notable_achievements[0][:100]
        
        # Create value connection based on company context
        value_connections = []
        
        # Industry alignment
        industry_match = self._get_sender_industry_match(sender_profile, prospect)
        if industry_match:
            value_connections.append(f"passionate about {industry_match.lower()}")
        
        # Product context alignment
        if product_context:
            if product_context.get('business_insights'):
                insights_lower = product_context['business_insights'].lower()
                if 'startup' in insights_lower or 'early' in insights_lower:
                    if any(startup_word in sender_profile.experience_summary.lower() for startup_word in ['startup', 'early-stage', 'founding']):
                        value_connections.append("experienced with early-stage company challenges")
                if 'scale' in insights_lower or 'growth' in insights_lower:
                    if any(scale_word in sender_profile.experience_summary.lower() for scale_word in ['scaled', 'growth', 'expansion']):
                        value_connections.append("experienced with scaling technical systems")
        
        highlights['value_connection'] = '; '.join(value_connections[:2]) if value_connections else sender_profile.value_proposition[:100]
        
        # Availability note
        availability_parts = []
        if sender_profile.availability:
            availability_parts.append(sender_profile.availability)
        if sender_profile.remote_preference:
            availability_parts.append(f"open to {sender_profile.remote_preference} work")
        if sender_profile.location:
            availability_parts.append(f"based in {sender_profile.location}")
        
        highlights['availability_note'] = ', '.join(availability_parts[:2])
        
        return highlights
    
    def create_contextual_email_sections(self, sender_profile: SenderProfile, prospect: Prospect, product_context: Dict[str, str] = None) -> Dict[str, str]:
        """
        Create contextual email sections that can be dynamically inserted into templates.
        
        Args:
            sender_profile: Sender's professional profile
            prospect: Target prospect information
            product_context: Optional product analysis context
            
        Returns:
            Dictionary with pre-formatted email sections
        """
        highlights = self.get_dynamic_sender_highlights(sender_profile, prospect, product_context)
        
        sections = {
            'sender_introduction': f"I'm {highlights['primary_introduction']}",
            'skill_connection': f"My expertise in {highlights['relevant_skills']} aligns well with your work in {prospect.role.lower()}",
            'achievement_highlight': f"Recently, {highlights['key_achievement'].lower()}" if highlights['key_achievement'] else "",
            'value_proposition': f"I'm {highlights['value_connection']}",
            'availability_mention': f"I'm {highlights['availability_note']}" if highlights['availability_note'] else "",
            'portfolio_reference': f"You can see examples of my work at {sender_profile.portfolio_links[0]}" if sender_profile.portfolio_links else ""
        }
        
        # Clean up empty sections
        sections = {k: v for k, v in sections.items() if v.strip()}
        
        return sections