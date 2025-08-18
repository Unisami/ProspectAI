"""
Integration tests for sender-aware email generation.
"""
import pytest
from tests.test_utilities import TestUtilities
import os
import tempfile
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime

from models.data_models import SenderProfile, Prospect, EmailContent, CompanyData, LinkedInProfile
from services.email_generator import EmailGenerator, EmailTemplate
from services.sender_profile_manager import SenderProfileManager
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config


def create_mock_config(**overrides):
    """Create a properly configured mock config with all required attributes."""
    mock_config = MagicMock(spec=Config)
    
    # Set all required attributes with defaults
    mock_config.notion_token = "test_token"
    mock_config.hunter_api_key = "test_key"
    mock_config.openai_api_key = "test_openai_key"
    mock_config.use_azure_openai = False
    mock_config.azure_openai_api_key = "test_azure_key"
    mock_config.azure_openai_endpoint = "https://test-endpoint.openai.azure.com"
    mock_config.azure_openai_api_version = "2023-05-15"
    mock_config.azure_openai_deployment_name = "gpt-4"
    mock_config.enable_ai_parsing = True
    mock_config.enable_product_analysis = True
    mock_config.enable_enhanced_workflow = True
    mock_config.batch_processing_enabled = True
    mock_config.auto_send_emails = False
    mock_config.email_review_required = True
    mock_config.scraping_delay = 2.0
    mock_config.hunter_requests_per_minute = 10
    mock_config.max_products_per_run = 50
    mock_config.max_prospects_per_company = 10
    mock_config.notion_database_id = None
    mock_config.email_template_type = "cold_outreach"
    mock_config.personalization_level = "medium"
    mock_config.resend_api_key = "test_resend_key"
    mock_config.sender_email = "test@example.com"
    mock_config.sender_name = "Test Sender"
    mock_config.reply_to_email = None
    mock_config.resend_requests_per_minute = 100
    mock_config.ai_parsing_model = "gpt-4"
    mock_config.ai_parsing_max_retries = 3
    mock_config.ai_parsing_timeout = 30
    mock_config.product_analysis_model = "gpt-4"
    mock_config.product_analysis_max_retries = 3
    mock_config.enhanced_personalization = True
    mock_config.email_generation_model = "gpt-4"
    mock_config.max_email_length = 500
    
    # Sender profile defaults
    mock_config.enable_sender_profile = True
    mock_config.sender_profile_path = None
    mock_config.sender_profile_format = "markdown"
    mock_config.enable_interactive_profile_setup = True
    mock_config.require_sender_profile = False
    mock_config.sender_profile_completeness_threshold = 0.7
    
    # Apply overrides
    for key, value in overrides.items():
        setattr(mock_config, key, value)
    
    return mock_config


class TestSenderAwareEmailGeneration:
    """Integration tests for sender-aware email generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a test sender profile
        self.sender_profile = SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "JavaScript", "React", "AWS", "Docker"],
            experience_summary="Experienced full-stack developer with 5 years in web development",
            education=["BS Computer Science - MIT"],
            certifications=["AWS Certified Developer"],
            value_proposition="I build scalable web applications that drive business growth",
            target_roles=["Senior Developer", "Tech Lead"],
            industries_of_interest=["FinTech", "Healthcare"],
            notable_achievements=[
                "Led team of 5 developers to deliver major platform upgrade",
                "Reduced API response time by 40% through optimization",
                "Implemented CI/CD pipeline reducing deployment time by 60%"
            ],
            portfolio_links=["https://johndoe.dev", "https://github.com/johndoe"],
            preferred_contact_method="email",
            availability="Available with 2 weeks notice",
            location="San Francisco, CA",
            remote_preference="hybrid"
        )
        
        # Create a test prospect
        self.prospect = Prospect(
            id="123",
            name="Jane Smith",
            role="CTO",
            company="FinTech Startup",
            linkedin_url="https://linkedin.com/in/janesmith",
            email="jane@fintechstartup.com",
            contacted=False,
            notes="Found on ProductHunt",
            created_at=datetime.now()
        )
        
        # Create a test LinkedIn profile
        self.linkedin_profile = LinkedInProfile(
            name="Jane Smith",
            current_role="CTO at FinTech Startup",
            experience=["Former VP Engineering at PayTech", "Lead Developer at FinanceCorp"],
            skills=["Leadership", "Fintech", "System Architecture", "Python", "AWS"],
            summary="Experienced technology leader with focus on financial technology"
        )
        
        # Create product analysis data
        self.product_analysis = MagicMock()
        self.product_analysis.basic_info.name = "FinPay"
        self.product_analysis.basic_info.description = "Modern payment processing platform"
        self.product_analysis.basic_info.target_market = "Small to medium businesses"
        self.product_analysis.features = [
            MagicMock(name="API Integration"),
            MagicMock(name="Real-time Analytics"),
            MagicMock(name="Fraud Detection")
        ]
        self.product_analysis.pricing.model = "Subscription + Transaction Fee"
        self.product_analysis.market_analysis.competitors = ["Stripe", "Square", "PayPal"]
        self.product_analysis.market_analysis.market_position = "Emerging challenger in SMB market"
        self.product_analysis.market_analysis.growth_potential = "High growth potential in underserved markets"
        self.product_analysis.market_analysis.competitive_advantages = ["Lower fees", "Better API"]
        self.product_analysis.funding_info = {"status": "Series A"}
        self.product_analysis.team_size = 15
        
        # Create AI-structured data
        self.ai_structured_data = {
            "product_summary": "FinPay is a modern payment processing platform for SMBs with competitive pricing and developer-friendly API",
            "business_insights": "Series A startup with 15 team members, growing rapidly in the SMB market with focus on API-first approach",
            "linkedin_summary": "Jane Smith is an experienced CTO with background in fintech and payment systems",
            "personalization_points": "Technical background in payment systems, looking for experienced developers to scale platform"
        }
        
        # Create mock OpenAI client
        self.mock_openai_client = MagicMock()
        self.mock_openai_response = MagicMock()
        self.mock_openai_response.choices = [MagicMock()]
        self.mock_openai_response.choices[0].message = MagicMock()
        self.mock_openai_response.choices[0].message.content = """Subject: Impressed by FinPay on ProductHunt - Senior Engineer with Fintech Experience

Hi Jane,

I discovered FinPay through your ProductHunt launch and was impressed by your modern payment processing platform. Your focus on API-first development and fraud detection particularly caught my attention.

I'm a Senior Software Engineer with 5 years of experience building scalable web applications, including payment processing systems. I recently led a team that reduced API response times by 40% - something that could benefit FinPay as you scale.

My background in fintech and experience with AWS infrastructure aligns well with your technical needs as you grow post-Series A. I'd love to discuss how my skills in Python and React could help strengthen your development team.

I'm available with two weeks' notice and open to hybrid work in San Francisco. Would you be open to a brief conversation about your engineering needs?

Best regards,
John Doe
https://johndoe.dev"""
        self.mock_openai_client.chat.completions.create.return_value = self.mock_openai_response
    
    @patch('openai.OpenAI')
    def test_generate_email_with_sender_profile(self, mock_openai):
        """Test generating an email with sender profile integration."""
        # Set up mock OpenAI client
        mock_openai.return_value = self.mock_openai_client
        
        # Create email generator with mock OpenAI client
        email_generator = EmailGenerator()
        email_generator.client = self.mock_openai_client
        
        # Generate email with sender profile
        email_content = email_generator.generate_outreach_email(
            prospect=self.prospect,
            linkedin_profile=self.linkedin_profile,
            product_analysis=self.product_analysis,
            ai_structured_data=self.ai_structured_data,
            sender_profile=self.sender_profile,
            template_type="cold_outreach"
        )
        
        # Verify email content
        assert email_content is not None
        assert isinstance(email_content, EmailContent)
        assert "FinPay" in email_content.subject or "Fintech" in email_content.subject
        assert "ProductHunt" in email_content.body
        
        # Verify sender profile integration
        assert self.sender_profile.name in email_content.body
        assert "Senior Software Engineer" in email_content.body or "Senior Engineer" in email_content.body
        assert "5 years" in email_content.body
        assert "40%" in email_content.body  # From notable achievements
        assert "San Francisco" in email_content.body or "hybrid" in email_content.body
        assert "johndoe.dev" in email_content.body  # Portfolio link
        
        # Verify OpenAI was called with sender profile data
        call_args = self.mock_openai_client.chat.completions.create.call_args[1]
        messages = call_args['messages']
        user_message = [m for m in messages if m['role'] == 'user'][0]['content']
        
        # Check that sender profile fields are included in the prompt
        assert "SENDER PROFILE:" in user_message
        assert self.sender_profile.name in user_message
        assert "Senior Software Engineer" in user_message
        assert "Python" in user_message
        assert "JavaScript" in user_message
        assert "fintech" in user_message.lower()
    
    @patch('openai.OpenAI')
    def test_generate_email_without_sender_profile(self, mock_openai):
        """Test generating an email without sender profile."""
        # Set up mock OpenAI client with different response for no sender profile
        mock_openai.return_value = self.mock_openai_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = """Subject: Impressed by FinPay on ProductHunt

Hi Jane,

I discovered your company FinPay through ProductHunt and was impressed by your modern payment processing platform for small to medium businesses.

Your focus on API integration and real-time analytics seems to address a real need in the market, especially with your competitive positioning against larger players like Stripe and PayPal.

I'd love to learn more about your team and potential opportunities to contribute to your growth as you scale post-Series A funding.

Would you be open to a brief conversation about your current needs and challenges?

Best regards,
[Your Name]"""
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Create email generator with mock OpenAI client
        email_generator = EmailGenerator()
        email_generator.client = self.mock_openai_client
        
        # Generate email without sender profile
        email_content = email_generator.generate_outreach_email(
            prospect=self.prospect,
            linkedin_profile=self.linkedin_profile,
            product_analysis=self.product_analysis,
            ai_structured_data=self.ai_structured_data,
            sender_profile=None,  # No sender profile
            template_type="cold_outreach"
        )
        
        # Verify email content
        assert email_content is not None
        assert isinstance(email_content, EmailContent)
        assert "FinPay" in email_content.subject or "ProductHunt" in email_content.subject
        assert "ProductHunt" in email_content.body
        
        # Verify no sender-specific information
        assert "[Your Name]" in email_content.body or not any(
            name in email_content.body for name in ["John Doe", "Jane Doe", "John Smith"]
        )
        assert "years experience" not in email_content.body.lower()
        assert "San Francisco" not in email_content.body
        assert "johndoe.dev" not in email_content.body
        
        # Verify OpenAI was called without sender profile data
        call_args = self.mock_openai_client.chat.completions.create.call_args[1]
        messages = call_args['messages']
        user_message = [m for m in messages if m['role'] == 'user'][0]['content']
        
        # Check that sender profile sections are empty or minimal
        assert "SENDER PROFILE:" in user_message
        assert "Name:" in user_message and ":" in user_message.split("Name:")[1].split("\n")[0]
        assert "Primary Introduction:" in user_message
        assert "Core Skills:" in user_message
    
    @patch('openai.OpenAI')
    def test_generate_email_with_different_sender_profiles(self, mock_openai):
        """Test generating emails with different sender profiles to verify personalization differences."""
        # Set up mock OpenAI client
        mock_openai.return_value = self.mock_openai_client
        
        # Create email generator with mock OpenAI client
        email_generator = EmailGenerator()
        email_generator.client = self.mock_openai_client
        
        # Create a second sender profile with different background
        developer_profile = SenderProfile(
            name="Alice Johnson",
            current_role="Frontend Developer",
            years_experience=3,
            key_skills=["React", "JavaScript", "UI/UX", "CSS", "TypeScript"],
            experience_summary="Frontend developer with focus on user experience and responsive design",
            value_proposition="I create intuitive user interfaces that enhance user engagement",
            target_roles=["Senior Frontend Developer", "UI Lead"],
            notable_achievements=[
                "Redesigned dashboard increasing user engagement by 35%",
                "Implemented responsive design reducing bounce rate by 25%",
                "Created component library improving development velocity"
            ],
            portfolio_links=["https://alicejohnson.dev"],
            location="Remote",
            remote_preference="remote"
        )
        
        # Set up different responses for different profiles
        developer_response = MagicMock()
        developer_response.choices = [MagicMock()]
        developer_response.choices[0].message = MagicMock()
        developer_response.choices[0].message.content = """Subject: Frontend Developer impressed by FinPay's ProductHunt launch

Hi Jane,

I discovered FinPay on ProductHunt and was impressed by your modern payment platform. As a Frontend Developer with 3 years of experience in React and UI/UX, I'm particularly interested in your user interface and customer experience.

I recently redesigned a financial dashboard that increased user engagement by 35% and have experience creating intuitive interfaces for complex financial data. My background in responsive design could help make FinPay even more accessible to your SMB customers.

I'd love to discuss how my frontend expertise could contribute to enhancing FinPay's user experience as you scale after your Series A funding.

I'm available for remote work and would welcome a conversation about your frontend development needs.

Best regards,
Alice Johnson
https://alicejohnson.dev"""
        
        # First generate with original profile
        self.mock_openai_client.chat.completions.create.return_value = self.mock_openai_response
        original_email = email_generator.generate_outreach_email(
            prospect=self.prospect,
            linkedin_profile=self.linkedin_profile,
            product_analysis=self.product_analysis,
            ai_structured_data=self.ai_structured_data,
            sender_profile=self.sender_profile,
            template_type="cold_outreach"
        )
        
        # Then generate with developer profile
        self.mock_openai_client.chat.completions.create.return_value = developer_response
        developer_email = email_generator.generate_outreach_email(
            prospect=self.prospect,
            linkedin_profile=self.linkedin_profile,
            product_analysis=self.product_analysis,
            ai_structured_data=self.ai_structured_data,
            sender_profile=developer_profile,
            template_type="cold_outreach"
        )
        
        # Verify different personalization based on sender profile
        assert original_email.subject != developer_email.subject
        assert "John Doe" in original_email.body
        assert "Alice Johnson" in developer_email.body
        
        # Check for profile-specific content
        assert "Senior Software Engineer" in original_email.body or "Senior Engineer" in original_email.body
        assert "Frontend Developer" in developer_email.body
        
        assert "5 years" in original_email.body
        assert "3 years" in developer_email.body
        
        assert "40%" in original_email.body  # From original profile achievements
        assert "35%" in developer_email.body  # From developer profile achievements
        
        assert "San Francisco" in original_email.body or "hybrid" in original_email.body
        assert "Remote" in developer_email.body or "remote" in developer_email.body
        
        assert "johndoe.dev" in original_email.body
        assert "alicejohnson.dev" in developer_email.body
    
    @patch('openai.OpenAI')
    def test_generate_email_with_incomplete_sender_profile(self, mock_openai):
        """Test generating an email with incomplete sender profile."""
        # Set up mock OpenAI client
        mock_openai.return_value = self.mock_openai_client
        
        # Create incomplete sender profile
        incomplete_profile = SenderProfile(
            name="Bob Wilson",
            current_role="Developer",
            years_experience=1,
            key_skills=["Python"],
            experience_summary="Junior developer",
            value_proposition="Learning quickly",
            target_roles=["Software Engineer"]
            # Missing many optional fields
        )
        
        # Set up response for incomplete profile
        incomplete_response = MagicMock()
        incomplete_response.choices = [MagicMock()]
        incomplete_response.choices[0].message = MagicMock()
        incomplete_response.choices[0].message.content = """Subject: Impressed by FinPay on ProductHunt - Python Developer

Hi Jane,

I discovered FinPay through ProductHunt and was impressed by your modern payment processing platform for small to medium businesses.

I'm a Developer with experience in Python and am particularly interested in your API-first approach and real-time analytics features.

As a junior developer eager to grow, I believe I could contribute to your team while learning from your experienced professionals in the fintech space.

Would you be open to discussing potential opportunities at FinPay?

Best regards,
Bob Wilson"""
        
        self.mock_openai_client.chat.completions.create.return_value = incomplete_response
        
        # Create email generator with mock OpenAI client
        email_generator = EmailGenerator()
        email_generator.client = self.mock_openai_client
        
        # Generate email with incomplete profile
        email_content = email_generator.generate_outreach_email(
            prospect=self.prospect,
            linkedin_profile=self.linkedin_profile,
            product_analysis=self.product_analysis,
            ai_structured_data=self.ai_structured_data,
            sender_profile=incomplete_profile,
            template_type="cold_outreach"
        )
        
        # Verify email content
        assert email_content is not None
        assert isinstance(email_content, EmailContent)
        assert "FinPay" in email_content.subject or "ProductHunt" in email_content.subject
        assert "ProductHunt" in email_content.body
        
        # Verify sender profile integration with available fields
        assert incomplete_profile.name in email_content.body
        assert "Developer" in email_content.body
        assert "Python" in email_content.body
        
        # Verify OpenAI was called with available sender profile data
        call_args = self.mock_openai_client.chat.completions.create.call_args[1]
        messages = call_args['messages']
        user_message = [m for m in messages if m['role'] == 'user'][0]['content']
        
        # Check that sender profile fields are included in the prompt
        assert "SENDER PROFILE:" in user_message
        assert incomplete_profile.name in user_message
        assert "Developer" in user_message
        assert "Python" in user_message
    
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    def test_controller_integration_with_sender_profile(self, mock_notion_manager, mock_email_generator):
        """Test integration of sender profile in the main controller workflow."""
        # Create mock config
        mock_config = create_mock_config()
        
        # Set up mock email generator
        mock_email_generator_instance = MagicMock()
        mock_email_generator.return_value = mock_email_generator_instance
        
        mock_email_content = MagicMock(spec=EmailContent)
        mock_email_content.subject = "Test Subject"
        mock_email_content.body = "Test Body with sender context"
        mock_email_content.to_dict.return_value = {
            "subject": "Test Subject",
            "body": "Test Body with sender context"
        }
        
        mock_email_generator_instance.generate_outreach_email.return_value = mock_email_content
        
        # Set up mock notion manager
        mock_notion_instance = MagicMock()
        mock_notion_manager.return_value = mock_notion_instance
        mock_notion_instance.get_prospects.return_value = [self.prospect]
        mock_notion_instance.get_prospect_data_for_email.return_value = {
            "linkedin_profile": self.linkedin_profile.to_dict(),
            "product_analysis": {"name": "FinPay"},
            "ai_structured_data": self.ai_structured_data
        }
        
        # Create controller with mocks
        controller = ProspectAutomationController(mock_config)
        controller.sender_profile = self.sender_profile
        
        # Call generate_outreach_emails
        result = controller.generate_outreach_emails(["123"])
        
        # Verify email generator was called with sender profile
        mock_email_generator_instance.generate_outreach_email.assert_called_once()
        call_args = mock_email_generator_instance.generate_outreach_email.call_args[1]
        assert call_args["sender_profile"] == self.sender_profile
        assert call_args["prospect"] == self.prospect
        assert call_args["template_type"] == "cold_outreach"
        
        # Verify result includes sender profile used flag
        assert result["successful"][0]["sender_profile_used"] is True
        assert result["successful"][0]["prospect_id"] == "123"
        assert result["successful"][0]["email_content"]["subject"] == "Test Subject"
        assert result["successful"][0]["email_content"]["body"] == "Test Body with sender context"
    
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    def test_batch_processing_with_sender_profile(self, mock_notion_manager, mock_email_generator):
        """Test batch processing with sender profile integration."""
        # Create mock config
        mock_config = create_mock_config(
            batch_processing_enabled=True,
            max_prospects_per_batch=5
        )
        
        # Set up mock email generator
        mock_email_generator_instance = MagicMock()
        mock_email_generator.return_value = mock_email_generator_instance
        
        # Create multiple prospects
        prospects = [
            self.prospect,
            Prospect(
                id="456",
                name="Alex Brown",
                role="Head of Engineering",
                company="TechCorp",
                linkedin_url="https://linkedin.com/in/alexbrown",
                email="alex@techcorp.com",
                contacted=False,
                notes="Found on ProductHunt",
                created_at=datetime.now()
            ),
            Prospect(
                id="789",
                name="Sam Lee",
                role="Product Manager",
                company="AppStartup",
                linkedin_url="https://linkedin.com/in/samlee",
                email="sam@appstartup.com",
                contacted=False,
                notes="Found on ProductHunt",
                created_at=datetime.now()
            )
        ]
        
        # Set up mock notion manager
        mock_notion_instance = MagicMock()
        mock_notion_manager.return_value = mock_notion_instance
        mock_notion_instance.get_prospects.return_value = prospects
        
        # Mock get_prospect_data_for_email to return different data for each prospect
        def mock_get_data(prospect_id):
            if prospect_id == "123":
                return {
                    "linkedin_profile": self.linkedin_profile.to_dict(),
                    "product_analysis": {"name": "FinPay"},
                    "ai_structured_data": self.ai_structured_data
                }
            elif prospect_id == "456":
                return {
                    "linkedin_profile": {"name": "Alex Brown", "current_role": "Head of Engineering"},
                    "product_analysis": {"name": "TechProduct"},
                    "ai_structured_data": {"product_summary": "Developer tools"}
                }
            else:
                return {
                    "linkedin_profile": {"name": "Sam Lee", "current_role": "Product Manager"},
                    "product_analysis": {"name": "AppProduct"},
                    "ai_structured_data": {"product_summary": "Mobile app platform"}
                }
        
        mock_notion_instance.get_prospect_data_for_email.side_effect = mock_get_data
        
        # Mock generate_outreach_email to return different content for each prospect
        def mock_generate_email(prospect, **kwargs):
            email_content = MagicMock(spec=EmailContent)
            email_content.subject = f"Subject for {prospect.name}"
            email_content.body = f"Email body for {prospect.name} with sender context"
            email_content.to_dict.return_value = {
                "subject": f"Subject for {prospect.name}",
                "body": f"Email body for {prospect.name} with sender context"
            }
            return email_content
        
        mock_email_generator_instance.generate_outreach_email.side_effect = mock_generate_email
        
        # Create controller with mocks
        controller = ProspectAutomationController(mock_config)
        controller.sender_profile = self.sender_profile
        
        # Call generate_outreach_emails for all prospects
        result = controller.generate_outreach_emails(["123", "456", "789"])
        
        # Verify email generator was called for each prospect with sender profile
        assert mock_email_generator_instance.generate_outreach_email.call_count == 3
        
        # Check all calls included sender profile
        for call in mock_email_generator_instance.generate_outreach_email.call_args_list:
            assert call[1]["sender_profile"] == self.sender_profile
            assert call[1]["template_type"] == "cold_outreach"
        
        # Verify results
        assert len(result["successful"]) == 3
        assert all(item["sender_profile_used"] is True for item in result["successful"])
        
        # Check individual results
        prospect_ids = [item["prospect_id"] for item in result["successful"]]
        assert "123" in prospect_ids
        assert "456" in prospect_ids
        assert "789" in prospect_ids
        
        # Find result for specific prospect
        result_123 = next(item for item in result["successful"] if item["prospect_id"] == "123")
        assert result_123["email_content"]["subject"] == "Subject for Jane Smith"
        assert "Jane Smith" in result_123["email_content"]["body"]
        assert "sender context" in result_123["email_content"]["body"]
    
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    def test_error_handling_for_missing_sender_profile(self, mock_notion_manager, mock_email_generator):
        """Test error handling when sender profile is required but missing."""
        # Create mock config requiring sender profile
        mock_config = create_mock_config(
            require_sender_profile=True
        )
        
        # Set up mock email generator
        mock_email_generator_instance = MagicMock()
        mock_email_generator.return_value = mock_email_generator_instance
        
        # Set up mock notion manager
        mock_notion_instance = MagicMock()
        mock_notion_manager.return_value = mock_notion_instance
        mock_notion_instance.get_prospects.return_value = [self.prospect]
        
        # Create controller with mocks but NO sender profile
        controller = ProspectAutomationController(mock_config)
        controller.sender_profile = None  # No sender profile
        
        # Call generate_outreach_emails
        result = controller.generate_outreach_emails(["123"])
        
        # Verify email generator was NOT called
        mock_email_generator_instance.generate_outreach_email.assert_not_called()
        
        # Verify error in result
        assert result["errors"] == 1
        assert len(result["failed"]) == 1
        assert result["failed"][0]["prospect_id"] == "123"
        assert "sender profile is required" in result["failed"][0]["error"].lower()
        assert len(result["successful"]) == 0