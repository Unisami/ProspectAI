#!/usr/bin/env python3
"""
Command-line interface for the Job Prospect Automation system.
"""
import sys
import os
import json
from pathlib import Path
from typing import (
    Optional,
    Dict,
    Any,
    List
)
from datetime import datetime

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn
)
# Import Windows-compatible progress for cross-platform compatibility
from utils.windows_progress import replace_spinner_progress
from rich.panel import Panel
# Platform detection utility
import platform


def get_platform_safe_text(text: str, emoji: str = "", fallback: str = "") -> str:
    """Get platform-safe text with optional emoji for Windows compatibility.
    
    Args:
        text: The main text to display
        emoji: Emoji to prepend (will be omitted on Windows)
        fallback: Fallback text for Windows (without emoji)
        
    Returns:
        Platform-appropriate formatted text
    """
    if platform.system().lower() == "windows":
        # On Windows, avoid Unicode emojis that cause encoding issues
        return fallback if fallback else text
    else:
        # On other platforms, include emojis
        return f"{emoji} {text}" if emoji else text


def get_platform_safe_emoji_text(text: str, check_emoji: str = "✅", cross_emoji: str = "❌", 
                                light_emoji: str = "💡", phone_emoji: str = "📱", 
                                link_emoji: str = "🔗", target_emoji: str = "🎯",
                                fallback_text: str = "") -> str:
    """Get platform-safe text with multiple emojis for Windows compatibility.
    
    Args:
        text: The main text to display
        check_emoji: Checkmark emoji
        cross_emoji: Cross emoji
        light_emoji: Light bulb emoji
        phone_emoji: Phone emoji
        link_emoji: Link emoji
        target_emoji: Target emoji
        fallback_text: Complete fallback text for Windows
        
    Returns:
        Platform-appropriate formatted text
    """
    if platform.system().lower() == "windows":
        # On Windows, avoid Unicode emojis that cause encoding issues
        return fallback_text if fallback_text else text
    else:
        # Replace emoji placeholders with actual emojis
        result = text.replace("{check}", check_emoji)
        result = result.replace("{cross}", cross_emoji)
        result = result.replace("{light}", light_emoji)
        result = result.replace("{phone}", phone_emoji)
        result = result.replace("{link}", link_emoji)
        result = result.replace("{target}", target_emoji)
        return result


# Import CLI profile commands
try:
    from scripts.cli_profile_commands import profile
except ImportError:
    profile = None
    print("Warning: cli_profile_commands import failed")

# Import setup dashboard function
try:
    from scripts.setup_dashboard import setup_dashboard as setup_func
except ImportError:
    setup_func = None

# Import setup issues database function
try:
    from scripts.setup_issues_database import setup_issues_database
except ImportError:
    setup_issues_database = None

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging
from models.data_models import CompanyData, ValidationError, EmailTemplate
from services.sender_profile_manager import SenderProfileManager
from services.notification_manager import NotificationManager
from services.ai_provider_manager import get_provider_manager, AIProviderManager
from services.issue_reporter import IssueReporter





# Initialize console with Windows compatibility
if platform.system().lower() == "windows":
    # Try to handle Windows encoding issues
    try:
        # Attempt to use UTF-8 encoding if available
        console = Console(force_terminal=True, legacy_windows=False)
    except Exception:
        # Fallback to basic console without Unicode characters
        console = Console(force_terminal=True, no_color=True)
else:
    console = Console()


def suggest_issue_report(error_type: str = "error", error_message: str = "") -> None:
    """
    Suggest issue reporting for certain types of errors.
    
    Args:
        error_type: Type of error (error, timeout, config, api)
        error_message: The actual error message
    """
    # Only suggest for certain error types that users might want to report
    suggest_types = {
        "config": "Configuration or setup issues",
        "api": "API or service connectivity problems", 
        "timeout": "Timeout or performance issues",
        "validation": "Data validation problems",
        "unexpected": "Unexpected errors or crashes"
    }
    
    if error_type in suggest_types or "timeout" in error_message.lower() or "api" in error_message.lower():
        console.print(f"[yellow]💡 Had an issue? Report it: python cli.py report-issue[/yellow]")


class CLIConfig:
    """Extended configuration class for CLI operations."""
    
    def __init__(self, config_file: Optional[str] = None, dry_run: bool = False):
        self.dry_run = dry_run
        self.config_file = config_file
        self.base_config = self._load_config()
    
    def _load_config(self) -> Config:
        """Load configuration from file or environment."""
        if self.config_file and os.path.exists(self.config_file):
            return self._load_from_file()
        return Config.from_env()
    
    def _load_from_file(self) -> Config:
        """Load configuration from YAML or JSON file."""
        with open(self.config_file, 'r') as f:
            if self.config_file.endswith('.yaml') or self.config_file.endswith('.yml'):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        # Set environment variables from config file
        for key, value in data.items():
            os.environ[key.upper()] = str(value)
        
        return Config.from_env()


def setup_cli_logging(verbose: bool = False):
    """Setup logging for CLI operations."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level=log_level)
@click.group()
@click.option('--config', '-c', help='Configuration file path (YAML or JSON)')
@click.option('--dry-run', is_flag=True, help='Run in dry-run mode (no actual API calls)')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, dry_run, verbose):
    """>> Job Prospect Automation CLI - Complete automation workflow in one command!
    
    QUICK COMMANDS:
    • quick-start     - Complete setup + first campaign (beginners)
    • run-campaign    - Full workflow: discovery -> emails -> analytics
    • discover        - Discovery only (advanced users)
    
    SETUP COMMANDS:
    • setup-dashboard - One-time Notion dashboard setup
    • validate-config - Check your configuration
    """
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config
    ctx.obj['dry_run'] = dry_run
    ctx.obj['verbose'] = verbose
    
    setup_cli_logging(verbose)
    
    if dry_run:
        console.print("[yellow]Running in DRY-RUN mode - no actual API calls will be made[/yellow]")

# Add the profile command group to the main CLI if available
if profile:
    cli.add_command(profile)


@cli.command('setup-dashboard')
@click.pass_context
def setup_dashboard(ctx):
    """Set up the Notion progress dashboard."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would set up Notion progress dashboard[/yellow]")
            return
        
        
        console.print("[blue]Setting up Notion progress dashboard...[/blue]")
        dashboard_info = setup_func()
        
        if dashboard_info:
            console.print("[green]✅ Dashboard setup completed successfully![/green]")
            return 0
        else:
            console.print("[red]❌ Dashboard setup failed[/red]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Error setting up dashboard: {str(e)}[/red]")
        suggest_issue_report("config", str(e))
        return 1


@cli.command('campaign-status')
@click.pass_context
def campaign_status(ctx):
    """Show current campaign status and progress."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        controller = ProspectAutomationController(cli_config.base_config)
        
        progress = controller.get_campaign_progress()
        
        if not progress:
            console.print("[yellow]No active campaign found[/yellow]")
            return
        
        # Create progress table
        table = Table(title="Campaign Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Campaign Name", progress['name'])
        table.add_row("Status", progress['status'])
        table.add_row("Progress", f"{progress['progress_percentage']:.1f}%")
        table.add_row("Current Step", progress['current_step'])
        table.add_row("Current Company", progress.get('current_company', 'N/A'))
        table.add_row("Companies Processed", f"{progress['companies_processed']}/{progress['companies_target']}")
        table.add_row("Prospects Found", str(progress['prospects_found']))
        table.add_row("Emails Generated", str(progress['emails_generated']))
        table.add_row("Success Rate", f"{progress['success_rate']:.1f}%")
        table.add_row("Errors", str(progress['error_count']))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting campaign status: {str(e)}[/red]")
        return 1


@cli.command('daily-summary')
@click.pass_context
def daily_summary(ctx):
    """Create or update today's daily analytics summary."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would create daily summary[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        analytics_db_id = cli_config.base_config.analytics_db_id
        if not analytics_db_id:
            console.print("[red]Analytics database not configured. Run setup-dashboard first.[/red]")
            return 1
        
        success = controller.create_daily_summary(analytics_db_id)
        
        if success:
            console.print("[green]✅ Daily summary updated successfully![/green]")
        else:
            console.print("[red]❌ Failed to update daily summary[/red]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Error creating daily summary: {str(e)}[/red]")
        return 1


@cli.command('email-queue')
@click.option('--action', type=click.Choice(['list', 'approve', 'reject']), default='list',
              help='Action to perform on email queue')
@click.option('--email-id', help='Email ID for approve/reject actions')
@click.pass_context
def email_queue(ctx, action, email_id):
    """Manage the email approval queue."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would {action} email queue[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        email_queue_db_id = cli_config.base_config.email_queue_db_id
        if not email_queue_db_id:
            console.print("[red]Email queue database not configured. Run setup-dashboard first.[/red]")
            return 1
        
        if action == 'list':
            # List pending emails
            pending_emails = controller.check_email_approvals(email_queue_db_id)
            
            if not pending_emails:
                console.print("[yellow]No emails pending approval[/yellow]")
                return
            
            table = Table(title="Email Approval Queue")
            table.add_column("Email ID", style="cyan")
            table.add_column("Prospect", style="green")
            table.add_column("Company", style="blue")
            table.add_column("Subject", style="yellow")
            
            for email in pending_emails:
                table.add_row(
                    email['email_id'][:20] + "...",
                    email['prospect_name'],
                    email['company'],
                    email['subject'][:50] + "..." if len(email['subject']) > 50 else email['subject']
                )
            
            console.print(table)
            
        elif action in ['approve', 'reject']:
            if not email_id:
                console.print("[red]Email ID required for approve/reject actions[/red]")
                return 1
            
            # Find email by ID and update status
            # This would need to be implemented with proper email ID lookup
            console.print(f"[yellow]Email {action} functionality coming soon![/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error managing email queue: {str(e)}[/red]")
        return 1


@cli.command('test-notifications')
@click.pass_context
def test_notifications(ctx):
    """Test all notification types to see how they appear in Notion."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would test all notification types[/yellow]")
            return
        
        
        controller = ProspectAutomationController(cli_config.base_config)
        notification_manager = NotificationManager(cli_config.base_config, controller.notion_manager)
        
        console.print("[blue]Testing all notification types...[/blue]")
        
        # Test campaign completion (success)
        success_data = {
            'name': 'Test Success Campaign',
            'companies_processed': 5,
            'prospects_found': 12,
            'success_rate': 0.95,
            'duration_minutes': 15.5,
            'status': 'Completed'
        }
        notification_manager.send_campaign_completion_notification(success_data)
        console.print("[green]✅ Campaign completion notification sent[/green]")
        
        # Test daily summary
        daily_stats = controller._calculate_daily_stats()
        notification_manager.send_daily_summary_notification(daily_stats)
        console.print("[green]✅ Daily summary notification sent[/green]")
        
        # Test error alert
        error_data = {
            'component': 'Test Component',
            'error_message': 'This is a test error for demonstration',
            'campaign_name': 'Test Campaign',
            'company_name': 'Test Company'
        }
        notification_manager.send_error_alert(error_data)
        console.print("[green]✅ Error alert notification sent[/green]")
        
        console.print(f"\n[cyan]Check your Daily Analytics database for notification sub-pages![/cyan]")
        console.print(f"[dim]Analytics DB: https://notion.so/{cli_config.base_config.analytics_db_id.replace('-', '') if cli_config.base_config.analytics_db_id else 'not-configured'}[/dim]")
        
        console.print(f"\n[yellow]💡 To get push notifications:[/yellow]")
        console.print(f"1. Go to the notification pages in Daily Analytics")
        console.print(f"2. Replace '@mention-user-here' with your actual @mention")
        console.print(f"3. This will trigger push notifications on mobile/desktop")
        console.print(f"\n[dim]Run 'python setup_user_mentions.py' to configure automatic mentions[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error testing notifications: {str(e)}[/red]")
        return 1


@cli.command('send-notification')
@click.option('--type', 'notification_type', type=click.Choice(['daily', 'test']), default='test',
              help='Type of notification to send')
@click.pass_context
def send_notification(ctx, notification_type):
    """Send a test notification or daily summary."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would send {notification_type} notification[/yellow]")
            return
        
        
        controller = ProspectAutomationController(cli_config.base_config)
        notification_manager = NotificationManager(cli_config.base_config, controller.notion_manager)
        
        if notification_type == 'daily':
            daily_stats = controller._calculate_daily_stats()
            success = notification_manager.send_daily_summary_notification(daily_stats)
        else:
            # Send test notification
            test_data = {
                'name': 'Test Campaign',
                'companies_processed': 5,
                'prospects_found': 12,
                'success_rate': 0.85,
                'duration_minutes': 15.5,
                'status': 'Completed'
            }
            success = notification_manager.send_campaign_completion_notification(test_data)
        
        if success:
            console.print(f"[green]✅ {notification_type.title()} notification sent successfully![/green]")
        else:
            console.print(f"[red]❌ Failed to send {notification_type} notification[/red]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Error sending notification: {str(e)}[/red]")
        return 1


@cli.command('analytics-report')
@click.option('--period', type=click.Choice(['daily', 'weekly', 'monthly']), default='daily',
              help='Report period')
@click.pass_context
def analytics_report(ctx, period):
    """Generate advanced analytics report."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would generate {period} analytics report[/yellow]")
            return
        
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        if period == 'daily':
            stats = controller._calculate_daily_stats()
            
            table = Table(title=f"Daily Analytics Report - {datetime.now().strftime('%Y-%m-%d')}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Campaigns Run", str(stats.get('campaigns_run', 0)))
            table.add_row("Companies Processed", str(stats.get('companies_processed', 0)))
            table.add_row("Prospects Found", str(stats.get('prospects_found', 0)))
            table.add_row("Emails Generated", str(stats.get('emails_generated', 0)))
            table.add_row("Success Rate", f"{stats.get('success_rate', 0) * 100:.1f}%")
            table.add_row("Processing Time", f"{stats.get('processing_time_minutes', 0):.1f} min")
            table.add_row("API Calls", str(stats.get('api_calls', 0)))
            table.add_row("Top Campaign", stats.get('top_campaign', 'N/A'))
            
            console.print(table)
        else:
            console.print(f"[yellow]{period.title()} reports coming soon![/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error generating analytics report: {str(e)}[/red]")
        return 1


@cli.command('quick-start')
@click.option('--limit', '-l', default=5, help='Number of companies to process (start small)')
@click.pass_context
def quick_start(ctx, limit):
    """>> QUICK START: Complete setup and first campaign in one command!"""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would run complete quick-start workflow[/yellow]")
            return
        
        console.print(Panel.fit(
            "[bold green]>> Job Prospect Automation - Quick Start[/bold green]\n"
            "This will set up everything and run your first campaign!",
            border_style="green"
        ))
        
        # Step 1: Check configuration
        console.print("\n[bold blue]Step 1: Configuration Check[/bold blue]")
        try:
            config = cli_config.base_config
            config.validate()
            console.print("[green]✅ Configuration valid[/green]")
        except Exception as e:
            console.print(f"[red]❌ Configuration error: {str(e)}[/red]")
            console.print("[yellow]Please check your .env file or config.yaml[/yellow]")
            return 1
        
        # Step 2: Dashboard setup
        console.print("\n[bold blue]Step 2: Dashboard Setup[/bold blue]")
        if not config.dashboard_id:
            console.print("[yellow]Setting up Notion dashboard...[/yellow]")
            dashboard_info = setup_func()
            if not dashboard_info:
                console.print("[red]❌ Dashboard setup failed[/red]")
                return 1
            console.print("[green]✅ Dashboard created successfully![/green]")
        else:
            console.print("[green]✅ Dashboard already configured[/green]")
        
        # Step 3: Run first campaign
        console.print(f"\n[bold blue]Step 3: First Campaign (Processing {limit} companies)[/bold blue]")
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        campaign_name = f"Quick Start Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Run discovery
        results = controller.run_discovery_pipeline(limit=limit, campaign_name=campaign_name)
        prospects_found = results['summary']['prospects_found']
        
        console.print(f"[green]✅ Discovery completed: {prospects_found} prospects found[/green]")
        
        # Generate emails if prospects found
        if prospects_found > 0:
            console.print("\n[bold blue]Step 4: Email Generation[/bold blue]")
            prospects = controller.notion_manager.get_prospects()
            recent_prospects = [p for p in prospects if p.id][-prospects_found:]
            prospect_ids = [p.id for p in recent_prospects if p.email]
            
            if prospect_ids:
                email_results = controller.generate_outreach_emails(
                    prospect_ids=prospect_ids[:3],  # Limit to 3 for quick start
                    template_type=EmailTemplate.COLD_OUTREACH
                )
                console.print(f"[green]✅ Generated {len(email_results.get('successful', []))} emails[/green]")
        
        # Update analytics
        if config.analytics_db_id:
            controller.create_daily_summary(config.analytics_db_id)
        
        console.print(Panel.fit(
            "[bold green]*** Quick Start Completed! ***[/bold green]\n\n"
            "✅ Dashboard created in Notion\n"
            "✅ Companies discovered and processed\n"
            "✅ Prospects extracted and stored\n"
            "✅ Emails generated (ready for review)\n"
            "✅ Analytics updated\n\n"
            "Next steps:\n"
            "* Check your Notion dashboard\n"
            "* Review generated emails\n"
            "* Run more campaigns with: python cli.py run-campaign",
            border_style="green"
        ))
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Quick start failed: {str(e)}[/red]")
        suggest_issue_report("config", str(e))
        return 1


@cli.command('generate-emails-recent')
@click.option('--limit', '-l', default=10, help='Number of recent prospects to generate emails for')
@click.option('--template', type=click.Choice(['cold_outreach', 'referral_followup', 'product_interest', 'networking']), 
              default='cold_outreach', help='Email template type')
@click.option('--send', is_flag=True, help='Send emails immediately after generation')
@click.pass_context
def generate_emails_recent(ctx, limit, template, send):
    """>> Generate emails for the most recently discovered prospects."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would generate emails for {limit} recent prospects[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        console.print(f"[blue]>> Generating emails for {limit} most recent prospects...[/blue]")
        
        # Get recent prospects with emails
        prospects = controller.notion_manager.get_prospects()
        prospects_with_emails = [p for p in prospects if p.email]
        
        # Sort by created_at to get truly recent ones, then take the most recent
        prospects_with_emails.sort(key=lambda x: x.created_at, reverse=True)  # Most recent first
        recent_prospects = prospects_with_emails[:limit]  # Take first N (most recent)
        
        if not recent_prospects:
            console.print("[yellow]WARNING: No recent prospects with emails found.[/yellow]")
            console.print("[dim]Run discovery first: python cli.py discover --limit 5[/dim]")
            return 1
        
        prospect_ids = [p.id for p in recent_prospects]
        
        console.print(f"[dim]Found {len(recent_prospects)} recent prospects with emails:[/dim]")
        for p in recent_prospects:
            console.print(f"  • {p.name} at {p.company}")
        
        # Generate emails
        template_map = {
            'cold_outreach': EmailTemplate.COLD_OUTREACH,
            'referral_followup': EmailTemplate.REFERRAL_FOLLOWUP,
            'product_interest': EmailTemplate.PRODUCT_INTEREST,
            'networking': EmailTemplate.NETWORKING
        }
        
        email_results = controller.generate_outreach_emails(
            prospect_ids=prospect_ids,
            template_type=template_map[template]
        )
        
        successful = len(email_results.get('successful', []))
        failed = len(email_results.get('failed', []))
        
        console.print(f"[green]✅ Email generation completed: {successful} successful, {failed} failed[/green]")
        
        # Show generated emails
        if successful > 0:
            console.print(f"\n[bold]*** Generated Emails:[/bold]")
            for result in email_results.get('successful', [])[:3]:  # Show first 3
                console.print(f"  • {result['prospect_name']} at {result['company']}")
                console.print(f"    Subject: {result['email_content']['subject']}")
                console.print(f"    Preview: {result['email_content']['body'][:100]}...")
                console.print()
        
        # Send emails if requested
        if send and successful > 0:
            console.print(f"[blue]>> Sending {successful} emails...[/blue]")
            
            send_results = controller.generate_and_send_outreach_emails(
                prospect_ids=prospect_ids,
                template_type=template_map[template],
                send_immediately=True,
                delay_between_emails=2.0
            )
            
            emails_sent = send_results.get('emails_sent', 0)
            console.print(f"[green]✅ Emails sent: {emails_sent}[/green]")
        
        # Update analytics
        if cli_config.base_config.analytics_db_id:
            controller.create_daily_summary(cli_config.base_config.analytics_db_id)
        
        console.print(f"\n[cyan]* Check your Notion Email Queue database for email details![/cyan]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Email generation failed: {str(e)}[/red]")
        return 1


@cli.command('profile-setup')
@click.option('--interactive', is_flag=True, help='Create profile interactively')
@click.option('--template', is_flag=True, help='Generate a profile template')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), default='markdown',
              help='Output format for the profile')
@click.option('--output', '-o', help='Output file path')
@click.option('--set-default', is_flag=True, help='Set as default profile')
@click.pass_context
def profile_setup(ctx, interactive, template, format, output, set_default):
    """Set up a sender profile for email personalization."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would set up sender profile[/yellow]")
            if interactive:
                console.print("[yellow]Would create profile interactively[/yellow]")
            if template:
                console.print(f"[yellow]Would generate {format} template[/yellow]")
            if output:
                console.print(f"[yellow]Would save to: {output}[/yellow]")
            if set_default:
                console.print("[yellow]Would set as default profile[/yellow]")
            return
        
        manager = SenderProfileManager()
        
        # Determine output path if not provided
        if not output:
            if interactive:
                output = f"profiles/profile_{format}.{format if format != 'markdown' else 'md'}"
            elif template:
                output = f"profiles/template_{format}.{format if format != 'markdown' else 'md'}"
            else:
                console.print("[red]Output path is required when not using --interactive or --template[/red]")
                return 1
        
        # Create directory if it doesn't exist
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        
        # Generate template or create interactively
        if template:
            console.print(f"[blue]Generating {format} template...[/blue]")
            template_content = manager.create_profile_template(format)
            
            with open(output, 'w', encoding='utf-8') as f:
                f.write(template_content)
                
            console.print(f"[green]Template saved to: {output}[/green]")
            console.print("[yellow]Please edit the file with your information.[/yellow]")
            
        elif interactive:
            console.print("[blue]Starting interactive profile creation...[/blue]")
            
            # Check for existing profiles
            try:
                existing_profiles = manager.discover_existing_profiles()
                if existing_profiles:
                    console.print(f"[yellow]Found {len(existing_profiles)} existing profile(s)[/yellow]")
                    
                    # Use the new functionality to handle existing profiles
                    profile = manager.create_profile_interactively(check_existing=True)
                else:
                    # No existing profiles, create new one
                    profile = manager.create_profile_interactively(check_existing=False)
                    
            except KeyboardInterrupt:
                console.print("[yellow]Profile setup cancelled by user[/yellow]")
                return 1
            except Exception as e:
                console.print(f"[red]Error during profile discovery: {e}[/red]")
                # Fallback to direct creation
                profile = manager.create_profile_interactively(check_existing=False)
            
            console.print(f"[green]Profile created successfully for {profile.name}![/green]")
            
            # Save profile to file
            if format == 'markdown':
                manager.save_profile_to_markdown(profile, output)
            elif format == 'json':
                manager.save_profile_to_json(profile, output)
            elif format == 'yaml':
                manager.save_profile_to_yaml(profile, output)
            
            console.print(f"[green]Profile saved to: {output}[/green]")
            
            # Set as default if requested
            if set_default:
                # Create config directory if it doesn't exist
                config_dir = Path.home() / '.job_prospect_automation'
                config_dir.mkdir(exist_ok=True)
                
                # Set default profile
                config_file = config_dir / 'config.json'
                config = {}
                
                if config_file.exists():
                    try:
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                    except json.JSONDecodeError:
                        config = {}
                
                # Convert to absolute path
                abs_path = str(Path(output).resolve())
                config['default_sender_profile'] = abs_path
                config['default_sender_profile_format'] = format
                
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                
                console.print(f"[green]Set {abs_path} as default sender profile[/green]")
        
        else:
            console.print("[red]Either --interactive or --template must be specified[/red]")
            return 1
        
    except Exception as e:
        console.print(f"[red]Error setting up profile: {e}[/red]")
        sys.exit(1)


@cli.command('run-campaign')
@click.option('--limit', '-l', default=10, help='Maximum number of companies to process')
@click.option('--campaign-name', '-c', help='Name for this campaign')
@click.option('--sender-profile', '-p', help='Path to sender profile file')
@click.option('--generate-emails', is_flag=True, help='Generate emails for found prospects')
@click.option('--send-emails', is_flag=True, help='Send generated emails immediately')
@click.option('--auto-setup', is_flag=True, help='Auto-setup dashboard if not configured')
@click.pass_context
def run_campaign(ctx, limit, campaign_name, sender_profile, generate_emails, send_emails, auto_setup):
    """>> Run the COMPLETE automation workflow - from discovery to email sending!"""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would run complete campaign workflow[/yellow]")
            console.print(f"[yellow]  • Discover up to {limit} companies[/yellow]")
            console.print(f"[yellow]  • Campaign: {campaign_name or 'Auto-generated'}[/yellow]")
            if generate_emails:
                console.print("[yellow]  • Generate personalized emails[/yellow]")
            if send_emails:
                console.print("[yellow]  • Send emails immediately[/yellow]")
            return
        
        # Step 0: Auto-setup dashboard if requested and not configured
        if auto_setup and not cli_config.base_config.dashboard_id:
            console.print("[blue]🔧 Setting up dashboard automatically...[/blue]")
            dashboard_info = setup_func()
            if not dashboard_info:
                console.print("[red]❌ Dashboard setup failed. Please run setup manually.[/red]")
                return 1
            console.print("[green]✅ Dashboard setup completed![/green]\n")
        
        # Initialize controller
        controller = ProspectAutomationController(cli_config.base_config)
        
        # Set sender profile if provided
        if sender_profile:
            controller.set_sender_profile(sender_profile)
        
        # Generate campaign name if not provided
        if not campaign_name:
            campaign_name = f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        console.print(Panel.fit(
            f"[bold green]>> Starting Complete Campaign Workflow[/bold green]\n"
            f"Campaign: {campaign_name}\n"
            f"Target: {limit} companies\n"
            f"Generate Emails: {'Yes' if generate_emails else 'No'}\n"
            f"Send Emails: {'Yes' if send_emails else 'No'}",
            border_style="green"
        ))
        
        # Step 1: Discovery Pipeline
        console.print("\n[bold blue]* Step 1: Company Discovery & Prospect Extraction[/bold blue]")
        # Use platform-safe text to avoid Unicode encoding issues on Windows
        safe_text = get_platform_safe_text(
            "Monitor real-time progress in your Notion dashboard", 
            "💡", 
            "Monitor real-time progress in your Notion dashboard"
        )
        console.print(f"[dim]{safe_text}[/dim]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running discovery pipeline...", total=None)
            
            results = controller.run_discovery_pipeline(limit=limit, campaign_name=campaign_name)
            
            progress.update(task, description="Discovery completed!")
        
        # Display discovery results
        _display_results(results)
        
        prospects_found = results['summary']['prospects_found']
        
        # Initialize result variables
        email_results = {'emails_generated': 0, 'successful': []}
        send_results = {'emails_sent': 0}
        
        if prospects_found == 0:
            console.print("[yellow]WARNING: No prospects found. Campaign completed.[/yellow]")
            return 0
        
        # Step 2: Email Generation (if requested)
        if generate_emails:
            console.print(f"\n[bold blue]* Step 2: Email Generation[/bold blue]")
            
            # Get prospect IDs from the results
            # Use the same logic as generate-emails-recent command for consistency
            all_prospects = controller.notion_manager.get_prospects()
            prospects_with_ids = [p for p in all_prospects if p.id]
            
            if prospects_with_ids and prospects_found > 0:
                # Sort by created_at to get truly recent ones (same as generate-emails-recent)
                prospects_with_ids.sort(key=lambda x: x.created_at, reverse=True)  # Most recent first
                recent_prospects = prospects_with_ids[:prospects_found]  # Take the exact number we found
                
                console.print(f"[dim]Debug: Selected prospects for email generation:[/dim]")
                for p in recent_prospects:
                    console.print(f"[dim]  - {p.name} at {getattr(p, 'company', 'Unknown')} (created: {p.created_at.strftime('%H:%M:%S')})[/dim]")
            else:
                recent_prospects = []
                
            prospect_ids = [p.id for p in recent_prospects]  # All prospects (email generation doesn't require existing emails)
            
            if not prospect_ids:
                console.print("[yellow]WARNING: No prospects with emails found for email generation.[/yellow]")
            else:
                console.print(f"[dim]Generating emails for {len(prospect_ids)} prospects...[/dim]")
                
                email_results = controller.generate_outreach_emails(
                    prospect_ids=prospect_ids,
                    template_type=EmailTemplate.COLD_OUTREACH
                )
                
                successful_emails = len(email_results.get('successful', []))
                failed_emails = len(email_results.get('failed', []))
                
                console.print(f"[green]✅ Email generation: {successful_emails} successful, {failed_emails} failed[/green]")
                
                # Step 3: Email Sending (if requested)
                if send_emails and successful_emails > 0:
                    console.print(f"\n[bold blue]>> Step 3: Email Sending[/bold blue]")
                    
                    send_results = controller.generate_and_send_outreach_emails(
                        prospect_ids=prospect_ids,
                        template_type=EmailTemplate.COLD_OUTREACH,
                        send_immediately=True,
                        delay_between_emails=2.0
                    )
                    
                    emails_sent = send_results.get('emails_sent', 0)
                    console.print(f"[green]✅ Emails sent: {emails_sent}[/green]")
        
        # Step 4: Update Analytics
        console.print(f"\n[bold blue]* Step 4: Analytics Update[/bold blue]")
        
        analytics_db_id = cli_config.base_config.analytics_db_id
        if analytics_db_id:
            success = controller.create_daily_summary(analytics_db_id)
            if success:
                console.print("[green]✅ Daily analytics updated[/green]")
            else:
                console.print("[yellow]WARNING: Analytics update failed[/yellow]")
        
        # Final Summary
        safe_phone_text = get_platform_safe_emoji_text(
            "{phone} Check your Notion dashboard for detailed progress and notifications!",
            phone_emoji="📱",
            fallback_text="Check your Notion dashboard for detailed progress and notifications!"
        )
        console.print(Panel.fit(
            f"[bold green]*** Campaign Completed Successfully! ***[/bold green]\n\n"
            f"* Results Summary:\n"
            f"• Companies Processed: {results['summary']['companies_processed']}\n"
            f"• Prospects Found: {prospects_found}\n"
            f"• Emails Generated: {email_results.get('emails_generated', 0) if generate_emails else 'Skipped'}\n"
            f"• Emails Sent: {send_results.get('emails_sent', 0) if send_emails else 'Skipped'}\n"
            f"• Success Rate: {results['summary']['success_rate']:.1f}%\n"
            f"• Duration: {results['summary']['duration_seconds']:.1f} seconds\n\n"
            f"{safe_phone_text}",
            border_style="green"
        ))
        
        # Show dashboard links
        if cli_config.base_config.dashboard_id:
            safe_link_text = get_platform_safe_emoji_text(
                "{link} Quick Links:",
                link_emoji="🔗",
                fallback_text="Quick Links:"
            )
            console.print(f"\n[cyan]{safe_link_text}[/cyan]")
            console.print(f"* Dashboard: https://notion.so/{cli_config.base_config.dashboard_id.replace('-', '')}")
            if cli_config.base_config.campaigns_db_id:
                safe_target_text = get_platform_safe_emoji_text(
                    "{target} Campaign Details: https://notion.so/{cli_config.base_config.campaigns_db_id.replace('-', '')}",
                    target_emoji="🎯",
                    fallback_text=f"Campaign Details: https://notion.so/{cli_config.base_config.campaigns_db_id.replace('-', '')}"
                )
                console.print(safe_target_text)
            if cli_config.base_config.analytics_db_id:
                console.print(f"* Analytics: https://notion.so/{cli_config.base_config.analytics_db_id.replace('-', '')}")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Campaign failed: {str(e)}[/red]")
        suggest_issue_report("unexpected", str(e))
        return 1


@cli.command()
@click.option('--limit', '-l', default=50, help='Maximum number of products to process')
@click.option('--batch-size', '-b', default=5, help='Batch size for processing companies')
@click.option('--sender-profile', '-p', help='Path to sender profile file for personalization')
@click.option('--campaign-name', '-c', help='Name for this campaign (for progress tracking)')
@click.pass_context
def discover(ctx, limit, batch_size, sender_profile, campaign_name):
    """Run the discovery pipeline to find prospects (discovery only)."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would discover companies and extract prospects[/yellow]")
            console.print(f"[yellow]Would process up to {limit} products in batches of {batch_size}[/yellow]")
            if sender_profile:
                console.print(f"[yellow]Would use sender profile: {sender_profile}[/yellow]")
            if campaign_name:
                console.print(f"[yellow]Would create campaign: {campaign_name}[/yellow]")
            return
        
        controller = ProspectAutomationController()
        
        # Set sender profile if provided
        if sender_profile:
            controller.set_sender_profile(sender_profile)
        
        # Generate campaign name if not provided
        if not campaign_name:
            campaign_name = f"Discovery Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        console.print(f"[blue]Starting campaign: {campaign_name}[/blue]")
        # Step 1: Discovery Pipeline
        console.print("\n[bold blue]* Step 1: Company Discovery & Prospect Extraction[/bold blue]")
        # Use platform-safe text to avoid Unicode encoding issues on Windows
        safe_text = get_platform_safe_text(
            "Monitor real-time progress in your Notion dashboard", 
            "💡", 
            "Monitor real-time progress in your Notion dashboard"
        )
        console.print(f"[dim]{safe_text}[/dim]")
        
        # Use Windows-compatible progress to avoid Unicode encoding issues on Windows
        if platform.system().lower() == "windows":
            with replace_spinner_progress(console, "Running discovery pipeline...") as progress:
                task = progress.add_task("Running discovery pipeline...")
                
                results = controller.run_discovery_pipeline(limit=limit, campaign_name=campaign_name)
                
                progress.update(task, completed=True, description="Discovery completed!")
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running discovery pipeline...", total=None)
                
                results = controller.run_discovery_pipeline(limit=limit, campaign_name=campaign_name)
                
                progress.update(task, description="Discovery completed!")
        
        _display_results(results)
        
        # Show campaign progress
        campaign_progress = controller.get_campaign_progress()
        if campaign_progress:
            # Use platform-safe text to avoid Unicode encoding issues on Windows
            safe_text = get_platform_safe_text(
                f"Campaign '{campaign_progress['name']}' completed successfully!", 
                "✅", 
                f"Campaign '{campaign_progress['name']}' completed successfully!"
            )
            console.print(f"\n[green]{safe_text}[/green]")
            console.print(f"[dim]* Check your Notion dashboard for detailed progress and logs[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error during discovery: {e}[/red]")
        sys.exit(1)
@cli.command('process-company')
@click.argument('company_name')
@click.option('--domain', help='Company domain (if known)')
@click.option('--sender-profile', '-p', help='Path to sender profile file for personalization')
@click.pass_context
def process_company(ctx, company_name, domain, sender_profile):
    """Process a specific company to find prospects."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would process company '{company_name}'[/yellow]")
            if domain:
                console.print(f"[yellow]Would use domain: {domain}[/yellow]")
            if sender_profile:
                console.print(f"[yellow]Would use sender profile: {sender_profile}[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        # Set sender profile if provided
        if sender_profile:
            controller.set_sender_profile(sender_profile)
        
        # Create company data object
        company_data = CompanyData(
            name=company_name,
            domain=domain or f"{company_name.lower().replace(' ', '')}.com",
            product_url="",
            description="Manually specified company",
            launch_date=None
        )
        
        # Use Windows-compatible progress to avoid Unicode encoding issues on Windows
        if platform.system().lower() == "windows":
            with replace_spinner_progress(console, f"Processing {company_name}...") as progress:
                task = progress.add_task(f"Processing {company_name}...")
                
                prospects = controller.process_company(company_data)
                
                progress.update(task, completed=True, description="Processing completed!")
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Processing {company_name}...", total=None)
                
                prospects = controller.process_company(company_data)
                
                progress.update(task, description="Processing completed!")
        
        _display_prospects(prospects)
        
    except Exception as e:
        console.print(f"[red]Error processing company: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--prospect-ids', help='Comma-separated list of prospect IDs')
@click.option('--template', type=click.Choice(['cold_outreach', 'referral', 'follow_up']), 
              default='cold_outreach', help='Email template type')
@click.option('--output', '-o', help='Output file for generated emails')
@click.option('--send', is_flag=True, help='Send emails immediately after generation')
@click.option('--sender-profile', '-p', help='Path to sender profile file for personalization')
@click.option('--use-default-profile', is_flag=True, help='Use default sender profile')
@click.option('--interactive-profile', is_flag=True, help='Create sender profile interactively')
@click.option('--validate-profile', is_flag=True, help='Validate sender profile before generating emails')
@click.option('--completeness-threshold', '-t', type=float, default=0.7,
              help='Profile completeness threshold (0.0-1.0, default: 0.7)')
@click.option('--profile-format', type=click.Choice(['markdown', 'json', 'yaml']), 
              help='Format of the sender profile file (auto-detected if not specified)')
@click.pass_context
def generate_emails(ctx, prospect_ids, template, output, send, sender_profile, 
                   use_default_profile, interactive_profile, validate_profile, 
                   completeness_threshold, profile_format):
    """Generate personalized outreach emails for prospects."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if not prospect_ids:
            console.print("[red]Error: --prospect-ids is required[/red]")
            sys.exit(1)
        
        ids = [id.strip() for id in prospect_ids.split(',')]
        template_enum = EmailTemplate[template.upper()]
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would generate {template} emails for {len(ids)} prospects[/yellow]")
            if send:
                console.print("[yellow]Would send emails immediately after generation[/yellow]")
            if output:
                console.print(f"[yellow]Would save to: {output}[/yellow]")
            if sender_profile:
                console.print(f"[yellow]Would use sender profile: {sender_profile}[/yellow]")
                if validate_profile:
                    console.print(f"[yellow]Would validate sender profile before generating emails[/yellow]")
                    console.print(f"[yellow]Would use completeness threshold: {completeness_threshold:.1%}[/yellow]")
            if interactive_profile:
                console.print("[yellow]Would create sender profile interactively[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        # Handle sender profile
        if interactive_profile:
            console.print("[blue]Creating sender profile interactively...[/blue]")
            manager = SenderProfileManager()
            profile = manager.create_profile_interactively(check_existing=True)
            controller.set_sender_profile_object(profile)
            console.print("[green]Sender profile created successfully[/green]")
        elif use_default_profile:
            # Try to load default profile from config
            config_file = Path.home() / '.job_prospect_automation' / 'config.json'
            
            if not config_file.exists():
                console.print("[red]No default sender profile found. Use --sender-profile to specify a profile.[/red]")
                sys.exit(1)
            
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                console.print("[red]Error reading configuration file[/red]")
                sys.exit(1)
            
            if 'default_sender_profile' not in config:
                console.print("[red]No default sender profile set. Use --sender-profile to specify a profile.[/red]")
                sys.exit(1)
            
            default_profile_path = config['default_sender_profile']
            default_profile_format = config.get('default_sender_profile_format', 'markdown')
            
            if not Path(default_profile_path).exists():
                console.print(f"[red]Default profile not found: {default_profile_path}[/red]")
                sys.exit(1)
            
            console.print(f"[blue]Using default sender profile: {default_profile_path}[/blue]")
            sender_profile = default_profile_path
            profile_format = default_profile_format
            
        elif sender_profile:
            # Use specified profile format or auto-detect
            if not profile_format:
                # Auto-detect format from file extension
                if sender_profile.endswith('.md'):
                    profile_format = 'markdown'
                elif sender_profile.endswith('.json'):
                    profile_format = 'json'
                elif sender_profile.endswith('.yaml') or sender_profile.endswith('.yml'):
                    profile_format = 'yaml'
                else:
                    console.print("[red]Could not detect profile format from file extension.[/red]")
                    console.print("[red]Please use --profile-format to specify the format.[/red]")
                    sys.exit(1)
        
        # Load and validate profile if specified
        if sender_profile:
            manager = SenderProfileManager()
            
            try:
                if profile_format == 'markdown':
                    profile = manager.load_profile_from_markdown(sender_profile)
                elif profile_format == 'json':
                    profile = manager.load_profile_from_json(sender_profile)
                elif profile_format == 'yaml':
                    profile = manager.load_profile_from_yaml(sender_profile)
            except FileNotFoundError:
                console.print(f"[red]Profile file not found: {sender_profile}[/red]")
                sys.exit(1)
            except ValidationError as e:
                console.print(f"[red]Profile validation failed: {e}[/red]")
                sys.exit(1)
            
            # Validate profile if requested
            if validate_profile:
                
                # Validate profile
                is_valid, issues = manager.validate_profile(profile)
                completeness = profile.get_completeness_score()
                
                if not is_valid:
                    console.print("[red]Sender profile validation failed:[/red]")
                    for issue in issues:
                        console.print(f"  [red]• {issue}[/red]")
                    sys.exit(1)
                
                if completeness < completeness_threshold:
                    console.print(f"[red]Sender profile completeness ({completeness:.1%}) is below threshold ({completeness_threshold:.1%})[/red]")
                    console.print("[yellow]Suggestions for improvement:[/yellow]")
                    suggestions = manager.get_profile_suggestions(profile)
                    for suggestion in suggestions:
                        console.print(f"  [yellow]• {suggestion}[/yellow]")
                    sys.exit(1)
                
                console.print(f"[green]Sender profile validation passed (completeness: {completeness:.1%})[/green]")
                controller.set_sender_profile_object(profile)
            else:
                controller.set_sender_profile(sender_profile)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating emails...", total=None)
            
            results = controller.generate_outreach_emails(ids, template_enum)
            
            progress.update(task, description="Email generation completed!")
        
        _display_email_results(results, output)
        
    except Exception as e:
        console.print(f"[red]Error generating emails: {e}[/red]")
        sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """Show current workflow status and statistics."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would show workflow status[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        status_info = controller.get_workflow_status()
        
        _display_status(status_info)
        
    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def batch_history(ctx):
    """Show batch processing history."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would show batch history[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        history = controller.list_batch_history()
        
        _display_batch_history(history)
        
    except Exception as e:
        console.print(f"[red]Error getting batch history: {e}[/red]")
        sys.exit(1)


@cli.command('analyze-products')
@click.option('--company-ids', help='Comma-separated list of company IDs to analyze')
@click.option('--limit', '-l', default=10, help='Maximum number of companies to analyze')
@click.pass_context
def analyze_products(ctx, company_ids, limit):
    """Run AI-powered product analysis for companies."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            if company_ids:
                ids = [id.strip() for id in company_ids.split(',')]
                console.print(f"[yellow]DRY-RUN: Would analyze products for {len(ids)} companies[/yellow]")
            else:
                console.print(f"[yellow]DRY-RUN: Would analyze products for up to {limit} companies[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing products...", total=None)
            
            if company_ids:
                ids = [id.strip() for id in company_ids.split(',')]
                results = controller.analyze_company_products(ids)
            else:
                results = controller.analyze_recent_products(limit=limit)
            
            progress.update(task, description="Product analysis completed!")
        
        _display_analysis_results(results)
        
    except Exception as e:
        console.print(f"[red]Error during product analysis: {e}[/red]")
        sys.exit(1)

@cli.command('send-emails')
@click.option('--prospect-ids', help='Comma-separated list of prospect IDs')
@click.option('--batch-size', '-b', default=10, help='Batch size for sending emails')
@click.option('--delay', '-d', default=60, help='Delay between batches in seconds')
@click.pass_context
def send_emails(ctx, prospect_ids, batch_size, delay):
    """Send generated emails to prospects."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if not prospect_ids:
            console.print("[red]Error: --prospect-ids is required[/red]")
            sys.exit(1)
        
        ids = [id.strip() for id in prospect_ids.split(',')]
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would send emails to {len(ids)} prospects[/yellow]")
            console.print(f"[yellow]Would use batch size: {batch_size}, delay: {delay}s[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Sending emails...", total=None)
            
            results = controller.send_prospect_emails(ids, batch_size=batch_size, delay=delay)
            
            progress.update(task, description="Email sending completed!")
        
        _display_sending_results(results)
        
    except Exception as e:
        console.print(f"[red]Error sending emails: {e}[/red]")
        sys.exit(1)


@cli.command('send-emails-recent')
@click.option('--limit', '-l', default=10, help='Number of recent generated emails to send')
@click.option('--batch-size', '-b', default=5, help='Batch size for sending emails')
@click.option('--delay', '-d', default=30, help='Delay between batches in seconds')
@click.pass_context
def send_emails_recent(ctx, limit, batch_size, delay):
    """>> Send the most recently generated emails that haven't been sent yet."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        console.print(f"[blue]>> Finding {limit} most recent generated emails to send...[/blue]")
        
        
        # Get prospects with generated emails that haven't been sent
        # This filters for emails that are generated but not yet sent
        unsent_prospect_data = controller.notion_manager.get_prospects_by_email_status(
            generation_status="Generated",
            delivery_status="Not Sent"
        )
        
        if not unsent_prospect_data:
            console.print("[yellow]⚠️ No prospects with generated but unsent emails found.[/yellow]")
            console.print("[dim]Generate emails first: python cli.py generate-emails-recent --limit 5[/dim]")
            return 1
        
        # Convert to prospect objects and filter for those with email addresses
        unsent_prospects = []
        for data in unsent_prospect_data:
            if data.get('email'):  # Only include prospects with email addresses
                # Double-check that this email hasn't been sent (additional safety check)
                delivery_status = data.get('delivery_status', 'Not Sent')
                if delivery_status in ['Not Sent', 'Failed']:  # Only include truly unsent emails
                    # Create a simple prospect-like object for display
                    class ProspectDisplay:
                        def __init__(self, data):
                            self.id = data['id']
                            self.name = data['name']
                            self.company = data['company']
                            self.email = data['email']
                            # Use email generated date for sorting (this is the key field)
                            self.generated_date = data.get('generated_date')
                            self.delivery_status = data.get('delivery_status', 'Not Sent')
                    
                    unsent_prospects.append(ProspectDisplay(data))
        
        if not unsent_prospects:
            console.print("[yellow]⚠️ No prospects with generated emails found.[/yellow]")
            console.print("[dim]Generate emails first: python cli.py generate-emails-recent --limit 5[/dim]")
            return 1
        
        # Sort by email generated date to get most recently generated emails first
        # Filter out prospects without generated_date and sort the rest
        prospects_with_dates = [p for p in unsent_prospects if p.generated_date]
        prospects_with_dates.sort(key=lambda x: x.generated_date, reverse=True)
        
        # Take the most recent ones up to the limit
        recent_unsent = prospects_with_dates[:limit]
        
        prospect_ids = [p.id for p in recent_unsent]
        
        console.print(f"[dim]Found {len(recent_unsent)} recent prospects with generated emails:[/dim]")
        for p in recent_unsent:
            status_color = "yellow" if p.delivery_status == "Failed" else "green"
            console.print(f"  • {p.name} at {p.company} [dim]({p.delivery_status})[/dim]")
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would send emails to {len(prospect_ids)} prospects[/yellow]")
            console.print(f"[yellow]Would use batch size: {batch_size}, delay: {delay}s[/yellow]")
            return
        
        # Confirm before sending
        if not click.confirm(f"\n>> Send emails to {len(recent_unsent)} prospects?"):
            console.print("[yellow]Email sending cancelled.[/yellow]")
            return
        
        console.print(f"[blue]>> Sending emails to {len(recent_unsent)} prospects...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Sending emails...", total=None)
            
            results = controller.send_prospect_emails(prospect_ids, batch_size=batch_size, delay=delay)
            
            progress.update(task, description="Email sending completed!")
        
        # Display detailed results
        successful = results.get('successful', [])
        failed = results.get('failed', [])
        skipped = [f for f in failed if f.get('skipped', False)]
        actual_failed = [f for f in failed if not f.get('skipped', False)]
        
        console.print(f"\n[bold]📊 Email Sending Summary:[/bold]")
        console.print(f"[green]✅ Sent: {len(successful)}[/green]")
        console.print(f"[yellow]⏭️  Skipped (already sent): {len(skipped)}[/yellow]")
        console.print(f"[red]❌ Failed: {len(actual_failed)}[/red]")
        
        if successful:
            console.print(f"\n[bold green]📧 Successfully Sent:[/bold green]")
            for result in successful:
                console.print(f"  ✅ {result['prospect_name']} ({result['email']}) - ID: {result['email_id']}")
        
        if skipped:
            console.print(f"\n[bold yellow]⏭️  Skipped (Already Sent):[/bold yellow]")
            for result in skipped:
                console.print(f"  ⏭️  {result['prospect_name']} - {result['error']}")
        
        if actual_failed:
            console.print(f"\n[bold red]❌ Failed:[/bold red]")
            for result in actual_failed[:5]:  # Show first 5 failures
                console.print(f"  ❌ {result['prospect_name']} - {result['error']}")
        
        # Show legacy results table for compatibility
        _display_sending_results({
            'summary': {
                'emails_sent': len(successful),
                'successful_deliveries': len(successful),
                'failed_deliveries': len(actual_failed),
                'delivery_success_rate': (len(successful) / len(prospect_ids) * 100) if prospect_ids else 0
            }
        })
        
    except Exception as e:
        console.print(f"[red]Error sending recent emails: {e}[/red]")
        sys.exit(1)


@cli.command('validate-config')
@click.option('--check-profile', '-p', help='Path to sender profile file to validate')
@click.pass_context
def validate_config(ctx, check_profile):
    """Validate configuration settings and API keys."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        console.print("[blue]Validating configuration...[/blue]")
        
        # Validate configuration
        cli_config.base_config.validate()
        console.print("[green]Configuration validation passed[/green]")
        
        # Validate sender profile if provided
        if check_profile:
            
            try:
                manager = SenderProfileManager()
                
                # Auto-detect format from file extension
                if check_profile.endswith('.md'):
                    profile_format = 'markdown'
                elif check_profile.endswith('.json'):
                    profile_format = 'json'
                elif check_profile.endswith('.yaml') or check_profile.endswith('.yml'):
                    profile_format = 'yaml'
                else:
                    console.print("[red]Could not detect profile format from file extension.[/red]")
                    console.print("[red]Please use a file with .md, .json, .yaml, or .yml extension.[/red]")
                    return 1
                
                # Load and validate profile
                if profile_format == 'markdown':
                    profile = manager.load_profile_from_markdown(check_profile)
                elif profile_format == 'json':
                    profile = manager.load_profile_from_json(check_profile)
                elif profile_format == 'yaml':
                    profile = manager.load_profile_from_yaml(check_profile)
                
                is_valid, issues = manager.validate_profile(profile)
                
                if is_valid:
                    console.print("[green]Sender profile validation passed[/green]")
                    completeness = profile.get_completeness_score()
                    console.print(f"Profile completeness: {completeness:.1%}")
                else:
                    console.print("[red]✗ Sender profile has issues:[/red]")
                    for issue in issues:
                        console.print(f"  [red]• {issue}[/red]")
                    
                    # Show suggestions
                    suggestions = manager.get_profile_suggestions(profile)
                    if suggestions:
                        console.print("\n[yellow]Suggestions for improvement:[/yellow]")
                        for suggestion in suggestions:
                            console.print(f"  [yellow]• {suggestion}[/yellow]")
            
            except FileNotFoundError:
                console.print(f"[red]Profile file not found: {check_profile}[/red]")
                return 1
            except ValidationError as e:
                console.print(f"[red]Profile validation failed: {e}[/red]")
                return 1
        
        # Test API connections if not in dry-run mode
        if not cli_config.dry_run:
            controller = ProspectAutomationController(cli_config.base_config)
            validation_results = controller.validate_api_connections()
            
            _display_validation_results(validation_results)
        else:
            console.print("[yellow]DRY-RUN: Skipping API connection tests[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        sys.exit(1)

@cli.command('enhanced-workflow')
@click.option('--limit', '-l', default=20, help='Maximum number of products to process')
@click.option('--enable-ai-parsing', is_flag=True, default=True, help='Enable AI parsing for data structuring')
@click.option('--enable-product-analysis', is_flag=True, default=True, help='Enable comprehensive product analysis')
@click.option('--generate-emails', is_flag=True, help='Generate emails after processing')
@click.option('--send-emails', is_flag=True, help='Send emails immediately after generation')
@click.option('--sender-profile', '-p', help='Path to sender profile file for personalization')
@click.pass_context
def enhanced_workflow(ctx, limit, enable_ai_parsing, enable_product_analysis, generate_emails, send_emails, sender_profile):
    """Run the complete enhanced workflow with AI parsing and product analysis."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would run enhanced workflow[/yellow]")
            console.print(f"[yellow]Would process up to {limit} products[/yellow]")
            console.print(f"[yellow]AI parsing: {'enabled' if enable_ai_parsing else 'disabled'}[/yellow]")
            console.print(f"[yellow]Product analysis: {'enabled' if enable_product_analysis else 'disabled'}[/yellow]")
            console.print(f"[yellow]Generate emails: {'yes' if generate_emails else 'no'}[/yellow]")
            console.print(f"[yellow]Send emails: {'yes' if send_emails else 'no'}[/yellow]")
            if sender_profile:
                console.print(f"[yellow]Would use sender profile: {sender_profile}[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        # Set sender profile if provided
        if sender_profile:
            controller.set_sender_profile(sender_profile)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running enhanced workflow...", total=None)
            
            results = controller.run_enhanced_workflow(
                limit=limit,
                enable_ai_parsing=enable_ai_parsing,
                enable_product_analysis=enable_product_analysis,
                generate_emails=generate_emails,
                send_emails=send_emails
            )
            
            progress.update(task, description="Enhanced workflow completed!")
        
        _display_enhanced_results(results)
        
    except Exception as e:
        console.print(f"[red]Error during enhanced workflow: {e}[/red]")
        sys.exit(1)


@cli.command('test-components')
@click.option('--component', type=click.Choice(['ai-parser', 'product-analyzer', 'email-sender', 'all']), 
              default='all', help='Component to test')
@click.option('--sample-data', help='Path to sample data file for testing')
@click.pass_context
def test_components(ctx, component, sample_data):
    """Test individual system components with sample data."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would test component '{component}'[/yellow]")
            if sample_data:
                console.print(f"[yellow]Would use sample data from: {sample_data}[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Testing {component}...", total=None)
            
            results = controller.test_components(component, sample_data)
            
            progress.update(task, description="Component testing completed!")
        
        _display_component_test_results(results)
        
    except Exception as e:
        console.print(f"[red]Error testing components: {e}[/red]")
        sys.exit(1)

@cli.command('ai-parse')
@click.option('--input-file', required=True, help='File containing raw data to parse')
@click.option('--data-type', type=click.Choice(['linkedin', 'product', 'team', 'company']), 
              required=True, help='Type of data to parse')
@click.option('--output-file', help='Output file for parsed data')
@click.pass_context
def ai_parse(ctx, input_file, data_type, output_file):
    """Parse raw scraped data using AI."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if not os.path.exists(input_file):
            console.print(f"[red]Input file not found: {input_file}[/red]")
            sys.exit(1)
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would parse {data_type} data from {input_file}[/yellow]")
            if output_file:
                console.print(f"[yellow]Would save to: {output_file}[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        with open(input_file, 'r') as f:
            raw_data = f.read()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Parsing {data_type} data...", total=None)
            
            parsed_data = controller.parse_raw_data(raw_data, data_type)
            
            progress.update(task, description="AI parsing completed!")
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(parsed_data, f, indent=2, default=str)
            console.print(f"[green]Parsed data saved to: {output_file}[/green]")
        else:
            console.print(json.dumps(parsed_data, indent=2, default=str))
        
    except Exception as e:
        console.print(f"[red]Error during AI parsing: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('output_file', default='config.yaml')
@click.option('--include-azure', is_flag=True, help='Include Azure OpenAI configuration options')
@click.option('--include-resend', is_flag=True, help='Include Resend email configuration options')
@click.option('--include-sender-profile', is_flag=True, help='Include sender profile configuration options')
def init_config(output_file, include_azure, include_resend, include_sender_profile):
    """Initialize a configuration file with default values."""
    config_template = {
        # Required API Keys
        'NOTION_TOKEN': 'your_notion_token_here',
        'HUNTER_API_KEY': 'your_hunter_api_key_here',
        'OPENAI_API_KEY': 'your_openai_api_key_here',
        
        # Rate Limiting
        'SCRAPING_DELAY': '2.0',
        'HUNTER_REQUESTS_PER_MINUTE': '10',
        
        # Processing Limits
        'MAX_PRODUCTS_PER_RUN': '50',
        'MAX_PROSPECTS_PER_COMPANY': '10',
        
        # Notion Configuration
        'NOTION_DATABASE_ID': '',
        
        # Email Generation
        'EMAIL_TEMPLATE_TYPE': 'professional',
        'PERSONALIZATION_LEVEL': 'medium',
        
        # AI Parsing Configuration
        'ENABLE_AI_PARSING': 'true',
        'AI_PARSING_MODEL': 'gpt-4',
        'AI_PARSING_MAX_RETRIES': '3',
        'AI_PARSING_TIMEOUT': '30',
        
        # Product Analysis Configuration
        'ENABLE_PRODUCT_ANALYSIS': 'true',
        'PRODUCT_ANALYSIS_MODEL': 'gpt-4',
        'PRODUCT_ANALYSIS_MAX_RETRIES': '3',
        
        # Enhanced Email Generation
        'ENHANCED_PERSONALIZATION': 'true',
        'EMAIL_GENERATION_MODEL': 'gpt-4',
        'MAX_EMAIL_LENGTH': '500',
        
        # Workflow Configuration
        'ENABLE_ENHANCED_WORKFLOW': 'true',
        'BATCH_PROCESSING_ENABLED': 'true',
        'AUTO_SEND_EMAILS': 'false',
        'EMAIL_REVIEW_REQUIRED': 'true',
    }
    
    # Add Azure OpenAI configuration if requested
    if include_azure:
        config_template.update({
            'USE_AZURE_OPENAI': 'false',
            'AZURE_OPENAI_API_KEY': 'your_azure_openai_api_key_here',
            'AZURE_OPENAI_ENDPOINT': 'https://your-resource-name.openai.azure.com/',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'gpt-4',
            'AZURE_OPENAI_API_VERSION': '2024-02-15-preview',
        })
    
    # Add Resend email configuration if requested
    if include_resend:
        config_template.update({
            'RESEND_API_KEY': 'your_resend_api_key_here',
            'SENDER_EMAIL': 'your-email@yourdomain.com',
            'SENDER_NAME': 'Your Name',
            'REPLY_TO_EMAIL': 'your-reply-to@yourdomain.com',
            'RESEND_REQUESTS_PER_MINUTE': '100',
        })
    
    # Add sender profile configuration if requested
    if include_sender_profile:
        config_template.update({
            'SENDER_PROFILE_PATH': 'profiles/default_profile.md',
            'SENDER_PROFILE_FORMAT': 'markdown',
            'ENABLE_INTERACTIVE_PROFILE_SETUP': 'true',
            'PROFILE_COMPLETENESS_THRESHOLD': '0.7',
        })
    
    try:
        with open(output_file, 'w') as f:
            yaml.dump(config_template, f, default_flow_style=False)
        
        console.print(f"[green]Configuration template created: {output_file}[/green]")
        console.print("[yellow]Please edit the file and add your API keys before running the system.[/yellow]")
        
        if include_azure:
            console.print("[blue]Azure OpenAI configuration options included.[/blue]")
        if include_resend:
            console.print("[blue]Resend email configuration options included.[/blue]")
        if include_sender_profile:
            console.print("[blue]Sender profile configuration options included.[/blue]")
            console.print("[yellow]Don't forget to create your sender profile using the 'profile create' command.[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error creating config file: {e}[/red]")
        sys.exit(1)


@cli.command('setup-profile')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json', 'yaml']), default='markdown',
              help='Output format for the profile')
@click.option('--output', '-o', default='profiles/default_profile.md', help='Output file path')
@click.pass_context
def setup_profile(ctx, format, output):
    """Interactive setup for sender profile creation."""
    try:
        console.print("[blue]Starting interactive sender profile setup...[/blue]")
        console.print("This will guide you through creating a profile for personalized outreach emails.")
        
        manager = SenderProfileManager()
        profile = manager.create_profile_interactively(check_existing=True)
        
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
        console.print("[yellow]To use this profile with commands, use the --sender-profile option.[/yellow]")
        console.print("[yellow]Example: --sender-profile " + output + "[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error setting up profile: {e}[/red]")
        sys.exit(1)


def _display_results(results: Dict[str, Any]):
    """Display pipeline results in a formatted table."""
    summary = results.get('summary', {})
    
    table = Table(title="Discovery Pipeline Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Companies Processed", str(summary.get('companies_processed', 0)))
    table.add_row("Prospects Found", str(summary.get('prospects_found', 0)))
    table.add_row("Emails Found", str(summary.get('emails_found', 0)))
    table.add_row("LinkedIn Profiles", str(summary.get('linkedin_profiles_extracted', 0)))
    table.add_row("Success Rate", f"{summary.get('success_rate', 0):.1f}%")
    
    if summary.get('duration_seconds'):
        table.add_row("Duration", f"{summary['duration_seconds']:.1f} seconds")
    
    console.print(table)


def _display_prospects(prospects: List):
    """Display prospects in a formatted table."""
    if not prospects:
        console.print("[yellow]No prospects found.[/yellow]")
        return
    
    table = Table(title="Found Prospects")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Company", style="blue")
    table.add_column("Email", style="magenta")
    table.add_column("LinkedIn", style="yellow")
    
    for prospect in prospects:
        table.add_row(
            prospect.name,
            prospect.role,
            prospect.company,
            prospect.email or "Not found",
            "Yes" if prospect.linkedin_url else "No"
        )
    
    console.print(table)

def _display_email_results(results: Dict[str, Any], output_file: Optional[str]):
    """Display email generation results."""
    successful = results.get('successful', [])
    failed = results.get('failed', [])
    emails_generated = results.get('emails_generated', 0)
    
    console.print(f"[green]Generated {emails_generated} emails[/green]")
    
    if failed:
        console.print(f"[red]Failed to generate {len(failed)} emails[/red]")
        for failure in failed:
            console.print(f"  [red]• {failure.get('prospect_name', 'Unknown')}: {failure.get('error', 'Unknown error')}[/red]")
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"[green]Results saved to: {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving results: {e}[/red]")
    
    # Display first few emails as preview
    for i, result in enumerate(successful[:3]):
        email_content = result.get('email_content', {})
        panel = Panel(
            f"Subject: {email_content.get('subject', 'N/A')}\n\n{email_content.get('body', 'N/A')[:200]}...",
            title=f"Email {i+1} Preview - {result.get('prospect_name', 'Unknown')}",
            border_style="blue"
        )
        console.print(panel)


def _display_status(status_info: Dict[str, Any]):
    """Display workflow status information."""
    table = Table(title="Workflow Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    for component, info in status_info.items():
        if isinstance(info, dict):
            status = info.get('status', 'Unknown')
            details = info.get('details', '')
        else:
            status = str(info)
            details = ''
        
        table.add_row(component.replace('_', ' ').title(), status, details)
    
    console.print(table)


def _display_batch_history(history: List[Dict[str, Any]]):
    """Display batch processing history."""
    if not history:
        console.print("[yellow]No batch history found.[/yellow]")
        return
    
    table = Table(title="Batch Processing History")
    table.add_column("Batch ID", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Companies", style="blue")
    table.add_column("Prospects", style="magenta")
    table.add_column("Start Time", style="yellow")
    
    for batch in history:
        table.add_row(
            batch.get('batch_id', 'N/A'),
            batch.get('status', 'N/A'),
            f"{batch.get('processed_companies', 0)}/{batch.get('total_companies', 0)}",
            str(batch.get('total_prospects', 0)),
            batch.get('start_time', 'N/A')
        )
    
    console.print(table)

def _display_analysis_results(results: Dict[str, Any]):
    """Display product analysis results."""
    summary = results.get('summary', {})
    
    table = Table(title="Product Analysis Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Companies Analyzed", str(summary.get('companies_analyzed', 0)))
    table.add_row("Products Analyzed", str(summary.get('products_analyzed', 0)))
    table.add_row("AI Parsing Success", f"{summary.get('ai_parsing_success_rate', 0):.1f}%")
    table.add_row("Features Extracted", str(summary.get('features_extracted', 0)))
    table.add_row("Market Insights", str(summary.get('market_insights_generated', 0)))
    
    if summary.get('duration_seconds'):
        table.add_row("Duration", f"{summary['duration_seconds']:.1f} seconds")
    
    console.print(table)
    
    # Display sample analysis results
    analyses = results.get('analyses', [])
    for i, analysis in enumerate(analyses[:2]):
        panel = Panel(
            f"Company: {analysis.get('company_name', 'N/A')}\n"
            f"Product: {analysis.get('product_name', 'N/A')}\n"
            f"Market Position: {analysis.get('market_position', 'N/A')[:100]}...\n"
            f"Key Features: {', '.join(analysis.get('key_features', [])[:3])}",
            title=f"Analysis {i+1} Preview",
            border_style="green"
        )
        console.print(panel)


def _display_sending_results(results: Dict[str, Any]):
    """Display email sending results."""
    total_sent = results.get('total_sent', 0)
    total_failed = results.get('total_failed', 0)
    successful = results.get('successful', [])
    failed = results.get('failed', [])
    
    total_attempts = total_sent + total_failed
    success_rate = (total_sent / total_attempts * 100) if total_attempts > 0 else 0
    
    table = Table(title="Email Sending Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Emails Sent", str(total_sent))
    table.add_row("Successful Deliveries", str(len(successful)))
    table.add_row("Failed Deliveries", str(total_failed))
    table.add_row("Success Rate", f"{success_rate:.1f}%")
    
    console.print(table)
    
    # Display successful sends
    if successful:
        console.print(f"\n[green]Successfully sent {len(successful)} emails:[/green]")
        for success in successful[:5]:  # Show first 5 successes
            console.print(f"[green]• {success.get('prospect_name', 'Unknown')} ({success.get('email', 'Unknown')})[/green]")
    
    # Display any errors
    if failed:
        console.print(f"\n[red]Failed to send {len(failed)} emails:[/red]")
        for failure in failed[:5]:  # Show first 5 errors
            console.print(f"[red]• {failure.get('prospect_name', 'Unknown')}: {failure.get('error', 'Unknown error')}[/red]")

def _display_validation_results(results: Dict[str, Any]):
    """Display API validation results."""
    table = Table(title="API Connection Validation")
    table.add_column("Service", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    for service, info in results.items():
        if isinstance(info, dict):
            status = info.get('status', 'Unknown')
            details = info.get('details', '')
        else:
            status = str(info)
            details = ''
        
        table.add_row(service.replace('_', ' ').title(), status, details)
    
    console.print(table)


def _display_enhanced_results(results: Dict[str, Any]):
    """Display enhanced workflow results."""
    summary = results.get('summary', {})
    
    table = Table(title="Enhanced Workflow Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Companies Processed", str(summary.get('companies_processed', 0)))
    table.add_row("Prospects Found", str(summary.get('prospects_found', 0)))
    table.add_row("AI Parsing Success", f"{summary.get('ai_parsing_success_rate', 0):.1f}%")
    table.add_row("Products Analyzed", str(summary.get('products_analyzed', 0)))
    table.add_row("Emails Generated", str(summary.get('emails_generated', 0)))
    table.add_row("Emails Sent", str(summary.get('emails_sent', 0)))
    
    if summary.get('duration_seconds'):
        table.add_row("Duration", f"{summary['duration_seconds']:.1f} seconds")
    
    console.print(table)


def _display_component_test_results(results: Dict[str, Any]):
    """Display component test results."""
    for component, result in results.items():
        if isinstance(result, dict):
            status = result.get('status', 'Unknown')
            details = result.get('details', '')
            data = result.get('data', {})
            
            panel = Panel(
                f"Status: {status}\n\nDetails: {details}",
                title=f"{component.replace('_', ' ').title()} Test Results",
                border_style="green" if status == "Success" else "red"
            )
            console.print(panel)
            
            if data:
                console.print(json.dumps(data, indent=2, default=str)[:500])
                if len(json.dumps(data, default=str)) > 500:
                    console.print("... (output truncated)")
        else:
            console.print(f"{component}: {result}")


# Add profile commands to CLI
cli.add_command(profile)


@cli.command('configure-ai')
@click.option('--provider', type=click.Choice(['openai', 'azure-openai', 'anthropic', 'google', 'deepseek']),
              help='AI provider to configure')
@click.option('--interactive', is_flag=True, default=True, help='Interactive configuration mode')
@click.option('--reconfigure', is_flag=True, help='Reconfigure an already configured provider')
@click.pass_context
def configure_ai(ctx, provider, interactive, reconfigure):
    """Configure AI provider settings interactively."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would configure AI provider: {provider or 'interactive selection'}[/yellow]")
            if reconfigure:
                console.print("[yellow]DRY-RUN: Would reconfigure existing provider[/yellow]")
            return
        
        # Get provider manager
        provider_manager = get_provider_manager()
        provider_manager.configure(cli_config.base_config)
        
        # If no provider specified, show selection menu
        if not provider:
            console.print("[blue]Available AI Providers:[/blue]")
            providers = provider_manager.list_providers()
            
            table = Table()
            table.add_column("Provider", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Status", style="green")
            
            for p in providers:
                try:
                    info = provider_manager.get_provider_info(p)
                    configured = p in provider_manager.list_configured_providers()
                    if reconfigure:
                        status = "✅ Configured" if configured else "❌ Not configured"
                    else:
                        status = "✅ Configured" if configured else "❌ Not configured"
                    table.add_row(p, info.description, status)
                except Exception as e:
                    table.add_row(p, "Unknown", f"❌ Error: {str(e)}")
            
            console.print(table)
            
            # Interactive provider selection
            if reconfigure:
                configured_providers = provider_manager.list_configured_providers()
                if not configured_providers:
                    console.print("[yellow]No configured providers to reconfigure[/yellow]")
                    return 0
                provider = click.prompt(
                    "\nSelect provider to reconfigure",
                    type=click.Choice(configured_providers),
                    show_choices=True
                )
            else:
                provider = click.prompt(
                    "\nSelect provider to configure",
                    type=click.Choice(providers),
                    show_choices=True
                )
        
        # Get provider info
        try:
            provider_info = provider_manager.get_provider_info(provider)
        except ValueError as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return 1
        
        console.print(f"\n[blue]Configuring {provider} ({provider_info.description})[/blue]")
        
        # Collect configuration interactively
        config = {}
        
        # Required configuration
        console.print(f"\n[yellow]Required Configuration:[/yellow]")
        for field in provider_info.required_config:
            if field.endswith('_api_key'):
                # Handle API keys with hidden input
                field_name = field.replace('_', ' ').title()
                value = click.prompt(f"{field_name}", hide_input=True)
                config[field] = value
            elif field == 'azure_openai_endpoint':
                value = click.prompt("Azure OpenAI Endpoint (e.g., https://your-resource.openai.azure.com/)")
                config[field] = value
            elif field == 'azure_openai_deployment_name':
                value = click.prompt("Azure OpenAI Deployment Name")
                config[field] = value
            else:
                field_name = field.replace('_', ' ').title()
                value = click.prompt(f"{field_name}")
                config[field] = value
        
        # Optional configuration
        if provider_info.optional_config:
            console.print(f"\n[yellow]Optional Configuration (press Enter to skip):[/yellow]")
            for field in provider_info.optional_config:
                if field == 'model':
                    # Show available models for the provider with interactive selection
                    available_models = []
                    default_model = ""
                    
                    if provider == "openai":
                        available_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
                        default_model = "gpt-4"
                    elif provider == "azure-openai":
                        console.print("[yellow]For Azure OpenAI, use your deployment name as the model[/yellow]")
                        value = click.prompt(f"Model/Deployment name (optional)", default="", show_default=False)
                        if value:
                            config[field] = value
                        continue
                    elif provider == "anthropic":
                        available_models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]
                        default_model = "claude-3-sonnet-20240229"
                    elif provider == "google":
                        available_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]
                        default_model = "gemini-2.5-flash"
                    elif provider == "deepseek":
                        available_models = ["deepseek-chat", "deepseek-coder"]
                        default_model = "deepseek-chat"
                    
                    if available_models:
                        console.print(f"\n[cyan]Available models for {provider}:[/cyan]")
                        
                        # Create a nice table showing models with descriptions
                        from rich.table import Table
                        model_table = Table()
                        model_table.add_column("Option", style="cyan")
                        model_table.add_column("Model", style="green")
                        model_table.add_column("Description", style="white")
                        
                        model_descriptions = {
                            # OpenAI models
                            "gpt-3.5-turbo": "Fast and cost-effective",
                            "gpt-4": "Most capable GPT-4 model",
                            "gpt-4-turbo": "Latest GPT-4 with improved performance",
                            "gpt-4o": "Optimized GPT-4 model",
                            "gpt-4o-mini": "Smaller, faster GPT-4 variant",
                            
                            # Anthropic models
                            "claude-3-haiku-20240307": "Fast and efficient",
                            "claude-3-sonnet-20240229": "Balanced performance and speed",
                            "claude-3-opus-20240229": "Most capable Claude model",
                            "claude-3-5-sonnet-20241022": "Latest Claude 3.5 Sonnet",
                            
                            # Google models
                            "gemini-2.5-pro": "Latest and most capable (2M+ context)",
                            "gemini-2.5-flash": "Latest fast model (recommended)",
                            "gemini-2.5-flash-lite": "Ultra-fast lightweight model",
                            "gemini-1.5-pro": "Previous generation pro model",
                            "gemini-1.5-flash": "Previous generation flash model",
                            
                            # DeepSeek models
                            "deepseek-chat": "General conversation model",
                            "deepseek-coder": "Specialized for coding tasks"
                        }
                        
                        for i, model in enumerate(available_models, 1):
                            description = model_descriptions.get(model, "")
                            is_default = " (default)" if model == default_model else ""
                            model_table.add_row(str(i), f"{model}{is_default}", description)
                        
                        console.print(model_table)
                        
                        # Interactive model selection
                        console.print(f"\n[yellow]Select a model (1-{len(available_models)}) or press Enter for default ({default_model}):[/yellow]")
                        
                        while True:
                            choice = click.prompt("Model choice", default="", show_default=False)
                            
                            if not choice:  # User pressed Enter, use default
                                config[field] = default_model
                                console.print(f"[green]Selected: {default_model} (default)[/green]")
                                break
                            
                            try:
                                choice_num = int(choice)
                                if 1 <= choice_num <= len(available_models):
                                    selected_model = available_models[choice_num - 1]
                                    config[field] = selected_model
                                    console.print(f"[green]Selected: {selected_model}[/green]")
                                    break
                                else:
                                    console.print(f"[red]Please enter a number between 1 and {len(available_models)}[/red]")
                            except ValueError:
                                # Maybe user typed the model name directly
                                if choice in available_models:
                                    config[field] = choice
                                    console.print(f"[green]Selected: {choice}[/green]")
                                    break
                                else:
                                    console.print(f"[red]Invalid choice. Please enter a number (1-{len(available_models)}) or valid model name[/red]")
                    else:
                        # Fallback for unknown providers
                        value = click.prompt(f"Model (optional)", default="", show_default=False)
                        if value:
                            config[field] = value
                elif field == 'temperature':
                    value = click.prompt("Temperature (0.0-2.0, optional)", default="", show_default=False)
                    if value:
                        try:
                            config[field] = float(value)
                        except ValueError:
                            console.print("[yellow]Invalid temperature, skipping[/yellow]")
                elif field == 'max_tokens':
                    value = click.prompt("Max tokens (optional)", default="", show_default=False)
                    if value:
                        try:
                            config[field] = int(value)
                        except ValueError:
                            console.print("[yellow]Invalid max tokens, skipping[/yellow]")
        
        # Test configuration
        console.print(f"\n[blue]Testing {provider} configuration...[/blue]")
        
        # Create temporary provider instance for testing
        try:
            provider_class = provider_manager._load_provider_class(provider)
            
            # Map config fields to provider-specific format
            provider_config = {}
            if provider == "openai":
                provider_config = {
                    "api_key": config.get("openai_api_key"),
                    "model": config.get("model", "gpt-3.5-turbo"),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000)
                }
            elif provider == "azure-openai":
                provider_config = {
                    "api_key": config.get("azure_openai_api_key"),
                    "endpoint": config.get("azure_openai_endpoint"),
                    "deployment_name": config.get("azure_openai_deployment_name"),
                    "api_version": config.get("azure_openai_api_version", "2024-02-15-preview"),
                    "model": config.get("model", config.get("azure_openai_deployment_name")),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000)
                }
            elif provider == "anthropic":
                provider_config = {
                    "api_key": config.get("anthropic_api_key"),
                    "model": config.get("model", "claude-3-sonnet-20240229"),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000)
                }
            elif provider == "google":
                provider_config = {
                    "api_key": config.get("google_api_key"),
                    "model": config.get("model", "gemini-pro"),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000)
                }
            elif provider == "deepseek":
                provider_config = {
                    "api_key": config.get("deepseek_api_key"),
                    "model": config.get("model", "deepseek-chat"),
                    "temperature": config.get("temperature", 0.7),
                    "max_tokens": config.get("max_tokens", 1000)
                }
            
            # Test the provider
            test_provider = provider_class(provider_config)
            validation_result = test_provider.validate_config()
            
            if validation_result.status.value == "success":
                console.print("[green]Configuration validation passed[/green]")
                
                # Test connection
                connection_result = test_provider.test_connection()
                if connection_result.status.value == "success":
                    console.print("[green]✅ Connection test passed[/green]")
                else:
                    console.print(f"[yellow]⚠️ Connection test failed: {connection_result.message}[/yellow]")
                    if not click.confirm("Continue with configuration anyway?"):
                        return 1
            else:
                console.print(f"[red]❌ Configuration validation failed: {validation_result.message}[/red]")
                return 1
        
        except Exception as e:
            console.print(f"[red]❌ Configuration test failed: {str(e)}[/red]")
            if not click.confirm("Continue with configuration anyway?"):
                return 1
        
        # Save configuration to environment file
        env_file = Path(".env")
        env_updates = {}
        
        # Map configuration to environment variables
        if provider == "openai":
            env_updates["AI_PROVIDER"] = "openai"
            env_updates["OPENAI_API_KEY"] = config.get("openai_api_key")
        elif provider == "azure-openai":
            env_updates["AI_PROVIDER"] = "azure-openai"
            env_updates["AZURE_OPENAI_API_KEY"] = config.get("azure_openai_api_key")
            env_updates["AZURE_OPENAI_ENDPOINT"] = config.get("azure_openai_endpoint")
            env_updates["AZURE_OPENAI_DEPLOYMENT_NAME"] = config.get("azure_openai_deployment_name")
            if config.get("azure_openai_api_version"):
                env_updates["AZURE_OPENAI_API_VERSION"] = config.get("azure_openai_api_version")
        elif provider == "anthropic":
            env_updates["AI_PROVIDER"] = "anthropic"
            env_updates["ANTHROPIC_API_KEY"] = config.get("anthropic_api_key")
        elif provider == "google":
            env_updates["AI_PROVIDER"] = "google"
            env_updates["GOOGLE_API_KEY"] = config.get("google_api_key")
        elif provider == "deepseek":
            env_updates["AI_PROVIDER"] = "deepseek"
            env_updates["DEEPSEEK_API_KEY"] = config.get("deepseek_api_key")
        
        # Add optional configuration
        if config.get("model"):
            env_updates["AI_MODEL"] = config.get("model")
        if config.get("temperature"):
            env_updates["AI_TEMPERATURE"] = str(config.get("temperature"))
        if config.get("max_tokens"):
            env_updates["AI_MAX_TOKENS"] = str(config.get("max_tokens"))
        
        # Update .env file
        _update_env_file(env_updates)
        
        console.print(f"\n[green]✅ {provider} configuration saved successfully![/green]")
        console.print(f"[dim]Configuration saved to .env file[/dim]")
        
        # Ask if user wants to set as active provider
        if click.confirm(f"Set {provider} as the active AI provider?", default=True):
            env_updates_active = {"AI_PROVIDER": provider}
            _update_env_file(env_updates_active)
            console.print(f"[green]✅ {provider} set as active provider[/green]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Configuration failed: {str(e)}[/red]")
        return 1


@cli.command('list-ai-providers')
@click.option('--show-config', is_flag=True, help='Show configuration details for each provider')
@click.pass_context
def list_ai_providers(ctx, show_config):
    """List available and configured AI providers."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would list AI providers[/yellow]")
            return
        
        # Get provider manager
        provider_manager = get_provider_manager()
        provider_manager.configure(cli_config.base_config)
        
        # Get provider status
        status = provider_manager.get_provider_status()
        
        console.print(f"[blue]AI Provider Status[/blue]")
        console.print(f"Active Provider: [green]{status['active_provider'] or 'None'}[/green]")
        console.print(f"Total Registered: {status['total_registered']}")
        console.print(f"Total Configured: {status['total_configured']}")
        
        # Create providers table
        table = Table(title="Available AI Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Status", style="green")
        table.add_column("Config Valid", style="yellow")
        
        if show_config:
            table.add_column("Configuration", style="dim")
        
        for provider_name, provider_status in status['providers'].items():
            # Status indicator
            if provider_status['configured']:
                if provider_status.get('config_valid', False):
                    status_text = "✅ Ready"
                else:
                    status_text = "⚠️ Config Issues"
            else:
                status_text = "❌ Not Configured"
            
            # Config validation
            config_valid = "✅ Valid" if provider_status.get('config_valid', False) else "❌ Invalid"
            if provider_status.get('validation_message'):
                config_valid += f" ({provider_status['validation_message'][:30]}...)"
            
            row = [
                provider_name,
                provider_status['description'][:50] + "..." if len(provider_status['description']) > 50 else provider_status['description'],
                status_text,
                config_valid if provider_status['configured'] else "N/A"
            ]
            
            if show_config and provider_status['configured']:
                config_info = provider_status.get('config', {})
                # Mask sensitive information
                masked_config = {}
                for key, value in config_info.items():
                    if 'key' in key.lower() or 'token' in key.lower():
                        masked_config[key] = f"{str(value)[:8]}..." if value else "Not set"
                    else:
                        masked_config[key] = value
                row.append(str(masked_config)[:50] + "...")
            elif show_config:
                row.append("Not configured")
            
            table.add_row(*row)
        
        console.print(table)
        
        # Show required configuration for unconfigured providers
        unconfigured = [name for name, status in status['providers'].items() if not status['configured']]
        if unconfigured:
            console.print(f"\n[yellow]To configure providers, run:[/yellow]")
            for provider in unconfigured[:3]:  # Show first 3
                console.print(f"  python cli.py configure-ai --provider {provider}")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Failed to list providers: {str(e)}[/red]")
        return 1


@cli.command('validate-ai-config')
@click.option('--provider', help='Specific provider to validate (validates all if not specified)')
@click.option('--test-connection', is_flag=True, help='Test actual API connections')
@click.pass_context
def validate_ai_config(ctx, provider, test_connection):
    """Validate AI provider configurations and test connections."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would validate AI config for {provider or 'all providers'}[/yellow]")
            return
        
        # Get provider manager
        provider_manager = get_provider_manager()
        provider_manager.configure(cli_config.base_config)
        
        # Determine which providers to validate
        if provider:
            if provider not in provider_manager.list_providers():
                console.print(f"[red]❌ Unknown provider: {provider}[/red]")
                return 1
            providers_to_validate = [provider]
        else:
            providers_to_validate = provider_manager.list_configured_providers()
        
        if not providers_to_validate:
            console.print("[yellow]⚠️ No configured providers to validate[/yellow]")
            console.print("[dim]Run 'python cli.py configure-ai' to set up a provider[/dim]")
            return 1
        
        console.print(f"[blue]Validating {len(providers_to_validate)} provider(s)...[/blue]")
        
        # Validate each provider
        results = {}
        for provider_name in providers_to_validate:
            console.print(f"\n[cyan]Validating {provider_name}...[/cyan]")
            
            try:
                validation_result = provider_manager.validate_provider(provider_name)
                results[provider_name] = validation_result
                
                if validation_result.status.value == "success":
                    console.print(f"[green]✅ {provider_name}: Configuration valid[/green]")
                    
                    if test_connection:
                        console.print(f"[blue]Testing {provider_name} connection...[/blue]")
                        provider_instance = provider_manager.get_provider(provider_name)
                        connection_result = provider_instance.test_connection()
                        
                        if connection_result.status.value == "success":
                            console.print(f"[green]✅ {provider_name}: Connection successful[/green]")
                        else:
                            console.print(f"[red]❌ {provider_name}: Connection failed - {connection_result.message}[/red]")
                            results[provider_name] = connection_result
                
                elif validation_result.status.value == "warning":
                    console.print(f"[yellow]⚠️ {provider_name}: {validation_result.message}[/yellow]")
                else:
                    console.print(f"[red]❌ {provider_name}: {validation_result.message}[/red]")
                    
            except Exception as e:
                console.print(f"[red]❌ {provider_name}: Validation error - {str(e)}[/red]")
                results[provider_name] = f"Error: {str(e)}"
        
        # Summary table
        console.print(f"\n[blue]Validation Summary:[/blue]")
        table = Table()
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Message", style="yellow")
        
        success_count = 0
        for provider_name, result in results.items():
            if hasattr(result, 'status'):
                status = result.status.value
                message = result.message
                if status == "success":
                    success_count += 1
                    status_display = "✅ Valid"
                elif status == "warning":
                    status_display = "⚠️ Warning"
                else:
                    status_display = "❌ Invalid"
            else:
                status_display = "❌ Error"
                message = str(result)
            
            table.add_row(provider_name, status_display, message[:60] + "..." if len(message) > 60 else message)
        
        console.print(table)
        
        # Final status
        if success_count == len(results):
            console.print(f"\n[green]✅ All {success_count} provider(s) validated successfully![/green]")
            return 0
        else:
            console.print(f"\n[yellow]⚠️ {success_count}/{len(results)} provider(s) validated successfully[/yellow]")
            return 1
        
    except Exception as e:
        console.print(f"[red]❌ Validation failed: {str(e)}[/red]")
        return 1


@cli.command('set-ai-model')
@click.argument('provider_name')
@click.option('--model', help='Specific model to set (interactive selection if not provided)')
@click.pass_context
def set_ai_model(ctx, provider_name, model):
    """Set the model for a configured AI provider."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would set model for {provider_name} to {model or 'interactive selection'}[/yellow]")
            return
        
        # Get provider manager
        provider_manager = get_provider_manager()
        provider_manager.configure(cli_config.base_config)
        
        # Check if provider exists and is configured
        if provider_name not in provider_manager.list_providers():
            console.print(f"[red]❌ Unknown provider: {provider_name}[/red]")
            console.print(f"[dim]Available providers: {', '.join(provider_manager.list_providers())}[/dim]")
            return 1
        
        if provider_name not in provider_manager.list_configured_providers():
            console.print(f"[red]❌ Provider '{provider_name}' is not configured[/red]")
            console.print(f"[dim]Run 'python cli.py configure-ai --provider {provider_name}' to configure it[/dim]")
            return 1
        
        # Get available models for the provider
        available_models = []
        default_model = ""
        
        if provider_name == "openai":
            available_models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
            default_model = "gpt-4"
        elif provider_name == "azure-openai":
            console.print("[yellow]For Azure OpenAI, specify your deployment name as the model[/yellow]")
            if not model:
                model = click.prompt("Deployment name")
        elif provider_name == "anthropic":
            available_models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]
            default_model = "claude-3-sonnet-20240229"
        elif provider_name == "google":
            available_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]
            default_model = "gemini-2.5-flash"
        elif provider_name == "deepseek":
            available_models = ["deepseek-chat", "deepseek-coder"]
            default_model = "deepseek-chat"
        
        # If model not specified and we have available models, show selection
        if not model and available_models:
            console.print(f"\n[cyan]Available models for {provider_name}:[/cyan]")
            
            from rich.table import Table
            model_table = Table()
            model_table.add_column("Option", style="cyan")
            model_table.add_column("Model", style="green")
            model_table.add_column("Description", style="white")
            
            model_descriptions = {
                # OpenAI models
                "gpt-3.5-turbo": "Fast and cost-effective",
                "gpt-4": "Most capable GPT-4 model",
                "gpt-4-turbo": "Latest GPT-4 with improved performance",
                "gpt-4o": "Optimized GPT-4 model",
                "gpt-4o-mini": "Smaller, faster GPT-4 variant",
                
                # Anthropic models
                "claude-3-haiku-20240307": "Fast and efficient",
                "claude-3-sonnet-20240229": "Balanced performance and speed",
                "claude-3-opus-20240229": "Most capable Claude model",
                "claude-3-5-sonnet-20241022": "Latest Claude 3.5 Sonnet",
                
                # Google models
                "gemini-2.5-pro": "Latest and most capable (2M+ context)",
                "gemini-2.5-flash": "Latest fast model (recommended)",
                "gemini-2.5-flash-lite": "Ultra-fast lightweight model",
                "gemini-1.5-pro": "Previous generation pro model",
                "gemini-1.5-flash": "Previous generation flash model",
                
                # DeepSeek models
                "deepseek-chat": "General conversation model",
                "deepseek-coder": "Specialized for coding tasks"
            }
            
            for i, model_name in enumerate(available_models, 1):
                description = model_descriptions.get(model_name, "")
                is_default = " (default)" if model_name == default_model else ""
                model_table.add_row(str(i), f"{model_name}{is_default}", description)
            
            console.print(model_table)
            
            # Interactive model selection
            console.print(f"\n[yellow]Select a model (1-{len(available_models)}) or press Enter for default ({default_model}):[/yellow]")
            
            while True:
                choice = click.prompt("Model choice", default="", show_default=False)
                
                if not choice:  # User pressed Enter, use default
                    model = default_model
                    console.print(f"[green]Selected: {model} (default)[/green]")
                    break
                
                try:
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(available_models):
                        model = available_models[choice_num - 1]
                        console.print(f"[green]Selected: {model}[/green]")
                        break
                    else:
                        console.print(f"[red]Please enter a number between 1 and {len(available_models)}[/red]")
                except ValueError:
                    # Maybe user typed the model name directly
                    if choice in available_models:
                        model = choice
                        console.print(f"[green]Selected: {model}[/green]")
                        break
                    else:
                        console.print(f"[red]Invalid choice. Please enter a number (1-{len(available_models)}) or valid model name[/red]")
        
        if not model:
            console.print("[red]❌ No model specified[/red]")
            return 1
        
        # Update .env file with new model
        env_updates = {"AI_MODEL": model}
        _update_env_file(env_updates)
        
        console.print(f"[green]✅ Model for {provider_name} set to: {model}[/green]")
        
        # Test the new model configuration
        console.print(f"[blue]Testing {provider_name} with model {model}...[/blue]")
        validation_result = provider_manager.validate_provider(provider_name)
        
        if validation_result.status.value == "success":
            console.print(f"[green]✅ Model configuration validated successfully[/green]")
        else:
            console.print(f"[yellow]⚠️ Model validation warning: {validation_result.message}[/yellow]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Failed to set model: {str(e)}[/red]")
        return 1


@cli.command('set-ai-provider')
@click.argument('provider_name')
@click.pass_context
def set_ai_provider(ctx, provider_name):
    """Set the active AI provider."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would set active AI provider to {provider_name}[/yellow]")
            return
        
        # Get provider manager
        provider_manager = get_provider_manager()
        provider_manager.configure(cli_config.base_config)
        
        # Check if provider exists and is configured
        if provider_name not in provider_manager.list_providers():
            console.print(f"[red]❌ Unknown provider: {provider_name}[/red]")
            console.print(f"[dim]Available providers: {', '.join(provider_manager.list_providers())}[/dim]")
            return 1
        
        if provider_name not in provider_manager.list_configured_providers():
            console.print(f"[red]❌ Provider '{provider_name}' is not configured[/red]")
            console.print(f"[dim]Run 'python cli.py configure-ai --provider {provider_name}' to configure it[/dim]")
            return 1
        
        # Validate provider before setting as active
        console.print(f"[blue]Validating {provider_name}...[/blue]")
        validation_result = provider_manager.validate_provider(provider_name)
        
        if validation_result.status.value != "success":
            console.print(f"[red]❌ Cannot set {provider_name} as active: {validation_result.message}[/red]")
            return 1
        
        # Set as active provider
        provider_manager.set_active_provider(provider_name)
        
        # Update .env file
        env_updates = {"AI_PROVIDER": provider_name}
        _update_env_file(env_updates)
        
        console.print(f"[green]✅ Active AI provider set to: {provider_name}[/green]")
        
        # Show provider info
        try:
            provider_info = provider_manager.get_provider_info(provider_name)
            console.print(f"[dim]Description: {provider_info.description}[/dim]")
            
            # Show current configuration (masked)
            provider_instance = provider_manager.get_provider(provider_name)
            config = provider_instance.get_config()
            masked_config = {}
            for key, value in config.items():
                if 'key' in key.lower() or 'token' in key.lower():
                    masked_config[key] = f"{str(value)[:8]}..." if value else "Not set"
                else:
                    masked_config[key] = value
            
            console.print(f"[dim]Configuration: {masked_config}[/dim]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️ Could not retrieve provider details: {str(e)}[/yellow]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Failed to set active provider: {str(e)}[/red]")
        return 1


@cli.command('setup-issues')
@click.pass_context
def setup_issues(ctx):
    """>> Set up the Issues database for tracking user feedback."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would set up Issues database[/yellow]")
            return
        
        if not setup_issues_database:
            console.print("[red]❌ Setup issues function not available[/red]")
            return 1
        
        console.print("[blue]Setting up Issues database...[/blue]")
        result = setup_issues_database(cli_config.base_config)
        
        if result and result.get('success'):
            console.print("[green]✅ Issues database setup completed successfully![/green]")
            console.print(f"[cyan]💡 Test it: python cli.py report-issue \"Test issue\"[/cyan]")
            return 0
        else:
            console.print("[red]❌ Issues database setup failed[/red]")
            return 1
            
    except Exception as e:
        console.print(f"[red]Error setting up issues database: {str(e)}[/red]")
        suggest_issue_report("config", str(e))
        return 1


@cli.command('report-issue')
@click.argument('description', required=False)
@click.option('--category', '-c', help='Issue category (Bug, Improvement, Question, Setup)')
@click.option('--title', '-t', help='Custom issue title')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode for detailed reporting')
@click.pass_context
def report_issue(ctx, description, category, title, interactive):
    """>> Report an issue or provide feedback.
    
    EXAMPLES:
    • python cli.py report-issue "Email generation failed"
    • python cli.py report-issue --interactive
    • python cli.py report-issue "How do I set up LinkedIn scraping?" --category Question
    """
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would report issue[/yellow]")
            return
        
        # Initialize issue reporter
        issue_reporter = IssueReporter(cli_config.base_config)
        
        # Interactive mode
        if interactive or not description:
            console.print("[cyan]🔧 Issue Reporter[/cyan]")
            console.print("Help us improve by reporting issues or providing feedback!\n")
            
            if not description:
                description = click.prompt("What's the issue or feedback?")
            
            if not title:
                title = click.prompt("Brief title (leave empty for auto-generated)", default="", show_default=False)
            
            if not category:
                console.print("\n[cyan]Categories:[/cyan]")
                console.print("• Bug - Something doesn't work")
                console.print("• Improvement - Enhancement request")
                console.print("• Question - Need help or clarification")
                console.print("• Setup - Installation or configuration issues")
                
                category = click.prompt("Category", default="Bug", show_default=True)
            
            # Ask for additional context
            additional_info = click.prompt("Any additional context? (optional)", default="", show_default=False)
            
            # Combine description with additional info
            if additional_info:
                description += f"\n\nAdditional context: {additional_info}"
        
        # Report the issue
        if title or category:
            issue_id = issue_reporter.report_with_context(
                description=description,
                title=title if title else None,
                category=category
            )
        else:
            issue_id = issue_reporter.quick_report(description, category)
        
        # Success feedback
        console.print(f"\n[green]📝 Issue reported: {issue_id}[/green]")
        console.print(f"[dim]Thank you for the feedback! We'll look into it.[/dim]")
        
        # Show how to check status
        console.print(f"\n[cyan]💡 Check status with:[/cyan]")
        console.print(f"[dim]python cli.py list-issues[/dim]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Failed to report issue: {str(e)}[/red]")
        console.print("[yellow]💡 You can also report this manually in our GitHub issues[/yellow]")
        return 1


@cli.command('list-issues')
@click.option('--status', '-s', help='Filter by status (Open, In Progress, Resolved, Closed)')
@click.option('--limit', '-l', default=10, help='Maximum number of issues to show')
@click.pass_context
def list_issues(ctx, status, limit):
    """>> List your reported issues.
    
    EXAMPLES:
    • python cli.py list-issues
    • python cli.py list-issues --status Open
    • python cli.py list-issues --limit 20
    """
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would list issues[/yellow]")
            return
        
        # Initialize issue reporter
        issue_reporter = IssueReporter(cli_config.base_config)
        
        # Get issues
        issues = issue_reporter.list_my_issues(status=status, limit=limit)
        
        if not issues:
            console.print("[yellow]No issues found[/yellow]")
            if status:
                console.print(f"[dim]Try removing the status filter: python cli.py list-issues[/dim]")
            else:
                console.print(f"[dim]Report your first issue: python cli.py report-issue[/dim]")
            return
        
        # Create issues table
        table = Table(title=f"Your Issues ({len(issues)} found)")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Title", style="white", width=30)
        table.add_column("Category", style="blue", width=12)
        table.add_column("Status", style="green", width=12)
        table.add_column("Created", style="dim", width=12)
        
        for issue in issues:
            # Format date
            created_date = issue.created_at.strftime("%m/%d/%Y")
            
            # Truncate title if too long
            display_title = issue.title
            if len(display_title) > 27:
                display_title = display_title[:24] + "..."
            
            # Add status emoji
            status_emoji = {
                "Open": "[O]",
                "In Progress": "[P]", 
                "Resolved": "[R]",
                "Closed": "[C]"
            }
            status_display = f"{status_emoji.get(issue.status.value, '')} {issue.status.value}"
            
            table.add_row(
                issue.issue_id,
                display_title,
                issue.category.value,
                status_display,
                created_date
            )
        
        console.print(table)
        
        # Show usage hints
        console.print(f"\n[cyan]💡 Tips:[/cyan]")
        console.print(f"[dim]• Report new issue: python cli.py report-issue[/dim]")
        console.print(f"[dim]• Filter by status: python cli.py list-issues --status Open[/dim]")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Failed to list issues: {str(e)}[/red]")
        return 1


def _update_env_file(updates: Dict[str, str]) -> None:
    """Update .env file with new values."""
    env_file = Path(".env")
    
    # Read existing content
    existing_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            existing_lines = f.readlines()
    
    # Create a dictionary of existing variables
    existing_vars = {}
    for line in existing_lines:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            existing_vars[key] = value
    
    # Update with new values
    existing_vars.update(updates)
    
    # Write back to file
    with open(env_file, 'w') as f:
        # Write updated variables
        for key, value in existing_vars.items():
            f.write(f"{key}={value}\n")


if __name__ == '__main__':
    cli()
