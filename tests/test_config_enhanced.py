"""
Tests for enhanced configuration management.
"""

import pytest
import os
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch

from utils.config import Config


class TestEnhancedConfig:
    """Test enhanced configuration features."""
    
    def test_ai_parsing_config_defaults(self):
        """Test AI parsing configuration defaults."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            assert config.enable_ai_parsing is True
            assert config.ai_parsing_model == "gpt-4"
            assert config.ai_parsing_max_retries == 3
            assert config.ai_parsing_timeout == 30
    
    def test_product_analysis_config_defaults(self):
        """Test product analysis configuration defaults."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            assert config.enable_product_analysis is True
            assert config.product_analysis_model == "gpt-4"
            assert config.product_analysis_max_retries == 3
    
    def test_enhanced_email_config_defaults(self):
        """Test enhanced email generation configuration defaults."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            assert config.enhanced_personalization is True
            assert config.email_generation_model == "gpt-4"
            assert config.max_email_length == 500
    
    def test_workflow_config_defaults(self):
        """Test workflow configuration defaults."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            assert config.enable_enhanced_workflow is True
            assert config.batch_processing_enabled is True
            assert config.auto_send_emails is False
            assert config.email_review_required is True
    
    def test_ai_parsing_config_from_env(self):
        """Test AI parsing configuration from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_AI_PARSING': 'false',
            'AI_PARSING_MODEL': 'gpt-3.5-turbo',
            'AI_PARSING_MAX_RETRIES': '5',
            'AI_PARSING_TIMEOUT': '60'
        }):
            config = Config.from_env()
            
            assert config.enable_ai_parsing is False
            assert config.ai_parsing_model == "gpt-3.5-turbo"
            assert config.ai_parsing_max_retries == 5
            assert config.ai_parsing_timeout == 60
    
    def test_product_analysis_config_from_env(self):
        """Test product analysis configuration from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_PRODUCT_ANALYSIS': 'false',
            'PRODUCT_ANALYSIS_MODEL': 'gpt-3.5-turbo',
            'PRODUCT_ANALYSIS_MAX_RETRIES': '2'
        }):
            config = Config.from_env()
            
            assert config.enable_product_analysis is False
            assert config.product_analysis_model == "gpt-3.5-turbo"
            assert config.product_analysis_max_retries == 2
    
    def test_enhanced_email_config_from_env(self):
        """Test enhanced email configuration from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENHANCED_PERSONALIZATION': 'false',
            'EMAIL_GENERATION_MODEL': 'gpt-3.5-turbo',
            'MAX_EMAIL_LENGTH': '300'
        }):
            config = Config.from_env()
            
            assert config.enhanced_personalization is False
            assert config.email_generation_model == "gpt-3.5-turbo"
            assert config.max_email_length == 300
    
    def test_workflow_config_from_env(self):
        """Test workflow configuration from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_ENHANCED_WORKFLOW': 'false',
            'BATCH_PROCESSING_ENABLED': 'false',
            'AUTO_SEND_EMAILS': 'true',
            'EMAIL_REVIEW_REQUIRED': 'false'
        }):
            config = Config.from_env()
            
            assert config.enable_enhanced_workflow is False
            assert config.batch_processing_enabled is False
            assert config.auto_send_emails is True
            assert config.email_review_required is False
    
    def test_config_from_dict_with_new_fields(self):
        """Test configuration creation from dictionary with new fields."""
        config_dict = {
            'notion_token': 'test_token',
            'hunter_api_key': 'test_key',
            'openai_api_key': 'test_openai_key',
            'enable_ai_parsing': False,
            'ai_parsing_model': 'gpt-3.5-turbo',
            'ai_parsing_max_retries': 5,
            'ai_parsing_timeout': 45,
            'enable_product_analysis': False,
            'product_analysis_model': 'gpt-3.5-turbo',
            'product_analysis_max_retries': 2,
            'enhanced_personalization': False,
            'email_generation_model': 'gpt-3.5-turbo',
            'max_email_length': 400,
            'enable_enhanced_workflow': False,
            'batch_processing_enabled': False,
            'auto_send_emails': True,
            'email_review_required': False
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.enable_ai_parsing is False
        assert config.ai_parsing_model == "gpt-3.5-turbo"
        assert config.ai_parsing_max_retries == 5
        assert config.ai_parsing_timeout == 45
        assert config.enable_product_analysis is False
        assert config.product_analysis_model == "gpt-3.5-turbo"
        assert config.product_analysis_max_retries == 2
        assert config.enhanced_personalization is False
        assert config.email_generation_model == "gpt-3.5-turbo"
        assert config.max_email_length == 400
        assert config.enable_enhanced_workflow is False
        assert config.batch_processing_enabled is False
        assert config.auto_send_emails is True
        assert config.email_review_required is False
    
    def test_config_to_dict_includes_new_fields(self):
        """Test that to_dict includes all new configuration fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            config_dict = config.to_dict()
            
            # Check that all new fields are included
            assert 'enable_ai_parsing' in config_dict
            assert 'ai_parsing_model' in config_dict
            assert 'ai_parsing_max_retries' in config_dict
            assert 'ai_parsing_timeout' in config_dict
            assert 'enable_product_analysis' in config_dict
            assert 'product_analysis_model' in config_dict
            assert 'product_analysis_max_retries' in config_dict
            assert 'enhanced_personalization' in config_dict
            assert 'email_generation_model' in config_dict
            assert 'max_email_length' in config_dict
            assert 'enable_enhanced_workflow' in config_dict
            assert 'batch_processing_enabled' in config_dict
            assert 'auto_send_emails' in config_dict
            assert 'email_review_required' in config_dict
    
    def test_config_validation_with_new_fields(self):
        """Test configuration validation with new fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            # Should not raise any exceptions
            config.validate()
    
    def test_config_validation_invalid_ai_parsing_retries(self):
        """Test validation fails with invalid AI parsing retries."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'AI_PARSING_MAX_RETRIES': '-1'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="AI parsing max retries must be non-negative"):
                config.validate()
    
    def test_config_validation_invalid_ai_parsing_timeout(self):
        """Test validation fails with invalid AI parsing timeout."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'AI_PARSING_TIMEOUT': '0'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="AI parsing timeout must be positive"):
                config.validate()
    
    def test_config_validation_invalid_ai_parsing_model(self):
        """Test validation fails with invalid AI parsing model."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'AI_PARSING_MODEL': 'invalid-model'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="AI parsing model must be a valid OpenAI model"):
                config.validate()
    
    def test_config_validation_invalid_product_analysis_retries(self):
        """Test validation fails with invalid product analysis retries."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'PRODUCT_ANALYSIS_MAX_RETRIES': '-1'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Product analysis max retries must be non-negative"):
                config.validate()
    
    def test_config_validation_invalid_product_analysis_model(self):
        """Test validation fails with invalid product analysis model."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'PRODUCT_ANALYSIS_MODEL': 'invalid-model'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Product analysis model must be a valid OpenAI model"):
                config.validate()
    
    def test_config_validation_invalid_max_email_length(self):
        """Test validation fails with invalid max email length."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'MAX_EMAIL_LENGTH': '0'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Max email length must be positive"):
                config.validate()
    
    def test_config_validation_invalid_email_generation_model(self):
        """Test validation fails with invalid email generation model."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'EMAIL_GENERATION_MODEL': 'invalid-model'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Email generation model must be a valid OpenAI model"):
                config.validate()
    
    def test_config_save_and_load_with_new_fields(self):
        """Test saving and loading configuration with new fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_AI_PARSING': 'false',
            'AI_PARSING_MODEL': 'gpt-3.5-turbo'
        }):
            original_config = Config.from_env()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                config_path = f.name
            
            try:
                # Save configuration
                original_config.save_to_file(config_path, include_secrets=True)
                
                # Load configuration
                loaded_config = Config.from_file(config_path)
                
                # Verify new fields are preserved
                assert loaded_config.enable_ai_parsing == original_config.enable_ai_parsing
                assert loaded_config.ai_parsing_model == original_config.ai_parsing_model
                assert loaded_config.ai_parsing_max_retries == original_config.ai_parsing_max_retries
                assert loaded_config.ai_parsing_timeout == original_config.ai_parsing_timeout
                assert loaded_config.enable_product_analysis == original_config.enable_product_analysis
                assert loaded_config.product_analysis_model == original_config.product_analysis_model
                assert loaded_config.enhanced_personalization == original_config.enhanced_personalization
                assert loaded_config.email_generation_model == original_config.email_generation_model
                assert loaded_config.max_email_length == original_config.max_email_length
                assert loaded_config.enable_enhanced_workflow == original_config.enable_enhanced_workflow
                assert loaded_config.batch_processing_enabled == original_config.batch_processing_enabled
                assert loaded_config.auto_send_emails == original_config.auto_send_emails
                assert loaded_config.email_review_required == original_config.email_review_required
                
            finally:
                # Clean up
                os.unlink(config_path)
    
    def test_azure_openai_validation_with_new_fields(self):
        """Test Azure OpenAI validation works with new fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'USE_AZURE_OPENAI': 'true',
            'AZURE_OPENAI_API_KEY': 'test_azure_key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'gpt-4'
        }):
            config = Config.from_env()
            
            # Should not raise any exceptions
            config.validate()
            
            assert config.use_azure_openai is True
            assert config.azure_openai_api_key == 'test_azure_key'
            assert config.azure_openai_endpoint == 'https://test.openai.azure.com/'