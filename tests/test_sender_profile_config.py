"""
Tests for sender profile configuration management.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.config import Config
from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile


class TestSenderProfileConfig:
    """Test sender profile configuration features."""
    
    def test_sender_profile_config_defaults(self):
        """Test sender profile configuration defaults."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            
            assert config.sender_profile_path is None
            assert config.sender_profile_format == "markdown"
            assert config.enable_sender_profile is True
            assert config.enable_interactive_profile_setup is True
            assert config.require_sender_profile is False
            assert config.sender_profile_completeness_threshold == 0.7
    
    def test_sender_profile_config_from_env(self):
        """Test sender profile configuration from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md',
            'SENDER_PROFILE_FORMAT': 'json',
            'ENABLE_SENDER_PROFILE': 'false',
            'ENABLE_INTERACTIVE_PROFILE_SETUP': 'false',
            'REQUIRE_SENDER_PROFILE': 'true',
            'SENDER_PROFILE_COMPLETENESS_THRESHOLD': '0.8'
        }):
            config = Config.from_env()
            
            assert config.sender_profile_path == '/path/to/profile.md'
            assert config.sender_profile_format == 'json'
            assert config.enable_sender_profile is False
            assert config.enable_interactive_profile_setup is False
            assert config.require_sender_profile is True
            assert config.sender_profile_completeness_threshold == 0.8
    
    def test_config_from_dict_with_sender_profile_fields(self):
        """Test configuration creation from dictionary with sender profile fields."""
        config_dict = {
            'notion_token': 'test_token',
            'hunter_api_key': 'test_key',
            'openai_api_key': 'test_openai_key',
            'sender_profile_path': '/path/to/profile.md',
            'sender_profile_format': 'yaml',
            'enable_sender_profile': False,
            'enable_interactive_profile_setup': False,
            'require_sender_profile': True,
            'sender_profile_completeness_threshold': 0.9
        }
        
        config = Config.from_dict(config_dict)
        
        assert config.sender_profile_path == '/path/to/profile.md'
        assert config.sender_profile_format == 'yaml'
        assert config.enable_sender_profile is False
        assert config.enable_interactive_profile_setup is False
        assert config.require_sender_profile is True
        assert config.sender_profile_completeness_threshold == 0.9
    
    def test_config_to_dict_includes_sender_profile_fields(self):
        """Test that to_dict includes all sender profile configuration fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md'
        }):
            config = Config.from_env()
            config_dict = config.to_dict()
            
            # Check that all sender profile fields are included
            assert 'sender_profile_path' in config_dict
            assert 'sender_profile_format' in config_dict
            assert 'enable_sender_profile' in config_dict
            assert 'enable_interactive_profile_setup' in config_dict
            assert 'require_sender_profile' in config_dict
            assert 'sender_profile_completeness_threshold' in config_dict
    
    def test_config_validation_with_sender_profile_fields(self):
        """Test configuration validation with sender profile fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md'
        }):
            config = Config.from_env()
            
            # Should not raise any exceptions
            config.validate()
    
    def test_config_validation_invalid_sender_profile_format(self):
        """Test validation fails with invalid sender profile format."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_FORMAT': 'invalid'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Sender profile format must be 'markdown', 'json', or 'yaml'"):
                config.validate()
    
    def test_config_validation_invalid_completeness_threshold(self):
        """Test validation fails with invalid completeness threshold."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_COMPLETENESS_THRESHOLD': '1.5'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Sender profile completeness threshold must be between 0 and 1"):
                config.validate()
    
    def test_config_validation_require_profile_but_disabled(self):
        """Test validation fails when profile is required but disabled."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_SENDER_PROFILE': 'false',
            'REQUIRE_SENDER_PROFILE': 'true'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="Cannot require sender profile when sender profile is disabled"):
                config.validate()
    
    def test_config_validation_require_profile_no_path_no_interactive(self):
        """Test validation fails when profile is required but no path or interactive setup."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'REQUIRE_SENDER_PROFILE': 'true',
            'ENABLE_INTERACTIVE_PROFILE_SETUP': 'false'
        }):
            config = Config.from_env()
            
            with pytest.raises(ValueError, match="When sender profile is required, either a profile path or interactive setup must be enabled"):
                config.validate()
    
    def test_get_missing_config_with_required_profile(self):
        """Test get_missing_config includes sender profile path when required."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'REQUIRE_SENDER_PROFILE': 'true'
        }):
            config = Config.from_env()
            missing = config.get_missing_config()
            
            assert "SENDER_PROFILE_PATH" in missing
    
    def test_validate_sender_profile_disabled(self):
        """Test validate_sender_profile when profile is disabled."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_SENDER_PROFILE': 'false'
        }):
            config = Config.from_env()
            result = config.validate_sender_profile()
            
            assert result["is_valid"] is True
            assert "Sender profile is disabled" in result["issues"]
    
    def test_validate_sender_profile_no_path(self):
        """Test validate_sender_profile when no profile path is provided."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            config = Config.from_env()
            result = config.validate_sender_profile()
            
            assert result["is_valid"] is True
            assert "No profile path provided, but interactive setup is enabled" in result["issues"]
    
    def test_validate_sender_profile_no_path_no_interactive(self):
        """Test validate_sender_profile when no path and interactive setup is disabled."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'ENABLE_INTERACTIVE_PROFILE_SETUP': 'false'
        }):
            config = Config.from_env()
            result = config.validate_sender_profile()
            
            assert result["is_valid"] is False
            assert "No sender profile path and interactive setup is disabled" in result["issues"]
    
    def test_validate_sender_profile_file_not_found(self):
        """Test validate_sender_profile when profile file doesn't exist."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/nonexistent/profile.md'
        }):
            config = Config.from_env()
            result = config.validate_sender_profile()
            
            assert result["is_valid"] is False
            assert "Sender profile file not found" in result["issues"][0]
            assert result["profile_exists"] is False
    
    def test_validate_sender_profile_with_valid_profile(self):
        """Test validate_sender_profile with a valid profile."""
        # Create a mock profile and manager
        mock_profile = MagicMock(spec=SenderProfile)
        mock_profile.is_complete.return_value = True
        mock_profile.get_completeness_score.return_value = 0.9
        
        mock_manager = MagicMock(spec=SenderProfileManager)
        mock_manager.load_profile_from_markdown.return_value = mock_profile
        mock_manager.validate_profile.return_value = (True, [])
        
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md'
        }), patch('os.path.exists', return_value=True):
            config = Config.from_env()
            result = config.validate_sender_profile(sender_profile_manager=mock_manager)
            
            assert result["is_valid"] is True
            assert result["profile_exists"] is True
            assert result["profile_loaded"] is True
            assert result["profile_complete"] is True
            assert result["completeness_score"] == 0.9
            assert result["meets_threshold"] is True
            assert len(result["issues"]) == 0
            assert result["profile"] == mock_profile
    
    def test_validate_sender_profile_with_incomplete_profile(self):
        """Test validate_sender_profile with an incomplete profile."""
        # Create a mock profile and manager
        mock_profile = MagicMock(spec=SenderProfile)
        mock_profile.is_complete.return_value = False
        mock_profile.get_completeness_score.return_value = 0.5
        
        mock_manager = MagicMock(spec=SenderProfileManager)
        mock_manager.load_profile_from_markdown.return_value = mock_profile
        mock_manager.validate_profile.return_value = (False, ["Profile is incomplete"])
        
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md',
            'REQUIRE_SENDER_PROFILE': 'true'
        }), patch('os.path.exists', return_value=True):
            config = Config.from_env()
            result = config.validate_sender_profile(sender_profile_manager=mock_manager)
            
            assert result["is_valid"] is False
            assert result["profile_exists"] is True
            assert result["profile_loaded"] is True
            assert result["profile_complete"] is False
            assert result["completeness_score"] == 0.5
            assert result["meets_threshold"] is False
            assert "Profile is incomplete" in result["issues"]
            assert "Sender profile completeness score (50.0%) is below the required threshold (70.0%)" in result["issues"]
    
    def test_config_save_and_load_with_sender_profile_fields(self):
        """Test saving and loading configuration with sender profile fields."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_openai_key',
            'SENDER_PROFILE_PATH': '/path/to/profile.md',
            'SENDER_PROFILE_FORMAT': 'json',
            'ENABLE_SENDER_PROFILE': 'false',
            'REQUIRE_SENDER_PROFILE': 'true',
            'SENDER_PROFILE_COMPLETENESS_THRESHOLD': '0.8'
        }):
            original_config = Config.from_env()
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                config_path = f.name
            
            try:
                # Save configuration
                original_config.save_to_file(config_path, include_secrets=True)
                
                # Load configuration
                loaded_config = Config.from_file(config_path)
                
                # Verify sender profile fields are preserved
                assert loaded_config.sender_profile_path == original_config.sender_profile_path
                assert loaded_config.sender_profile_format == original_config.sender_profile_format
                assert loaded_config.enable_sender_profile == original_config.enable_sender_profile
                assert loaded_config.enable_interactive_profile_setup == original_config.enable_interactive_profile_setup
                assert loaded_config.require_sender_profile == original_config.require_sender_profile
                assert loaded_config.sender_profile_completeness_threshold == original_config.sender_profile_completeness_threshold
                
            finally:
                # Clean up
                os.unlink(config_path)