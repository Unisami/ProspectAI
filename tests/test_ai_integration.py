"""
Integration tests for AI parsing integration with scrapers.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from services.linkedin_scraper import LinkedInScraper
from services.product_hunt_scraper import ProductHuntScraper
from services.ai_parser import AIParser, ParseResult
from models.data_models import LinkedInProfile, TeamMember
from utils.config import Config


class TestLinkedInScraperAIIntegration(unittest.TestCase):
    """Test cases for LinkedIn scraper AI integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.use_azure_openai = True
        self.mock_config.azure_openai_api_key = "test-key"
        self.mock_config.azure_openai_endpoint = "https://test.openai.azure.com/"
        self.mock_config.azure_openai_deployment_name = "gpt-4"
        self.mock_config.azure_openai_api_version = "2024-02-15-preview"
        self.mock_config.linkedin_scraping_delay = 1.0
        
        # Sample HTML content
        self.sample_html = """
        <html>
            <div class="pv-text-details__left-panel">
                <h1>John Doe</h1>
                <div class="text-body-medium">Senior Software Engineer at TechCorp</div>
            </div>
            <section class="pv-profile-section pv-about-section">
                <p>Experienced software engineer with 8+ years in full-stack development...</p>
            </section>
        </html>
        """
    
    @patch('services.linkedin_scraper.webdriver.Chrome')
    @patch('services.ai_parser.get_client_manager')
    def test_linkedin_scraper_with_ai_parsing_success(self, mock_get_client_manager, mock_webdriver):
        """Test LinkedIn scraper with successful AI parsing."""
        # Setup AI parser mock
        mock_client_manager = Mock()
        mock_get_client_manager.return_value = mock_client_manager
        
        mock_completion_response = json.dumps({
            "name": "John Doe",
            "current_role": "Senior Software Engineer at TechCorp",
            "experience": ["Senior Software Engineer at TechCorp (2020-Present)"],
            "skills": ["Python", "JavaScript", "React"],
            "summary": "Experienced software engineer with 8+ years in development"
        })
        mock_client_manager.make_completion.return_value = mock_completion_response
        
        # Setup WebDriver mock
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        mock_driver.page_source = self.sample_html
        
        # Mock traditional extraction methods
        mock_driver.find_element.return_value.text = "John Doe"
        mock_driver.find_elements.return_value = []
        
        scraper = LinkedInScraper(self.mock_config)
        
        # Verify AI parser was initialized
        self.assertTrue(scraper.use_ai_parsing)
        self.assertIsNotNone(scraper.ai_parser)
        
        # Test profile extraction
        profile = scraper.extract_profile_data("https://linkedin.com/in/john-doe")
        
        # Verify results
        self.assertIsNotNone(profile)
        self.assertEqual(profile.name, "John Doe")
        self.assertEqual(profile.current_role, "Senior Software Engineer")
        self.assertEqual(profile.company, "TechCorp")
        self.assertEqual(len(profile.skills), 3)
        
        # Verify AI parsing was called
        mock_client_manager.make_completion.assert_called_once()
    
    @patch('services.linkedin_scraper.webdriver.Chrome')
    @patch('services.ai_parser.get_client_manager')
    def test_linkedin_scraper_ai_fallback_to_traditional(self, mock_get_client_manager, mock_webdriver):
        """Test LinkedIn scraper falls back to traditional parsing when AI fails."""
        # Setup AI parser mock to fail
        mock_client_manager = Mock()
        mock_get_client_manager.return_value = mock_client_manager
        mock_client_manager.make_completion.side_effect = Exception("AI parsing failed")
        
        # Setup WebDriver mock
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        mock_driver.page_source = self.sample_html
        
        # Mock traditional extraction methods
        def mock_find_element(by, selector):
            mock_elem = Mock()
            if "h1" in selector:
                mock_elem.text = "John Doe"
            elif "text-body-medium" in selector:
                mock_elem.text = "Senior Software Engineer at TechCorp"
            else:
                mock_elem.text = ""
            return mock_elem
        
        # Mock the _extract_text_safely method to return proper values
        def mock_extract_text_safely(driver, selector, multiple=False):
            if multiple:
                return []
            if "h1" in selector:
                return "John Doe"
            elif "text-body-medium" in selector:
                return "Senior Software Engineer at TechCorp"
            else:
                return ""
        
        mock_driver.find_element.side_effect = mock_find_element
        mock_driver.find_elements.return_value = []
        
        scraper = LinkedInScraper(self.mock_config)
        
        # Mock the traditional extraction method to return proper fallback data
        with patch.object(scraper, '_extract_traditional_profile_data') as mock_traditional:
            mock_traditional.return_value = {
                'name': 'John Doe',
                'current_role': 'Senior Software Engineer at TechCorp',  # Include company in role
                'company': 'TechCorp',
                'location': '',
                'summary': '',
                'experience': [],
                'skills': [],
                'education': []
            }
            
            profile = scraper.extract_profile_data("https://linkedin.com/in/john-doe")
        
            # Verify fallback worked (AI parser uses fallback data when it fails)
            self.assertIsNotNone(profile)
            self.assertEqual(profile.name, "John Doe")
            # The AI parser fallback will extract company from the current_role
            self.assertEqual(profile.current_role, "Senior Software Engineer")
            self.assertEqual(profile.company, "TechCorp")
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_linkedin_scraper_ai_initialization_failure(self, mock_azure_openai):
        """Test LinkedIn scraper handles AI parser initialization failure gracefully."""
        # Make AI parser initialization fail
        mock_azure_openai.side_effect = Exception("Failed to initialize AI parser")
        
        scraper = LinkedInScraper(self.mock_config)
        
        # Verify fallback to traditional parsing
        self.assertFalse(scraper.use_ai_parsing)
        self.assertIsNone(scraper.ai_parser)


class TestProductHuntScraperAIIntegration(unittest.TestCase):
    """Test cases for ProductHunt scraper AI integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock config
        self.mock_config = Mock(spec=Config)
        self.mock_config.use_azure_openai = True
        self.mock_config.azure_openai_api_key = "test-key"
        self.mock_config.azure_openai_endpoint = "https://test.openai.azure.com/"
        self.mock_config.azure_openai_deployment_name = "gpt-4"
        self.mock_config.azure_openai_api_version = "2024-02-15-preview"
        self.mock_config.scraping_delay = 1.0
        
        # Sample team content
        self.sample_team_content = """
        Meet the Team:
        
        Sarah Johnson - CEO & Co-founder
        LinkedIn: https://linkedin.com/in/sarah-johnson-ceo
        
        Mike Chen - CTO & Co-founder  
        LinkedIn: https://linkedin.com/in/mike-chen-cto
        
        Emily Rodriguez - Head of Product
        LinkedIn: https://linkedin.com/in/emily-rodriguez-product
        """
    
    @patch('services.product_hunt_scraper.webdriver.Chrome')
    @patch('services.ai_parser.AzureOpenAI')
    def test_product_hunt_scraper_with_ai_parsing_success(self, mock_azure_openai, mock_webdriver):
        """Test ProductHunt scraper with successful AI team parsing."""
        # Setup AI parser mock
        mock_ai_client = Mock()
        mock_azure_openai.return_value = mock_ai_client
        
        mock_ai_response = Mock()
        mock_ai_response.choices = [Mock()]
        mock_ai_response.choices[0].message.content = json.dumps([
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
        mock_ai_client.chat.completions.create.return_value = mock_ai_response
        
        # Setup WebDriver mock
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        mock_driver.page_source = f"<html><body>{self.sample_team_content}</body></html>"
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Verify AI parser was initialized
        self.assertTrue(scraper.use_ai_parsing)
        self.assertIsNotNone(scraper.ai_parser)
        
        # Test team extraction
        team_members = scraper.extract_team_info("https://producthunt.com/posts/taskmaster")
        
        # Verify results
        self.assertEqual(len(team_members), 2)
        
        # Check first team member
        first_member = team_members[0]
        self.assertEqual(first_member.name, "Sarah Johnson")
        self.assertEqual(first_member.role, "CEO & Co-founder")
        self.assertEqual(first_member.company, "Taskmaster")  # Company name extracted from URL
        self.assertIn("linkedin.com", first_member.linkedin_url)
        
        # Verify AI parsing was called
        mock_ai_client.chat.completions.create.assert_called_once()
    
    @patch('services.product_hunt_scraper.webdriver.Chrome')
    @patch('services.ai_parser.AzureOpenAI')
    def test_product_hunt_scraper_ai_fallback_to_traditional(self, mock_azure_openai, mock_webdriver):
        """Test ProductHunt scraper falls back to traditional parsing when AI fails."""
        # Setup AI parser mock to fail
        mock_ai_client = Mock()
        mock_azure_openai.return_value = mock_ai_client
        mock_ai_client.chat.completions.create.side_effect = Exception("AI parsing failed")
        
        # Setup WebDriver mock
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        
        # Create mock soup with team content
        mock_soup_content = f"<html><body>{self.sample_team_content}</body></html>"
        mock_driver.page_source = mock_soup_content
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Mock the traditional extraction method to return some team members
        with patch.object(scraper, '_extract_team_from_soup') as mock_extract:
            mock_extract.return_value = [
                TeamMember(
                    name="Sarah Johnson",
                    role="CEO",
                    company="TaskMaster",
                    linkedin_url="https://linkedin.com/in/sarah-johnson-ceo"
                )
            ]
            
            team_members = scraper.extract_team_info("https://producthunt.com/posts/taskmaster")
            
            # Verify fallback worked
            self.assertEqual(len(team_members), 1)
            self.assertEqual(team_members[0].name, "Sarah Johnson")
            mock_extract.assert_called_once()
    
    @patch('services.product_hunt_scraper.webdriver.Chrome')
    @patch('services.ai_parser.AzureOpenAI')
    def test_product_hunt_scraper_ai_low_confidence_enhancement(self, mock_azure_openai, mock_webdriver):
        """Test ProductHunt scraper enhances low-confidence AI results with traditional parsing."""
        # Setup AI parser mock with low confidence
        mock_ai_client = Mock()
        mock_azure_openai.return_value = mock_ai_client
        
        mock_ai_response = Mock()
        mock_ai_response.choices = [Mock()]
        mock_ai_response.choices[0].message.content = json.dumps([
            {
                "name": "Sarah Johnson",
                "role": "CEO",
                "company": "TaskMaster",
                "linkedin_url": ""  # Missing LinkedIn URL
            }
        ])
        mock_ai_client.chat.completions.create.return_value = mock_ai_response
        
        # Setup WebDriver mock
        mock_driver = Mock()
        mock_webdriver.return_value = mock_driver
        mock_driver.page_source = f"<html><body>{self.sample_team_content}</body></html>"
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Mock AI parser to return low confidence
        with patch.object(scraper.ai_parser, 'structure_team_data') as mock_ai_parse:
            mock_ai_parse.return_value = ParseResult(
                success=True,
                data=[TeamMember(name="Sarah Johnson", role="CEO", company="TaskMaster", linkedin_url="")],
                confidence_score=0.5  # Low confidence
            )
            
            # Mock traditional extraction to provide enhancement
            with patch.object(scraper, '_extract_team_from_soup') as mock_traditional:
                mock_traditional.return_value = [
                    TeamMember(
                        name="Sarah Johnson",
                        role="CEO & Co-founder",
                        company="TaskMaster",
                        linkedin_url="https://linkedin.com/in/sarah-johnson-ceo"
                    )
                ]
                
                team_members = scraper.extract_team_info("https://producthunt.com/posts/taskmaster")
                
                # Verify enhancement occurred
                self.assertEqual(len(team_members), 1)
                enhanced_member = team_members[0]
                self.assertEqual(enhanced_member.name, "Sarah Johnson")
                # Should have enhanced LinkedIn URL from traditional parsing
                self.assertIn("linkedin.com", enhanced_member.linkedin_url)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_product_hunt_scraper_ai_initialization_failure(self, mock_azure_openai):
        """Test ProductHunt scraper handles AI parser initialization failure gracefully."""
        # Make AI parser initialization fail
        mock_azure_openai.side_effect = Exception("Failed to initialize AI parser")
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Verify fallback to traditional parsing
        self.assertFalse(scraper.use_ai_parsing)
        self.assertIsNone(scraper.ai_parser)


class TestAIParsingHelperMethods(unittest.TestCase):
    """Test cases for AI parsing helper methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.use_azure_openai = True
        self.mock_config.azure_openai_api_key = "test-key"
        self.mock_config.azure_openai_endpoint = "https://test.openai.azure.com/"
        self.mock_config.azure_openai_deployment_name = "gpt-4"
        self.mock_config.azure_openai_api_version = "2024-02-15-preview"
        self.mock_config.scraping_delay = 1.0
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_extract_company_from_role(self, mock_azure_openai):
        """Test company extraction from role text."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        scraper = LinkedInScraper(self.mock_config)
        
        # Test various role formats
        test_cases = [
            ("Senior Engineer at Google", "Google"),
            ("Product Manager at Microsoft Corporation", "Microsoft Corporation"),
            ("CEO at Startup Inc.", "Startup Inc."),
            ("Freelance Developer", None),
            ("", None),
            (None, None)
        ]
        
        for role, expected_company in test_cases:
            with self.subTest(role=role):
                result = scraper._extract_company_from_role(role)
                self.assertEqual(result, expected_company)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_names_similar(self, mock_azure_openai):
        """Test name similarity checking."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Test various name similarity cases
        test_cases = [
            ("John Doe", "John Doe", True),  # Exact match
            ("John Doe", "john doe", True),  # Case insensitive
            ("John", "John Doe", True),  # Partial match
            ("John Doe", "John", True),  # Reverse partial match
            ("John Smith", "Jane Smith", True),  # Common surname
            ("John Doe", "Jane Doe", True),  # Common surname
            ("John Smith", "Bob Johnson", False),  # No similarity
            ("", "John Doe", False),  # Empty name
            ("John Doe", "", False),  # Empty name
        ]
        
        for name1, name2, expected in test_cases:
            with self.subTest(name1=name1, name2=name2):
                result = scraper._names_similar(name1, name2)
                self.assertEqual(result, expected)
    
    @patch('services.ai_parser.AzureOpenAI')
    def test_merge_team_data(self, mock_azure_openai):
        """Test merging AI and traditional team data."""
        mock_client = Mock()
        mock_azure_openai.return_value = mock_client
        
        scraper = ProductHuntScraper(self.mock_config)
        
        # Create test data
        ai_members = [
            TeamMember(name="John Doe", role="CEO", company="TestCorp", linkedin_url=""),
            TeamMember(name="Jane Smith", role="CTO", company="TestCorp", linkedin_url="https://linkedin.com/in/jane")
        ]
        
        traditional_members = [
            TeamMember(name="John Doe", role="CEO & Founder", company="TestCorp", linkedin_url="https://linkedin.com/in/john"),
            TeamMember(name="Bob Johnson", role="Engineer", company="TestCorp", linkedin_url="https://linkedin.com/in/bob")
        ]
        
        merged = scraper._merge_team_data(ai_members, traditional_members)
        
        # Should have 3 unique members (John enhanced, Jane unchanged, Bob added)
        self.assertEqual(len(merged), 3)
        
        # Find John Doe in merged results
        john = next((m for m in merged if m.name == "John Doe"), None)
        self.assertIsNotNone(john)
        # Should have LinkedIn URL from traditional parsing
        self.assertEqual(john.linkedin_url, "https://linkedin.com/in/john")
        
        # Should have Bob from traditional parsing
        bob = next((m for m in merged if m.name == "Bob Johnson"), None)
        self.assertIsNotNone(bob)


if __name__ == '__main__':
    unittest.main()