#!/usr/bin/env python3
"""
Tests for enhanced CLI profile integration with main CLI commands.
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
from controllers.prospect_automation_controller import ProspectAutomationController


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


def test_profile_commands_integration(runner):
    """Test that profile commands are properly integrated with main CLI."""
    result = runner.invoke(cli, ['profile', '--help'])
    
    assert result.exit_code == 0
    assert "Manage sender profiles for personalized outreach emails" in result.output
    assert "create" in result.output
    assert "validate" in result.output
    assert "convert" in result.output
    assert "preview" in result.output
    assert "edit" in result.output
    assert "check-completeness" in result.output
    assert "list" in result.output
    assert "generate-template" in result.output
    assert "analyze" in result.output
    assert "import" in result.output
    assert "bulk-validate" in result.output


def test_process_company_with_profile_validation(runner, temp_profile_dir, mock_profile):
    """Test process-company command with profile validation."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch('cli.CLIConfig') as mock_cli_config:
        mock_cli_config.return_value.dry_run = True
        
        with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
            mock_load.return_value = mock_profile
            
            with patch.object(SenderProfileManager, 'validate_profile') as mock_validate:
                mock_validate.return_value = (True, [])
                
                result = runner.invoke(cli, [
                    'process-company', 
                    'TestCompany', 
                    '--sender-profile', profile_path,
                    '--validate-profile'
                ])
                
                assert result.exit_code == 0
                assert "DRY-RUN: Would process company 'TestCompany'" in result.output
                assert f"Would use sender profile: {profile_path}" in result.output
                assert "Would validate sender profile before processing" in result.output


def test_generate_emails_with_interactive_profile(runner, temp_profile_dir, mock_profile):
    """Test generate-emails command with interactive profile setup."""
    with patch('cli.CLIConfig') as mock_cli_config:
        mock_cli_config.return_value.dry_run = True
        
        with patch.object(SenderProfileManager, 'create_profile_interactively') as mock_create:
            mock_create.return_value = mock_profile
            
            result = runner.invoke(cli, [
                'generate-emails', 
                '--prospect-ids', '123,456',
                '--interactive-profile'
            ])
            
            assert result.exit_code == 0
            assert "DRY-RUN: Would generate cold_outreach emails for 2 prospects" in result.output
            assert "Would create sender profile interactively" in result.output


def test_enhanced_workflow_with_profile_completeness_check(runner, temp_profile_dir, mock_profile):
    """Test enhanced-workflow command with profile completeness check."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch('cli.CLIConfig') as mock_cli_config:
        mock_cli_config.return_value.dry_run = True
        
        with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
            mock_load.return_value = mock_profile
            
            with patch.object(mock_profile, 'get_completeness_score') as mock_score:
                mock_score.return_value = 0.85
                
                result = runner.invoke(cli, [
                    'enhanced-workflow',
                    '--sender-profile', profile_path,
                    '--check-profile-completeness',
                    '--completeness-threshold', '0.8'
                ])
                
                assert result.exit_code == 0
                assert "DRY-RUN: Would run enhanced workflow" in result.output
                assert f"Would use sender profile: {profile_path}" in result.output
                assert "Would check profile completeness (threshold: 80.0%)" in result.output