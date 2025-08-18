

import os
import json
import threading
import time
from pathlib import Path
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Callable,
    Union
)
from dataclasses import (
    dataclass,
    asdict
)
from datetime import datetime
import logging
import hashlib

import yaml

# Check if watchdog is available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

from utils.config import Config

"""
Enhanced configuration service with validation, caching, and hot-reloading capabilities.

This service provides centralized configuration management with the following features:
- Configuration validation and caching
- Hot-reloading without application restart
- Environment-specific configuration overrides
- Configuration change notifications
- Thread-safe operations
"""






@dataclass
class ConfigurationValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    missing_required: List[str]
    
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return len(self.errors) > 0 or len(self.missing_required) > 0
    
    def get_summary(self) -> str:
        """Get validation summary."""
        if self.is_valid:
            return "Configuration is valid"
        
        summary = []
        if self.errors:
            summary.append(f"Errors: {len(self.errors)}")
        if self.missing_required:
            summary.append(f"Missing required: {len(self.missing_required)}")
        if self.warnings:
            summary.append(f"Warnings: {len(self.warnings)}")
        
        return f"Configuration validation failed - {', '.join(summary)}"


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration overrides."""
    name: str
    overrides: Dict[str, Any]
    description: Optional[str] = None
    
    def apply_overrides(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment overrides to base configuration."""
        config = base_config.copy()
        config.update(self.overrides)
        return config


class ConfigurationChangeHandler:
    """File system event handler for configuration file changes."""
    
    def __init__(self, config_service: 'ConfigurationService'):
        self.config_service = config_service
        self.logger = logging.getLogger(__name__)
        
        # Only inherit from FileSystemEventHandler if watchdog is available
        if WATCHDOG_AVAILABLE and FileSystemEventHandler:
            self.__class__.__bases__ = (FileSystemEventHandler,)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            file_path = Path(event.src_path)
            if file_path.suffix.lower() in ['.yaml', '.yml', '.json', '.env']:
                self.logger.info(f"Configuration file changed: {file_path}")
                self.config_service._handle_file_change(str(file_path))


class ConfigurationService:
    """
    Enhanced configuration service with validation, caching, and hot-reloading.
    
    Features:
    - Configuration validation and caching
    - Hot-reloading without restart
    - Environment-specific overrides
    - Thread-safe operations
    - Change notifications
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 environment: Optional[str] = None,
                 enable_hot_reload: bool = True,
                 cache_ttl: int = 300):  # 5 minutes default TTL
        """
        Initialize configuration service.
        
        Args:
            config_path: Path to configuration file
            environment: Environment name (dev, staging, prod)
            enable_hot_reload: Enable automatic configuration reloading
            cache_ttl: Cache time-to-live in seconds
        """
        self.config_path = config_path
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.enable_hot_reload = enable_hot_reload
        self.cache_ttl = cache_ttl
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Configuration cache
        self._config_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._current_config: Optional[Config] = None
        self._config_hash: Optional[str] = None
        
        # Environment configurations
        self._environment_configs: Dict[str, EnvironmentConfig] = {}
        
        # Change notification callbacks
        self._change_callbacks: List[Callable[[Config, Config], None]] = []
        
        # File watching
        self._observer: Optional['Observer'] = None
        self._watched_files: List[str] = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the configuration service."""
        try:
            # Load initial configuration
            self._load_configuration()
            
            # Set up file watching if enabled
            if self.enable_hot_reload:
                self._setup_file_watching()
            
            # Load environment-specific configurations
            self._load_environment_configs()
            
            self.logger.info(f"Configuration service initialized for environment: {self.environment}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize configuration service: {e}")
            raise
    
    def _load_configuration(self) -> None:
        """Load configuration from file or environment."""
        with self._lock:
            try:
                if self.config_path and os.path.exists(self.config_path):
                    self._current_config = Config.from_file(self.config_path)
                    self._watched_files = [self.config_path]
                else:
                    self._current_config = Config.from_env()
                    # Watch .env file if it exists
                    env_file = Path('.env')
                    if env_file.exists():
                        self._watched_files = [str(env_file)]
                
                # Validate configuration
                validation_result = self.validate_configuration()
                if validation_result.has_errors():
                    self.logger.warning(f"Configuration validation issues: {validation_result.get_summary()}")
                
                # Update cache hash
                self._config_hash = self._calculate_config_hash()
                
                self.logger.info("Configuration loaded successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to load configuration: {e}")
                raise
    
    def _calculate_config_hash(self) -> str:
        """Calculate hash of current configuration for change detection."""
        try:
            if self._current_config:
                # Try to use asdict for dataclass instances
                config_dict = asdict(self._current_config)
            else:
                config_dict = {}
        except (TypeError, AttributeError):
            # Fallback for non-dataclass objects (like mocks in tests)
            if self._current_config:
                if hasattr(self._current_config, 'to_dict'):
                    config_dict = self._current_config.to_dict()
                else:
                    config_dict = {}
            else:
                config_dict = {}
        
        # Ensure all values are JSON serializable
        def make_serializable(obj):
            if hasattr(obj, '__dict__'):
                return str(obj)
            elif callable(obj):
                return str(obj)
            else:
                return obj
        
        try:
            # Clean the config dict to ensure JSON serializability
            clean_dict = {}
            for key, value in config_dict.items():
                clean_dict[key] = make_serializable(value)
            
            config_str = json.dumps(clean_dict, sort_keys=True, default=str)
        except (TypeError, ValueError):
            # Last resort: use string representation
            config_str = str(config_dict)
        
        return hashlib.md5(config_str.encode()).hexdigest()
    
    def _setup_file_watching(self) -> None:
        """Set up file system watching for configuration changes."""
        if not self._watched_files or not WATCHDOG_AVAILABLE:
            if not WATCHDOG_AVAILABLE:
                self.logger.warning("File watching disabled - watchdog package not available")
            return
        
        try:
            self._observer = Observer()
            handler = ConfigurationChangeHandler(self)
            
            # Watch directories containing configuration files
            watched_dirs = set()
            for file_path in self._watched_files:
                dir_path = Path(file_path).parent
                if dir_path not in watched_dirs:
                    self._observer.schedule(handler, str(dir_path), recursive=False)
                    watched_dirs.add(dir_path)
            
            self._observer.start()
            self.logger.info(f"File watching enabled for {len(watched_dirs)} directories")
            
        except Exception as e:
            self.logger.warning(f"Failed to set up file watching: {e}")
    
    def _handle_file_change(self, file_path: str) -> None:
        """Handle configuration file changes."""
        if file_path not in self._watched_files:
            return
        
        try:
            # Small delay to ensure file write is complete
            time.sleep(0.1)
            
            # Reload configuration
            old_config = self._current_config
            self._load_configuration()
            
            # Check if configuration actually changed
            new_hash = self._calculate_config_hash()
            if new_hash != self._config_hash:
                self.logger.info("Configuration changed, reloading...")
                
                # Clear cache
                self._clear_cache()
                
                # Notify callbacks
                if old_config and self._current_config:
                    self._notify_change_callbacks(old_config, self._current_config)
                
                self._config_hash = new_hash
            
        except Exception as e:
            self.logger.error(f"Failed to handle configuration file change: {e}")
    
    def _load_environment_configs(self) -> None:
        """Load environment-specific configuration overrides."""
        env_config_dir = Path('config/environments')
        if not env_config_dir.exists():
            return
        
        try:
            for env_file in env_config_dir.glob('*.yaml'):
                env_name = env_file.stem
                with open(env_file, 'r') as f:
                    env_data = yaml.safe_load(f)
                
                self._environment_configs[env_name] = EnvironmentConfig(
                    name=env_name,
                    overrides=env_data.get('overrides', {}),
                    description=env_data.get('description')
                )
            
            self.logger.info(f"Loaded {len(self._environment_configs)} environment configurations")
            
        except Exception as e:
            self.logger.warning(f"Failed to load environment configurations: {e}")
    
    def get_config(self, section: Optional[str] = None, use_cache: bool = True) -> Union[Config, Any]:
        """
        Get configuration or configuration section.
        
        Args:
            section: Optional section name to retrieve
            use_cache: Whether to use cached values
            
        Returns:
            Configuration object or section value
        """
        with self._lock:
            if not self._current_config:
                raise RuntimeError("Configuration not loaded")
            
            if section is None:
                return self._current_config
            
            # Check cache first
            if use_cache and section in self._config_cache:
                cache_time = self._cache_timestamps.get(section)
                if cache_time and (datetime.now() - cache_time).seconds < self.cache_ttl:
                    return self._config_cache[section]
            
            # Get section value
            try:
                value = getattr(self._current_config, section)
                
                # Cache the value
                if use_cache:
                    self._config_cache[section] = value
                    self._cache_timestamps[section] = datetime.now()
                
                return value
                
            except AttributeError:
                raise ValueError(f"Configuration section '{section}' not found")
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        with self._lock:
            if not self._current_config:
                raise RuntimeError("Configuration not loaded")
            
            try:
                # Try to use asdict for dataclass instances
                return asdict(self._current_config)
            except (TypeError, AttributeError):
                # Fallback for non-dataclass objects (like mocks in tests)
                if hasattr(self._current_config, 'to_dict'):
                    return self._current_config.to_dict()
                else:
                    # Last resort: try to extract attributes
                    return {
                        attr: getattr(self._current_config, attr)
                        for attr in dir(self._current_config)
                        if not attr.startswith('_') and not callable(getattr(self._current_config, attr))
                    }
    
    def validate_configuration(self) -> ConfigurationValidationResult:
        """
        Comprehensive configuration validation.
        
        Returns:
            Validation result with errors, warnings, and missing fields
        """
        errors = []
        warnings = []
        missing_required = []
        
        if not self._current_config:
            return ConfigurationValidationResult(
                is_valid=False,
                errors=["Configuration not loaded"],
                warnings=[],
                missing_required=[]
            )
        
        try:
            # Use existing validation method
            self._current_config.validate()
            
            # Check for missing required configuration
            missing = self._current_config.get_missing_config()
            missing_required.extend(missing)
            
            # Validate API keys
            api_validation = self._current_config.validate_api_keys()
            for key, is_valid in api_validation.items():
                if not is_valid:
                    errors.append(f"Invalid or missing API key: {key}")
            
            # Environment-specific validation
            if self.environment == 'production':
                if not self._current_config.notion_token:
                    errors.append("Notion token is required in production")
                if not self._current_config.hunter_api_key:
                    errors.append("Hunter API key is required in production")
            
            # Check for deprecated settings
            if hasattr(self._current_config, 'enable_interactive_controls') and self._current_config.enable_interactive_controls:
                warnings.append("Interactive controls are deprecated and will be removed")
            
            # Validate file paths
            if self._current_config.sender_profile_path:
                if not os.path.exists(self._current_config.sender_profile_path):
                    warnings.append(f"Sender profile path does not exist: {self._current_config.sender_profile_path}")
            
        except Exception as e:
            errors.append(f"Configuration validation error: {str(e)}")
        
        is_valid = len(errors) == 0 and len(missing_required) == 0
        
        return ConfigurationValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            missing_required=missing_required
        )
    
    def reload_configuration(self) -> bool:
        """
        Hot reload configuration without restart.
        
        Returns:
            True if reload was successful, False otherwise
        """
        try:
            old_config = self._current_config
            self._load_configuration()
            
            # Clear cache after successful reload
            self._clear_cache()
            
            # Notify callbacks
            if old_config and self._current_config:
                self._notify_change_callbacks(old_config, self._current_config)
            
            self.logger.info("Configuration reloaded successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            return False
    
    def _clear_cache(self) -> None:
        """Clear configuration cache."""
        with self._lock:
            self._config_cache.clear()
            self._cache_timestamps.clear()
    
    def add_change_callback(self, callback: Callable[[Config, Config], None]) -> None:
        """
        Add callback for configuration changes.
        
        Args:
            callback: Function to call when configuration changes (old_config, new_config)
        """
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[Config, Config], None]) -> None:
        """Remove configuration change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def _notify_change_callbacks(self, old_config: Config, new_config: Config) -> None:
        """Notify all registered callbacks of configuration changes."""
        for callback in self._change_callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                self.logger.error(f"Error in configuration change callback: {e}")
    
    def get_environment_config(self, environment: str) -> Optional[EnvironmentConfig]:
        """Get environment-specific configuration."""
        return self._environment_configs.get(environment)
    
    def apply_environment_overrides(self, environment: str) -> bool:
        """
        Apply environment-specific configuration overrides.
        
        Args:
            environment: Environment name
            
        Returns:
            True if overrides were applied successfully
        """
        env_config = self.get_environment_config(environment)
        if not env_config:
            self.logger.warning(f"No environment configuration found for: {environment}")
            return False
        
        try:
            # Get current config as dict
            current_dict = self.get_config_dict()
            
            # Apply overrides
            updated_dict = env_config.apply_overrides(current_dict)
            
            # Create new config from updated dict
            old_config = self._current_config
            self._current_config = Config.from_dict(updated_dict)
            
            # Clear cache
            self._clear_cache()
            
            # Notify callbacks
            if old_config:
                self._notify_change_callbacks(old_config, self._current_config)
            
            self.logger.info(f"Applied environment overrides for: {environment}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply environment overrides: {e}")
            return False
    
    def export_configuration(self, 
                           output_path: str, 
                           format: str = 'yaml',
                           include_secrets: bool = False,
                           environment_overrides: Optional[str] = None) -> bool:
        """
        Export configuration to file.
        
        Args:
            output_path: Output file path
            format: Export format ('yaml', 'json')
            include_secrets: Whether to include sensitive values
            environment_overrides: Environment overrides to apply
            
        Returns:
            True if export was successful
        """
        try:
            config_dict = self.get_config_dict()
            
            # Apply environment overrides if specified
            if environment_overrides:
                env_config = self.get_environment_config(environment_overrides)
                if env_config:
                    config_dict = env_config.apply_overrides(config_dict)
            
            # Mask secrets if requested
            if not include_secrets:
                sensitive_keys = [
                    'notion_token', 'hunter_api_key', 'openai_api_key',
                    'azure_openai_api_key', 'resend_api_key'
                ]
                for key in sensitive_keys:
                    if key in config_dict and config_dict[key]:
                        config_dict[key] = '***MASKED***'
            
            # Export to file
            output_file = Path(output_path)
            with open(output_file, 'w') as f:
                if format.lower() == 'yaml':
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                elif format.lower() == 'json':
                    json.dump(config_dict, f, indent=2)
                else:
                    raise ValueError(f"Unsupported export format: {format}")
            
            self.logger.info(f"Configuration exported to: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export configuration: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get configuration cache statistics."""
        with self._lock:
            return {
                'cached_sections': len(self._config_cache),
                'cache_ttl': self.cache_ttl,
                'oldest_cache_entry': min(self._cache_timestamps.values()) if self._cache_timestamps else None,
                'newest_cache_entry': max(self._cache_timestamps.values()) if self._cache_timestamps else None
            }
    
    def shutdown(self) -> None:
        """Shutdown configuration service and cleanup resources."""
        try:
            if self._observer:
                self._observer.stop()
                self._observer.join()
            
            self._clear_cache()
            self._change_callbacks.clear()
            
            self.logger.info("Configuration service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during configuration service shutdown: {e}")


# Global configuration service instance
_config_service: Optional[ConfigurationService] = None
_service_lock = threading.Lock()


def get_configuration_service(config_path: Optional[str] = None,
                            environment: Optional[str] = None,
                            enable_hot_reload: bool = True) -> ConfigurationService:
    """
    Get global configuration service instance (singleton pattern).
    
    Args:
        config_path: Path to configuration file
        environment: Environment name
        enable_hot_reload: Enable hot reloading
        
    Returns:
        ConfigurationService instance
    """
    global _config_service
    
    with _service_lock:
        if _config_service is None:
            _config_service = ConfigurationService(
                config_path=config_path,
                environment=environment,
                enable_hot_reload=enable_hot_reload
            )
        
        return _config_service


def reset_configuration_service() -> None:
    """Reset global configuration service (mainly for testing)."""
    global _config_service
    
    with _service_lock:
        if _config_service:
            _config_service.shutdown()
        _config_service = None
