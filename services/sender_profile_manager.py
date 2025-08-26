

import json
from pathlib import Path
from typing import (
    Dict,
    Any,
    List,
    Optional,
    Tuple
)
from dataclasses import asdict
from urllib.parse import urlparse
import os

import yaml

from models.data_models import (
    SenderProfile,
    ValidationError
)
from utils.validation_framework import ValidationFramework


class SenderProfileManager:
    """
    Service for managing sender profiles with support for multiple formats.
    
    This service handles loading, saving, and validating sender profiles
    in various formats (markdown, JSON, YAML) for personalized outreach emails.
    """
    
    def __init__(self):
        """Initialize the sender profile manager."""
        pass
    
    def discover_existing_profiles(self) -> List[Dict[str, Any]]:
        """
        Discover existing profiles in common locations.
        
        Returns:
            List of dictionaries containing profile information:
            [
                {
                    'path': '/path/to/profile.md',
                    'format': 'markdown',
                    'name': 'John Doe',
                    'role': 'Software Engineer',
                    'modified': datetime,
                    'size': 1024
                },
                ...
            ]
        """
        profiles = []
        
        # Common profile locations to check
        search_locations = [
            Path.cwd() / "profiles",  # Current directory profiles folder
            Path.cwd(),  # Current directory
            Path.home() / ".job_prospect_automation" / "profiles",  # User config folder
            Path.home() / "profiles",  # User home profiles folder
        ]
        
        # Profile file patterns to look for
        patterns = [
            "*.md", "*.markdown",  # Markdown files
            "*.json",  # JSON files
            "*.yaml", "*.yml"  # YAML files
        ]
        
        for location in search_locations:
            if not location.exists():
                continue
                
            for pattern in patterns:
                for profile_path in location.glob(pattern):
                    try:
                        # Determine format from extension
                        suffix = profile_path.suffix.lower()
                        if suffix in ['.md', '.markdown']:
                            format_type = 'markdown'
                        elif suffix == '.json':
                            format_type = 'json'
                        elif suffix in ['.yaml', '.yml']:
                            format_type = 'yaml'
                        else:
                            continue
                        
                        # Try to load profile to get name and role
                        try:
                            if format_type == 'markdown':
                                profile = self.load_profile_from_markdown(str(profile_path))
                            elif format_type == 'json':
                                profile = self.load_profile_from_json(str(profile_path))
                            elif format_type == 'yaml':
                                profile = self.load_profile_from_yaml(str(profile_path))
                            
                            # Get file stats
                            stat = profile_path.stat()
                            
                            profiles.append({
                                'path': str(profile_path),
                                'format': format_type,
                                'name': profile.name,
                                'role': profile.current_role,
                                'modified': stat.st_mtime,
                                'size': stat.st_size
                            })
                            
                        except (ValidationError, FileNotFoundError, Exception):
                            # Skip invalid profiles
                            continue
                            
                    except Exception:
                        # Skip files that can't be processed
                        continue
        
        # Sort by modification time (newest first)
        profiles.sort(key=lambda x: x['modified'], reverse=True)
        
        # Remove duplicates (same name and role)
        seen = set()
        unique_profiles = []
        for profile in profiles:
            key = (profile['name'], profile['role'])
            if key not in seen:
                seen.add(key)
                unique_profiles.append(profile)
        
        return unique_profiles
    
    def show_profile_selection_dialog(self, existing_profiles: List[Dict[str, Any]]) -> Optional[str]:
        """
        Show a dialog for selecting from existing profiles or creating a new one.
        
        Args:
            existing_profiles: List of existing profile dictionaries
            
        Returns:
            Profile path if existing profile selected, None if create new, 'cancel' if cancelled
        """
        if not existing_profiles:
            return None
        
        print("\n" + "="*60)
        print("🔍 EXISTING PROFILES FOUND")
        print("="*60)
        print("The following sender profiles were found on your system:\n")
        
        for i, profile in enumerate(existing_profiles, 1):
            # Convert modification time to readable format
            import datetime
            mod_time = datetime.datetime.fromtimestamp(profile['modified'])
            
            print(f"[{i}] {profile['name']} - {profile['role']}")
            print(f"    📁 File: {profile['path']}")
            print(f"    📅 Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"    📄 Format: {profile['format']}")
            print()
        
        print(f"[{len(existing_profiles) + 1}] Create a new profile")
        print(f"[0] Cancel")
        print("\n" + "="*60)
        
        while True:
            try:
                choice = input(f"Select an option (0-{len(existing_profiles) + 1}): ").strip()
                
                if choice == '0':
                    return 'cancel'
                elif choice == str(len(existing_profiles) + 1):
                    return None  # Create new
                else:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(existing_profiles):
                        selected_profile = existing_profiles[choice_num - 1]
                        print(f"\n✅ Selected: {selected_profile['name']} - {selected_profile['role']}")
                        return selected_profile['path']
                    else:
                        print(f"❌ Please enter a number between 0 and {len(existing_profiles) + 1}")
                        
            except ValueError:
                print(f"❌ Please enter a valid number between 0 and {len(existing_profiles) + 1}")
            except KeyboardInterrupt:
                print("\n⚠️  Selection cancelled.")
                return 'cancel'
    
    def load_profile_from_markdown(self, file_path: str) -> SenderProfile:
        """
        Load sender profile from markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            SenderProfile instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If profile data is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile file not found: {file_path}")
        
        try:
            content = path.read_text(encoding='utf-8')
            profile_data = self._parse_markdown_content(content)
            return SenderProfile.from_dict(profile_data)
        except Exception as e:
            raise ValidationError(f"Failed to load profile from markdown: {str(e)}")
    
    def load_profile_from_config(self, config_data: Dict[str, Any]) -> SenderProfile:
        """
        Load sender profile from configuration dictionary.
        
        Args:
            config_data: Dictionary containing profile data
            
        Returns:
            SenderProfile instance
            
        Raises:
            ValidationError: If profile data is invalid
        """
        try:
            return SenderProfile.from_dict(config_data)
        except Exception as e:
            raise ValidationError(f"Failed to load profile from config: {str(e)}")
    
    def load_profile_from_json(self, file_path: str) -> SenderProfile:
        """
        Load sender profile from JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            SenderProfile instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If profile data is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return self.load_profile_from_config(config_data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Failed to load profile from JSON: {str(e)}")
    
    def load_profile_from_yaml(self, file_path: str) -> SenderProfile:
        """
        Load sender profile from YAML file.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            SenderProfile instance
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValidationError: If profile data is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile file not found: {file_path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            return self.load_profile_from_config(config_data)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML format: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Failed to load profile from YAML: {str(e)}")
    
    def save_profile_to_markdown(self, profile: SenderProfile, file_path: str) -> None:
        """
        Save sender profile to markdown file.
        
        Args:
            profile: SenderProfile instance to save
            file_path: Path where to save the markdown file
            
        Raises:
            ValidationError: If profile is invalid or save fails
        """
        try:
            # Validate profile before saving
            profile.validate()
            
            markdown_content = self._generate_markdown_content(profile)
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown_content, encoding='utf-8')
            
        except Exception as e:
            raise ValidationError(f"Failed to save profile to markdown: {str(e)}")
    
    def save_profile_to_json(self, profile: SenderProfile, file_path: str) -> None:
        """
        Save sender profile to JSON file.
        
        Args:
            profile: SenderProfile instance to save
            file_path: Path where to save the JSON file
            
        Raises:
            ValidationError: If profile is invalid or save fails
        """
        try:
            # Validate profile before saving
            profile.validate()
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise ValidationError(f"Failed to save profile to JSON: {str(e)}")
    
    def save_profile_to_yaml(self, profile: SenderProfile, file_path: str) -> None:
        """
        Save sender profile to YAML file.
        
        Args:
            profile: SenderProfile instance to save
            file_path: Path where to save the YAML file
            
        Raises:
            ValidationError: If profile is invalid or save fails
        """
        try:
            # Validate profile before saving
            profile.validate()
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(profile.to_dict(), f, default_flow_style=False, allow_unicode=True)
                
        except Exception as e:
            raise ValidationError(f"Failed to save profile to YAML: {str(e)}")
    
    def validate_profile(self, profile: SenderProfile) -> Tuple[bool, List[str]]:
        """
        Validate sender profile and return validation results using enhanced validation framework.
        
        Args:
            profile: SenderProfile instance to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Use enhanced validation framework
        validation_result = profile.validate()
        if not validation_result.is_valid:
            issues.append(validation_result.message)
        
        # Check completeness using existing methods
        if not profile.is_complete():
            missing_fields = profile.get_missing_fields()
            issues.append(f"Profile is incomplete. Missing fields: {', '.join(missing_fields)}")
        
        # Check completeness score with enhanced messaging
        score = profile.get_completeness_score()
        if score < 0.7:
            issues.append(f"Profile completeness score is low ({score:.1%}). Consider adding more details for better job matching.")
        
        # Additional validation using ValidationFramework for better error messages
        if profile.portfolio_links:
            for i, link in enumerate(profile.portfolio_links):
                if link:
                    url_validation = ValidationFramework.validate_url(link)
                    if not url_validation.is_valid:
                        issues.append(f"Portfolio link {i+1} is invalid: {url_validation.message}")
        
        return len(issues) == 0, issues
    
    def get_profile_suggestions(self, profile: SenderProfile) -> List[str]:
        """
        Get suggestions for improving the sender profile.
        
        Args:
            profile: SenderProfile instance to analyze
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check missing fields
        missing_fields = profile.get_missing_fields()
        if missing_fields:
            suggestions.append(f"Add missing required fields: {', '.join(missing_fields)}")
        
        # Check field quality
        if profile.experience_summary and len(profile.experience_summary) < 50:
            suggestions.append("Consider expanding your experience summary (aim for 50+ characters)")
        
        if profile.value_proposition and len(profile.value_proposition) < 30:
            suggestions.append("Consider expanding your value proposition (aim for 30+ characters)")
        
        if len(profile.key_skills) < 3:
            suggestions.append("Add more key skills (aim for at least 3-5 skills)")
        
        if len(profile.target_roles) < 2:
            suggestions.append("Consider adding more target roles to increase opportunities")
        
        if not profile.notable_achievements:
            suggestions.append("Add notable achievements to strengthen your profile")
        
        if not profile.portfolio_links:
            suggestions.append("Add portfolio links (LinkedIn, GitHub, personal website)")
        
        if not profile.location:
            suggestions.append("Add your location to help with location-based matching")
        
        if not profile.remote_preference:
            suggestions.append("Specify your remote work preference")
        
        return suggestions
    
    def _parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """
        Parse markdown content and extract profile data.
        
        Args:
            content: Markdown content string
            
        Returns:
            Dictionary containing profile data
        """
        profile_data = {
            'name': '',
            'current_role': '',
            'years_experience': 0,
            'key_skills': [],
            'experience_summary': '',
            'education': [],
            'certifications': [],
            'value_proposition': '',
            'target_roles': [],
            'industries_of_interest': [],
            'notable_achievements': [],
            'portfolio_links': [],
            'preferred_contact_method': 'email',
            'availability': '',
            'location': '',
            'remote_preference': '',
            'salary_expectations': None,
            'additional_context': {}
        }
        
        lines = content.split('\n')
        current_section = None
        current_list = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and main headers
            if not line or line.startswith('# '):
                continue
            
            # Section headers
            if line.startswith('## '):
                # Save previous section if it was a list
                if current_section and current_list:
                    self._save_list_section(profile_data, current_section, current_list)
                    current_list = []
                
                current_section = line[3:].strip().lower()
                continue
            
            # Handle different sections
            if current_section == 'basic information':
                self._parse_basic_info_line(profile_data, line)
            elif current_section == 'professional summary':
                if profile_data['experience_summary']:
                    profile_data['experience_summary'] += ' ' + line
                else:
                    profile_data['experience_summary'] = line
            elif current_section == 'value proposition':
                if profile_data['value_proposition']:
                    profile_data['value_proposition'] += ' ' + line
                else:
                    profile_data['value_proposition'] = line
            elif current_section in ['key skills', 'experience highlights', 'education & certifications',
                                   'target roles', 'industries of interest', 'portfolio/links']:
                if line.startswith('- '):
                    current_list.append(line[2:].strip())
            elif current_section == 'additional context':
                if profile_data['additional_context'] == {}:
                    profile_data['additional_context'] = {}
                if line and not line.startswith('-'):
                    profile_data['additional_context']['notes'] = line
        
        # Save final section if it was a list
        if current_section and current_list:
            self._save_list_section(profile_data, current_section, current_list)
        
        return profile_data
    
    def _parse_basic_info_line(self, profile_data: Dict[str, Any], line: str) -> None:
        """Parse a line from the basic information section."""
        if line.startswith('- **Name**:'):
            profile_data['name'] = line.split(':', 1)[1].strip()
        elif line.startswith('- **Current Role**:'):
            profile_data['current_role'] = line.split(':', 1)[1].strip()
        elif line.startswith('- **Years of Experience**:'):
            try:
                years_str = line.split(':', 1)[1].strip()
                profile_data['years_experience'] = int(years_str)
            except ValueError:
                profile_data['years_experience'] = 0
        elif line.startswith('- **Location**:'):
            profile_data['location'] = line.split(':', 1)[1].strip()
        elif line.startswith('- **Remote Preference**:'):
            profile_data['remote_preference'] = line.split(':', 1)[1].strip().lower()
        elif line.startswith('- **Availability**:'):
            profile_data['availability'] = line.split(':', 1)[1].strip()
        elif line.startswith('- **Salary Expectations**:'):
            salary = line.split(':', 1)[1].strip()
            profile_data['salary_expectations'] = salary if salary else None
    
    def _save_list_section(self, profile_data: Dict[str, Any], section: str, items: List[str]) -> None:
        """Save list items to the appropriate profile data field."""
        if section == 'key skills':
            profile_data['key_skills'] = items
        elif section == 'experience highlights':
            profile_data['notable_achievements'] = items
        elif section == 'education & certifications':
            # Split education and certifications
            education = []
            certifications = []
            for item in items:
                if any(cert_word in item.lower() for cert_word in ['certified', 'certification', 'certificate']):
                    certifications.append(item)
                else:
                    education.append(item)
            profile_data['education'] = education
            profile_data['certifications'] = certifications
        elif section == 'target roles':
            profile_data['target_roles'] = items
        elif section == 'industries of interest':
            profile_data['industries_of_interest'] = items
        elif section == 'portfolio/links':
            profile_data['portfolio_links'] = items
    
    def _generate_markdown_content(self, profile: SenderProfile) -> str:
        """
        Generate markdown content from sender profile.
        
        Args:
            profile: SenderProfile instance
            
        Returns:
            Markdown content string
        """
        content = []
        content.append("# Sender Profile")
        content.append("")
        
        # Basic Information
        content.append("## Basic Information")
        content.append(f"- **Name**: {profile.name}")
        content.append(f"- **Current Role**: {profile.current_role}")
        content.append(f"- **Years of Experience**: {profile.years_experience}")
        if profile.location:
            content.append(f"- **Location**: {profile.location}")
        if profile.remote_preference:
            content.append(f"- **Remote Preference**: {profile.remote_preference}")
        if profile.availability:
            content.append(f"- **Availability**: {profile.availability}")
        if profile.salary_expectations:
            content.append(f"- **Salary Expectations**: {profile.salary_expectations}")
        content.append("")
        
        # Professional Summary
        if profile.experience_summary:
            content.append("## Professional Summary")
            content.append(profile.experience_summary)
            content.append("")
        
        # Key Skills
        if profile.key_skills:
            content.append("## Key Skills")
            for skill in profile.key_skills:
                content.append(f"- {skill}")
            content.append("")
        
        # Experience Highlights
        if profile.notable_achievements:
            content.append("## Experience Highlights")
            for achievement in profile.notable_achievements:
                content.append(f"- {achievement}")
            content.append("")
        
        # Education & Certifications
        if profile.education or profile.certifications:
            content.append("## Education & Certifications")
            for edu in profile.education:
                content.append(f"- {edu}")
            for cert in profile.certifications:
                content.append(f"- {cert}")
            content.append("")
        
        # Value Proposition
        if profile.value_proposition:
            content.append("## Value Proposition")
            content.append(profile.value_proposition)
            content.append("")
        
        # Target Roles
        if profile.target_roles:
            content.append("## Target Roles")
            for role in profile.target_roles:
                content.append(f"- {role}")
            content.append("")
        
        # Industries of Interest
        if profile.industries_of_interest:
            content.append("## Industries of Interest")
            for industry in profile.industries_of_interest:
                content.append(f"- {industry}")
            content.append("")
        
        # Portfolio/Links
        if profile.portfolio_links:
            content.append("## Portfolio/Links")
            for link in profile.portfolio_links:
                content.append(f"- {link}")
            content.append("")
        
        # Additional Context
        if profile.additional_context:
            content.append("## Additional Context")
            for key, value in profile.additional_context.items():
                content.append(f"**{key.title()}**: {value}")
            content.append("")
        
        return '\n'.join(content)
    
    def create_profile_interactively(self, check_existing: bool = True) -> SenderProfile:
        """
        Create sender profile through interactive CLI-based wizard.
        
        Args:
            check_existing: Whether to check for existing profiles first
        
        Returns:
            SenderProfile instance created interactively or loaded from existing
        """
        # Check for existing profiles if requested
        if check_existing:
            existing_profiles = self.discover_existing_profiles()
            
            if existing_profiles:
                selected_path = self.show_profile_selection_dialog(existing_profiles)
                
                if selected_path == 'cancel':
                    print("\n⚠️  Profile setup cancelled.")
                    raise KeyboardInterrupt("Profile setup cancelled by user")
                elif selected_path:  # Existing profile selected
                    try:
                        # Load the selected profile
                        selected_info = next(p for p in existing_profiles if p['path'] == selected_path)
                        format_type = selected_info['format']
                        
                        if format_type == 'markdown':
                            profile = self.load_profile_from_markdown(selected_path)
                        elif format_type == 'json':
                            profile = self.load_profile_from_json(selected_path)
                        elif format_type == 'yaml':
                            profile = self.load_profile_from_yaml(selected_path)
                        
                        print(f"\n✅ Successfully loaded existing profile: {profile.name}")
                        self._show_profile_preview(profile)
                        return profile
                        
                    except Exception as e:
                        print(f"\n❌ Error loading selected profile: {e}")
                        print("Proceeding with new profile creation...\n")
                # If selected_path is None, proceed with creating new profile
        
        print("\n=== Interactive Sender Profile Setup ===")
        print("Let's create your professional profile for personalized outreach emails.")
        print("You can skip optional fields by pressing Enter.\n")
        
        # Basic Information
        print("📋 Basic Information")
        name = self._get_input("Your full name", required=True)
        current_role = self._get_input("Your current role/position", required=True)
        
        years_experience = 0
        while True:
            try:
                years_str = self._get_input("Years of professional experience", required=True)
                years_experience = int(years_str)
                if years_experience < 0:
                    print("❌ Years of experience cannot be negative. Please try again.")
                    continue
                break
            except ValueError:
                print("❌ Please enter a valid number.")
        
        location = self._get_input("Your location (e.g., San Francisco, CA)")
        
        # Remote preference
        print("\nRemote work preference options: remote, hybrid, on-site, flexible")
        remote_preference = self._get_input("Remote work preference").lower()
        if remote_preference and remote_preference not in ["remote", "hybrid", "on-site", "flexible"]:
            print("⚠️  Using 'flexible' as default. You can edit this later.")
            remote_preference = "flexible"
        
        availability = self._get_input("Availability (e.g., Available immediately, 2 weeks notice)")
        salary_expectations = self._get_input("Salary expectations (optional)")
        
        # Professional Summary
        print("\n📝 Professional Summary")
        print("Write a 2-3 sentence summary of your professional background and what you're looking for.")
        experience_summary = self._get_multiline_input("Professional summary", required=True)
        
        # Value Proposition
        print("\n💡 Value Proposition")
        print("What unique value do you bring to potential employers? What makes you stand out?")
        value_proposition = self._get_multiline_input("Value proposition", required=True)
        
        # Skills
        print("\n🛠️  Key Skills")
        print("Enter your key skills one by one. Press Enter on empty line to finish.")
        key_skills = self._get_list_input("skill")
        
        # Target Roles
        print("\n🎯 Target Roles")
        print("What roles are you targeting? Enter one by one. Press Enter on empty line to finish.")
        target_roles = self._get_list_input("target role")
        
        # Notable Achievements
        print("\n🏆 Notable Achievements")
        print("Enter your notable achievements/accomplishments. Press Enter on empty line to finish.")
        notable_achievements = self._get_list_input("achievement")
        
        # Education
        print("\n🎓 Education")
        print("Enter your education background. Press Enter on empty line to finish.")
        education = self._get_list_input("education")
        
        # Certifications
        print("\n📜 Certifications")
        print("Enter your certifications. Press Enter on empty line to finish.")
        certifications = self._get_list_input("certification")
        
        # Industries of Interest
        print("\n🏢 Industries of Interest")
        print("Which industries interest you? Press Enter on empty line to finish.")
        industries_of_interest = self._get_list_input("industry")
        
        # Portfolio Links
        print("\n🔗 Portfolio/Links")
        print("Enter your portfolio links (LinkedIn, GitHub, personal website, etc.)")
        print("Press Enter on empty line to finish.")
        portfolio_links = self._get_list_input("link", validate_url=True)
        
        # Contact Preference
        print("\nContact preference options: email, linkedin, phone, other")
        preferred_contact_method = self._get_input("Preferred contact method", default="email").lower()
        if preferred_contact_method not in ["email", "linkedin", "phone", "other"]:
            preferred_contact_method = "email"
        
        # Create profile
        try:
            profile = SenderProfile(
                name=name,
                current_role=current_role,
                years_experience=years_experience,
                key_skills=key_skills,
                experience_summary=experience_summary,
                education=education,
                certifications=certifications,
                value_proposition=value_proposition,
                target_roles=target_roles,
                industries_of_interest=industries_of_interest,
                notable_achievements=notable_achievements,
                portfolio_links=portfolio_links,
                preferred_contact_method=preferred_contact_method,
                availability=availability,
                location=location,
                remote_preference=remote_preference,
                salary_expectations=salary_expectations if salary_expectations else None
            )
            
            print("\n✅ Profile created successfully!")
            self._show_profile_preview(profile)
            
            return profile
            
        except ValidationError as e:
            print(f"\n❌ Error creating profile: {e}")
            print("Please try again with valid information.")
            raise
    
    def _get_input(self, prompt: str, required: bool = False, default: str = "") -> str:
        """Get input from user with validation."""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    return default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if required and not user_input:
                print("❌ This field is required. Please enter a value.")
                continue
            
            return user_input
    
    def _get_multiline_input(self, prompt: str, required: bool = False) -> str:
        """Get multiline input from user."""
        print(f"{prompt}:")
        lines = []
        while True:
            try:
                line = input()
                if not line and lines:  # Empty line and we have content
                    break
                if line:
                    lines.append(line)
                elif not lines and required:
                    print("❌ This field is required. Please enter some text.")
            except KeyboardInterrupt:
                print("\n⚠️  Input cancelled.")
                break
        
        return ' '.join(lines)
    
    def _get_list_input(self, item_type: str, validate_url: bool = False) -> List[str]:
        """Get list input from user."""
        items = []
        while True:
            try:
                item = input(f"Enter {item_type} (or press Enter to finish): ").strip()
                if not item:
                    break
                
                if validate_url and item:
                    parsed = urlparse(item)
                    if not parsed.scheme or not parsed.netloc:
                        print("❌ Please enter a valid URL (including http:// or https://)")
                        continue
                
                items.append(item)
                print(f"✓ Added: {item}")
            except KeyboardInterrupt:
                print("\n⚠️  Input cancelled.")
                break
        
        return items
    
    def _show_profile_preview(self, profile: SenderProfile) -> None:
        """Show a preview of the created profile."""
        print("\n" + "="*50)
        print("📋 PROFILE PREVIEW")
        print("="*50)
        print(f"Name: {profile.name}")
        print(f"Role: {profile.current_role}")
        print(f"Experience: {profile.years_experience} years")
        print(f"Location: {profile.location or 'Not specified'}")
        print(f"Remote Preference: {profile.remote_preference or 'Not specified'}")
        print(f"\nSkills: {', '.join(profile.key_skills[:5])}")
        if len(profile.key_skills) > 5:
            print(f"  ... and {len(profile.key_skills) - 5} more")
        print(f"\nTarget Roles: {', '.join(profile.target_roles[:3])}")
        if len(profile.target_roles) > 3:
            print(f"  ... and {len(profile.target_roles) - 3} more")
        
        # Show completeness
        completeness = profile.get_completeness_score()
        print(f"\nProfile Completeness: {completeness:.1%}")
        
        if completeness < 0.8:
            print("💡 Consider adding more details to improve email personalization.")
        
        print("="*50)
    
    def edit_profile_interactively(self, profile: SenderProfile) -> SenderProfile:
        """
        Edit an existing profile interactively.
        
        Args:
            profile: Existing SenderProfile to edit
            
        Returns:
            Updated SenderProfile instance
        """
        print("\n=== Edit Sender Profile ===")
        print("Current profile preview:")
        self._show_profile_preview(profile)
        
        print("\nWhat would you like to edit?")
        print("1. Basic Information")
        print("2. Professional Summary")
        print("3. Skills")
        print("4. Target Roles")
        print("5. Achievements")
        print("6. Education & Certifications")
        print("7. Portfolio Links")
        print("8. All fields")
        print("0. Cancel")
        
        choice = input("\nEnter your choice (0-8): ").strip()
        
        if choice == "0":
            return profile
        elif choice == "1":
            return self._edit_basic_info(profile)
        elif choice == "2":
            return self._edit_professional_summary(profile)
        elif choice == "3":
            return self._edit_skills(profile)
        elif choice == "4":
            return self._edit_target_roles(profile)
        elif choice == "5":
            return self._edit_achievements(profile)
        elif choice == "6":
            return self._edit_education_certs(profile)
        elif choice == "7":
            return self._edit_portfolio_links(profile)
        elif choice == "8":
            print("Creating new profile with current values as defaults...")
            return self.create_profile_interactively()
        else:
            print("❌ Invalid choice. No changes made.")
            return profile
    
    def _edit_basic_info(self, profile: SenderProfile) -> SenderProfile:
        """Edit basic information fields."""
        print("\n📋 Edit Basic Information")
        print("Press Enter to keep current value.")
        
        name = self._get_input(f"Name [{profile.name}]", default=profile.name)
        current_role = self._get_input(f"Current role [{profile.current_role}]", default=profile.current_role)
        
        years_str = self._get_input(f"Years of experience [{profile.years_experience}]", default=str(profile.years_experience))
        try:
            years_experience = int(years_str)
        except ValueError:
            years_experience = profile.years_experience
        
        location = self._get_input(f"Location [{profile.location}]", default=profile.location)
        remote_preference = self._get_input(f"Remote preference [{profile.remote_preference}]", default=profile.remote_preference)
        availability = self._get_input(f"Availability [{profile.availability}]", default=profile.availability)
        
        # Create updated profile
        profile.name = name
        profile.current_role = current_role
        profile.years_experience = years_experience
        profile.location = location
        profile.remote_preference = remote_preference
        profile.availability = availability
        
        return profile
    
    def _edit_professional_summary(self, profile: SenderProfile) -> SenderProfile:
        """Edit professional summary and value proposition."""
        print("\n📝 Edit Professional Summary")
        print(f"Current summary: {profile.experience_summary}")
        print("\nEnter new summary (or press Enter twice to keep current):")
        new_summary = self._get_multiline_input("Professional summary")
        if new_summary:
            profile.experience_summary = new_summary
        
        print(f"\nCurrent value proposition: {profile.value_proposition}")
        print("\nEnter new value proposition (or press Enter twice to keep current):")
        new_value_prop = self._get_multiline_input("Value proposition")
        if new_value_prop:
            profile.value_proposition = new_value_prop
        
        return profile
    
    def _edit_skills(self, profile: SenderProfile) -> SenderProfile:
        """Edit skills list."""
        print("\n🛠️  Edit Skills")
        print(f"Current skills: {', '.join(profile.key_skills)}")
        print("\nEnter new skills (press Enter on empty line to finish):")
        new_skills = self._get_list_input("skill")
        if new_skills:
            profile.key_skills = new_skills
        
        return profile
    
    def _edit_target_roles(self, profile: SenderProfile) -> SenderProfile:
        """Edit target roles list."""
        print("\n🎯 Edit Target Roles")
        print(f"Current target roles: {', '.join(profile.target_roles)}")
        print("\nEnter new target roles (press Enter on empty line to finish):")
        new_roles = self._get_list_input("target role")
        if new_roles:
            profile.target_roles = new_roles
        
        return profile
    
    def _edit_achievements(self, profile: SenderProfile) -> SenderProfile:
        """Edit achievements list."""
        print("\n🏆 Edit Achievements")
        print(f"Current achievements: {', '.join(profile.notable_achievements)}")
        print("\nEnter new achievements (press Enter on empty line to finish):")
        new_achievements = self._get_list_input("achievement")
        if new_achievements:
            profile.notable_achievements = new_achievements
        
        return profile
    
    def _edit_education_certs(self, profile: SenderProfile) -> SenderProfile:
        """Edit education and certifications."""
        print("\n🎓 Edit Education")
        print(f"Current education: {', '.join(profile.education)}")
        print("\nEnter new education (press Enter on empty line to finish):")
        new_education = self._get_list_input("education")
        if new_education:
            profile.education = new_education
        
        print("\n📜 Edit Certifications")
        print(f"Current certifications: {', '.join(profile.certifications)}")
        print("\nEnter new certifications (press Enter on empty line to finish):")
        new_certs = self._get_list_input("certification")
        if new_certs:
            profile.certifications = new_certs
        
        return profile
    
    def _edit_portfolio_links(self, profile: SenderProfile) -> SenderProfile:
        """Edit portfolio links."""
        print("\n🔗 Edit Portfolio Links")
        print(f"Current links: {', '.join(profile.portfolio_links)}")
        print("\nEnter new portfolio links (press Enter on empty line to finish):")
        new_links = self._get_list_input("link", validate_url=True)
        if new_links:
            profile.portfolio_links = new_links
        
        return profile

    def create_profile_template(self, format_type: str = "markdown") -> str:
        """
        Create a template for sender profile in the specified format.
        
        Args:
            format_type: Format type ("markdown", "json", "yaml")
            
        Returns:
            Template content as string
            
        Raises:
            ValueError: If format_type is not supported
        """
        if format_type == "markdown":
            return self._create_markdown_template()
        elif format_type == "json":
            return self._create_json_template()
        elif format_type == "yaml":
            return self._create_yaml_template()
        else:
            raise ValueError(f"Unsupported format type: {format_type}")
    
    def _create_markdown_template(self) -> str:
        """Create markdown template."""
        return """# Sender Profile

## Basic Information
- **Name**: [Your Full Name]
- **Current Role**: [Your Current Position]
- **Years of Experience**: [Number]
- **Location**: [City, Country]
- **Remote Preference**: [Remote/Hybrid/On-site/Flexible]
- **Availability**: [Available immediately/2 weeks notice/etc.]
- **Salary Expectations**: [Optional: $X-$Y or negotiable]

## Professional Summary
[2-3 sentence summary of your professional background and what you're looking for]

## Key Skills
- [Skill 1]
- [Skill 2]
- [Skill 3]
- [Add more skills...]

## Experience Highlights
- [Notable achievement 1]
- [Notable achievement 2]
- [Notable achievement 3]
- [Add more achievements...]

## Education & Certifications
- [Degree/University]
- [Certification 1]
- [Certification 2]
- [Add more...]

## Value Proposition
[What unique value do you bring to potential employers? What makes you stand out?]

## Target Roles
- [Target Role 1]
- [Target Role 2]
- [Target Role 3]
- [Add more roles...]

## Industries of Interest
- [Industry 1]
- [Industry 2]
- [Industry 3]
- [Add more industries...]

## Portfolio/Links
- [Portfolio URL]
- [LinkedIn Profile]
- [GitHub Profile]
- [Other relevant links...]

## Additional Context
[Any other relevant information for personalization, special circumstances, etc.]
"""
    
    def _create_json_template(self) -> str:
        """Create JSON template."""
        template_data = {
            "name": "[Your Full Name]",
            "current_role": "[Your Current Position]",
            "years_experience": 0,
            "key_skills": ["[Skill 1]", "[Skill 2]", "[Skill 3]"],
            "experience_summary": "[2-3 sentence summary of your professional background]",
            "education": ["[Degree/University]", "[Other education]"],
            "certifications": ["[Certification 1]", "[Certification 2]"],
            "value_proposition": "[What unique value do you bring to potential employers?]",
            "target_roles": ["[Target Role 1]", "[Target Role 2]"],
            "industries_of_interest": ["[Industry 1]", "[Industry 2]"],
            "notable_achievements": ["[Achievement 1]", "[Achievement 2]"],
            "portfolio_links": ["[Portfolio URL]", "[LinkedIn Profile]", "[GitHub Profile]"],
            "preferred_contact_method": "email",
            "availability": "[Available immediately/2 weeks notice/etc.]",
            "location": "[City, Country]",
            "remote_preference": "[remote/hybrid/on-site/flexible]",
            "salary_expectations": "[Optional: $X-$Y or negotiable]",
            "additional_context": {
                "notes": "[Any other relevant information]"
            }
        }
        return json.dumps(template_data, indent=2)
    
    def _create_yaml_template(self) -> str:
        """Create YAML template."""
        template_data = {
            "name": "[Your Full Name]",
            "current_role": "[Your Current Position]",
            "years_experience": 0,
            "key_skills": ["[Skill 1]", "[Skill 2]", "[Skill 3]"],
            "experience_summary": "[2-3 sentence summary of your professional background]",
            "education": ["[Degree/University]", "[Other education]"],
            "certifications": ["[Certification 1]", "[Certification 2]"],
            "value_proposition": "[What unique value do you bring to potential employers?]",
            "target_roles": ["[Target Role 1]", "[Target Role 2]"],
            "industries_of_interest": ["[Industry 1]", "[Industry 2]"],
            "notable_achievements": ["[Achievement 1]", "[Achievement 2]"],
            "portfolio_links": ["[Portfolio URL]", "[LinkedIn Profile]", "[GitHub Profile]"],
            "preferred_contact_method": "email",
            "availability": "[Available immediately/2 weeks notice/etc.]",
            "location": "[City, Country]",
            "remote_preference": "[remote/hybrid/on-site/flexible]",
            "salary_expectations": "[Optional: $X-$Y or negotiable]",
            "additional_context": {
                "notes": "[Any other relevant information]"
            }
        }
        return yaml.dump(template_data, default_flow_style=False)
