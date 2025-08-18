"""
Integration tests for the ProspectAutomationController.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List

from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData, TeamMember, Prospect, ProspectStatus, LinkedInProfile, EmailData
from services.product_hunt_scraper import ProductData
from utils.config import Config


class TestProspectAutomationController:
    """Test cases for ProspectAutomationController."""
    
    @pytest.fixture
    def sample_company_data(self):
        """Create sample company data for testing."""
        return CompanyData(
            name="Test Company",
            domain="testcompany.com",
            product_url="https://producthunt.com/posts/test-product",
            description="A test company for automation",
            launch_date=datetime.now()
        )
    
    @pytest.fixture
    def sample_team_members(self):
        """Create sample team members for testing."""
        return [
            TeamMember(
                name="John Doe",
                role="CEO",
                company="Test Company",
                linkedin_url="https://linkedin.com/in/johndoe"
            ),
            TeamMember(
                name="Jane Smith",
                role="CTO",
                company="Test Company",
                linkedin_url="https://linkedin.com/in/janesmith"
            )
        ]
    
    @pytest.fixture
    def sample_linkedin_profile(self):
        """Create sample LinkedIn profile for testing."""
        return LinkedInProfile(
            name="John Doe",
            current_role="CEO at Test Company",
            experience=["Previous role at Another Company"],
            skills=["Leadership", "Strategy", "Product Management"],
            summary="Experienced CEO with a passion for innovation"
        )
    
    @pytest.fixture
    def sample_email_data(self):
        """Create sample email data for testing."""
        return EmailData(
            email="john@testcompany.com",
            first_name="John",
            last_name="Doe",
            position="CEO",
            confidence=95
        )
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_controller_initialization(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                     mock_notion, mock_scraper, mock_config):
        """Test controller initialization with all services."""
        controller = ProspectAutomationController(mock_config)
        
        # Verify all services were initialized
        mock_scraper.assert_called_once_with(mock_config)
        mock_notion.assert_called_once_with(mock_config)
        mock_email_finder.assert_called_once_with(mock_config)
        mock_linkedin.assert_called_once_with(mock_config)
        mock_email_gen.assert_called_once_with(config=mock_config)
        
        # Verify controller attributes
        assert controller.config == mock_config
        assert controller.stats['companies_processed'] == 0
        assert controller.stats['prospects_found'] == 0
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_discover_companies(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                              mock_notion, mock_scraper, mock_config):
        """Test company discovery from ProductHunt."""
        # Setup mocks
        mock_product = Mock(spec=ProductData)
        mock_product.company_name = "Test Company"
        mock_product.website_url = "https://testcompany.com"
        mock_product.product_url = "https://producthunt.com/posts/test"
        mock_product.description = "Test description"
        mock_product.launch_date = datetime.now()
        
        mock_scraper_instance = mock_scraper.return_value
        mock_scraper_instance.get_latest_products.return_value = [mock_product]
        
        controller = ProspectAutomationController(mock_config)
        companies = controller._discover_companies(5)
        
        # Verify scraper was called
        mock_scraper_instance.get_latest_products.assert_called_once_with(5)
        
        # Verify company data was created
        assert len(companies) == 1
        assert companies[0].name == "Test Company"
        assert companies[0].domain == "testcompany.com"
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_extract_team_members(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                mock_notion, mock_scraper, mock_config, sample_company_data, sample_team_members):
        """Test team member extraction."""
        # Setup mocks
        mock_scraper_instance = mock_scraper.return_value
        mock_scraper_instance.extract_team_info.return_value = sample_team_members
        
        controller = ProspectAutomationController(mock_config)
        team_members = controller._extract_team_members(sample_company_data)
        
        # Verify scraper was called
        mock_scraper_instance.extract_team_info.assert_called_once_with(sample_company_data.product_url)
        
        # Verify team members were returned
        assert len(team_members) == 2
        assert team_members[0].name == "John Doe"
        assert team_members[1].name == "Jane Smith"
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_find_team_emails(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                            mock_notion, mock_scraper, mock_config, sample_team_members):
        """Test email finding for team members."""
        # Setup mocks
        mock_email_results = {
            "John Doe": {
                'email_data': Mock(email="john@testcompany.com"),
                'verification': Mock(result="deliverable"),
                'is_deliverable': True,
                'confidence_score': 95
            }
        }
        
        mock_email_finder_instance = mock_email_finder.return_value
        mock_email_finder_instance.find_and_verify_team_emails.return_value = mock_email_results
        mock_email_finder_instance.get_best_emails.return_value = {"John Doe": "john@testcompany.com"}
        
        controller = ProspectAutomationController(mock_config)
        results = controller._find_team_emails(sample_team_members, "testcompany.com")
        
        # Verify email finder was called
        mock_email_finder_instance.find_and_verify_team_emails.assert_called_once_with(
            sample_team_members, "testcompany.com"
        )
        mock_email_finder_instance.get_best_emails.assert_called_once_with(mock_email_results, min_confidence=70)
        
        # Verify results
        assert "John Doe" in results
        assert results["John Doe"]['email_data'].email == "john@testcompany.com"
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_extract_linkedin_profiles(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                     mock_notion, mock_scraper, mock_config, sample_team_members, sample_linkedin_profile):
        """Test LinkedIn profile extraction."""
        # Setup mocks
        mock_linkedin_instance = mock_linkedin.return_value
        mock_linkedin_instance.extract_multiple_profiles.return_value = {
            "https://linkedin.com/in/johndoe": sample_linkedin_profile,
            "https://linkedin.com/in/janesmith": None  # Failed extraction
        }
        
        controller = ProspectAutomationController(mock_config)
        profiles = controller._extract_linkedin_profiles(sample_team_members)
        
        # Verify LinkedIn scraper was called
        expected_urls = ["https://linkedin.com/in/johndoe", "https://linkedin.com/in/janesmith"]
        mock_linkedin_instance.extract_multiple_profiles.assert_called_once_with(expected_urls)
        
        # Verify results (None results should be filtered out)
        assert len(profiles) == 1
        assert "https://linkedin.com/in/johndoe" in profiles
        assert profiles["https://linkedin.com/in/johndoe"].name == "John Doe"
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_create_prospect_from_team_member(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                            mock_notion, mock_scraper, mock_config, sample_company_data, 
                                            sample_linkedin_profile, sample_email_data):
        """Test prospect creation from team member data."""
        team_member = TeamMember(
            name="John Doe",
            role="CEO",
            company="Test Company",
            linkedin_url="https://linkedin.com/in/johndoe"
        )
        
        email_result = {
            'email_data': sample_email_data,
            'verification': Mock(result="deliverable"),
            'is_deliverable': True,
            'confidence_score': 95
        }
        
        controller = ProspectAutomationController(mock_config)
        prospect = controller._create_prospect_from_team_member(
            team_member, sample_company_data, email_result, sample_linkedin_profile
        )
        
        # Verify prospect was created correctly
        assert prospect is not None
        assert prospect.name == "John Doe"
        assert prospect.role == "CEO"
        assert prospect.company == "Test Company"
        assert prospect.email == "john@testcompany.com"
        assert prospect.linkedin_url == "https://linkedin.com/in/johndoe"
        assert prospect.status == ProspectStatus.NOT_CONTACTED
        assert prospect.source_url == sample_company_data.product_url
        assert "LinkedIn Summary:" in prospect.notes
        assert "Skills:" in prospect.notes
        assert "Email verification:" in prospect.notes
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('controllers.prospect_automation_controller.ProductAnalyzer')
    @patch('controllers.prospect_automation_controller.AIParser')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_process_company_integration(self, mock_sleep, mock_ai_parser, mock_product_analyzer, 
                                       mock_email_gen, mock_linkedin, mock_email_finder, 
                                       mock_notion, mock_scraper, mock_config, sample_company_data, 
                                       sample_team_members, sample_linkedin_profile, sample_email_data):
        """Test complete company processing workflow with enhanced AI workflow."""
        # Setup mocks for enhanced workflow
        mock_scraper_instance = mock_scraper.return_value
        mock_scraper_instance.extract_team_info.return_value = sample_team_members
        
        # Mock AI Parser
        mock_ai_parser_instance = mock_ai_parser.return_value
        mock_ai_parser_instance.structure_team_data.return_value = Mock(success=True, data=sample_team_members)
        mock_ai_parser_instance.parse_linkedin_profile.return_value = Mock(success=True, data=sample_linkedin_profile)
        mock_ai_parser_instance.extract_business_metrics.return_value = Mock(success=True, data=Mock())
        
        # Mock AI Parser client for chat completions
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "AI generated summary"
        
        mock_ai_parser_instance.client = Mock()
        mock_ai_parser_instance.client.chat = Mock()
        mock_ai_parser_instance.client.chat.completions = Mock()
        mock_ai_parser_instance.client.chat.completions.create = Mock(return_value=mock_response)
        mock_ai_parser_instance.model_name = "gpt-3.5-turbo"
        
        # Mock Product Analyzer
        mock_product_analyzer_instance = mock_product_analyzer.return_value
        mock_product_analysis = Mock()
        mock_product_analysis.basic_info = Mock()
        mock_product_analysis.basic_info.name = "Test Product"
        mock_product_analysis.basic_info.description = "Test description"
        mock_product_analysis.features = []
        mock_product_analysis.pricing = Mock()
        mock_product_analysis.pricing.model = "freemium"
        mock_product_analysis.market_analysis = Mock()
        mock_product_analysis.market_analysis.target_market = "B2B"
        mock_product_analysis.market_analysis.competitors = []
        mock_product_analysis.funding_info = None
        mock_product_analyzer_instance.analyze_product.return_value = mock_product_analysis
        
        mock_email_results = {
            "John Doe": {
                'email_data': sample_email_data,
                'verification': Mock(result="deliverable"),
                'is_deliverable': True,
                'confidence_score': 95
            }
        }
        mock_email_finder_instance = mock_email_finder.return_value
        mock_email_finder_instance.find_and_verify_team_emails.return_value = mock_email_results
        mock_email_finder_instance.get_best_emails.return_value = {"John Doe": "john@testcompany.com"}
        
        # Mock LinkedIn scraper for enhanced workflow
        mock_linkedin_instance = mock_linkedin.return_value
        mock_linkedin_profile_with_html = Mock()
        mock_linkedin_profile_with_html.name = sample_linkedin_profile.name
        mock_linkedin_profile_with_html.current_role = sample_linkedin_profile.current_role
        mock_linkedin_profile_with_html.experience = sample_linkedin_profile.experience
        mock_linkedin_profile_with_html.skills = sample_linkedin_profile.skills
        mock_linkedin_profile_with_html.summary = sample_linkedin_profile.summary
        mock_linkedin_profile_with_html.raw_html = "<html>Mock LinkedIn HTML</html>"
        mock_linkedin_instance.extract_profile_data.return_value = mock_linkedin_profile_with_html
        
        # Mock Notion manager for enhanced workflow
        mock_notion_instance = mock_notion.return_value
        mock_notion_instance.store_ai_structured_data.return_value = "test_page_id"
        
        controller = ProspectAutomationController(mock_config)
        prospects = controller.process_company(sample_company_data)
        
        # Verify enhanced workflow steps were executed
        mock_product_analyzer_instance.analyze_product.assert_called_once()
        mock_ai_parser_instance.structure_team_data.assert_called_once()
        mock_email_finder_instance.find_and_verify_team_emails.assert_called_once()
        mock_linkedin_instance.extract_profile_data.assert_called()  # Called for each team member
        mock_notion_instance.store_ai_structured_data.assert_called()  # Called for each prospect
        
        # Verify prospects were created and stored
        assert len(prospects) == 2  # Both team members should be processed
        assert all(p.id == "test_page_id" for p in prospects)
        
        # Verify statistics were updated
        assert controller.stats['prospects_found'] == 2
        assert controller.stats['emails_found'] == 1  # Only John Doe has email
        assert controller.stats['linkedin_profiles_extracted'] == 2  # Both team members have LinkedIn profiles
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_error_handling_in_process_company(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                             mock_notion, mock_scraper, mock_config, sample_company_data):
        """Test error handling during company processing."""
        # Setup mock to raise exception
        mock_scraper_instance = mock_scraper.return_value
        mock_scraper_instance.extract_team_info.side_effect = Exception("Scraping failed")
        
        controller = ProspectAutomationController(mock_config)
        
        # Should not raise exception, but return empty list
        prospects = controller.process_company(sample_company_data)
        
        assert prospects == []
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_get_workflow_status(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                               mock_notion, mock_scraper, mock_config):
        """Test workflow status reporting."""
        controller = ProspectAutomationController(mock_config)
        
        status = controller.get_workflow_status()
        
        assert 'is_running' in status
        assert 'current_stats' in status
        assert 'services_status' in status
        assert status['is_running'] is False  # Not running initially
        assert status['services_status']['product_hunt_scraper'] == 'initialized'
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_pipeline_results_calculation(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                        mock_notion, mock_scraper, mock_config):
        """Test pipeline results and statistics calculation."""
        controller = ProspectAutomationController(mock_config)
        
        # Simulate some processing
        controller.stats['companies_processed'] = 5
        controller.stats['prospects_found'] = 12
        controller.stats['emails_found'] = 8
        controller.stats['errors'] = 1
        controller.stats['start_time'] = datetime.now()
        controller.stats['end_time'] = datetime.now()
        
        results = controller._get_pipeline_results()
        
        assert results['statistics']['companies_processed'] == 5
        assert results['statistics']['prospects_found'] == 12
        assert results['summary']['success_rate'] > 0  # Should calculate success rate
        assert 'duration_seconds' in results['summary']
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_batch_processing_initialization(self, mock_sleep, mock_email_gen, mock_linkedin, 
                                           mock_email_finder, mock_notion, mock_scraper, 
                                           mock_config, sample_company_data):
        """Test batch processing initialization."""
        # Setup mocks
        mock_notion_instance = mock_notion.return_value
        mock_notion_instance.store_prospect.return_value = "batch_progress_id"
        
        controller = ProspectAutomationController(mock_config)
        companies = [sample_company_data]
        
        # Mock the processing methods to avoid actual processing
        controller._process_company_with_tracking = Mock(return_value=Mock(
            company_name="Test Company",
            success=True,
            prospects_found=2,
            emails_found=1,
            linkedin_profiles_found=1,
            processing_time=1.5
        ))
        
        results = controller.run_batch_processing(companies, batch_size=1)
        
        # Verify batch was initialized
        assert controller.current_batch is not None
        assert controller.current_batch.total_companies == 1
        assert controller.current_batch.status.value == "completed"
        
        # Verify results structure
        assert 'batch_id' in results
        assert 'status' in results
        assert 'summary' in results
        assert 'detailed_results' in results
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_batch_progress_tracking(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                   mock_notion, mock_scraper, mock_config):
        """Test batch progress tracking functionality."""
        from controllers.prospect_automation_controller import BatchProgress, ProcessingStatus
        
        controller = ProspectAutomationController(mock_config)
        
        # Create a mock batch progress
        batch_progress = BatchProgress(
            batch_id="test_batch_123",
            status=ProcessingStatus.IN_PROGRESS,
            total_companies=10,
            processed_companies=5,
            successful_companies=4,
            failed_companies=1,
            total_prospects=15,
            start_time=datetime.now(),
            last_update_time=datetime.now()
        )
        
        controller.current_batch = batch_progress
        
        # Test progress retrieval
        current_progress = controller.get_batch_progress()
        assert current_progress is not None
        assert current_progress.batch_id == "test_batch_123"
        assert current_progress.processed_companies == 5
        assert current_progress.successful_companies == 4
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_batch_pause_and_resume(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                   mock_notion, mock_scraper, mock_config):
        """Test batch processing pause and resume functionality."""
        from controllers.prospect_automation_controller import BatchProgress, ProcessingStatus
        
        controller = ProspectAutomationController(mock_config)
        
        # Create a running batch
        controller.current_batch = BatchProgress(
            batch_id="test_batch_pause",
            status=ProcessingStatus.IN_PROGRESS,
            total_companies=10,
            processed_companies=3,
            successful_companies=3,
            failed_companies=0,
            total_prospects=8,
            start_time=datetime.now(),
            last_update_time=datetime.now()
        )
        
        # Test pause
        paused = controller.pause_batch_processing()
        assert paused is True
        assert controller.current_batch.status == ProcessingStatus.PAUSED
        
        # Test pause when no batch is running
        controller.current_batch = None
        paused = controller.pause_batch_processing()
        assert paused is False
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_batch_progress_serialization(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                        mock_notion, mock_scraper, mock_config):
        """Test batch progress serialization and deserialization."""
        from controllers.prospect_automation_controller import BatchProgress, ProcessingStatus
        
        # Create batch progress
        original_progress = BatchProgress(
            batch_id="test_serialization",
            status=ProcessingStatus.IN_PROGRESS,
            total_companies=5,
            processed_companies=2,
            successful_companies=2,
            failed_companies=0,
            total_prospects=6,
            start_time=datetime.now(),
            last_update_time=datetime.now(),
            current_company="Test Company"
        )
        
        # Test serialization
        progress_dict = original_progress.to_dict()
        assert progress_dict['batch_id'] == "test_serialization"
        assert progress_dict['status'] == "in_progress"
        assert progress_dict['total_companies'] == 5
        assert 'start_time' in progress_dict
        
        # Test deserialization
        restored_progress = BatchProgress.from_dict(progress_dict)
        assert restored_progress.batch_id == original_progress.batch_id
        assert restored_progress.status == original_progress.status
        assert restored_progress.total_companies == original_progress.total_companies
        assert restored_progress.current_company == original_progress.current_company
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_progress_callbacks(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                              mock_notion, mock_scraper, mock_config):
        """Test progress callback functionality."""
        from controllers.prospect_automation_controller import CompanyProcessingResult
        
        controller = ProspectAutomationController(mock_config)
        
        # Create mock callback
        callback_mock = Mock()
        controller.add_progress_callback(callback_mock)
        
        # Create a batch progress
        from controllers.prospect_automation_controller import BatchProgress, ProcessingStatus
        controller.current_batch = BatchProgress(
            batch_id="test_callbacks",
            status=ProcessingStatus.IN_PROGRESS,
            total_companies=1,
            processed_companies=0,
            successful_companies=0,
            failed_companies=0,
            total_prospects=0,
            start_time=datetime.now(),
            last_update_time=datetime.now()
        )
        
        # Simulate progress update
        result = CompanyProcessingResult(
            company_name="Test Company",
            success=True,
            prospects_found=2,
            emails_found=1,
            linkedin_profiles_found=1,
            processing_time=1.0
        )
        
        controller._update_batch_progress("Test Company", result)
        
        # Verify callback was called
        callback_mock.assert_called_once()
        called_progress = callback_mock.call_args[0][0]
        assert called_progress.processed_companies == 1
        assert called_progress.successful_companies == 1
        
        # Test callback removal
        controller.remove_progress_callback(callback_mock)
        assert callback_mock not in controller.progress_callbacks
    
    @patch('controllers.prospect_automation_controller.ProductHuntScraper')
    @patch('controllers.prospect_automation_controller.NotionDataManager')
    @patch('controllers.prospect_automation_controller.EmailFinder')
    @patch('controllers.prospect_automation_controller.LinkedInScraper')
    @patch('controllers.prospect_automation_controller.EmailGenerator')
    def test_batch_results_calculation(self, mock_email_gen, mock_linkedin, mock_email_finder, 
                                     mock_notion, mock_scraper, mock_config):
        """Test batch results calculation and statistics."""
        from controllers.prospect_automation_controller import BatchProgress, ProcessingStatus, CompanyProcessingResult
        
        controller = ProspectAutomationController(mock_config)
        
        # Set up batch progress
        controller.current_batch = BatchProgress(
            batch_id="test_results",
            status=ProcessingStatus.COMPLETED,
            total_companies=3,
            processed_companies=3,
            successful_companies=2,
            failed_companies=1,
            total_prospects=5,
            start_time=datetime.now(),
            last_update_time=datetime.now(),
            end_time=datetime.now()
        )
        
        # Add some batch results
        controller.batch_results = [
            CompanyProcessingResult(
                company_name="Company 1",
                success=True,
                prospects_found=2,
                emails_found=1,
                linkedin_profiles_found=1,
                processing_time=2.5
            ),
            CompanyProcessingResult(
                company_name="Company 2",
                success=True,
                prospects_found=3,
                emails_found=2,
                linkedin_profiles_found=1,
                processing_time=3.0
            ),
            CompanyProcessingResult(
                company_name="Company 3",
                success=False,
                prospects_found=0,
                emails_found=0,
                linkedin_profiles_found=0,
                error_message="Processing failed",
                processing_time=1.0
            )
        ]
        
        results = controller._get_batch_results()
        
        # Verify results structure
        assert results['batch_id'] == "test_results"
        assert results['status'] == "completed"
        assert results['summary']['total_companies'] == 3
        assert results['summary']['successful_companies'] == 2
        assert results['summary']['failed_companies'] == 1
        assert abs(results['summary']['success_rate'] - 66.67) < 0.1  # 2 successful out of 3 processed
        assert results['summary']['total_processing_time'] == 6.5  # 2.5 + 3.0 + 1.0
        assert results['summary']['average_processing_time'] == 6.5/3
        
        # Verify detailed results
        assert len(results['detailed_results']) == 3
        assert results['detailed_results'][0]['company_name'] == "Company 1"
        assert results['detailed_results'][0]['success'] is True
        assert results['detailed_results'][2]['success'] is False
        assert results['detailed_results'][2]['error_message'] == "Processing failed"