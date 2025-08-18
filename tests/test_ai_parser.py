"""
Unit tests for the AI Parser service.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from dataclasses import dataclass

from services.ai_parser import AIParser, ParseResult, ParseType, ProductInfo, BusinessMetrics
from services.openai_client_manager import CompletionResponse
from models.data_models import LinkedInProfile, TeamMember, ValidationError
from utils.config import Config


class TestAIParser(unittest.TestCase):
    """Test cases for AIParser class."""
    
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
        self.sample_linkedin_html = """
        <html>
            <div class="pv-text-details__left-panel">
                <h1>John Doe</h1>
                <div class="text-body-medium">Senior Software Engineer at TechCorp</div>
            </div>
            <section class="pv-profile-section pv-about-section">
                <p>Experienced software engineer with 8+ years in full-stack development...</p>
            </section>
            <section class="experience-section">
                <div class="pv-entity__summary-info">
                    <h3>Senior Software Engineer</h3>
                    <h4>TechCorp</h4>
                    <span>2020 - Present</span>
                </div>
                <div class="pv-entity__summary-info">
                    <h3>Software Engineer</h3>
                    <h4>StartupXYZ</h4>
                    <span>2018 - 2020</span>
                </div>
            </section>
            <section class="skills-section">
                <span>Python</span>
                <span>JavaScript</span>
                <span>React</span>
                <span>Node.js</span>
            </section>
        </html>
        """
        
        self.sample_product_content = """
        ProductHunt Launch: TaskMaster Pro
        
        TaskMaster Pro is a revolutionary project management tool that helps teams collaborate 
        more effectively and deliver projects on time. 
        
        Key Features:
        - Real-time collaboration
        - Advanced analytics
        - Custom workflows
        - Integration with 50+ tools
        
        Pricing: Starting at $9/month per user with a free tier for small teams.
        Target Market: Small to medium businesses and remote teams.
        
        Competitors include Asana, Trello, and Monday.com.
        
        The company recently raised $2M in seed funding and is growing rapidly.
        """
        
        self.sample_team_content = """
        Meet the Team:
        
        Sarah Johnson - CEO & Co-founder
        LinkedIn: https://linkedin.com/in/sarah-johnson-ceo
        
        Mike Chen - CTO & Co-founder  
        LinkedIn: https://linkedin.com/in/mike-chen-cto
        
        Emily Rodriguez - Head of Product
        LinkedIn: https://linkedin.com/in/emily-rodriguez-product
        
        David Kim - Lead Engineer
        LinkedIn: https://linkedin.com/in/david-kim-engineer
        """
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_init_with_azure_openai(self, mock_azure_openai):
        """Test AIParser initialization with Azure OpenAI."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        parser = AIParser(self.mock_config)
        
        self.assertEqual(parser.client, mock_client)
        self.assertEqual(parser.model_name, "gpt-4")
        mock_azure_openai.assert_called_once_with(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com/",
            api_version="2024-02-15-preview"
        )
    
    @patch('services.ai_parser.OpenAI')
    def test_init_with_regular_openai(self, mock_openai):
        """Test AIParser initialization with regular OpenAI."""
        self.mock_config.use_azure_openai = False
        self.mock_config.openai_api_key = "regular-openai-key"
        
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        parser = AIParser(self.mock_config)
        
        self.assertEqual(parser.client, mock_client)
        self.assertEqual(parser.model_name, "gpt-3.5-turbo")
        mock_openai.assert_called_once_with(api_key="regular-openai-key")
    
    def test_init_missing_azure_config(self):
        """Test AIParser initialization with missing Azure OpenAI configuration."""
        self.mock_config.azure_openai_api_key = None
        
        with self.assertRaises(ValueError) as context:
            AIParser(self.mock_config)
        
        self.assertIn("Azure OpenAI API key is required", str(context.exception))
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_linkedin_profile_success(self, mock_azure_openai):
        """Test successful LinkedIn profile parsing."""
        # Setup mock client and response
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "John Doe",
            "current_role": "Senior Software Engineer at TechCorp",
            "experience": [
                "Senior Software Engineer at TechCorp (2020 - Present)",
                "Software Engineer at StartupXYZ (2018 - 2020)"
            ],
            "skills": ["Python", "JavaScript", "React", "Node.js"],
            "summary": "Experienced software engineer with 8+ years in full-stack development"
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "John Doe")
        self.assertEqual(result.data.current_role, "Senior Software Engineer at TechCorp")
        self.assertEqual(len(result.data.experience), 2)
        self.assertEqual(len(result.data.skills), 4)
        self.assertGreater(result.confidence_score, 0.5)
        
        # Verify API call
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args[1]['model'], "gpt-4")
        self.assertEqual(call_args[1]['temperature'], 0.1)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_linkedin_profile_with_fallback(self, mock_azure_openai):
        """Test LinkedIn profile parsing with fallback data."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock API failure
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        fallback_data = {
            "name": "John Doe",
            "current_role": "Engineer",
            "experience": ["Previous role"],
            "skills": ["Python"],
            "summary": "Engineer"
        }
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html, fallback_data)
        
        # Should use fallback data
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "John Doe")
        self.assertEqual(result.confidence_score, 0.3)  # Lower confidence for fallback
        self.assertIn("AI parsing failed", result.error_message)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_product_info_success(self, mock_azure_openai):
        """Test successful product information parsing."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "TaskMaster Pro",
            "description": "Revolutionary project management tool for team collaboration",
            "features": ["Real-time collaboration", "Advanced analytics", "Custom workflows"],
            "pricing_model": "freemium",
            "target_market": "Small to medium businesses",
            "competitors": ["Asana", "Trello", "Monday.com"],
            "funding_status": "seed",
            "market_analysis": "Growing rapidly in the project management space"
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_product_info(self.sample_product_content)
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, ProductInfo)
        self.assertEqual(result.data.name, "TaskMaster Pro")
        self.assertEqual(len(result.data.features), 3)
        self.assertEqual(len(result.data.competitors), 3)
        self.assertEqual(result.data.pricing_model, "freemium")
        self.assertGreater(result.confidence_score, 0.5)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_structure_team_data_success(self, mock_azure_openai):
        """Test successful team data structuring."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps([
            {
                "name": "Sarah Johnson",
                "role": "CEO & Co-founder",
                "company": "TaskMaster",
                "linkedin_url": "https://linkedin.com/in/sarah-johnson-ceo"
            },
            {
                "name": "Mike Chen",
                "role": "CTO & Co-founder",
                "company": "TaskMaster",
                "linkedin_url": "https://linkedin.com/in/mike-chen-cto"
            }
        ])
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.structure_team_data(self.sample_team_content, "TaskMaster")
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, list)
        self.assertEqual(len(result.data), 2)
        
        # Check first team member
        first_member = result.data[0]
        self.assertIsInstance(first_member, TeamMember)
        self.assertEqual(first_member.name, "Sarah Johnson")
        self.assertEqual(first_member.role, "CEO & Co-founder")
        self.assertEqual(first_member.company, "TaskMaster")
        self.assertIn("linkedin.com", first_member.linkedin_url)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_extract_business_metrics_success(self, mock_azure_openai):
        """Test successful business metrics extraction."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "employee_count": 15,
            "funding_amount": "$2M seed",
            "growth_stage": "early-stage startup",
            "key_metrics": {
                "users": "10K+ active users",
                "growth_rate": "20% MoM"
            },
            "business_model": "B2B SaaS",
            "revenue_model": "subscription",
            "market_position": "Emerging player in project management"
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.extract_business_metrics(self.sample_product_content, "TaskMaster")
        
        # Verify result
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, BusinessMetrics)
        self.assertEqual(result.data.employee_count, 15)
        self.assertEqual(result.data.funding_amount, "$2M seed")
        self.assertEqual(result.data.business_model, "B2B SaaS")
        self.assertEqual(len(result.data.key_metrics), 2)
        self.assertGreater(result.confidence_score, 0.5)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_with_invalid_json_response(self, mock_azure_openai):
        """Test parsing with invalid JSON response from AI."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is not valid JSON content"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html)
        
        # Should fail gracefully
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("No valid JSON found", result.error_message)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_with_rate_limit_error(self, mock_azure_openai):
        """Test parsing with rate limit error."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Import the actual openai module to get the real exception
        import openai
        mock_client.chat.completions.create.side_effect = openai.RateLimitError(
            message="Rate limit exceeded",
            response=Mock(),
            body={}
        )
        
        parser = AIParser(self.mock_config)
        result = parser.parse_product_info(self.sample_product_content)
        
        # Should fail with rate limit error
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("Rate limit exceeded", result.error_message)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_calculate_confidence_score_linkedin(self, mock_azure_openai):
        """Test confidence score calculation for LinkedIn profiles."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        parser = AIParser(self.mock_config)
        
        # Complete data
        complete_data = {
            "name": "John Doe",
            "current_role": "Engineer",
            "experience": ["Role 1", "Role 2"],
            "skills": ["Python", "JavaScript"],
            "summary": "Professional summary"
        }
        score = parser._calculate_confidence_score(complete_data, ParseType.LINKEDIN_PROFILE)
        self.assertGreater(score, 0.8)
        
        # Minimal data
        minimal_data = {
            "name": "John Doe",
            "current_role": "Engineer",
            "experience": [],
            "skills": [],
            "summary": ""
        }
        score = parser._calculate_confidence_score(minimal_data, ParseType.LINKEDIN_PROFILE)
        self.assertAlmostEqual(score, 0.6, places=1)  # Only required fields
        
        # Empty data
        empty_data = {}
        score = parser._calculate_confidence_score(empty_data, ParseType.LINKEDIN_PROFILE)
        self.assertEqual(score, 0.0)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_calculate_confidence_score_product(self, mock_azure_openai):
        """Test confidence score calculation for product information."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        parser = AIParser(self.mock_config)
        
        # Complete data
        complete_data = {
            "name": "Product",
            "description": "Description",
            "features": ["Feature 1"],
            "pricing_model": "freemium",
            "target_market": "SMB",
            "competitors": ["Competitor 1"]
        }
        score = parser._calculate_confidence_score(complete_data, ParseType.PRODUCT_INFO)
        self.assertGreater(score, 0.8)
        
        # Only required fields
        minimal_data = {
            "name": "Product",
            "description": "Description",
            "features": [],
            "pricing_model": "",
            "target_market": "",
            "competitors": []
        }
        score = parser._calculate_confidence_score(minimal_data, ParseType.PRODUCT_INFO)
        self.assertEqual(score, 0.5)  # Only required fields
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_parse_with_retry_success_on_second_attempt(self, mock_azure_openai):
        """Test parse_with_retry succeeds on second attempt."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "Test Product",
            "description": "Test Description",
            "features": [],
            "pricing_model": "free",
            "target_market": "everyone",
            "competitors": []
        })
        
        mock_client.chat.completions.create.side_effect = [
            Exception("First attempt fails"),
            mock_response
        ]
        
        parser = AIParser(self.mock_config)
        result = parser.parse_with_retry(parser.parse_product_info, self.sample_product_content)
        
        # Should succeed on retry
        self.assertTrue(result.success)
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
    
    @patch('services.ai_parser.AzureOpenAI')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_parse_with_retry_rate_limit_backoff(self, mock_sleep, mock_azure_openai):
        """Test parse_with_retry handles rate limits with exponential backoff."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        import openai
        
        # Create a mock function that raises rate limit errors
        def mock_parse_function(*args, **kwargs):
            raise openai.RateLimitError(message="Rate limit", response=Mock(), body={})
        
        parser = AIParser(self.mock_config)
        result = parser.parse_with_retry(mock_parse_function, self.sample_product_content, max_retries=2)
        
        # Should fail after retries
        self.assertFalse(result.success)
        self.assertIn("Rate limit", result.error_message)
        
        # Should have called sleep with exponential backoff
        expected_calls = [unittest.mock.call(5), unittest.mock.call(10)]
        mock_sleep.assert_has_calls(expected_calls)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_get_parsing_stats(self, mock_azure_openai):
        """Test get_parsing_stats returns expected structure."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        parser = AIParser(self.mock_config)
        stats = parser.get_parsing_stats()
        
        # Verify structure
        self.assertIn("total_parses", stats)
        self.assertIn("successful_parses", stats)
        self.assertIn("average_confidence", stats)
        self.assertIn("parse_types", stats)
        
        # Verify parse_types structure
        parse_types = stats["parse_types"]
        self.assertIn("linkedin_profile", parse_types)
        self.assertIn("product_info", parse_types)
        self.assertIn("team_data", parse_types)
        self.assertIn("business_metrics", parse_types)


class TestProductInfo(unittest.TestCase):
    """Test cases for ProductInfo data model."""
    
    def test_product_info_creation(self):
        """Test ProductInfo object creation."""
        product = ProductInfo(
            name="Test Product",
            description="Test Description",
            features=["Feature 1", "Feature 2"],
            pricing_model="freemium",
            target_market="SMB",
            competitors=["Competitor 1"],
            funding_status="seed",
            market_analysis="Growing market"
        )
        
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(len(product.features), 2)
        self.assertEqual(len(product.competitors), 1)
    
    def test_product_info_to_dict(self):
        """Test ProductInfo to_dict conversion."""
        product = ProductInfo(
            name="Test Product",
            description="Test Description",
            features=["Feature 1"],
            pricing_model="freemium",
            target_market="SMB",
            competitors=["Competitor 1"]
        )
        
        result = product.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["name"], "Test Product")
        self.assertEqual(len(result["features"]), 1)
        self.assertIn("funding_status", result)


class TestBusinessMetrics(unittest.TestCase):
    """Test cases for BusinessMetrics data model."""
    
    def test_business_metrics_creation(self):
        """Test BusinessMetrics object creation."""
        metrics = BusinessMetrics(
            employee_count=50,
            funding_amount="$2M",
            growth_stage="seed",
            business_model="B2B SaaS"
        )
        
        self.assertEqual(metrics.employee_count, 50)
        self.assertEqual(metrics.funding_amount, "$2M")
        self.assertIsInstance(metrics.key_metrics, dict)
    
    def test_business_metrics_to_dict(self):
        """Test BusinessMetrics to_dict conversion."""
        metrics = BusinessMetrics(
            employee_count=25,
            funding_amount="$1M",
            key_metrics={"users": "1000", "revenue": "$10K MRR"}
        )
        
        result = metrics.to_dict()
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["employee_count"], 25)
        self.assertEqual(len(result["key_metrics"]), 2)


if __name__ == '__main__':
    unittest.main()