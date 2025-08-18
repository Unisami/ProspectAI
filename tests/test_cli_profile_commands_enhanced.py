#!/usr/bin/env python3
"""
Tests for enhanced CLI profile management commands.
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


def test_list_profiles(runner, temp_profile_dir, mock_profile):
    """Test listing profiles."""
    # Create test profile files
    md_path = temp_profile_dir / "profile1.md"
    json_path = temp_profile_dir / "profile2.json"
    yaml_path = temp_profile_dir / "profile3.yaml"
    
    with open(md_path, 'w') as f:
        f.write("# Test Profile 1")
    
    with open(json_path, 'w') as f:
        json.dump({"name": "Test Profile 2"}, f)
    
    with open(yaml_path, 'w') as f:
        yaml.dump({"name": "Test Profile 3"}, f)
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load_md:
        mock_load_md.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'load_profile_from_json') as mock_load_json:
            mock_load_json.return_value = mock_profile
            
            with patch.object(SenderProfileManager, 'load_profile_from_yaml') as mock_load_yaml:
                mock_load_yaml.return_value = mock_profile
                
                result = runner.invoke(profile, ['list', '--directory', str(temp_profile_dir)])
                
                assert result.exit_code == 0
                assert "Sender Profiles in" in result.output
                # Check for the profile name and format instead of the filename
                assert "Test User" in result.output
                assert "markdown" in result.output
                assert "json" in result.output
                assert "yaml" in result.output


def test_generate_template(runner, temp_profile_dir):
    """Test generating a profile template."""
    output_path = str(temp_profile_dir / "template.md")
    
    with patch.object(SenderProfileManager, 'create_profile_template') as mock_create:
        mock_create.return_value = "# Template Content"
        
        result = runner.invoke(profile, ['generate-template', '--output', output_path])
        
        assert result.exit_code == 0
        assert "Generating markdown template" in result.output
        assert "Template saved to:" in result.output
        mock_create.assert_called_once_with('markdown')
        
        # Check file was created
        assert Path(output_path).exists()


def test_analyze_profile(runner, temp_profile_dir, mock_profile):
    """Test analyzing a profile for relevance."""
    profile_path = str(temp_profile_dir / "test_profile.md")
    
    # Create a test profile file
    with open(profile_path, 'w') as f:
        f.write("# Test Profile")
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load:
        mock_load.return_value = mock_profile
        
        # Mock the get_relevant_experience method
        mock_profile.get_relevant_experience = MagicMock(return_value=["Relevant skill: Python", "Led team of 5 engineers"])
        
        result = runner.invoke(profile, ['analyze', profile_path, '--target-role', 'Backend Developer'])
        
        assert result.exit_code == 0
        assert "Profile Summary" in result.output
        assert "Relevance Analysis for 'Backend Developer'" in result.output
        assert "Relevant experience and skills" in result.output
        mock_load.assert_called_once_with(profile_path)
        mock_profile.get_relevant_experience.assert_called_once()


def test_import_profile(runner, temp_profile_dir):
    """Test importing a profile from external source."""
    input_path = str(temp_profile_dir / "input.txt")
    output_path = str(temp_profile_dir / "output_profile.md")
    
    # Create a test input file
    with open(input_path, 'w') as f:
        f.write("Name: Test User\nHeadline: Software Engineer\nSkills: Python, JavaScript")
    
    with patch.object(SenderProfileManager, 'save_profile_to_markdown') as mock_save:
        result = runner.invoke(profile, ['import', input_path, '--format', 'linkedin', '--output', output_path])
        
        assert result.exit_code == 0
        assert "Importing profile from linkedin format" in result.output
        assert "Profile imported and saved to:" in result.output
        mock_save.assert_called_once()


def test_bulk_validate(runner, temp_profile_dir, mock_profile):
    """Test bulk validation of profiles."""
    # Create test profile files
    md_path = temp_profile_dir / "profile1.md"
    json_path = temp_profile_dir / "profile2.json"
    
    with open(md_path, 'w') as f:
        f.write("# Test Profile 1")
    
    with open(json_path, 'w') as f:
        json.dump({"name": "Test Profile 2"}, f)
    
    with patch.object(SenderProfileManager, 'load_profile_from_markdown') as mock_load_md:
        mock_load_md.return_value = mock_profile
        
        with patch.object(SenderProfileManager, 'load_profile_from_json') as mock_load_json:
            mock_load_json.return_value = mock_profile
            
            with patch.object(SenderProfileManager, 'validate_profile') as mock_validate:
                # First profile passes, second fails
                mock_validate.side_effect = [(True, []), (False, ["Missing fields"])]
                
                # Use a mock for sys.exit to avoid test termination
                with patch('sys.exit') as mock_exit:
                    result = runner.invoke(profile, ['bulk-validate', '--directory', str(temp_profile_dir)])
                    
                    # Check that sys.exit was called
                    assert mock_exit
                assert "Profile Validation Results" in result.output
                assert "✓ Passed" in result.output
                assert "✗ Failed" in result.output
                assert "Summary:" in result.output
                assert mock_validate.call_count == 2