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
            
            # Use sys.exit(1) instead of return 1 for Click testing compatibility
            import sys
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        return 1