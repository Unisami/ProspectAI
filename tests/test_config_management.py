"""
Unit tests for configuration management and preservation system.
"""

import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pytest

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_manager import ConfigurationManager, ConfigurationInfo, CompatibilityCheck


class TestConfigurationManager:
    """Test suite for ConfigurationManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigurationManager(self.temp_dir)
        self.env_file = self.temp_dir / ".env"
        self.venv_path = self.temp_dir / "venv"
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test ConfigurationManager initialization"""
        assert self.config_manager.project_root == self.temp_dir
        assert self.config_manager.env_file == self.env_file
        assert self.config_manager.venv_path == self.venv_path
        assert self.config_manager.env_backup_dir.exists()
    
    def test_analyze_existing_configuration_no_files(self):
        """Test analysis when no configuration files exist"""
        config_info = self.config_manager.analyze_existing_configuration()
        
        assert config_info.env_file_exists is False
        assert config_info.env_file_size == 0
        assert config_info.venv_exists is False
        assert config_info.venv_python_version is None
        assert config_info.venv_size_mb == 0.0
        assert config_info.config_keys == []
        assert config_info.is_compatible is False
    
    def test_analyze_existing_configuration_with_env_file(self):
        """Test analysis with existing .env file"""
        # Create .env file
        env_content = """# Test configuration
NOTION_TOKEN=secret_test123
HUNTER_API_KEY=hunter_test123
OPENAI_API_KEY=sk-test123
SENDER_EMAIL=test@example.com
"""
        self.env_file.write_text(env_content)
        
        config_info = self.config_manager.analyze_existing_configuration()
        
        assert config_info.env_file_exists is True
        assert config_info.env_file_size > 0
        assert "NOTION_TOKEN" in config_info.config_keys
        assert "HUNTER_API_KEY" in config_info.config_keys
        assert "OPENAI_API_KEY" in config_info.config_keys
        assert "SENDER_EMAIL" in config_info.config_keys
    
    def test_analyze_existing_configuration_with_venv(self):
        """Test analysis with existing virtual environment"""
        # Create venv directory structure
        self.venv_path.mkdir()
        (self.venv_path / "Scripts").mkdir()  # Windows structure
        (self.venv_path / "Scripts" / "python.exe").write_text("fake python")
        
        with patch.object(self.config_manager, '_get_venv_python_version', return_value="Python 3.13.1"):
            config_info = self.config_manager.analyze_existing_configuration()
        
        assert config_info.venv_exists is True
        assert config_info.venv_python_version == "Python 3.13.1"
        assert config_info.venv_size_mb > 0
    
    @patch('subprocess.run')
    def test_get_venv_python_version_success(self, mock_subprocess):
        """Test getting Python version from venv"""
        # Create venv directory and python executable
        self.venv_path.mkdir()
        python_exe = self.config_manager.platform_manager.get_venv_python_path(self.venv_path)
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("fake python")
        
        # Mock subprocess result
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Python 3.13.1"
        
        with patch.object(Path, 'exists', return_value=True):
            version = self.config_manager._get_venv_python_version()
        
        assert version == "Python 3.13.1"
    
    @patch('subprocess.run')
    def test_get_venv_python_version_failure(self, mock_subprocess):
        """Test getting Python version from venv when it fails"""
        # Mock subprocess failure
        mock_subprocess.return_value.returncode = 1
        
        with patch.object(Path, 'exists', return_value=True):
            version = self.config_manager._get_venv_python_version()
        
        assert version is None
    
    def test_parse_env_keys_valid_file(self):
        """Test parsing keys from valid .env file"""
        env_content = """# Configuration file
NOTION_TOKEN=secret_test123
HUNTER_API_KEY=hunter_test123
# Comment line
OPENAI_API_KEY=sk-test123

SENDER_EMAIL=test@example.com
"""
        self.env_file.write_text(env_content)
        
        keys = self.config_manager._parse_env_keys()
        
        expected_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY", "SENDER_EMAIL"]
        assert all(key in keys for key in expected_keys)
    
    def test_parse_env_keys_malformed_file(self):
        """Test parsing keys from malformed .env file"""
        env_content = """NOTION_TOKEN=secret_test123
INVALID_LINE_NO_EQUALS
HUNTER_API_KEY=hunter_test123
=INVALID_EMPTY_KEY
"""
        self.env_file.write_text(env_content)
        
        keys = self.config_manager._parse_env_keys()
        
        assert "NOTION_TOKEN" in keys
        assert "HUNTER_API_KEY" in keys
        assert "INVALID_LINE_NO_EQUALS" not in keys
    
    def test_parse_env_keys_nonexistent_file(self):
        """Test parsing keys from nonexistent file"""
        keys = self.config_manager._parse_env_keys()
        assert keys == []
    
    def test_check_basic_compatibility_compatible(self):
        """Test basic compatibility check with compatible setup"""
        venv_python_version = "Python 3.13.1"
        config_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY"]
        
        result = self.config_manager._check_basic_compatibility(venv_python_version, config_keys)
        assert result is True
    
    def test_check_basic_compatibility_old_python(self):
        """Test basic compatibility check with old Python version"""
        venv_python_version = "Python 3.11.5"
        config_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY"]
        
        result = self.config_manager._check_basic_compatibility(venv_python_version, config_keys)
        assert result is False
    
    def test_check_basic_compatibility_missing_keys(self):
        """Test basic compatibility check with missing required keys"""
        venv_python_version = "Python 3.13.1"
        config_keys = ["NOTION_TOKEN"]  # Missing required keys
        
        result = self.config_manager._check_basic_compatibility(venv_python_version, config_keys)
        assert result is False
    
    def test_create_backup_success(self):
        """Test successful configuration backup creation"""
        # Create .env file
        env_content = "NOTION_TOKEN=secret_test123\nHUNTER_API_KEY=hunter_test123"
        self.env_file.write_text(env_content)
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=len(env_content),
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=["NOTION_TOKEN", "HUNTER_API_KEY"],
            is_compatible=True
        )
        
        success, backup_path = self.config_manager.create_backup(config_info)
        
        assert success is True
        assert backup_path is not None
        
        backup_file = Path(backup_path)
        assert backup_file.exists()
        assert backup_file.read_text() == env_content
        
        # Check metadata file
        metadata_file = backup_file.with_suffix(backup_file.suffix + '.metadata.json')
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        assert "config_keys" in metadata
        assert metadata["config_keys"] == ["NOTION_TOKEN", "HUNTER_API_KEY"]
    
    def test_create_backup_no_env_file(self):
        """Test backup creation when no .env file exists"""
        config_info = ConfigurationInfo(
            env_file_exists=False,
            env_file_size=0,
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=[],
            is_compatible=False
        )
        
        success, backup_path = self.config_manager.create_backup(config_info)
        
        assert success is True
        assert backup_path is None
    
    def test_restore_backup_success(self):
        """Test successful backup restoration"""
        # Create original .env file and backup
        original_content = "NOTION_TOKEN=secret_original"
        self.env_file.write_text(original_content)
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=len(original_content),
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=True
        )
        
        success, backup_path = self.config_manager.create_backup(config_info)
        assert success is True
        
        # Modify original file
        modified_content = "NOTION_TOKEN=secret_modified"
        self.env_file.write_text(modified_content)
        
        # Restore from backup
        restore_success = self.config_manager.restore_backup(backup_path)
        
        assert restore_success is True
        assert self.env_file.read_text() == original_content
    
    def test_restore_backup_nonexistent_file(self):
        """Test backup restoration with nonexistent backup file"""
        result = self.config_manager.restore_backup("/nonexistent/backup/file")
        assert result is False
    
    def test_list_backups(self):
        """Test listing available backups"""
        # Create a backup
        env_content = "NOTION_TOKEN=secret_test123"
        self.env_file.write_text(env_content)
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=len(env_content),
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=True
        )
        
        success, backup_path = self.config_manager.create_backup(config_info)
        assert success is True
        
        # List backups
        backups = self.config_manager.list_backups()
        
        assert len(backups) == 1
        assert backups[0]["path"] == backup_path
        assert "metadata" in backups[0]
        assert backups[0]["metadata"] is not None
    
    def test_check_compatibility_all_good(self):
        """Test compatibility check with all systems OK"""
        with patch('sys.version_info', (3, 13, 1)), \
             patch.object(self.config_manager, '_check_dependencies', return_value=True):
            
            # Create compatible .env file
            env_content = "NOTION_TOKEN=secret_test123\nHUNTER_API_KEY=hunter_test123\nOPENAI_API_KEY=sk-test123"
            self.env_file.write_text(env_content)
            
            compatibility = self.config_manager.check_compatibility()
        
        assert compatibility.python_version_ok is True
        assert compatibility.dependencies_ok is True
        assert compatibility.config_format_ok is True
        assert compatibility.overall_compatible is True
        assert len(compatibility.issues) == 0
    
    def test_check_compatibility_old_python(self):
        """Test compatibility check with old Python version"""
        with patch('sys.version_info', (3, 11, 5)):
            compatibility = self.config_manager.check_compatibility()
        
        assert compatibility.python_version_ok is False
        assert compatibility.overall_compatible is False
        assert any("Python" in issue for issue in compatibility.issues)
        assert any("Upgrade" in rec for rec in compatibility.recommendations)
    
    def test_check_compatibility_missing_config(self):
        """Test compatibility check with missing configuration"""
        with patch('sys.version_info', (3, 13, 1)), \
             patch.object(self.config_manager, '_check_dependencies', return_value=True):
            
            # Create incomplete .env file
            env_content = "NOTION_TOKEN=secret_test123"
            self.env_file.write_text(env_content)
            
            compatibility = self.config_manager.check_compatibility()
        
        assert compatibility.config_format_ok is False
        assert compatibility.overall_compatible is False
        assert any("Missing required configuration keys" in issue for issue in compatibility.issues)
    
    @patch('subprocess.run')
    def test_check_dependencies_success(self, mock_subprocess):
        """Test dependency checking with all packages available"""
        # Create venv structure
        self.venv_path.mkdir()
        python_exe = self.config_manager.platform_manager.get_venv_python_path(self.venv_path)
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("fake python")
        
        # Mock all import checks to succeed
        mock_subprocess.return_value.returncode = 0
        
        with patch.object(Path, 'exists', return_value=True):
            result = self.config_manager._check_dependencies()
        
        assert result is True
    
    @patch('subprocess.run')
    def test_check_dependencies_missing_package(self, mock_subprocess):
        """Test dependency checking with missing package"""
        # Create venv structure
        self.venv_path.mkdir()
        python_exe = self.config_manager.platform_manager.get_venv_python_path(self.venv_path)
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("fake python")
        
        # Mock some import checks to fail
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # First package OK
            Mock(returncode=1),  # Second package missing
        ]
        
        with patch.object(Path, 'exists', return_value=True):
            result = self.config_manager._check_dependencies()
        
        assert result is False
    
    def test_migrate_configuration_success(self):
        """Test successful configuration migration"""
        # Create old format .env file
        old_content = """NOTION_API_KEY=secret_old123
HUNTER_KEY=hunter_old123
OPENAI_KEY=sk-old123
"""
        self.env_file.write_text(old_content)
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=len(old_content),
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=["NOTION_API_KEY", "HUNTER_KEY", "OPENAI_KEY"],
            is_compatible=False
        )
        
        result = self.config_manager.migrate_configuration(config_info)
        
        assert result is True
        
        # Check that file was updated with new format
        new_content = self.env_file.read_text()
        assert "NOTION_TOKEN=" in new_content
        assert "HUNTER_API_KEY=" in new_content
        assert "OPENAI_API_KEY=" in new_content
        assert "Updated by configuration manager" in new_content
    
    def test_create_updated_config(self):
        """Test creating updated configuration from existing"""
        existing_config = {
            "NOTION_API_KEY": "secret_old123",  # Old key name
            "HUNTER_API_KEY": "hunter_test123",  # Correct key name
            "OPENAI_KEY": "sk-old123",  # Old key name
            "UNKNOWN_KEY": "unknown_value"  # Unknown key
        }
        
        updated = self.config_manager._create_updated_config(existing_config)
        
        # Check key mappings
        assert updated["NOTION_TOKEN"] == "secret_old123"
        assert updated["HUNTER_API_KEY"] == "hunter_test123"
        assert updated["OPENAI_API_KEY"] == "sk-old123"
        assert "UNKNOWN_KEY" not in updated
    
    @patch('builtins.input')
    def test_prompt_for_preservation_choices_preserve_all(self, mock_input):
        """Test prompting for preservation choices (preserve all)"""
        mock_input.side_effect = ["Y", "Y", "Y"]  # Preserve env, create backup, preserve venv
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=100,
            env_file_modified=datetime.now(),
            venv_exists=True,
            venv_python_version="Python 3.13.1",
            venv_size_mb=50.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=True
        )
        
        choices = self.config_manager.prompt_for_preservation_choices(config_info)
        
        assert choices["preserve_env"] is True
        assert choices["create_backup"] is True
        assert choices["preserve_venv"] is True
    
    @patch('builtins.input')
    def test_prompt_for_preservation_choices_incompatible(self, mock_input):
        """Test prompting for preservation choices with incompatible config"""
        mock_input.side_effect = ["n", "n"]  # Don't preserve incompatible config and venv
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=100,
            env_file_modified=datetime.now(),
            venv_exists=True,
            venv_python_version="Python 3.11.5",  # Incompatible
            venv_size_mb=50.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=False
        )
        
        choices = self.config_manager.prompt_for_preservation_choices(config_info)
        
        assert choices["preserve_env"] is False
        assert choices["preserve_venv"] is False
    
    def test_apply_preservation_choices_remove_all(self):
        """Test applying preservation choices (remove all)"""
        # Create .env file and venv directory
        self.env_file.write_text("NOTION_TOKEN=secret_test123")
        self.venv_path.mkdir()
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=100,
            env_file_modified=datetime.now(),
            venv_exists=True,
            venv_python_version="Python 3.13.1",
            venv_size_mb=50.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=True
        )
        
        choices = {
            "preserve_env": False,
            "preserve_venv": False,
            "create_backup": False
        }
        
        result = self.config_manager.apply_preservation_choices(config_info, choices)
        
        assert result is True
        assert not self.env_file.exists()
        assert not self.venv_path.exists()
    
    def test_apply_preservation_choices_with_backup(self):
        """Test applying preservation choices with backup creation"""
        # Create .env file
        original_content = "NOTION_TOKEN=secret_test123"
        self.env_file.write_text(original_content)
        
        config_info = ConfigurationInfo(
            env_file_exists=True,
            env_file_size=len(original_content),
            env_file_modified=datetime.now(),
            venv_exists=False,
            venv_python_version=None,
            venv_size_mb=0.0,
            config_keys=["NOTION_TOKEN"],
            is_compatible=True
        )
        
        choices = {
            "preserve_env": True,
            "preserve_venv": False,
            "create_backup": True
        }
        
        result = self.config_manager.apply_preservation_choices(config_info, choices)
        
        assert result is True
        assert self.env_file.exists()
        
        # Check that backup was created
        backups = self.config_manager.list_backups()
        assert len(backups) > 0


if __name__ == "__main__":
    pytest.main([__file__])