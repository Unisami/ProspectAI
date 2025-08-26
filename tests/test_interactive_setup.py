"""
Unit tests for the InteractiveSetup class and related installer components.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from interactive_setup import InteractiveSetup, InstallationState, APIKeyPrompt, ErrorCategory


class TestInteractiveSetup:
    """Test suite for InteractiveSetup class"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.setup = InteractiveSetup()
        self.setup.project_root = self.temp_dir
        self.setup.venv_path = self.temp_dir / "venv"
        self.setup.env_file = self.temp_dir / ".env"
    
    def teardown_method(self):
        """Clean up test fixtures after each test method"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_installation_state_progress_calculation(self):
        """Test InstallationState progress percentage calculation"""
        state = InstallationState()
        assert state.get_progress_percentage() == 0.0
        
        state.python_installed = True
        assert state.get_progress_percentage() == (1/7) * 100
        
        state.venv_created = True
        state.dependencies_installed = True
        assert state.get_progress_percentage() == (3/7) * 100
        
        # All completed
        state.config_created = True
        state.config_validated = True
        state.dashboard_setup = True
        state.runners_created = True
        assert state.get_progress_percentage() == 100.0
    
    def test_installation_state_current_step(self):
        """Test InstallationState current step identification"""
        state = InstallationState()
        assert state.get_current_step() == "Python installation"
        
        state.python_installed = True
        assert state.get_current_step() == "Virtual environment creation"
        
        state.venv_created = True
        assert state.get_current_step() == "Dependency installation"
        
        state.dependencies_installed = True
        assert state.get_current_step() == "API configuration"
        
        state.config_created = True
        assert state.get_current_step() == "Configuration validation"
        
        state.config_validated = True
        assert state.get_current_step() == "Dashboard setup"
        
        state.dashboard_setup = True
        assert state.get_current_step() == "Runner script creation"
        
        state.runners_created = True
        assert state.get_current_step() == "Installation complete"
    
    def test_get_venv_python_windows(self):
        """Test virtual environment Python path detection on Windows"""
        with patch('platform.system', return_value='Windows'):
            setup = InteractiveSetup()
            setup.venv_path = Path("test_venv")
            python_path = setup.get_venv_python()
            assert python_path == Path("test_venv") / "Scripts" / "python.exe"
    
    def test_get_venv_python_unix(self):
        """Test virtual environment Python path detection on Unix"""
        with patch('platform.system', return_value='Linux'):
            setup = InteractiveSetup()
            setup.venv_path = Path("test_venv")
            python_path = setup.get_venv_python()
            assert python_path == Path("test_venv") / "bin" / "python"
    
    @patch('subprocess.run')
    def test_create_virtual_environment_success(self, mock_subprocess):
        """Test successful virtual environment creation"""
        # Mock successful subprocess call
        mock_subprocess.return_value.returncode = 0
        
        # Mock the Python executable existing
        with patch.object(Path, 'exists', return_value=True):
            result = self.setup.create_virtual_environment()
        
        assert result is True
        assert self.setup.installation_state.venv_created is True
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_create_virtual_environment_failure(self, mock_subprocess):
        """Test virtual environment creation failure"""
        # Mock failed subprocess call
        mock_subprocess.return_value.returncode = 1
        mock_subprocess.return_value.stderr = "Error creating venv"
        
        result = self.setup.create_virtual_environment()
        
        assert result is False
        assert self.setup.installation_state.venv_created is False
    
    @patch('subprocess.run')
    @patch('builtins.input', return_value='y')
    @patch('shutil.rmtree')
    def test_create_virtual_environment_recreate_existing(self, mock_rmtree, mock_input, mock_subprocess):
        """Test recreating existing virtual environment"""
        # Create existing venv directory
        self.setup.venv_path.mkdir(parents=True)
        
        # Mock successful subprocess call
        mock_subprocess.return_value.returncode = 0
        
        # Mock the Python executable existing after creation
        with patch.object(Path, 'exists', side_effect=lambda: True):
            result = self.setup.create_virtual_environment()
        
        assert result is True
        mock_rmtree.assert_called_once_with(self.setup.venv_path)
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_subprocess):
        """Test successful dependency installation"""
        # Create requirements.txt
        requirements_file = self.temp_dir / "requirements.txt"
        requirements_file.write_text("requests>=2.31.0\nclick>=8.1.7")
        
        # Create mock Python executable
        python_exe = self.setup.get_venv_python()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("#!/usr/bin/env python")
        
        # Mock successful subprocess calls
        mock_subprocess.return_value.returncode = 0
        
        with patch.object(Path, 'exists', return_value=True):
            result = self.setup.install_dependencies()
        
        assert result is True
        assert self.setup.installation_state.dependencies_installed is True
        
        # Verify both pip upgrade and requirements install were called
        assert mock_subprocess.call_count == 2
    
    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_subprocess):
        """Test dependency installation failure"""
        # Create requirements.txt
        requirements_file = self.temp_dir / "requirements.txt"
        requirements_file.write_text("requests>=2.31.0")
        
        # Mock Python executable existing
        with patch.object(Path, 'exists', return_value=True):
            # Mock pip upgrade success but requirements install failure
            mock_subprocess.side_effect = [
                Mock(returncode=0),  # pip upgrade success
                Mock(returncode=1, stderr="Package not found")  # requirements install failure
            ]
            
            result = self.setup.install_dependencies()
        
        assert result is False
        assert self.setup.installation_state.dependencies_installed is False
    
    def test_validate_api_key_notion_valid(self):
        """Test valid Notion API key validation"""
        valid_key = "secret_" + "a" * 43
        result = self.setup.validate_api_key("NOTION_TOKEN", valid_key)
        assert result is True
    
    def test_validate_api_key_notion_invalid(self):
        """Test invalid Notion API key validation"""
        invalid_key = "invalid_key"
        result = self.setup.validate_api_key("NOTION_TOKEN", invalid_key)
        assert result is False
    
    def test_validate_api_key_openai_valid(self):
        """Test valid OpenAI API key validation"""
        valid_key = "sk-" + "a" * 48
        result = self.setup.validate_api_key("OPENAI_API_KEY", valid_key)
        assert result is True
    
    def test_validate_api_key_openai_invalid(self):
        """Test invalid OpenAI API key validation"""
        invalid_key = "sk-short"
        result = self.setup.validate_api_key("OPENAI_API_KEY", invalid_key)
        assert result is False
    
    def test_validate_api_key_no_pattern(self):
        """Test API key validation when no pattern is specified"""
        # Hunter API key has no validation pattern in the setup
        result = self.setup.validate_api_key("HUNTER_API_KEY", "any_value")
        assert result is True
    
    @patch('builtins.input')
    def test_collect_api_configuration_all_required(self, mock_input):
        """Test collecting all required API configuration"""
        # Mock user inputs
        mock_input.side_effect = [
            "secret_" + "a" * 43,  # NOTION_TOKEN
            "hunter_key_123",      # HUNTER_API_KEY
            "sk-" + "a" * 48,      # OPENAI_API_KEY
            "",                    # RESEND_API_KEY (skip)
            "",                    # SENDER_EMAIL (skip)
            ""                     # SENDER_NAME (skip)
        ]
        
        config = self.setup.collect_api_configuration()
        
        assert "NOTION_TOKEN" in config
        assert "HUNTER_API_KEY" in config
        assert "OPENAI_API_KEY" in config
        assert "RESEND_API_KEY" not in config
    
    @patch('builtins.input')
    def test_collect_api_configuration_retry_invalid(self, mock_input):
        """Test retrying when invalid API key is provided"""
        # Mock user inputs: invalid then valid Notion token
        mock_input.side_effect = [
            "invalid_notion_token",  # Invalid first attempt
            "secret_" + "a" * 43,    # Valid second attempt
            "hunter_key_123",        # HUNTER_API_KEY
            "sk-" + "a" * 48,        # OPENAI_API_KEY
            "", "", ""               # Skip optional fields
        ]
        
        config = self.setup.collect_api_configuration()
        
        assert config["NOTION_TOKEN"] == "secret_" + "a" * 43
        # Should have been called multiple times due to retry
        assert mock_input.call_count > 3
    
    def test_create_env_file_success(self):
        """Test successful .env file creation"""
        config = {
            "NOTION_TOKEN": "secret_test123",
            "HUNTER_API_KEY": "hunter_test123",
            "OPENAI_API_KEY": "sk-test123",
            "SENDER_EMAIL": "test@example.com"
        }
        
        result = self.setup.create_env_file(config)
        
        assert result is True
        assert self.setup.env_file.exists()
        assert self.setup.installation_state.config_created is True
        
        # Verify file contents
        content = self.setup.env_file.read_text()
        assert "NOTION_TOKEN=secret_test123" in content
        assert "HUNTER_API_KEY=hunter_test123" in content
        assert "OPENAI_API_KEY=sk-test123" in content
        assert "SENDER_EMAIL=test@example.com" in content
    
    @patch('subprocess.run')
    def test_validate_configuration_success(self, mock_subprocess):
        """Test successful configuration validation"""
        # Create CLI script
        cli_script = self.temp_dir / "cli.py"
        cli_script.write_text("#!/usr/bin/env python\nprint('CLI script')")
        
        # Mock Python executable and successful validation
        with patch.object(Path, 'exists', return_value=True):
            mock_subprocess.return_value.returncode = 0
            
            result = self.setup.validate_configuration()
        
        assert result is True
        assert self.setup.installation_state.config_validated is True
    
    @patch('subprocess.run')
    def test_validate_configuration_failure(self, mock_subprocess):
        """Test configuration validation failure"""
        # Create CLI script
        cli_script = self.temp_dir / "cli.py"
        cli_script.write_text("#!/usr/bin/env python\nprint('CLI script')")
        
        # Mock Python executable and failed validation
        with patch.object(Path, 'exists', return_value=True):
            mock_subprocess.return_value.returncode = 1
            mock_subprocess.return_value.stderr = "Invalid configuration"
            
            result = self.setup.validate_configuration()
        
        assert result is False
        assert self.setup.installation_state.config_validated is False
    
    @patch('subprocess.run')
    def test_setup_dashboard_success(self, mock_subprocess):
        """Test successful dashboard setup"""
        # Create setup script
        setup_script = self.temp_dir / "scripts" / "setup_dashboard.py"
        setup_script.parent.mkdir(parents=True)
        setup_script.write_text("#!/usr/bin/env python\nprint('Setup script')")
        
        # Mock Python executable and successful setup
        with patch.object(Path, 'exists', return_value=True):
            mock_subprocess.return_value.returncode = 0
            
            result = self.setup.setup_dashboard()
        
        assert result is True
        assert self.setup.installation_state.dashboard_setup is True
    
    def test_create_windows_runner_success(self):
        """Test Windows runner script creation"""
        result = self.setup.create_windows_runner()
        
        assert result is True
        
        runner_path = self.temp_dir / "run.bat"
        assert runner_path.exists()
        
        content = runner_path.read_text()
        assert "@echo off" in content
        assert "venv\\Scripts\\python.exe" in content
        assert "cli.py" in content
    
    @patch('os.chmod')
    @patch('platform.system', return_value='Linux')
    def test_create_unix_runner_success(self, mock_system, mock_chmod):
        """Test Unix runner script creation"""
        result = self.setup.create_unix_runner()
        
        assert result is True
        
        runner_path = self.temp_dir / "run.sh"
        assert runner_path.exists()
        
        content = runner_path.read_text()
        assert "#!/bin/bash" in content
        assert "venv/bin/python" in content
        assert "cli.py" in content
        
        # Verify chmod was called to make script executable
        mock_chmod.assert_called_once()
    
    def test_create_runner_scripts_success(self):
        """Test complete runner scripts creation"""
        with patch.object(self.setup, 'create_windows_runner', return_value=True), \
             patch.object(self.setup, 'create_unix_runner', return_value=True):
            
            result = self.setup.create_runner_scripts()
        
        assert result is True
        assert self.setup.installation_state.runners_created is True
    
    def test_create_runner_scripts_windows_failure(self):
        """Test runner scripts creation with Windows failure"""
        with patch.object(self.setup, 'create_windows_runner', return_value=False), \
             patch.object(self.setup, 'create_unix_runner', return_value=True):
            
            result = self.setup.create_runner_scripts()
        
        assert result is False
        assert self.setup.installation_state.runners_created is False
    
    @patch('builtins.input')
    @patch.object(InteractiveSetup, 'create_virtual_environment', return_value=True)
    @patch.object(InteractiveSetup, 'install_dependencies', return_value=True)
    @patch.object(InteractiveSetup, 'collect_api_configuration', return_value={"NOTION_TOKEN": "test"})
    @patch.object(InteractiveSetup, 'create_env_file', return_value=True)
    @patch.object(InteractiveSetup, 'validate_configuration', return_value=True)
    @patch.object(InteractiveSetup, 'setup_dashboard', return_value=True)
    @patch.object(InteractiveSetup, 'create_runner_scripts', return_value=True)
    def test_run_setup_complete_success(self, mock_runners, mock_dashboard, mock_validate, 
                                      mock_env_file, mock_config, mock_deps, mock_venv, mock_input):
        """Test complete setup process success"""
        result = self.setup.run_setup()
        
        assert result is True
        # Verify all steps were called
        mock_venv.assert_called_once()
        mock_deps.assert_called_once()
        mock_config.assert_called_once()
        mock_env_file.assert_called_once()
        mock_validate.assert_called_once()
        mock_dashboard.assert_called_once()
        mock_runners.assert_called_once()
    
    @patch.object(InteractiveSetup, 'create_virtual_environment', return_value=False)
    def test_run_setup_early_failure(self, mock_venv):
        """Test setup process with early failure"""
        result = self.setup.run_setup()
        
        assert result is False
        mock_venv.assert_called_once()


class TestAPIKeyPrompt:
    """Test suite for APIKeyPrompt dataclass"""
    
    def test_api_key_prompt_creation(self):
        """Test APIKeyPrompt creation with all fields"""
        prompt = APIKeyPrompt(
            key_name="TEST_KEY",
            description="Test API key",
            obtain_url="https://example.com",
            required=True,
            validation_pattern=r"test_.*",
            example_format="test_123"
        )
        
        assert prompt.key_name == "TEST_KEY"
        assert prompt.description == "Test API key"
        assert prompt.obtain_url == "https://example.com"
        assert prompt.required is True
        assert prompt.validation_pattern == r"test_.*"
        assert prompt.example_format == "test_123"
    
    def test_api_key_prompt_defaults(self):
        """Test APIKeyPrompt with default values"""
        prompt = APIKeyPrompt(
            key_name="TEST_KEY",
            description="Test API key",
            obtain_url="https://example.com"
        )
        
        assert prompt.required is True
        assert prompt.validation_pattern is None
        assert prompt.example_format is None


if __name__ == "__main__":
    pytest.main([__file__])