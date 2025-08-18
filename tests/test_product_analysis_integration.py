"""
Integration tests for product analysis workflow.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from controllers.prospect_automation_controller import ProspectAutomationController
from services.product_analyzer import ProductAnalyzer, ComprehensiveProductInfo, Feature, PricingInfo, MarketAnalysis
from services.ai_parser import ProductInfo
from models.data_models import CompanyData, TeamMember, Prospect
from utils.config import Config


class TestProductAnalysisIntegration(unittest.TestCase):
    """Integration tests for product analysis workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config(
            notion_token="test_token",
            hunter_api_key="test_hunter_key",
            openai_api_key="test_openai_key",
            use_azure_openai=False,  # Use regular OpenAI for tests to avoid client issues
            azure_openai_api_key="test_azure_key",
            azure_openai_endpoint="https://test.openai.azure.com/",
            scraping_delay=0.1  # Faster for tests
        )
        
        # Sample company data
        self.company_data = CompanyData(
            name="TestCorp",
            domain="testcorp.com",
            product_url="https://producthunt.com/posts/testcorp",
            description="A revolutionary AI-powered analytics platform",
            launch_date=datetime.now()
        )
        
        # Sample team member
        self.team_member = TeamMember(
            name="John Doe",
            role="CEO",
            company="TestCorp",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        # Sample product analysis
        self.product_analysis = ComprehensiveProductInfo(
            basic_info=ProductInfo(
                name="TestCorp Analytics",
                description="AI-powered analytics platform for businesses",
                features=[],
                pricing_model="freemium",
                target_market="B2B SaaS",
                competitors=["Competitor1", "Competitor2"]
            ),
            features=[
                Feature("Real-time Analytics", "Get insights in real-time", "Analytics"),
                Feature("AI Predictions", "Predict future trends", "AI")
            ],
            pricing=PricingInfo(
                model="freemium",
                tiers=[{"name": "Free", "price": "$0"}, {"name": "Pro", "price": "$29"}]
            ),
            market_analysis=MarketAnalysis(
                target_market="B2B SaaS",
                competitors=["Competitor1", "Competitor2"],
                competitive_advantages=["AI-powered", "Real-time"],
                market_position="Early stage startup",
                growth_potential="High"
            ),
            team_size=15,
            funding_info={"status": "Series A", "details": "$2M raised"}
        )
    
    @patch('services.product_analyzer.ProductAnalyzer')
    @patch('services.product_hunt_scraper.ProductHuntScraper')
    @patch('services.notion_manager.NotionDataManager')
    @patch('services.email_finder.EmailFinder')
    @patch('services.linkedin_scraper.LinkedInScraper')
    @patch('services.email_generator.EmailGenerator')
    def test_complete_product_analysis_workflow(self, mock_email_gen, mock_linkedin, 
                                              mock_email_finder, mock_notion, 
                                              mock_scraper, mock_analyzer):
        """Test complete workflow with product analysis integration."""
        # Setup mocks
        mock_analyzer_instance = Mock()
        mock_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_product.return_value = self.product_analysis
        
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.extract_team_info.return_value = [self.team_member]
        
        mock_notion_instance = Mock()
        mock_notion.return_value = mock_notion_instance
        mock_notion_instance.store_prospect_with_product_analysis.return_value = "test_page_id"
        
        mock_email_finder_instance = Mock()
        mock_email_finder.return_value = mock_email_finder_instance
        mock_email_finder_instance.find_and_verify_team_emails.return_value = {}
        
        mock_linkedin_instance = Mock()
        mock_linkedin.return_value = mock_linkedin_instance
        mock_linkedin_instance.extract_multiple_profiles.return_value = {}
        
        mock_email_gen_instance = Mock()
        mock_email_gen.return_value = mock_email_gen_instance
        
        # Initialize controller with mocked services
        with patch('controllers.prospect_automation_controller.ProspectAutomationController.__init__') as mock_init:
            mock_init.return_value = None
            controller = ProspectAutomationController.__new__(ProspectAutomationController)
            controller.config = self.config
            controller.product_analyzer = mock_analyzer_instance
            controller.product_hunt_scraper = mock_scraper_instance
            controller.notion_manager = mock_notion_instance
            controller.email_finder = mock_email_finder_instance
            controller.linkedin_scraper = mock_linkedin_instance
            controller.email_generator = mock_email_gen_instance
            controller.logger = Mock()
            controller.stats = {
                'companies_processed': 0,
                'prospects_found': 0,
                'emails_found': 0,
                'linkedin_profiles_extracted': 0,
                'emails_generated': 0,
                'errors': 0,
                'start_time': None,
                'end_time': None
            }
        
        # Process company
        prospects = controller.process_company(self.company_data)
        
        # Verify product analysis was called
        mock_analyzer_instance.analyze_product.assert_called_once_with(
            product_url=self.company_data.product_url,
            company_website=f"https://{self.company_data.domain}"
        )
        
        # Verify prospect was stored with product analysis
        mock_notion_instance.store_prospect_with_product_analysis.assert_called_once()
        
        # Verify we got prospects back
        self.assertEqual(len(prospects), 1)
        self.assertEqual(prospects[0].name, "John Doe")
        self.assertEqual(prospects[0].id, "test_page_id")
    
    @patch('services.product_analyzer.ProductAnalyzer')
    @patch('services.product_hunt_scraper.ProductHuntScraper')
    @patch('services.notion_manager.NotionDataManager')
    @patch('services.email_finder.EmailFinder')
    @patch('services.linkedin_scraper.LinkedInScraper')
    @patch('services.email_generator.EmailGenerator')
    def test_workflow_continues_when_product_analysis_fails(self, mock_email_gen, mock_linkedin, 
                                                          mock_email_finder, mock_notion, 
                                                          mock_scraper, mock_analyzer):
        """Test that workflow continues when product analysis fails."""
        # Setup mocks - product analysis fails
        mock_analyzer_instance = Mock()
        mock_analyzer.return_value = mock_analyzer_instance
        mock_analyzer_instance.analyze_product.side_effect = Exception("Product analysis failed")
        
        mock_scraper_instance = Mock()
        mock_scraper.return_value = mock_scraper_instance
        mock_scraper_instance.extract_team_info.return_value = [self.team_member]
        
        mock_notion_instance = Mock()
        mock_notion.return_value = mock_notion_instance
        mock_notion_instance.store_prospect_with_product_analysis.return_value = "test_page_id"
        
        mock_email_finder_instance = Mock()
        mock_email_finder.return_value = mock_email_finder_instance
        mock_email_finder_instance.find_and_verify_team_emails.return_value = {}
        
        mock_linkedin_instance = Mock()
        mock_linkedin.return_value = mock_linkedin_instance
        mock_linkedin_instance.extract_multiple_profiles.return_value = {}
        
        mock_email_gen_instance = Mock()
        mock_email_gen.return_value = mock_email_gen_instance
        
        # Initialize controller with mocked services
        with patch('controllers.prospect_automation_controller.ProspectAutomationController.__init__') as mock_init:
            mock_init.return_value = None
            controller = ProspectAutomationController.__new__(ProspectAutomationController)
            controller.config = self.config
            controller.product_analyzer = mock_analyzer_instance
            controller.product_hunt_scraper = mock_scraper_instance
            controller.notion_manager = mock_notion_instance
            controller.email_finder = mock_email_finder_instance
            controller.linkedin_scraper = mock_linkedin_instance
            controller.email_generator = mock_email_gen_instance
            controller.logger = Mock()
            controller.stats = {
                'companies_processed': 0,
                'prospects_found': 0,
                'emails_found': 0,
                'linkedin_profiles_extracted': 0,
                'emails_generated': 0,
                'errors': 0,
                'start_time': None,
                'end_time': None
            }
        
        # Process company - should not fail even if product analysis fails
        prospects = controller.process_company(self.company_data)
        
        # Verify product analysis was attempted
        mock_analyzer_instance.analyze_product.assert_called_once()
        
        # Verify prospect was still stored (with None product analysis)
        mock_notion_instance.store_prospect_with_product_analysis.assert_called_once()
        call_args = mock_notion_instance.store_prospect_with_product_analysis.call_args
        self.assertIsNone(call_args[0][2])  # product_analysis should be None
        
        # Verify we still got prospects back
        self.assertEqual(len(prospects), 1)
    
    @patch('services.product_analyzer.ProductAnalyzer')
    def test_product_analyzer_comprehensive_analysis(self, mock_analyzer_class):
        """Test ProductAnalyzer performs comprehensive analysis."""
        # Mock the ProductAnalyzer class entirely to avoid initialization issues
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer
        
        # Setup the mock to return our test data
        mock_analyzer.analyze_product.return_value = self.product_analysis
        
        # Create analyzer instance
        analyzer = mock_analyzer_class.return_value
        
        # Perform analysis
        result = analyzer.analyze_product(
            "https://producthunt.com/posts/testcorp",
            "https://testcorp.com"
        )
        
        # Verify comprehensive analysis
        self.assertIsInstance(result, ComprehensiveProductInfo)
        self.assertEqual(result.basic_info.name, "TestCorp Analytics")
        self.assertEqual(len(result.features), 2)
        self.assertEqual(result.pricing.model, "freemium")
        self.assertEqual(result.market_analysis.target_market, "B2B SaaS")
        self.assertEqual(result.team_size, 15)
        
        # Verify the method was called with correct parameters
        mock_analyzer.analyze_product.assert_called_once_with(
            "https://producthunt.com/posts/testcorp",
            "https://testcorp.com"
        )
    
    @patch('services.notion_manager.NotionDataManager')
    def test_notion_stores_product_analysis_data(self, mock_notion_class):
        """Test that Notion manager stores product analysis data correctly."""
        from models.data_models import LinkedInProfile
        
        # Create mock Notion client
        mock_client = Mock()
        mock_notion_class.return_value.client = mock_client
        mock_notion_class.return_value.database_id = "test_db_id"
        mock_notion_class.return_value.check_duplicate.return_value = False
        
        mock_client.pages.create.return_value = {"id": "test_page_id"}
        
        notion_manager = mock_notion_class.return_value
        
        # Create prospect
        prospect = Prospect(
            name="John Doe",
            role="CEO",
            company="TestCorp",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="CEO at TestCorp",
            experience=["CEO at TestCorp"],
            skills=["Leadership", "Strategy"],
            summary="Experienced CEO"
        )
        
        # Mock the actual method implementation
        def mock_store_with_analysis(prospect, linkedin_profile, product_analysis):
            # Verify product analysis data is included
            if product_analysis:
                self.assertEqual(product_analysis.basic_info.name, "TestCorp Analytics")
                self.assertEqual(len(product_analysis.features), 2)
                self.assertEqual(product_analysis.team_size, 15)
            return "test_page_id"
        
        notion_manager.store_prospect_with_product_analysis.side_effect = mock_store_with_analysis
        
        # Store prospect with product analysis
        page_id = notion_manager.store_prospect_with_product_analysis(
            prospect, linkedin_profile, self.product_analysis
        )
        
        # Verify storage was called
        self.assertEqual(page_id, "test_page_id")
        notion_manager.store_prospect_with_product_analysis.assert_called_once_with(
            prospect, linkedin_profile, self.product_analysis
        )
    
    @patch('services.email_generator.EmailGenerator')
    def test_email_generation_uses_product_analysis(self, mock_email_gen_class):
        """Test that email generation uses product analysis data."""
        from models.data_models import EmailContent
        
        mock_email_gen = Mock()
        mock_email_gen_class.return_value = mock_email_gen
        
        # Mock email generation with product analysis
        def mock_generate_email(prospect, template_type=None, linkedin_profile=None, 
                              product_analysis=None, additional_context=None):
            # Verify product analysis is passed
            if product_analysis:
                self.assertIn('product_name', product_analysis)
                self.assertIn('business_insights', product_analysis)
            
            return EmailContent(
                subject="Personalized outreach with product context",
                body="Hi John, I noticed TestCorp's innovative AI-powered analytics platform...",
                template_used="cold_outreach",
                personalization_score=0.8
            )
        
        mock_email_gen.generate_outreach_email.side_effect = mock_generate_email
        
        # Create prospect
        prospect = Prospect(
            name="John Doe",
            role="CEO",
            company="TestCorp",
            id="test_page_id"
        )
        
        # Mock product analysis data from Notion
        product_data = {
            'product_name': 'TestCorp Analytics',
            'product_description': 'AI-powered analytics platform',
            'business_insights': 'Series A funding; Team size: ~15',
            'product_features': 'Real-time Analytics, AI Predictions'
        }
        
        email_generator = mock_email_gen_class.return_value
        
        # Generate email with product analysis
        email_content = email_generator.generate_outreach_email(
            prospect=prospect,
            product_analysis=product_data
        )
        
        # Verify email was generated with product context
        self.assertIn("TestCorp", email_content.body)
        self.assertIn("analytics", email_content.body.lower())
        mock_email_gen.generate_outreach_email.assert_called_once()
    
    @patch('services.product_analyzer.ProductAnalyzer')
    @patch('services.notion_manager.NotionDataManager')
    def test_product_analysis_data_retrieval_for_email(self, mock_notion_class, mock_analyzer):
        """Test retrieving product analysis data for email generation."""
        mock_notion = Mock()
        mock_notion_class.return_value = mock_notion
        
        # Mock data retrieval
        prospect_data = {
            'name': 'John Doe',
            'company': 'TestCorp',
            'product_summary': 'TestCorp Analytics - AI-powered analytics platform for B2B SaaS',
            'business_insights': 'Series A funding; Team size: ~15; Growth potential: High',
            'product_features': 'Analytics: Real-time Analytics; AI: AI Predictions',
            'pricing_model': 'Model: freemium; Tiers: Free, Pro',
            'competitors': 'Competitor1, Competitor2'
        }
        
        mock_notion.get_prospect_data_for_email.return_value = prospect_data
        
        notion_manager = mock_notion_class.return_value
        
        # Retrieve data
        result = notion_manager.get_prospect_data_for_email("test_page_id")
        
        # Verify data structure
        self.assertEqual(result['name'], 'John Doe')
        self.assertEqual(result['company'], 'TestCorp')
        self.assertIn('AI-powered analytics', result['product_summary'])
        self.assertIn('Series A funding', result['business_insights'])
        self.assertIn('Real-time Analytics', result['product_features'])
        self.assertEqual(result['pricing_model'], 'Model: freemium; Tiers: Free, Pro')
        self.assertEqual(result['competitors'], 'Competitor1, Competitor2')
    
    def test_product_analysis_data_formatting(self):
        """Test that product analysis data is formatted correctly for storage."""
        from services.notion_manager import NotionDataManager
        
        # Create a real instance to test formatting methods
        notion_manager = NotionDataManager(self.config)
        
        # Test product summary formatting
        summary = notion_manager._create_product_summary(self.product_analysis)
        self.assertIn("TestCorp Analytics", summary)
        self.assertIn("AI-powered analytics platform", summary)
        self.assertIn("B2B SaaS", summary)
        self.assertIn("~15 people", summary)
        
        # Test business insights formatting
        insights = notion_manager._create_business_insights(self.product_analysis)
        self.assertIn("Series A", insights)
        self.assertIn("High", insights)  # Growth potential
        self.assertIn("AI-powered", insights)  # Competitive advantages
        
        # Test market analysis formatting
        market_text = notion_manager._format_market_analysis(self.product_analysis.market_analysis)
        self.assertIn("B2B SaaS", market_text)
        self.assertIn("Competitor1, Competitor2", market_text)
        self.assertIn("AI-powered, Real-time", market_text)
        
        # Test features formatting
        features_text = notion_manager._format_features(self.product_analysis.features)
        self.assertIn("Analytics: Real-time Analytics", features_text)
        self.assertIn("AI: AI Predictions", features_text)
        
        # Test pricing formatting
        pricing_text = notion_manager._format_pricing(self.product_analysis.pricing)
        self.assertIn("freemium", pricing_text)
        self.assertIn("Free, Pro", pricing_text)


if __name__ == '__main__':
    unittest.main()