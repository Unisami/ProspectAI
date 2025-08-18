#!/usr/bin/env python3
"""
Integration tests for CLI profile management commands.
"""

import os
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cli import cli
from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile


@pytest.fixture
def runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_profile():
    """Create a mock sender profile for testing."""
    return SenderProfile(
        name="Test User",
        current_role="Software Engineer",
        years_experience=5,
        key_skills=["Python", "JavaScript", "AWS"],
        experience_summary="Experienced software engineer with a focus on backend development.",
        education=["BS Computer Science"],
        certifications=["AWS Certified Developer"],
        value_proposition="I build scalable backend systems with a focus on clean code.",
        target_roles=["Backend Engineer", "DevOps Engineer"],
        industries_of_interest=["Tech", "Finance"],
        notable_achievements=["Led team of 5 engineers", "Reduced system latency by 30%"],
        portfolio_links=["https://github.com/testuser", "https://linkedin.com/in/testuser"],
        preferred_contact_method="email",
        availability="Available immediately",
        location="San Francisco, CA",
        remote_preference="remote"
    )


@pytest.fixture
def temp_profile_dir(tmp_path):
    """Create a temporary directory for profile files."""
    profile_dir = tmp_path / "profiles"
    profile_dir.mkdir()
    return profile_dir


def test_profile_setup_template(runner):
    """Test profile-setup command with template option."""
    with runner.isolated_filesystem():
        with patch.object(SenderProfileManager, 'create_profile_template') as mock_create:
            mock_create.return_value = "# Test Template"
            
            result = runner.invoke(cli, ['profile-setup', '--template', '--output', 'test_profile.md'])
            
            assert result.exit_code == 0
            assert "Template saved to:" in result.output
            mock_create.assert_called_once_with('markdown')
            
            # Check file was created
            assert Path('test_profile.md').exists()


def test_profile_setup_interactive(runner, mock_profile):
    """Test profile-setup command with interactive option."""
    with runner.isolated_filesystem():
        with patch.object(SenderProfileManager, 'create_profile_interactively') as mock_create:
            mock_create.return_value = mock_profile
            
            with patch.object(SenderProfileManager, 'save_profile_to_markdown') as mock_save:
                result = runner.invoke(cli, ['profile-setup', '--interactive', '--output', 'test_profile.md'])
                
                assert result.exit_code == 0
                assert "Profile created successfully" in result.output
                mock_create.assert_called_once()
                mock_save.assert_called_once()


def test_profile_setup_set_default(runner, mock_profile):
    """Test profile-setup command with set-default option."""
    with runner.isolated_filesystem():
        with patch.object(SenderProfileManager, 'create_profile_interactively') as mock_create:
            mock_create.return_value = mock_profile
            
            with patch.object(SenderProfileManager, 'save_profile_to_markdown') as mock_save:
                with patch('builtins.open', MagicMock()):
                    with patch('json.dump') as mock_json_dump:
                        result = runner.invoke(cli, ['profile-setup', '--interactive', '--output', 'test_profile.md', '--set-default'])
                        
                        assert result.exit_code == 0
                        assert "Set" in result.output
                        assert "as default sender profile" in result.output
                        mock_create.assert_called_once()
                        mock_save.assert_called_once()
                        mock_json_dump.assert_called_once()


def test_generate_emails_with_default_profile(runner):
    """Test generate_emails command with use-default-profile option."""
    with runner.isolated_filesystem():
        # Create mock config file
        config_dir = Path.home() / '.job_prospect_automation'
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / 'config.json'
        
        with open(config_file, 'w') as f:
            json.dump({
                'default_sender_profile': str(Path.cwd() / 'test_profile.md'),
                'default_sender_profile_format': 'markdown'
            }, f)
        
        # Create mock profile file
        with open('test_profile.md', 'w') as f:
            f.write("# Test Profile")
        
        with patch('controllers.prospect_automation_controller.ProspectAutomationController') as mock_controller_class:
            mock_controller = MagicMock()
            mock_controller_class.return_value = mock_controller
            
            result = runner.invoke(cli, ['generate-emails', '--prospect-ids', '123', '--use-default-profile'])
            
            assert result.exit_code == 0
            assert "Using default sender profile" in result.output
            mock_controller.set_sender_profile.assert_called_once()


def test_generate_emails_with_profile_format(runner):
    """Test generate_emails command with profile-format option."""
    with runner.isolated_filesystem():
        # Create mock profile file
        with open('test_profile.json', 'w') as f:
            json.dump({
                'name': 'Test User',
                'current_role': 'Developer',
                'years_experience': 5,
                'key_skills': ['Python'],
                'experience_summary': 'Test',
                'value_proposition': 'Test'
            }, f)
        
        with patch('controllers.prospect_automation_controller.ProspectAutomationController') as mock_controller_class:
            mock_controller = MagicMock()
            mock_controller_class.return_value = mock_controller
            
            result = runner.invoke(cli, [
                'generate-emails', 
                '--prospect-ids', '123', 
                '--sender-profile', 'test_profile.json',
                '--profile-format', 'json'
            ])
            
            assert result.exit_code == 0
            mock_controller.set_sender_profile_object.assert_called_once()