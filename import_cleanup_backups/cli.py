#!/usr/bin/env python3
"""
Command-line interface for the Job Prospect Automation system.
"""

import click
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config
from utils.logging_config import setup_logging, get_logger
from models.data_models import CompanyData
from services.email_generator import EmailTemplate
from services.sender_profile_manager import SenderProfileManager
from cli_profile_commands import profile


console = Console()


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
    """🚀 Job Prospect Automation CLI - Complete automation workflow in one command!
    
    QUICK COMMANDS:
    • quick-start     - Complete setup + first campaign (beginners)
    • run-campaign    - Full workflow: discovery → emails → analytics
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

# Add the profile command group to the main CLI
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
        
        from setup_dashboard import setup_dashboard as setup_func
        
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
        
        from services.notification_manager import NotificationManager
        from controllers.prospect_automation_controller import ProspectAutomationController
        
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
        
        from services.notification_manager import NotificationManager
        from controllers.prospect_automation_controller import ProspectAutomationController
        
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
        
        from datetime import datetime
        from rich.table import Table
        
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
    """🚀 QUICK START: Complete setup and first campaign in one command!"""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print("[yellow]DRY-RUN: Would run complete quick-start workflow[/yellow]")
            return
        
        console.print(Panel.fit(
            "[bold green]🚀 Job Prospect Automation - Quick Start[/bold green]\n"
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
            from setup_dashboard import setup_dashboard as setup_func
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
        
        from datetime import datetime
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
            "[bold green]🎉 Quick Start Completed![/bold green]\n\n"
            "✅ Dashboard created in Notion\n"
            "✅ Companies discovered and processed\n"
            "✅ Prospects extracted and stored\n"
            "✅ Emails generated (ready for review)\n"
            "✅ Analytics updated\n\n"
            "Next steps:\n"
            "📊 Check your Notion dashboard\n"
            "📧 Review generated emails\n"
            "🚀 Run more campaigns with: python cli.py run-campaign",
            border_style="green"
        ))
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Quick start failed: {str(e)}[/red]")
        return 1


@cli.command('generate-emails-recent')
@click.option('--limit', '-l', default=10, help='Number of recent prospects to generate emails for')
@click.option('--template', type=click.Choice(['cold_outreach', 'referral_followup', 'product_interest', 'networking']), 
              default='cold_outreach', help='Email template type')
@click.option('--send', is_flag=True, help='Send emails immediately after generation')
@click.pass_context
def generate_emails_recent(ctx, limit, template, send):
    """📧 Generate emails for the most recently discovered prospects."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        if cli_config.dry_run:
            console.print(f"[yellow]DRY-RUN: Would generate emails for {limit} recent prospects[/yellow]")
            return
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        console.print(f"[blue]📧 Generating emails for {limit} most recent prospects...[/blue]")
        
        # Get recent prospects with emails
        prospects = controller.notion_manager.get_prospects()
        prospects_with_emails = [p for p in prospects if p.email]
        
        # Sort by created_at to get truly recent ones, then take the most recent
        prospects_with_emails.sort(key=lambda x: x.created_at, reverse=True)  # Most recent first
        recent_prospects = prospects_with_emails[:limit]  # Take first N (most recent)
        
        if not recent_prospects:
            console.print("[yellow]⚠️ No recent prospects with emails found.[/yellow]")
            console.print("[dim]Run discovery first: python cli.py discover --limit 5[/dim]")
            return 1
        
        prospect_ids = [p.id for p in recent_prospects]
        
        console.print(f"[dim]Found {len(recent_prospects)} recent prospects with emails:[/dim]")
        for p in recent_prospects:
            console.print(f"  • {p.name} at {p.company}")
        
        # Generate emails
        from services.email_generator import EmailTemplate
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
            console.print(f"\n[bold]📧 Generated Emails:[/bold]")
            for result in email_results.get('successful', [])[:3]:  # Show first 3
                console.print(f"  • {result['prospect_name']} at {result['company']}")
                console.print(f"    Subject: {result['email_content']['subject']}")
                console.print(f"    Preview: {result['email_content']['body'][:100]}...")
                console.print()
        
        # Send emails if requested
        if send and successful > 0:
            console.print(f"[blue]📤 Sending {successful} emails...[/blue]")
            
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
        
        console.print(f"\n[cyan]📊 Check your Notion Email Queue database for email details![/cyan]")
        
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
            profile = manager.create_profile_interactively()
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
                
                console.print(f"[green]✓ Set {abs_path} as default sender profile[/green]")
        
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
    """🚀 Run the COMPLETE automation workflow - from discovery to email sending!"""
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
            from setup_dashboard import setup_dashboard as setup_func
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
            from datetime import datetime
            campaign_name = f"Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        console.print(Panel.fit(
            f"[bold green]🚀 Starting Complete Campaign Workflow[/bold green]\n"
            f"Campaign: {campaign_name}\n"
            f"Target: {limit} companies\n"
            f"Generate Emails: {'Yes' if generate_emails else 'No'}\n"
            f"Send Emails: {'Yes' if send_emails else 'No'}",
            border_style="green"
        ))
        
        # Step 1: Discovery Pipeline
        console.print("\n[bold blue]📊 Step 1: Company Discovery & Prospect Extraction[/bold blue]")
        console.print("[dim]💡 Monitor real-time progress in your Notion dashboard[/dim]")
        
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
            console.print("[yellow]⚠️ No prospects found. Campaign completed.[/yellow]")
            return 0
        
        # Step 2: Email Generation (if requested)
        if generate_emails:
            console.print(f"\n[bold blue]📧 Step 2: Email Generation[/bold blue]")
            
            # Get prospect IDs from the results
            prospects = controller.notion_manager.get_prospects()
            recent_prospects = [p for p in prospects if p.id][-prospects_found:]  # Get most recent prospects
            prospect_ids = [p.id for p in recent_prospects if p.email]  # Only prospects with emails
            
            if not prospect_ids:
                console.print("[yellow]⚠️ No prospects with emails found for email generation.[/yellow]")
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
                    console.print(f"\n[bold blue]📤 Step 3: Email Sending[/bold blue]")
                    
                    send_results = controller.generate_and_send_outreach_emails(
                        prospect_ids=prospect_ids,
                        template_type=EmailTemplate.COLD_OUTREACH,
                        send_immediately=True,
                        delay_between_emails=2.0
                    )
                    
                    emails_sent = send_results.get('emails_sent', 0)
                    console.print(f"[green]✅ Emails sent: {emails_sent}[/green]")
        
        # Step 4: Update Analytics
        console.print(f"\n[bold blue]📈 Step 4: Analytics Update[/bold blue]")
        
        analytics_db_id = cli_config.base_config.analytics_db_id
        if analytics_db_id:
            success = controller.create_daily_summary(analytics_db_id)
            if success:
                console.print("[green]✅ Daily analytics updated[/green]")
            else:
                console.print("[yellow]⚠️ Analytics update failed[/yellow]")
        
        # Final Summary
        console.print(Panel.fit(
            f"[bold green]🎉 Campaign Completed Successfully![/bold green]\n\n"
            f"📊 Results Summary:\n"
            f"• Companies Processed: {results['summary']['companies_processed']}\n"
            f"• Prospects Found: {prospects_found}\n"
            f"• Emails Generated: {email_results.get('emails_generated', 0) if generate_emails else 'Skipped'}\n"
            f"• Emails Sent: {send_results.get('emails_sent', 0) if send_emails else 'Skipped'}\n"
            f"• Success Rate: {results['summary']['success_rate']:.1f}%\n"
            f"• Duration: {results['summary']['duration_seconds']:.1f} seconds\n\n"
            f"📱 Check your Notion dashboard for detailed progress and notifications!",
            border_style="green"
        ))
        
        # Show dashboard links
        if cli_config.base_config.dashboard_id:
            console.print(f"\n[cyan]🔗 Quick Links:[/cyan]")
            console.print(f"📊 Dashboard: https://notion.so/{cli_config.base_config.dashboard_id.replace('-', '')}")
            if cli_config.base_config.campaigns_db_id:
                console.print(f"🎯 Campaign Details: https://notion.so/{cli_config.base_config.campaigns_db_id.replace('-', '')}")
            if cli_config.base_config.analytics_db_id:
                console.print(f"📈 Analytics: https://notion.so/{cli_config.base_config.analytics_db_id.replace('-', '')}")
        
        return 0
        
    except Exception as e:
        console.print(f"[red]❌ Campaign failed: {str(e)}[/red]")
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
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        # Set sender profile if provided
        if sender_profile:
            controller.set_sender_profile(sender_profile)
        
        # Generate campaign name if not provided
        if not campaign_name:
            from datetime import datetime
            campaign_name = f"Discovery Campaign {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        console.print(f"[blue]Starting campaign: {campaign_name}[/blue]")
        console.print("[dim]💡 Monitor progress in your Notion dashboard[/dim]")
        
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
            console.print(f"\n[green]✅ Campaign '{campaign_progress['name']}' completed successfully![/green]")
            console.print(f"[dim]📊 Check your Notion dashboard for detailed progress and logs[/dim]")
        
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
            profile = manager.create_profile_interactively()
            controller.set_sender_profile_object(profile)
            console.print("[green]✓ Sender profile created successfully[/green]")
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
                
                console.print(f"[green]✓ Sender profile validation passed (completeness: {completeness:.1%})[/green]")
                controller.set_sender_profile_object(profile)
            else:
                controller.set_sender_profile(sender_profile)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating emails...", total=None)
            
            results = controller.generate_outreach_emails(ids, template_enum, send_immediately=send)
            
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
    """📤 Send the most recently generated emails that haven't been sent yet."""
    try:
        cli_config = CLIConfig(ctx.obj['config_file'], ctx.obj['dry_run'])
        
        controller = ProspectAutomationController(cli_config.base_config)
        
        console.print(f"[blue]📤 Finding {limit} most recent generated emails to send...[/blue]")
        
        from datetime import datetime
        
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
        if not click.confirm(f"\n📤 Send emails to {len(recent_unsent)} prospects?"):
            console.print("[yellow]Email sending cancelled.[/yellow]")
            return
        
        console.print(f"[blue]📤 Sending emails to {len(recent_unsent)} prospects...[/blue]")
        
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
        console.print("[green]✓ Configuration validation passed[/green]")
        
        # Validate sender profile if provided
        if check_profile:
            from services.sender_profile_manager import SenderProfileManager
            from models.data_models import ValidationError
            
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
                    console.print("[green]✓ Sender profile validation passed[/green]")
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
        profile = manager.create_profile_interactively()
        
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
    emails = results.get('emails', [])
    
    console.print(f"[green]Generated {len(emails)} emails[/green]")
    
    if output_file:
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            console.print(f"[green]Results saved to: {output_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving results: {e}[/red]")
    
    # Display first few emails as preview
    for i, email in enumerate(emails[:3]):
        panel = Panel(
            f"Subject: {email.get('subject', 'N/A')}\n\n{email.get('body', 'N/A')[:200]}...",
            title=f"Email {i+1} Preview",
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
    summary = results.get('summary', {})
    
    table = Table(title="Email Sending Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Emails Sent", str(summary.get('emails_sent', 0)))
    table.add_row("Successful Deliveries", str(summary.get('successful_deliveries', 0)))
    table.add_row("Failed Deliveries", str(summary.get('failed_deliveries', 0)))
    table.add_row("Bounced Emails", str(summary.get('bounced_emails', 0)))
    table.add_row("Success Rate", f"{summary.get('delivery_success_rate', 0):.1f}%")
    
    if summary.get('duration_seconds'):
        table.add_row("Duration", f"{summary['duration_seconds']:.1f} seconds")
    
    console.print(table)
    
    # Display any errors
    errors = results.get('errors', [])
    if errors:
        console.print("\n[red]Sending Errors:[/red]")
        for error in errors[:5]:  # Show first 5 errors
            console.print(f"[red]• {error}[/red]")

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


if __name__ == '__main__':
    cli()