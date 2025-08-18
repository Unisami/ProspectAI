"""
Tests for the test utilities module.

This module tests the shared test utilities and fixtures to ensure they work correctly
and provide consistent, reliable test data.
"""

import pytest
import os
import tempfile
import json
from datetime import datetime
from unittest.mock import Mock, patch

from tests.test_utilities import (
    TestUtilities, MockExternalServices, PerformanceTestUtilities
)
from models.data_models import (
    CompanyData, TeamMember, LinkedInProfile, Prospect, 
    ProspectStatus, EmailContent, SenderProfile
)
# Skip config import due to circular dependencies
# from utils.config import Config
# Skip validation framework import due to dependencies
# from utils.validation_framework import ValidationResult, ValidationSeverity


class TestTestUtilities:
    """Test cases for TestUtilities class."""
    
    def test_create_mock_config_defaults(self):
        """Test creating mock config with default values."""
        config = TestUtilities.create_mock_config()
        
        # Verify essential attributes exist
        assert hasattr(config, 'notion_token')
        assert hasattr(config, 'hunter_api_key')
        assert hasattr(config, 'openai_api_key')
        assert hasattr(config, 'scraping_delay')
        
        # Verify default values
        assert config.notion_token == 'test_notion_token'
        assert config.hunter_api_key == 'test_hunter_key'
        assert config.openai_api_key == 'test_openai_key'
        assert config.scraping_delay == 0.1  # Faster for tests
        assert config.use_azure_openai is False
        assert config.enable_ai_parsing is True
    
    def test_create_mock_config_with_overrides(self):
        """Test creating mock config with custom overrides."""
        overrides = {
            'notion_token': 'custom_token',
            'scraping_delay': 0.5,
            'use_azure_openai': True,
            'custom_field': 'custom_value'
        }
        
        config = TestUtilities.create_mock_config(**overrides)
        
        # Verify overrides applied
        assert config.notion_token == 'custom_token'
        assert config.scraping_delay == 0.5
        assert config.use_azure_openai is True
        assert config.custom_field == 'custom_value'
        
        # Verify defaults still exist
        assert config.hunter_api_key == 'test_hunter_key'
        assert config.openai_api_key == 'test_openai_key'
    
    def test_create_test_company_data_defaults(self):
        """Test creating test company data with defaults."""
        company = TestUtilities.create_test_company_data()
        
        assert company.name == TestUtilities.TEST_COMPANY_NAME
        assert company.domain == TestUtilities.TEST_DOMAIN
        assert company.product_url == TestUtilities.TEST_PRODUCT_URL
        assert company.description == TestUtilities.TEST_DESCRIPTION
        assert isinstance(company.launch_date, datetime)
    
    def test_create_test_company_data_with_overrides(self):
        """Test creating test company data with custom values."""
        custom_date = datetime(2023, 6, 15)
        overrides = {
            'name': 'Custom Corp',
            'domain': 'custom.com',
            'launch_date': custom_date
        }
        
        company = TestUtilities.create_test_company_data(**overrides)
        
        assert company.name == 'Custom Corp'
        assert company.domain == 'custom.com'
        assert company.launch_date == custom_date
        # Verify defaults still exist
        assert company.product_url == TestUtilities.TEST_PRODUCT_URL
        assert company.description == TestUtilities.TEST_DESCRIPTION
    
    def test_create_test_team_member_defaults(self):
        """Test creating test team member with defaults."""
        member = TestUtilities.create_test_team_member()
        
        assert member.name == 'John Doe'
        assert member.title == 'Software Engineer'
        assert member.linkedin_url == TestUtilities.TEST_LINKEDIN_URL
        assert member.email == TestUtilities.TEST_EMAIL
        assert member.company_domain == TestUtilities.TEST_DOMAIN
    
    def test_create_test_team_member_with_overrides(self):
        """Test creating test team member with custom values."""
        overrides = {
            'name': 'Jane Smith',
            'title': 'Product Manager',
            'email': 'jane@example.com'
        }
        
        member = TestUtilities.create_test_team_member(**overrides)
        
        assert member.name == 'Jane Smith'
        assert member.title == 'Product Manager'
        assert member.email == 'jane@example.com'
        # Verify defaults still exist
        assert member.linkedin_url == TestUtilities.TEST_LINKEDIN_URL
        assert member.company_domain == TestUtilities.TEST_DOMAIN
    
    def test_create_test_linkedin_profile_defaults(self):
        """Test creating test LinkedIn profile with defaults."""
        profile = TestUtilities.create_test_linkedin_profile()
        
        assert profile.name == 'John Doe'
        assert profile.title == 'Software Engineer'
        assert profile.company == TestUtilities.TEST_COMPANY_NAME
        assert profile.location == 'San Francisco, CA'
        assert isinstance(profile.experience, list)
        assert isinstance(profile.education, list)
        assert isinstance(profile.skills, list)
        assert profile.url == TestUtilities.TEST_LINKEDIN_URL
    
    def test_create_test_linkedin_profile_with_overrides(self):
        """Test creating test LinkedIn profile with custom values."""
        custom_experience = [
            {
                'title': 'CTO',
                'company': 'Custom Corp',
                'duration': '2023 - Present',
                'description': 'Leading technology initiatives'
            }
        ]
        
        overrides = {
            'name': 'Jane Smith',
            'title': 'Chief Technology Officer',
            'experience': custom_experience
        }
        
        profile = TestUtilities.create_test_linkedin_profile(**overrides)
        
        assert profile.name == 'Jane Smith'
        assert profile.title == 'Chief Technology Officer'
        assert profile.experience == custom_experience
        # Verify defaults still exist
        assert profile.company == TestUtilities.TEST_COMPANY_NAME
        assert profile.location == 'San Francisco, CA'
    
    def test_create_test_prospect_defaults(self):
        """Test creating test prospect with defaults."""
        prospect = TestUtilities.create_test_prospect()
        
        assert prospect.name == 'John Doe'
        assert prospect.email == TestUtilities.TEST_EMAIL
        assert prospect.title == 'Software Engineer'
        assert prospect.company == TestUtilities.TEST_COMPANY_NAME
        assert prospect.linkedin_url == TestUtilities.TEST_LINKEDIN_URL
        assert prospect.status == ProspectStatus.NOT_CONTACTED
        assert isinstance(prospect.created_date, datetime)
        assert prospect.last_contacted is None
    
    def test_create_test_email_content_defaults(self):
        """Test creating test email content with defaults."""
        content = TestUtilities.create_test_email_content()
        
        assert content.subject == 'Exciting Opportunity at TestCorp'
        assert 'Hi John' in content.body
        assert content.personalization_notes == 'Mentioned their AI expertise'
        assert isinstance(content.generated_at, datetime)
    
    def test_create_test_sender_profile_defaults(self):
        """Test creating test sender profile with defaults."""
        profile = TestUtilities.create_test_sender_profile()
        
        assert profile.name == 'Test Sender'
        assert profile.email == 'test@example.com'
        assert profile.company == 'Test Company'
        assert profile.role == 'Hiring Manager'
        assert isinstance(profile.interests, list)
        assert profile.communication_style == 'professional'
    
    def test_create_test_validation_result_valid(self):
        """Test creating valid validation result."""
        result = TestUtilities.create_test_validation_result(is_valid=True)
        
        assert result.is_valid is True
        assert result.message == 'Validation passed'
        # Check severity value (could be enum or string)
        if hasattr(result.severity, 'value'):
            assert result.severity.value == 'info'
        else:
            assert result.severity == 'INFO'
        assert result.field_name == 'test_field'
    
    def test_create_test_validation_result_invalid(self):
        """Test creating invalid validation result."""
        result = TestUtilities.create_test_validation_result(
            is_valid=False,
            message='Custom error message',
            field_name='custom_field'
        )
        
        assert result.is_valid is False
        assert result.message == 'Custom error message'
        # Check severity value (could be enum or string)
        if hasattr(result.severity, 'value'):
            assert result.severity.value == 'error'
        else:
            assert result.severity == 'ERROR'
        assert result.field_name == 'custom_field'
    
    def test_create_temporary_config_file(self):
        """Test creating temporary configuration file."""
        config_data = {
            'notion_token': 'temp_token',
            'hunter_api_key': 'temp_key',
            'settings': {
                'delay': 1.0,
                'enabled': True
            }
        }
        
        file_path = TestUtilities.create_temporary_config_file(config_data)
        
        try:
            # Verify file exists
            assert os.path.exists(file_path)
            assert file_path.endswith('.yaml')
            
            # Verify content
            import yaml
            with open(file_path, 'r') as f:
                loaded_data = yaml.safe_load(f)
            
            assert loaded_data == config_data
        finally:
            # Clean up
            TestUtilities.cleanup_temporary_file(file_path)
            assert not os.path.exists(file_path)
    
    def test_cleanup_temporary_file_nonexistent(self):
        """Test cleaning up non-existent file doesn't raise error."""
        # Should not raise exception
        TestUtilities.cleanup_temporary_file('/nonexistent/file.yaml')


class TestMockExternalServices:
    """Test cases for MockExternalServices class."""
    
    def test_mock_openai_client(self):
        """Test OpenAI client mock."""
        mock_client = MockExternalServices.mock_openai_client()
        
        # Test completion call
        response = mock_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )
        
        assert hasattr(response, 'choices')
        assert len(response.choices) > 0
        assert hasattr(response.choices[0], 'message')
        assert hasattr(response.choices[0].message, 'content')
        
        # Verify content is valid JSON
        content = response.choices[0].message.content
        parsed_content = json.loads(content)
        assert 'name' in parsed_content
        assert 'title' in parsed_content
        assert 'company' in parsed_content
        assert 'email' in parsed_content
    
    def test_mock_hunter_client(self):
        """Test Hunter.io client mock."""
        mock_client = MockExternalServices.mock_hunter_client()
        
        # Test email finder
        email_result = mock_client.email_finder('John', 'Doe', 'testcorp.com')
        assert 'data' in email_result
        assert 'email' in email_result['data']
        assert 'score' in email_result['data']
        assert email_result['data']['email'] == 'john.doe@testcorp.com'
        
        # Test domain search
        domain_result = mock_client.domain_search('testcorp.com')
        assert 'data' in domain_result
        assert 'emails' in domain_result['data']
        assert len(domain_result['data']['emails']) > 0
        
        email_data = domain_result['data']['emails'][0]
        assert 'value' in email_data
        assert 'confidence' in email_data
        assert 'first_name' in email_data
        assert 'last_name' in email_data
    
    def test_mock_notion_client(self):
        """Test Notion client mock."""
        mock_client = MockExternalServices.mock_notion_client()
        
        # Test database query
        query_result = mock_client.databases.query(database_id='test-db')
        assert 'results' in query_result
        assert 'has_more' in query_result
        assert len(query_result['results']) > 0
        
        page = query_result['results'][0]
        assert 'id' in page
        assert 'properties' in page
        
        # Test page creation
        create_result = mock_client.pages.create(
            parent={'database_id': 'test-db'},
            properties={}
        )
        assert 'id' in create_result
        assert 'url' in create_result
        
        # Test page update
        update_result = mock_client.pages.update(
            page_id='test-page',
            properties={}
        )
        assert 'id' in update_result
        assert 'url' in update_result
    
    def test_mock_selenium_driver(self):
        """Test Selenium WebDriver mock."""
        mock_driver = MockExternalServices.mock_selenium_driver()
        
        # Test page source
        assert mock_driver.page_source is not None
        assert 'John Doe' in mock_driver.page_source
        assert 'Software Engineer' in mock_driver.page_source
        
        # Test element finding
        element = mock_driver.find_element('css', '.profile-info h1')
        assert element.text == 'John Doe'
        
        elements = mock_driver.find_elements('css', '.profile-info')
        assert len(elements) > 0
        
        # Test attribute getting
        url = element.get_attribute('href')
        assert url == 'https://linkedin.com/in/johndoe'
    
    def test_mock_resend_client(self):
        """Test Resend email client mock."""
        mock_client = MockExternalServices.mock_resend_client()
        
        # Test email sending
        send_result = mock_client.emails.send(
            from_email='test@example.com',
            to=['john.doe@testcorp.com'],
            subject='Test Email',
            html='<p>Test content</p>'
        )
        
        assert 'id' in send_result
        assert 'from' in send_result
        assert 'to' in send_result
        assert 'subject' in send_result
        assert 'created_at' in send_result
        
        assert send_result['from'] == 'test@example.com'
        assert 'john.doe@testcorp.com' in send_result['to']
        assert send_result['subject'] == 'Test Email'
    
    def test_mock_all_external_services(self):
        """Test comprehensive external services mock."""
        mocks = MockExternalServices.mock_all_external_services()
        
        # Verify all expected services are mocked
        expected_services = [
            'openai_client', 'hunter_client', 'notion_client',
            'selenium_driver', 'resend_client'
        ]
        
        for service in expected_services:
            assert service in mocks
            assert mocks[service] is not None


class TestPerformanceTestUtilities:
    """Test cases for PerformanceTestUtilities class."""
    
    def test_measure_execution_time(self):
        """Test execution time measurement."""
        import time
        
        def test_function(delay):
            time.sleep(delay)
            return "completed"
        
        result, execution_time = PerformanceTestUtilities.measure_execution_time(
            test_function, 0.1
        )
        
        assert result == "completed"
        assert execution_time >= 0.1  # Should be at least the sleep time
        assert execution_time < 0.2   # Should not be too much longer
    
    def test_create_performance_benchmark_pass(self):
        """Test performance benchmark that passes."""
        @PerformanceTestUtilities.create_performance_benchmark("fast_test", 0.2)
        def fast_function():
            import time
            time.sleep(0.05)  # Well under the limit
            return "fast"
        
        # Should not raise exception
        result = fast_function()
        assert result == "fast"
    
    def test_create_performance_benchmark_fail(self):
        """Test performance benchmark that fails."""
        @PerformanceTestUtilities.create_performance_benchmark("slow_test", 0.05)
        def slow_function():
            import time
            time.sleep(0.1)  # Over the limit
            return "slow"
        
        # Should raise pytest failure
        with pytest.raises(pytest.fail.Exception) as exc_info:
            slow_function()
        
        assert "Performance benchmark 'slow_test' failed" in str(exc_info.value)
    
    def test_create_memory_usage_monitor(self):
        """Test memory usage monitoring."""
        monitor = PerformanceTestUtilities.create_memory_usage_monitor()
        
        # Test context manager
        with monitor:
            # Allocate some memory
            data = [i for i in range(10000)]
            assert len(data) == 10000
        
        # Memory usage should be calculated (might be 0 if psutil not available)
        memory_usage = monitor.get_memory_usage_mb()
        assert isinstance(memory_usage, (int, float))
        # Memory usage might be 0 for small allocations or mock, but should not be negative
        assert memory_usage >= 0


class TestPytestFixtures:
    """Test the pytest fixtures defined in test_utilities."""
    
    def test_mock_config_fixture(self, mock_config):
        """Test mock_config pytest fixture."""
        assert hasattr(mock_config, 'notion_token')
        assert hasattr(mock_config, 'hunter_api_key')
        assert mock_config.notion_token == 'test_notion_token'
    
    def test_test_company_data_fixture(self, test_company_data):
        """Test test_company_data pytest fixture."""
        assert test_company_data.name == TestUtilities.TEST_COMPANY_NAME
        assert test_company_data.domain == TestUtilities.TEST_DOMAIN
        assert isinstance(test_company_data.launch_date, datetime)
    
    def test_test_team_member_fixture(self, test_team_member):
        """Test test_team_member pytest fixture."""
        assert test_team_member.name == 'John Doe'
        assert test_team_member.title == 'Software Engineer'
        assert test_team_member.email == TestUtilities.TEST_EMAIL
    
    def test_test_linkedin_profile_fixture(self, test_linkedin_profile):
        """Test test_linkedin_profile pytest fixture."""
        assert test_linkedin_profile.name == 'John Doe'
        assert test_linkedin_profile.title == 'Software Engineer'
        assert isinstance(test_linkedin_profile.experience, list)
        assert isinstance(test_linkedin_profile.skills, list)
    
    def test_test_prospect_fixture(self, test_prospect):
        """Test test_prospect pytest fixture."""
        assert test_prospect.name == 'John Doe'
        assert test_prospect.email == TestUtilities.TEST_EMAIL
        assert test_prospect.status == ProspectStatus.NOT_CONTACTED
    
    def test_test_email_content_fixture(self, test_email_content):
        """Test test_email_content pytest fixture."""
        assert test_email_content.subject == 'Exciting Opportunity at TestCorp'
        assert 'Hi John' in test_email_content.body
        assert isinstance(test_email_content.generated_at, datetime)
    
    def test_test_sender_profile_fixture(self, test_sender_profile):
        """Test test_sender_profile pytest fixture."""
        assert test_sender_profile.name == 'Test Sender'
        assert test_sender_profile.email == 'test@example.com'
        assert test_sender_profile.role == 'Hiring Manager'
    
    def test_mock_external_services_fixture(self, mock_external_services):
        """Test mock_external_services pytest fixture."""
        expected_services = [
            'openai_client', 'hunter_client', 'notion_client',
            'selenium_driver', 'resend_client'
        ]
        
        for service in expected_services:
            assert service in mock_external_services
            assert mock_external_services[service] is not None
    
    def test_performance_monitor_fixture(self, performance_monitor):
        """Test performance_monitor pytest fixture."""
        # Test that it's a context manager
        with performance_monitor:
            # Do some work
            data = list(range(1000))
            assert len(data) == 1000
        
        # Should be able to get memory usage
        memory_usage = performance_monitor.get_memory_usage_mb()
        assert isinstance(memory_usage, (int, float))
        assert memory_usage >= 0