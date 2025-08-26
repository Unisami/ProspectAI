"""
Platform detection and utilities for cross-platform installer compatibility.
"""

import os
import sys
import platform
import subprocess
from typing import Dict, Any, Optional, Tuple
from pathlib import Path


class PlatformManager:
    """Comprehensive platform detection and management utilities"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.release = platform.release()
        self.version = platform.version()
    
    @property
    def is_windows(self) -> bool:
        """Check if running on Windows"""
        return self.system == "windows"
    
    @property
    def is_macos(self) -> bool:
        """Check if running on macOS"""
        return self.system == "darwin"
    
    @property
    def is_linux(self) -> bool:
        """Check if running on Linux"""
        return self.system == "linux"
    
    @property
    def is_unix(self) -> bool:
        """Check if running on Unix-like system"""
        return self.is_macos or self.is_linux
    
    @property
    def platform_name(self) -> str:
        """Get friendly platform name"""
        if self.is_windows:
            return "Windows"
        elif self.is_macos:
            return "macOS"
        elif self.is_linux:
            return "Linux"
        else:
            return "Unknown"
    
    def get_python_executable_name(self) -> str:
        """Get the expected Python executable name for this platform"""
        if self.is_windows:
            return "python.exe"
        else:
            return "python"
    
    def get_venv_python_path(self, venv_dir: Path) -> Path:
        """Get the path to Python executable in virtual environment"""
        if self.is_windows:
            return venv_dir / "Scripts" / "python.exe"
        else:
            return venv_dir / "bin" / "python"
    
    def get_venv_pip_path(self, venv_dir: Path) -> Path:
        """Get the path to pip executable in virtual environment"""
        if self.is_windows:
            return venv_dir / "Scripts" / "pip.exe"
        else:
            return venv_dir / "bin" / "pip"
    
    def get_shell_extension(self) -> str:
        """Get shell script extension for this platform"""
        if self.is_windows:
            return ".bat"
        else:
            return ".sh"
    
    def get_executable_extension(self) -> str:
        """Get executable file extension"""
        if self.is_windows:
            return ".exe"
        else:
            return ""
    
    def detect_linux_distribution(self) -> Tuple[str, str]:
        """Detect Linux distribution and version"""
        if not self.is_linux:
            return "unknown", "unknown"
        
        try:
            # Try to read /etc/os-release
            if Path("/etc/os-release").exists():
                with open("/etc/os-release", "r") as f:
                    lines = f.readlines()
                
                distro_info = {}
                for line in lines:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        distro_info[key] = value.strip('"')
                
                name = distro_info.get("ID", "unknown")
                version = distro_info.get("VERSION_ID", "unknown")
                return name, version
            
            # Fallback methods
            elif Path("/etc/debian_version").exists():
                return "debian", "unknown"
            elif Path("/etc/redhat-release").exists():
                return "redhat", "unknown"
            elif Path("/etc/arch-release").exists():
                return "arch", "unknown"
            
        except Exception:
            pass
        
        return "unknown", "unknown"
    
    def get_package_manager(self) -> Optional[str]:
        """Detect available package manager"""
        if self.is_windows:
            # Check for winget
            if self.command_exists("winget"):
                return "winget"
            return None
        
        elif self.is_macos:
            # Check for Homebrew
            if self.command_exists("brew"):
                return "brew"
            return None
        
        elif self.is_linux:
            # Check for various Linux package managers
            if self.command_exists("apt-get"):
                return "apt"
            elif self.command_exists("dnf"):
                return "dnf"
            elif self.command_exists("yum"):
                return "yum"
            elif self.command_exists("pacman"):
                return "pacman"
            elif self.command_exists("zypper"):
                return "zypper"
            return None
        
        return None
    
    def command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH"""
        try:
            if self.is_windows:
                result = subprocess.run(
                    ["where", command], 
                    capture_output=True, 
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["which", command], 
                    capture_output=True, 
                    timeout=5
                )
            return result.returncode == 0
        except Exception:
            return False
    
    def check_python_version(self, python_cmd: str = "python") -> Tuple[bool, str]:
        """Check Python version and return (is_compatible, version_string)"""
        try:
            result = subprocess.run(
                [python_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version_str = result.stdout.strip()
                # Extract version numbers
                import re
                match = re.search(r"Python (\d+)\.(\d+)\.(\d+)", version_str)
                if match:
                    major, minor, patch = map(int, match.groups())
                    is_compatible = (major == 3 and minor >= 13)
                    return is_compatible, version_str
            
            return False, "Version detection failed"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def find_python_executables(self) -> Dict[str, Dict[str, Any]]:
        """Find all available Python executables and their versions"""
        python_commands = [
            "python", "python3", "python3.13", "python3.12", "python3.11",
            "py", "py.exe"  # Windows Python Launcher
        ]
        
        if self.is_windows:
            python_commands.extend(["python.exe", "python3.exe"])
        
        found_pythons = {}
        
        for cmd in python_commands:
            try:
                is_compatible, version = self.check_python_version(cmd)
                if "Error" not in version and "failed" not in version:
                    found_pythons[cmd] = {
                        "version": version,
                        "compatible": is_compatible,
                        "path": self.get_command_path(cmd)
                    }
            except Exception:
                continue
        
        return found_pythons
    
    def get_command_path(self, command: str) -> Optional[str]:
        """Get the full path of a command"""
        try:
            if self.is_windows:
                result = subprocess.run(
                    ["where", command],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["which", command],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except Exception:
            pass
        
        return None
    
    def is_admin(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            if self.is_windows:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin() != 0
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    def get_install_python_command(self) -> Optional[str]:
        """Get the command to install Python on this platform"""
        package_manager = self.get_package_manager()
        
        if self.is_windows and package_manager == "winget":
            return "winget install --id Python.Python.3.13 -e"
        
        elif self.is_macos and package_manager == "brew":
            return "brew install python@3.13"
        
        elif self.is_linux:
            if package_manager == "apt":
                return "sudo apt-get install -y python3.13 python3.13-venv python3.13-pip"
            elif package_manager == "dnf":
                return "sudo dnf install -y python3.13 python3.13-pip"
            elif package_manager == "yum":
                return "sudo yum install -y python3.13 python3.13-pip"
            elif package_manager == "pacman":
                return "sudo pacman -S python"
        
        return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "architecture": platform.architecture()
            },
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "path": sys.path[:3]  # First 3 entries
            },
            "environment": {
                "user": os.getlogin() if hasattr(os, 'getlogin') else "unknown",
                "home": str(Path.home()),
                "cwd": str(Path.cwd()),
                "is_admin": self.is_admin()
            },
            "capabilities": {
                "package_manager": self.get_package_manager(),
                "python_executables": self.find_python_executables(),
                "install_command": self.get_install_python_command()
            }
        }
        
        if self.is_linux:
            distro, version = self.detect_linux_distribution()
            info["platform"]["linux_distribution"] = distro
            info["platform"]["linux_version"] = version
        
        return info
    
    def check_requirements(self) -> Tuple[bool, List[str]]:
        """Check if system meets installation requirements"""
        issues = []
        
        # Check Python
        pythons = self.find_python_executables()
        compatible_python = any(p["compatible"] for p in pythons.values())
        
        if not compatible_python:
            if pythons:
                issues.append(f"Python 3.13+ required, found: {list(pythons.keys())}")
            else:
                issues.append("Python not found on system")
        
        # Check package manager (for auto-installation)
        if not compatible_python and not self.get_package_manager():
            issues.append(f"No package manager found for {self.platform_name}")
        
        # Check disk space
        try:
            import shutil
            free_space = shutil.disk_usage(Path.cwd()).free / (1024**3)  # GB
            if free_space < 0.5:
                issues.append(f"Insufficient disk space: {free_space:.1f}GB available")
        except Exception:
            issues.append("Could not check disk space")
        
        # Check network connectivity
        try:
            import urllib.request
            urllib.request.urlopen('https://pypi.org', timeout=5)
        except Exception:
            issues.append("No internet connection detected")
        
        # Check write permissions
        if not os.access(Path.cwd(), os.W_OK):
            issues.append("No write permission in current directory")
        
        return len(issues) == 0, issues


# Global platform manager instance
_platform_manager = None

def get_platform_manager() -> PlatformManager:
    """Get or create global platform manager instance"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformManager()
    return _platform_manager