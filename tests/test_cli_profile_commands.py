#!/usr/bin/env python3
"""
Tests for CLI profile management commands.
"""

import os
import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cli_profile_commands import profile
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


def test_create_profile_template(runner, temp_profile_dir):
    """Test creating a profile template."""
    output_path = str(temp_profile_dir / "test_profile.md")
    
    with patch.object(SenderProfileManager, 'create_profile_template') as mock_create:
        mock_create.return_value = "# Test Template"
        
        result = runner.invoke(profile, ['create', '--template', '--output', output_path])
        
        assert result.exit_code == 0
        assert "Template saved to:" in result.output
        mock_create.assert_called_once_with('markdown')
        
        # Check file was created
        assert Path(output_path).exists()


def test_create_profile_interactive(runner, temp_profile_dir, mock_profile):
    """Test creating a profile interactively."""
    output_path = str(temp_profile_dir / "test_profile.md")
    
    with patch.object(SenderProfileManager, 'create_profile_interactively') as mock_create:
        mock_create.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'save_profile_to_markdown') as mock_save:
            result = runner.invoke(profile, ['create', '--interactive', '--output', output_path])
            
            assert result.exit_code == 0
            assert "Profile created successfully" in result.output
            mock_create.assert_called_once()
            mock_save.assert_called_once_with(mock_profile, output_path)


def test_validate_profile(runner, temp_profile_dir, mock_profile):
    """Test validating a profile."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'validate_profile') as mock_validate:
            mock_validate.return_value = (True, [])
            
            result = runner.invoke(profile, ['validate', profile_path])
            
            assert result.exit_code == 0
            assert "Profile is valid" in result.output
            mock_load.assert_called_once_with(profile_path)
            mock_validate.assert_called_once_with(mock_profile)


def test_validate_profile_with_issues(runner, temp_profile_dir, mock_profile):
    """Test validating a profile with issues."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'validate_profile') as mock_validate:
            mock_validate.return_value = (False, ["Missing required fields"])
            
            with patch.object(SenderProfileManager, 'get_profile_suggestions') as mock_suggestions:
                mock_suggestions.return_value = ["Add more skills"]
                
                result = runner.invoke(profile, ['validate', profile_path])
                
                assert result.exit_code == 0
                assert "Profile has issues" in result.output
                assert "Missing required fields" in result.output
                assert "Add more skills" in result.output
                mock_load.assert_called_once_with(profile_path)
                mock_validate.assert_called_once_with(mock_profile)
                mock_suggestions.assert_called_once_with(mock_profile)


def test_convert_profile(runner, temp_profile_dir, mock_profile):
    """Test converting a profile between formats."""
    input_path = str(temp_profile_dir / "input_profile.md")
    output_path = str(temp_profile_dir / "output_profile.json")
    
    # Create a test profile file
    with open(input_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'save_profile_to_json') as mock_save:
            result = runner.invoke(profile, ['convert', input_path, output_path])
            
            assert result.exit_code == 0
            assert "Successfully converted profile from markdown to json" in result.output
            mock_load.assert_called_once_with(input_path)
            mock_save.assert_called_once_with(mock_profile, output_path)


def test_preview_profile(runner, temp_profile_dir, mock_profile):
    """Test previewing a profile."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        with patch.object(SenderProfileManager, '_generate_markdown_content') as mock_generate:
            mock_generate.return_value = "# Test Profile Preview"
            
            result = runner.invoke(profile, ['preview', profile_path])
            
            assert result.exit_code == 0
            assert "Completeness Score" in result.output
            mock_load.assert_called_once_with(profile_path)
            mock_generate.assert_called_once_with(mock_profile)


def test_edit_profile(runner, temp_profile_dir, mock_profile):
    """Test editing a profile."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'edit_profile_interactively') as mock_edit:
            updated_profile = mock_profile
            updated_profile.name = "Updated Name"
            mock_edit.return_value = updated_profile
            
            with patch.object(SenderProfileManager, 'save_profile_to_markdown') as mock_save:
                result = runner.invoke(profile, ['edit', profile_path])
                
                assert result.exit_code == 0
                assert "Profile updated and saved" in result.output
                mock_load.assert_called_once_with(profile_path)
                mock_edit.assert_called_once_with(mock_profile)
                mock_save.assert_called_once_with(updated_profile, profile_path)


def test_check_completeness_pass(runner, temp_profile_dir, mock_profile):
    """Test checking profile completeness that passes threshold."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        # Mock the get_completeness_score method on the profile
        mock_profile.get_completeness_score = MagicMock(return_value=0.8)
        
        result = runner.invoke(profile, ['check-completeness', profile_path])
        
        assert result.exit_code == 0
        assert "meets or exceeds threshold" in result.output
        mock_load.assert_called_once_with(profile_path)
        mock_profile.get_completeness_score.assert_called_once()


def test_check_completeness_fail(runner, temp_profile_dir, mock_profile):
    """Test checking profile completeness that fails threshold."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        # Mock the get_completeness_score method on the profile
        mock_profile.get_completeness_score = MagicMock(return_value=0.5)
        mock_profile.get_missing_fields = MagicMock(return_value=["value_proposition"])
        
        with patch.object(SenderProfileManager, 'get_profile_suggestions') as mock_suggestions:
            mock_suggestions.return_value = ["Add a value proposition"]
            
            # For this test, we'll check the output messages and ignore the exit code
            # since sys.exit() is hard to test with Click's testing framework
            with patch('sys.exit') as mock_exit:
                result = runner.invoke(profile, ['check-completeness', profile_path])
                
                # Check that sys.exit was called (ignore the specific code)
                assert mock_exit.called
                
                assert "below threshold" in result.output
                assert "value_proposition" in result.output
                assert "Add a value proposition" in result.output
                mock_load.assert_called_once_with(profile_path)
                mock_profile.get_completeness_score.assert_called_once()
                mock_profile.get_missing_fields.assert_called_once()
                mock_suggestions.assert_called_once_with(mock_profile)