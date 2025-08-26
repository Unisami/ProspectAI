"""
Setup script for creating the Issues database in Notion.
Extends the existing dashboard setup to include issue tracking.
"""
import sys
import os
import logging
from typing import Optional, Dict, Any

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from notion_client import Client
from notion_client.errors import APIResponseError
from rich.console import Console
from rich.panel import Panel

from utils.config import Config

console = Console()
logger = logging.getLogger(__name__)


def create_issues_database(notion_client: Client, parent_page_id: str) -> str:
    """
    Create the Issues database in Notion.
    
    Args:
        notion_client: Authenticated Notion client
        parent_page_id: ID of the parent page (dashboard)
        
    Returns:
        Database ID of the created issues database
        
    Raises:
        Exception: If database creation fails
    """
    try:
        # Define the database schema
        database_properties = {
            "Title": {"title": {}},
            "Description": {"rich_text": {}},
            "Category": {
                "select": {
                    "options": [
                        {"name": "Bug", "color": "red"},
                        {"name": "Improvement", "color": "blue"},
                        {"name": "Question", "color": "yellow"},
                        {"name": "Setup", "color": "green"}
                    ]
                }
            },
            "Status": {
                "select": {
                    "options": [
                        {"name": "Open", "color": "red"},
                        {"name": "In Progress", "color": "yellow"},
                        {"name": "Resolved", "color": "green"},
                        {"name": "Closed", "color": "gray"}
                    ]
                }
            },
            "Created": {"date": {}},
            "Issue ID": {"rich_text": {}},
            "Context": {"rich_text": {}},
            "Priority": {
                "select": {
                    "options": [
                        {"name": "Low", "color": "gray"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "High", "color": "orange"},
                        {"name": "Critical", "color": "red"}
                    ]
                }
            }
        }
        
        # Create the database
        response = notion_client.databases.create(
            parent={"page_id": parent_page_id},
            title=[{"type": "text", "text": {"content": "🐛 Issues & Feedback"}}],
            properties=database_properties,
            icon={"type": "emoji", "emoji": "🐛"},
            description=[
                {
                    "type": "text",
                    "text": {
                        "content": "Track user-reported issues, bugs, and feature requests for the ProspectAI system"
                    }
                }
            ]
        )
        
        database_id = response["id"]
        logger.info(f"Issues database created successfully: {database_id}")
        
        return database_id
        
    except APIResponseError as e:
        logger.error(f"Notion API error creating issues database: {e}")
        raise Exception(f"Failed to create issues database: {e}")
    except Exception as e:
        logger.error(f"Unexpected error creating issues database: {e}")
        raise Exception(f"Failed to create issues database: {e}")


def setup_issues_database(config: Optional[Config] = None) -> Dict[str, Any]:
    """
    Set up the issues database in the existing Notion dashboard.
    
    Args:
        config: Configuration object (if None, loads from environment)
        
    Returns:
        Dictionary with setup results
        
    Raises:
        Exception: If setup fails
    """
    if not config:
        config = Config.from_env()
    
    # Check if we have required configuration
    if not config.notion_token:
        raise Exception("Notion token not configured. Please set NOTION_TOKEN environment variable.")
    
    if not config.dashboard_id:
        raise Exception("Dashboard not setup. Please run 'python cli.py setup-dashboard' first.")
    
    try:
        # Initialize Notion client
        client = Client(auth=config.notion_token)
        
        console.print("[blue]Creating Issues database in Notion...[/blue]")
        
        # Create the issues database
        issues_db_id = create_issues_database(client, config.dashboard_id)
        
        # Update .env file with new database ID
        _update_env_with_issues_db(issues_db_id)
        
        console.print("[green]✅ Issues database created successfully![/green]")
        console.print(f"[dim]Database ID: {issues_db_id}[/dim]")
        
        # Create a sample issue to demonstrate functionality
        console.print("[blue]Creating sample issue...[/blue]")
        _create_sample_issue(client, issues_db_id)
        
        return {
            "success": True,
            "issues_database_id": issues_db_id,
            "dashboard_url": f"https://notion.so/{config.dashboard_id.replace('-', '')}",
            "issues_url": f"https://notion.so/{issues_db_id.replace('-', '')}"
        }
        
    except Exception as e:
        logger.error(f"Issues database setup failed: {e}")
        raise


def _update_env_with_issues_db(database_id: str) -> None:
    """Update .env file with issues database ID."""
    try:
        env_file = ".env"
        
        # Read existing content
        lines = []
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
        
        # Look for existing ISSUES_DATABASE_ID line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("ISSUES_DATABASE_ID="):
                lines[i] = f"ISSUES_DATABASE_ID={database_id}\\n"
                updated = True
                break
        
        # Add new line if not found
        if not updated:
            lines.append(f"ISSUES_DATABASE_ID={database_id}\\n")
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        console.print(f"[green]Updated .env file with ISSUES_DATABASE_ID[/green]")
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not update .env file: {e}[/yellow]")


def _create_sample_issue(client: Client, database_id: str) -> None:
    """Create a sample issue to demonstrate the system."""
    try:
        from datetime import datetime
        
        properties = {
            "Title": {
                "title": [{"type": "text", "text": {"content": "Welcome to Issue Tracking!"}}]
            },
            "Description": {
                "rich_text": [{
                    "type": "text", 
                    "text": {"content": "This is a sample issue to demonstrate the issue tracking system. You can delete this after testing."}
                }]
            },
            "Category": {
                "select": {"name": "Improvement"}
            },
            "Status": {
                "select": {"name": "Open"}
            },
            "Created": {
                "date": {"start": datetime.now().isoformat()}
            },
            "Issue ID": {
                "rich_text": [{"type": "text", "text": {"content": "#SAMPLE"}}]
            },
            "Context": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": '{"source": "setup_script", "type": "sample", "version": "1.0"}'}
                }]
            },
            "Priority": {
                "select": {"name": "Low"}
            }
        }
        
        client.pages.create(
            parent={"database_id": database_id},
            properties=properties
        )
        
        console.print("[green]✅ Sample issue created[/green]")
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not create sample issue: {e}[/yellow]")


def main():
    """Main entry point for the setup script."""
    try:
        console.print(Panel.fit(
            "[bold green]🐛 Setting Up Issues Database[/bold green]\\n\\n"
            "This will create an Issues database in your existing Notion dashboard\\n"
            "to track user feedback, bugs, and feature requests.",
            border_style="green"
        ))
        
        # Load configuration
        config = Config.from_env()
        
        # Setup issues database
        result = setup_issues_database(config)
        
        # Show success message
        console.print(Panel.fit(
            f"[bold green]🎉 Issues Database Setup Complete![/bold green]\\n\\n"
            f"📊 Dashboard: {result['dashboard_url']}\\n"
            f"🐛 Issues Database: {result['issues_url']}\\n\\n"
            f"[cyan]Quick Test:[/cyan]\\n"
            f"• python cli.py report-issue \"Test issue\"\\n"
            f"• python cli.py list-issues",
            border_style="green"
        ))
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Setup failed: {str(e)}[/red]")
        console.print(f"[yellow]💡 Need help? Report this: python cli.py report-issue \"Setup failed: {str(e)}\"[/yellow]")
        return 1


if __name__ == "__main__":
    exit(main())