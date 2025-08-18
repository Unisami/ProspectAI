"""
Unit tests for the refactored AI Parser service using OpenAI Client Manager.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from dataclasses import dataclass

from services.ai_parser import AIParser, ParseResult, ParseType, ProductInfo, BusinessMetrics
from services.openai_client_manager import CompletionResponse
from models.data_models import LinkedInProfile, TeamMember, ValidationError
from utils.config import Config


class TestAIParserRefactored(unittest.TestCase):
    """Test cases for refactored AIParser class."""
    
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
            </section>
            <section class="skills-section">
                <span>Python</span>
                <span>JavaScript</span>
                <span>React</span>
            </section>
        </html>
        """
        
        self.sample_product_content = """
        ProductName: AI Analytics Platform
        Description: Advanced analytics platform using machine learning
        Features: Real-time analytics, ML models, Custom dashboards
        Pricing: $99/month subscription
        Target Market: Enterprise businesses
        """
        
        self.sample_team_content = """
        Team Members:
        - John Smith, CEO and Founder
        - Sarah Johnson, CTO
        - Mike Davis, Head of Engineering
        """
    
    @patch('services.ai_parser.get_client_manager')
    def test_init_with_client_manager(self, mock_get_client_manager):
        """Test AIParser initialization with client manager."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config, client_id="test_parser")
        
        self.assertEqual(parser.client_manager, self.mock_client_manager)
        self.assertEqual(parser.client_id, "test_parser")
        mock_get_client_manager.assert_called_once()
        self.mock_client_manager.configure.assert_called_once_with(self.mock_config, "test_parser")
    
    @patch('services.ai_parser.get_client_manager')
    def test_init_default_client_id(self, mock_get_client_manager):
        """Test AIParser initialization with default client ID."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        
        self.assertEqual(parser.client_id, "ai_parser")
        self.mock_client_manager.configure.assert_called_once_with(self.mock_config, "ai_parser")
    
    @patch('services.ai_parser.get_client_manager')
    def test_init_configuration_error(self, mock_get_client_manager):
        """Test AIParser initialization with configuration error."""
        mock_get_client_manager.return_value = self.mock_client_manager
        self.mock_client_manager.configure.side_effect = ValueError("Configuration failed")
        
        with self.assertRaises(ValueError):
            AIParser(self.mock_config)
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_linkedin_profile_success(self, mock_get_client_manager):
        """Test successful LinkedIn profile parsing."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content='{"name": "John Doe", "current_role": "Senior Software Engineer at TechCorp", "experience": ["Senior Software Engineer at TechCorp (2020 - Present)"], "skills": ["Python", "JavaScript", "React"], "summary": "Experienced software engineer with 8+ years in full-stack development..."}',
            model="gpt-4",
            usage={"total_tokens": 150},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "John Doe")
        self.assertEqual(result.data.current_role, "Senior Software Engineer at TechCorp")
        self.assertGreater(result.confidence_score, 0)
        self.mock_client_manager.make_completion.assert_called_once()
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_linkedin_profile_api_error(self, mock_get_client_manager):
        """Test LinkedIn profile parsing with API error."""
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
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("API connection error", result.error_message)
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_linkedin_profile_invalid_json(self, mock_get_client_manager):
        """Test LinkedIn profile parsing with invalid JSON response."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock response with invalid JSON
        mock_response = CompletionResponse(
            content='{"name": "John Doe", "current_role": "Engineer", invalid json}',
            model="gpt-4",
            usage={"total_tokens": 100},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("Expecting property name", result.error_message)
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_linkedin_profile_with_fallback(self, mock_get_client_manager):
        """Test LinkedIn profile parsing with fallback data."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock error response
        mock_response = CompletionResponse(
            content="",
            model="gpt-4",
            usage={},
            finish_reason="error",
            success=False,
            error_message="API error"
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        # Provide fallback data
        fallback_data = {
            "name": "Fallback Name",
            "current_role": "Fallback Role",
            "experience": [],
            "skills": [],
            "summary": ""
        }
        
        parser = AIParser(self.mock_config)
        result = parser.parse_linkedin_profile(self.sample_linkedin_html, fallback_data)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "Fallback Name")
        self.assertEqual(result.confidence_score, 0.3)  # Lower confidence for fallback
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_product_info_success(self, mock_get_client_manager):
        """Test successful product information parsing."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content='{"name": "AI Analytics Platform", "description": "Advanced analytics platform using machine learning", "features": ["Real-time analytics", "ML models", "Custom dashboards"], "pricing_model": "subscription", "target_market": "Enterprise businesses", "competitors": ["Tableau", "PowerBI"], "funding_status": "Series A", "market_analysis": "Growing market with high demand"}',
            model="gpt-4",
            usage={"total_tokens": 200},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.parse_product_info(self.sample_product_content)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, ProductInfo)
        self.assertEqual(result.data.name, "AI Analytics Platform")
        self.assertEqual(result.data.pricing_model, "subscription")
        self.assertGreater(len(result.data.features), 0)
        self.assertGreater(result.confidence_score, 0)
    
    @patch('services.ai_parser.get_client_manager')
    def test_structure_team_data_success(self, mock_get_client_manager):
        """Test successful team data structuring."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content='[{"name": "John Smith", "role": "CEO and Founder", "company": "TestCorp", "linkedin_url": null}, {"name": "Sarah Johnson", "role": "CTO", "company": "TestCorp", "linkedin_url": null}, {"name": "Mike Davis", "role": "Head of Engineering", "company": "TestCorp", "linkedin_url": null}]',
            model="gpt-4",
            usage={"total_tokens": 180},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.structure_team_data(self.sample_team_content, "TestCorp")
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, list)
        self.assertEqual(len(result.data), 3)
        self.assertIsInstance(result.data[0], TeamMember)
        self.assertEqual(result.data[0].name, "John Smith")
        self.assertEqual(result.data[0].role, "CEO and Founder")
        self.assertGreater(result.confidence_score, 0)
    
    @patch('services.ai_parser.get_client_manager')
    def test_extract_business_metrics_success(self, mock_get_client_manager):
        """Test successful business metrics extraction."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        # Mock successful completion response
        mock_response = CompletionResponse(
            content='{"employee_count": 50, "funding_amount": "$2.5M Series A", "growth_stage": "early-stage startup", "key_metrics": {"users": "10K+ active users", "revenue": "ARR $1M"}, "business_model": "B2B SaaS", "revenue_model": "subscription-based", "market_position": "Emerging player in analytics space"}',
            model="gpt-4",
            usage={"total_tokens": 160},
            finish_reason="stop",
            success=True
        )
        self.mock_client_manager.make_completion.return_value = mock_response
        
        parser = AIParser(self.mock_config)
        result = parser.extract_business_metrics("Company data with metrics", "TestCorp")
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, BusinessMetrics)
        self.assertEqual(result.data.employee_count, 50)
        self.assertEqual(result.data.funding_amount, "$2.5M Series A")
        self.assertEqual(result.data.business_model, "B2B SaaS")
        self.assertGreater(result.confidence_score, 0)
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_with_retry_success_on_second_attempt(self, mock_get_client_manager):
        """Test parse_with_retry succeeds on second attempt."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        
        # Mock function that fails first time, succeeds second time
        mock_parse_function = Mock()
        mock_parse_function.side_effect = [
            ParseResult(success=False, data=None, error_message="First attempt failed"),
            ParseResult(success=True, data="Success", error_message=None)
        ]
        
        result = parser.parse_with_retry(mock_parse_function, "test_arg", max_retries=2)
        
        self.assertTrue(result.success)
        self.assertEqual(result.data, "Success")
        self.assertEqual(mock_parse_function.call_count, 2)
    
    @patch('services.ai_parser.get_client_manager')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_parse_with_retry_rate_limit_backoff(self, mock_sleep, mock_get_client_manager):
        """Test parse_with_retry handles rate limits with exponential backoff."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        
        # Mock function that raises rate limit errors
        mock_parse_function = Mock()
        mock_parse_function.side_effect = [
            Exception("Rate limit exceeded"),
            Exception("Rate limit exceeded"),
            ParseResult(success=True, data="Success", error_message=None)
        ]
        
        result = parser.parse_with_retry(mock_parse_function, "test_arg", max_retries=2)
        
        self.assertTrue(result.success)
        self.assertEqual(result.data, "Success")
        self.assertEqual(mock_parse_function.call_count, 3)
        # Verify exponential backoff was applied
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(5)  # First retry: 2^0 * 5 = 5
        mock_sleep.assert_any_call(10)  # Second retry: 2^1 * 5 = 10
    
    @patch('services.ai_parser.get_client_manager')
    def test_parse_with_retry_max_retries_exceeded(self, mock_get_client_manager):
        """Test parse_with_retry when max retries are exceeded."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        
        # Mock function that always fails
        mock_parse_function = Mock()
        mock_parse_function.side_effect = Exception("Persistent error")
        
        result = parser.parse_with_retry(mock_parse_function, "test_arg", max_retries=1)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("All parsing attempts failed", result.error_message)
        self.assertEqual(mock_parse_function.call_count, 2)  # Initial + 1 retry
    
    @patch('services.ai_parser.get_client_manager')
    def test_calculate_confidence_score_linkedin(self, mock_get_client_manager):
        """Test confidence score calculation for LinkedIn profiles."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        
        # Test with complete data
        complete_data = {
            "name": "John Doe",
            "current_role": "Software Engineer",
            "experience": ["Role 1", "Role 2"],
            "skills": ["Python", "JavaScript"],
            "summary": "Professional summary"
        }
        score = parser._calculate_confidence_score(complete_data, ParseType.LINKEDIN_PROFILE)
        self.assertGreater(score, 0.8)  # Should be high confidence
        
        # Test with minimal data
        minimal_data = {
            "name": "John Doe",
            "current_role": "",
            "experience": [],
            "skills": [],
            "summary": ""
        }
        score = parser._calculate_confidence_score(minimal_data, ParseType.LINKEDIN_PROFILE)
        self.assertLess(score, 0.5)  # Should be lower confidence
    
    @patch('services.ai_parser.get_client_manager')
    def test_get_parsing_stats(self, mock_get_client_manager):
        """Test get_parsing_stats returns expected structure."""
        mock_get_client_manager.return_value = self.mock_client_manager
        
        parser = AIParser(self.mock_config)
        stats = parser.get_parsing_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn("total_parses", stats)
        self.assertIn("successful_parses", stats)
        self.assertIn("average_confidence", stats)
        self.assertIn("parse_types", stats)
        self.assertIsInstance(stats["parse_types"], dict)


class TestProductInfoRefactored(unittest.TestCase):
    """Test cases for ProductInfo data model."""
    
    def test_product_info_creation(self):
        """Test ProductInfo object creation."""
        product = ProductInfo(
            name="Test Product",
            description="Test description",
            features=["Feature 1", "Feature 2"],
            pricing_model="subscription",
            target_market="Enterprise",
            competitors=["Competitor 1"],
            funding_status="Series A",
            market_analysis="Growing market"
        )
        
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.pricing_model, "subscription")
        self.assertEqual(len(product.features), 2)
        self.assertEqual(len(product.competitors), 1)
    
    def test_product_info_to_dict(self):
        """Test ProductInfo to_dict conversion."""
        product = ProductInfo(
            name="Test Product",
            description="Test description",
            features=["Feature 1"],
            pricing_model="subscription",
            target_market="Enterprise",
            competitors=["Competitor 1"]
        )
        
        product_dict = product.to_dict()
        
        self.assertIsInstance(product_dict, dict)
        self.assertEqual(product_dict["name"], "Test Product")
        self.assertEqual(product_dict["pricing_model"], "subscription")
        self.assertIn("features", product_dict)
        self.assertIn("competitors", product_dict)


class TestBusinessMetricsRefactored(unittest.TestCase):
    """Test cases for BusinessMetrics data model."""
    
    def test_business_metrics_creation(self):
        """Test BusinessMetrics object creation."""
        metrics = BusinessMetrics(
            employee_count=50,
            funding_amount="$2M",
            growth_stage="early-stage",
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
            key_metrics={"users": "1000"}
        )
        
        metrics_dict = metrics.to_dict()
        
        self.assertIsInstance(metrics_dict, dict)
        self.assertEqual(metrics_dict["employee_count"], 25)
        self.assertEqual(metrics_dict["funding_amount"], "$1M")
        self.assertIn("key_metrics", metrics_dict)


if __name__ == '__main__':
    unittest.main()