"""
Demonstration of consolidated test utilities and fixtures.

This test file shows how the shared test utilities and fixtures
can be used across different test files to reduce duplication.
"""

import pytest
from tests.test_utilities import TestUtilities, MockExternalServices


class TestConsolidationDemo:
    """Demonstrate the use of consolidated test utilities."""
    
    def test_shared_mock_config_fixture(self, mock_config):
        """Test using shared mock_config fixture."""
        # The fixture is automatically injected from conftest.py
        assert hasattr(mock_config, 'notion_token')
        assert hasattr(mock_config, 'hunter_api_key')
        assert mock_config.notion_token == 'test_notion_token'
        assert mock_config.scraping_delay == 0.1  # Optimized for tests
    
    def test_shared_test_data_fixtures(self, test_company_data, test_team_member):
        """Test using shared test data fixtures."""
        # Company data fixture
        assert test_company_data.name == TestUtilities.TEST_COMPANY_NAME
        assert test_company_data.domain == TestUtilities.TEST_DOMAIN
        
        # Team member fixture
        assert test_team_member.name == 'John Doe'
        assert test_team_member.email == TestUtilities.TEST_EMAIL
    
    def test_shared_external_service_mocks(self, mock_external_services):
        """Test using shared external service mocks."""
        # All external services should be mocked
        expected_services = [
            'openai_client', 'hunter_client', 'notion_client',
            'selenium_driver', 'resend_client'
        ]
        
        for service in expected_services:
            assert service in mock_external_services
            assert mock_external_services[service] is not None
    
    def test_manual_test_utilities_usage(self):
        """Test using TestUtilities class directly."""
        # Create custom test data
        custom_company = TestUtilities.create_test_company_data(
            name='Custom Corp',
            domain='custom.com'
        )
        
        assert custom_company.name == 'Custom Corp'
        assert custom_company.domain == 'custom.com'
        # Default values should still be present
        assert custom_company.description == TestUtilities.TEST_DESCRIPTION
    
    def test_mock_external_services_directly(self):
        """Test using MockExternalServices class directly."""
        # Create individual service mocks
        openai_client = MockExternalServices.mock_openai_client()
        hunter_client = MockExternalServices.mock_hunter_client()
        
        # Test OpenAI mock
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "test"}]
        )
        assert hasattr(response, 'choices')
        
        # Test Hunter mock
        result = hunter_client.email_finder('John', 'Doe', 'testcorp.com')
        assert 'data' in result
        assert 'email' in result['data']