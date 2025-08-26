"""
Integration tests for the cross-platform installer system.
Tests end-to-end installation workflows and cross-platform compatibility.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from interactive_setup import InteractiveSetup
from utils.platform_detection import get_platform_manager
from utils.installer_error_handler import get_error_handler
from utils.config_manager import get_config_manager
from utils.recovery_manager import get_recovery_manager


class TestEndToEndInstallation:
    """Integration tests for complete installation workflows"""
    
    def setup_method(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        os.chdir(self.temp_dir)
        
        # Create minimal project structure
        self.create_test_project_structure()
    
    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_project_structure(self):
        """Create minimal project structure for testing"""
        # Create requirements.txt
        requirements_content = """requests>=2.31.0
click>=8.1.7
python-dotenv>=1.0.1
"""
        (self.temp_dir / "requirements.txt").write_text(requirements_content)
        
        # Create minimal CLI script
        cli_content = """#!/usr/bin/env python3
import sys
import click

@click.command()
def validate_config():
    print("Configuration validation passed")
    return 0

@click.command()
@click.group()
def cli():
    pass

cli.add_command(validate_config, name='validate-config')

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate-config":
        validate_config()
    else:
        cli()
"""
        (self.temp_dir / "cli.py").write_text(cli_content)
        
        # Create scripts directory and setup dashboard script
        scripts_dir = self.temp_dir / "scripts"
        scripts_dir.mkdir()
        
        dashboard_script = """#!/usr/bin/env python3
print("Dashboard setup completed")
"""
        (scripts_dir / "setup_dashboard.py").write_text(dashboard_script)
    
    @pytest.mark.integration
    def test_full_installation_success_simulation(self):
        """Test complete installation workflow simulation"""
        setup = InteractiveSetup()
        setup.project_root = self.temp_dir
        setup.venv_path = self.temp_dir / "venv"
        setup.env_file = self.temp_dir / ".env"
        
        # Mock user inputs for API configuration
        test_config = {
            "NOTION_TOKEN": "secret_" + "a" * 43,
            "HUNTER_API_KEY": "hunter_test_key_123",
            "OPENAI_API_KEY": "sk-" + "a" * 48
        }
        
        with patch.object(setup, 'collect_api_configuration', return_value=test_config), \
             patch('subprocess.run') as mock_subprocess, \
             patch('builtins.input', return_value=''):  # Skip prompts
            
            # Mock all subprocess calls to succeed
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = ""
            mock_subprocess.return_value.stderr = ""
            
            # Mock Python executable existence
            with patch.object(Path, 'exists', return_value=True):
                result = setup.run_setup()
        
        assert result is True
        assert setup.installation_state.runners_created is True
        
        # Verify that configuration file was created
        assert setup.env_file.exists()
        config_content = setup.env_file.read_text()
        assert "NOTION_TOKEN=secret_" in config_content
        assert "HUNTER_API_KEY=hunter_test_key_123" in config_content
        assert "OPENAI_API_KEY=sk-" in config_content
    
    @pytest.mark.integration
    def test_installation_with_existing_configuration(self):
        """Test installation when configuration already exists"""
        # Create existing .env file
        existing_config = """NOTION_TOKEN=secret_existing123
HUNTER_API_KEY=hunter_existing123
OPENAI_API_KEY=sk-existing123
"""
        env_file = self.temp_dir / ".env"
        env_file.write_text(existing_config)
        
        setup = InteractiveSetup()
        setup.project_root = self.temp_dir
        setup.venv_path = self.temp_dir / "venv"
        setup.env_file = env_file
        
        # Mock user choosing to keep existing config
        with patch.object(setup, 'collect_api_configuration', return_value={}), \
             patch('subprocess.run') as mock_subprocess:
            
            mock_subprocess.return_value.returncode = 0
            
            with patch.object(Path, 'exists', return_value=True):
                result = setup.run_setup()
        
        assert result is True
        # Verify existing config was preserved
        preserved_content = env_file.read_text()
        assert "secret_existing123" in preserved_content
    
    @pytest.mark.integration
    def test_installation_failure_recovery(self):
        """Test installation failure and recovery workflow"""
        setup = InteractiveSetup()
        setup.project_root = self.temp_dir
        setup.venv_path = self.temp_dir / "venv"
        setup.env_file = self.temp_dir / ".env"
        
        recovery_manager = get_recovery_manager(self.temp_dir)
        
        # Simulate virtual environment creation failure
        with patch.object(setup, 'create_virtual_environment', return_value=False):
            result = setup.run_setup()
            assert result is False
        
        # Test recovery diagnosis
        plan = recovery_manager.diagnose_failure("VENV_CREATION_FAILED", {})
        assert plan is not None
        assert plan.issue_type == "venv_creation_failed"
        assert len(plan.steps) > 0
    
    @pytest.mark.integration
    def test_configuration_preservation_workflow(self):
        """Test configuration preservation and migration workflow"""
        config_manager = get_config_manager(self.temp_dir)
        
        # Create old format configuration
        old_config = """NOTION_API_KEY=secret_old123
HUNTER_KEY=hunter_old123
OPENAI_KEY=sk-old123
"""
        env_file = self.temp_dir / ".env"
        env_file.write_text(old_config)
        
        # Analyze existing configuration
        config_info = config_manager.analyze_existing_configuration()
        assert config_info.env_file_exists is True
        assert "NOTION_API_KEY" in config_info.config_keys
        
        # Create backup
        success, backup_path = config_manager.create_backup(config_info)
        assert success is True
        assert backup_path is not None
        
        # Migrate configuration
        migration_success = config_manager.migrate_configuration(config_info)
        assert migration_success is True
        
        # Verify migration
        new_content = env_file.read_text()
        assert "NOTION_TOKEN=" in new_content
        assert "HUNTER_API_KEY=" in new_content
        assert "OPENAI_API_KEY=" in new_content


class TestCrossPlatformCompatibility:
    """Tests for cross-platform compatibility matrix"""
    
    def setup_method(self):
        """Set up platform testing environment"""
        self.platform_manager = get_platform_manager()
    
    @pytest.mark.platform
    @patch('platform.system', return_value='Windows')
    def test_windows_platform_detection(self, mock_system):
        """Test Windows platform-specific behavior"""
        from utils.platform_detection import PlatformManager
        pm = PlatformManager()
        
        assert pm.is_windows is True
        assert pm.is_unix is False
        assert pm.get_python_executable_name() == "python.exe"
        assert pm.get_shell_extension() == ".bat"
        
        # Test venv path
        venv_path = pm.get_venv_python_path(Path("test_venv"))
        assert str(venv_path) == "test_venv\\Scripts\\python.exe"
    
    @pytest.mark.platform
    @patch('platform.system', return_value='Darwin')
    def test_macos_platform_detection(self, mock_system):
        """Test macOS platform-specific behavior"""
        from utils.platform_detection import PlatformManager
        pm = PlatformManager()
        
        assert pm.is_macos is True
        assert pm.is_unix is True
        assert pm.get_python_executable_name() == "python"
        assert pm.get_shell_extension() == ".sh"
        
        # Test venv path
        venv_path = pm.get_venv_python_path(Path("test_venv"))
        assert str(venv_path) == "test_venv/bin/python"
    
    @pytest.mark.platform
    @patch('platform.system', return_value='Linux')
    def test_linux_platform_detection(self, mock_system):
        """Test Linux platform-specific behavior"""
        from utils.platform_detection import PlatformManager
        pm = PlatformManager()
        
        assert pm.is_linux is True
        assert pm.is_unix is True
        assert pm.get_python_executable_name() == "python"
        assert pm.get_shell_extension() == ".sh"
        
        # Test package manager detection
        with patch.object(pm, 'command_exists') as mock_cmd:
            mock_cmd.side_effect = lambda cmd: cmd == "apt-get"
            package_manager = pm.get_package_manager()
            assert package_manager == "apt"
    
    @pytest.mark.platform
    def test_cross_platform_runner_script_generation(self):
        """Test runner script generation across platforms"""
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            setup = InteractiveSetup()
            setup.project_root = temp_dir
            
            # Test Windows runner
            with patch('platform.system', return_value='Windows'):
                result = setup.create_windows_runner()
                assert result is True
                
                runner_file = temp_dir / "run.bat"
                assert runner_file.exists()
                
                content = runner_file.read_text()
                assert "@echo off" in content
                assert "venv\\Scripts\\python.exe" in content
                assert "%*" in content  # Windows argument passing
            
            # Test Unix runner
            with patch('platform.system', return_value='Linux'), \
                 patch('os.chmod') as mock_chmod:
                
                result = setup.create_unix_runner()
                assert result is True
                
                runner_file = temp_dir / "run.sh"
                assert runner_file.exists()
                
                content = runner_file.read_text()
                assert "#!/bin/bash" in content
                assert "venv/bin/python" in content
                assert '"$@"' in content  # Unix argument passing
                
                # Verify chmod was called to make executable
                mock_chmod.assert_called()
        
        finally:
            shutil.rmtree(temp_dir)
    
    @pytest.mark.platform
    def test_platform_specific_error_messages(self):
        """Test platform-specific error messages and recovery instructions"""
        error_handler = get_error_handler()
        
        # Test Python installation instructions
        with patch.object(error_handler, 'platform', 'windows'):
            error_info = error_handler.handle_error("PYTHON_NOT_FOUND")
            instructions = error_info.recovery_instructions
            assert any("python.org" in inst for inst in instructions)
            assert any("PATH" in inst for inst in instructions)
        
        with patch.object(error_handler, 'platform', 'macos'):
            error_info = error_handler.handle_error("PYTHON_NOT_FOUND")
            instructions = error_info.recovery_instructions
            assert any("brew" in inst for inst in instructions)
        
        with patch.object(error_handler, 'platform', 'linux'):
            error_info = error_handler.handle_error("PYTHON_NOT_FOUND")
            instructions = error_info.recovery_instructions
            assert any("apt-get" in inst for inst in instructions)
    
    @pytest.mark.platform
    def test_system_requirements_check(self):
        """Test system requirements checking across platforms"""
        pm = self.platform_manager
        
        requirements_ok, issues = pm.check_requirements()
        
        # Should always return boolean and list
        assert isinstance(requirements_ok, bool)
        assert isinstance(issues, list)
        
        # If Python is too old, should be in issues
        if sys.version_info < (3, 13):
            assert any("Python" in issue for issue in issues)


class TestErrorScenarioHandling:
    """Tests for various error scenarios and recovery"""
    
    def setup_method(self):
        """Set up error testing environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.error_handler = get_error_handler()
        self.recovery_manager = get_recovery_manager(self.temp_dir)
    
    def teardown_method(self):
        """Clean up error testing environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.integration
    def test_network_error_scenario(self):
        """Test handling of network connectivity issues"""
        from utils.api_validators import APIValidator
        
        validator = APIValidator(timeout=1, max_retries=1)
        
        # Mock network error
        with patch('requests.get', side_effect=ConnectionError("Network unreachable")):
            result = validator.validate_api_connection("NOTION_TOKEN", "secret_" + "a" * 43)
            
            assert result.result.value == "network_error"
            assert "Could not connect" in result.message
            assert result.retry_suggested is True
    
    @pytest.mark.integration
    def test_permission_error_scenario(self):
        """Test handling of permission errors"""
        # Create a directory without write permissions
        test_dir = self.temp_dir / "readonly"
        test_dir.mkdir()
        
        setup = InteractiveSetup()
        setup.project_root = test_dir
        setup.venv_path = test_dir / "venv"
        
        # Mock permission error
        with patch('subprocess.run', side_effect=PermissionError("Permission denied")):
            result = setup.create_virtual_environment()
            assert result is False
    
    @pytest.mark.integration
    def test_dependency_installation_failure(self):
        """Test handling of dependency installation failures"""
        setup = InteractiveSetup()
        setup.project_root = self.temp_dir
        setup.venv_path = self.temp_dir / "venv"
        
        # Create requirements.txt
        (self.temp_dir / "requirements.txt").write_text("nonexistent-package>=999.0")
        
        # Create venv structure
        setup.venv_path.mkdir()
        python_exe = setup.get_venv_python()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("fake python")
        
        # Mock failed dependency installation
        with patch('subprocess.run') as mock_subprocess, \
             patch.object(Path, 'exists', return_value=True):
            
            # Pip upgrade succeeds, but requirements install fails
            mock_subprocess.side_effect = [
                Mock(returncode=0),  # pip upgrade success
                Mock(returncode=1, stderr="Package not found")  # requirements failure
            ]
            
            result = setup.install_dependencies()
            assert result is False
    
    @pytest.mark.integration
    def test_configuration_validation_failure(self):
        """Test handling of configuration validation failures"""
        setup = InteractiveSetup()
        setup.project_root = self.temp_dir
        setup.venv_path = self.temp_dir / "venv"
        
        # Create CLI script that fails validation
        cli_content = """#!/usr/bin/env python3
import sys
sys.exit(1)  # Always fail
"""
        (self.temp_dir / "cli.py").write_text(cli_content)
        
        # Create venv structure
        setup.venv_path.mkdir()
        python_exe = setup.get_venv_python()
        python_exe.parent.mkdir(parents=True, exist_ok=True)
        python_exe.write_text("fake python")
        
        with patch.object(Path, 'exists', return_value=True):
            result = setup.validate_configuration()
            assert result is False
    
    @pytest.mark.integration
    def test_recovery_plan_execution(self):
        """Test execution of recovery plans"""
        # Test recovery for dependency installation failure
        plan = self.recovery_manager.diagnose_failure("DEPENDENCY_INSTALL_FAILED", {})
        assert plan is not None
        
        # Mock successful recovery steps
        with patch.object(self.recovery_manager, '_execute_recovery_step', return_value=True):
            success = self.recovery_manager.execute_recovery(plan, interactive=False)
            assert success is True
    
    @pytest.mark.integration
    def test_automatic_error_recovery(self):
        """Test automatic error recovery workflow"""
        error_type = "VENV_CREATION_FAILED"
        error_details = {"path": str(self.temp_dir / "venv")}
        
        # Mock successful automatic recovery
        with patch.object(self.recovery_manager, '_execute_recovery_step', return_value=True):
            result = self.recovery_manager.auto_recover_installation(error_type, error_details)
            assert result is True


class TestAPIValidationIntegration:
    """Integration tests for API validation workflow"""
    
    def setup_method(self):
        """Set up API validation testing"""
        from utils.api_validators import APIValidator
        self.validator = APIValidator(timeout=5, max_retries=1)
    
    @pytest.mark.network
    @pytest.mark.slow
    def test_real_api_validation_with_invalid_keys(self):
        """Test real API validation with intentionally invalid keys (requires network)"""
        # Test with obviously invalid keys
        invalid_keys = {
            "NOTION_TOKEN": "secret_invalid123",
            "HUNTER_API_KEY": "invalid_hunter_key",
            "OPENAI_API_KEY": "sk-invalid123"
        }
        
        results = self.validator.validate_all_apis(invalid_keys)
        
        # All should fail validation
        for key, result in results.items():
            if key in invalid_keys:
                assert result.result.value in ["invalid_credentials", "network_error"]
    
    @pytest.mark.integration
    def test_api_validation_format_checking(self):
        """Test API validation format checking without network calls"""
        # Test valid formats
        valid_keys = {
            "NOTION_TOKEN": "secret_" + "a" * 43,
            "HUNTER_API_KEY": "a" * 40,
            "OPENAI_API_KEY": "sk-" + "a" * 48,
            "RESEND_API_KEY": "re_" + "a" * 24,
            "SENDER_EMAIL": "test@example.com",
            "SENDER_NAME": "Test User"
        }
        
        for key, value in valid_keys.items():
            if key in ["SENDER_EMAIL", "SENDER_NAME"]:
                if key == "SENDER_EMAIL":
                    result = self.validator.validate_email_format(value)
                else:
                    continue  # Skip SENDER_NAME for this test
            else:
                result = self.validator.validate_format(key, value)
            
            assert result.result.value == "valid", f"Failed for {key}: {result.message}"
    
    @pytest.mark.integration
    def test_api_validation_retry_mechanism(self):
        """Test API validation retry mechanism"""
        # Mock intermittent network failures
        call_count = 0
        
        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:  # Fail first call, succeed second
                raise ConnectionError("Temporary network error")
            else:
                # Return successful response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"type": "user"}
                return mock_response
        
        with patch('requests.get', side_effect=mock_request):
            result = self.validator.validate_api_connection("NOTION_TOKEN", "secret_" + "a" * 43)
            
            # Should succeed after retry
            assert result.result.value == "valid"
            assert call_count == 2  # Verify retry happened


if __name__ == "__main__":
    pytest.main([__file__, "-v"])