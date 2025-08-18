"""
Unit tests for the email generation service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import os
import openai

from services.email_generator import EmailGenerator, EmailTemplate, ValidationResult
from models.data_models import Prospect, EmailContent, LinkedInProfile, ProspectStatus
from utils.config import Config


class TestEmailGenerator:
    """Test cases for EmailGenerator class."""
    
    @pytest.fixture
    def mock_azure_openai_client(self):
        """Mock Azure OpenAI client for testing."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Subject: Azure Test Subject\n\nAzure test email body content"
            mock_client.chat.completions.create.return_value = mock_response
            
            yield mock_azure_openai
    
    @pytest.fixture
    def sample_config_regular_openai(self):
        """Create sample config for regular OpenAI."""
        return Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            use_azure_openai=False
        )
    
    @pytest.fixture
    def sample_config_azure_openai(self):
        """Create sample config for Azure OpenAI."""
        return Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            azure_openai_api_key="test-azure-key",
            azure_openai_endpoint="https://test-resource.openai.azure.com/",
            azure_openai_deployment_name="gpt-4-test",
            azure_openai_api_version="2024-02-15-preview",
            use_azure_openai=True
        )
    
    @pytest.fixture
    def email_generator(self, mock_openai_client):
        """Create EmailGenerator instance for testing."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            return EmailGenerator()
    
    @pytest.fixture
    def sample_prospect(self):
        """Create sample prospect for testing."""
        return Prospect(
            name="John Doe",
            role="Software Engineer",
            company="TechCorp",
            linkedin_url="https://linkedin.com/in/johndoe",
            email="john@techcorp.com",
            source_url="https://producthunt.com/posts/techcorp-app",
            notes="Experienced in Python and AI"
        )
    
    @pytest.fixture
    def sample_linkedin_profile(self):
        """Create sample LinkedIn profile for testing."""
        return LinkedInProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            experience=["Software Engineer at TechCorp", "Developer at StartupXYZ"],
            skills=["Python", "Machine Learning", "React", "Node.js"],
            summary="Passionate software engineer with 5 years of experience"
        )
    
    def test_init_with_api_key(self, mock_openai_client):
        """Test EmailGenerator initialization with API key."""
        generator = EmailGenerator(api_key="test-key")
        assert generator.client is not None
        assert len(generator.templates) == 4
    
    def test_init_without_api_key_raises_error(self):
        """Test EmailGenerator initialization without API key raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                EmailGenerator()
    
    def test_init_with_env_api_key(self, mock_openai_client):
        """Test EmailGenerator initialization with environment API key."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-test-key'}):
            generator = EmailGenerator()
            assert generator.client is not None
    
    def test_generate_outreach_email_cold_outreach(self, email_generator, sample_prospect, mock_openai_client):
        """Test generating cold outreach email."""
        email_content = email_generator.generate_outreach_email(
            sample_prospect, 
            EmailTemplate.COLD_OUTREACH
        )
        
        assert isinstance(email_content, EmailContent)
        assert email_content.subject == "Test Subject"
        assert email_content.body == "Test email body content"
        assert email_content.template_used == "cold_outreach"
        assert email_content.recipient_name == "John Doe"
        assert email_content.company_name == "TechCorp"
        assert 0 <= email_content.personalization_score <= 1
        
        # Verify OpenAI was called correctly
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-3.5-turbo'
        assert len(call_args[1]['messages']) == 2
        assert call_args[1]['messages'][0]['role'] == 'system'
        assert call_args[1]['messages'][1]['role'] == 'user'
    
    def test_generate_outreach_email_with_linkedin_profile(self, email_generator, sample_prospect, sample_linkedin_profile, mock_openai_client):
        """Test generating email with LinkedIn profile data."""
        email_content = email_generator.generate_outreach_email(
            sample_prospect,
            EmailTemplate.COLD_OUTREACH,
            linkedin_profile=sample_linkedin_profile
        )
        
        assert isinstance(email_content, EmailContent)
        assert email_content.template_used == "cold_outreach"
        
        # Check that LinkedIn data was included in the prompt
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]['messages'][1]['content']
        assert "Python, Machine Learning, React, Node.js" in user_message
        assert "Software Engineer at TechCorp" in user_message
    
    def test_generate_outreach_email_different_templates(self, email_generator, sample_prospect, mock_openai_client):
        """Test generating emails with different templates."""
        templates = [
            EmailTemplate.COLD_OUTREACH,
            EmailTemplate.REFERRAL_FOLLOWUP,
            EmailTemplate.PRODUCT_INTEREST,
            EmailTemplate.NETWORKING
        ]
        
        for template in templates:
            email_content = email_generator.generate_outreach_email(sample_prospect, template)
            assert email_content.template_used == template.value
    
    def test_generate_outreach_email_with_additional_context(self, email_generator, sample_prospect, mock_openai_client):
        """Test generating email with additional context."""
        additional_context = {
            "mutual_connection": "Jane Smith",
            "specific_interest": "AI/ML projects"
        }
        
        email_content = email_generator.generate_outreach_email(
            sample_prospect,
            EmailTemplate.REFERRAL_FOLLOWUP,
            additional_context=additional_context
        )
        
        assert isinstance(email_content, EmailContent)
        
        # Check that additional context was included
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]['messages'][1]['content']
        assert "Jane Smith" in user_message
        assert "AI/ML projects" in user_message
    
    def test_personalize_content(self, email_generator):
        """Test content personalization."""
        template = "Hello {name}, I saw you work at {company} as a {role}."
        prospect_data = {
            "name": "John Doe",
            "company": "TechCorp",
            "role": "Software Engineer"
        }
        
        result = email_generator.personalize_content(template, prospect_data)
        expected = "Hello John Doe, I saw you work at TechCorp as a Software Engineer."
        assert result == expected
    
    def test_personalize_content_missing_data(self, email_generator):
        """Test content personalization with missing data."""
        template = "Hello {name}, I saw you work at {company}."
        prospect_data = {"name": "John Doe"}  # Missing company
        
        # Should return original template when data is missing
        result = email_generator.personalize_content(template, prospect_data)
        assert result == template
    
    def test_validate_email_content_valid(self, email_generator):
        """Test validation of valid email content."""
        content = """I discovered your company through ProductHunt and was impressed by your recent launch. 
        As a software engineer with experience in Python and machine learning, I'd love to learn more about 
        potential opportunities at your company. Would you be open to a brief conversation?"""
        
        result = email_generator.validate_email_content(content)
        
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.issues) == 0
        assert result.spam_score < 0.3
    
    def test_validate_email_content_too_short(self, email_generator):
        """Test validation of too short email content."""
        content = "Hi there!"
        
        result = email_generator.validate_email_content(content)
        
        assert not result.is_valid
        assert "too short" in result.issues[0].lower()
        assert "add more personalized content" in result.suggestions[0].lower()
    
    def test_validate_email_content_too_long(self, email_generator):
        """Test validation of too long email content."""
        content = "A" * 2500  # Very long content
        
        result = email_generator.validate_email_content(content)
        
        assert not result.is_valid
        assert "too long" in result.issues[0].lower()
        assert "concise" in result.suggestions[0].lower()
    
    def test_validate_email_content_spam_indicators(self, email_generator):
        """Test validation with spam indicators."""
        content = """URGENT! ACT NOW! This is a LIMITED TIME offer with GUARANTEED results! 
        CLICK HERE to buy now with NO OBLIGATION and RISK FREE guarantee! CALL NOW!!!"""
        
        result = email_generator.validate_email_content(content)
        
        assert not result.is_valid
        assert result.spam_score > 0.3
        assert any("capitalization" in issue.lower() for issue in result.issues)
        assert any("exclamation" in issue.lower() for issue in result.issues)
    
    def test_validate_email_content_missing_producthunt(self, email_generator):
        """Test validation when ProductHunt mention is missing."""
        content = """Hello, I'm interested in opportunities at your company. 
        I have experience in software development and would love to chat."""
        
        result = email_generator.validate_email_content(content)
        
        assert not result.is_valid
        assert any("producthunt" in issue.lower() for issue in result.issues)
        assert any("mention" in suggestion.lower() for suggestion in result.suggestions)
    
    def test_prepare_personalization_data(self, email_generator, sample_prospect, sample_linkedin_profile):
        """Test preparation of personalization data."""
        data = email_generator._prepare_personalization_data(
            sample_prospect, 
            sample_linkedin_profile
        )
        
        assert data['name'] == "John Doe"
        assert data['role'] == "Software Engineer"
        assert data['company'] == "TechCorp"
        assert "Python" in data['skills']
        assert "TechCorp" in data['experience']
        assert len(data['summary']) <= 200
    
    def test_prepare_personalization_data_no_linkedin(self, email_generator, sample_prospect):
        """Test preparation of personalization data without LinkedIn profile."""
        data = email_generator._prepare_personalization_data(sample_prospect)
        
        assert data['name'] == "John Doe"
        assert data['skills'] == ''
        assert data['experience'] == ''
        assert data['summary'] == ''
    
    def test_parse_generated_content_with_subject(self, email_generator):
        """Test parsing generated content with subject line."""
        content = "Subject: Great opportunity at TechCorp\n\nHello John,\n\nI hope this email finds you well."
        
        subject, body = email_generator._parse_generated_content(content)
        
        assert subject == "Great opportunity at TechCorp"
        assert body == "Hello John,\n\nI hope this email finds you well."
    
    def test_parse_generated_content_without_subject(self, email_generator):
        """Test parsing generated content without explicit subject line."""
        content = "Great opportunity at TechCorp\n\nHello John,\n\nI hope this email finds you well."
        
        subject, body = email_generator._parse_generated_content(content)
        
        assert subject == "Great opportunity at TechCorp"
        assert body == "Hello John,\n\nI hope this email finds you well."
    
    def test_calculate_personalization_score(self, email_generator):
        """Test calculation of personalization score."""
        content = "Hello John Doe, I saw you work at TechCorp as a Software Engineer with Python skills."
        data = {
            'name': 'John Doe',
            'company': 'TechCorp',
            'role': 'Software Engineer',
            'skills': 'Python',
            'experience': 'Not mentioned'
        }
        
        score = email_generator._calculate_personalization_score(content, data)
        
        # Should be 4/5 = 0.8 (4 out of 5 fields used)
        assert score == 0.8
    
    def test_calculate_personalization_score_empty_content(self, email_generator):
        """Test personalization score calculation with empty content."""
        score = email_generator._calculate_personalization_score("", {"name": "John"})
        assert score == 0.0
    
    def test_openai_api_error_handling(self, email_generator, sample_prospect):
        """Test handling of OpenAI API errors."""
        with patch.object(email_generator.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            with pytest.raises(Exception, match="API Error"):
                email_generator.generate_outreach_email(sample_prospect)
    
    def test_all_template_types_have_prompts(self, email_generator):
        """Test that all template types have corresponding prompts."""
        for template_type in EmailTemplate:
            assert template_type in email_generator.templates
            template_config = email_generator.templates[template_type]
            assert 'system_prompt' in template_config
            assert 'user_template' in template_config
            assert len(template_config['system_prompt']) > 0
            assert len(template_config['user_template']) > 0
    
    def test_interactive_mode_initialization(self, mock_openai_client):
        """Test EmailGenerator initialization with interactive mode."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator(interactive_mode=True)
            assert generator.interactive_mode is True
    
    def test_customize_email_guidelines(self, email_generator):
        """Test customizing email generation guidelines."""
        guidelines = {
            'additional_spam_words': ['urgent', 'limited'],
            'min_length': 100,
            'max_length': 500,
            'required_mentions': ['ProductHunt']
        }
        
        # Should not raise any exceptions
        email_generator.customize_email_guidelines(guidelines)
    
    def test_get_content_suggestions_comprehensive(self, email_generator, sample_prospect):
        """Test getting comprehensive content suggestions."""
        # Email with multiple issues
        email_content = EmailContent(
            subject="Test Subject",
            body="Short email without personalization or call to action.",
            template_used="cold_outreach",
            personalization_score=0.1,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        suggestions = email_generator.get_content_suggestions(email_content, sample_prospect)
        
        assert len(suggestions) > 0
        # Should suggest mentioning name and company
        assert any("name" in suggestion.lower() for suggestion in suggestions)
        assert any("company" in suggestion.lower() for suggestion in suggestions)
        # Should suggest adding call-to-action (check for both hyphenated and non-hyphenated)
        assert any("call-to-action" in suggestion.lower() or "call to action" in suggestion.lower() for suggestion in suggestions)
        # Should suggest ProductHunt mention
        assert any("producthunt" in suggestion.lower() for suggestion in suggestions)
    
    def test_get_content_suggestions_good_email(self, email_generator, sample_prospect):
        """Test getting suggestions for a well-written email."""
        email_content = EmailContent(
            subject="Great opportunity at TechCorp",
            body="""Hi John Doe,

I discovered TechCorp through ProductHunt and was impressed by your recent launch. 
As a software engineer with experience in Python and machine learning, I'd love to 
discuss potential opportunities at TechCorp.

Would you be open to a brief conversation?

Best regards""",
            template_used="cold_outreach",
            personalization_score=0.8,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        suggestions = email_generator.get_content_suggestions(email_content, sample_prospect)
        
        # Should have fewer suggestions for a good email
        assert len(suggestions) <= 2
    
    def test_get_content_suggestions_long_email(self, email_generator, sample_prospect):
        """Test suggestions for overly long email."""
        long_body = " ".join(["This is a very long email with lots of unnecessary content."] * 20)
        email_content = EmailContent(
            subject="Test Subject",
            body=long_body,
            template_used="cold_outreach",
            personalization_score=0.5,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        suggestions = email_generator.get_content_suggestions(email_content, sample_prospect)
        
        assert any("shortening" in suggestion.lower() or "150 words" in suggestion.lower() for suggestion in suggestions)
    
    def test_get_content_suggestions_short_email(self, email_generator, sample_prospect):
        """Test suggestions for overly short email."""
        email_content = EmailContent(
            subject="Test Subject",
            body="Hi John, interested in TechCorp. Let's chat.",
            template_used="cold_outreach",
            personalization_score=0.2,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        suggestions = email_generator.get_content_suggestions(email_content, sample_prospect)
        
        assert any("personalized content" in suggestion.lower() for suggestion in suggestions)
    
    def test_enhanced_validation_with_producthunt_mention(self, email_generator):
        """Test enhanced validation specifically for ProductHunt mention requirement."""
        # Test with ProductHunt mention
        content_with_ph = "I discovered your company through ProductHunt and was impressed by your launch."
        result = email_generator.validate_email_content(content_with_ph)
        
        # Should not have ProductHunt-related issues
        ph_issues = [issue for issue in result.issues if 'producthunt' in issue.lower()]
        assert len(ph_issues) == 0
        
        # Test with Product Hunt (space separated)
        content_with_ph_space = "I saw your Product Hunt launch and wanted to reach out."
        result = email_generator.validate_email_content(content_with_ph_space)
        
        ph_issues = [issue for issue in result.issues if 'producthunt' in issue.lower()]
        assert len(ph_issues) == 0
    
    def test_validation_brief_clear_guidelines(self, email_generator):
        """Test validation enforces brief and clear content guidelines."""
        # Test overly verbose content
        verbose_content = """
        I hope this email finds you in the best of health and spirits. I am writing to you today 
        because I have been extensively researching companies in your industry and I came across 
        your organization through ProductHunt, which is a fantastic platform for discovering 
        innovative companies. After conducting thorough research about your company's mission, 
        vision, and values, I believe that there might be potential synergies between my 
        professional background and your organizational needs. Furthermore, I would like to
        elaborate on my extensive experience and qualifications that make me an ideal candidate.
        """ * 5  # Make it very long
        
        result = email_generator.validate_email_content(verbose_content)
        
        assert not result.is_valid
        assert any("too long" in issue.lower() for issue in result.issues)
        assert any("concise" in suggestion.lower() for suggestion in result.suggestions)
    
    def test_validation_non_spammy_guidelines(self, email_generator):
        """Test validation enforces non-spammy content guidelines."""
        spammy_content = """
        URGENT OPPORTUNITY! ACT NOW before this LIMITED TIME offer expires! 
        GUARANTEED success with NO OBLIGATION and completely RISK FREE! 
        CLICK HERE to CALL NOW and BUY NOW! This is your chance for FREE MONEY!
        I found you on ProductHunt.
        """
        
        result = email_generator.validate_email_content(spammy_content)
        
        assert not result.is_valid
        assert result.spam_score > 0.5  # High spam score
        assert any("capitalization" in issue.lower() for issue in result.issues)
        assert any("exclamation" in issue.lower() for issue in result.issues)
    
    def test_email_content_validation_comprehensive(self, email_generator):
        """Test comprehensive email content validation."""
        # Test perfect email
        perfect_email = """Hi John,

I discovered your company through ProductHunt and was impressed by your recent AI tool launch. 
As a software engineer with experience in machine learning, I'd love to learn about potential 
opportunities at your company.

Would you be open to a brief conversation?

Best regards"""
        
        result = email_generator.validate_email_content(perfect_email)
        assert result.is_valid
        assert result.spam_score < 0.3
        assert len(result.issues) == 0
    
    @patch('builtins.input')
    def test_review_and_edit_email_accept(self, mock_input, email_generator):
        """Test review and edit email with accept option."""
        mock_input.return_value = "1"  # Accept email as is
        
        email_content = EmailContent(
            subject="Test Subject",
            body="I discovered your company through ProductHunt. Would you be open to a chat?",
            template_used="cold_outreach",
            personalization_score=0.7,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        with patch('builtins.print'):  # Suppress print output during test
            result = email_generator.review_and_edit_email(email_content)
        
        assert result == email_content
        assert result.subject == "Test Subject"
    
    @patch('builtins.input')
    def test_review_and_edit_email_edit_subject(self, mock_input, email_generator):
        """Test review and edit email with subject editing."""
        mock_input.side_effect = ["2", "New Subject Line", "1"]  # Edit subject, then accept
        
        email_content = EmailContent(
            subject="Old Subject",
            body="I discovered your company through ProductHunt. Would you be open to a chat?",
            template_used="cold_outreach",
            personalization_score=0.7,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        with patch('builtins.print'):  # Suppress print output during test
            result = email_generator.review_and_edit_email(email_content)
        
        assert result.subject == "New Subject Line"
    
    @patch('builtins.input')
    def test_review_and_edit_email_edit_body(self, mock_input, email_generator):
        """Test review and edit email with body editing."""
        mock_input.side_effect = [
            "3",  # Edit body
            "New email body line 1",
            "New email body line 2",
            "",  # Empty line to finish
            "",  # Second empty line to finish
            "1"   # Accept
        ]
        
        email_content = EmailContent(
            subject="Test Subject",
            body="Old body content",
            template_used="cold_outreach",
            personalization_score=0.7,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        with patch('builtins.print'):  # Suppress print output during test
            result = email_generator.review_and_edit_email(email_content)
        
        assert "New email body line 1" in result.body
        assert "New email body line 2" in result.body
    
    @patch('builtins.input')
    def test_review_and_edit_email_show_validation(self, mock_input, email_generator):
        """Test review and edit email with validation details."""
        mock_input.side_effect = ["5", "1"]  # Show validation, then accept
        
        email_content = EmailContent(
            subject="Test Subject",
            body="Short",  # This will trigger validation issues
            template_used="cold_outreach",
            personalization_score=0.1,
            recipient_name="John Doe",
            company_name="TechCorp"
        )
        
        with patch('builtins.print') as mock_print:
            result = email_generator.review_and_edit_email(email_content)
        
        # Should have called print to show validation details
        assert mock_print.called
        assert result == email_content
    
    # Azure OpenAI specific tests
    def test_init_with_azure_openai_config(self, mock_azure_openai_client, sample_config_azure_openai):
        """Test EmailGenerator initialization with Azure OpenAI configuration."""
        generator = EmailGenerator(config=sample_config_azure_openai)
        
        assert generator.client is not None
        assert generator.model_name == "gpt-4-test"
        assert len(generator.templates) == 4
        
        # Verify Azure OpenAI client was initialized with correct parameters
        mock_azure_openai_client.assert_called_once_with(
            api_key="test-azure-key",
            azure_endpoint="https://test-resource.openai.azure.com/",
            api_version="2024-02-15-preview"
        )
    
    def test_init_with_regular_openai_config(self, sample_config_regular_openai):
        """Test EmailGenerator initialization with regular OpenAI configuration."""
        with patch('services.email_generator.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Subject: Test Subject\n\nTest email body content"
            mock_client.chat.completions.create.return_value = mock_response
            
            generator = EmailGenerator(config=sample_config_regular_openai)
            
            assert generator.client is not None
            assert generator.model_name == "gpt-3.5-turbo"
            assert len(generator.templates) == 4
            
            # Verify regular OpenAI client was initialized
            mock_openai.assert_called_once_with(api_key="test-openai-key")
    
    def test_azure_openai_missing_api_key_raises_error(self):
        """Test Azure OpenAI initialization without API key raises error."""
        config = Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            use_azure_openai=True,
            azure_openai_endpoint="https://test-resource.openai.azure.com/"
        )
        
        with pytest.raises(ValueError, match="Azure OpenAI API key is required"):
            EmailGenerator(config=config)
    
    def test_generate_enhanced_outreach_email(self, mock_openai_client):
        """Test generating enhanced outreach email with AI-structured data."""
        # Mock NotionDataManager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Software Engineer',
            'company': 'TechCorp',
            'linkedin_url': 'https://linkedin.com/in/johndoe',
            'email': 'john@techcorp.com',
            'source_url': 'https://producthunt.com/posts/techcorp-app',
            'notes': 'Experienced developer',
            'product_summary': 'AI-powered productivity tool for developers',
            'business_insights': 'Series A funded, 50+ employees, growing rapidly',
            'linkedin_summary': 'Senior engineer with 5+ years experience in Python and ML',
            'personalization_data': 'Interested in AI/ML, open source contributor',
            'market_analysis': 'Competing with Notion and Linear',
            'product_features': 'Real-time collaboration, AI assistance',
            'pricing_model': 'Freemium with enterprise plans',
            'competitors': 'Notion, Linear, Asana'
        }
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            email_content = generator.generate_enhanced_outreach_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                template_type=EmailTemplate.COLD_OUTREACH
            )
        
        assert isinstance(email_content, EmailContent)
        assert email_content.recipient_name == "John Doe"
        assert email_content.company_name == "TechCorp"
        assert email_content.template_used == "cold_outreach"
        
        # Verify NotionDataManager was called
        mock_notion_manager.get_prospect_data_for_email.assert_called_once_with("test-prospect-id")
        
        # Verify OpenAI was called with enhanced data
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]['messages'][1]['content']
        
        # Check that AI-structured data was included
        assert "AI-powered productivity tool" in user_message
        assert "Series A funded" in user_message
        assert "Senior engineer with 5+ years experience" in user_message
        assert "Interested in AI/ML" in user_message
    
    def test_prepare_personalization_data_with_ai_structured_data(self, email_generator, sample_prospect):
        """Test preparation of personalization data with AI-structured data."""
        ai_structured_data = {
            'product_summary': 'Revolutionary AI tool for developers that automates code review',
            'business_insights': 'Series B funded startup with 100+ employees, expanding globally',
            'linkedin_summary': 'Experienced CTO with background in distributed systems and AI',
            'personalization_data': 'Active in open source, speaks at conferences, interested in developer tools',
            'market_analysis': 'Leading in the developer productivity space',
            'product_features': 'AI code review, automated testing, deployment pipelines',
            'pricing_model': 'Usage-based pricing with enterprise tiers',
            'competitors': 'GitHub Copilot, CodeClimate, SonarQube'
        }
        
        data = email_generator._prepare_personalization_data(
            sample_prospect,
            ai_structured_data=ai_structured_data
        )
        
        # Check that AI-structured data is properly included and truncated
        assert data['product_summary'] == ai_structured_data['product_summary'][:500]
        assert data['business_insights'] == ai_structured_data['business_insights'][:300]
        assert data['linkedin_summary'] == ai_structured_data['linkedin_summary'][:300]
        assert data['personalization_points'] == ai_structured_data['personalization_data'][:400]
        assert data['market_analysis'] == ai_structured_data['market_analysis'][:200]
        assert data['product_features'] == ai_structured_data['product_features'][:200]
        assert data['pricing_model'] == ai_structured_data['pricing_model'][:200]
        assert data['competitors'] == ai_structured_data['competitors'][:200]
    
    def test_prepare_personalization_data_ai_overrides_basic_data(self, email_generator, sample_prospect, sample_linkedin_profile):
        """Test that AI-structured data overrides basic LinkedIn data."""
        ai_structured_data = {
            'linkedin_summary': 'AI-enhanced LinkedIn summary with deeper insights',
            'product_summary': 'Comprehensive product analysis from AI'
        }
        
        data = email_generator._prepare_personalization_data(
            sample_prospect,
            linkedin_profile=sample_linkedin_profile,
            ai_structured_data=ai_structured_data
        )
        
        # AI-structured LinkedIn summary should override basic summary
        assert data['summary'] == ai_structured_data['linkedin_summary'][:200]
        assert data['linkedin_summary'] == ai_structured_data['linkedin_summary'][:300]
        
        # But basic LinkedIn data should still be present
        assert "Python" in data['skills']  # From basic LinkedIn profile
    
    def test_enhanced_email_templates_include_ai_data(self, email_generator, sample_prospect):
        """Test that enhanced email templates include AI-structured data fields."""
        ai_structured_data = {
            'product_summary': 'AI-powered analytics platform',
            'business_insights': 'Fast-growing SaaS company',
            'personalization_points': 'Focus on data science and ML'
        }
        
        data = email_generator._prepare_personalization_data(
            sample_prospect,
            ai_structured_data=ai_structured_data
        )
        
        # Test cold outreach template
        template = email_generator._get_cold_outreach_user_template()
        formatted_template = template.format(**data)
        
        assert "AI-powered analytics platform" in formatted_template
        assert "Fast-growing SaaS company" in formatted_template
        assert "Focus on data science and ML" in formatted_template
    
    def test_enhanced_system_prompts_mention_ai_data(self, email_generator):
        """Test that enhanced system prompts mention using AI-structured data."""
        cold_outreach_prompt = email_generator._get_cold_outreach_system_prompt()
        product_interest_prompt = email_generator._get_product_interest_system_prompt()
        
        # Check that system prompts mention AI-structured data
        assert "AI-structured data" in cold_outreach_prompt
        assert "product_summary" in cold_outreach_prompt
        assert "business_insights" in cold_outreach_prompt
        
        assert "AI-structured data" in product_interest_prompt
        assert "comprehensive product context" in product_interest_prompt
    
    def test_generate_outreach_email_with_ai_structured_data(self, email_generator, sample_prospect, mock_openai_client):
        """Test generating outreach email with AI-structured data parameter."""
        ai_structured_data = {
            'product_summary': 'Innovative fintech solution for small businesses',
            'business_insights': 'Seed-funded startup with strong traction',
            'linkedin_summary': 'Fintech entrepreneur with banking background',
            'personalization_points': 'Passionate about financial inclusion'
        }
        
        email_content = email_generator.generate_outreach_email(
            sample_prospect,
            EmailTemplate.COLD_OUTREACH,
            ai_structured_data=ai_structured_data
        )
        
        assert isinstance(email_content, EmailContent)
        assert email_content.template_used == "cold_outreach"
        
        # Check that AI-structured data was included in the prompt
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]['messages'][1]['content']
        
        assert "Innovative fintech solution" in user_message
        assert "Seed-funded startup" in user_message
        assert "Fintech entrepreneur" in user_message
        assert "Passionate about financial inclusion" in user_message
    
    def test_all_templates_support_ai_structured_data(self, email_generator, sample_prospect):
        """Test that all email templates support AI-structured data fields."""
        ai_structured_data = {
            'product_summary': 'Test product summary',
            'business_insights': 'Test business insights',
            'linkedin_summary': 'Test LinkedIn summary',
            'personalization_points': 'Test personalization points',
            'market_analysis': 'Test market analysis',
            'product_features': 'Test features',
            'pricing_model': 'Test pricing',
            'competitors': 'Test competitors'
        }
        
        data = email_generator._prepare_personalization_data(
            sample_prospect,
            ai_structured_data=ai_structured_data
        )
        
        # Test all templates can be formatted with AI data
        for template_type in EmailTemplate:
            template_config = email_generator.templates[template_type]
            user_template = template_config['user_template']
            
            # Should not raise KeyError
            try:
                formatted_template = user_template.format(**data)
                # Check that AI data is included
                assert "Test product summary" in formatted_template
                assert "Test business insights" in formatted_template
            except KeyError as e:
                pytest.fail(f"Template {template_type.value} missing field: {e}")
    
    def test_enhanced_personalization_score_calculation(self, email_generator):
        """Test personalization score calculation with AI-structured data."""
        content = """Hi John Doe, I discovered TechCorp through ProductHunt and was impressed by your AI-powered analytics platform. 
        As someone with experience in data science, I'm excited about your fast-growing SaaS company's focus on ML innovation."""
        
        data = {
            'name': 'John Doe',
            'company': 'TechCorp',
            'product_summary': 'AI-powered analytics platform',
            'business_insights': 'fast-growing SaaS company',
            'personalization_points': 'focus on ML innovation',
            'skills': 'data science',
            'unused_field': 'not mentioned'
        }
        
        score = email_generator._calculate_personalization_score(content, data)
        
        # Should have high score since most fields are used
        assert score > 0.7  # At least 70% of fields used
    
    def test_enhanced_email_validation_with_ai_context(self, email_generator):
        """Test email validation with AI-enhanced context."""
        # Email with good AI-structured personalization
        ai_enhanced_email = """Hi Sarah,

I discovered your company through ProductHunt and was impressed by your AI-powered customer service platform. 
Your Series A funding and focus on enterprise clients aligns perfectly with my background in B2B SaaS and ML engineering.

Would you be open to a brief conversation about potential opportunities?

Best regards"""
        
        result = email_generator.validate_email_content(ai_enhanced_email)
        
        assert result.is_valid
        assert result.spam_score < 0.3
        assert len(result.issues) == 0
    
    def test_generate_enhanced_outreach_email_error_handling(self, mock_openai_client):
        """Test error handling in generate_enhanced_outreach_email."""
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.side_effect = Exception("Notion API error")
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            with pytest.raises(Exception, match="Failed to generate enhanced email"):
                generator.generate_enhanced_outreach_email(
                    prospect_id="test-prospect-id",
                    notion_manager=mock_notion_manager
                )
    
    def test_ai_structured_data_field_truncation(self, email_generator, sample_prospect):
        """Test that AI-structured data fields are properly truncated."""
        # Create very long AI-structured data
        long_text = "A" * 1000
        ai_structured_data = {
            'product_summary': long_text,
            'business_insights': long_text,
            'linkedin_summary': long_text,
            'personalization_data': long_text,
            'market_analysis': long_text
        }
        
        data = email_generator._prepare_personalization_data(
            sample_prospect,
            ai_structured_data=ai_structured_data
        )
        
        # Check truncation limits
        assert len(data['product_summary']) <= 500
        assert len(data['business_insights']) <= 300
        assert len(data['linkedin_summary']) <= 300
        assert len(data['personalization_points']) <= 400
        assert len(data['market_analysis']) <= 200
    
    def test_generate_and_send_email_success(self, mock_openai_client):
        """Test successful email generation and sending workflow."""
        # Mock NotionDataManager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'Jane Smith',
            'role': 'CTO',
            'company': 'InnovateCorp',
            'email': 'jane@innovatecorp.com',
            'product_summary': 'AI-powered analytics platform for enterprises',
            'business_insights': 'Series B funded, 200+ employees, rapid growth',
            'linkedin_summary': 'Experienced CTO with 10+ years in enterprise software'
        }
        
        # Mock EmailSender
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "sent"
        mock_send_result.email_id = "test-email-123"
        mock_send_result.error_message = None
        mock_send_result.recipient_email = "jane@innovatecorp.com"
        mock_email_sender.send_email.return_value = mock_send_result
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            result = generator.generate_and_send_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                send_immediately=True
            )
        
        # Verify result structure
        assert result['prospect_id'] == "test-prospect-id"
        assert result['sent'] is True
        assert result['send_result']['email_id'] == "test-email-123"
        assert result['send_result']['status'] == "sent"
        assert 'email_content' in result
        assert 'generated_at' in result
        
        # Verify NotionDataManager was called (twice - once for email generation, once for sending)
        assert mock_notion_manager.get_prospect_data_for_email.call_count == 2
        
        # Verify EmailSender was called
        mock_email_sender.validate_email_address.assert_called_once_with("jane@innovatecorp.com")
        mock_email_sender.send_email.assert_called_once()
        
        # Check email sending parameters
        send_call_args = mock_email_sender.send_email.call_args
        assert send_call_args[1]['recipient_email'] == "jane@innovatecorp.com"
        assert send_call_args[1]['prospect_id'] == "test-prospect-id"
        assert "job-prospect" in send_call_args[1]['tags']
    
    def test_generate_and_send_email_no_email_address(self, mock_openai_client):
        """Test email generation when prospect has no email address."""
        # Mock NotionDataManager with no email
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Developer',
            'company': 'TechCorp',
            'email': None,  # No email address
            'product_summary': 'Great product'
        }
        
        mock_email_sender = Mock()
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            result = generator.generate_and_send_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                send_immediately=True
            )
        
        # Should generate email but not send it
        assert result['sent'] is False
        assert 'error' in result
        assert "No email address available" in result['error']
        assert 'email_content' in result  # Email should still be generated
        
        # EmailSender should not be called
        mock_email_sender.send_email.assert_not_called()
    
    def test_generate_and_send_email_invalid_email(self, mock_openai_client):
        """Test email generation with invalid email address."""
        # Mock NotionDataManager with valid format but invalid email that fails sender validation
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Developer',
            'company': 'TechCorp',
            'email': 'test@invalid-domain.fake',  # Valid format but invalid domain
            'product_summary': 'Great product'
        }
        
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = False  # Sender validation fails
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            result = generator.generate_and_send_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                send_immediately=True
            )
        
        # Should generate email but not send it
        assert result['sent'] is False
        assert 'error' in result
        assert "Invalid email address" in result['error']
        assert 'email_content' in result
        
        # EmailSender validation should be called but not send_email
        mock_email_sender.validate_email_address.assert_called_once_with("test@invalid-domain.fake")
        mock_email_sender.send_email.assert_not_called()
    
    def test_generate_and_send_email_send_failure(self, mock_openai_client):
        """Test email generation when sending fails."""
        # Mock NotionDataManager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'Jane Smith',
            'role': 'CTO',
            'company': 'InnovateCorp',
            'email': 'jane@innovatecorp.com',
            'product_summary': 'AI platform'
        }
        
        # Mock EmailSender with send failure
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "failed"
        mock_send_result.email_id = ""
        mock_send_result.error_message = "API rate limit exceeded"
        mock_send_result.recipient_email = "jane@innovatecorp.com"
        mock_email_sender.send_email.return_value = mock_send_result
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            result = generator.generate_and_send_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                send_immediately=True
            )
        
        # Should generate email but sending should fail
        assert result['sent'] is False
        assert result['send_result']['status'] == "failed"
        assert result['send_result']['error_message'] == "API rate limit exceeded"
        assert 'email_content' in result
    
    def test_generate_and_send_email_generation_only(self, mock_openai_client):
        """Test email generation without sending."""
        # Mock NotionDataManager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'role': 'Developer',
            'company': 'TechCorp',
            'email': 'john@techcorp.com',
            'product_summary': 'Great product'
        }
        
        mock_email_sender = Mock()
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            generator = EmailGenerator()
            
            result = generator.generate_and_send_email(
                prospect_id="test-prospect-id",
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                send_immediately=False  # Don't send
            )
        
        # Should generate email but not send it
        assert result['sent'] is False
        assert result['send_result'] is None
        assert 'email_content' in result
        
        # EmailSender should not be called at all
        mock_email_sender.validate_email_address.assert_not_called()
        mock_email_sender.send_email.assert_not_called()
    
    def test_convert_to_html(self, email_generator):
        """Test conversion of plain text to HTML format."""
        text_content = "Hello John,\n\nI hope this email finds you well.\n\nBest regards"
        
        html_content = email_generator._convert_to_html(text_content)
        
        # Check HTML structure
        assert "<html>" in html_content
        assert "<body" in html_content
        assert "</body>" in html_content
        assert "</html>" in html_content
        
        # Check content conversion (double newlines become paragraph breaks)
        assert "<p>Hello John,</p><p>I hope this email finds you well.</p><p>Best regards</p>" in html_content
        
        # Check CSS styling
        assert "font-family: Arial, sans-serif" in html_content
        assert "line-height: 1.6" in html_content
    
    def test_generate_and_send_bulk_emails(self, mock_openai_client):
        """Test bulk email generation and sending."""
        prospect_ids = ["prospect-1", "prospect-2", "prospect-3"]
        
        # Mock NotionDataManager - need to handle multiple calls per prospect (2 calls each)
        mock_notion_manager = Mock()
        prospect_data = [
            {
                'name': 'John Doe',
                'role': 'Developer',
                'company': 'TechCorp',
                'email': 'john@techcorp.com',
                'product_summary': 'Great product 1'
            },
            {
                'name': 'Jane Smith',
                'role': 'CTO',
                'company': 'InnovateCorp',
                'email': 'jane@innovatecorp.com',
                'product_summary': 'Great product 2'
            },
            {
                'name': 'Bob Wilson',
                'role': 'CEO',
                'company': 'StartupXYZ',
                'email': 'bob@startupxyz.com',
                'product_summary': 'Great product 3'
            }
        ]
        # Each prospect gets called twice, so we need 6 total calls
        mock_notion_manager.get_prospect_data_for_email.side_effect = prospect_data * 2
        
        # Mock EmailSender
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "sent"
        mock_send_result.email_id = "test-email-123"
        mock_send_result.error_message = None
        mock_email_sender.send_email.return_value = mock_send_result
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Mock sleep to speed up test
                generator = EmailGenerator()
                
                results = generator.generate_and_send_bulk_emails(
                    prospect_ids=prospect_ids,
                    notion_manager=mock_notion_manager,
                    email_sender=mock_email_sender,
                    delay_between_emails=0.1  # Short delay for testing
                )
        
        # Should process all prospects
        assert len(results) == 3
        
        # All should be successful
        successful_results = [r for r in results if r.get('sent', False)]
        assert len(successful_results) == 3
        
        # Verify all prospects were processed (2 calls per prospect = 6 total)
        assert mock_notion_manager.get_prospect_data_for_email.call_count == 6
        assert mock_email_sender.send_email.call_count == 3
    
    def test_generate_and_send_bulk_emails_with_failures(self, mock_openai_client):
        """Test bulk email generation with some failures."""
        prospect_ids = ["prospect-1", "prospect-2"]
        
        # Mock NotionDataManager - use a function to return correct data based on prospect_id
        mock_notion_manager = Mock()
        def get_prospect_data(prospect_id):
            if prospect_id == "prospect-1":
                return {
                    'name': 'John Doe',
                    'role': 'Developer',
                    'company': 'TechCorp',
                    'email': 'john@techcorp.com',
                    'product_summary': 'Great product 1'
                }
            elif prospect_id == "prospect-2":
                return {
                    'name': 'Jane Smith',
                    'role': 'CTO',
                    'company': 'InnovateCorp',
                    'email': None,  # No email
                    'product_summary': 'Great product 2'
                }
        
        mock_notion_manager.get_prospect_data_for_email.side_effect = get_prospect_data
        
        # Mock EmailSender
        mock_email_sender = Mock()
        mock_email_sender.validate_email_address.return_value = True
        mock_send_result = Mock()
        mock_send_result.status = "sent"
        mock_send_result.email_id = "test-email-123"
        mock_email_sender.send_email.return_value = mock_send_result
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('time.sleep'):  # Mock sleep to speed up test
                generator = EmailGenerator()
                
                results = generator.generate_and_send_bulk_emails(
                    prospect_ids=prospect_ids,
                    notion_manager=mock_notion_manager,
                    email_sender=mock_email_sender,
                    delay_between_emails=0.1
                )
        
        # Should process both prospects
        assert len(results) == 2
        
        # One successful, one failed
        successful_results = [r for r in results if r.get('sent', False)]
        failed_results = [r for r in results if not r.get('sent', False)]
        
        assert len(successful_results) == 1
        assert len(failed_results) == 1
        
        # Check that the failed result has an error
        assert 'error' in failed_results[0]
        assert "No email address available" in failed_results[0]['error']
    
    def test_azure_openai_missing_endpoint_raises_error(self):
        """Test Azure OpenAI initialization without endpoint raises error."""
        config = Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            azure_openai_api_key="test-azure-key",
            use_azure_openai=True
        )
        
        with pytest.raises(ValueError, match="Azure OpenAI endpoint is required"):
            EmailGenerator(config=config)
    
    def test_generate_email_with_azure_openai(self, sample_config_azure_openai, sample_prospect):
        """Test generating email with Azure OpenAI."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Subject: Azure Test Subject\n\nAzure test email body content"
            mock_client.chat.completions.create.return_value = mock_response
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            email_content = generator.generate_outreach_email(
                sample_prospect,
                EmailTemplate.COLD_OUTREACH
            )
            
            assert isinstance(email_content, EmailContent)
            assert email_content.subject == "Azure Test Subject"
            assert email_content.body == "Azure test email body content"
            assert email_content.template_used == "cold_outreach"
            
            # Verify Azure OpenAI was called with correct model
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4-test'
            assert len(call_args[1]['messages']) == 2
            assert call_args[1]['messages'][0]['role'] == 'system'
            assert call_args[1]['messages'][1]['role'] == 'user'
    
    def test_azure_openai_api_error_handling(self, sample_config_azure_openai, sample_prospect):
        """Test handling of Azure OpenAI API errors."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("Azure API Error")
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            with pytest.raises(Exception, match="Azure API Error"):
                generator.generate_outreach_email(sample_prospect)
    
    def test_backward_compatibility_with_api_key_parameter(self):
        """Test backward compatibility with deprecated api_key parameter."""
        with patch('services.email_generator.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Subject: Test Subject\n\nTest email body content"
            mock_client.chat.completions.create.return_value = mock_response
            
            generator = EmailGenerator(api_key="test-key")
            
            assert generator.client is not None
            assert generator.model_name == "gpt-3.5-turbo"
            
            # Verify regular OpenAI client was initialized
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_config_overrides_api_key_parameter(self, mock_azure_openai_client, sample_config_azure_openai):
        """Test that config parameter takes precedence over api_key parameter."""
        generator = EmailGenerator(config=sample_config_azure_openai, api_key="ignored-key")
        
        assert generator.client is not None
        assert generator.model_name == "gpt-4-test"
        
        # Verify Azure OpenAI client was initialized, not regular OpenAI
        mock_azure_openai_client.assert_called_once()
    
    def test_azure_openai_with_different_deployment_name(self, mock_azure_openai_client):
        """Test Azure OpenAI with different deployment name."""
        config = Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            azure_openai_api_key="test-azure-key",
            azure_openai_endpoint="https://test-resource.openai.azure.com/",
            azure_openai_deployment_name="gpt-35-turbo",
            use_azure_openai=True
        )
        
        generator = EmailGenerator(config=config)
        
        assert generator.model_name == "gpt-35-turbo"
    
    def test_azure_openai_with_different_api_version(self, mock_azure_openai_client):
        """Test Azure OpenAI with different API version."""
        config = Config(
            notion_token="test-notion-token",
            hunter_api_key="test-hunter-key",
            openai_api_key="test-openai-key",
            azure_openai_api_key="test-azure-key",
            azure_openai_endpoint="https://test-resource.openai.azure.com/",
            azure_openai_api_version="2023-12-01-preview",
            use_azure_openai=True
        )
        
        generator = EmailGenerator(config=config)
        
        # Verify Azure OpenAI client was initialized with correct API version
        mock_azure_openai_client.assert_called_once_with(
            api_key="test-azure-key",
            azure_endpoint="https://test-resource.openai.azure.com/",
            api_version="2023-12-01-preview"
        )
    
    def test_azure_openai_rate_limit_error_handling(self, sample_config_azure_openai, sample_prospect):
        """Test handling of Azure OpenAI rate limit errors."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = openai.RateLimitError(
                message="Rate limit exceeded",
                response=Mock(),
                body={}
            )
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            with pytest.raises(openai.RateLimitError):
                generator.generate_outreach_email(sample_prospect)
    
    def test_azure_openai_authentication_error_handling(self, sample_config_azure_openai, sample_prospect):
        """Test handling of Azure OpenAI authentication errors."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
                message="Invalid API key",
                response=Mock(),
                body={}
            )
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            with pytest.raises(openai.AuthenticationError):
                generator.generate_outreach_email(sample_prospect)
    
    def test_azure_openai_connection_error_handling(self, sample_config_azure_openai, sample_prospect):
        """Test handling of Azure OpenAI connection errors."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = openai.APIConnectionError(
                message="Connection failed",
                request=Mock()
            )
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            with pytest.raises(openai.APIConnectionError):
                generator.generate_outreach_email(sample_prospect)
    
    def test_azure_openai_bad_request_error_handling(self, sample_config_azure_openai, sample_prospect):
        """Test handling of Azure OpenAI bad request errors."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = openai.BadRequestError(
                message="Invalid request",
                response=Mock(),
                body={}
            )
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            with pytest.raises(openai.BadRequestError):
                generator.generate_outreach_email(sample_prospect)
    
    def test_azure_openai_email_generation_quality(self, sample_config_azure_openai, sample_prospect, sample_linkedin_profile):
        """Test email generation quality with Azure OpenAI models."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            # Mock a high-quality response that would come from Azure OpenAI
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = """Subject: Impressed by TechCorp's ProductHunt Launch

Hi John Doe,

I discovered TechCorp through ProductHunt and was genuinely impressed by your recent launch. As a Software Engineer with experience in Python, Machine Learning, React, and Node.js, I'm particularly drawn to the innovative approach your team is taking.

Your background as a Senior Software Engineer at TechCorp and your experience in software development caught my attention. Given your passionate approach to software engineering with 5 years of experience, I'd love to learn more about potential opportunities to contribute to your team's continued success.

Would you be open to a brief conversation?

Best regards"""
            mock_client.chat.completions.create.return_value = mock_response
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            email_content = generator.generate_outreach_email(
                sample_prospect,
                EmailTemplate.COLD_OUTREACH,
                linkedin_profile=sample_linkedin_profile
            )
            
            # Verify the email quality
            assert isinstance(email_content, EmailContent)
            assert "TechCorp" in email_content.subject
            assert "ProductHunt" in email_content.body
            assert "John" in email_content.body
            assert email_content.template_used == "cold_outreach"
            
            # Verify the email passes validation
            validation_result = generator.validate_email_content(email_content.body)
            assert validation_result.is_valid
            assert validation_result.spam_score < 0.3
            
            # Verify personalization score is reasonable (at least some personalization)
            assert email_content.personalization_score > 0.2
            
            # Verify Azure OpenAI was called with correct parameters
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4-test'
            assert call_args[1]['temperature'] == 0.7
            assert call_args[1]['max_tokens'] == 800
    
    def test_azure_openai_prompt_format_compatibility(self, sample_config_azure_openai, sample_prospect):
        """Test that Azure OpenAI prompts are formatted correctly."""
        with patch('services.email_generator.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            # Mock response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "Subject: Test\n\nTest body"
            mock_client.chat.completions.create.return_value = mock_response
            
            generator = EmailGenerator(config=sample_config_azure_openai)
            
            generator.generate_outreach_email(sample_prospect, EmailTemplate.COLD_OUTREACH)
            
            # Verify the prompt format is correct for Azure OpenAI
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]['messages']
            
            assert len(messages) == 2
            assert messages[0]['role'] == 'system'
            assert messages[1]['role'] == 'user'
            assert 'ProductHunt' in messages[0]['content'] or 'ProductHunt' in messages[1]['content']
            assert len(messages[0]['content']) > 50  # System prompt should be substantial
            assert len(messages[1]['content']) > 20  # User prompt should contain prospect data    
  
  # Tests for sender-aware email generation (Task 24.1)
    
    @pytest.fixture
    def sample_sender_profile(self):
        """Create sample sender profile for testing."""
        from models.data_models import SenderProfile
        return SenderProfile(
            name="John Doe",
            current_role="Senior Software Engineer",
            years_experience=5,
            key_skills=["Python", "React", "AWS", "Docker", "Machine Learning"],
            experience_summary="Experienced software engineer with expertise in full-stack development and cloud architecture. Led multiple successful product launches and scaled systems to handle millions of users.",
            education=["BS Computer Science - MIT", "MS Software Engineering - Stanford"],
            certifications=["AWS Solutions Architect", "Google Cloud Professional"],
            value_proposition="I help startups build scalable, reliable software systems that grow with their business needs.",
            target_roles=["Senior Engineer", "Tech Lead", "Engineering Manager"],
            industries_of_interest=["SaaS", "FinTech", "HealthTech", "EdTech"],
            notable_achievements=[
                "Led team that reduced system latency by 60%",
                "Built ML pipeline that increased user engagement by 40%",
                "Architected microservices platform serving 10M+ requests/day"
            ],
            portfolio_links=["https://github.com/johndoe", "https://johndoe.dev"],
            preferred_contact_method="email",
            availability="Available for immediate start",
            location="San Francisco, CA",
            remote_preference="remote",
            additional_context={"timezone": "PST", "visa_status": "US Citizen"}
        )
    
    def test_generate_outreach_email_with_sender_profile(self, mock_openai_client, sample_prospect, sample_sender_profile):
        """Test email generation with sender profile integration."""
        generator = EmailGenerator(api_key="test-key")
        
        result = generator.generate_outreach_email(
            prospect=sample_prospect,
            template_type=EmailTemplate.COLD_OUTREACH,
            sender_profile=sample_sender_profile
        )
        
        assert isinstance(result, EmailContent)
        assert result.subject == "Test Subject"
        assert result.body == "Test email body content"
        assert result.template_used == "cold_outreach"
        
        # Verify that sender profile data was included in the API call
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args
        user_message = call_args[1]['messages'][1]['content']
        
        # Check that sender profile information is included in the prompt
        assert "John Doe" in user_message
        assert "Senior Software Engineer" in user_message
        assert "Python" in user_message
        assert "AWS" in user_message
        # Check for dynamic sections
        assert "SENDER PROFILE:" in user_message
        assert "DYNAMIC SECTIONS" in user_message
    
    def test_prepare_personalization_data_with_sender_profile(self, sample_prospect, sample_sender_profile):
        """Test that sender profile data is properly included in personalization data."""
        generator = EmailGenerator(api_key="test-key")
        
        data = generator._prepare_personalization_data(
            prospect=sample_prospect,
            sender_profile=sample_sender_profile
        )
        
        # Check sender profile fields are included
        assert data['sender_name'] == "John Doe"
        assert data['sender_role'] == "Senior Software Engineer"
        assert data['sender_experience_years'] == "5"
        assert "Python" in data['sender_skills']
        assert "React" in data['sender_skills']
        assert "AWS" in data['sender_skills']
        assert "Experienced software engineer" in data['sender_experience_summary']
        assert "BS Computer Science" in data['sender_education']
        assert "AWS Solutions Architect" in data['sender_certifications']
        assert "scalable, reliable software systems" in data['sender_value_proposition']
        assert "Led team that reduced system latency" in data['sender_achievements']
        assert "github.com/johndoe" in data['sender_portfolio']
        assert data['sender_location'] == "San Francisco, CA"
        assert data['sender_availability'] == "Available for immediate start"
        assert data['sender_remote_preference'] == "remote"
    
    def test_get_relevant_sender_experience(self, sample_sender_profile):
        """Test extraction of relevant sender experience for specific prospect."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with engineering prospect
        engineering_prospect = Prospect(
            name="Jane Smith",
            role="Engineering Manager",
            company="TechCorp",
            email="jane@techcorp.com"
        )
        
        relevant_exp = generator._get_relevant_sender_experience(sample_sender_profile, engineering_prospect)
        
        # Should include relevant achievements and experience
        assert len(relevant_exp) > 0
        assert any(keyword in relevant_exp.lower() for keyword in ['led', 'team', 'system', 'built'])
    
    def test_get_sender_industry_match(self, sample_sender_profile):
        """Test industry matching between sender and prospect."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with SaaS company prospect
        saas_prospect = Prospect(
            name="Bob Wilson",
            role="CTO",
            company="SaaS Solutions Inc",
            email="bob@saassolutions.com"
        )
        
        industry_match = generator._get_sender_industry_match(sample_sender_profile, saas_prospect)
        
        # Should match SaaS industry
        assert "SaaS" in industry_match
    
    def test_get_sender_skill_match(self, sample_sender_profile):
        """Test skill matching between sender and prospect role."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with engineering prospect
        engineering_prospect = Prospect(
            name="Alice Johnson",
            role="Senior Python Developer",
            company="DevCorp",
            email="alice@devcorp.com"
        )
        
        skill_match = generator._get_sender_skill_match(sample_sender_profile, engineering_prospect)
        
        # Should include Python and other relevant technical skills
        assert "Python" in skill_match
        assert len(skill_match) > 0
    
    def test_enhanced_email_generation_with_sender_profile(self, sample_sender_profile):
        """Test enhanced email generation with sender profile."""
        generator = EmailGenerator(api_key="test-key")
        
        # Mock notion manager
        mock_notion_manager = Mock()
        mock_notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'Test Prospect',
            'role': 'CTO',
            'company': 'Test Company',
            'email': 'test@company.com',
            'linkedin_url': 'https://linkedin.com/in/testprospect',
            'source_url': 'https://producthunt.com/posts/test-product',
            'notes': 'Interesting AI startup',
            'product_summary': 'AI-powered analytics platform',
            'business_insights': 'Series A funded, 50 employees, growing rapidly',
            'linkedin_summary': 'Experienced CTO with background in AI and data science',
            'personalization_data': 'Focus on scalability and AI/ML expertise'
        }
        
        with patch.object(generator, 'generate_outreach_email') as mock_generate:
            mock_generate.return_value = EmailContent(
                subject="Test Subject",
                body="Test Body",
                template_used="cold_outreach",
                personalization_score=0.8,
                recipient_name="Test Prospect",
                company_name="Test Company"
            )
            
            result = generator.generate_enhanced_outreach_email(
                prospect_id="test-id",
                notion_manager=mock_notion_manager,
                sender_profile=sample_sender_profile
            )
            
            # Verify sender profile was passed to generate_outreach_email
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[1]['sender_profile'] == sample_sender_profile
    
    def test_bulk_email_generation_with_sender_profile(self, sample_sender_profile):
        """Test bulk email generation with sender profile."""
        generator = EmailGenerator(api_key="test-key")
        
        # Mock dependencies
        mock_notion_manager = Mock()
        mock_email_sender = Mock()
        
        # Mock successful email generation and sending
        with patch.object(generator, 'generate_and_send_email') as mock_generate_send:
            mock_generate_send.return_value = {
                "email_content": EmailContent(
                    subject="Test Subject",
                    body="Test Body",
                    template_used="cold_outreach",
                    personalization_score=0.8,
                    recipient_name="Test Prospect",
                    company_name="Test Company"
                ),
                "prospect_id": "test-id",
                "sent": True,
                "send_result": {"email_id": "email-123", "status": "sent"}
            }
            
            results = generator.generate_and_send_bulk_emails(
                prospect_ids=["test-id-1", "test-id-2"],
                notion_manager=mock_notion_manager,
                email_sender=mock_email_sender,
                sender_profile=sample_sender_profile
            )
            
            # Verify sender profile was passed to each email generation
            assert mock_generate_send.call_count == 2
            for call in mock_generate_send.call_args_list:
                assert call[1]['sender_profile'] == sample_sender_profile
    
    def test_load_sender_profile_markdown(self):
        """Test loading sender profile from markdown file."""
        generator = EmailGenerator(api_key="test-key")
        
        # Mock the SenderProfileManager import
        with patch('services.sender_profile_manager.SenderProfileManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            mock_profile = Mock()
            mock_manager.load_profile_from_markdown.return_value = mock_profile
            
            result = generator.load_sender_profile("profile.md")
            
            mock_manager.load_profile_from_markdown.assert_called_once_with("profile.md")
            assert result == mock_profile
    
    def test_load_sender_profile_json(self):
        """Test loading sender profile from JSON file."""
        generator = EmailGenerator(api_key="test-key")
        
        # Mock file reading and SenderProfileManager
        mock_config_data = {"name": "Test User", "current_role": "Engineer"}
        
        with patch('builtins.open', mock_open(read_data='{"name": "Test User", "current_role": "Engineer"}')):
            with patch('json.load', return_value=mock_config_data):
                with patch('services.sender_profile_manager.SenderProfileManager') as mock_manager_class:
                    mock_manager = Mock()
                    mock_manager_class.return_value = mock_manager
                    
                    mock_profile = Mock()
                    mock_manager.load_profile_from_config.return_value = mock_profile
                    
                    result = generator.load_sender_profile("profile.json")
                    
                    mock_manager.load_profile_from_config.assert_called_once_with(mock_config_data)
                    assert result == mock_profile
    
    def test_create_sender_profile_interactively(self):
        """Test interactive sender profile creation."""
        generator = EmailGenerator(api_key="test-key")
        
        with patch('services.sender_profile_manager.SenderProfileManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            mock_profile = Mock()
            mock_manager.create_profile_interactively.return_value = mock_profile
            
            result = generator.create_sender_profile_interactively()
            
            mock_manager.create_profile_interactively.assert_called_once()
            assert result == mock_profile
    
    def test_email_templates_include_sender_context(self, sample_sender_profile):
        """Test that email templates properly incorporate sender context."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test cold outreach template
        template_config = generator.templates[EmailTemplate.COLD_OUTREACH]
        system_prompt = template_config["system_prompt"]
        user_template = template_config["user_template"]
        
        # System prompt should mention sender context
        assert "sender" in system_prompt.lower()
        assert "background" in system_prompt.lower()
        assert "experience" in system_prompt.lower()
        
        # User template should include sender fields
        assert "{sender_name}" in user_template
        assert "{sender_skills}" in user_template
        assert "{sender_primary_intro}" in user_template
        assert "{sender_value_connection}" in user_template
        assert "{sender_key_achievement}" in user_template
        
        # Test that template can be formatted with sender data using proper personalization data
        prospect = Prospect(
            name="Test Prospect",
            role="CTO",
            company="Test Company",
            email="test@company.com"
        )
        
        # Get complete personalization data
        sample_data = generator._prepare_personalization_data(
            prospect=prospect,
            sender_profile=sample_sender_profile
        )
        
        try:
            formatted_template = user_template.format(**sample_data)
            assert len(formatted_template) > 0
            assert sample_sender_profile.name in formatted_template
            assert prospect.name in formatted_template
        except KeyError as e:
            pytest.fail(f"Template formatting failed due to missing key: {e}")


    # Tests for intelligent sender context matching (Task 24.2)
    
    def test_score_achievement_relevance(self, sample_sender_profile):
        """Test achievement relevance scoring algorithm."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with senior role prospect
        senior_prospect = Prospect(
            name="Alice Johnson",
            role="Senior Engineering Manager",
            company="TechCorp",
            email="alice@techcorp.com"
        )
        
        # Test leadership achievement
        leadership_achievement = "Led team of 10 engineers that reduced system latency by 60%"
        score = generator._score_achievement_relevance(leadership_achievement, senior_prospect)
        assert score > 0.5  # Should score high for senior role
        
        # Test technical achievement
        tech_achievement = "Built ML pipeline that increased user engagement by 40%"
        tech_prospect = Prospect(
            name="Bob Smith",
            role="Software Engineer",
            company="AI Startup",
            email="bob@aistartup.com"
        )
        score = generator._score_achievement_relevance(tech_achievement, tech_prospect)
        assert score > 0.3  # Should score well for technical role
    
    def test_enhanced_industry_matching(self, sample_sender_profile):
        """Test enhanced industry matching with keyword expansion."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test SaaS company with platform keywords
        saas_prospect = Prospect(
            name="Carol Wilson",
            role="Product Manager",
            company="CloudPlatform Solutions",
            email="carol@cloudplatform.com"
        )
        
        industry_match = generator._get_sender_industry_match(sample_sender_profile, saas_prospect)
        assert "SaaS" in industry_match
        
        # Test FinTech company with financial keywords
        fintech_prospect = Prospect(
            name="David Brown",
            role="CTO",
            company="PaymentTech Inc",
            email="david@paymenttech.com"
        )
        
        # Add FinTech to sender's interests for this test
        sample_sender_profile.industries_of_interest.append("FinTech")
        industry_match = generator._get_sender_industry_match(sample_sender_profile, fintech_prospect)
        assert "FinTech" in industry_match
    
    def test_enhanced_skill_matching(self, sample_sender_profile):
        """Test enhanced skill matching with scoring and categorization."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with Python developer prospect
        python_prospect = Prospect(
            name="Eve Davis",
            role="Senior Python Developer",
            company="DataCorp",
            email="eve@datacorp.com"
        )
        
        skill_match = generator._get_sender_skill_match(sample_sender_profile, python_prospect)
        assert "Python" in skill_match  # Should prioritize Python for Python developer
        
        # Test with DevOps engineer prospect
        devops_prospect = Prospect(
            name="Frank Miller",
            role="DevOps Engineer",
            company="CloudOps",
            email="frank@cloudops.com"
        )
        
        skill_match = generator._get_sender_skill_match(sample_sender_profile, devops_prospect)
        assert "AWS" in skill_match or "Docker" in skill_match  # Should include relevant DevOps skills
    
    def test_text_relevance_scoring(self, sample_sender_profile):
        """Test text relevance scoring for experience summaries."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with software engineering prospect
        engineer_prospect = Prospect(
            name="Grace Lee",
            role="Software Engineer",
            company="TechStartup",
            email="grace@techstartup.com"
        )
        
        # Test relevant experience summary
        relevant_text = "Experienced software engineer with expertise in full-stack development and cloud architecture"
        score = generator._score_text_relevance(relevant_text, engineer_prospect)
        assert score > 0.2  # Should score as relevant
        
        # Test irrelevant text
        irrelevant_text = "Marketing professional with expertise in social media campaigns"
        score = generator._score_text_relevance(irrelevant_text, engineer_prospect)
        assert score < 0.1  # Should score as less relevant
    
    def test_portfolio_relevance_selection(self, sample_sender_profile):
        """Test portfolio link relevance selection."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Henry Wilson",
            role="CTO",
            company="DevCorp",
            email="henry@devcorp.com"
        )
        
        relevant_links = generator.get_sender_portfolio_relevance(sample_sender_profile, prospect)
        assert len(relevant_links) <= 2  # Should limit to top 2 links
        assert all(link in sample_sender_profile.portfolio_links for link in relevant_links)
    
    def test_achievement_company_matching(self, sample_sender_profile):
        """Test matching achievements to specific company needs."""
        generator = EmailGenerator(api_key="test-key")
        
        startup_prospect = Prospect(
            name="Ivy Chen",
            role="Founder",
            company="EarlyStage Startup",
            email="ivy@earlystage.com"
        )
        
        product_context = {
            'business_insights': 'Early-stage startup, Series A funded, scaling rapidly',
            'product_features': 'Machine learning platform, real-time analytics'
        }
        
        matched_achievements = generator.match_sender_achievements_to_company_needs(
            sample_sender_profile, startup_prospect, product_context
        )
        
        assert len(matched_achievements) <= 3  # Should limit to top 3
        # Should prioritize achievements relevant to scaling and ML
        achievement_text = ' '.join(matched_achievements).lower()
        assert any(keyword in achievement_text for keyword in ['scaled', 'ml', 'system', 'team'])
    
    def test_comprehensive_sender_matching_integration(self, sample_sender_profile):
        """Test that all matching algorithms work together in email generation."""
        generator = EmailGenerator(api_key="test-key")
        
        # Create a prospect that should match well with the sample sender profile
        matching_prospect = Prospect(
            name="Jack Thompson",
            role="Senior Software Engineer",
            company="SaaS Platform Inc",
            email="jack@saasplatform.com"
        )
        
        # Test personalization data preparation with enhanced matching
        data = generator._prepare_personalization_data(
            prospect=matching_prospect,
            sender_profile=sample_sender_profile
        )
        
        # Verify that matching algorithms produced relevant results
        assert data['sender_relevant_experience']  # Should have relevant experience
        assert data['sender_industry_match']  # Should match SaaS industry
        assert data['sender_skill_match']  # Should have relevant skills
        
        # Check that the matches are actually relevant
        assert "SaaS" in data['sender_industry_match']
        assert any(skill in data['sender_skill_match'] for skill in ['Python', 'React', 'AWS'])
        assert len(data['sender_relevant_experience']) > 0
    
    def test_role_specific_skill_prioritization(self, sample_sender_profile):
        """Test that skills are prioritized correctly for different roles."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with data scientist prospect
        data_prospect = Prospect(
            name="Kelly Rodriguez",
            role="Data Scientist",
            company="Analytics Corp",
            email="kelly@analytics.com"
        )
        
        # Add data science skills to sender profile for this test
        sample_sender_profile.key_skills.extend(["Data Science", "Statistics", "TensorFlow"])
        
        skill_match = generator._get_sender_skill_match(sample_sender_profile, data_prospect)
        
        # Should prioritize data-related skills
        assert any(skill in skill_match for skill in ["Python", "Machine Learning", "Data Science"])
        
        # Test with product manager prospect
        pm_prospect = Prospect(
            name="Laura Kim",
            role="Product Manager",
            company="ProductCorp",
            email="laura@productcorp.com"
        )
        
        # Add product management skills
        sample_sender_profile.key_skills.extend(["Product Management", "Analytics", "User Research"])
        
        skill_match = generator._get_sender_skill_match(sample_sender_profile, pm_prospect)
        
        # Should prioritize product-related skills
        assert any(skill in skill_match for skill in ["Product Management", "Analytics"])
    
    def test_achievement_scoring_with_quantified_results(self, sample_sender_profile):
        """Test that achievements with quantified results score higher."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Mike Johnson",
            role="Engineering Manager",
            company="ScaleCorp",
            email="mike@scalecorp.com"
        )
        
        # Achievement with quantified results
        quantified_achievement = "Scaled system to handle 10M+ requests per day, reducing costs by 40%"
        score1 = generator._score_achievement_relevance(quantified_achievement, prospect)
        
        # Achievement without quantified results
        general_achievement = "Improved system performance and reduced operational costs"
        score2 = generator._score_achievement_relevance(general_achievement, prospect)
        
        assert score1 > score2  # Quantified achievement should score higher


    # Tests for enhanced email templates with sender integration (Task 24.3)
    
    def test_get_dynamic_sender_highlights(self, sample_sender_profile):
        """Test dynamic sender highlights selection based on prospect context."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with senior role prospect
        senior_prospect = Prospect(
            name="Alice Johnson",
            role="Senior Engineering Manager",
            company="TechCorp",
            email="alice@techcorp.com"
        )
        
        highlights = generator.get_dynamic_sender_highlights(sample_sender_profile, senior_prospect)
        
        assert 'primary_introduction' in highlights
        assert 'relevant_skills' in highlights
        assert 'key_achievement' in highlights
        assert 'value_connection' in highlights
        assert 'availability_note' in highlights
        
        # Should emphasize leadership for senior roles
        assert 'senior' in highlights['primary_introduction'].lower() or 'lead' in highlights['primary_introduction'].lower()
        
        # Test with individual contributor prospect
        ic_prospect = Prospect(
            name="Bob Smith",
            role="Software Engineer",
            company="DevCorp",
            email="bob@devcorp.com"
        )
        
        ic_highlights = generator.get_dynamic_sender_highlights(sample_sender_profile, ic_prospect)
        
        # Should emphasize technical skills for IC roles
        assert any(skill in ic_highlights['primary_introduction'] for skill in sample_sender_profile.key_skills[:3])
    
    def test_create_contextual_email_sections(self, sample_sender_profile):
        """Test creation of contextual email sections."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Carol Wilson",
            role="Product Manager",
            company="ProductCorp",
            email="carol@productcorp.com"
        )
        
        product_context = {
            'business_insights': 'Early-stage startup, Series A funded, scaling rapidly',
            'product_features': 'Machine learning platform, real-time analytics'
        }
        
        sections = generator.create_contextual_email_sections(sample_sender_profile, prospect, product_context)
        
        # Should have key sections
        expected_sections = ['sender_introduction', 'skill_connection', 'value_proposition']
        for section in expected_sections:
            assert section in sections
            assert len(sections[section]) > 0
        
        # Sections should be properly formatted
        assert sections['sender_introduction'].startswith("I'm")
        assert 'expertise' in sections['skill_connection'].lower()
    
    def test_enhanced_personalization_data_with_dynamic_sections(self, sample_sender_profile):
        """Test that personalization data includes dynamic sections."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="David Brown",
            role="CTO",
            company="StartupCorp",
            email="david@startupcorp.com"
        )
        
        data = generator._prepare_personalization_data(
            prospect=prospect,
            sender_profile=sample_sender_profile
        )
        
        # Should include dynamic highlights
        dynamic_fields = [
            'sender_primary_intro',
            'sender_key_achievement',
            'sender_value_connection',
            'sender_availability_note'
        ]
        
        for field in dynamic_fields:
            assert field in data
        
        # Should include contextual sections
        section_fields = [
            'sender_intro_section',
            'skill_connection_section',
            'value_prop_section'
        ]
        
        for field in section_fields:
            assert field in data
            # Sections should be properly formatted
            if data[field]:  # Only check non-empty sections
                assert len(data[field]) > 10  # Should be substantial
    
    def test_template_integration_with_sender_context(self, sample_sender_profile):
        """Test that templates properly integrate sender context."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test cold outreach template
        template_config = generator.templates[EmailTemplate.COLD_OUTREACH]
        user_template = template_config["user_template"]
        
        # Should include dynamic section placeholders
        dynamic_placeholders = [
            '{sender_intro_section}',
            '{skill_connection_section}',
            '{achievement_section}',
            '{value_prop_section}',
            '{availability_section}'
        ]
        
        for placeholder in dynamic_placeholders:
            assert placeholder in user_template
        
        # Test template formatting with sample data
        prospect = Prospect(
            name="Eve Davis",
            role="Engineering Manager",
            company="TechStartup",
            email="eve@techstartup.com"
        )
        
        data = generator._prepare_personalization_data(
            prospect=prospect,
            sender_profile=sample_sender_profile
        )
        
        # Should be able to format template without errors
        try:
            formatted_template = user_template.format(**data)
            assert len(formatted_template) > 0
            assert sample_sender_profile.name in formatted_template
            assert prospect.name in formatted_template
        except KeyError as e:
            pytest.fail(f"Template formatting failed due to missing key: {e}")
    
    def test_role_specific_template_adaptation(self, sample_sender_profile):
        """Test that templates adapt to different prospect roles."""
        generator = EmailGenerator(api_key="test-key")
        
        # Test with different role types
        roles_to_test = [
            ("Senior Software Engineer", "technical"),
            ("Engineering Manager", "leadership"),
            ("Product Manager", "product"),
            ("CTO", "executive")
        ]
        
        for role, expected_focus in roles_to_test:
            prospect = Prospect(
                name="Test Person",
                role=role,
                company="TestCorp",
                email="test@testcorp.com"
            )
            
            highlights = generator.get_dynamic_sender_highlights(sample_sender_profile, prospect)
            
            # Should adapt introduction based on role
            intro = highlights['primary_introduction'].lower()
            
            if expected_focus == "leadership":
                assert any(word in intro for word in ['senior', 'lead', 'experience', 'years'])
            elif expected_focus == "technical":
                # For technical roles, should include skills or technical terms
                assert any(skill.lower() in intro for skill in sample_sender_profile.key_skills[:3]) or 'engineer' in intro
    
    def test_product_context_influences_sender_highlighting(self, sample_sender_profile):
        """Test that product context influences how sender information is highlighted."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Frank Miller",
            role="Founder",
            company="EarlyStage",
            email="frank@earlystage.com"
        )
        
        # Test with startup context
        startup_context = {
            'business_insights': 'Early-stage startup, pre-seed funding, building MVP',
            'product_features': 'AI-powered analytics platform'
        }
        
        highlights = generator.get_dynamic_sender_highlights(sample_sender_profile, prospect, startup_context)
        
        # Should emphasize startup-relevant experience
        value_connection = highlights['value_connection'].lower()
        if 'startup' in sample_sender_profile.experience_summary.lower():
            assert 'startup' in value_connection or 'early' in value_connection
    
    def test_availability_and_contact_preferences_integration(self, sample_sender_profile):
        """Test that availability and contact preferences are naturally integrated."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Grace Lee",
            role="VP Engineering",
            company="RemoteCorp",
            email="grace@remotecorp.com"
        )
        
        sections = generator.create_contextual_email_sections(sample_sender_profile, prospect)
        
        # Should include availability information
        if 'availability_mention' in sections and sections['availability_mention']:
            availability_text = sections['availability_mention'].lower()
            assert any(word in availability_text for word in ['available', 'open', 'based', 'remote'])
    
    def test_portfolio_integration_in_templates(self, sample_sender_profile):
        """Test that portfolio links are naturally integrated into templates."""
        generator = EmailGenerator(api_key="test-key")
        
        prospect = Prospect(
            name="Henry Wilson",
            role="CTO",
            company="TechCorp",
            email="henry@techcorp.com"
        )
        
        sections = generator.create_contextual_email_sections(sample_sender_profile, prospect)
        
        # Should include portfolio reference if available
        if sample_sender_profile.portfolio_links:
            assert 'portfolio_reference' in sections
            if sections['portfolio_reference']:
                assert sample_sender_profile.portfolio_links[0] in sections['portfolio_reference']

# Helper function for mocking file operations
def mock_open(read_data=""):
    """Helper function to mock file operations."""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)