#!/usr/bin/env python3
"""
Security Cleanup Script
Removes hardcoded credentials and sensitive information from the codebase.
"""

import os
import re
from pathlib import Path

def clean_config_yaml():
    """Remove hardcoded credentials from config.yaml"""
    config_path = "config.yaml"
    
    if not os.path.exists(config_path):
        print(f"❌ {config_path} not found")
        return
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Replace actual credentials with placeholders
    replacements = {
        r'HUNTER_API_KEY: [a-f0-9]{40}': 'HUNTER_API_KEY: your_hunter_api_key_here',
        r'NOTION_TOKEN: ntn_[a-zA-Z0-9]+': 'NOTION_TOKEN: your_notion_token_here',
        r'OPENAI_API_KEY: sk-[a-zA-Z0-9-]+': 'OPENAI_API_KEY: your_openai_api_key_here',
        r'DASHBOARD_ID: \'[0-9a-f-]+\'': 'DASHBOARD_ID: your_dashboard_id_here',
        r'CAMPAIGNS_DB_ID: \'[0-9a-f-]+\'': 'CAMPAIGNS_DB_ID: your_campaigns_db_id_here',
        r'LOGS_DB_ID: \'[0-9a-f-]+\'': 'LOGS_DB_ID: your_logs_db_id_here',
        r'STATUS_DB_ID: \'[0-9a-f-]+\'': 'STATUS_DB_ID: your_status_db_id_here',
        r'ANALYTICS_DB_ID: \'[0-9a-f-]+\'': 'ANALYTICS_DB_ID: your_analytics_db_id_here',
        r'EMAIL_QUEUE_DB_ID: \'[0-9a-f-]+\'': 'EMAIL_QUEUE_DB_ID: your_email_queue_db_id_here',
    }
    
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)
    
    # Create a template version
    template_path = "config/config.yaml.template"
    with open(template_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Created clean template: {template_path}")
    
    # Move original to backup
    backup_path = "config.yaml.backup"
    os.rename(config_path, backup_path)
    print(f"✅ Backed up original to: {backup_path}")

def clean_debug_scripts():
    """Remove hardcoded email addresses from debug scripts"""
    scripts_to_clean = [
        "scripts/debug_email_length.py",
        "scripts/debug_email_content.py"
    ]
    
    for script_path in scripts_to_clean:
        if not os.path.exists(script_path):
            continue
            
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Replace hardcoded email with placeholder
        content = re.sub(
            r'recipient_email="[^"]+@[^"]+\.[^"]+"',
            'recipient_email="test@example.com"',
            content
        )
        
        with open(script_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Cleaned email addresses in: {script_path}")

def create_env_template():
    """Create a clean .env template"""
    env_template = """# Job Prospect Automation - Environment Variables Template
# Copy this file to .env and fill in your actual values

# Notion Integration
NOTION_TOKEN=your_notion_integration_token_here
NOTION_DATABASE_ID=your_main_database_id_here

# Dashboard IDs (created by setup-dashboard command)
DASHBOARD_ID=your_dashboard_id_here
CAMPAIGNS_DB_ID=your_campaigns_db_id_here
LOGS_DB_ID=your_logs_db_id_here
STATUS_DB_ID=your_status_db_id_here
ANALYTICS_DB_ID=your_analytics_db_id_here
EMAIL_QUEUE_DB_ID=your_email_queue_db_id_here

# Hunter.io API
HUNTER_API_KEY=your_hunter_api_key_here

# OpenAI API (choose one)
# Option 1: OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Option 2: Azure OpenAI (alternative)
USE_AZURE_OPENAI=false
AZURE_OPENAI_API_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=your_azure_endpoint_here
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name_here
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Email Sending (Resend API)
RESEND_API_KEY=your_resend_api_key_here
SENDER_EMAIL=your_email@yourdomain.com
SENDER_NAME=Your Name

# Sender Profile
SENDER_PROFILE_PATH=profiles/my_profile.md

# Performance Settings
SCRAPING_DELAY=5
LINKEDIN_SCRAPING_DELAY=0.5
MAX_PROSPECTS_PER_COMPANY=3
EMAIL_TEMPLATE_TYPE=professional
PERSONALIZATION_LEVEL=medium

# Optional: User identification
USER_EMAIL=your_email@yourdomain.com
NOTION_USER_ID=your_notion_user_id_here
"""
    
    with open(".env.template", 'w') as f:
        f.write(env_template)
    
    print("✅ Created clean .env.template")

def create_gitignore():
    """Create/update .gitignore to prevent credential exposure"""
    gitignore_content = """# Environment variables and credentials
.env
config.yaml
*.backup

# API Keys and sensitive data
**/api_keys.txt
**/credentials.json
**/secrets.yaml

# Notion database IDs
**/database_ids.txt

# Personal information
**/personal_info.txt

# Logs that might contain sensitive data
logs/*.log
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
htmlcov/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
    
    with open(".gitignore", 'w') as f:
        f.write(gitignore_content)
    
    print("✅ Created/updated .gitignore")

def main():
    """Run security cleanup"""
    print("🛡️  Starting security cleanup...")
    
    clean_config_yaml()
    clean_debug_scripts()
    create_env_template()
    create_gitignore()
    
    print("\n🎉 Security cleanup complete!")
    print("\n⚠️  IMPORTANT NEXT STEPS:")
    print("1. Copy .env.template to .env and fill in your actual credentials")
    print("2. Use config/config.yaml.template as your template")
    print("3. Never commit .env or config.yaml files to version control")
    print("4. Review all files before committing to ensure no credentials remain")

if __name__ == "__main__":
    main()