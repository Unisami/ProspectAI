"""
Configuration preservation and management system for ProspectAI installer.
Handles existing configuration detection, backup, migration, and compatibility verification.
"""

import os
import sys
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from .platform_detection import get_platform_manager
from .api_validators import get_api_validator


@dataclass
class ConfigurationInfo:
    """Information about existing configuration"""
    env_file_exists: bool
    env_file_size: int
    env_file_modified: datetime
    venv_exists: bool
    venv_python_version: Optional[str]
    venv_size_mb: float
    config_keys: List[str]
    is_compatible: bool
    backup_created: bool = False
    backup_path: Optional[str] = None


@dataclass
class CompatibilityCheck:
    """Results of compatibility verification"""
    python_version_ok: bool
    venv_version_ok: bool
    dependencies_ok: bool
    config_format_ok: bool
    overall_compatible: bool
    issues: List[str]
    recommendations: List[str]


class ConfigurationManager:
    """Manages configuration preservation, backup, and migration"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.env_file = self.project_root / ".env"
        self.env_backup_dir = self.project_root / ".env_backups"
        self.venv_path = self.project_root / "venv"
        self.platform_manager = get_platform_manager()
        self.api_validator = get_api_validator()
        self.logger = logging.getLogger("config_manager")
        
        # Ensure backup directory exists
        self.env_backup_dir.mkdir(exist_ok=True)
    
    def analyze_existing_configuration(self) -> ConfigurationInfo:
        """Analyze existing configuration and environment"""
        env_exists = self.env_file.exists()
        env_size = self.env_file.stat().st_size if env_exists else 0
        env_modified = datetime.fromtimestamp(self.env_file.stat().st_mtime) if env_exists else datetime.min
        
        venv_exists = self.venv_path.exists()
        venv_python_version = self._get_venv_python_version() if venv_exists else None
        venv_size = self._calculate_directory_size(self.venv_path) if venv_exists else 0.0
        
        config_keys = self._parse_env_keys() if env_exists else []
        is_compatible = self._check_basic_compatibility(venv_python_version, config_keys)
        
        return ConfigurationInfo(
            env_file_exists=env_exists,
            env_file_size=env_size,
            env_file_modified=env_modified,
            venv_exists=venv_exists,
            venv_python_version=venv_python_version,
            venv_size_mb=venv_size,
            config_keys=config_keys,
            is_compatible=is_compatible
        )
    
    def _get_venv_python_version(self) -> Optional[str]:
        """Get Python version in virtual environment"""
        try:
            python_exe = self.platform_manager.get_venv_python_path(self.venv_path)
            if not python_exe.exists():
                return None
            
            import subprocess
            result = subprocess.run([
                str(python_exe), "--version"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout.strip()
            
        except Exception as e:
            self.logger.debug(f"Could not get venv Python version: {e}")
        
        return None
    
    def _calculate_directory_size(self, directory: Path) -> float:
        """Calculate directory size in MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _parse_env_keys(self) -> List[str]:
        """Parse keys from existing .env file"""
        if not self.env_file.exists():
            return []
        
        try:
            keys = []
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key = line.split('=', 1)[0].strip()
                        if key:
                            keys.append(key)
            return keys
        except Exception as e:
            self.logger.error(f"Error parsing .env file: {e}")
            return []
    
    def _check_basic_compatibility(self, venv_python_version: Optional[str], config_keys: List[str]) -> bool:
        """Check basic compatibility of existing setup"""
        if venv_python_version:
            # Check if Python version is compatible
            import re
            match = re.search(r"(\d+)\.(\d+)\.(\d+)", venv_python_version)
            if match:
                major, minor, patch = map(int, match.groups())
                if major != 3 or minor < 13:
                    return False
        
        # Check if essential config keys are present
        required_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY"]
        missing_keys = [key for key in required_keys if key not in config_keys]
        
        return len(missing_keys) == 0
    
    def create_backup(self, config_info: ConfigurationInfo) -> Tuple[bool, Optional[str]]:
        """Create backup of existing configuration"""
        if not config_info.env_file_exists:
            return True, None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f".env.backup_{timestamp}"
            backup_path = self.env_backup_dir / backup_filename
            
            shutil.copy2(self.env_file, backup_path)
            
            # Also create a metadata file
            metadata = {
                "original_path": str(self.env_file),
                "backup_created": timestamp,
                "original_size": config_info.env_file_size,
                "original_modified": config_info.env_file_modified.isoformat(),
                "config_keys": config_info.config_keys,
                "python_version": sys.version,
                "platform": self.platform_manager.platform_name
            }
            
            metadata_path = self.env_backup_dir / f"{backup_filename}.metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Configuration backup created: {backup_path}")
            return True, str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return False, None
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore configuration from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create current backup before restore
            if self.env_file.exists():
                current_backup_path = self.env_backup_dir / f".env.before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(self.env_file, current_backup_path)
            
            # Restore from backup
            shutil.copy2(backup_file, self.env_file)
            
            self.logger.info(f"Configuration restored from: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available configuration backups"""
        backups = []
        
        try:
            for backup_file in self.env_backup_dir.glob(".env.backup_*"):
                if backup_file.suffix != '.json':  # Skip metadata files
                    metadata_file = backup_file.with_suffix(backup_file.suffix + '.metadata.json')
                    
                    backup_info = {
                        "path": str(backup_file),
                        "filename": backup_file.name,
                        "size": backup_file.stat().st_size,
                        "created": datetime.fromtimestamp(backup_file.stat().st_mtime),
                        "metadata": None
                    }
                    
                    # Load metadata if available
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r') as f:
                                backup_info["metadata"] = json.load(f)
                        except Exception:
                            pass
                    
                    backups.append(backup_info)
            
            # Sort by creation time, newest first
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Error listing backups: {e}")
        
        return backups
    
    def check_compatibility(self) -> CompatibilityCheck:
        """Comprehensive compatibility check"""
        issues = []
        recommendations = []
        
        # Check Python version
        current_version = sys.version_info
        python_version_ok = current_version >= (3, 13)
        if not python_version_ok:
            issues.append(f"Python {current_version.major}.{current_version.minor} is too old, need 3.13+")
            recommendations.append("Upgrade to Python 3.13 or higher")
        
        # Check virtual environment
        venv_version_ok = True
        if self.venv_path.exists():
            venv_python_version = self._get_venv_python_version()
            if venv_python_version:
                import re
                match = re.search(r"(\d+)\.(\d+)\.(\d+)", venv_python_version)
                if match:
                    major, minor, patch = map(int, match.groups())
                    venv_version_ok = major == 3 and minor >= 13
                    if not venv_version_ok:
                        issues.append(f"Virtual environment Python version {major}.{minor} is too old")
                        recommendations.append("Recreate virtual environment with Python 3.13+")
        
        # Check dependencies
        dependencies_ok = self._check_dependencies()
        if not dependencies_ok:
            issues.append("Some required dependencies are missing or incompatible")
            recommendations.append("Reinstall dependencies with: pip install -r requirements.txt")
        
        # Check configuration format
        config_format_ok = True
        if self.env_file.exists():
            config_keys = self._parse_env_keys()
            required_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY"]
            missing_keys = [key for key in required_keys if key not in config_keys]
            
            if missing_keys:
                config_format_ok = False
                issues.append(f"Missing required configuration keys: {', '.join(missing_keys)}")
                recommendations.append("Run interactive setup to complete configuration")
        
        overall_compatible = python_version_ok and venv_version_ok and dependencies_ok and config_format_ok
        
        return CompatibilityCheck(
            python_version_ok=python_version_ok,
            venv_version_ok=venv_version_ok,
            dependencies_ok=dependencies_ok,
            config_format_ok=config_format_ok,
            overall_compatible=overall_compatible,
            issues=issues,
            recommendations=recommendations
        )
    
    def _check_dependencies(self) -> bool:
        """Check if required dependencies are installed in venv"""
        if not self.venv_path.exists():
            return False
        
        try:
            python_exe = self.platform_manager.get_venv_python_path(self.venv_path)
            if not python_exe.exists():
                return False
            
            # Check for essential packages
            essential_packages = [
                "requests", "notion-client", "openai", "pyhunter",
                "click", "rich", "python-dotenv"
            ]
            
            import subprocess
            for package in essential_packages:
                result = subprocess.run([
                    str(python_exe), "-c", f"import {package.replace('-', '_')}"
                ], capture_output=True, timeout=10)
                
                if result.returncode != 0:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def migrate_configuration(self, config_info: ConfigurationInfo) -> bool:
        """Migrate existing configuration to current format"""
        try:
            if not config_info.env_file_exists:
                return True
            
            # Read existing configuration
            existing_config = {}
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        existing_config[key.strip()] = value.strip()
            
            # Create updated configuration with current format
            updated_config = self._create_updated_config(existing_config)
            
            # Write updated configuration
            self._write_updated_config(updated_config)
            
            self.logger.info("Configuration migrated to current format")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration migration failed: {e}")
            return False
    
    def _create_updated_config(self, existing_config: Dict[str, str]) -> Dict[str, str]:
        """Create updated configuration with current standards"""
        updated = {}
        
        # Standard key mappings (in case keys were renamed)
        key_mappings = {
            "NOTION_API_KEY": "NOTION_TOKEN",
            "HUNTER_KEY": "HUNTER_API_KEY",
            "OPENAI_KEY": "OPENAI_API_KEY",
            "RESEND_KEY": "RESEND_API_KEY"
        }
        
        # Map old keys to new keys
        for old_key, new_key in key_mappings.items():
            if old_key in existing_config and new_key not in existing_config:
                updated[new_key] = existing_config[old_key]
        
        # Copy existing valid keys
        valid_keys = [
            "NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY", "RESEND_API_KEY",
            "SENDER_EMAIL", "SENDER_NAME"
        ]
        
        for key in valid_keys:
            if key in existing_config:
                updated[key] = existing_config[key]
        
        return updated
    
    def _write_updated_config(self, config: Dict[str, str]):
        """Write updated configuration to .env file"""
        lines = [
            "# ProspectAI Configuration",
            "# Updated by configuration manager",
            f"# Last updated: {datetime.now().isoformat()}",
            "",
            "# Core API Configuration"
        ]
        
        core_keys = ["NOTION_TOKEN", "HUNTER_API_KEY", "OPENAI_API_KEY"]
        for key in core_keys:
            if key in config:
                lines.append(f"{key}={config[key]}")
            else:
                lines.append(f"# {key}=")
        
        lines.extend(["", "# Optional Email Configuration"])
        optional_keys = ["RESEND_API_KEY", "SENDER_EMAIL", "SENDER_NAME"]
        for key in optional_keys:
            if key in config:
                lines.append(f"{key}={config[key]}")
            else:
                lines.append(f"# {key}=")
        
        lines.append("")
        
        with open(self.env_file, 'w') as f:
            f.write('\n'.join(lines))
    
    def prompt_for_preservation_choices(self, config_info: ConfigurationInfo) -> Dict[str, bool]:
        """Prompt user for configuration preservation choices"""
        choices = {
            "preserve_env": False,
            "preserve_venv": False,
            "create_backup": False
        }
        
        print("\n" + "=" * 60)
        print("🔍 Existing Configuration Detected")
        print("=" * 60)
        
        if config_info.env_file_exists:
            print(f"📁 Configuration file: {self.env_file}")
            print(f"   Size: {config_info.env_file_size} bytes")
            print(f"   Modified: {config_info.env_file_modified.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Keys found: {', '.join(config_info.config_keys)}")
            print()
            
            if config_info.is_compatible:
                default_preserve = "Y"
                print("✅ Configuration appears compatible with current version")
            else:
                default_preserve = "n"
                print("⚠️  Configuration may need updates for current version")
            
            response = input(f"Preserve existing configuration? ({default_preserve}/n): ").strip()
            choices["preserve_env"] = response.lower() not in ['n', 'no'] if default_preserve == "Y" else response.lower() in ['y', 'yes']
            
            if choices["preserve_env"]:
                response = input("Create backup before modifying? (Y/n): ").strip()
                choices["create_backup"] = response.lower() not in ['n', 'no']
        
        if config_info.venv_exists:
            print(f"\n📦 Virtual environment: {self.venv_path}")
            print(f"   Python version: {config_info.venv_python_version or 'Unknown'}")
            print(f"   Size: {config_info.venv_size_mb:.1f} MB")
            print()
            
            if config_info.venv_python_version and "3.13" in config_info.venv_python_version:
                default_preserve = "Y"
                print("✅ Virtual environment Python version is compatible")
            else:
                default_preserve = "n"
                print("⚠️  Virtual environment may need recreation")
            
            response = input(f"Reuse existing virtual environment? ({default_preserve}/n): ").strip()
            choices["preserve_venv"] = response.lower() not in ['n', 'no'] if default_preserve == "Y" else response.lower() in ['y', 'yes']
        
        return choices
    
    def apply_preservation_choices(self, config_info: ConfigurationInfo, choices: Dict[str, bool]) -> bool:
        """Apply user's preservation choices"""
        try:
            # Create backup if requested
            if choices.get("create_backup", False) and config_info.env_file_exists:
                success, backup_path = self.create_backup(config_info)
                if success:
                    print(f"✅ Configuration backup created: {backup_path}")
                else:
                    print("❌ Failed to create backup")
                    return False
            
            # Handle virtual environment preservation
            if not choices.get("preserve_venv", False) and config_info.venv_exists:
                print("🗑️  Removing existing virtual environment...")
                shutil.rmtree(self.venv_path)
                print("✅ Virtual environment removed")
            
            # Handle configuration preservation
            if not choices.get("preserve_env", False) and config_info.env_file_exists:
                print("🗑️  Removing existing configuration...")
                self.env_file.unlink()
                print("✅ Configuration file removed")
            elif choices.get("preserve_env", False) and config_info.env_file_exists:
                # Migrate configuration if needed
                if not config_info.is_compatible:
                    print("🔄 Migrating configuration to current format...")
                    if self.migrate_configuration(config_info):
                        print("✅ Configuration migrated successfully")
                    else:
                        print("❌ Configuration migration failed")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying preservation choices: {e}")
            return False


# Global configuration manager instance
_config_manager = None

def get_config_manager(project_root: Path = None) -> ConfigurationManager:
    """Get or create global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(project_root)
    return _config_manager