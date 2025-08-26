#!/usr/bin/env python3
"""
Test for the GUI Runner application.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestGUIRunner(unittest.TestCase):
    """Test cases for the GUI Runner application."""
    
    def setUp(self):
        """Set up test fixtures."""
        pass
        
    def tearDown(self):
        """Tear down test fixtures."""
        pass
        
    @patch('tkinter.Tk')
    def test_gui_imports(self, mock_tk):
        """Test that the GUI can be imported without errors."""
        try:
            from gui_runner import GUIRunner, CommandConfiguration, DiscoverConfig, RunCampaignConfig
            self.assertTrue(True, "GUIRunner imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import GUIRunner: {e}")
            
    def test_data_models(self):
        """Test that data models work correctly."""
        try:
            from gui_runner import CommandConfiguration, DiscoverConfig, RunCampaignConfig
            
            # Test base configuration
            base_config = CommandConfiguration()
            self.assertFalse(base_config.dry_run)
            self.assertIsNone(base_config.config_file)
            self.assertIsNone(base_config.env_file)
            self.assertIsNone(base_config.sender_profile)
            
            # Test discover configuration
            discover_config = DiscoverConfig()
            self.assertEqual(discover_config.limit, 10)
            self.assertEqual(discover_config.batch_size, 5)
            self.assertEqual(discover_config.campaign_name, "")
            
            # Test run campaign configuration
            campaign_config = RunCampaignConfig()
            self.assertEqual(campaign_config.limit, 10)
            self.assertEqual(campaign_config.campaign_name, "")
            self.assertTrue(campaign_config.generate_emails)
            self.assertFalse(campaign_config.send_emails)
            self.assertFalse(campaign_config.auto_setup)
            
        except Exception as e:
            self.fail(f"Failed to test data models: {e}")
            
    def test_gui_files_exist(self):
        """Test that all GUI-related files exist."""
        expected_files = [
            'gui_runner.py',
            'run_gui.py',
            'run_gui.bat',
            'run_gui.sh'
        ]
        
        for filename in expected_files:
            file_path = Path(project_root) / filename
            self.assertTrue(file_path.exists(), f"File {filename} should exist")
            
    def test_readme_updated(self):
        """Test that README.md contains GUI information."""
        readme_path = Path(project_root) / 'README.md'
        self.assertTrue(readme_path.exists(), "README.md should exist")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('Graphical User Interface (GUI)', content, "README should mention GUI")
        self.assertIn('run_gui.py', content, "README should mention run_gui.py")
        
    def test_quickstart_updated(self):
        """Test that QUICKSTART.md contains GUI information."""
        quickstart_path = Path(project_root) / 'QUICKSTART.md'
        self.assertTrue(quickstart_path.exists(), "QUICKSTART.md should exist")
        
        with open(quickstart_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn('GUI Application', content, "QUICKSTART should mention GUI")
        self.assertIn('run_gui.py', content, "QUICKSTART should mention run_gui.py")

if __name__ == '__main__':
    unittest.main()