"""
Comprehensive tests for enhanced features including AI parsing, product analysis, and email sending.

This test suite covers:
1. Integration tests for AI parsing and structuring workflow
2. Complete pipeline from scraping to AI processing to email sending
3. Performance tests for AI parsing and email generation
4. End-to-end tests with mock APIs for all new services
"""

import pytest
from tests.test_utilities import TestUtilities
import unittest
import time
import asyncio
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from typing import List, Dict, Any
import json
import concurrent.futures

from controllers.prospect_automation_controller import ProspectAutomationController
from services.ai_parser import AIParser, ParseResult, ProductInfo, BusinessMetrics
from services.product_analyzer import ProductAnalyzer, ComprehensiveProductInfo, Feature, PricingInfo, MarketAnalysis
from services.email_sender import EmailSender, SendResult, DeliveryStatus
from services.email_generator import EmailGenerator, EmailContent
from models.data_models import CompanyData, TeamMember, Prospect, LinkedInProfile
from utils.config import Config


class TestAIParsingWorkflowIntegration(unittest.TestCase):
    """Integration tests for AI parsing and structuring workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock(spec=Config)
        self.config.use_azure_openai = True
        self.config.azure_openai_api_key = "test_key"
        self.config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.config.azure_openai_deployment_name = "gpt-4"
        self.config.enable_ai_parsing = True
        
        # Test data
        self.sample_company = CompanyData(
            name="AI Startup Inc",
            domain="aistartup.com",
            product_url="https://producthunt.com/posts/ai-startup",
            description="Revolutionary AI platform for businesses",
            launch_date=datetime.now()
        )
        
        self.sample_raw_html = """
        <html>
            <head><title>John Doe - LinkedIn</title></head>
            <body>
                <h1>John Doe</h1>
                <div class="role">Senior AI Engineer at AI Startup Inc</div>
                <div class="summary">Experienced AI engineer with 10+ years building ML systems</div>
                <div class="experience">
                    <div>Senior AI Engineer at AI Startup Inc (2022-Present)</div>
                    <div>ML Engineer at TechCorp (2019-2022)</div>
                </div>
                <div class="skills">Python, TensorFlow, PyTorch, AWS, Docker</div>
            </body>
        </html>
        """
        
        self.sample_product_content = """
        AI Startup Inc - Revolutionary AI Platform
        
        Our platform helps businesses automate complex workflows using advanced AI.
        
        Features:
        - Natural Language Processing
        - Computer Vision
        - Predictive Analytics
        - Real-time Processing
        
        Pricing: Starting at $99/month with enterprise plans available
        Target Market: Mid-market and enterprise businesses
        Competitors: OpenAI, Anthropic, Google AI
        
        Recently raised $10M Series A funding and growing rapidly.
        Team of 25 engineers and data scientists.
        """
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_workflow_linkedin_profile(self, mock_azure_openai):
        """Test complete AI parsing workflow for LinkedIn profiles."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock successful AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "John Doe",
            "current_role": "Senior AI Engineer at AI Startup Inc",
            "experience": [
                "Senior AI Engineer at AI Startup Inc (2022-Present)",
                "ML Engineer at TechCorp (2019-2022)"
            ],
            "skills": ["Python", "TensorFlow", "PyTorch", "AWS", "Docker"],
            "summary": "Experienced AI engineer with 10+ years building ML systems"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test LinkedIn profile parsing
        result = ai_parser.parse_linkedin_profile(self.sample_raw_html)
        
        # Verify successful parsing
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "John Doe")
        self.assertEqual(result.data.current_role, "Senior AI Engineer at AI Startup Inc")
        self.assertEqual(len(result.data.experience), 2)
        self.assertEqual(len(result.data.skills), 5)
        self.assertGreater(result.confidence_score, 0.8)
        
        # Verify AI API was called with correct parameters
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        self.assertEqual(call_args[1]['model'], "gpt-4")
        self.assertEqual(call_args[1]['temperature'], 0.1)
        self.assertIn("LinkedIn profile", call_args[1]['messages'][0]['content'])
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_workflow_product_analysis(self, mock_azure_openai):
        """Test complete AI parsing workflow for product information."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock successful AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "AI Startup Platform",
            "description": "Revolutionary AI platform for business automation",
            "features": ["Natural Language Processing", "Computer Vision", "Predictive Analytics"],
            "pricing_model": "subscription",
            "target_market": "Mid-market and enterprise businesses",
            "competitors": ["OpenAI", "Anthropic", "Google AI"],
            "funding_status": "Series A",
            "market_analysis": "Growing rapidly in the AI automation space"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test product info parsing
        result = ai_parser.parse_product_info(self.sample_product_content)
        
        # Verify successful parsing
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, ProductInfo)
        self.assertEqual(result.data.name, "AI Startup Platform")
        self.assertEqual(len(result.data.features), 3)
        self.assertEqual(len(result.data.competitors), 3)
        self.assertEqual(result.data.pricing_model, "subscription")
        self.assertGreater(result.confidence_score, 0.8)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_workflow_business_metrics(self, mock_azure_openai):
        """Test complete AI parsing workflow for business metrics extraction."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock successful AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "employee_count": 25,
            "funding_amount": "$10M Series A",
            "growth_stage": "early-stage startup",
            "business_model": "B2B SaaS",
            "revenue_model": "subscription",
            "key_metrics": {
                "funding": "$10M Series A",
                "team_size": "25 engineers and data scientists",
                "growth_rate": "rapidly growing"
            },
            "market_position": "Emerging player in AI automation"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test business metrics extraction
        result = ai_parser.extract_business_metrics(self.sample_product_content, "AI Startup Inc")
        
        # Verify successful parsing
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, BusinessMetrics)
        self.assertEqual(result.data.employee_count, 25)
        self.assertEqual(result.data.funding_amount, "$10M Series A")
        self.assertEqual(result.data.business_model, "B2B SaaS")
        self.assertEqual(len(result.data.key_metrics), 3)
        self.assertGreater(result.confidence_score, 0.7)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_workflow_error_handling(self, mock_azure_openai):
        """Test AI parsing workflow error handling and fallback mechanisms."""
        # Setup AI client mock to fail
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test parsing with fallback data
        fallback_data = {
            "name": "John Doe",
            "current_role": "Engineer",
            "experience": ["Current role"],
            "skills": ["Python"],
            "summary": "Engineer"
        }
        
        result = ai_parser.parse_linkedin_profile(self.sample_raw_html, fallback_data)
        
        # Verify fallback behavior
        self.assertTrue(result.success)
        self.assertIsInstance(result.data, LinkedInProfile)
        self.assertEqual(result.data.name, "John Doe")
        self.assertEqual(result.confidence_score, 0.3)  # Lower confidence for fallback
        self.assertIn("AI parsing failed", result.error_message)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_workflow_retry_mechanism(self, mock_azure_openai):
        """Test AI parsing workflow retry mechanism with exponential backoff."""
        # Setup AI client mock to fail first, then succeed
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        mock_success_response = Mock()
        mock_success_response.choices = [Mock()]
        mock_success_response.choices[0].message.content = json.dumps({
            "name": "Test Product",
            "description": "Test Description",
            "features": [],
            "pricing_model": "free",
            "target_market": "everyone",
            "competitors": []
        })
        
        # First call fails, second succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("Temporary API Error"),
            mock_success_response
        ]
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test parsing with retry
        with patch('time.sleep') as mock_sleep:
            result = ai_parser.parse_with_retry(
                ai_parser.parse_product_info, 
                self.sample_product_content,
                max_retries=2
            )
        
        # Verify retry succeeded
        self.assertTrue(result.success)
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)
        mock_sleep.assert_called_once_with(5)  # First retry delay


class TestCompleteEnhancedPipeline(unittest.TestCase):
    """Test complete pipeline from scraping to AI processing to email sending."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock(spec=Config)
        self.config.use_azure_openai = True
        self.config.azure_openai_api_key = "test_key"
        self.config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.config.resend_api_key = "test_resend_key"
        self.config.sender_email = "test@example.com"
        self.config.sender_name = "Test Sender"
        self.config.max_products_per_run = 2
        self.config.max_prospects_per_company = 3
        self.config.scraping_delay = 0.1
        
        self.test_company = CompanyData(
            name="TechCorp",
            domain="techcorp.com",
            product_url="https://producthunt.com/posts/techcorp",
            description="Innovative tech company",
            launch_date=datetime.now()
        )
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.EmailSender')
    @patch('controllers.prospect_automation_controller.ProductAnalyzer')
    @patch('controllers.prospect_automation_controller.AIParser')
    def test_complete_enhanced_pipeline_workflow(self, mock_ai_parser, mock_product_analyzer,
                                               mock_email_sender, mock_email_generator,
                                               mock_linkedin_scraper, mock_email_finder,
                                               mock_notion_manager, mock_product_hunt_scraper):
        """Test the complete enhanced pipeline from discovery to email sending."""
        
        # Setup all service mocks
        self._setup_complete_pipeline_mocks(
            mock_ai_parser, mock_product_analyzer, mock_email_sender,
            mock_email_generator, mock_linkedin_scraper, mock_email_finder,
            mock_notion_manager, mock_product_hunt_scraper
        )
        
        # Initialize controller
        controller = ProspectAutomationController(self.config)
        
        # Run complete pipeline
        discovery_results = controller.run_discovery_pipeline(limit=1)
        
        # Verify discovery phase
        self.assertEqual(discovery_results['summary']['companies_processed'], 1)
        self.assertEqual(discovery_results['summary']['prospects_found'], 2)
        self.assertEqual(discovery_results['summary']['ai_parsing_successes'], 3)  # Team + 2 LinkedIn
        self.assertEqual(discovery_results['summary']['product_analyses_completed'], 1)
        self.assertEqual(discovery_results['summary']['ai_structured_data_created'], 2)
        
        # Get prospect IDs for email generation
        prospect_ids = ["prospect_1", "prospect_2"]
        
        # Generate and send emails
        email_results = controller.generate_and_send_outreach_emails(
            prospect_ids=prospect_ids,
            send_immediately=True,
            delay_between_emails=0.5
        )
        
        # Verify email generation and sending
        self.assertEqual(email_results['emails_generated'], 2)
        self.assertEqual(email_results['emails_sent'], 2)
        self.assertEqual(email_results['errors'], 0)
        self.assertEqual(len(email_results['successful']), 2)
        
        # Verify all services were called in correct order
        mock_product_hunt_scraper.return_value.get_latest_products.assert_called_once()
        mock_product_analyzer.return_value.analyze_product.assert_called_once()
        mock_ai_parser.return_value.extract_business_metrics.assert_called_once()
        mock_ai_parser.return_value.structure_team_data.assert_called_once()
        self.assertEqual(mock_ai_parser.return_value.parse_linkedin_profile.call_count, 2)
        self.assertEqual(mock_notion_manager.return_value.store_ai_structured_data.call_count, 2)
        mock_email_generator.return_value.generate_and_send_bulk_emails.assert_called_once()
    
    def _setup_complete_pipeline_mocks(self, mock_ai_parser, mock_product_analyzer,
                                     mock_email_sender, mock_email_generator,
                                     mock_linkedin_scraper, mock_email_finder,
                                     mock_notion_manager, mock_product_hunt_scraper):
        """Setup all mocks for complete pipeline test."""
        
        # ProductHunt scraper mocks
        mock_product_hunt_scraper.return_value.get_latest_products.return_value = [
            Mock(
                company_name="TechCorp",
                website_url="https://techcorp.com",
                product_url="https://producthunt.com/posts/techcorp",
                description="Innovative tech company",
                launch_date=datetime.now()
            )
        ]
        
        mock_team_members = [
            TeamMember(name="John Doe", role="CEO", company="TechCorp", linkedin_url="https://linkedin.com/in/john"),
            TeamMember(name="Jane Smith", role="CTO", company="TechCorp", linkedin_url="https://linkedin.com/in/jane")
        ]
        mock_product_hunt_scraper.return_value.extract_team_info.return_value = mock_team_members
        
        # AI Parser mocks
        mock_ai_parser.return_value.extract_business_metrics.return_value = ParseResult(
            success=True,
            data=BusinessMetrics(employee_count=50, funding_amount="$5M", business_model="B2B SaaS"),
            confidence_score=0.9
        )
        
        mock_ai_parser.return_value.structure_team_data.return_value = ParseResult(
            success=True,
            data=mock_team_members,
            confidence_score=0.85
        )
        
        mock_linkedin_profile = LinkedInProfile(
            name="John Doe",
            current_role="CEO at TechCorp",
            experience=["CEO at TechCorp"],
            skills=["Leadership", "Strategy"],
            summary="Experienced CEO"
        )
        
        mock_ai_parser.return_value.parse_linkedin_profile.return_value = ParseResult(
            success=True,
            data=mock_linkedin_profile,
            confidence_score=0.8
        )
        
        # Mock AI parser client for summary generation
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "AI generated summary"
        
        mock_ai_parser.return_value.client = Mock()
        mock_ai_parser.return_value.client.chat.completions.create.return_value = mock_response
        mock_ai_parser.return_value.model_name = "gpt-4"
        
        # Product Analyzer mocks
        mock_product_analysis = Mock()
        mock_product_analysis.basic_info.name = "TechCorp Product"
        mock_product_analysis.features = [Mock(name="Feature 1"), Mock(name="Feature 2")]
        mock_product_analysis.pricing.model = "freemium"
        mock_product_analysis.market_analysis.target_market = "B2B"
        mock_product_analyzer.return_value.analyze_product.return_value = mock_product_analysis
        
        # Email Finder mocks
        mock_email_finder.return_value.find_and_verify_team_emails.return_value = {
            "John Doe": {"email": "john@techcorp.com", "confidence": 90},
            "Jane Smith": {"email": "jane@techcorp.com", "confidence": 85}
        }
        mock_email_finder.return_value.get_best_emails.return_value = {
            "John Doe": "john@techcorp.com",
            "Jane Smith": "jane@techcorp.com"
        }
        
        # LinkedIn Scraper mocks
        mock_linkedin_with_html = Mock()
        mock_linkedin_with_html.name = "John Doe"
        mock_linkedin_with_html.current_role = "CEO at TechCorp"
        mock_linkedin_with_html.experience = ["CEO at TechCorp"]
        mock_linkedin_with_html.skills = ["Leadership"]
        mock_linkedin_with_html.summary = "CEO"
        mock_linkedin_with_html.raw_html = "<html>Mock HTML</html>"
        
        mock_linkedin_scraper.return_value.extract_profile_data.return_value = mock_linkedin_with_html
        
        # Notion Manager mocks
        mock_notion_manager.return_value.store_ai_structured_data.return_value = "page_123"
        mock_notion_manager.return_value.get_prospect_data_for_email.return_value = {
            'name': 'John Doe',
            'company': 'TechCorp',
            'email': 'john@techcorp.com'
        }
        
        # Email Generator mocks
        mock_email_content = Mock()
        mock_email_content.subject = "Opportunity at TechCorp"
        mock_email_content.body = "Personalized email content"
        mock_email_content.personalization_score = 0.9
        
        mock_email_generator.return_value.generate_and_send_bulk_emails.return_value = [
            {
                'prospect_id': 'prospect_1',
                'email_content': mock_email_content,
                'sent': True,
                'send_result': {'email_id': 'email_123', 'status': 'sent'}
            },
            {
                'prospect_id': 'prospect_2',
                'email_content': mock_email_content,
                'sent': True,
                'send_result': {'email_id': 'email_124', 'status': 'sent'}
            }
        ]
        
        # Email Sender mocks
        mock_send_result = SendResult(
            email_id="email_123",
            status="sent",
            recipient_email="john@techcorp.com",
            subject="Test Subject",
            sent_at=datetime.now()
        )
        mock_email_sender.return_value.send_email.return_value = mock_send_result


class TestPerformanceEnhancedFeatures(unittest.TestCase):
    """Performance tests for AI parsing and email generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock(spec=Config)
        self.config.use_azure_openai = True
        self.config.azure_openai_api_key = "test_key"
        self.config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.config.azure_openai_deployment_name = "gpt-4"
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_performance_linkedin_profiles(self, mock_azure_openai):
        """Test AI parsing performance for multiple LinkedIn profiles."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "Test User",
            "current_role": "Engineer",
            "experience": ["Current role"],
            "skills": ["Python"],
            "summary": "Engineer"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test parsing multiple profiles
        num_profiles = 10
        sample_html = "<html><body>Test profile content</body></html>"
        
        start_time = time.time()
        
        results = []
        for i in range(num_profiles):
            result = ai_parser.parse_linkedin_profile(sample_html)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_profile = total_time / num_profiles
        
        # Verify performance
        self.assertLess(avg_time_per_profile, 2.0)  # Should be under 2 seconds per profile
        self.assertEqual(len(results), num_profiles)
        self.assertTrue(all(r.success for r in results))
        
        # Verify API calls
        self.assertEqual(mock_client.chat.completions.create.call_count, num_profiles)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_performance_concurrent_processing(self, mock_azure_openai):
        """Test AI parsing performance with concurrent processing."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock AI response with slight delay to simulate real API
        def mock_api_call(*args, **kwargs):
            time.sleep(0.1)  # Simulate API latency
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
            return mock_response
        
        mock_client.chat.completions.create.side_effect = mock_api_call
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test concurrent parsing
        num_items = 5
        sample_content = "Test product content"
        
        # Sequential processing
        start_time = time.time()
        sequential_results = []
        for i in range(num_items):
            result = ai_parser.parse_product_info(sample_content)
            sequential_results.append(result)
        sequential_time = time.time() - start_time
        
        # Concurrent processing using ThreadPoolExecutor
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(ai_parser.parse_product_info, sample_content)
                for _ in range(num_items)
            ]
            concurrent_results = [future.result() for future in futures]
        concurrent_time = time.time() - start_time
        
        # Verify concurrent processing is faster
        self.assertLess(concurrent_time, sequential_time)
        self.assertEqual(len(concurrent_results), num_items)
        self.assertTrue(all(r.success for r in concurrent_results))
        
        # Performance should be at least 30% better with concurrency
        performance_improvement = (sequential_time - concurrent_time) / sequential_time
        self.assertGreater(performance_improvement, 0.3)
    
    @patch('services.email_generator.AzureOpenAI')
    def test_email_generation_performance_bulk_processing(self, mock_azure_openai):
        """Test email generation performance for bulk processing."""
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated email content"
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize email generator
        email_generator = EmailGenerator(self.config)
        
        # Create test prospects
        num_prospects = 20
        prospects = []
        for i in range(num_prospects):
            prospect = Mock()
            prospect.name = f"Test User {i}"
            prospect.company = f"Company {i}"
            prospect.role = "Engineer"
            prospect.email = f"user{i}@company{i}.com"
            prospects.append(prospect)
        
        # Test bulk email generation
        start_time = time.time()
        
        results = []
        for prospect in prospects:
            email_content = email_generator.generate_outreach_email(
                prospect=prospect,
                template_type="cold_outreach"
            )
            results.append(email_content)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_email = total_time / num_prospects
        
        # Verify performance
        self.assertLess(avg_time_per_email, 1.0)  # Should be under 1 second per email
        self.assertEqual(len(results), num_prospects)
        
        # Verify throughput
        emails_per_minute = (num_prospects / total_time) * 60
        self.assertGreater(emails_per_minute, 60)  # Should generate at least 60 emails per minute
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_ai_parsing_memory_usage(self, mock_azure_openai):
        """Test AI parsing memory usage with large datasets."""
        import psutil
        import os
        
        # Setup AI client mock
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        # Mock AI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "name": "Test User",
            "current_role": "Engineer",
            "experience": ["Role 1", "Role 2"],
            "skills": ["Skill 1", "Skill 2"],
            "summary": "Summary"
        })
        mock_client.chat.completions.create.return_value = mock_response
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        num_items = 100
        large_html_content = "<html><body>" + "x" * 10000 + "</body></html>"  # 10KB content
        
        results = []
        for i in range(num_items):
            result = ai_parser.parse_linkedin_profile(large_html_content)
            results.append(result)
            
            # Clear result data to test memory cleanup
            if i % 10 == 0:
                results = results[-5:]  # Keep only last 5 results
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        self.assertLess(memory_increase, 100)  # Should not increase by more than 100MB
        self.assertEqual(len(results), 5)  # Should have cleaned up old results
        for i in range(num_items):
            result = ai_parser.parse_linkedin_profile(large_html_content)
            results.append(result)
            
            # Clear result data to test memory cleanup
            if i % 10 == 0:
                results = results[-5:]  # Keep only last 5 results
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Verify memory usage is reasonable
        self.assertLess(memory_increase, 100)  # Should not increase by more than 100MB
        self.assertEqual(len(results), 5)  # Should have cleaned up old results


class TestEndToEndMockAPIIntegration(unittest.TestCase):
    """End-to-end tests with mock APIs for all new services."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock(spec=Config)
        self.config.use_azure_openai = True
        self.config.azure_openai_api_key = "test_key"
        self.config.azure_openai_endpoint = "https://test.openai.azure.com"
        self.config.resend_api_key = "test_resend_key"
        self.config.sender_email = "test@example.com"
        self.config.sender_name = "Test Sender"
        self.config.notion_token = "test_notion_token"
        self.config.hunter_api_key = "test_hunter_key"
        self.config.max_products_per_run = 3
        self.config.scraping_delay = 0.1
    
    @patch('services.ai_parser.AzureOpenAI')
    @patch('services.product_analyzer.webdriver.Chrome')
    @patch('services.email_sender.resend')
    @patch('services.notion_manager.Client')
    @patch('services.email_finder.requests.get')
    def test_end_to_end_with_all_mock_apis(self, mock_hunter_api, mock_notion_client,
                                         mock_resend, mock_webdriver, mock_azure_openai):
        """Test complete end-to-end workflow with all APIs mocked."""
        
        # Setup Azure OpenAI mock
        mock_ai_client = Mock()
        mock_azure_openai.return_value = mock_ai_client
        
        # Mock different AI responses for different parsing tasks
        def mock_ai_response_generator(call_count=[0]):
            call_count[0] += 1
            mock_response = Mock()
            mock_response.choices = [Mock()]
            
            if call_count[0] == 1:  # Business metrics
                mock_response.choices[0].message.content = json.dumps({
                    "employee_count": 25,
                    "funding_amount": "$5M Series A",
                    "growth_stage": "early-stage startup",
                    "business_model": "B2B SaaS"
                })
            elif call_count[0] == 2:  # Team structuring
                mock_response.choices[0].message.content = json.dumps([
                    {
                        "name": "John Doe",
                        "role": "CEO",
                        "company": "TestCorp",
                        "linkedin_url": "https://linkedin.com/in/john"
                    }
                ])
            elif call_count[0] == 3:  # LinkedIn parsing
                mock_response.choices[0].message.content = json.dumps({
                    "name": "John Doe",
                    "current_role": "CEO at TestCorp",
                    "experience": ["CEO at TestCorp"],
                    "skills": ["Leadership"],
                    "summary": "Experienced CEO"
                })
            elif call_count[0] == 4:  # Product analysis
                mock_response.choices[0].message.content = json.dumps({
                    "name": "TestCorp Product",
                    "description": "Innovative solution",
                    "features": ["Feature 1", "Feature 2"],
                    "pricing_model": "freemium",
                    "target_market": "SMB",
                    "competitors": ["Competitor 1"]
                })
            else:  # Email generation or summaries
                mock_response.choices[0].message.content = "Generated content"
            
            return mock_response
        
        mock_ai_client.chat.completions.create.side_effect = mock_ai_response_generator
        
        # Setup WebDriver mock for scraping
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        mock_driver.page_source = """
        <html>
            <body>
                <h1>TestCorp Product</h1>
                <div class="team">
                    <div>John Doe - CEO</div>
                    <a href="https://linkedin.com/in/john">LinkedIn</a>
                </div>
            </body>
        </html>
        """
        
        # Setup Resend API mock
        mock_resend.api_key = "test_key"
        mock_resend_emails = Mock()
        mock_resend.Emails = mock_resend_emails
        
        mock_send_response = Mock()
        mock_send_response.id = "email_123"
        mock_resend_emails.send.return_value = mock_send_response
        
        # Setup Notion API mock
        mock_notion = Mock()
        mock_notion_client.return_value = mock_notion
        
        mock_notion.databases.create.return_value = {"id": "database_123"}
        mock_notion.pages.create.return_value = {"id": "page_123"}
        mock_notion.databases.query.return_value = {
            "results": [
                {
                    "id": "page_123",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "John Doe"}}]},
                        "Email": {"email": "john@testcorp.com"}
                    }
                }
            ]
        }
        
        # Setup Hunter.io API mock
        mock_hunter_response = Mock()
        mock_hunter_response.json.return_value = {
            "data": {
                "emails": [
                    {
                        "value": "john@testcorp.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "position": "CEO",
                        "confidence": 95
                    }
                ]
            }
        }
        mock_hunter_response.status_code = 200
        mock_hunter_api.return_value = mock_hunter_response
        
        # Initialize and run complete workflow
        with patch('controllers.prospect_automation_controller.ProductHuntScraper') as mock_scraper:
            # Setup ProductHunt scraper mock
            mock_scraper_instance = mock_scraper.return_value
            mock_scraper_instance.get_latest_products.return_value = [
                Mock(
                    company_name="TestCorp",
                    website_url="https://testcorp.com",
                    product_url="https://producthunt.com/posts/testcorp",
                    description="Test company",
                    launch_date=datetime.now()
                )
            ]
            mock_scraper_instance.extract_team_info.return_value = [
                TeamMember(
                    name="John Doe",
                    role="CEO",
                    company="TestCorp",
                    linkedin_url="https://linkedin.com/in/john"
                )
            ]
            
            # Initialize controller and run pipeline
            controller = ProspectAutomationController(self.config)
            
            # Run discovery
            discovery_results = controller.run_discovery_pipeline(limit=1)
            
            # Verify discovery results
            self.assertEqual(discovery_results['summary']['companies_processed'], 1)
            self.assertGreater(discovery_results['summary']['prospects_found'], 0)
            
            # Generate and send emails
            prospect_ids = ["page_123"]
            email_results = controller.generate_and_send_outreach_emails(
                prospect_ids=prospect_ids,
                send_immediately=True
            )
            
            # Verify email results
            self.assertGreater(email_results['emails_generated'], 0)
            self.assertEqual(email_results['errors'], 0)
        
        # Verify all APIs were called
        mock_ai_client.chat.completions.create.assert_called()
        mock_driver.get.assert_called()
        mock_notion.databases.create.assert_called()
        mock_hunter_api.assert_called()
        mock_resend_emails.send.assert_called()
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_api_error_handling_and_fallbacks(self, mock_azure_openai):
        """Test API error handling and fallback mechanisms."""
        
        # Setup AI client to fail intermittently
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        call_count = [0]
        def mock_api_with_failures(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] % 3 == 0:  # Every 3rd call fails
                raise Exception("API Error")
            
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "name": "Test",
                "description": "Test",
                "features": [],
                "pricing_model": "free",
                "target_market": "everyone",
                "competitors": []
            })
            return mock_response
        
        mock_client.chat.completions.create.side_effect = mock_api_with_failures
        
        # Initialize AI parser
        ai_parser = AIParser(self.config)
        
        # Test multiple parsing attempts
        num_attempts = 10
        successful_parses = 0
        failed_parses = 0
        
        for i in range(num_attempts):
            result = ai_parser.parse_product_info("test content")
            if result.success:
                successful_parses += 1
            else:
                failed_parses += 1
        
        # Verify error handling
        self.assertGreater(successful_parses, 0)  # Some should succeed
        self.assertGreater(failed_parses, 0)  # Some should fail
        self.assertEqual(successful_parses + failed_parses, num_attempts)
        
        # Verify retry mechanism was used
        self.assertGreater(mock_client.chat.completions.create.call_count, num_attempts)
    
    def test_rate_limiting_compliance(self):
        """Test that all services comply with rate limiting requirements."""
        
        # Test AI Parser rate limiting
        with patch('services.ai_parser.AzureOpenAI') as mock_azure_openai:
            mock_client = Mock()
            mock_azure_openai.return_value = mock_client
            
            # Mock successful response
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = '{"test": "data"}'
            mock_client.chat.completions.create.return_value = mock_response
            
            ai_parser = AIParser(self.config)
            
            # Make rapid requests
            start_time = time.time()
            for i in range(5):
                ai_parser.parse_product_info("test content")
            end_time = time.time()
            
            # Should take at least some time due to rate limiting
            self.assertGreater(end_time - start_time, 0.1)
        
        # Test Email Sender rate limiting
        with patch('services.email_sender.resend') as mock_resend:
            mock_resend.api_key = "test_key"
            mock_emails = Mock()
            mock_resend.Emails = mock_emails
            
            mock_response = Mock()
            mock_response.id = "email_123"
            mock_emails.send.return_value = mock_response
            
            email_sender = EmailSender(self.config)
            
            # Make rapid email sends
            start_time = time.time()
            for i in range(3):
                email_sender.send_email(
                    recipient_email=f"test{i}@example.com",
                    subject="Test",
                    html_body="<p>Test</p>"
                )
            end_time = time.time()
            
            # Should respect rate limiting
            self.assertGreater(end_time - start_time, 0.05)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)