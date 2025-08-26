#!/usr/bin/env python3
"""
Setup script for creating the Notion progress dashboard.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.panel import Panel

from utils.config import Config
from services.notion_manager import NotionDataManager
from utils.logging_config import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def setup_dashboard():
    """Set up the Notion progress dashboard."""
    console.print(Panel.fit(
        "[bold blue]Job Prospect Automation Dashboard Setup[/bold blue]",
        border_style="blue"
    ))
    
    try:
        # Load configuration
        console.print("[yellow]Loading configuration...[/yellow]")
        config = Config.from_env()
        
        # Initialize Notion manager
        console.print("[yellow]Connecting to Notion...[/yellow]")
        notion_manager = NotionDataManager(config)
        
        # Create dashboard with simple progress indicator (Windows-compatible)
        console.print("[blue]Creating dashboard components...[/blue]")
        
        # Create main prospect database if needed
        console.print("[blue]Step 1/3: Creating prospect database...[/blue]")
        if not notion_manager.database_id:
            prospect_db_id = notion_manager.create_prospect_database()
            console.print(f"[green]Created prospect database: {prospect_db_id}[/green]")
        else:
            console.print(f"[green]Using existing prospect database: {notion_manager.database_id}[/green]")
        
        # Create campaign dashboard
        console.print("[blue]Step 2/3: Creating campaign dashboard...[/blue]")
        dashboard_info = notion_manager.create_campaign_dashboard()
        
        # Initialize system status
        console.print("[blue]Step 3/3: Initializing system status...[/blue]")
        _initialize_system_status(notion_manager, dashboard_info["status_db"])
        
        # Display results
        console.print("\n[bold green]Dashboard setup completed successfully![/bold green]")
        console.print("\n[bold]Dashboard Components:[/bold]")
        console.print(f"Main Dashboard: https://notion.so/{dashboard_info['dashboard_id'].replace('-', '')}")
        console.print(f"Campaign Runs: https://notion.so/{dashboard_info['campaigns_db'].replace('-', '')}")
        console.print(f"Processing Log: https://notion.so/{dashboard_info['logs_db'].replace('-', '')}")
        console.print(f"System Status: https://notion.so/{dashboard_info['status_db'].replace('-', '')}")
        console.print(f"Daily Analytics: https://notion.so/{dashboard_info['analytics_db'].replace('-', '')}")
        console.print(f"Email Queue: https://notion.so/{dashboard_info['email_queue_db'].replace('-', '')}")
        
        # Save dashboard IDs to config
        console.print(f"\n[yellow]Add these to your config.yaml:[/yellow]")
        console.print(f"DASHBOARD_ID: '{dashboard_info['dashboard_id']}'")
        console.print(f"CAMPAIGNS_DB_ID: '{dashboard_info['campaigns_db']}'")
        console.print(f"LOGS_DB_ID: '{dashboard_info['logs_db']}'")
        console.print(f"STATUS_DB_ID: '{dashboard_info['status_db']}'")
        console.print(f"ANALYTICS_DB_ID: '{dashboard_info['analytics_db']}'")
        console.print(f"EMAIL_QUEUE_DB_ID: '{dashboard_info['email_queue_db']}'")
        
        console.print(f"\n[green]Enhanced dashboard with analytics and email queue ready![/green]")
        
        return dashboard_info
        
    except Exception as e:
        console.print(f"[red]Dashboard setup failed: {str(e)}[/red]")
        logger.error(f"Dashboard setup failed: {str(e)}")
        return None


def _initialize_system_status(notion_manager: NotionDataManager, status_db_id: str):
    """Initialize system status entries."""
    components = [
        ("ProductHunt Scraper", "Healthy", "Ready for company discovery"),
        ("AI Parser", "Healthy", "GPT-4 integration active"),
        ("Email Finder", "Healthy", "Hunter.io API connected"),
        ("LinkedIn Scraper", "Healthy", "Profile extraction ready"),
        ("Email Generator", "Healthy", "AI email generation ready"),
        ("Email Sender", "Healthy", "Resend API connected"),
        ("Notion Manager", "Healthy", "Database connections active")
    ]
    
    for component, status, details in components:
        notion_manager.update_system_status(
            status_db_id=status_db_id,
            component=component,
            status=status,
            details=details,
            success_rate=1.0,
            error_count=0
        )


if __name__ == "__main__":
    setup_logging(log_level="INFO")
    
    console.print("[blue]Setting up your Notion progress dashboard...[/blue]")
    
    dashboard_info = setup_dashboard()
    
    if dashboard_info:
        sys.exit(0)
    else:
        sys.exit(1)