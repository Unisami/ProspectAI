"""
Unit tests for WebDriverManager and related classes.
"""

import pytest
from tests.test_utilities import TestUtilities
import threading
import time
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from queue import Queue

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

from utils.webdriver_manager import (
    WebDriverManager, 
    WebDriverPool, 
    WebDriverConfig,
    get_webdriver_manager
)
from utils.config import Config


class TestWebDriverConfig:
    """Test WebDriverConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = WebDriverConfig()
        
        assert config.headless is True
        assert config.window_size == (1920, 1080)
        assert "Mozilla/5.0" in config.user_agent
        assert config.page_load_timeout == 20
        assert config.implicit_wait == 10
        assert config.disable_images is False
        assert config.disable_javascript is False
        assert config.proxy is None
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = WebDriverConfig(
            headless=False,
            window_size=(1366, 768),
            user_agent="Custom Agent",
            page_load_timeout=30,
            implicit_wait=5,
            disable_images=True,
            disable_javascript=True,
            proxy="http://proxy:8080"
        )
        
        assert config.headless is False
        assert config.window_size == (1366, 768)
        assert config.user_agent == "Custom Agent"
        assert config.page_load_timeout == 30
        assert config.implicit_wait == 5
        assert config.disable_images is True
        assert config.disable_javascript is True
        assert config.proxy == "http://proxy:8080"


class TestWebDriverPool:
    """Test WebDriverPool class."""
    
    @pytest.fixture
    def mock_driver(self):
        """Create a mock WebDriver instance."""
        driver = Mock()
        driver.current_url = "about:blank"
        driver.quit = Mock()
        driver.delete_all_cookies = Mock()
        driver.execute_script = Mock()
        driver.get = Mock()
        driver.set_page_load_timeout = Mock()
        driver.implicitly_wait = Mock()
        driver.set_window_size = Mock()
        return driver
    
    @pytest.fixture
    def webdriver_config(self):
        """Create a test WebDriver configuration."""
        return WebDriverConfig(
            headless=True,
            window_size=(1024, 768),
            page_load_timeout=15,
            implicit_wait=5
        )
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_pool_initialization(self, mock_chrome, webdriver_config):
        """Test WebDriverPool initialization."""
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        
        assert pool.max_size == 2
        assert pool.config == webdriver_config
        assert pool.pool.maxsize == 2
        assert len(pool.active_drivers) == 0
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_get_driver_creates_new(self, mock_chrome, mock_driver, webdriver_config):
        """Test getting driver creates new instance when pool is empty."""
        mock_chrome.return_value = mock_driver
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        
        driver = pool.get_driver()
        
        assert driver == mock_driver
        assert driver in pool.active_drivers
        mock_chrome.assert_called_once()
        mock_driver.set_page_load_timeout.assert_called_with(15)
        mock_driver.implicitly_wait.assert_called_with(5)
        mock_driver.set_window_size.assert_called_with(1024, 768)
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_return_driver_to_pool(self, mock_chrome, mock_driver, webdriver_config):
        """Test returning driver to pool."""
        mock_chrome.return_value = mock_driver
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        
        # Get and return driver
        driver = pool.get_driver()
        pool.return_driver(driver)
        
        # Driver should be removed from active set
        assert driver not in pool.active_drivers
        # Driver should be in pool (queue size should be 1)
        assert pool.pool.qsize() == 1
        # Driver state should be reset
        mock_driver.delete_all_cookies.assert_called_once()
        mock_driver.execute_script.assert_called()
        mock_driver.get.assert_called_with("about:blank")
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_return_unhealthy_driver(self, mock_chrome, mock_driver, webdriver_config):
        """Test returning unhealthy driver quits it."""
        mock_chrome.return_value = mock_driver
        # Make driver unhealthy by raising exception on current_url access
        type(mock_driver).current_url = PropertyMock(side_effect=WebDriverException("Driver crashed"))
        
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        driver = pool.get_driver()
        pool.return_driver(driver)
        
        # Unhealthy driver should be quit
        mock_driver.quit.assert_called()
        # Pool should be empty
        assert pool.pool.qsize() == 0
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_pool_reuse(self, mock_chrome, webdriver_config):
        """Test driver reuse from pool."""
        mock_driver1 = Mock()
        mock_driver1.current_url = "about:blank"
        mock_driver1.delete_all_cookies = Mock()
        mock_driver1.execute_script = Mock()
        mock_driver1.get = Mock()
        
        mock_chrome.return_value = mock_driver1
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        
        # Get and return driver
        driver1 = pool.get_driver()
        pool.return_driver(driver1)
        
        # Get driver again - should reuse the same instance
        driver2 = pool.get_driver()
        
        assert driver1 == driver2
        # Chrome should only be called once (for initial creation)
        assert mock_chrome.call_count == 1
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_cleanup(self, mock_chrome, webdriver_config):
        """Test pool cleanup."""
        mock_driver1 = Mock()
        mock_driver2 = Mock()
        mock_chrome.side_effect = [mock_driver1, mock_driver2]
        
        pool = WebDriverPool(max_size=2, config=webdriver_config)
        
        # Get two drivers
        driver1 = pool.get_driver()
        driver2 = pool.get_driver()
        
        # Return one to pool
        pool.return_driver(driver1)
        
        # Cleanup
        pool.cleanup()
        
        # Both drivers should be quit
        mock_driver1.quit.assert_called()
        mock_driver2.quit.assert_called()
        # Active drivers should be empty
        assert len(pool.active_drivers) == 0
        # Pool should be empty
        assert pool.pool.qsize() == 0
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_create_chrome_options(self, mock_chrome, webdriver_config):
        """Test Chrome options creation."""
        pool = WebDriverPool(max_size=1, config=webdriver_config)
        options = pool._create_chrome_options()
        
        assert isinstance(options, Options)
        # Verify some key arguments are set
        arguments = [arg for arg in options.arguments]
        assert "--headless" in arguments
        assert "--no-sandbox" in arguments
        assert "--disable-dev-shm-usage" in arguments
        assert "--window-size=1024,768" in arguments
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_create_chrome_options_with_proxy(self, mock_chrome):
        """Test Chrome options with proxy configuration."""
        config = WebDriverConfig(proxy="http://proxy:8080")
        pool = WebDriverPool(max_size=1, config=config)
        options = pool._create_chrome_options()
        
        arguments = [arg for arg in options.arguments]
        assert "--proxy-server=http://proxy:8080" in arguments
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_create_chrome_options_disable_images(self, mock_chrome):
        """Test Chrome options with images disabled."""
        config = WebDriverConfig(disable_images=True)
        pool = WebDriverPool(max_size=1, config=config)
        options = pool._create_chrome_options()
        
        # Check that prefs were set for disabling images
        assert hasattr(options, '_experimental_options')


class TestWebDriverManager:
    """Test WebDriverManager class."""
    
    # Using shared mock_config fixture from conftest.py
    def test_singleton_pattern(self, mock_config):
        """Test that WebDriverManager follows singleton pattern."""
        manager1 = WebDriverManager(mock_config)
        manager2 = WebDriverManager(mock_config)
        
        assert manager1 is manager2
    
    def test_initialization_with_config(self, mock_config):
        """Test WebDriverManager initialization with configuration."""
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        
        assert manager.config == mock_config
        assert manager.webdriver_config.headless is True
        assert manager.webdriver_config.page_load_timeout == 25
        assert manager.webdriver_config.implicit_wait == 8
        assert manager.webdriver_config.window_size == (1366, 768)
        assert manager.driver_pool.max_size == 2
    
    def test_initialization_without_config(self):
        """Test WebDriverManager initialization without configuration."""
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager()
        
        assert manager.config is None
        assert manager.error_handler is None
        assert manager.webdriver_config.headless is True  # Default value
        assert manager.driver_pool.max_size == 3  # Default value
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_get_driver_context_manager(self, mock_chrome, mock_config):
        """Test get_driver context manager."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        
        with manager.get_driver("test_service") as driver:
            assert driver == mock_driver
        
        # Driver should be returned to pool after context exit
        # (We can't easily test this without accessing private members)
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_get_driver_context_manager_with_exception(self, mock_chrome, mock_config):
        """Test get_driver context manager handles exceptions."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        
        with pytest.raises(ValueError):
            with manager.get_driver("test_service") as driver:
                raise ValueError("Test exception")
        
        # Driver should still be returned to pool even after exception
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_create_driver(self, mock_chrome, mock_config):
        """Test create_driver method."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        driver = manager.create_driver()
        
        assert driver == mock_driver
        mock_chrome.assert_called_once()
    
    def test_setup_chrome_options(self, mock_config):
        """Test setup_chrome_options method."""
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        options = manager.setup_chrome_options()
        
        assert isinstance(options, Options)
        arguments = [arg for arg in options.arguments]
        assert "--headless" in arguments
    
    def test_setup_chrome_options_with_custom(self, mock_config):
        """Test setup_chrome_options with custom options."""
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        custom_options = {
            'arguments': ['--custom-arg'],
            'experimental_options': {'custom_key': 'custom_value'},
            'prefs': {'custom_pref': True}
        }
        
        options = manager.setup_chrome_options(custom_options)
        
        assert isinstance(options, Options)
        arguments = [arg for arg in options.arguments]
        assert "--custom-arg" in arguments
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_get_pool_stats(self, mock_chrome, mock_config):
        """Test get_pool_stats method."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        
        # Get initial stats
        stats = manager.get_pool_stats()
        assert stats['pool_size'] == 0
        assert stats['active_drivers'] == 0
        assert stats['max_pool_size'] == 2
        
        # Get a driver and check stats
        with manager.get_driver("test") as driver:
            stats = manager.get_pool_stats()
            assert stats['active_drivers'] == 1
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_cleanup(self, mock_chrome, mock_config):
        """Test cleanup method."""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton for this test
        WebDriverManager._instance = None
        
        manager = WebDriverManager(mock_config)
        
        # Get a driver to populate the pool
        with manager.get_driver("test") as driver:
            pass
        
        # Cleanup
        manager.cleanup()
        
        # Pool should be cleaned up
        stats = manager.get_pool_stats()
        assert stats['pool_size'] == 0
        assert stats['active_drivers'] == 0


class TestGlobalWebDriverManager:
    """Test global WebDriverManager functions."""
    
    def test_get_webdriver_manager_singleton(self):
        """Test get_webdriver_manager returns singleton."""
        # Reset global instance
        import utils.webdriver_manager
        utils.webdriver_manager._webdriver_manager = None
        
        config = Mock(spec=Config)
        manager1 = get_webdriver_manager(config)
        manager2 = get_webdriver_manager()
        
        assert manager1 is manager2
        # Note: Due to singleton pattern, config is only set on first initialization
        assert manager1.config is not None
    
    def test_get_webdriver_manager_thread_safety(self):
        """Test get_webdriver_manager is thread-safe."""
        # Reset global instance
        import utils.webdriver_manager
        utils.webdriver_manager._webdriver_manager = None
        
        managers = []
        
        def create_manager():
            manager = get_webdriver_manager()
            managers.append(manager)
        
        # Create multiple threads
        threads = [threading.Thread(target=create_manager) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All managers should be the same instance
        assert len(set(id(manager) for manager in managers)) == 1


class TestWebDriverManagerIntegration:
    """Integration tests for WebDriverManager."""
    
    @pytest.fixture
    def integration_config(self):
        """Create configuration for integration tests."""
        config = Mock(spec=Config)
        config.webdriver_headless = True
        config.webdriver_pool_size = 1
        config.webdriver_page_load_timeout = 10
        config.webdriver_implicit_wait = 5
        config.webdriver_window_width = 800
        config.webdriver_window_height = 600
        config.webdriver_disable_images = True
        config.webdriver_disable_javascript = False
        config.webdriver_proxy = None
        config.webdriver_user_agent = "Test Agent"
        return config
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_full_workflow(self, mock_chrome, integration_config):
        """Test complete workflow with WebDriverManager."""
        mock_driver = Mock()
        mock_driver.current_url = "about:blank"
        mock_driver.delete_all_cookies = Mock()
        mock_driver.execute_script = Mock()
        mock_driver.get = Mock()
        mock_driver.quit = Mock()
        mock_chrome.return_value = mock_driver
        
        # Reset singleton
        WebDriverManager._instance = None
        
        manager = WebDriverManager(integration_config)
        
        # Test getting and using driver
        with manager.get_driver("integration_test") as driver:
            assert driver == mock_driver
            # Simulate some operations
            driver.get("https://example.com")
        
        # Test pool stats
        stats = manager.get_pool_stats()
        assert stats['max_pool_size'] == 1
        
        # Test cleanup
        manager.cleanup()
        mock_driver.quit.assert_called()
    
    @patch('utils.webdriver_manager.webdriver.Chrome')
    def test_concurrent_access(self, mock_chrome, integration_config):
        """Test concurrent access to WebDriverManager."""
        def create_mock_driver(*args, **kwargs):
            mock_driver = Mock()
            mock_driver.current_url = "about:blank"
            mock_driver.delete_all_cookies = Mock()
            mock_driver.execute_script = Mock()
            mock_driver.get = Mock()
            mock_driver.quit = Mock()
            mock_driver.set_page_load_timeout = Mock()
            mock_driver.implicitly_wait = Mock()
            mock_driver.set_window_size = Mock()
            return mock_driver
        
        mock_chrome.side_effect = create_mock_driver
        
        # Reset singleton
        WebDriverManager._instance = None
        
        manager = WebDriverManager(integration_config)
        results = []
        
        def use_driver(service_name):
            try:
                with manager.get_driver(service_name) as driver:
                    time.sleep(0.1)  # Simulate work
                    results.append(f"{service_name}_success")
            except Exception as e:
                results.append(f"{service_name}_error: {e}")
        
        # Create multiple threads
        threads = [
            threading.Thread(target=use_driver, args=(f"service_{i}",))
            for i in range(3)
        ]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All operations should succeed
        assert len(results) == 3
        assert all("success" in result for result in results)
        
        # Cleanup
        manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__])