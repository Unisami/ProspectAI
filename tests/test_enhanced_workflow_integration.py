"""
Integration tests for the enhanced workflow with AI parsing, product analysis, and email sending.
"""

import pytest
from tests.test_utilities import TestUtilities
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List, Dict, Any

from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData, TeamMember, Prospect, LinkedInProfile
from services.ai_parser import AIParser, ParseResult, ProductInfo, BusinessMetrics
from services.product_analyzer import ProductAnalyzer, ComprehensiveProductInfo
from services.email_sender import EmailSender, SendResult
from utils.config import Config


class TestEnhancedWorkflowIntegration(unittest.TestCase):
    """Test the complete enhanced workflow integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock config
        self.config = Mock(spec=Config)
        self.config.max_products_per_run = 5
        self.config.max_prospects_per_company = 10
        self.config.scraping_delay = 0.1
        self.config.use_ai_parsing = True
        self.config.azure_openai_api_key = "test_key"
        self.config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.config.resend_api_key = "test_resend_key"
        self.config.sender_email = "test@example.com"
        self.config.sender_name = "Test Sender"
        
        # Create test data
        self.test_company = CompanyData(
            name="TestCorp",
            domain="testcorp.com",
            product_url="https://producthunt.com/posts/testcorp",
            description="A test company for AI automation",
            launch_date=datetime.now()
        )
        
        self.test_team_members = [
            TeamMember(
                name="John Doe",
                role="CEO",
                company="TestCorp",
                linkedin_url="https://linkedin.com/in/johndoe"
            ),
            TeamMember(
                name="Jane Smith",
                role="CTO",
                company="TestCorp",
                linkedin_url="https://linkedin.com/in/janesmith"
            )
        ]
        
        self.test_linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="CEO at TestCorp",
            experience=["CEO at TestCorp", "VP at PrevCorp"],
            skills=["Leadership", "Strategy", "AI"],
            summary="Experienced CEO with AI background"
        )
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.EmailSender')
    @patch('controllers.prospect_automation_controller.ProductAnalyzer')
    @patch('controllers.prospect_automation_controller.AIParser')
    def test_enhanced_workflow_initialization(self, mock_ai_parser, mock_product_analyzer, 
                                            mock_email_sender, mock_email_generator,
                                            mock_linkedin_scraper, mock_email_finder,
                                            mock_notion_manager, mock_product_hunt_scraper):
        """Test that the enhanced workflow initializes all services correctly."""
        
        # Setup mocks
        mock_ai_parser.return_value = Mock()
        mock_product_analyzer.return_value = Mock()
        mock_email_sender.return_value = Mock()
        mock_email_generator.return_value = Mock()
        mock_linkedin_scraper.return_value = Mock()
        mock_email_finder.return_value = Mock()
        mock_notion_manager.return_value = Mock()
        mock_product_hunt_scraper.return_value = Mock()
        
        # Initialize controller
        controller = ProspectAutomationController(self.config)
        
        # Verify all services are initialized
        self.assertIsNotNone(controller.product_hunt_scraper)
        self.assertIsNotNone(controller.notion_manager)
        self.assertIsNotNone(controller.email_finder)
        self.assertIsNotNone(controller.linkedin_scraper)
        self.assertIsNotNone(controller.email_generator)
        self.assertIsNotNone(controller.email_sender)
        self.assertIsNotNone(controller.product_analyzer)
        self.assertIsNotNone(controller.ai_parser)
        self.assertTrue(controller.use_ai_parsing)
        
        # Verify enhanced statistics are initialized
        expected_stats = [
            'companies_processed', 'prospects_found', 'emails_found',
            'linkedin_profiles_extracted', 'emails_generated',
            'ai_parsing_successes', 'ai_parsing_failures',
            'product_analyses_completed', 'ai_structured_data_created',
            'emails_sent', 'errors'
        ]
        
        for stat in expected_stats:
            self.assertIn(stat, controller.stats)
            self.assertEqual(controller.stats[stat], 0)
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.EmailSender')
    @patch('controllers.prospect_automation_controller.ProductAnalyzer')
    @patch('controllers.prospect_automation_controller.AIParser')
    def test_ai_parser_fallback_initialization(self, mock_ai_parser, mock_product_analyzer,
                                             mock_email_sender, mock_email_generator,
                                             mock_linkedin_scraper, mock_email_finder,
                                             mock_notion_manager, mock_product_hunt_scraper):
        """Test that controller handles AI Parser initialization failure gracefully."""
        
        # Setup mocks - AI Parser fails to initialize
        mock_ai_parser.side_effect = Exception("AI Parser initialization failed")
        mock_product_analyzer.return_value = Mock()
        mock_email_sender.return_value = Mock()
        mock_email_generator.return_value = Mock()
        mock_linkedin_scraper.return_value = Mock()
        mock_email_finder.return_value = Mock()
        mock_notion_manager.return_value = Mock()
        mock_product_hunt_scraper.return_value = Mock()
        
        # Initialize controller
        controller = ProspectAutomationController(self.config)
        
        # Verify fallback behavior
        self.assertIsNone(controller.ai_parser)
        self.assertFalse(controller.use_ai_parsing)
        
        # Verify other services still work
        self.assertIsNotNone(controller.product_analyzer)
        self.assertIsNotNone(controller.email_sender)
    
    def test_enhanced_workflow_process_company_with_ai(self):
        """Test the complete enhanced workflow for processing a company with AI."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup AI parsing mocks
        controller.ai_parser.extract_business_metrics.return_value = ParseResult(
            success=True,
            data=BusinessMetrics(
                employee_count=50,
                funding_amount="$5M Series A",
                growth_stage="early-stage startup",
                business_model="B2B SaaS"
            ),
            confidence_score=0.8
        )
        
        controller.ai_parser.structure_team_data.return_value = ParseResult(
            success=True,
            data=self.test_team_members,
            confidence_score=0.9
        )
        
        controller.ai_parser.parse_linkedin_profile.return_value = ParseResult(
            success=True,
            data=self.test_linkedin_profile,
            confidence_score=0.85
        )
        
        # Mock the AI parser client for chat completions
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "AI generated summary"
        
        controller.ai_parser.client = Mock()
        controller.ai_parser.client.chat = Mock()
        controller.ai_parser.client.chat.completions = Mock()
        controller.ai_parser.client.chat.completions.create = Mock(return_value=mock_response)
        controller.ai_parser.model_name = "gpt-3.5-turbo"
        
        # Setup other service mocks
        controller.product_analyzer.analyze_product.return_value = self._create_mock_product_analysis()
        controller.email_finder.find_company_emails.return_value = [
            Mock(email="john@testcorp.com", name="John Doe")
        ]
        
        # Make sure LinkedIn scraper returns the mock with raw_html
        mock_linkedin_with_html = Mock()
        mock_linkedin_with_html.name = self.test_linkedin_profile.name
        mock_linkedin_with_html.current_role = self.test_linkedin_profile.current_role
        mock_linkedin_with_html.experience = self.test_linkedin_profile.experience
        mock_linkedin_with_html.skills = self.test_linkedin_profile.skills
        mock_linkedin_with_html.summary = self.test_linkedin_profile.summary
        mock_linkedin_with_html.raw_html = "<html>Mock LinkedIn HTML</html>"
        
        controller.linkedin_scraper.extract_profile_data.return_value = mock_linkedin_with_html
        controller.notion_manager.store_ai_structured_data.return_value = "page_123"
        
        # Process company
        prospects = controller.process_company(self.test_company)
        
        # Verify results
        self.assertEqual(len(prospects), 2)  # Two team members
        self.assertEqual(controller.stats['product_analyses_completed'], 1)
        self.assertEqual(controller.stats['ai_parsing_successes'], 3)  # Team data + 2 LinkedIn profiles
        self.assertEqual(controller.stats['ai_structured_data_created'], 2)  # One per prospect
        self.assertEqual(controller.stats['prospects_found'], 2)
        
        # Verify AI methods were called
        controller.ai_parser.extract_business_metrics.assert_called_once()
        controller.ai_parser.structure_team_data.assert_called_once()
        self.assertEqual(controller.ai_parser.parse_linkedin_profile.call_count, 2)  # Called for each team member
        self.assertEqual(controller.notion_manager.store_ai_structured_data.call_count, 2)  # Called for each prospect
    
    def test_enhanced_workflow_with_ai_failures(self):
        """Test enhanced workflow handles AI parsing failures gracefully."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup AI parsing failures
        controller.ai_parser.extract_business_metrics.return_value = ParseResult(
            success=False,
            data=None,
            error_message="AI parsing failed"
        )
        
        controller.ai_parser.structure_team_data.return_value = ParseResult(
            success=False,
            data=None,
            error_message="Team structuring failed"
        )
        
        # Setup fallback data
        controller.product_hunt_scraper.extract_team_info.return_value = self.test_team_members
        controller.product_analyzer.analyze_product.return_value = self._create_mock_product_analysis()
        controller.linkedin_scraper.extract_profile_data.return_value = self.test_linkedin_profile
        controller.notion_manager.store_ai_structured_data.return_value = "page_123"
        
        # Process company
        prospects = controller.process_company(self.test_company)
        
        # Verify fallback behavior
        self.assertEqual(len(prospects), 2)  # Still processes team members
        self.assertEqual(controller.stats['ai_parsing_failures'], 1)  # Records team structuring failure
        self.assertEqual(controller.stats['prospects_found'], 2)  # Still finds prospects
        
        # Verify fallback methods were used
        controller.product_hunt_scraper.extract_team_info.assert_called_once()
    
    def test_enhanced_email_generation_and_sending_workflow(self):
        """Test the complete email generation and sending workflow with AI-structured data."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup email generation and sending mocks
        mock_email_content = Mock()
        mock_email_content.subject = "Test Subject"
        mock_email_content.body = "Test email body with AI personalization"
        mock_email_content.personalization_score = 0.9
        mock_email_content.template_used = "cold_outreach"
        
        controller.email_generator.generate_and_send_bulk_emails.return_value = [
            {
                'prospect_id': 'prospect_1',
                'email_content': mock_email_content,
                'sent': True,
                'generated_at': datetime.now().isoformat(),
                'send_result': {'email_id': 'email_123', 'status': 'sent'}
            }
        ]
        
        controller.notion_manager.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'company': 'TestCorp',
            'email': 'john@testcorp.com'
        }
        
        # Generate and send emails
        results = controller.generate_and_send_outreach_emails(
            prospect_ids=['prospect_1'],
            send_immediately=True,
            delay_between_emails=1.0
        )
        
        # Verify results
        self.assertEqual(results['emails_generated'], 1)
        self.assertEqual(results['emails_sent'], 1)
        self.assertEqual(results['errors'], 0)
        self.assertEqual(len(results['successful']), 1)
        
        # Verify email generation was called with correct parameters
        controller.email_generator.generate_and_send_bulk_emails.assert_called_once()
        call_args = controller.email_generator.generate_and_send_bulk_emails.call_args
        self.assertIn('additional_context', call_args.kwargs)
        self.assertEqual(call_args.kwargs['additional_context']['source_mention'], 'ProductHunt')
    
    def test_enhanced_workflow_statistics_tracking(self):
        """Test that enhanced workflow statistics are tracked correctly."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup mocks for successful processing
        controller.ai_parser.extract_business_metrics.return_value = ParseResult(success=True, data=Mock())
        controller.ai_parser.structure_team_data.return_value = ParseResult(success=True, data=self.test_team_members)
        controller.ai_parser.parse_linkedin_profile.return_value = ParseResult(success=True, data=self.test_linkedin_profile)
        controller.product_analyzer.analyze_product.return_value = self._create_mock_product_analysis()
        
        # Setup LinkedIn scraper to return profile with raw_html for AI parsing
        mock_linkedin_with_html = Mock()
        mock_linkedin_with_html.name = self.test_linkedin_profile.name
        mock_linkedin_with_html.current_role = self.test_linkedin_profile.current_role
        mock_linkedin_with_html.experience = self.test_linkedin_profile.experience
        mock_linkedin_with_html.skills = self.test_linkedin_profile.skills
        mock_linkedin_with_html.summary = self.test_linkedin_profile.summary
        mock_linkedin_with_html.raw_html = "<html>Mock LinkedIn HTML</html>"
        
        controller.linkedin_scraper.extract_profile_data.return_value = mock_linkedin_with_html
        controller.notion_manager.store_ai_structured_data.return_value = "page_123"
        
        # Mock the AI parser client for chat completions
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "AI generated summary"
        
        controller.ai_parser.client = Mock()
        controller.ai_parser.client.chat = Mock()
        controller.ai_parser.client.chat.completions = Mock()
        controller.ai_parser.client.chat.completions.create = Mock(return_value=mock_response)
        controller.ai_parser.model_name = "gpt-3.5-turbo"
        
        # Process company
        controller.process_company(self.test_company)
        
        # Verify statistics
        self.assertEqual(controller.stats['product_analyses_completed'], 1)
        self.assertEqual(controller.stats['ai_parsing_successes'], 3)  # Team + 2 LinkedIn profiles
        self.assertEqual(controller.stats['ai_structured_data_created'], 2)  # Per prospect
        self.assertEqual(controller.stats['prospects_found'], 2)
        self.assertEqual(controller.stats['linkedin_profiles_extracted'], 2)
    
    def test_enhanced_workflow_error_handling(self):
        """Test comprehensive error handling in enhanced workflow."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup service failures
        controller.product_analyzer.analyze_product.side_effect = Exception("Product analysis failed")
        controller.ai_parser.structure_team_data.side_effect = Exception("AI parsing failed")
        
        # Process company should handle errors gracefully
        with self.assertLogs(level='ERROR') as log:
            prospects = controller.process_company(self.test_company)
        
        # Verify error handling
        self.assertEqual(len(prospects), 0)  # No prospects due to failures
        self.assertIn('ERROR', str(log.output))
    
    def test_enhanced_workflow_progress_tracking(self):
        """Test progress tracking for enhanced workflow stages."""
        
        # Create controller with mocked services
        controller = self._create_mocked_controller()
        
        # Setup mocks
        controller.product_hunt_scraper.get_latest_products.return_value = [Mock(
            company_name="TestCorp",
            website_url="https://testcorp.com",
            product_url="https://producthunt.com/posts/testcorp",
            description="Test company",
            launch_date=datetime.now()
        )]
        
        controller.ai_parser.extract_business_metrics.return_value = ParseResult(success=True, data=Mock())
        controller.ai_parser.structure_team_data.return_value = ParseResult(success=True, data=self.test_team_members)
        controller.product_analyzer.analyze_product.return_value = self._create_mock_product_analysis()
        controller.notion_manager.store_ai_structured_data.return_value = "page_123"
        
        # Run discovery pipeline
        results = controller.run_discovery_pipeline(limit=1)
        
        # Verify progress tracking
        self.assertIn('summary', results)
        self.assertEqual(results['summary']['companies_processed'], 1)
        self.assertIsNotNone(results['statistics']['start_time'])
        self.assertIsNotNone(results['statistics']['end_time'])
    
    def _create_mocked_controller(self) -> ProspectAutomationController:
        """Create a controller with mocked services for testing."""
        
        with patch.multiple(
            'controllers.prospect_automation_controller',
            ProductHuntScraper=Mock(),
            NotionDataManager=Mock(),
            EmailFinder=Mock(),
            LinkedInScraper=Mock(),
            EmailGenerator=Mock(),
            EmailSender=Mock(),
            ProductAnalyzer=Mock(),
            AIParser=Mock()
        ):
            controller = ProspectAutomationController(self.config)
            
            # Setup basic mocks
            controller.product_hunt_scraper.extract_team_info.return_value = self.test_team_members
            
            # Fix email finder mocks
            controller.email_finder.find_and_verify_team_emails.return_value = {
                "John Doe": {"email": "john@testcorp.com", "confidence": 85},
                "Jane Smith": {"email": "jane@testcorp.com", "confidence": 80}
            }
            controller.email_finder.get_best_emails.return_value = {
                "John Doe": {"email": "john@testcorp.com", "confidence": 85},
                "Jane Smith": {"email": "jane@testcorp.com", "confidence": 80}
            }
            
            # Fix LinkedIn scraper mock to return proper data with raw_html attribute
            mock_linkedin_profile = Mock()
            mock_linkedin_profile.name = self.test_linkedin_profile.name
            mock_linkedin_profile.current_role = self.test_linkedin_profile.current_role
            mock_linkedin_profile.experience = self.test_linkedin_profile.experience
            mock_linkedin_profile.skills = self.test_linkedin_profile.skills
            mock_linkedin_profile.summary = self.test_linkedin_profile.summary
            mock_linkedin_profile.raw_html = "<html>Mock LinkedIn HTML</html>"
            
            controller.linkedin_scraper.extract_profile_data.return_value = mock_linkedin_profile
            controller.notion_manager.store_ai_structured_data.return_value = "page_123"
            
            return controller
    
    def _create_mock_product_analysis(self) -> Mock:
        """Create a mock comprehensive product analysis."""
        
        # Create proper mock objects with string representations
        mock_feature1 = Mock()
        mock_feature1.name = "Feature 1"
        mock_feature1.__str__ = lambda self: "Feature 1"
        
        mock_feature2 = Mock()
        mock_feature2.name = "Feature 2"
        mock_feature2.__str__ = lambda self: "Feature 2"
        
        mock_analysis = Mock()
        mock_analysis.basic_info = Mock()
        mock_analysis.basic_info.name = "TestCorp Product"
        mock_analysis.basic_info.description = "AI-powered test product"
        mock_analysis.features = [mock_feature1, mock_feature2]
        mock_analysis.pricing = Mock()
        mock_analysis.pricing.model = "freemium"
        mock_analysis.market_analysis = Mock()
        mock_analysis.market_analysis.target_market = "B2B SaaS"
        mock_analysis.market_analysis.competitors = ["Competitor1", "Competitor2"]
        mock_analysis.funding_info = None
        
        return mock_analysis


if __name__ == '__main__':
    unittest.main()