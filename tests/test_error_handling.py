"""
Unit tests for error handling framework and API validation components.
"""

import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.installer_error_handler import ErrorHandler, ErrorCategory, ErrorInfo, PlatformDetector
from utils.api_validators import APIValidator, APIValidationResult, ValidationResult
from utils.platform_detection import PlatformManager
from utils.recovery_manager import InstallationRecoveryManager, RecoveryAction, RecoveryStep


class TestErrorHandler:
    """Test suite for ErrorHandler class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_file = self.temp_dir / "test_errors.log"
        self.error_handler = ErrorHandler(self.log_file)
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization"""
        assert self.error_handler.platform in ["windows", "macos", "linux", "unknown"]
        assert self.error_handler.logger is not None
        assert len(self.error_handler.error_registry) > 0
    
    def test_handle_known_error(self):
        """Test handling a known error code"""
        result = self.error_handler.handle_error("PYTHON_NOT_FOUND")
        
        assert isinstance(result, ErrorInfo)
        assert result.category == ErrorCategory.SYSTEM_ERROR
        assert result.code == "PYTHON_NOT_FOUND"
        assert "Python 3.13 not found" in result.message
        assert len(result.recovery_instructions) > 0
    
    def test_handle_unknown_error(self):
        """Test handling an unknown error code"""
        result = self.error_handler.handle_error("UNKNOWN_ERROR_CODE")
        
        assert isinstance(result, ErrorInfo)
        assert result.category == ErrorCategory.UNKNOWN_ERROR
        assert result.code == "UNKNOWN_ERROR_CODE"
        assert "Unknown error occurred" in result.message
    
    def test_handle_exception_with_context(self):
        """Test handling exception with context"""
        exception = FileNotFoundError("Test file not found")
        context = "Testing file operations"
        
        result = self.error_handler.handle_exception(exception, context)
        
        assert isinstance(result, ErrorInfo)
        assert result.code == "FILE_NOT_FOUND"
    
    def test_validate_environment(self):
        """Test environment validation"""
        warnings = self.error_handler.validate_environment()
        
        assert isinstance(warnings, list)
        # Should have at least one warning about Python version if < 3.13
        if sys.version_info < (3, 13):
            assert any("Python" in warning for warning in warnings)
    
    def test_create_diagnostic_report(self):
        """Test diagnostic report creation"""
        report = self.error_handler.create_diagnostic_report()
        
        assert "platform_info" in report
        assert "python_executable" in report
        assert "environment_variables" in report
        assert "user_permissions" in report
        assert "warnings" in report


class TestPlatformDetector:
    """Test suite for PlatformDetector utility"""
    
    def test_get_platform(self):
        """Test platform detection"""
        platform = PlatformDetector.get_platform()
        assert platform in ["windows", "macos", "linux", "unknown"]
    
    def test_get_platform_info(self):
        """Test platform info collection"""
        info = PlatformDetector.get_platform_info()
        
        assert "system" in info
        assert "python_version" in info
        assert "executable" in info
        assert info["system"] in ["Windows", "Darwin", "Linux"]
    
    @patch('platform.system', return_value='Windows')
    @patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=1)
    def test_is_admin_windows_true(self, mock_admin, mock_system):
        """Test admin detection on Windows (admin)"""
        result = PlatformDetector.is_admin()
        assert result is True
    
    @patch('platform.system', return_value='Linux')
    @patch('os.geteuid', return_value=0)
    def test_is_admin_unix_true(self, mock_geteuid, mock_system):
        """Test admin detection on Unix (root)"""
        result = PlatformDetector.is_admin()
        assert result is True
    
    @patch('platform.system', return_value='Linux')
    @patch('os.geteuid', return_value=1000)
    def test_is_admin_unix_false(self, mock_geteuid, mock_system):
        """Test admin detection on Unix (non-root)"""
        result = PlatformDetector.is_admin()
        assert result is False


class TestAPIValidator:
    """Test suite for APIValidator class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = APIValidator(timeout=5, max_retries=1)
    
    def test_validate_format_notion_valid(self):
        """Test valid Notion token format validation"""
        valid_token = "secret_" + "a" * 43
        result = self.validator.validate_format("NOTION_TOKEN", valid_token)
        
        assert result.result == APIValidationResult.VALID
        assert result.api_name == "Notion"
        assert result.key_name == "NOTION_TOKEN"
    
    def test_validate_format_notion_invalid(self):
        """Test invalid Notion token format validation"""
        invalid_token = "invalid_token"
        result = self.validator.validate_format("NOTION_TOKEN", invalid_token)
        
        assert result.result == APIValidationResult.INVALID_FORMAT
        assert "Invalid format" in result.message
        assert result.help_url is not None
    
    def test_validate_format_openai_valid(self):
        """Test valid OpenAI key format validation"""
        valid_key = "sk-" + "a" * 48
        result = self.validator.validate_format("OPENAI_API_KEY", valid_key)
        
        assert result.result == APIValidationResult.VALID
        assert result.api_name == "OpenAI"
    
    def test_validate_format_openai_invalid(self):
        """Test invalid OpenAI key format validation"""
        invalid_key = "sk-short"
        result = self.validator.validate_format("OPENAI_API_KEY", invalid_key)
        
        assert result.result == APIValidationResult.INVALID_FORMAT
    
    def test_validate_format_empty_key(self):
        """Test validation of empty API key"""
        result = self.validator.validate_format("NOTION_TOKEN", "")
        
        assert result.result == APIValidationResult.INVALID_FORMAT
        assert "empty" in result.message
    
    def test_validate_format_unknown_key(self):
        """Test validation of unknown key type"""
        result = self.validator.validate_format("UNKNOWN_KEY", "test_value")
        
        assert result.result == APIValidationResult.UNKNOWN_ERROR
    
    @patch('requests.get')
    def test_validate_notion_success(self, mock_get):
        """Test successful Notion API validation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"type": "user", "name": "Test User"}
        mock_get.return_value = mock_response
        
        valid_token = "secret_" + "a" * 43
        result = self.validator.validate_api_connection("NOTION_TOKEN", valid_token)
        
        assert result.result == APIValidationResult.VALID
        assert "Valid Notion token" in result.message
    
    @patch('requests.get')
    def test_validate_notion_invalid_credentials(self, mock_get):
        """Test Notion API validation with invalid credentials"""
        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        invalid_token = "secret_" + "a" * 43
        result = self.validator.validate_api_connection("NOTION_TOKEN", invalid_token)
        
        assert result.result == APIValidationResult.INVALID_CREDENTIALS
        assert "Invalid Notion token" in result.message
    
    @patch('requests.get')
    def test_validate_api_network_error(self, mock_get):
        """Test API validation with network error"""
        # Mock network error
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        valid_token = "secret_" + "a" * 43
        result = self.validator.validate_api_connection("NOTION_TOKEN", valid_token)
        
        assert result.result == APIValidationResult.NETWORK_ERROR
        assert "Could not connect" in result.message
    
    @patch('requests.get')
    def test_validate_api_timeout(self, mock_get):
        """Test API validation with timeout"""
        # Mock timeout error
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        valid_token = "secret_" + "a" * 43
        result = self.validator.validate_api_connection("NOTION_TOKEN", valid_token)
        
        assert result.result == APIValidationResult.NETWORK_ERROR
        assert "timed out" in result.message
    
    @patch('requests.get')
    def test_validate_hunter_success(self, mock_get):
        """Test successful Hunter.io API validation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "plan_name": "Free",
                "calls": {"used": 10, "available": 100}
            }
        }
        mock_get.return_value = mock_response
        
        result = self.validator.validate_api_connection("HUNTER_API_KEY", "test_hunter_key")
        
        assert result.result == APIValidationResult.VALID
        assert "Valid Hunter.io key" in result.message
    
    @patch('requests.get')
    def test_validate_openai_success(self, mock_get):
        """Test successful OpenAI API validation"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-3.5-turbo"},
                {"id": "gpt-4"}
            ]
        }
        mock_get.return_value = mock_response
        
        valid_key = "sk-" + "a" * 48
        result = self.validator.validate_api_connection("OPENAI_API_KEY", valid_key)
        
        assert result.result == APIValidationResult.VALID
        assert "Valid OpenAI API key" in result.message
    
    def test_validate_email_format_valid(self):
        """Test valid email format validation"""
        result = self.validator.validate_email_format("test@example.com")
        
        assert result.result == APIValidationResult.VALID
        assert result.api_name == "Email"
    
    def test_validate_email_format_invalid(self):
        """Test invalid email format validation"""
        result = self.validator.validate_email_format("invalid_email")
        
        assert result.result == APIValidationResult.INVALID_FORMAT
        assert "Invalid email address format" in result.message
    
    def test_validate_email_format_empty(self):
        """Test empty email validation"""
        result = self.validator.validate_email_format("")
        
        assert result.result == APIValidationResult.INVALID_FORMAT
        assert "empty" in result.message
    
    def test_validate_all_apis(self):
        """Test validation of multiple APIs"""
        config = {
            "NOTION_TOKEN": "secret_" + "a" * 43,
            "HUNTER_API_KEY": "hunter_key_123",
            "OPENAI_API_KEY": "sk-" + "a" * 48,
            "SENDER_EMAIL": "test@example.com",
            "SENDER_NAME": "Test User"
        }
        
        with patch.object(self.validator, 'validate_api_connection') as mock_validate:
            mock_validate.return_value = ValidationResult(
                api_name="Test",
                key_name="TEST_KEY",
                result=APIValidationResult.VALID,
                message="Valid"
            )
            
            results = self.validator.validate_all_apis(config)
        
        assert len(results) == 5
        assert all(result.result == APIValidationResult.VALID for result in results.values())
    
    def test_get_validation_summary_all_valid(self):
        """Test validation summary with all valid results"""
        results = {
            "NOTION_TOKEN": ValidationResult("Notion", "NOTION_TOKEN", APIValidationResult.VALID, "Valid"),
            "HUNTER_API_KEY": ValidationResult("Hunter", "HUNTER_API_KEY", APIValidationResult.VALID, "Valid")
        }
        
        success, summary = self.validator.get_validation_summary(results)
        
        assert success is True
        assert "All 2 API keys validated successfully" in summary
    
    def test_get_validation_summary_some_failed(self):
        """Test validation summary with some failures"""
        results = {
            "NOTION_TOKEN": ValidationResult("Notion", "NOTION_TOKEN", APIValidationResult.VALID, "Valid"),
            "HUNTER_API_KEY": ValidationResult("Hunter", "HUNTER_API_KEY", APIValidationResult.INVALID_FORMAT, "Invalid")
        }
        
        success, summary = self.validator.get_validation_summary(results)
        
        assert success is False
        assert "1/2 API keys failed validation" in summary


class TestPlatformManager:
    """Test suite for PlatformManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.platform_manager = PlatformManager()
    
    def test_platform_properties(self):
        """Test platform detection properties"""
        # At least one should be true
        platforms = [
            self.platform_manager.is_windows,
            self.platform_manager.is_macos,
            self.platform_manager.is_linux
        ]
        assert any(platforms)
        
        # Unix should be true if macOS or Linux
        if self.platform_manager.is_macos or self.platform_manager.is_linux:
            assert self.platform_manager.is_unix
    
    @patch('platform.system', return_value='Windows')
    def test_windows_detection(self, mock_system):
        """Test Windows platform detection"""
        pm = PlatformManager()
        assert pm.is_windows
        assert not pm.is_macos
        assert not pm.is_linux
        assert not pm.is_unix
        assert pm.platform_name == "Windows"
    
    @patch('platform.system', return_value='Darwin')
    def test_macos_detection(self, mock_system):
        """Test macOS platform detection"""
        pm = PlatformManager()
        assert not pm.is_windows
        assert pm.is_macos
        assert not pm.is_linux
        assert pm.is_unix
        assert pm.platform_name == "macOS"
    
    def test_get_python_executable_name(self):
        """Test Python executable name detection"""
        if self.platform_manager.is_windows:
            assert self.platform_manager.get_python_executable_name() == "python.exe"
        else:
            assert self.platform_manager.get_python_executable_name() == "python"
    
    def test_get_venv_python_path(self):
        """Test virtual environment Python path"""
        venv_dir = Path("test_venv")
        python_path = self.platform_manager.get_venv_python_path(venv_dir)
        
        if self.platform_manager.is_windows:
            assert python_path == venv_dir / "Scripts" / "python.exe"
        else:
            assert python_path == venv_dir / "bin" / "python"
    
    def test_get_shell_extension(self):
        """Test shell script extension"""
        if self.platform_manager.is_windows:
            assert self.platform_manager.get_shell_extension() == ".bat"
        else:
            assert self.platform_manager.get_shell_extension() == ".sh"
    
    @patch('subprocess.run')
    def test_command_exists_true(self, mock_subprocess):
        """Test command existence check (exists)"""
        mock_subprocess.return_value.returncode = 0
        
        result = self.platform_manager.command_exists("python")
        assert result is True
    
    @patch('subprocess.run')
    def test_command_exists_false(self, mock_subprocess):
        """Test command existence check (doesn't exist)"""
        mock_subprocess.return_value.returncode = 1
        
        result = self.platform_manager.command_exists("nonexistent_command")
        assert result is False
    
    @patch('subprocess.run')
    def test_check_python_version_compatible(self, mock_subprocess):
        """Test Python version check (compatible)"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Python 3.13.1"
        
        is_compatible, version = self.platform_manager.check_python_version("python3.13")
        
        assert is_compatible is True
        assert "Python 3.13.1" in version
    
    @patch('subprocess.run')
    def test_check_python_version_incompatible(self, mock_subprocess):
        """Test Python version check (incompatible)"""
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "Python 3.11.5"
        
        is_compatible, version = self.platform_manager.check_python_version("python3.11")
        
        assert is_compatible is False
        assert "Python 3.11.5" in version
    
    def test_get_system_info(self):
        """Test system information collection"""
        info = self.platform_manager.get_system_info()
        
        assert "platform" in info
        assert "python" in info
        assert "environment" in info
        assert "capabilities" in info
        
        assert "system" in info["platform"]
        assert "version" in info["python"]


class TestRecoveryManager:
    """Test suite for InstallationRecoveryManager class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.recovery_manager = InstallationRecoveryManager(self.temp_dir)
    
    def test_recovery_manager_initialization(self):
        """Test RecoveryManager initialization"""
        assert self.recovery_manager.project_root == self.temp_dir
        assert len(self.recovery_manager.recovery_plans) > 0
    
    def test_diagnose_failure_known_error(self):
        """Test diagnosing a known failure type"""
        plan = self.recovery_manager.diagnose_failure("PYTHON_NOT_FOUND", {})
        
        assert plan is not None
        assert plan.issue_type == "python_install_failed"
        assert len(plan.steps) > 0
    
    def test_diagnose_failure_unknown_error(self):
        """Test diagnosing an unknown failure type"""
        plan = self.recovery_manager.diagnose_failure("UNKNOWN_ERROR", {})
        
        assert plan is None
    
    def test_create_diagnostic_report(self):
        """Test diagnostic report creation"""
        failures = ["PYTHON_NOT_FOUND", "VENV_CREATION_FAILED"]
        report = self.recovery_manager.create_recovery_report(failures)
        
        assert "platform" in report
        assert "failures" in report
        assert "recovery_plans" in report
        assert "recommendations" in report
        
        assert len(report["failures"]) == 2
        assert len(report["recovery_plans"]) > 0
        assert len(report["recommendations"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])