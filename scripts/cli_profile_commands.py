#!/usr/bin/env python3
"""
CLI commands for sender profile management.
"""

import click
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

from services.sender_profile_manager import SenderProfileManager
from models.data_models import SenderProfile, ValidationError

console = Console()


@click.group()
def profile():
    """Manage sender profiles for personalized outreach emails."""
    pass


@profile.command('create')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), default='markdown',
              help='Output format for the profile')
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--interactive/--template', default=True, help='Create interactively or generate template')
def create_profile(format, output, interactive):
    """Create a new sender profile."""
    try:
        manager = SenderProfileManager()
        
        if interactive:
            console.print("[blue]Starting interactive profile creation...[/blue]")
            profile = manager.create_profile_interactively()
            console.print(f"[green]Profile created successfully for {profile.name}![/green]")
        else:
            console.print(f"[blue]Generating {format} template...[/blue]")
            template_content = manager.create_profile_template(format)
            
            # Save template to file
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(template_content)
                
            console.print(f"[green]Template saved to: {output}[/green]")
            console.print("[yellow]Please edit the file with your information.[/yellow]")
            return
        
        # Save profile to file
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'markdown':
            manager.save_profile_to_markdown(profile, output)
        elif format == 'json':
            manager.save_profile_to_json(profile, output)
        elif format == 'yaml':
            manager.save_profile_to_yaml(profile, output)
        
        console.print(f"[green]Profile saved to: {output}[/green]")
        
    except ValidationError as e:
        console.print(f"[red]Error creating profile: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('validate')
@click.argument('profile_path')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Profile format (auto-detected from file extension if not specified)')
def validate_profile(profile_path, format):
    """Validate a sender profile and check for issues."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect format from file extension if not specified
        if not format:
            if profile_path.endswith('.md'):
                format = 'markdown'
            elif profile_path.endswith('.json'):
                format = 'json'
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                format = 'yaml'
            else:
                console.print("[red]Could not detect profile format from file extension.[/red]")
                console.print("[red]Please specify format using --format option.[/red]")
                return 1
        
        # Load profile based on format
        try:
            if format == 'markdown':
                profile = manager.load_profile_from_markdown(profile_path)
            elif format == 'json':
                profile = manager.load_profile_from_json(profile_path)
            elif format == 'yaml':
                profile = manager.load_profile_from_yaml(profile_path)
        except FileNotFoundError:
            console.print(f"[red]Profile file not found: {profile_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Profile validation failed: {e}[/red]")
            return 1
        
        # Validate profile
        is_valid, issues = manager.validate_profile(profile)
        
        # Display profile summary
        console.print(f"[blue]Profile Summary for {profile.name}[/blue]")
        console.print(f"Current Role: {profile.current_role}")
        console.print(f"Experience: {profile.years_experience} years")
        console.print(f"Skills: {', '.join(profile.key_skills[:5])}")
        if len(profile.key_skills) > 5:
            console.print(f"...and {len(profile.key_skills) - 5} more skills")
        
        # Display validation results
        completeness = profile.get_completeness_score()
        console.print(f"\nCompleteness Score: {completeness:.1%}")
        
        if is_valid:
            console.print("[green]✓ Profile is valid[/green]")
        else:
            console.print("[red]✗ Profile has issues:[/red]")
            for issue in issues:
                console.print(f"  [red]• {issue}[/red]")
        
        # Display suggestions
        suggestions = manager.get_profile_suggestions(profile)
        if suggestions:
            console.print("\n[yellow]Suggestions for improvement:[/yellow]")
            for suggestion in suggestions:
                console.print(f"  [yellow]• {suggestion}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('convert')
@click.argument('input_path')
@click.argument('output_path')
@click.option('--input-format', '-i', type=click.Choice(['markdown', 'json', 'yaml']),
              help='Input format (auto-detected from file extension if not specified)')
@click.option('--output-format', '-o', type=click.Choice(['markdown', 'json', 'yaml']),
              help='Output format (auto-detected from file extension if not specified)')
def convert_profile(input_path, output_path, input_format, output_format):
    """Convert a sender profile between formats (markdown/JSON/YAML)."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect input format from file extension if not specified
        if not input_format:
            if input_path.endswith('.md'):
                input_format = 'markdown'
            elif input_path.endswith('.json'):
                input_format = 'json'
            elif input_path.endswith('.yaml') or input_path.endswith('.yml'):
                input_format = 'yaml'
            else:
                console.print("[red]Could not detect input format from file extension.[/red]")
                console.print("[red]Please specify input format using --input-format option.[/red]")
                return 1
        
        # Auto-detect output format from file extension if not specified
        if not output_format:
            if output_path.endswith('.md'):
                output_format = 'markdown'
            elif output_path.endswith('.json'):
                output_format = 'json'
            elif output_path.endswith('.yaml') or output_path.endswith('.yml'):
                output_format = 'yaml'
            else:
                console.print("[red]Could not detect output format from file extension.[/red]")
                console.print("[red]Please specify output format using --output-format option.[/red]")
                return 1
        
        # Load profile based on input format
        try:
            if input_format == 'markdown':
                profile = manager.load_profile_from_markdown(input_path)
            elif input_format == 'json':
                profile = manager.load_profile_from_json(input_path)
            elif input_format == 'yaml':
                profile = manager.load_profile_from_yaml(input_path)
        except FileNotFoundError:
            console.print(f"[red]Input file not found: {input_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Input profile validation failed: {e}[/red]")
            return 1
        
        # Save profile based on output format
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if output_format == 'markdown':
                manager.save_profile_to_markdown(profile, output_path)
            elif output_format == 'json':
                manager.save_profile_to_json(profile, output_path)
            elif output_format == 'yaml':
                manager.save_profile_to_yaml(profile, output_path)
        except Exception as e:
            console.print(f"[red]Error saving output file: {e}[/red]")
            return 1
        
        console.print(f"[green]Successfully converted profile from {input_format} to {output_format}[/green]")
        console.print(f"[green]Output saved to: {output_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('preview')
@click.argument('profile_path')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Profile format (auto-detected from file extension if not specified)')
def preview_profile(profile_path, format):
    """Preview a sender profile with formatting."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect format from file extension if not specified
        if not format:
            if profile_path.endswith('.md'):
                format = 'markdown'
            elif profile_path.endswith('.json'):
                format = 'json'
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                format = 'yaml'
            else:
                console.print("[red]Could not detect profile format from file extension.[/red]")
                console.print("[red]Please specify format using --format option.[/red]")
                return 1
        
        # Load profile based on format
        try:
            if format == 'markdown':
                profile = manager.load_profile_from_markdown(profile_path)
            elif format == 'json':
                profile = manager.load_profile_from_json(profile_path)
            elif format == 'yaml':
                profile = manager.load_profile_from_yaml(profile_path)
        except FileNotFoundError:
            console.print(f"[red]Profile file not found: {profile_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Profile validation failed: {e}[/red]")
            return 1
        
        # Generate markdown content for preview
        markdown_content = manager._generate_markdown_content(profile)
        
        # Display profile preview
        console.print(Panel(
            Markdown(markdown_content),
            title=f"Profile Preview: {profile.name}",
            border_style="blue",
            expand=False
        ))
        
        # Display completeness score
        completeness = profile.get_completeness_score()
        console.print(f"\nCompleteness Score: {completeness:.1%}")
        
        if completeness < 0.7:
            console.print("[yellow]⚠️ Profile completeness is below recommended threshold (70%)[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('edit')
@click.argument('profile_path')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Profile format (auto-detected from file extension if not specified)')
def edit_profile(profile_path, format):
    """Edit an existing sender profile interactively."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect format from file extension if not specified
        if not format:
            if profile_path.endswith('.md'):
                format = 'markdown'
            elif profile_path.endswith('.json'):
                format = 'json'
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                format = 'yaml'
            else:
                console.print("[red]Could not detect profile format from file extension.[/red]")
                console.print("[red]Please specify format using --format option.[/red]")
                return 1
        
        # Load profile based on format
        try:
            if format == 'markdown':
                profile = manager.load_profile_from_markdown(profile_path)
            elif format == 'json':
                profile = manager.load_profile_from_json(profile_path)
            elif format == 'yaml':
                profile = manager.load_profile_from_yaml(profile_path)
        except FileNotFoundError:
            console.print(f"[red]Profile file not found: {profile_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Profile validation failed: {e}[/red]")
            return 1
        
        # Edit profile interactively
        console.print("[blue]Starting interactive profile editing...[/blue]")
        updated_profile = manager.edit_profile_interactively(profile)
        
        # Save updated profile
        if format == 'markdown':
            manager.save_profile_to_markdown(updated_profile, profile_path)
        elif format == 'json':
            manager.save_profile_to_json(updated_profile, profile_path)
        elif format == 'yaml':
            manager.save_profile_to_yaml(updated_profile, profile_path)
        
        console.print(f"[green]Profile updated and saved to: {profile_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('check-completeness')
@click.argument('profile_path')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Profile format (auto-detected from file extension if not specified)')
@click.option('--threshold', '-t', type=float, default=0.7,
              help='Completeness threshold (0.0-1.0, default: 0.7)')
def check_completeness(profile_path, format, threshold):
    """Check profile completeness against a threshold."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect format from file extension if not specified
        if not format:
            if profile_path.endswith('.md'):
                format = 'markdown'
            elif profile_path.endswith('.json'):
                format = 'json'
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                format = 'yaml'
            else:
                console.print("[red]Could not detect profile format from file extension.[/red]")
                console.print("[red]Please specify format using --format option.[/red]")
                return 1
        
        # Load profile based on format
        try:
            if format == 'markdown':
                profile = manager.load_profile_from_markdown(profile_path)
            elif format == 'json':
                profile = manager.load_profile_from_json(profile_path)
            elif format == 'yaml':
                profile = manager.load_profile_from_yaml(profile_path)
        except FileNotFoundError:
            console.print(f"[red]Profile file not found: {profile_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Profile validation failed: {e}[/red]")
            return 1
        
        # Check completeness
        completeness = profile.get_completeness_score()
        console.print(f"Profile: {profile.name}")
        console.print(f"Completeness Score: {completeness:.1%}")
        
        if completeness >= threshold:
            console.print(f"[green]✓ Profile meets or exceeds threshold of {threshold:.1%}[/green]")
            return 0
        else:
            console.print(f"[red]✗ Profile below threshold of {threshold:.1%}[/red]")
            
            # Get missing fields and suggestions
            missing_fields = profile.get_missing_fields()
            if missing_fields:
                console.print("[red]Missing required fields:[/red]")
                for field in missing_fields:
                    console.print(f"  [red]• {field}[/red]")
            
            suggestions = manager.get_profile_suggestions(profile)
            if suggestions:
                console.print("[yellow]Suggestions for improvement:[/yellow]")
                for suggestion in suggestions:
                    console.print(f"  [yellow]• {suggestion}[/yellow]")
            
            return 1
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('list')
@click.option('--directory', '-d', default='profiles', help='Directory to search for profiles')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml', 'all']), default='all',
              help='Filter profiles by format')
def list_profiles(directory, format):
    """List all available sender profiles."""
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            console.print(f"[red]Directory not found: {directory}[/red]")
            return 1
        
        # Define file extensions to search for based on format
        extensions = []
        if format == 'all' or format == 'markdown':
            extensions.append('.md')
        if format == 'all' or format == 'json':
            extensions.append('.json')
        if format == 'all' or format == 'yaml':
            extensions.extend(['.yaml', '.yml'])
        
        # Find all profile files
        profiles = []
        for ext in extensions:
            profiles.extend(list(path.glob(f'**/*{ext}')))
        
        if not profiles:
            console.print(f"[yellow]No profiles found in {directory}[/yellow]")
            return 0
        
        # Create a table to display profiles
        table = Table(title=f"Sender Profiles in {directory}")
        table.add_column("Name", style="cyan")
        table.add_column("Format", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Completeness", style="yellow")
        
        manager = SenderProfileManager()
        
        for profile_path in sorted(profiles):
            # Use string representation to avoid relative_to issues in tests
            rel_path = str(profile_path)
            
            # Determine format from extension
            if profile_path.suffix == '.md':
                profile_format = 'markdown'
            elif profile_path.suffix == '.json':
                profile_format = 'json'
            elif profile_path.suffix in ['.yaml', '.yml']:
                profile_format = 'yaml'
            else:
                continue  # Skip files with unknown extensions
            
            # Try to load the profile to get completeness score
            try:
                if profile_format == 'markdown':
                    profile = manager.load_profile_from_markdown(str(profile_path))
                elif profile_format == 'json':
                    profile = manager.load_profile_from_json(str(profile_path))
                elif profile_format == 'yaml':
                    profile = manager.load_profile_from_yaml(str(profile_path))
                
                completeness = f"{profile.get_completeness_score():.1%}"
                name = profile.name
            except Exception:
                completeness = "Error"
                name = profile_path.stem
            
            table.add_row(name, profile_format, rel_path, completeness)
        
        console.print(table)
        return 0
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('generate-template')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), default='markdown',
              help='Output format for the template')
@click.option('--output', '-o', required=True, help='Output file path')
def generate_template(format, output):
    """Generate a template file for a sender profile."""
    try:
        manager = SenderProfileManager()
        
        console.print(f"[blue]Generating {format} template...[/blue]")
        template_content = manager.create_profile_template(format)
        
        # Save template to file
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(template_content)
            
        console.print(f"[green]Template saved to: {output}[/green]")
        console.print("[yellow]Please edit the file with your information.[/yellow]")
        return 0
        
    except Exception as e:
        console.print(f"[red]Error generating template: {e}[/red]")
        return 1


@profile.command('analyze')
@click.argument('profile_path')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Profile format (auto-detected from file extension if not specified)')
@click.option('--target-role', '-r', help='Target role to analyze relevance for')
@click.option('--target-company', '-c', help='Target company to analyze relevance for')
def analyze_profile(profile_path, format, target_role, target_company):
    """Analyze a sender profile for relevance to target roles/companies."""
    try:
        manager = SenderProfileManager()
        
        # Auto-detect format from file extension if not specified
        if not format:
            if profile_path.endswith('.md'):
                format = 'markdown'
            elif profile_path.endswith('.json'):
                format = 'json'
            elif profile_path.endswith('.yaml') or profile_path.endswith('.yml'):
                format = 'yaml'
            else:
                console.print("[red]Could not detect profile format from file extension.[/red]")
                console.print("[red]Please specify format using --format option.[/red]")
                return 1
        
        # Load profile based on format
        try:
            if format == 'markdown':
                profile = manager.load_profile_from_markdown(profile_path)
            elif format == 'json':
                profile = manager.load_profile_from_json(profile_path)
            elif format == 'yaml':
                profile = manager.load_profile_from_yaml(profile_path)
        except FileNotFoundError:
            console.print(f"[red]Profile file not found: {profile_path}[/red]")
            return 1
        except ValidationError as e:
            console.print(f"[red]Profile validation failed: {e}[/red]")
            return 1
        
        # Display profile summary
        console.print(Panel(
            f"[bold]Name:[/bold] {profile.name}\n"
            f"[bold]Current Role:[/bold] {profile.current_role}\n"
            f"[bold]Experience:[/bold] {profile.years_experience} years\n"
            f"[bold]Location:[/bold] {profile.location or 'Not specified'}\n"
            f"[bold]Remote Preference:[/bold] {profile.remote_preference or 'Not specified'}\n"
            f"[bold]Completeness Score:[/bold] {profile.get_completeness_score():.1%}",
            title="Profile Summary",
            border_style="blue"
        ))
        
        # Display skills
        if profile.key_skills:
            console.print("\n[bold]Key Skills:[/bold]")
            for skill in profile.key_skills:
                console.print(f"  • {skill}")
        
        # Display target roles
        if profile.target_roles:
            console.print("\n[bold]Target Roles:[/bold]")
            for role in profile.target_roles:
                console.print(f"  • {role}")
        
        # Display notable achievements
        if profile.notable_achievements:
            console.print("\n[bold]Notable Achievements:[/bold]")
            for achievement in profile.notable_achievements:
                console.print(f"  • {achievement}")
        
        # If target role is specified, analyze relevance
        if target_role:
            console.print(f"\n[bold]Relevance Analysis for '{target_role}':[/bold]")
            relevant_experience = profile.get_relevant_experience(target_role, target_company or "")
            
            if relevant_experience:
                console.print("[green]Relevant experience and skills:[/green]")
                for item in relevant_experience:
                    console.print(f"  • {item}")
            else:
                console.print("[yellow]No directly relevant experience found for this role.[/yellow]")
                console.print("[yellow]Consider adding more specific skills or achievements related to this role.[/yellow]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1


@profile.command('import')
@click.argument('input_path')
@click.option('--format', '-f', type=click.Choice(['linkedin', 'resume', 'custom']), default='custom',
              help='Source format to import from')
@click.option('--output', '-o', required=True, help='Output profile path')
@click.option('--output-format', '-of', type=click.Choice(['markdown', 'json', 'yaml']), default='markdown',
              help='Output format for the profile')
def import_profile(input_path, format, output, output_format):
    """Import a profile from LinkedIn export or resume."""
    try:
        manager = SenderProfileManager()
        
        if not Path(input_path).exists():
            console.print(f"[red]Input file not found: {input_path}[/red]")
            return 1
        
        console.print(f"[blue]Importing profile from {format} format...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing import...", total=None)
            
            # Create a basic profile structure
            profile = SenderProfile(
                name="Imported Profile",
                current_role="Software Engineer",  # Default value to avoid validation errors
                years_experience=0,
                key_skills=[],
                experience_summary="",
                value_proposition=""
            )
            
            # Read input file
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process based on format
            if format == 'linkedin':
                # Basic LinkedIn export parsing (simplified)
                # In a real implementation, this would be more sophisticated
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('Name:') and i+1 < len(lines):
                        profile.name = lines[i+1].strip()
                    elif line.startswith('Headline:') and i+1 < len(lines):
                        profile.current_role = lines[i+1].strip()
                    elif line.startswith('Summary:') and i+1 < len(lines):
                        profile.experience_summary = lines[i+1].strip()
                    elif line.startswith('Skills:'):
                        skills_section = []
                        j = i + 1
                        while j < len(lines) and lines[j].strip() and not lines[j].strip().endswith(':'):
                            skills_section.append(lines[j].strip())
                            j += 1
                        profile.key_skills = skills_section
            
            elif format == 'resume':
                # Basic resume parsing (simplified)
                # In a real implementation, this would use NLP or other techniques
                if 'experience' in content.lower():
                    profile.experience_summary = "Experience extracted from resume."
                
                # Extract skills (very basic approach)
                skill_keywords = ['python', 'javascript', 'java', 'c++', 'react', 'node', 'aws', 'azure', 
                                 'docker', 'kubernetes', 'machine learning', 'data science', 'agile']
                found_skills = []
                for skill in skill_keywords:
                    if skill.lower() in content.lower():
                        found_skills.append(skill.title())
                
                profile.key_skills = found_skills
            
            else:  # custom
                # For custom format, just create a basic template
                profile.name = Path(input_path).stem
                profile.experience_summary = "Imported from custom format."
            
            progress.update(task, description="Import completed!")
        
        # Save profile to output file
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_format == 'markdown':
            manager.save_profile_to_markdown(profile, output)
        elif output_format == 'json':
            manager.save_profile_to_json(profile, output)
        elif output_format == 'yaml':
            manager.save_profile_to_yaml(profile, output)
        
        console.print(f"[green]Profile imported and saved to: {output}[/green]")
        return 0
        
    except Exception as e:
        console.print(f"[red]Error importing profile: {e}[/red]")
        return 1


@profile.command('bulk-validate')
@click.option('--directory', '-d', default='profiles', help='Directory to search for profiles')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml', 'all']), default='all',
              help='Filter profiles by format')
@click.option('--threshold', '-t', type=float, default=0.7,
              help='Completeness threshold (0.0-1.0, default: 0.7)')
def bulk_validate(directory, format, threshold):
    """Validate multiple profiles in a directory."""
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            console.print(f"[red]Directory not found: {directory}[/red]")
            return 1
        
        # Define file extensions to search for based on format
        extensions = []
        if format == 'all' or format == 'markdown':
            extensions.append('.md')
        if format == 'all' or format == 'json':
            extensions.append('.json')
        if format == 'all' or format == 'yaml':
            extensions.extend(['.yaml', '.yml'])
        
        # Find all profile files
        profiles = []
        for ext in extensions:
            profiles.extend(list(path.glob(f'**/*{ext}')))
        
        if not profiles:
            console.print(f"[yellow]No profiles found in {directory}[/yellow]")
            return 0
        
        # Create a table to display validation results
        table = Table(title=f"Profile Validation Results")
        table.add_column("Status", style="cyan")
        table.add_column("Name", style="blue")
        table.add_column("Path", style="green")
        table.add_column("Completeness", style="yellow")
        table.add_column("Issues", style="red")
        
        manager = SenderProfileManager()
        
        passed_count = 0
        failed_count = 0
        error_count = 0
        
        for profile_path in sorted(profiles):
            # Use string representation to avoid relative_to issues in tests
            rel_path = str(profile_path)
            
            # Determine format from extension
            if profile_path.suffix == '.md':
                profile_format = 'markdown'
            elif profile_path.suffix == '.json':
                profile_format = 'json'
            elif profile_path.suffix in ['.yaml', '.yml']:
                profile_format = 'yaml'
            else:
                continue  # Skip files with unknown extensions
            
            # Try to load and validate the profile
            try:
                if profile_format == 'markdown':
                    profile = manager.load_profile_from_markdown(str(profile_path))
                elif profile_format == 'json':
                    profile = manager.load_profile_from_json(str(profile_path))
                elif profile_format == 'yaml':
                    profile = manager.load_profile_from_yaml(str(profile_path))
                
                completeness = profile.get_completeness_score()
                is_valid, issues = manager.validate_profile(profile)
                
                if is_valid and completeness >= threshold:
                    status = "[green]✓ Passed[/green]"
                    issues_text = ""
                    passed_count += 1
                else:
                    status = "[red]✗ Failed[/red]"
                    issues_list = []
                    if not is_valid:
                        issues_list.extend(issues)
                    if completeness < threshold:
                        issues_list.append(f"Completeness below threshold ({completeness:.1%} < {threshold:.1%})")
                    issues_text = ", ".join(issues_list)
                    failed_count += 1
                
                table.add_row(status, profile.name, rel_path, f"{completeness:.1%}", issues_text)
                
            except Exception as e:
                status = "[red]✗ Error[/red]"
                error_count += 1
                table.add_row(status, profile_path.stem, rel_path, "N/A", str(e))
        
        console.print(table)
        
        # Print summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"Total profiles: {len(profiles)}")
        console.print(f"[green]Passed: {passed_count}[/green]")
        console.print(f"[red]Failed: {failed_count}[/red]")
        if error_count > 0:
            console.print(f"[red]Errors: {error_count}[/red]")
        
        # Return appropriate exit code
        if failed_count > 0 or error_count > 0:
            return 1
        return 0
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1