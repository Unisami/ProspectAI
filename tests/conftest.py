"""
Pytest configuration and shared fixtures for the test suite.

This module provides shared fixtures that can be used across all test files.
"""

import pytest
from tests.test_utilities import (
    TestUtilities, MockExternalServices, PerformanceTestUtilities
)


# Pytest fixtures for common use
@pytest.fixture
def mock_config():
    """Pytest fixture for mock configuration."""
    return TestUtilities.create_mock_config()


@pytest.fixture
def test_company_data():
    """Pytest fixture for test company data."""
    return TestUtilities.create_test_company_data()


@pytest.fixture
def test_team_member():
    """Pytest fixture for test team member."""
    return TestUtilities.create_test_team_member()


@pytest.fixture
def test_linkedin_profile():
    """Pytest fixture for test LinkedIn profile."""
    return TestUtilities.create_test_linkedin_profile()


@pytest.fixture
def test_prospect():
    """Pytest fixture for test prospect."""
    return TestUtilities.create_test_prospect()


@pytest.fixture
def test_email_content():
    """Pytest fixture for test email content."""
    return TestUtilities.create_test_email_content()


@pytest.fixture
def test_sender_profile():
    """Pytest fixture for test sender profile."""
    return TestUtilities.create_test_sender_profile()


@pytest.fixture
def mock_external_services():
    """Pytest fixture for mocked external services."""
    return MockExternalServices.mock_all_external_services()


@pytest.fixture
def performance_monitor():
    """Pytest fixture for performance monitoring."""
    return PerformanceTestUtilities.create_memory_usage_monitor()


@pytest.fixture
def mock_openai_client():
    """Pytest fixture for mock OpenAI client."""
    return MockExternalServices.mock_openai_client()


@pytest.fixture
def mock_hunter_client():
    """Pytest fixture for mock Hunter.io client."""
    return MockExternalServices.mock_hunter_client()


@pytest.fixture
def mock_notion_client():
    """Pytest fixture for mock Notion client."""
    return MockExternalServices.mock_notion_client()


@pytest.fixture
def mock_selenium_driver():
    """Pytest fixture for mock Selenium WebDriver."""
    return MockExternalServices.mock_selenium_driver()


@pytest.fixture
def mock_resend_client():
    """Pytest fixture for mock Resend client."""
    return MockExternalServices.mock_resend_client()