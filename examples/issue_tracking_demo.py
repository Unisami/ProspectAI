#!/usr/bin/env python3
"""
Demo script for the Issue Tracking System.
Shows how users can interact with the issue tracking functionality.
"""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def demo_user_perspective():
    """Demo from a user's perspective (both techie and non-techie)."""
    
    console.print(Panel.fit(
        "[bold green]🐛 Issue Tracking System Demo[/bold green]\n\n"
        "This demo shows how users can easily report issues\n"
        "and track them without complexity.",
        border_style="green"
    ))
    
    console.print("\n[bold cyan]📝 User Scenarios:[/bold cyan]\n")
    
    # Scenario 1: Non-techie user
    console.print("[bold]1. Non-technical user encounters an error:[/bold]")
    console.print("   [dim]User runs a command and gets an error[/dim]")
    console.print("   [yellow]💡 System suggests: python cli.py report-issue[/yellow]")
    console.print("   [green]✅ User reports: \"Email generation failed for me\"[/green]")
    console.print("   [blue]📝 Gets issue ID: #12345[/blue]")
    console.print()
    
    # Scenario 2: Technical user
    console.print("[bold]2. Technical user wants a feature:[/bold]")
    console.print("   [green]✅ User reports: \"Need better LinkedIn search\" --category Improvement[/green]")
    console.print("   [blue]📝 Gets issue ID: #12346[/blue]")
    console.print()
    
    # Scenario 3: User needs help
    console.print("[bold]3. User needs help with setup:[/bold]")
    console.print("   [green]✅ User reports: \"How do I configure API keys?\" --category Question[/green]")
    console.print("   [blue]📝 Gets issue ID: #12347[/blue]")
    console.print()


def demo_cli_commands():
    """Demo the CLI commands available."""
    
    console.print("[bold cyan]🔧 Available CLI Commands:[/bold cyan]\n")
    
    # Create commands table
    table = Table()
    table.add_column("Command", style="cyan", width=25)
    table.add_column("Description", style="white", width=35)
    table.add_column("Example", style="green", width=40)
    
    table.add_row(
        "setup-issues",
        "Set up Issues database",
        "python cli.py setup-issues"
    )
    
    table.add_row(
        "report-issue",
        "Report a bug, question, or request",
        'python cli.py report-issue "Issue description"'
    )
    
    table.add_row(
        "report-issue --interactive",
        "Interactive issue reporting",
        "python cli.py report-issue --interactive"
    )
    
    table.add_row(
        "list-issues",
        "View your reported issues",
        "python cli.py list-issues"
    )
    
    table.add_row(
        "list-issues --status",
        "Filter issues by status",
        "python cli.py list-issues --status Open"
    )
    
    console.print(table)
    console.print()


def demo_categories():
    """Demo the issue categories."""
    
    console.print("[bold cyan]📂 Issue Categories:[/bold cyan]\n")
    
    # Create categories table
    table = Table()
    table.add_column("Category", style="blue", width=15)
    table.add_column("Description", style="white", width=30)
    table.add_column("Example", style="green", width=35)
    
    table.add_row(
        "🐛 Bug",
        "Something doesn't work",
        '"Email generation failed"'
    )
    
    table.add_row(
        "💡 Improvement",
        "Enhancement request",
        '"Better UX for setup process"'
    )
    
    table.add_row(
        "❓ Question",
        "Need help or clarification",
        '"How do I configure LinkedIn?"'
    )
    
    table.add_row(
        "🔧 Setup",
        "Installation/config issues",
        '"Cannot connect to Notion API"'
    )
    
    console.print(table)
    console.print()


def demo_integration():
    """Demo how it integrates with existing error handling."""
    
    console.print("[bold cyan]🔗 Integration with Error Handling:[/bold cyan]\n")
    
    console.print("The system automatically suggests issue reporting when errors occur:")
    console.print()
    console.print("[red]❌ Campaign failed: API timeout error[/red]")
    console.print("[yellow]💡 Had an issue? Report it: python cli.py report-issue[/yellow]")
    console.print()
    console.print("[red]❌ Setup failed: Invalid configuration[/red]")
    console.print("[yellow]💡 Had an issue? Report it: python cli.py report-issue[/yellow]")
    console.print()


def demo_notion_integration():
    """Demo how it works with Notion."""
    
    console.print("[bold cyan]📊 Notion Integration:[/bold cyan]\n")
    
    console.print("✅ Issues are stored in a dedicated Notion database")
    console.print("✅ Automatic context capture (Python version, platform, etc.)")
    console.print("✅ Categorization and status tracking")
    console.print("✅ Simple issue IDs for easy reference")
    console.print("✅ Developer dashboard for issue management")
    console.print()


def demo_developer_perspective():
    """Demo from a developer's perspective."""
    
    console.print("[bold cyan]👨‍💻 Developer Benefits:[/bold cyan]\n")
    
    console.print("🔍 **Centralized Feedback Collection**")
    console.print("   • All user issues in one Notion database")
    console.print("   • Automatic context capture for debugging")
    console.print("   • Categorized for easy triage")
    console.print()
    
    console.print("⚡ **Low Maintenance**")
    console.print("   • No separate issue tracking system needed")
    console.print("   • Uses existing Notion infrastructure")
    console.print("   • Simple CLI integration")
    console.print()
    
    console.print("📈 **Better User Experience**")
    console.print("   • Easy for users to report issues")
    console.print("   • Immediate feedback with issue IDs")
    console.print("   • Suggestions appear during errors")
    console.print()


def main():
    """Run the demo."""
    console.print("[bold]🚀 Welcome to the Issue Tracking System Demo![/bold]\n")
    
    demo_user_perspective()
    demo_cli_commands()
    demo_categories()
    demo_integration()
    demo_notion_integration()
    demo_developer_perspective()
    
    console.print(Panel.fit(
        "[bold green]🎯 Key Benefits[/bold green]\n\n"
        "✅ Simple and lightweight\n"
        "✅ No over-complexity\n"
        "✅ Works for both techie and non-techie users\n"
        "✅ Integrates seamlessly with existing CLI\n"
        "✅ Provides immediate value for feedback collection\n"
        "✅ Easy to maintain and extend",
        border_style="green"
    ))
    
    console.print("\n[bold cyan]🚀 Ready to test?[/bold cyan]")
    console.print("[dim]Try: python cli.py --dry-run report-issue \"Demo issue\"[/dim]")


if __name__ == "__main__":
    main()