"""
WebDriver manager for unified WebDriver setup and management across scrapers.
Provides standardized Chrome options, driver pooling, and lifecycle management.
"""

import time
import logging
import threading
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Queue, Empty

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException

from utils.config import Config
from utils.logging_config import get_logger
from utils.error_handling_enhanced import ErrorHandlingService, ErrorCategory


@dataclass
class WebDriverConfig:
    """Configuration for WebDriver instances."""
    headless: bool = True
    window_size: tuple = (1920, 1080)
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    page_load_timeout: int = 20
    implicit_wait: int = 10
    disable_images: bool = False
    disable_javascript: bool = False
    proxy: Optional[str] = None


class WebDriverPool:
    """Pool of WebDriver instances for reuse and better resource management."""
    
    def __init__(self, max_size: int = 3, config: WebDriverConfig = None):
        self.max_size = max_size
        self.config = config or WebDriverConfig()
        self.pool = Queue(maxsize=max_size)
        self.active_drivers = set()
        self.lock = threading.Lock()
        self.logger = get_logger(__name__)
        
    def get_driver(self) -> webdriver.Chrome:
        """Get a WebDriver instance from the pool or create a new one."""
        try:
            # Try to get an existing driver from the pool
            driver = self.pool.get_nowait()
            with self.lock:
                self.active_drivers.add(driver)
            self.logger.debug("Retrieved WebDriver from pool")
            return driver
        except Empty:
            # Create a new driver if pool is empty
            driver = self._create_driver()
            with self.lock:
                self.active_drivers.add(driver)
            self.logger.debug("Created new WebDriver instance")
            return driver
    
    def return_driver(self, driver: webdriver.Chrome) -> None:
        """Return a WebDriver instance to the pool."""
        if not driver:
            return
            
        try:
            with self.lock:
                if driver in self.active_drivers:
                    self.active_drivers.remove(driver)
            
            # Check if driver is still usable
            if self._is_driver_healthy(driver):
                # Clear any existing state
                self._reset_driver_state(driver)
                
                # Return to pool if there's space
                try:
                    self.pool.put_nowait(driver)
                    self.logger.debug("Returned WebDriver to pool")
                except:
                    # Pool is full, quit the driver
                    driver.quit()
                    self.logger.debug("Pool full, quit WebDriver")
            else:
                # Driver is unhealthy, quit it
                driver.quit()
                self.logger.debug("Quit unhealthy WebDriver")
                
        except Exception as e:
            self.logger.warning(f"Error returning driver to pool: {e}")
            try:
                driver.quit()
            except:
                pass
    
    def cleanup(self) -> None:
        """Clean up all drivers in the pool."""
        self.logger.info("Cleaning up WebDriver pool")
        
        # Quit all active drivers
        with self.lock:
            for driver in list(self.active_drivers):
                try:
                    driver.quit()
                except:
                    pass
            self.active_drivers.clear()
        
        # Quit all pooled drivers
        while not self.pool.empty():
            try:
                driver = self.pool.get_nowait()
                driver.quit()
            except:
                pass
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create a new WebDriver instance with standardized configuration."""
        options = self._create_chrome_options()
        
        try:
            driver = webdriver.Chrome(options=options)
            
            # Set timeouts
            driver.set_page_load_timeout(self.config.page_load_timeout)
            driver.implicitly_wait(self.config.implicit_wait)
            
            # Set window size
            driver.set_window_size(*self.config.window_size)
            
            # Execute script to avoid detection
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
            
        except Exception as e:
            raise WebDriverException(f"Failed to create WebDriver: {e}")
    
    def _create_chrome_options(self) -> Options:
        """Create standardized Chrome options."""
        options = Options()
        
        # Basic options
        if self.config.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={self.config.window_size[0]},{self.config.window_size[1]}")
        options.add_argument(f"--user-agent={self.config.user_agent}")
        
        # Anti-detection options
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Performance options
        if self.config.disable_images:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        if self.config.disable_javascript:
            prefs = {"profile.managed_default_content_settings.javascript": 2}
            options.add_experimental_option("prefs", prefs)
        
        # Proxy configuration
        if self.config.proxy:
            options.add_argument(f"--proxy-server={self.config.proxy}")
        
        # Additional stability options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        
        return options
    
    def _is_driver_healthy(self, driver: webdriver.Chrome) -> bool:
        """Check if a WebDriver instance is still healthy and usable."""
        try:
            # Try to get the current URL to test if driver is responsive
            _ = driver.current_url
            return True
        except Exception:
            return False
    
    def _reset_driver_state(self, driver: webdriver.Chrome) -> None:
        """Reset WebDriver state for reuse."""
        try:
            # Clear cookies and local storage
            driver.delete_all_cookies()
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            
            # Navigate to blank page
            driver.get("about:blank")
            
        except Exception as e:
            self.logger.warning(f"Error resetting driver state: {e}")


class WebDriverManager:
    """
    Unified WebDriver manager for all scraping operations.
    Provides standardized Chrome options, driver pooling, and lifecycle management.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config: Config = None):
        """Singleton pattern to ensure only one manager instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Config = None):
        if hasattr(self, '_initialized'):
            return
            
        self.config = config
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandlingService(config) if config else None
        
        # Default WebDriver configuration
        self.webdriver_config = WebDriverConfig()
        if config:
            self._load_config_settings(config)
        
        # Initialize driver pool
        pool_size = getattr(config, 'webdriver_pool_size', 3) if config else 3
        self.driver_pool = WebDriverPool(max_size=pool_size, config=self.webdriver_config)
        
        self._initialized = True
        self.logger.info("WebDriverManager initialized")
    
    def _load_config_settings(self, config: Config) -> None:
        """Load WebDriver settings from configuration."""
        self.webdriver_config.headless = getattr(config, 'webdriver_headless', True)
        self.webdriver_config.page_load_timeout = getattr(config, 'webdriver_page_load_timeout', 20)
        self.webdriver_config.implicit_wait = getattr(config, 'webdriver_implicit_wait', 10)
        self.webdriver_config.disable_images = getattr(config, 'webdriver_disable_images', False)
        self.webdriver_config.disable_javascript = getattr(config, 'webdriver_disable_javascript', False)
        self.webdriver_config.proxy = getattr(config, 'webdriver_proxy', None)
        
        # Window size configuration
        window_width = getattr(config, 'webdriver_window_width', 1920)
        window_height = getattr(config, 'webdriver_window_height', 1080)
        self.webdriver_config.window_size = (window_width, window_height)
        
        # User agent configuration
        user_agent = getattr(config, 'webdriver_user_agent', None)
        if user_agent:
            self.webdriver_config.user_agent = user_agent
    
    @contextmanager
    def get_driver(self, service_name: str = "default"):
        """
        Context manager to get a WebDriver instance with automatic cleanup.
        
        Args:
            service_name: Name of the service requesting the driver (for logging)
            
        Yields:
            webdriver.Chrome: Configured Chrome WebDriver instance
        """
        driver = None
        start_time = time.time()
        
        try:
            self.logger.info(f"Acquiring WebDriver for service: {service_name}")
            driver = self.driver_pool.get_driver()
            
            # Log acquisition time
            acquisition_time = time.time() - start_time
            self.logger.debug(f"WebDriver acquired in {acquisition_time:.2f}s for {service_name}")
            
            yield driver
            
        except Exception as e:
            self.logger.error(f"Error with WebDriver for {service_name}: {e}")
            if self.error_handler:
                self.error_handler.handle_error(
                    e, 
                    service=service_name,
                    operation='webdriver_usage',
                    context={'service': service_name, 'operation': 'webdriver_usage'}
                )
            raise
            
        finally:
            if driver:
                try:
                    self.driver_pool.return_driver(driver)
                    total_time = time.time() - start_time
                    self.logger.debug(f"WebDriver session completed in {total_time:.2f}s for {service_name}")
                except Exception as e:
                    self.logger.warning(f"Error returning WebDriver for {service_name}: {e}")
    
    def create_driver(self, custom_config: Optional[WebDriverConfig] = None) -> webdriver.Chrome:
        """
        Create a new WebDriver instance with custom configuration.
        Note: This bypasses the pool and should be used sparingly.
        
        Args:
            custom_config: Custom WebDriver configuration
            
        Returns:
            webdriver.Chrome: New Chrome WebDriver instance
        """
        config = custom_config or self.webdriver_config
        temp_pool = WebDriverPool(max_size=1, config=config)
        return temp_pool._create_driver()
    
    def setup_chrome_options(self, custom_options: Optional[Dict[str, Any]] = None) -> Options:
        """
        Create standardized Chrome options with optional customizations.
        
        Args:
            custom_options: Dictionary of custom options to add/override
            
        Returns:
            Options: Configured Chrome options
        """
        temp_pool = WebDriverPool(max_size=1, config=self.webdriver_config)
        options = temp_pool._create_chrome_options()
        
        # Apply custom options if provided
        if custom_options:
            for key, value in custom_options.items():
                if key == 'arguments':
                    for arg in value:
                        options.add_argument(arg)
                elif key == 'experimental_options':
                    for exp_key, exp_value in value.items():
                        options.add_experimental_option(exp_key, exp_value)
                elif key == 'prefs':
                    options.add_experimental_option("prefs", value)
        
        return options
    
    def get_pool_stats(self) -> Dict[str, int]:
        """
        Get statistics about the WebDriver pool.
        
        Returns:
            Dict containing pool statistics
        """
        with self.driver_pool.lock:
            return {
                'pool_size': self.driver_pool.pool.qsize(),
                'active_drivers': len(self.driver_pool.active_drivers),
                'max_pool_size': self.driver_pool.max_size
            }
    
    def cleanup(self) -> None:
        """Clean up all WebDriver resources."""
        self.logger.info("Cleaning up WebDriverManager")
        self.driver_pool.cleanup()
    
    def __del__(self):
        """Destructor to ensure cleanup on garbage collection."""
        try:
            self.cleanup()
        except:
            pass


# Global instance for easy access
_webdriver_manager = None
_manager_lock = threading.Lock()


def get_webdriver_manager(config: Config = None) -> WebDriverManager:
    """
    Get the global WebDriverManager instance.
    
    Args:
        config: Configuration object (only used for first initialization)
        
    Returns:
        WebDriverManager: Global WebDriverManager instance
    """
    global _webdriver_manager
    
    if _webdriver_manager is None:
        with _manager_lock:
            if _webdriver_manager is None:
                _webdriver_manager = WebDriverManager(config)
    
    return _webdriver_manager