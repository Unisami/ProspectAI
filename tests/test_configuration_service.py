"""
Unit tests for the enhanced configuration service.

Tests cover:
- Configuration loading and validation
- Caching functionality
- Hot-reloading capabilities
- Environment-specific overrides
- Thread safety
- Error handling
"""

import pytest
from tests.test_utilities import TestUtilities
import os
import tempfile
import yaml
import json
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from utils.configuration_service import (
    ConfigurationService,
    ConfigurationValidationResult,
    EnvironmentConfig,
    get_configuration_service,
    reset_configuration_service
)
from utils.config import Config


class TestConfigurationValidationResult:
    """Test ConfigurationValidationResult class."""
    
    def test_has_errors_with_errors(self):
        """Test has_errors returns True when errors exist."""
        result = ConfigurationValidationResult(
            is_valid=False,
            errors=["Error 1"],
            warnings=[],
            missing_required=[]
        )
        assert result.has_errors() is True
    
    def test_has_errors_with_missing_required(self):
        """Test has_errors returns True when missing required fields exist."""
        result = ConfigurationValidationResult(
            is_valid=False,
            errors=[],
            warnings=[],
            missing_required=["REQUIRED_FIELD"]
        )
        assert result.has_errors() is True
    
    def test_has_errors_no_errors(self):
        """Test has_errors returns False when no errors."""
        result = ConfigurationValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning"],
            missing_required=[]
        )
        assert result.has_errors() is False
    
    def test_get_summary_valid(self):
        """Test get_summary for valid configuration."""
        result = ConfigurationValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            missing_required=[]
        )
        assert result.get_summary() == "Configuration is valid"
    
    def test_get_summary_with_issues(self):
        """Test get_summary with various issues."""
        result = ConfigurationValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            missing_required=["FIELD1"]
        )
        summary = result.get_summary()
        assert "Errors: 2" in summary
        assert "Missing required: 1" in summary
        assert "Warnings: 1" in summary


class TestEnvironmentConfig:
    """Test EnvironmentConfig class."""
    
    def test_apply_overrides(self):
        """Test applying environment overrides."""
        env_config = EnvironmentConfig(
            name="test",
            overrides={"key1": "new_value", "key2": "override_value"},
            description="Test environment"
        )
        
        base_config = {"key1": "old_value", "key3": "unchanged"}
        result = env_config.apply_overrides(base_config)
        
        assert result["key1"] == "new_value"
        assert result["key2"] == "override_value"
        assert result["key3"] == "unchanged"
        assert base_config["key1"] == "old_value"  # Original unchanged


class TestConfigurationService:
    """Test ConfigurationService class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create temporary configuration file."""
        config_data = {
            "notion_token": "test_notion_token",
            "hunter_api_key": "test_hunter_key",
            "openai_api_key": "test_openai_key",
            "scraping_delay": 1.0,
            "max_products_per_run": 25
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def temp_env_file(self):
        """Create temporary .env file."""
        env_content = """
NOTION_TOKEN=env_notion_token
HUNTER_API_KEY=env_hunter_key
OPENAI_API_KEY=env_openai_key
SCRAPING_DELAY=2.0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write(env_content)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    # Using shared mock_config fixture from conftest.py
    def test_init_with_config_file(self, temp_config_file):
        """Test initialization with configuration file."""
        with patch('utils.configuration_service.Config.from_file') as mock_from_file:
            mock_from_file.return_value = Mock(spec=Config)
            
            service = ConfigurationService(
                config_path=temp_config_file,
                enable_hot_reload=False
            )
            
            assert service.config_path == temp_config_file
            assert service.environment == 'development'
            mock_from_file.assert_called_once_with(temp_config_file)
    
    def test_init_from_env(self):
        """Test initialization from environment variables."""
        with patch('utils.configuration_service.Config.from_env') as mock_from_env:
            mock_from_env.return_value = Mock(spec=Config)
            
            service = ConfigurationService(enable_hot_reload=False)
            
            assert service.config_path is None
            mock_from_env.assert_called_once()
    
    def test_get_config_full(self, mock_config):
        """Test getting full configuration."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            config = service.get_config()
            assert config == mock_config
    
    def test_get_config_section(self, mock_config):
        """Test getting configuration section."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Test getting existing attribute
            result = service.get_config('notion_token')
            assert result == "test_token"
            
            # Test getting non-existent attribute
            with pytest.raises(ValueError, match="Configuration section 'nonexistent' not found"):
                service.get_config('nonexistent')
    
    def test_config_caching(self, mock_config):
        """Test configuration value caching."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False, cache_ttl=60)
            
            # First call should access the attribute
            result1 = service.get_config('notion_token')
            
            # Second call should use cache
            result2 = service.get_config('notion_token')
            
            assert result1 == result2 == "test_token"
            
            # Verify caching worked
            assert 'notion_token' in service._config_cache
            assert service._config_cache['notion_token'] == "test_token"
    
    def test_cache_expiration(self, mock_config):
        """Test cache expiration."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False, cache_ttl=1)  # 1 second TTL
            
            # Get value to cache it
            service.get_config('notion_token')
            assert 'notion_token' in service._config_cache
            
            # Wait for cache to expire
            time.sleep(1.1)
            
            # Mock datetime to simulate time passage
            with patch('utils.configuration_service.datetime') as mock_datetime:
                mock_datetime.now.return_value = datetime.now() + timedelta(seconds=2)
                
                # This should bypass cache due to expiration
                result = service.get_config('notion_token')
                assert result == "test_token"
    
    def test_validate_configuration_success(self, mock_config):
        """Test successful configuration validation."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            result = service.validate_configuration()
            
            assert result.is_valid is True
            assert len(result.errors) == 0
            assert len(result.missing_required) == 0
    
    def test_validate_configuration_with_errors(self, mock_config):
        """Test configuration validation with errors."""
        mock_config.validate.side_effect = ValueError("Test validation error")
        
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            result = service.validate_configuration()
            
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert "Test validation error" in result.errors[0]
    
    def test_validate_configuration_missing_required(self, mock_config):
        """Test configuration validation with missing required fields."""
        mock_config.get_missing_config.return_value = ["REQUIRED_FIELD"]
        
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            result = service.validate_configuration()
            
            assert result.is_valid is False
            assert "REQUIRED_FIELD" in result.missing_required
    
    def test_validate_configuration_invalid_api_keys(self, mock_config):
        """Test configuration validation with invalid API keys."""
        mock_config.validate_api_keys.return_value = {
            'notion_token': False,
            'hunter_api_key': True,
            'openai_api_key': True
        }
        
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            result = service.validate_configuration()
            
            assert result.is_valid is False
            assert any("notion_token" in error for error in result.errors)
    
    def test_reload_configuration_success(self, mock_config):
        """Test successful configuration reload."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Add some cache entries
            service._config_cache['test_key'] = 'test_value'
            
            # Mock change callback
            callback = Mock()
            service.add_change_callback(callback)
            
            result = service.reload_configuration()
            
            assert result is True
            assert len(service._config_cache) == 0  # Cache should be cleared
            callback.assert_called_once()
    
    def test_reload_configuration_failure(self, mock_config):
        """Test configuration reload failure."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Mock reload failure
            with patch.object(service, '_load_configuration', side_effect=Exception("Load failed")):
                result = service.reload_configuration()
                
                assert result is False
    
    def test_change_callbacks(self, mock_config):
        """Test configuration change callbacks."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            callback1 = Mock()
            callback2 = Mock()
            
            # Add callbacks
            service.add_change_callback(callback1)
            service.add_change_callback(callback2)
            
            # Trigger change notification
            old_config = Mock()
            new_config = Mock()
            service._notify_change_callbacks(old_config, new_config)
            
            callback1.assert_called_once_with(old_config, new_config)
            callback2.assert_called_once_with(old_config, new_config)
            
            # Remove callback
            service.remove_change_callback(callback1)
            
            # Trigger again
            service._notify_change_callbacks(old_config, new_config)
            
            # callback1 should not be called again, callback2 should
            assert callback1.call_count == 1
            assert callback2.call_count == 2
    
    def test_change_callback_error_handling(self, mock_config):
        """Test error handling in change callbacks."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Add callback that raises exception
            error_callback = Mock(side_effect=Exception("Callback error"))
            good_callback = Mock()
            
            service.add_change_callback(error_callback)
            service.add_change_callback(good_callback)
            
            # Should not raise exception
            service._notify_change_callbacks(Mock(), Mock())
            
            # Good callback should still be called
            good_callback.assert_called_once()
    
    def test_get_config_dict(self, mock_config):
        """Test getting configuration as dictionary."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.configuration_service.asdict') as mock_asdict:
                mock_asdict.return_value = {'key': 'value'}
                
                service = ConfigurationService(enable_hot_reload=False)
                result = service.get_config_dict()
                
                assert result == {'key': 'value'}
                # asdict is called during initialization and during get_config_dict
                assert mock_asdict.call_count >= 1
    
    def test_export_configuration_yaml(self, mock_config, tmp_path):
        """Test exporting configuration to YAML."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.configuration_service.asdict') as mock_asdict:
                mock_asdict.return_value = {
                    'notion_token': 'secret_token',
                    'hunter_api_key': 'secret_key',
                    'scraping_delay': 1.0
                }
                
                service = ConfigurationService(enable_hot_reload=False)
                output_path = tmp_path / "config.yaml"
                
                result = service.export_configuration(str(output_path), format='yaml')
                
                assert result is True
                assert output_path.exists()
                
                # Check content
                with open(output_path, 'r') as f:
                    content = yaml.safe_load(f)
                
                assert content['notion_token'] == '***MASKED***'  # Should be masked by default
                assert content['scraping_delay'] == 1.0
    
    def test_export_configuration_with_secrets(self, mock_config, tmp_path):
        """Test exporting configuration with secrets included."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.configuration_service.asdict') as mock_asdict:
                mock_asdict.return_value = {
                    'notion_token': 'secret_token',
                    'scraping_delay': 1.0
                }
                
                service = ConfigurationService(enable_hot_reload=False)
                output_path = tmp_path / "config.yaml"
                
                result = service.export_configuration(
                    str(output_path), 
                    format='yaml', 
                    include_secrets=True
                )
                
                assert result is True
                
                # Check content
                with open(output_path, 'r') as f:
                    content = yaml.safe_load(f)
                
                assert content['notion_token'] == 'secret_token'  # Should not be masked
    
    def test_export_configuration_json(self, mock_config, tmp_path):
        """Test exporting configuration to JSON."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            with patch('utils.configuration_service.asdict') as mock_asdict:
                mock_asdict.return_value = {'key': 'value'}
                
                service = ConfigurationService(enable_hot_reload=False)
                output_path = tmp_path / "config.json"
                
                result = service.export_configuration(str(output_path), format='json')
                
                assert result is True
                assert output_path.exists()
                
                # Check content
                with open(output_path, 'r') as f:
                    content = json.load(f)
                
                assert content == {'key': 'value'}
    
    def test_get_cache_stats(self, mock_config):
        """Test getting cache statistics."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Add some cache entries
            service.get_config('notion_token')
            time.sleep(0.01)  # Small delay
            service.get_config('hunter_api_key')
            
            stats = service.get_cache_stats()
            
            assert stats['cached_sections'] == 2
            assert stats['cache_ttl'] == 300  # Default TTL
            assert stats['oldest_cache_entry'] is not None
            assert stats['newest_cache_entry'] is not None
    
    def test_thread_safety(self, mock_config):
        """Test thread safety of configuration service."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            results = []
            errors = []
            
            def worker():
                try:
                    for _ in range(10):
                        config = service.get_config('notion_token')
                        results.append(config)
                        time.sleep(0.001)
                except Exception as e:
                    errors.append(e)
            
            # Start multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=worker)
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Check results
            assert len(errors) == 0
            assert len(results) == 50  # 5 threads * 10 calls each
            assert all(result == "test_token" for result in results)
    
    def test_shutdown(self, mock_config):
        """Test service shutdown."""
        with patch('utils.configuration_service.Config.from_env', return_value=mock_config):
            service = ConfigurationService(enable_hot_reload=False)
            
            # Add some data
            service._config_cache['test'] = 'value'
            service.add_change_callback(Mock())
            
            service.shutdown()
            
            assert len(service._config_cache) == 0
            assert len(service._change_callbacks) == 0


class TestGlobalConfigurationService:
    """Test global configuration service functions."""
    
    def teardown_method(self):
        """Reset global service after each test."""
        reset_configuration_service()
    
    def test_get_configuration_service_singleton(self):
        """Test that get_configuration_service returns singleton."""
        with patch('utils.configuration_service.ConfigurationService') as mock_service_class:
            mock_instance = Mock()
            mock_service_class.return_value = mock_instance
            
            service1 = get_configuration_service()
            service2 = get_configuration_service()
            
            assert service1 is service2
            mock_service_class.assert_called_once()
    
    def test_reset_configuration_service(self):
        """Test resetting global configuration service."""
        with patch('utils.configuration_service.ConfigurationService') as mock_service_class:
            mock_instance1 = Mock()
            mock_instance2 = Mock()
            mock_service_class.side_effect = [mock_instance1, mock_instance2]
            
            # Get service instance
            service1 = get_configuration_service()
            
            # Reset
            reset_configuration_service()
            
            # Get new instance
            service2 = get_configuration_service()
            
            # Should be different instances
            assert service1 is not service2
            mock_instance1.shutdown.assert_called_once()


class TestConfigurationServiceIntegration:
    """Integration tests for configuration service."""
    
    def test_environment_config_loading(self, tmp_path):
        """Test loading environment-specific configurations."""
        # Create environment config directory
        env_dir = tmp_path / "config" / "environments"
        env_dir.mkdir(parents=True)
        
        # Create test environment config
        test_env_config = {
            'description': 'Test environment',
            'overrides': {
                'scraping_delay': 0.5,
                'max_products_per_run': 10
            }
        }
        
        env_file = env_dir / "test.yaml"
        with open(env_file, 'w') as f:
            yaml.dump(test_env_config, f)
        
        # Change to temp directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            
            with patch('utils.configuration_service.Config.from_env') as mock_from_env:
                mock_from_env.return_value = Mock(spec=Config)
                
                service = ConfigurationService(enable_hot_reload=False)
                
                # Check that environment config was loaded
                env_config = service.get_environment_config('test')
                assert env_config is not None
                assert env_config.name == 'test'
                assert env_config.description == 'Test environment'
                assert env_config.overrides['scraping_delay'] == 0.5
        
        finally:
            os.chdir(original_cwd)
    
    @pytest.mark.skipif(os.name == 'nt', reason="File watching may be unreliable on Windows in tests")
    def test_file_watching_integration(self, tmp_path):
        """Test file watching integration (if supported)."""
        # Create config file
        config_file = tmp_path / "test_config.yaml"
        initial_config = {
            'notion_token': 'initial_token',
            'hunter_api_key': 'initial_key',
            'openai_api_key': 'initial_openai'
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(initial_config, f)
        
        with patch('utils.configuration_service.Config.from_file') as mock_from_file:
            mock_config = Mock(spec=Config)
            mock_from_file.return_value = mock_config
            
            # Create service with file watching
            service = ConfigurationService(
                config_path=str(config_file),
                enable_hot_reload=True
            )
            
            # Add change callback
            callback = Mock()
            service.add_change_callback(callback)
            
            # Modify config file
            updated_config = initial_config.copy()
            updated_config['notion_token'] = 'updated_token'
            
            with open(config_file, 'w') as f:
                yaml.dump(updated_config, f)
            
            # Give file watcher time to detect change
            time.sleep(0.5)
            
            # Cleanup
            service.shutdown()