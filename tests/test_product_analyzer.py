"""
Unit tests for the Product Analyzer service.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from services.product_analyzer import (
    ProductAnalyzer, Feature, PricingInfo, MarketAnalysis, 
    ComprehensiveProductInfo, RateLimiter
)
from services.ai_parser import ProductInfo, ParseResult
from utils.config import Config
from models.data_models import ValidationError


class TestFeature(unittest.TestCase):
    """Test cases for Feature data model."""
    
    def test_feature_creation(self):
        """Test creating a Feature object."""
        feature = Feature(
            name="Real-time Analytics",
            description="Get insights in real-time",
            category="Analytics"
        )
        
        self.assertEqual(feature.name, "Real-time Analytics")
        self.assertEqual(feature.description, "Get insights in real-time")
        self.assertEqual(feature.category, "Analytics")
    
    def test_feature_to_dict(self):
        """Test Feature to_dict method."""
        feature = Feature(
            name="API Integration",
            description="Connect with external APIs",
            category="Integration"
        )
        
        expected_dict = {
            'name': "API Integration",
            'description': "Connect with external APIs",
            'category': "Integration"
        }
        
        self.assertEqual(feature.to_dict(), expected_dict)


class TestPricingInfo(unittest.TestCase):
    """Test cases for PricingInfo data model."""
    
    def test_pricing_info_creation(self):
        """Test creating a PricingInfo object."""
        pricing = PricingInfo(
            model="freemium",
            tiers=[{"name": "Free", "price": "$0"}],
            currency="USD",
            billing_cycles=["monthly", "yearly"]
        )
        
        self.assertEqual(pricing.model, "freemium")
        self.assertEqual(len(pricing.tiers), 1)
        self.assertEqual(pricing.currency, "USD")
        self.assertEqual(pricing.billing_cycles, ["monthly", "yearly"])
    
    def test_pricing_info_default_billing_cycles(self):
        """Test PricingInfo with default billing cycles."""
        pricing = PricingInfo(
            model="subscription",
            tiers=[]
        )
        
        self.assertEqual(pricing.billing_cycles, [])
    
    def test_pricing_info_to_dict(self):
        """Test PricingInfo to_dict method."""
        pricing = PricingInfo(
            model="subscription",
            tiers=[{"name": "Pro", "price": "$10"}],
            currency="EUR"
        )
        
        expected_dict = {
            'model': "subscription",
            'tiers': [{"name": "Pro", "price": "$10"}],
            'currency': "EUR",
            'billing_cycles': []
        }
        
        self.assertEqual(pricing.to_dict(), expected_dict)


class TestMarketAnalysis(unittest.TestCase):
    """Test cases for MarketAnalysis data model."""
    
    def test_market_analysis_creation(self):
        """Test creating a MarketAnalysis object."""
        analysis = MarketAnalysis(
            target_market="B2B SaaS",
            market_size="$10B",
            competitors=["Competitor1", "Competitor2"],
            competitive_advantages=["AI-powered", "Real-time"],
            market_position="Early stage",
            growth_potential="High"
        )
        
        self.assertEqual(analysis.target_market, "B2B SaaS")
        self.assertEqual(analysis.market_size, "$10B")
        self.assertEqual(len(analysis.competitors), 2)
        self.assertEqual(len(analysis.competitive_advantages), 2)
    
    def test_market_analysis_defaults(self):
        """Test MarketAnalysis with default values."""
        analysis = MarketAnalysis(target_market="B2C")
        
        self.assertEqual(analysis.competitors, [])
        self.assertEqual(analysis.competitive_advantages, [])
        self.assertEqual(analysis.market_position, "")
    
    def test_market_analysis_to_dict(self):
        """Test MarketAnalysis to_dict method."""
        analysis = MarketAnalysis(
            target_market="Enterprise",
            competitors=["CompA", "CompB"]
        )
        
        result_dict = analysis.to_dict()
        
        self.assertEqual(result_dict['target_market'], "Enterprise")
        self.assertEqual(result_dict['competitors'], ["CompA", "CompB"])
        self.assertIn('market_size', result_dict)
        self.assertIn('competitive_advantages', result_dict)


class TestComprehensiveProductInfo(unittest.TestCase):
    """Test cases for ComprehensiveProductInfo data model."""
    
    def setUp(self):
        """Set up test data."""
        self.basic_info = ProductInfo(
            name="Test Product",
            description="A test product",
            features=[],
            pricing_model="freemium",
            target_market="Developers",
            competitors=[]
        )
        
        self.features = [
            Feature("Feature1", "Description1"),
            Feature("Feature2", "Description2")
        ]
        
        self.pricing = PricingInfo(
            model="freemium",
            tiers=[{"name": "Free", "price": "$0"}]
        )
        
        self.market_analysis = MarketAnalysis(
            target_market="Developers"
        )
    
    def test_comprehensive_product_info_creation(self):
        """Test creating a ComprehensiveProductInfo object."""
        info = ComprehensiveProductInfo(
            basic_info=self.basic_info,
            features=self.features,
            pricing=self.pricing,
            market_analysis=self.market_analysis,
            team_size=10
        )
        
        self.assertEqual(info.basic_info.name, "Test Product")
        self.assertEqual(len(info.features), 2)
        self.assertEqual(info.pricing.model, "freemium")
        self.assertEqual(info.team_size, 10)
    
    def test_comprehensive_product_info_to_dict(self):
        """Test ComprehensiveProductInfo to_dict method."""
        launch_date = datetime.now()
        
        info = ComprehensiveProductInfo(
            basic_info=self.basic_info,
            features=self.features,
            pricing=self.pricing,
            market_analysis=self.market_analysis,
            launch_date=launch_date
        )
        
        result_dict = info.to_dict()
        
        self.assertIn('basic_info', result_dict)
        self.assertIn('features', result_dict)
        self.assertIn('pricing', result_dict)
        self.assertIn('market_analysis', result_dict)
        self.assertEqual(result_dict['launch_date'], launch_date.isoformat())


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter."""
    
    @patch('services.product_analyzer.time.time')
    @patch('services.product_analyzer.time.sleep')
    def test_rate_limiter_waits_when_needed(self, mock_sleep, mock_time):
        """Test that rate limiter waits when requests are too frequent."""
        # Set up time sequence: current time when checking, then time after setting last_request_time
        mock_time.side_effect = [1.0, 3.0]  # Current time is 1.0, then 3.0 after sleep
        
        limiter = RateLimiter(delay=2.0)
        limiter.last_request_time = 0.0  # Set initial time to 0
        limiter.wait_if_needed()
        
        mock_sleep.assert_called_once_with(1.0)  # Should sleep for 1 second (2.0 - 1.0)
    
    @patch('services.product_analyzer.time.time')
    @patch('services.product_analyzer.time.sleep')
    def test_rate_limiter_no_wait_when_enough_time_passed(self, mock_sleep, mock_time):
        """Test that rate limiter doesn't wait when enough time has passed."""
        mock_time.side_effect = [3.0, 3.0]  # Current time is 3.0, enough time has passed
        
        limiter = RateLimiter(delay=2.0)
        limiter.last_request_time = 0.0  # Set initial time to 0
        limiter.wait_if_needed()
        
        mock_sleep.assert_not_called()


class TestProductAnalyzer(unittest.TestCase):
    """Test cases for ProductAnalyzer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(
            notion_token="test_token",
            hunter_api_key="test_hunter_key",
            openai_api_key="test_openai_key",
            use_azure_openai=True,
            azure_openai_api_key="test_azure_key",
            azure_openai_endpoint="https://test.openai.azure.com/",
            scraping_delay=1.0
        )
    
    @patch('services.product_analyzer.AIParser')
    def test_product_analyzer_initialization(self, mock_ai_parser):
        """Test ProductAnalyzer initialization."""
        mock_ai_parser.return_value = Mock()
        
        analyzer = ProductAnalyzer(self.config)
        
        self.assertEqual(analyzer.config, self.config)
        self.assertIsNotNone(analyzer.rate_limiter)
        self.assertIsNotNone(analyzer.session)
        self.assertTrue(analyzer.use_ai_parsing)
    
    @patch('services.product_analyzer.AIParser')
    def test_product_analyzer_initialization_without_ai(self, mock_ai_parser):
        """Test ProductAnalyzer initialization when AI parser fails."""
        mock_ai_parser.side_effect = Exception("AI parser failed")
        
        analyzer = ProductAnalyzer(self.config)
        
        self.assertFalse(analyzer.use_ai_parsing)
        self.assertIsNone(analyzer.ai_parser)
    
    @patch('services.product_analyzer.ProductAnalyzer._extract_basic_product_info')
    @patch('services.product_analyzer.ProductAnalyzer.extract_features')
    @patch('services.product_analyzer.ProductAnalyzer.get_pricing_info')
    @patch('services.product_analyzer.ProductAnalyzer.analyze_market_position')
    @patch('services.product_analyzer.ProductAnalyzer._gather_additional_context')
    @patch('services.product_analyzer.AIParser')
    def test_analyze_product_success(self, mock_ai_parser, mock_context, mock_market, 
                                   mock_pricing, mock_features, mock_basic):
        """Test successful product analysis."""
        # Setup mocks
        mock_ai_parser.return_value = Mock()
        
        basic_info = ProductInfo(
            name="Test Product",
            description="Test description",
            features=[],
            pricing_model="freemium",
            target_market="Developers",
            competitors=[]
        )
        
        features = [Feature("Feature1", "Description1")]
        pricing = PricingInfo(model="freemium", tiers=[])
        market_analysis = MarketAnalysis(target_market="Developers")
        additional_context = {"team_size": 5}
        
        mock_basic.return_value = basic_info
        mock_features.return_value = features
        mock_pricing.return_value = pricing
        mock_market.return_value = market_analysis
        mock_context.return_value = additional_context
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer.analyze_product("https://example.com/product", "https://example.com")
        
        self.assertIsInstance(result, ComprehensiveProductInfo)
        self.assertEqual(result.basic_info.name, "Test Product")
        self.assertEqual(len(result.features), 1)
        self.assertEqual(result.team_size, 5)
    
    @patch('services.product_analyzer.ProductAnalyzer._scrape_page_content')
    @patch('services.product_analyzer.AIParser')
    def test_extract_basic_product_info_with_ai(self, mock_ai_parser, mock_scrape):
        """Test basic product info extraction with AI parsing."""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_parser.return_value = mock_ai_instance
        
        mock_scrape.return_value = "<html><title>Test Product</title></html>"
        
        product_info = ProductInfo(
            name="Test Product",
            description="AI extracted description",
            features=[],
            pricing_model="subscription",
            target_market="B2B",
            competitors=[]
        )
        
        parse_result = ParseResult(
            success=True,
            data=product_info,
            confidence_score=0.9
        )
        
        mock_ai_instance.parse_product_info.return_value = parse_result
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._extract_basic_product_info("https://example.com")
        
        self.assertEqual(result.name, "Test Product")
        self.assertEqual(result.description, "AI extracted description")
        mock_ai_instance.parse_product_info.assert_called_once()
    
    @patch('services.product_analyzer.ProductAnalyzer._scrape_page_content')
    @patch('services.product_analyzer.AIParser')
    def test_extract_basic_product_info_fallback(self, mock_ai_parser, mock_scrape):
        """Test basic product info extraction with fallback when AI fails."""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_parser.return_value = mock_ai_instance
        
        mock_scrape.return_value = """
        <html>
            <head>
                <title>Fallback Product</title>
                <meta name="description" content="Fallback description">
            </head>
        </html>
        """
        
        parse_result = ParseResult(
            success=False,
            data=None,
            error_message="AI parsing failed"
        )
        
        mock_ai_instance.parse_product_info.return_value = parse_result
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._extract_basic_product_info("https://example.com")
        
        self.assertEqual(result.name, "Fallback Product")
        self.assertEqual(result.description, "Fallback description")
    
    @patch('services.product_analyzer.ProductAnalyzer._extract_features_from_url')
    @patch('services.product_analyzer.AIParser')
    def test_extract_features(self, mock_ai_parser, mock_extract):
        """Test feature extraction."""
        mock_ai_parser.return_value = Mock()
        
        features = [
            Feature("Feature1", "Description1"),
            Feature("Feature2", "Description2")
        ]
        
        mock_extract.side_effect = [features[:1], features[1:]]  # Product page, then website
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer.extract_features("https://product.com", "https://company.com")
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].name, "Feature1")
        self.assertEqual(result[1].name, "Feature2")
    
    @patch('services.product_analyzer.ProductAnalyzer._extract_pricing_from_url')
    @patch('services.product_analyzer.AIParser')
    def test_get_pricing_info(self, mock_ai_parser, mock_extract):
        """Test pricing info extraction."""
        mock_ai_parser.return_value = Mock()
        
        pricing = PricingInfo(
            model="subscription",
            tiers=[{"name": "Pro", "price": "$10"}]
        )
        
        mock_extract.return_value = pricing
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer.get_pricing_info("https://product.com", "https://company.com")
        
        self.assertEqual(result.model, "subscription")
        self.assertEqual(len(result.tiers), 1)
    
    @patch('services.product_analyzer.ProductAnalyzer._analyze_market_with_ai')
    @patch('services.product_analyzer.ProductAnalyzer._gather_market_content')
    @patch('services.product_analyzer.AIParser')
    def test_analyze_market_position_with_ai(self, mock_ai_parser, mock_gather, mock_analyze):
        """Test market position analysis with AI."""
        mock_ai_parser.return_value = Mock()
        
        product_info = ProductInfo(
            name="Test Product",
            description="Test description",
            features=[],
            pricing_model="freemium",
            target_market="Developers",
            competitors=["Competitor1"]
        )
        
        mock_gather.return_value = "Market content"
        
        market_analysis = MarketAnalysis(
            target_market="Developers",
            competitors=["Competitor1", "Competitor2"],
            market_position="Strong position"
        )
        
        mock_analyze.return_value = market_analysis
        
        analyzer = ProductAnalyzer(self.config)
        analyzer.use_ai_parsing = True
        result = analyzer.analyze_market_position(product_info, "https://company.com")
        
        self.assertEqual(result.target_market, "Developers")
        self.assertEqual(len(result.competitors), 2)
        self.assertEqual(result.market_position, "Strong position")
    
    @patch('services.product_analyzer.webdriver.Chrome')
    @patch('services.product_analyzer.AIParser')
    def test_scrape_page_content_selenium(self, mock_ai_parser, mock_webdriver):
        """Test page content scraping with Selenium."""
        mock_ai_parser.return_value = Mock()
        
        # Setup mock driver
        mock_driver = Mock()
        mock_driver.page_source = "<html><body>Test content</body></html>"
        mock_webdriver.return_value = mock_driver
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._scrape_page_content("https://example.com")
        
        self.assertEqual(result, "<html><body>Test content</body></html>")
        mock_driver.get.assert_called_once_with("https://example.com")
        mock_driver.quit.assert_called_once()
    
    @patch('services.product_analyzer.webdriver.Chrome')
    @patch('services.product_analyzer.requests.Session.get')
    @patch('services.product_analyzer.AIParser')
    def test_scrape_page_content_fallback_to_requests(self, mock_ai_parser, mock_get, mock_webdriver):
        """Test page content scraping fallback to requests when Selenium fails."""
        mock_ai_parser.return_value = Mock()
        
        # Make Selenium fail
        mock_webdriver.side_effect = Exception("Selenium failed")
        
        # Setup requests mock
        mock_response = Mock()
        mock_response.text = "<html><body>Requests content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._scrape_page_content("https://example.com")
        
        self.assertEqual(result, "<html><body>Requests content</body></html>")
        mock_get.assert_called_once()
    
    @patch('services.product_analyzer.AIParser')
    def test_extract_basic_info_fallback(self, mock_ai_parser):
        """Test basic info extraction fallback method."""
        mock_ai_parser.return_value = Mock()
        
        content = """
        <html>
            <head>
                <title>Fallback Product - Best Tool Ever</title>
                <meta name="description" content="This is a great product for developers">
            </head>
        </html>
        """
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._extract_basic_info_fallback(content, "https://example.com")
        
        self.assertEqual(result.name, "Fallback Product - Best Tool Ever")
        self.assertEqual(result.description, "This is a great product for developers")
        self.assertEqual(result.pricing_model, "unknown")
    
    @patch('services.product_analyzer.AIParser')
    def test_extract_features_traditional(self, mock_ai_parser):
        """Test traditional feature extraction method."""
        mock_ai_parser.return_value = Mock()
        
        content = """
        <html>
            <body>
                <ul>
                    <li>Real-time analytics dashboard</li>
                    <li>Advanced reporting capabilities</li>
                    <li>API integration support</li>
                    <li>Custom alerts and notifications</li>
                </ul>
            </body>
        </html>
        """
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._extract_features_traditional(content)
        
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], Feature)
        self.assertIn("Real-time analytics", result[0].name)
    
    @patch('services.product_analyzer.AIParser')
    def test_extract_pricing_traditional(self, mock_ai_parser):
        """Test traditional pricing extraction method."""
        mock_ai_parser.return_value = Mock()
        
        content = """
        <html>
            <body>
                <p>Our pricing is simple: free tier available, premium at $10/month</p>
                <p>We offer monthly and yearly subscription options</p>
            </body>
        </html>
        """
        
        analyzer = ProductAnalyzer(self.config)
        result = analyzer._extract_pricing_traditional(content)
        
        self.assertEqual(result.model, "freemium")
        self.assertEqual(result.currency, "USD")


if __name__ == '__main__':
    unittest.main()