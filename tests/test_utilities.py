"""
Shared test utilities and fixtures for the job prospect automation system.

This module provides:
- Common test fixtures for data models
- Mock configurations for different test scenarios
- Comprehensive mocking for external services
- Shared test utilities and helpers
- Performance testing utilities
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from dataclasses import dataclass

# Import data models with error handling for circular dependencies
try:
    from models.data_models import (
        CompanyData, TeamMember, LinkedInProfile, Prospect, 
        ProspectStatus, EmailContent
    )
    DATA_MODELS_AVAILABLE = True
except ImportError:
    DATA_MODELS_AVAILABLE = False

# Skip config import due to circular dependencies
CONFIG_AVAILABLE = False

# Skip openai client import due to import issues
OPENAI_CLIENT_AVAILABLE = False

try:
    from utils.validation_framework import ValidationResult, ValidationSeverity
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False


class TestUtilities:
    """Shared test utilities and helpers."""
    
    # Test data constants
    TEST_COMPANY_NAME = "TestCorp Inc"
    TEST_DOMAIN = "testcorp.com"
    TEST_PRODUCT_URL = "https://producthunt.com/posts/testcorp"
    TEST_DESCRIPTION = "A revolutionary test automation platform"
    TEST_EMAIL = "test@testcorp.com"
    TEST_LINKEDIN_URL = "https://linkedin.com/in/testuser"
    
    @staticmethod
    def create_mock_config(**overrides):
        """
        Create mock configuration for testing.
        
        Args:
            **overrides: Configuration values to override
            
        Returns:
            Mock Config instance with realistic defaults
        """
        defaults = {
            'notion_token': 'test_notion_token',
            'hunter_api_key': 'test_hunter_key',
            'openai_api_key': 'test_openai_key',
            'azure_openai_api_key': None,
            'azure_openai_endpoint': None,
            'azure_openai_deployment_name': 'gpt-4',
            'azure_openai_api_version': '2024-02-15-preview',
            'use_azure_openai': False,
            'scraping_delay': 0.1,  # Faster for tests
            'hunter_requests_per_minute': 60,
            'max_products_per_run': 10,
            'max_prospects_per_company': 5,
            'notion_database_id': 'test_db_id',
            'email_template_type': 'professional',
            'personalization_level': 'medium',
            'resend_api_key': 'test_resend_key',
            'sender_email': 'test@example.com',
            'sender_name': 'Test Sender',
            'reply_to_email': 'reply@example.com',
            'resend_requests_per_minute': 100,
            'enable_ai_parsing': True,
            'ai_parsing_model': 'gpt-4',
            'ai_parsing_max_retries': 2,  # Fewer retries for tests
            'ai_parsing_timeout': 10,  # Shorter timeout for tests
            'enable_product_analysis': True,
            'product_analysis_model': 'gpt-4',
            'product_analysis_max_retries': 2,
            'enhanced_personalization': True,
            'email_generation_model': 'gpt-4',
            'max_email_length': 500,
            'enable_enhanced_workflow': True,
            'batch_processing_enabled': True,
            'auto_send_emails': False,
            'email_review_required': True,
            'sender_profile_path': None,
            'sender_profile_format': 'markdown',
            'enable_sender_profile': True,
            'enable_interactive_profile_setup': False,  # Disable for tests
            'require_sender_profile': False,
            'sender_profile_completeness_threshold': 0.7,
            'enable_progress_tracking': True,
            'campaigns_db_id': 'test_campaigns_db',
            'logs_db_id': 'test_logs_db',
            'status_db_id': 'test_status_db',
            'openai_delay': 0.1,  # Faster for tests
            'max_parallel_workers': 2,  # Fewer workers for tests
            'cache_directory': '/tmp/test_cache',
            'log_level': 'DEBUG'
        }
        
        # Apply overrides
        defaults.update(overrides)
        
        # Create mock config with all attributes
        config = Mock()
        for key, value in defaults.items():
            setattr(config, key, value)
        
        return config
    
    @staticmethod
    def create_test_company_data(**overrides):
        """
        Create test company data with realistic values.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            CompanyData instance for testing
        """
        defaults = {
            'name': TestUtilities.TEST_COMPANY_NAME,
            'domain': TestUtilities.TEST_DOMAIN,
            'product_url': TestUtilities.TEST_PRODUCT_URL,
            'description': TestUtilities.TEST_DESCRIPTION,
            'launch_date': datetime(2024, 1, 15)
        }
        
        defaults.update(overrides)
        
        # Create without validation for testing
        if DATA_MODELS_AVAILABLE:
            company = object.__new__(CompanyData)
            for key, value in defaults.items():
                setattr(company, key, value)
        else:
            # Create mock object if data models not available
            company = Mock()
            for key, value in defaults.items():
                setattr(company, key, value)
        
        return company
    
    @staticmethod
    def create_test_team_member(**overrides):
        """
        Create test team member data.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            TeamMember instance for testing
        """
        defaults = {
            'name': 'John Doe',
            'title': 'Software Engineer',
            'linkedin_url': TestUtilities.TEST_LINKEDIN_URL,
            'email': TestUtilities.TEST_EMAIL,
            'company_domain': TestUtilities.TEST_DOMAIN
        }
        
        defaults.update(overrides)
        
        # Create without validation for testing
        if DATA_MODELS_AVAILABLE:
            member = object.__new__(TeamMember)
            for key, value in defaults.items():
                setattr(member, key, value)
        else:
            member = Mock()
            for key, value in defaults.items():
                setattr(member, key, value)
        
        return member
    
    @staticmethod
    def create_test_linkedin_profile(**overrides):
        """
        Create test LinkedIn profile data.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            LinkedInProfile instance for testing
        """
        defaults = {
            'name': 'John Doe',
            'title': 'Software Engineer',
            'company': TestUtilities.TEST_COMPANY_NAME,
            'location': 'San Francisco, CA',
            'summary': 'Experienced software engineer with expertise in Python and AI',
            'experience': [
                {
                    'title': 'Senior Software Engineer',
                    'company': TestUtilities.TEST_COMPANY_NAME,
                    'duration': '2022 - Present',
                    'description': 'Leading AI initiatives'
                }
            ],
            'education': [
                {
                    'school': 'Stanford University',
                    'degree': 'BS Computer Science',
                    'year': '2020'
                }
            ],
            'skills': ['Python', 'Machine Learning', 'Software Architecture'],
            'url': TestUtilities.TEST_LINKEDIN_URL
        }
        
        defaults.update(overrides)
        
        # Create without validation for testing
        if DATA_MODELS_AVAILABLE:
            profile = object.__new__(LinkedInProfile)
            for key, value in defaults.items():
                setattr(profile, key, value)
        else:
            profile = Mock()
            for key, value in defaults.items():
                setattr(profile, key, value)
        
        return profile
    
    @staticmethod
    def create_test_prospect(**overrides):
        """
        Create test prospect data.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            Prospect instance for testing
        """
        # Use string status if enum not available
        default_status = 'NOT_CONTACTED'
        if DATA_MODELS_AVAILABLE:
            try:
                default_status = ProspectStatus.NOT_CONTACTED
            except:
                default_status = 'NOT_CONTACTED'
        
        defaults = {
            'name': 'John Doe',
            'email': TestUtilities.TEST_EMAIL,
            'title': 'Software Engineer',
            'company': TestUtilities.TEST_COMPANY_NAME,
            'linkedin_url': TestUtilities.TEST_LINKEDIN_URL,
            'status': default_status,
            'notes': 'Test prospect for automation',
            'created_date': datetime.now(),
            'last_contacted': None
        }
        
        defaults.update(overrides)
        
        # Create without validation for testing
        if DATA_MODELS_AVAILABLE:
            prospect = object.__new__(Prospect)
            for key, value in defaults.items():
                setattr(prospect, key, value)
        else:
            prospect = Mock()
            for key, value in defaults.items():
                setattr(prospect, key, value)
        
        return prospect
    
    @staticmethod
    def create_test_email_content(**overrides):
        """
        Create test email content.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            EmailContent instance for testing
        """
        defaults = {
            'subject': 'Exciting Opportunity at TestCorp',
            'body': 'Hi John,\n\nI came across your profile and was impressed by your work...',
            'personalization_notes': 'Mentioned their AI expertise',
            'generated_at': datetime.now()
        }
        
        defaults.update(overrides)
        
        # Create without validation for testing
        if DATA_MODELS_AVAILABLE:
            content = object.__new__(EmailContent)
            for key, value in defaults.items():
                setattr(content, key, value)
        else:
            content = Mock()
            for key, value in defaults.items():
                setattr(content, key, value)
        
        return content
    
    @staticmethod
    def create_test_sender_profile(**overrides):
        """
        Create test sender profile.
        
        Args:
            **overrides: Fields to override
            
        Returns:
            SenderProfile instance for testing
        """
        defaults = {
            'name': 'Test Sender',
            'email': 'test@example.com',
            'company': 'Test Company',
            'role': 'Hiring Manager',
            'bio': 'Experienced hiring manager looking for top talent',
            'interests': ['AI', 'Software Engineering', 'Startups'],
            'communication_style': 'professional',
            'signature': 'Best regards,\nTest Sender'
        }
        
        defaults.update(overrides)
        
        # Create mock object (SenderProfile may have circular dependencies)
        profile = Mock()
        for key, value in defaults.items():
            setattr(profile, key, value)
        
        return profile
    
    @staticmethod
    def create_test_validation_result(is_valid: bool = True, **overrides):
        """
        Create test validation result.
        
        Args:
            is_valid: Whether validation passed
            **overrides: Fields to override
            
        Returns:
            ValidationResult instance for testing
        """
        # Use enum severity if available, otherwise string
        if VALIDATION_AVAILABLE:
            info_severity = ValidationSeverity.INFO
            error_severity = ValidationSeverity.ERROR
        else:
            info_severity = 'INFO'
            error_severity = 'ERROR'
        
        defaults = {
            'is_valid': is_valid,
            'message': 'Validation passed' if is_valid else 'Validation failed',
            'severity': info_severity if is_valid else error_severity,
            'field_name': 'test_field',
            'suggested_fix': None,
            'error_code': None
        }
        
        defaults.update(overrides)
        
        if VALIDATION_AVAILABLE:
            return ValidationResult(**defaults)
        else:
            # Create mock if ValidationResult not available
            result = Mock()
            for key, value in defaults.items():
                setattr(result, key, value)
            return result
    
    @staticmethod
    def create_temporary_config_file(config_data: Dict[str, Any]) -> str:
        """
        Create temporary configuration file for testing.
        
        Args:
            config_data: Configuration data to write
            
        Returns:
            Path to temporary config file
        """
        import yaml
        
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(config_data, temp_file, default_flow_style=False)
        temp_file.close()
        
        return temp_file.name
    
    @staticmethod
    def cleanup_temporary_file(file_path: str):
        """
        Clean up temporary file.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            os.unlink(file_path)
        except (OSError, FileNotFoundError):
            pass  # File already deleted or doesn't exist


class MockExternalServices:
    """Comprehensive mocking for external services."""
    
    @staticmethod
    def mock_openai_client():
        """Create mock OpenAI client with realistic responses."""
        mock_client = Mock()
        
        # Mock completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "name": "John Doe",
            "title": "Software Engineer",
            "company": "TestCorp Inc",
            "email": "john.doe@testcorp.com"
        })
        
        mock_client.chat.completions.create.return_value = mock_response
        
        return mock_client
    
    @staticmethod
    def mock_hunter_client():
        """Create mock Hunter.io client."""
        mock_client = Mock()
        
        # Mock email finder response
        mock_client.email_finder.return_value = {
            'data': {
                'email': 'john.doe@testcorp.com',
                'score': 95,
                'sources': [{'domain': 'testcorp.com', 'type': 'website'}]
            }
        }
        
        # Mock domain search response
        mock_client.domain_search.return_value = {
            'data': {
                'emails': [
                    {
                        'value': 'john.doe@testcorp.com',
                        'type': 'personal',
                        'confidence': 95,
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'position': 'Software Engineer'
                    }
                ]
            }
        }
        
        return mock_client
    
    @staticmethod
    def mock_notion_client():
        """Create mock Notion client."""
        mock_client = Mock()
        
        # Mock database query response
        mock_client.databases.query.return_value = {
            'results': [
                {
                    'id': 'test-page-id',
                    'properties': {
                        'Name': {'title': [{'text': {'content': 'TestCorp Inc'}}]},
                        'Domain': {'rich_text': [{'text': {'content': 'testcorp.com'}}]},
                        'Status': {'select': {'name': 'Not Contacted'}}
                    }
                }
            ],
            'has_more': False
        }
        
        # Mock page creation response
        mock_client.pages.create.return_value = {
            'id': 'new-page-id',
            'url': 'https://notion.so/new-page-id'
        }
        
        # Mock page update response
        mock_client.pages.update.return_value = {
            'id': 'updated-page-id',
            'url': 'https://notion.so/updated-page-id'
        }
        
        return mock_client
    
    @staticmethod
    def mock_selenium_driver():
        """Create mock Selenium WebDriver."""
        mock_driver = Mock()
        
        # Mock page source
        mock_driver.page_source = """
        <html>
            <body>
                <div class="profile-info">
                    <h1>John Doe</h1>
                    <p>Software Engineer at TestCorp Inc</p>
                </div>
            </body>
        </html>
        """
        
        # Mock find_element methods
        mock_element = Mock()
        mock_element.text = "John Doe"
        mock_element.get_attribute.return_value = "https://linkedin.com/in/johndoe"
        
        mock_driver.find_element.return_value = mock_element
        mock_driver.find_elements.return_value = [mock_element]
        
        return mock_driver
    
    @staticmethod
    def mock_resend_client():
        """Create mock Resend email client."""
        mock_client = Mock()
        
        # Mock email send response
        mock_client.emails.send.return_value = {
            'id': 'email-id-123',
            'from': 'test@example.com',
            'to': ['john.doe@testcorp.com'],
            'subject': 'Test Email',
            'created_at': datetime.now().isoformat()
        }
        
        return mock_client
    
    @staticmethod
    def mock_all_external_services():
        """
        Create comprehensive mock context for all external services.
        
        Returns:
            Dictionary of mock contexts that can be used with patch
        """
        return {
            'openai_client': MockExternalServices.mock_openai_client(),
            'hunter_client': MockExternalServices.mock_hunter_client(),
            'notion_client': MockExternalServices.mock_notion_client(),
            'selenium_driver': MockExternalServices.mock_selenium_driver(),
            'resend_client': MockExternalServices.mock_resend_client()
        }


class PerformanceTestUtilities:
    """Utilities for performance testing and benchmarking."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """
        Measure execution time of a function.
        
        Args:
            func: Function to measure
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Tuple of (result, execution_time_seconds)
        """
        import time
        
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    @staticmethod
    def create_performance_benchmark(name: str, target_time: float):
        """
        Create a performance benchmark decorator.
        
        Args:
            name: Benchmark name
            target_time: Target execution time in seconds
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                result, execution_time = PerformanceTestUtilities.measure_execution_time(
                    func, *args, **kwargs
                )
                
                if execution_time > target_time:
                    pytest.fail(
                        f"Performance benchmark '{name}' failed: "
                        f"Expected <= {target_time}s, got {execution_time:.3f}s"
                    )
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def create_memory_usage_monitor():
        """
        Create memory usage monitor for testing.
        
        Returns:
            Context manager for monitoring memory usage
        """
        try:
            import psutil
            import os
            
            class MemoryMonitor:
                def __init__(self):
                    self.process = psutil.Process(os.getpid())
                    self.start_memory = None
                    self.end_memory = None
                
                def __enter__(self):
                    self.start_memory = self.process.memory_info().rss
                    return self
                
                def __exit__(self, exc_type, exc_val, exc_tb):
                    self.end_memory = self.process.memory_info().rss
                
                def get_memory_usage_mb(self):
                    """Get memory usage in MB."""
                    if self.start_memory and self.end_memory:
                        return (self.end_memory - self.start_memory) / 1024 / 1024
                    return 0
            
            return MemoryMonitor()
        
        except ImportError:
            # Return mock monitor if psutil not available
            class MockMemoryMonitor:
                def __enter__(self):
                    return self
                
                def __exit__(self, exc_type, exc_val, exc_tb):
                    pass
                
                def get_memory_usage_mb(self):
                    """Return mock memory usage."""
                    return 0.0
            
            return MockMemoryMonitor()


# Pytest fixtures are now defined in conftest.py