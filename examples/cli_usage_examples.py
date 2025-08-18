#!/usr/bin/env python3
"""
Examples demonstrating CLI usage for the Job Prospect Automation system.
"""

import subprocess
import os
from pathlib import Path


def run_command(command, description):
    """Run a CLI command and display the result."""
    print(f"\n{'='*60}")
    print(f"Example: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            print("Output:")
            print(result.stdout)
        
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            
        print(f"Exit code: {result.returncode}")
        
    except subprocess.TimeoutExpired:
        print("Command timed out")
    except Exception as e:
        print(f"Error running command: {e}")


def main():
    """Run CLI usage examples."""
    print("Job Prospect Automation CLI - Usage Examples")
    print("=" * 60)
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    # Example 1: Show help
    run_command(
        "python cli.py --help",
        "Display CLI help and available commands"
    )
    
    # Example 2: Initialize configuration
    run_command(
        "python cli.py init-config example-config.yaml",
        "Create a configuration template file"
    )
    
    # Example 3: Dry-run discovery
    run_command(
        "python cli.py --dry-run discover --limit 5",
        "Test discovery pipeline without API calls"
    )
    
    # Example 4: Dry-run company processing
    run_command(
        "python cli.py --dry-run process-company 'Acme Corp' --domain acme.com",
        "Test company processing without API calls"
    )
    
    # Example 5: Dry-run email generation
    run_command(
        "python cli.py --dry-run generate-emails --prospect-ids '1,2,3' --template cold_outreach",
        "Test email generation without API calls"
    )
    
    # Example 6: Show status (dry-run)
    run_command(
        "python cli.py --dry-run status",
        "Check system status without API calls"
    )
    
    # Example 7: Show batch history (dry-run)
    run_command(
        "python cli.py --dry-run batch-history",
        "View batch processing history without API calls"
    )
    
    # Example 8: Using configuration file
    run_command(
        "python cli.py --config example-config.yaml --dry-run discover --limit 3",
        "Use configuration file with discovery command"
    )
    
    # Example 9: Verbose mode
    run_command(
        "python cli.py --verbose --dry-run status",
        "Run with verbose logging enabled"
    )
    
    # Example 10: Help for specific command
    run_command(
        "python cli.py discover --help",
        "Show help for the discover command"
    )
    
    print(f"\n{'='*60}")
    print("Examples completed!")
    print("Note: All examples used --dry-run mode to avoid actual API calls.")
    print("Remove --dry-run flag and configure API keys for real usage.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()