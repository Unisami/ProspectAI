#!/usr/bin/env python3
"""
Setup script for configuring user mentions in notifications.
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import os

console = Console()

def setup_user_mentions():
    """Set up user mentions for push notifications."""
    console.print(Panel.fit(
        "[bold blue]📱 User Mention Setup for Push Notifications[/bold blue]",
        border_style="blue"
    ))
    
    console.print("\n[yellow]To receive proper push notifications in Notion, we need to set up @mentions.[/yellow]")
    console.print("[dim]This will ensure you get notified on mobile and desktop when campaigns complete.[/dim]\n")
    
    # Get user email
    console.print("[bold]Step 1: User Email[/bold]")
    console.print("Enter your email address (used for @remind notifications):")
    user_email = Prompt.ask("Email", default=os.getenv("USER_EMAIL", ""))
    
    # Instructions for getting Notion User ID
    console.print("\n[bold]Step 2: Notion User ID (Optional but Recommended)[/bold]")
    console.print("To get your Notion User ID for @mentions:")
    console.print("1. Go to any Notion page")
    console.print("2. Type '@' and select your name")
    console.print("3. Right-click the mention and 'Copy link'")
    console.print("4. The URL will contain your user ID (after '/user/')")
    console.print("\nExample: https://notion.so/user/12345678-1234-1234-1234-123456789abc")
    console.print("Your User ID would be: 12345678-1234-1234-1234-123456789abc")
    
    notion_user_id = Prompt.ask("\nNotion User ID (optional)", default=os.getenv("NOTION_USER_ID", ""))
    
    # Update .env file
    env_file = ".env"
    env_updates = []
    
    if user_email:
        env_updates.append(f"USER_EMAIL={user_email}")
    
    if notion_user_id:
        env_updates.append(f"NOTION_USER_ID={notion_user_id}")
    
    if env_updates:
        console.print(f"\n[blue]Updating {env_file}...[/blue]")
        
        # Read existing .env
        existing_env = {}
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        existing_env[key] = value
        
        # Update with new values
        if user_email:
            existing_env['USER_EMAIL'] = user_email
        if notion_user_id:
            existing_env['NOTION_USER_ID'] = notion_user_id
        
        # Write back to .env
        with open(env_file, 'w') as f:
            for key, value in existing_env.items():
                f.write(f"{key}={value}\n")
        
        console.print("[green]✅ Configuration updated![/green]")
    
    # Instructions for manual setup
    console.print("\n[bold yellow]📝 Manual Setup Instructions:[/bold yellow]")
    console.print("1. In your Notion notifications, you'll see '@mention-user-here'")
    console.print("2. Edit those pages and replace with your actual @mention")
    console.print("3. This will trigger proper push notifications")
    
    console.print("\n[bold green]🎉 Setup Complete![/bold green]")
    console.print("Now test notifications with: [cyan]python cli.py test-notifications[/cyan]")

if __name__ == "__main__":
    setup_user_mentions()