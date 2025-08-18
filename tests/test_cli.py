"""
Integration tests for the CLI interface.
"""

import pytest
import tempfile
import os
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from cli import cli, CLIConfig
from utils.config import Config
from models.data_models import CompanyData, Prospect, ProspectStatus
from services.email_generator import EmailTemplate


class TestCLIConfig:
    """Test CLI configuration management."""
    
    def test_cli_config_from_env(self):
        """Test CLI config creation from environment variables."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }):
            cli_config = CLIConfig()
            assert cli_config.base_config.notion_token == 'test_notion_token'
            assert cli_config.base_config.hunter_api_key == 'test_hunter_key'
            assert cli_config.base_config.openai_api_key == 'test_openai_key'
    
    def test_cli_config_from_yaml_file(self):
        """Test CLI config creation from YAML file."""
        config_data = {
            'NOTION_TOKEN': 'yaml_notion_token',
            'HUNTER_API_KEY': 'yaml_hunter_key',
            'OPENAI_API_KEY': 'yaml_openai_key',
            'SCRAPING_DELAY': '3.0',
            'MAX_PRODUCTS_PER_RUN': '25'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            cli_config = CLIConfig(config_file=config_file)
            assert cli_config.base_config.notion_token == 'yaml_notion_token'
            assert cli_config.base_config.scraping_delay == 3.0
            assert cli_config.base_config.max_products_per_run == 25
        finally:
            os.unlink(config_file)
    
    def test_cli_config_from_json_file(self):
        """Test CLI config creation from JSON file."""
        config_data = {
            'NOTION_TOKEN': 'json_notion_token',
            'HUNTER_API_KEY': 'json_hunter_key',
            'OPENAI_API_KEY': 'json_openai_key',
            'EMAIL_TEMPLATE_TYPE': 'casual'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            cli_config = CLIConfig(config_file=config_file)
            assert cli_config.base_config.notion_token == 'json_notion_token'
            assert cli_config.base_config.email_template_type == 'casual'
        finally:
            os.unlink(config_file)
    
    def test_cli_config_dry_run_mode(self):
        """Test CLI config with dry-run mode."""
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_key'
        }):
            cli_config = CLIConfig(dry_run=True)
            assert cli_config.dry_run is True


class TestCLICommands:
    """Test CLI command functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.mock_env = {
            'NOTION_TOKEN': 'test_notion_token',
            'HUNTER_API_KEY': 'test_hunter_key',
            'OPENAI_API_KEY': 'test_openai_key'
        }
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Job Prospect Automation CLI' in result.output
        assert 'discover' in result.output
        assert 'process-company' in result.output
        assert 'generate-emails' in result.output
    
    def test_discover_command_dry_run(self):
        """Test discover command in dry-run mode."""
        result = self.runner.invoke(cli, ['--dry-run', 'discover', '--limit', '10'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
        assert 'Would discover companies' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_discover_command_success(self, mock_controller_class):
        """Test successful discover command execution."""
        # Mock controller and its methods
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.run_discovery_pipeline.return_value = {
            'summary': {
                'companies_processed': 5,
                'prospects_found': 15,
                'emails_found': 12,
                'linkedin_profiles_extracted': 10,
                'success_rate': 80.0,
                'duration_seconds': 45.5
            }
        }
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, ['discover', '--limit', '10'])
            
        assert result.exit_code == 0
        mock_controller.run_discovery_pipeline.assert_called_once_with(limit=10)
        assert 'Companies Processed' in result.output
        assert '5' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_discover_command_error(self, mock_controller_class):
        """Test discover command with error."""
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.run_discovery_pipeline.side_effect = Exception("Test error")
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, ['discover'])
            
        assert result.exit_code == 1
        assert 'Error during discovery' in result.output
    
    def test_process_company_dry_run(self):
        """Test process-company command in dry-run mode."""
        result = self.runner.invoke(cli, [
            '--dry-run', 'process-company', 'Test Company', '--domain', 'test.com'
        ])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
        assert 'Test Company' in result.output
        assert 'test.com' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_process_company_success(self, mock_controller_class):
        """Test successful process-company command."""
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        
        # Create mock prospects
        mock_prospects = [
            Prospect(
                id="1",
                name="John Doe",
                role="CEO",
                company="Test Company",
                linkedin_url="https://linkedin.com/in/johndoe",
                email="john@test.com",
                status=ProspectStatus.NOT_CONTACTED,
                notes="",
                created_at=None
            )
        ]
        mock_controller.process_company.return_value = mock_prospects
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, ['process-company', 'Test Company'])
            
        assert result.exit_code == 0
        assert 'John Doe' in result.output
        assert 'CEO' in result.output
    
    def test_generate_emails_dry_run(self):
        """Test generate-emails command in dry-run mode."""
        result = self.runner.invoke(cli, [
            '--dry-run', 'generate-emails', 
            '--prospect-ids', '1,2,3',
            '--template', 'cold_outreach'
        ])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
        assert 'cold_outreach emails for 3 prospects' in result.output
    
    def test_generate_emails_missing_ids(self):
        """Test generate-emails command without prospect IDs."""
        result = self.runner.invoke(cli, ['generate-emails'])
        assert result.exit_code == 1
        assert '--prospect-ids is required' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_generate_emails_success(self, mock_controller_class):
        """Test successful generate-emails command."""
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.generate_outreach_emails.return_value = {
            'emails': [
                {
                    'subject': 'Test Subject',
                    'body': 'Test email body content for testing purposes.',
                    'prospect_id': '1'
                }
            ],
            'summary': {
                'generated': 1,
                'failed': 0
            }
        }
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, [
                'generate-emails', 
                '--prospect-ids', '1',
                '--template', 'cold_outreach'
            ])
            
        assert result.exit_code == 0
        assert 'Generated 1 emails' in result.output
        assert 'Test Subject' in result.output
    
    def test_status_dry_run(self):
        """Test status command in dry-run mode."""
        result = self.runner.invoke(cli, ['--dry-run', 'status'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_status_success(self, mock_controller_class):
        """Test successful status command."""
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.get_workflow_status.return_value = {
            'notion_connection': {'status': 'Connected', 'details': 'Database accessible'},
            'hunter_api': {'status': 'Active', 'details': '95 requests remaining'},
            'openai_api': {'status': 'Active', 'details': 'Service operational'}
        }
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, ['status'])
            
        assert result.exit_code == 0
        assert 'Workflow Status' in result.output
        assert 'Connected' in result.output
    
    def test_batch_history_dry_run(self):
        """Test batch-history command in dry-run mode."""
        result = self.runner.invoke(cli, ['--dry-run', 'batch-history'])
        assert result.exit_code == 0
        assert 'DRY-RUN' in result.output
    
    @patch('cli.ProspectAutomationController')
    def test_batch_history_success(self, mock_controller_class):
        """Test successful batch-history command."""
        mock_controller = Mock()
        mock_controller_class.return_value = mock_controller
        mock_controller.list_batch_history.return_value = [
            {
                'batch_id': 'batch_123',
                'status': 'completed',
                'total_companies': 10,
                'processed_companies': 10,
                'total_prospects': 25,
                'start_time': '2024-01-01 10:00:00'
            }
        ]
        
        with patch.dict(os.environ, self.mock_env):
            result = self.runner.invoke(cli, ['batch-history'])
            
        assert result.exit_code == 0
        assert 'Batch Processing History' in result.output
        assert 'batch_123' in result.output
    
    def test_init_config_yaml(self):
        """Test init-config command for YAML file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, 'test_config.yaml')
            result = self.runner.invoke(cli, ['init-config', config_file])
            
            assert result.exit_code == 0
            assert 'Configuration template created' in result.output
            assert os.path.exists(config_file)
            
            # Verify file content
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
                assert 'NOTION_TOKEN' in config_data
                assert 'HUNTER_API_KEY' in config_data
                assert 'OPENAI_API_KEY' in config_data
    
    def test_init_config_default_name(self):
        """Test init-config command with default filename."""
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                result = self.runner.invoke(cli, ['init-config'])
                assert result.exit_code == 0
                assert os.path.exists('config.yaml')
            finally:
                os.chdir(original_cwd)
    
    def test_verbose_flag(self):
        """Test verbose flag functionality."""
        result = self.runner.invoke(cli, ['--verbose', '--dry-run', 'status'])
        assert result.exit_code == 0
        # Verbose flag should be processed without errors
    
    def test_config_file_flag(self):
        """Test config file flag functionality."""
        config_data = {
            'NOTION_TOKEN': 'file_notion_token',
            'HUNTER_API_KEY': 'file_hunter_key',
            'OPENAI_API_KEY': 'file_openai_key'
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            result = self.runner.invoke(cli, [
                '--config', config_file, 
                '--dry-run', 
                'discover'
            ])
            assert result.exit_code == 0
        finally:
            os.unlink(config_file)


class TestCLIIntegration:
    """Integration tests for CLI with real components."""
    
    def test_cli_config_validation(self):
        """Test CLI configuration validation."""
        # Test with invalid configuration
        with patch.dict(os.environ, {
            'NOTION_TOKEN': 'test_token',
            'HUNTER_API_KEY': 'test_key',
            'OPENAI_API_KEY': 'test_key',
            'SCRAPING_DELAY': '-1.0'  # Invalid value
        }):
            with pytest.raises(ValueError, match="Scraping delay must be non-negative"):
                cli_config = CLIConfig()
                cli_config.base_config.validate()
    
    def test_cli_error_handling(self):
        """Test CLI error handling for various scenarios."""
        runner = CliRunner()
        
        # Test with missing environment variables
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(cli, ['discover'])
            assert result.exit_code == 1
            assert 'Configuration error' in result.output
    
    def test_cli_output_formatting(self):
        """Test CLI output formatting and display functions."""
        from cli import _display_results, _display_prospects, _display_status
        
        # Test results display
        results = {
            'summary': {
                'companies_processed': 5,
                'prospects_found': 15,
                'emails_found': 12,
                'linkedin_profiles_extracted': 10,
                'success_rate': 80.0,
                'duration_seconds': 45.5
            }
        }
        
        # These should not raise exceptions
        _display_results(results)
        
        # Test prospects display
        prospects = [
            Prospect(
                id="1",
                name="John Doe",
                role="CEO",
                company="Test Company",
                linkedin_url="https://linkedin.com/in/johndoe",
                email="john@test.com",
                status=ProspectStatus.NOT_CONTACTED,
                notes="",
                created_at=None
            )
        ]
        _display_prospects(prospects)
        
        # Test status display
        status_info = {
            'notion_connection': {'status': 'Connected', 'details': 'OK'},
            'hunter_api': {'status': 'Active', 'details': 'OK'}
        }
        _display_status(status_info)


if __name__ == '__main__':
    pytest.main([__file__])