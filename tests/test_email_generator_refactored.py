"""
Unit tests for the refactored Email Generator service using OpenAI Client Manager.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from dataclasses import dataclass

from services.email_generator import EmailGenerator, EmailTemplate, ValidationResult
from services.openai_client_manager import CompletionResponse
from models.data_models import Prospect, EmailContent, LinkedInProfile, SenderProfile
from utils.config import Config


class TestEmailGeneratorRefactored(unittest.TestCase):
    """Test cases for refactored EmailGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.use_azure_openai = True
        self.mock_config.azure_openai_api_key = "test-key"
        self.mock_config.azure_openai_endpoint = "https://test.openai.azure.com/"
        self.mock_config.azure_openai_deployment_name = "gpt-4"
        self.mock_config.azure_openai_api_version = "2024-02-15-preview"
        
        # Mock the client manager
        self.mock_client_manager = Mock()
        self.mock_client_manager.configure = Mock()
        self.mock_client_manager.make_completion = Mock()
        
        # Sample test data
        self.sample_prospect = Prospect(
            id="test-prospect-1",
            name="John Doe",
            role="Software Engineer",
            company="TechCorp",
            linkedin_url="https://linkedin.com/in/johndoe",
            email="john.doe@techcorp.com",
            source_url="https://producthunt.com/posts/techcorp",
            notes="Interested in AI solutions"
        )
        
        self.sample_linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="Senior Software Engineer at TechCorp",
            experience=["Senior Software Engineer at TechCorp (2020-Present)", "Software Engineer at StartupXYZ (2018-2020)"],
            skills=["Python", "JavaScript", "React", "Node.js", "AWS"],
            summary="Experienced software engineer with 8+ years in full-stack development and cloud architecture."
        )
        
        self.sample_sender_profile = SenderProfile(
            name="Jane Smith",
            current_role="Senior Developer",
            years_experience=5,
            key_skills=["Python", "Django", "React"],
            experience_summary="Full-stack developer with expertise in web applications",
            education=["BS Computer Science"],
            certifications=["AWS Certified Developer"],
            value_proposition="Passionate about building scalable web applications",
            notable_achievements=["Led team of 5 developers", "Reduced deployment time by 50%"],
            portfolio_links=["https://janesmith.dev"],
            location="San Francisco, CA",
            availability="Available for full-time opportunities",
            remote_preference="hybrid"
        )
    
    @patch('services.email_generator.get_client_manager')
    def test_init_with_client_manager(self, mock_get_client_manager):
        """Test EmailGenerator initialization with client manager."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config, client_id="test_generator")
        
        self.assertEqual(generator.client_manager, self.mock_client_manager)
        self.assertEqual(generator.client_id, "test_generator")
        mock_get_client_manager.assert_called_once()
        self.mock_client_manager.configure.assert_called_once_with(self.mock_config, "test_generator")
    
    @patch('services.email_generator.get_client_manager')
    def test_init_default_client_id(self, mock_get_client_manager):
        """Test EmailGenerator initialization with default client ID."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config)
        
        self.assertEqual(generator.client_id, "email_generator")
        self.mock_client_manager.configure.assert_called_once_with(self.mock_config, "email_generator")
    
    @patch('services.email_generator.get_client_manager')
    def test_init_interactive_mode(self, mock_get_client_manager):
        """Test EmailGenerator initialization with interactive mode."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config, interactive_mode=True)
        
        self.assertTrue(generator.interactive_mode)
    
    @patch('services.email_generator.get_client_manager')
    def test_init_configuration_error(self, mock_get_client_manager):
        """Test EmailGenerator initialization with configuration error."""
        mock_get_client_manager.return_value = self.mock_client_manager
        self.mock_client_manager.configure.side_effect = ValueError("Configuration failed")
        
        with self.assertRaises(ValueError):
            EmailGenerator(self.mock_config)
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_outreach_email_success(self, mock_get_client_manager):
        """Test successful email generation."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content="Subject: Exciting Opportunity at TechCorp\n\nHi John,\n\nI came across your profile on ProductHunt and was impressed by TechCorp's innovative approach to AI solutions. As a Senior Software Engineer with expertise in Python and JavaScript, I believe there could be great synergy between your work and my background in full-stack development.\n\nI'd love to discuss potential collaboration opportunities.\n\nBest regards,\nJane Smith",
            model="gpt-4",
            usage={"total_tokens": 200},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        generator = EmailGenerator(self.mock_config)
        result = generator.generate_outreach_email(
            prospect=self.sample_prospect,
            template_type=EmailTemplate.COLD_OUTREACH,
            linkedin_profile=self.sample_linkedin_profile,
            sender_profile=self.sample_sender_profile
        )
        
        self.assertIsInstance(result, EmailContent)
        self.assertEqual(result.recipient_name, "John Doe")
        self.assertEqual(result.company_name, "TechCorp")
        self.assertEqual(result.template_used, "cold_outreach")
        self.assertIn("TechCorp", result.subject)
        self.assertIn("John", result.body)
        self.assertGreater(result.personalization_score, 0)
        self.mock_client_manager.make_completion.assert_called_once()
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_outreach_email_api_error(self, mock_get_client_manager):
        """Test email generation with API error."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock error response
        mock_response = CompletionResponse(
            content="",
            model="gpt-4",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API connection error"
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        generator = EmailGenerator(self.mock_config)
        
        with self.assertRaises(Exception) as context:
            generator.generate_outreach_email(
                prospect=self.sample_prospect,
                template_type=EmailTemplate.COLD_OUTREACH
            )
        
        self.assertIn("API connection error", str(context.exception))
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_outreach_email_different_templates(self, mock_get_client_manager):
        """Test email generation with different templates."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content="Subject: Following up on our connection\n\nHi John,\n\nThank you for connecting with me. I wanted to follow up on our previous conversation about potential opportunities at TechCorp.\n\nBest regards,\nJane Smith",
            model="gpt-4",
            usage={"total_tokens": 150},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        generator = EmailGenerator(self.mock_config)
        
        # Test different template types
        templates_to_test = [
            EmailTemplate.COLD_OUTREACH,
            EmailTemplate.REFERRAL_FOLLOWUP,
            EmailTemplate.PRODUCT_INTEREST,
            EmailTemplate.NETWORKING
        ]
        
        for template in templates_to_test:
            result = generator.generate_outreach_email(
                prospect=self.sample_prospect,
                template_type=template
            )
            
            self.assertIsInstance(result, EmailContent)
            self.assertEqual(result.template_used, template.value)
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_enhanced_outreach_email(self, mock_get_client_manager):
        """Test enhanced email generation with Notion data."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content="Subject: Impressed by TechCorp's AI Innovation\n\nHi John,\n\nI discovered TechCorp through ProductHunt and was impressed by your AI analytics platform. Your background in Python and JavaScript aligns perfectly with my experience.\n\nI'd love to explore potential opportunities.\n\nBest regards,\nJane Smith",
            model="gpt-4",
            usage={"total_tokens": 180},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        # Mock notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'company': 'TechCorp',
            'linkedin_url': 'https://linkedin.com/in/johndoe',
            'email': 'john.doe@techcorp.com',
            'source_url': 'https://producthunt.com/posts/techcorp',
            'notes': 'Interested in AI solutions',
            'product_summary': 'AI analytics platform for enterprise',
            'business_insights': 'Growing company with strong technical team'
        }
        
        generator = EmailGenerator(self.mock_config)
        result = generator.generate_enhanced_outreach_email(
            prospect_id="test-prospect-1",
            notion_manager=mock_notion_manager,
            template_type=EmailTemplate.COLD_OUTREACH,
            sender_profile=self.sample_sender_profile
        )
        
        self.assertIsInstance(result, EmailContent)
        self.assertEqual(result.recipient_name, "John Doe")
        self.assertEqual(result.company_name, "TechCorp")
        mock_notion_manager.get_prospect_data_for_email.assert_called_once_with("test-prospect-1")
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_and_send_email(self, mock_get_client_manager):
        """Test email generation and sending."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content="Subject: Great opportunity at TechCorp\n\nHi John,\n\nI'd like to discuss opportunities at TechCorp.\n\nBest regards,\nJane Smith",
            model="gpt-4",
            usage={"total_tokens": 120},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        # Mock notion manager and email sender
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'company': 'TechCorp',
            'email': 'john.doe@techcorp.com'
        }
        
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "sent"
        mock_send_result.email_id = "email-123"
        mock_send_result.error_message = None
        mock_send_result.recipient_email = "john.doe@techcorp.com"
        mock_email_sender.send_email.return_value = mock_send_result
        
        generator = EmailGenerator(self.mock_config)
        result = generator.generate_and_send_email(
            prospect_id="test-prospect-1",
            notion_manager=mock_notion_manager,
            email_sender=mock_email_sender,
            send_immediately=True
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("email_content", result)
        self.assertIn("sent", result)
        self.assertTrue(result["sent"])
        self.assertIn("send_result", result)
        self.assertEqual(result["send_result"]["status"], "sent")
        self.assertEqual(result["send_result"]["email_id"], "email-123")
    
    @patch('services.email_generator.get_client_manager')
    def test_generate_and_send_bulk_emails(self, mock_get_client_manager):
        """Test bulk email generation and sending."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content="Subject: Opportunity\n\nHi there,\n\nI'd like to discuss opportunities.\n\nBest regards,\nJane Smith",
            model="gpt-4",
            usage={"total_tokens": 100},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        # Mock notion manager and email sender
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.side_effect = [
            {
                'name': 'John Doe', 
                'role': 'Software Engineer', 
                'company': 'TechCorp', 
                'email': 'john@techcorp.com',
                'linkedin_url': 'https://linkedin.com/in/johndoe',
                'source_url': 'https://producthunt.com/posts/techcorp',
                'notes': 'Interested in AI solutions'
            },
            {
                'name': 'Jane Smith', 
                'role': 'Product Manager', 
                'company': 'StartupXYZ', 
                'email': 'jane@startupxyz.com',
                'linkedin_url': 'https://linkedin.com/in/janesmith',
                'source_url': 'https://producthunt.com/posts/startupxyz',
                'notes': 'Looking for new opportunities'
            }
        ]
        
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "sent"
        mock_send_result.email_id = "email-123"
        mock_send_result.error_message = None
        mock_email_sender.send_email.return_value = mock_send_result
        
        generator = EmailGenerator(self.mock_config)
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            results = generator.generate_and_send_bulk_emails(
                prospect_ids=["prospect-1", "prospect-2"],
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                delay_between_emails=1.0
            )
        
        self.assertEqual(len(results), 2)
        for result in results:
            self.assertIsInstance(result, dict)
            self.assertIn("prospect_id", result)
            self.assertIn("sent", result)
            # Results should have either email_content (success) or error (failure)
            self.assertTrue("email_content" in result or "error" in result)
    
    @patch('services.email_generator.get_client_manager')
    def test_validate_email_content(self, mock_get_client_manager):
        """Test email content validation."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config)
        
        # Test valid email content
        valid_content = "Hi John, I found your company on ProductHunt and was impressed by your innovative approach to AI solutions. I'd love to discuss potential collaboration opportunities. Best regards, Jane"
        result = generator.validate_email_content(valid_content)
        
        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
        self.assertLess(result.spam_score, 0.3)
        
        # Test email content without ProductHunt mention
        invalid_content = "Hi John, I'd love to discuss opportunities. Best regards, Jane"
        result = generator.validate_email_content(invalid_content)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.issues), 0)
        self.assertIn("ProductHunt", result.issues[0])
        
        # Test spammy content
        spammy_content = "URGENT!!! ACT NOW!!! LIMITED TIME OFFER!!! CLICK HERE!!! FREE MONEY!!!"
        result = generator.validate_email_content(spammy_content)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.spam_score, 0.3)
        self.assertGreater(len(result.issues), 0)
    
    @patch('services.email_generator.get_client_manager')
    def test_personalize_content(self, mock_get_client_manager):
        """Test content personalization."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config)
        
        template = "Hi {name}, I saw that you work at {company} as a {role}. Your experience with {skills} is impressive."
        prospect_data = {
            "name": "John Doe",
            "company": "TechCorp",
            "role": "Software Engineer",
            "skills": "Python, JavaScript"
        }
        
        personalized = generator.personalize_content(template, prospect_data)
        
        self.assertIn("John Doe", personalized)
        self.assertIn("TechCorp", personalized)
        self.assertIn("Software Engineer", personalized)
        self.assertIn("Python, JavaScript", personalized)
    
    @patch('services.email_generator.get_client_manager')
    def test_personalize_content_missing_data(self, mock_get_client_manager):
        """Test content personalization with missing data."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config)
        
        template = "Hi {name}, I saw that you work at {company} as a {role}."
        prospect_data = {
            "name": "John Doe",
            "company": "TechCorp"
            # Missing 'role' key
        }
        
        # Should return original template when key is missing
        personalized = generator.personalize_content(template, prospect_data)
        self.assertEqual(personalized, template)
    
    @patch('services.email_generator.get_client_manager')
    def test_convert_to_html(self, mock_get_client_manager):
        """Test text to HTML conversion."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        generator = EmailGenerator(self.mock_config)
        
        text_content = "Hi John,\n\nI hope this email finds you well.\n\nBest regards,\nJane"
        html_content = generator._convert_to_html(text_content)
        
        self.assertIn("<html>", html_content)
        self.assertIn("<body", html_content)
        self.assertIn("<p>", html_content)
        self.assertIn("</p>", html_content)
        self.assertIn("<br>", html_content)
        self.assertIn("Hi John,", html_content)


class TestEmailTemplate(unittest.TestCase):
    """Test cases for EmailTemplate enum."""
    
    def test_email_template_values(self):
        """Test EmailTemplate enum values."""
        self.assertEqual(EmailTemplate.COLD_OUTREACH.value, "cold_outreach")
        self.assertEqual(EmailTemplate.REFERRAL_FOLLOWUP.value, "referral_followup")
        self.assertEqual(EmailTemplate.PRODUCT_INTEREST.value, "product_interest")
        self.assertEqual(EmailTemplate.NETWORKING.value, "networking")


class TestValidationResult(unittest.TestCase):
    """Test cases for ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult object creation."""
        result = ValidationResult(
            is_valid=True,
            issues=[],
            suggestions=["Add more personalization"],
            spam_score=0.1
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.issues), 0)
        self.assertEqual(len(result.suggestions), 1)
        self.assertEqual(result.spam_score, 0.1)
    
    def test_validation_result_with_issues(self):
        """Test ValidationResult with validation issues."""
        result = ValidationResult(
            is_valid=False,
            issues=["Content too short", "Missing ProductHunt mention"],
            suggestions=["Add more content", "Mention ProductHunt discovery"],
            spam_score=0.2
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(len(result.issues), 2)
        self.assertEqual(len(result.suggestions), 2)
        self.assertIn("Content too short", result.issues)
        self.assertIn("Missing ProductHunt mention", result.issues)


if __name__ == '__main__':
    unittest.main()