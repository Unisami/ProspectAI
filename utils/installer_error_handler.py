"""
Comprehensive error handling framework for ProspectAI installer system.
Provides categorized error responses, platform-specific recovery guidance, and logging.
"""

import os
import sys
import platform
import logging
import traceback
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass


class ErrorCategory(Enum):
    """Error categories for installer issues"""
    SYSTEM_ERROR = "system"
    NETWORK_ERROR = "network"
    CONFIGURATION_ERROR = "configuration"
    PERMISSION_ERROR = "permission"
    VALIDATION_ERROR = "validation"
    DEPENDENCY_ERROR = "dependency"
    UNKNOWN_ERROR = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information"""
    category: ErrorCategory
    code: str
    message: str
    details: str
    recovery_instructions: List[str]
    platform_specific: bool = False
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class PlatformDetector:
    """Utility class for platform detection and information"""
    
    @staticmethod
    def get_platform() -> str:
        """Get current platform identifier"""
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        elif system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        else:
            return "unknown"
    
    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """Get detailed platform information"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": platform.architecture(),
            "python_version": sys.version,
            "executable": sys.executable
        }
    
    @staticmethod
    def is_admin() -> bool:
        """Check if running with administrator/root privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False


class ErrorHandler:
    """Comprehensive error handling with categorized responses and recovery guidance"""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.platform = PlatformDetector.get_platform()
        self.platform_info = PlatformDetector.get_platform_info()
        self.logger = self._setup_logging(log_file)
        
        # Error code to ErrorInfo mapping
        self.error_registry = self._initialize_error_registry()
    
    def _setup_logging(self, log_file: Optional[Path] = None) -> logging.Logger:
        """Setup logging for error handling"""
        logger = logging.getLogger("installer_errors")
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.DEBUG)
                file_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
                file_handler.setFormatter(file_format)
                logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}")
        
        return logger
    
    def _initialize_error_registry(self) -> Dict[str, ErrorInfo]:
        """Initialize the error registry with predefined errors"""
        errors = {}
        
        # Python-related errors
        errors["PYTHON_NOT_FOUND"] = ErrorInfo(
            category=ErrorCategory.SYSTEM_ERROR,
            code="PYTHON_NOT_FOUND",
            message="Python 3.13 not found on system",
            details="The installer could not locate Python 3.13 on your system.",
            recovery_instructions=self._get_python_install_instructions()
        )
        
        errors["PYTHON_VERSION_INCOMPATIBLE"] = ErrorInfo(
            category=ErrorCategory.SYSTEM_ERROR,
            code="PYTHON_VERSION_INCOMPATIBLE",
            message="Python version is not compatible",
            details="ProspectAI requires Python 3.13 or higher.",
            recovery_instructions=self._get_python_upgrade_instructions()
        )
        
        # Package manager errors
        errors["PACKAGE_MANAGER_NOT_FOUND"] = ErrorInfo(
            category=ErrorCategory.SYSTEM_ERROR,
            code="PACKAGE_MANAGER_NOT_FOUND",
            message="Package manager not found",
            details="Could not find a suitable package manager to install Python.",
            recovery_instructions=self._get_package_manager_instructions()
        )
        
        # Virtual environment errors
        errors["VENV_CREATION_FAILED"] = ErrorInfo(
            category=ErrorCategory.SYSTEM_ERROR,
            code="VENV_CREATION_FAILED",
            message="Virtual environment creation failed",
            details="Could not create Python virtual environment.",
            recovery_instructions=[
                "Ensure Python 3.13 is properly installed",
                "Check available disk space",
                "Try running with administrator/sudo privileges",
                "Verify the venv module is available: python -m venv --help"
            ]
        )
        
        # Dependency installation errors
        errors["DEPENDENCY_INSTALL_FAILED"] = ErrorInfo(
            category=ErrorCategory.DEPENDENCY_ERROR,
            code="DEPENDENCY_INSTALL_FAILED",
            message="Failed to install dependencies",
            details="Could not install required Python packages.",
            recovery_instructions=[
                "Check your internet connection",
                "Upgrade pip: python -m pip install --upgrade pip",
                "Try installing packages individually",
                "Check if proxy settings are needed",
                "Disable antivirus temporarily if it's blocking downloads"
            ]
        )
        
        # Network errors
        errors["NETWORK_TIMEOUT"] = ErrorInfo(
            category=ErrorCategory.NETWORK_ERROR,
            code="NETWORK_TIMEOUT",
            message="Network operation timed out",
            details="Network operation took too long to complete.",
            recovery_instructions=[
                "Check your internet connection",
                "Try again in a few minutes",
                "Check if you're behind a firewall or proxy",
                "Consider using a different network"
            ]
        )
        
        # Permission errors
        errors["PERMISSION_DENIED"] = ErrorInfo(
            category=ErrorCategory.PERMISSION_ERROR,
            code="PERMISSION_DENIED",
            message="Permission denied",
            details="Insufficient permissions to perform the operation.",
            recovery_instructions=self._get_permission_instructions()
        )
        
        # Configuration errors
        errors["CONFIG_VALIDATION_FAILED"] = ErrorInfo(
            category=ErrorCategory.CONFIGURATION_ERROR,
            code="CONFIG_VALIDATION_FAILED",
            message="Configuration validation failed",
            details="API keys or configuration values are invalid.",
            recovery_instructions=[
                "Check API key formats and validity",
                "Ensure API keys have proper permissions",
                "Verify network connectivity to API services",
                "Check if API quotas are exceeded"
            ]
        )
        
        errors["API_KEY_INVALID"] = ErrorInfo(
            category=ErrorCategory.VALIDATION_ERROR,
            code="API_KEY_INVALID",
            message="Invalid API key format",
            details="The provided API key does not match the expected format.",
            recovery_instructions=[
                "Check the API key format against the documentation",
                "Ensure you copied the complete key",
                "Verify the key is from the correct service",
                "Check if the key has expired"
            ]
        )
        
        # Dashboard setup errors
        errors["DASHBOARD_SETUP_FAILED"] = ErrorInfo(
            category=ErrorCategory.CONFIGURATION_ERROR,
            code="DASHBOARD_SETUP_FAILED",
            message="Dashboard setup failed",
            details="Could not set up the Notion dashboard.",
            recovery_instructions=[
                "Check Notion token permissions",
                "Verify the integration has access to create pages",
                "Ensure the integration is shared with your workspace",
                "Check network connectivity to Notion API"
            ]
        )
        
        return errors
    
    def _get_python_install_instructions(self) -> List[str]:
        """Get platform-specific Python installation instructions"""
        if self.platform == "windows":
            return [
                "Install Python 3.13 from the Microsoft Store or python.org",
                "Download from: https://www.python.org/downloads/",
                "During installation, check 'Add Python to PATH'",
                "Restart your command prompt after installation"
            ]
        elif self.platform == "macos":
            return [
                "Install Homebrew if not already installed",
                "Run: brew install python@3.13",
                "Or download from: https://www.python.org/downloads/"
            ]
        else:  # linux
            return [
                "Ubuntu/Debian: sudo apt-get install python3.13 python3.13-venv",
                "CentOS/RHEL: sudo dnf install python3.13",
                "Or download from: https://www.python.org/downloads/"
            ]
    
    def _get_python_upgrade_instructions(self) -> List[str]:
        """Get Python upgrade instructions"""
        base_instructions = [
            "ProspectAI requires Python 3.13 or higher",
            "Current Python version: " + sys.version.split()[0]
        ]
        base_instructions.extend(self._get_python_install_instructions())
        return base_instructions
    
    def _get_package_manager_instructions(self) -> List[str]:
        """Get package manager installation instructions"""
        if self.platform == "windows":
            return [
                "Install winget (Windows Package Manager)",
                "It should be available on Windows 10 1709+ and Windows 11",
                "Or install Python manually from python.org"
            ]
        elif self.platform == "macos":
            return [
                "Install Homebrew package manager",
                "Run: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"",
                "Then run the installer again"
            ]
        else:  # linux
            return [
                "Ensure your system's package manager is available",
                "Ubuntu/Debian: apt-get should be pre-installed",
                "CentOS/RHEL: dnf or yum should be available",
                "If not available, install Python manually"
            ]
    
    def _get_permission_instructions(self) -> List[str]:
        """Get permission elevation instructions"""
        if self.platform == "windows":
            return [
                "Run the installer as Administrator",
                "Right-click Command Prompt and select 'Run as administrator'",
                "Or right-click the installer and select 'Run as administrator'"
            ]
        else:  # unix systems
            return [
                "Run the installer with sudo privileges",
                "Use: sudo ./install.sh",
                "Or change permissions: chmod +x install.sh"
            ]
    
    def handle_error(self, error_code: str, exception: Optional[Exception] = None, 
                    context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
        """Handle an error with appropriate response and logging"""
        
        # Get error info
        error_info = self.error_registry.get(error_code)
        if not error_info:
            error_info = ErrorInfo(
                category=ErrorCategory.UNKNOWN_ERROR,
                code=error_code,
                message="Unknown error occurred",
                details="An unexpected error occurred during installation.",
                recovery_instructions=[
                    "Check the error logs for more details",
                    "Try running the installer again",
                    "Report this issue if it persists"
                ]
            )
        
        # Log the error
        self._log_error(error_info, exception, context)
        
        # Display error to user
        self._display_error(error_info, exception)
        
        return error_info
    
    def _log_error(self, error_info: ErrorInfo, exception: Optional[Exception] = None,
                  context: Optional[Dict[str, Any]] = None):
        """Log error details"""
        log_data = {
            "error_code": error_info.code,
            "category": error_info.category.value,
            "message": error_info.message,
            "platform": self.platform,
            "platform_info": self.platform_info
        }
        
        if context:
            log_data["context"] = context
        
        if exception:
            log_data["exception"] = str(exception)
            log_data["traceback"] = traceback.format_exc()
        
        self.logger.error(f"Installation error: {error_info.code}", extra=log_data)
    
    def _display_error(self, error_info: ErrorInfo, exception: Optional[Exception] = None):
        """Display user-friendly error message"""
        print("\n" + "=" * 50)
        print(f"❌ {error_info.message}")
        print("=" * 50)
        print(f"\nError Code: {error_info.code}")
        print(f"Category: {error_info.category.value.title()}")
        print(f"\nDescription:")
        print(f"  {error_info.details}")
        
        if exception:
            print(f"\nTechnical Details:")
            print(f"  {str(exception)}")
        
        print(f"\n🔧 Recovery Instructions:")
        for i, instruction in enumerate(error_info.recovery_instructions, 1):
            print(f"  {i}. {instruction}")
        
        print(f"\n💡 If the problem persists:")
        print(f"  • Check the log files for detailed error information")
        print(f"  • Report the issue with error code: {error_info.code}")
        print(f"  • Include your platform: {self.platform}")
        print()
    
    def handle_exception(self, exception: Exception, context: Optional[str] = None) -> ErrorInfo:
        """Handle unexpected exceptions"""
        
        # Determine error code based on exception type
        error_code = "UNKNOWN_ERROR"
        
        if isinstance(exception, FileNotFoundError):
            error_code = "FILE_NOT_FOUND"
        elif isinstance(exception, PermissionError):
            error_code = "PERMISSION_DENIED"
        elif isinstance(exception, subprocess.TimeoutExpired):
            error_code = "NETWORK_TIMEOUT"
        elif isinstance(exception, ConnectionError):
            error_code = "NETWORK_ERROR"
        
        return self.handle_error(error_code, exception, {"context": context})
    
    def validate_environment(self) -> List[str]:
        """Validate the installation environment and return warnings"""
        warnings = []
        
        # Check Python version
        if sys.version_info < (3, 13):
            warnings.append(f"Python {sys.version_info.major}.{sys.version_info.minor} detected, 3.13+ recommended")
        
        # Check available disk space
        try:
            import shutil
            free_space = shutil.disk_usage(Path.cwd()).free / (1024**3)  # GB
            if free_space < 1:
                warnings.append(f"Low disk space: {free_space:.1f}GB available")
        except Exception:
            warnings.append("Could not check available disk space")
        
        # Check internet connectivity
        try:
            import urllib.request
            urllib.request.urlopen('https://pypi.org', timeout=5)
        except Exception:
            warnings.append("Internet connectivity issue detected")
        
        # Check permissions
        if not os.access(Path.cwd(), os.W_OK):
            warnings.append("Limited write permissions in current directory")
        
        return warnings
    
    def create_diagnostic_report(self) -> Dict[str, Any]:
        """Create a diagnostic report for troubleshooting"""
        return {
            "platform_info": self.platform_info,
            "python_executable": sys.executable,
            "python_path": sys.path,
            "environment_variables": dict(os.environ),
            "current_directory": str(Path.cwd()),
            "user_permissions": {
                "is_admin": PlatformDetector.is_admin(),
                "can_write": os.access(Path.cwd(), os.W_OK),
                "can_execute": os.access(Path.cwd(), os.X_OK)
            },
            "warnings": self.validate_environment()
        }


# Global error handler instance
_error_handler = None

def get_error_handler(log_file: Optional[Path] = None) -> ErrorHandler:
    """Get or create global error handler instance"""
    global _error_handler
    if _error_handler is None:
        if log_file is None:
            log_file = Path("logs") / "installer_errors.log"
        _error_handler = ErrorHandler(log_file)
    return _error_handler


def handle_error(error_code: str, exception: Optional[Exception] = None,
                context: Optional[Dict[str, Any]] = None) -> ErrorInfo:
    """Convenience function to handle errors"""
    return get_error_handler().handle_error(error_code, exception, context)


def handle_exception(exception: Exception, context: Optional[str] = None) -> ErrorInfo:
    """Convenience function to handle exceptions"""
    return get_error_handler().handle_exception(exception, context)