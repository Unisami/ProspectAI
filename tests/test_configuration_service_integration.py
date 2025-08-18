"""
Integration tests for services using ConfigurationService.

Tests verify that refactored services can properly use the centralized configuration service.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from utils.configuration_service import get_configuration_service, reset_configuration_service
from utils.config import Config
from services.ai_parser import AIParser
from services.email_generator import EmailGenerator
from services.notion_manager import NotionDataManager
from services.linkedin_scraper import LinkedInScraper
from services.product_hunt_scraper import ProductHuntScraper
from services.email_finder import EmailFinder
from controllers.prospect_automation_controller import ProspectAutomationController


class TestConfigurationServiceIntegration:
    """Test integration between services and ConfigurationService."""
    
    def setup_method(self):
        """Reset configuration service before each test."""
        reset_configuration_service()
    
    def teardown_method(self):
        """Reset configuration service after each test."""
        reset_configuration_service()
    
    @pytest.fixture
    # Using shared mock_config fixture from conftest.py
    def test_ai_parser_uses_configuration_service(self, mock_config):
        """Test that AIParser can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('services.ai_parser.get_client_manager') as mock_client_manager:
                mock_manager = Mock()
                mock_client_manager.return_value = mock_manager
                
                # Test without config parameter (should use ConfigurationService)
                parser = AIParser()
                
                # Verify client manager was configured with config from service
                mock_manager.configure.assert_called_once()
                args, kwargs = mock_manager.configure.call_args
                assert args[0] == mock_config  # First argument should be the config
    
    def test_email_generator_uses_configuration_service(self, mock_config):
        """Test that EmailGenerator can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('services.email_generator.get_client_manager') as mock_client_manager:
                mock_manager = Mock()
                mock_client_manager.return_value = mock_manager
                
                # Test without config parameter (should use ConfigurationService)
                generator = EmailGenerator()
                
                # Verify client manager was configured with config from service
                mock_manager.configure.assert_called_once()
                args, kwargs = mock_manager.configure.call_args
                assert args[0] == mock_config
    
    def test_notion_manager_uses_configuration_service(self, mock_config):
        """Test that NotionDataManager can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('services.notion_manager.Client') as mock_client:
                # Test without config parameter (should use ConfigurationService)
                manager = NotionDataManager()
                
                # Verify Notion client was initialized with token from config service
                mock_client.assert_called_once_with(auth=mock_config.notion_token)
                assert manager.database_id == mock_config.notion_database_id
    
    def test_linkedin_scraper_uses_configuration_service(self, mock_config):
        """Test that LinkedInScraper can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            # Test without config parameter (should use ConfigurationService)
            scraper = LinkedInScraper()
            
            # Verify scraper has access to config from service
            assert scraper.config == mock_config
    
    def test_product_hunt_scraper_uses_configuration_service(self, mock_config):
        """Test that ProductHuntScraper can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.webdriver_manager.get_webdriver_manager') as mock_webdriver:
                with patch('services.ai_parser.AIParser') as mock_ai_parser:
                    # Test without config parameter (should use ConfigurationService)
                    scraper = ProductHuntScraper()
                    
                    # Verify scraper has access to config from service
                    assert scraper.config == mock_config
                    assert scraper.rate_limiter.delay == mock_config.scraping_delay
    
    def test_email_finder_uses_configuration_service(self, mock_config):
        """Test that EmailFinder can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.error_handling.get_error_handler') as mock_error_handler:
                with patch('utils.api_monitor.get_api_monitor') as mock_api_monitor:
                    # Test without config parameter (should use ConfigurationService)
                    finder = EmailFinder()
                    
                    # Verify finder has access to config from service
                    assert finder.config == mock_config
                    assert finder.api_key == mock_config.hunter_api_key
                    assert finder.rate_limiter.requests_per_minute == mock_config.hunter_requests_per_minute
    
    def test_controller_uses_configuration_service(self, mock_config):
        """Test that ProspectAutomationController can use ConfigurationService."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('services.product_hunt_scraper.ProductHuntScraper') as mock_scraper:
                with patch('services.notion_manager.NotionDataManager') as mock_notion:
                    with patch('services.email_finder.EmailFinder') as mock_email_finder:
                        with patch('services.linkedin_scraper.LinkedInScraper') as mock_linkedin:
                            with patch('services.email_generator.EmailGenerator') as mock_email_gen:
                                with patch('services.email_sender.EmailSender') as mock_email_sender:
                                    with patch('services.product_analyzer.ProductAnalyzer') as mock_analyzer:
                                        with patch('services.ai_parser.AIParser') as mock_ai_parser:
                                            # Test without config parameter (should use ConfigurationService)
                                            controller = ProspectAutomationController()
                                            
                                            # Verify controller has access to config from service
                                            assert controller.config == mock_config
    
    def test_backward_compatibility_with_direct_config(self, mock_config):
        """Test that services still work when config is passed directly."""
        with patch('services.ai_parser.get_client_manager') as mock_client_manager:
            mock_manager = Mock()
            mock_client_manager.return_value = mock_manager
            
            # Test with direct config parameter (backward compatibility)
            parser = AIParser(config=mock_config)
            
            # Verify client manager was configured with the provided config
            mock_manager.configure.assert_called_once()
            args, kwargs = mock_manager.configure.call_args
            assert args[0] == mock_config
    
    def test_configuration_service_singleton_behavior(self, mock_config):
        """Test that multiple services use the same configuration service instance."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('services.ai_parser.get_client_manager') as mock_ai_client_manager:
                with patch('services.email_generator.get_client_manager') as mock_email_client_manager:
                    with patch('services.notion_manager.Client') as mock_notion_client:
                        mock_ai_manager = Mock()
                        mock_email_manager = Mock()
                        mock_ai_client_manager.return_value = mock_ai_manager
                        mock_email_client_manager.return_value = mock_email_manager
                        
                        # Create multiple services without config
                        parser = AIParser()
                        generator = EmailGenerator()
                        notion_manager = NotionDataManager()
                        
                        # All should have the same config instance from ConfigurationService
                        # We can't directly compare client managers since they're different instances
                        # But we can verify they all got the same config
                        assert notion_manager.config == mock_config
                        
                        # Verify configuration service was used
                        mock_ai_manager.configure.assert_called_once()
                        mock_email_manager.configure.assert_called_once()
                        mock_notion_client.assert_called_once_with(auth=mock_config.notion_token)