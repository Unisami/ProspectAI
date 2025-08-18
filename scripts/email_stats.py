#!/usr/bin/env python3
"""
Email statistics viewer for the Job Prospect Automation system.
"""

import sys
from datetime import datetime
from typing import Dict, Any

from services.notion_manager import NotionDataManager
from utils.config import Config
from utils.logging_config import setup_logging, get_logger


def setup_test_logging():
    """Setup logging."""
    setup_logging("INFO")
    return get_logger(__name__)


def print_separator(title: str):
    """Print a formatted separator."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)


def display_email_stats(stats: Dict[str, Any]):
    """Display email generation statistics in a formatted way."""
    
    print_separator("EMAIL GENERATION OVERVIEW")
    
    print(f"📊 OVERALL STATISTICS:")
    print(f"   Total prospects: {stats['total_prospects']}")
    print(f"   Emails generated: {stats['emails_generated']}")
    print(f"   Emails sent: {stats['emails_sent']}")
    print(f"   Emails delivered: {stats['emails_delivered']}")
    print(f"   Emails opened: {stats['emails_opened']}")
    print(f"   Emails clicked: {stats['emails_clicked']}")
    print(f"   Emails bounced: {stats['emails_bounced']}")
    
    print_separator("SUCCESS RATES")
    
    print(f"📈 PERFORMANCE METRICS:")
    print(f"   Generation success rate: {stats['generation_success_rate']:.1%}")
    print(f"   Delivery success rate: {stats['delivery_success_rate']:.1%}")
    
    if stats['emails_sent'] > 0:
        open_rate = stats['emails_opened'] / stats['emails_sent']
        click_rate = stats['emails_clicked'] / stats['emails_sent']
        bounce_rate = stats['emails_bounced'] / stats['emails_sent']
        
        print(f"   Open rate: {open_rate:.1%}")
        print(f"   Click rate: {click_rate:.1%}")
        print(f"   Bounce rate: {bounce_rate:.1%}")
    
    print_separator("EMAIL QUALITY METRICS")
    
    print(f"✨ CONTENT QUALITY:")
    print(f"   Average personalization score: {stats['avg_personalization_score']:.2f}")
    print(f"   Average word count: {stats['avg_word_count']:.0f}")
    
    if stats['templates_used']:
        print_separator("TEMPLATE USAGE")
        
        print(f"📝 TEMPLATES USED:")
        total_templates = sum(stats['templates_used'].values())
        for template, count in sorted(stats['templates_used'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_templates) * 100
            print(f"   {template}: {count} ({percentage:.1f}%)")
    
    if stats['models_used']:
        print_separator("AI MODEL USAGE")
        
        print(f"🤖 MODELS USED:")
        total_models = sum(stats['models_used'].values())
        for model, count in sorted(stats['models_used'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_models) * 100
            print(f"   {model}: {count} ({percentage:.1f}%)")
    
    if stats['sender_profiles_used']:
        print_separator("SENDER PROFILE USAGE")
        
        print(f"👤 SENDER PROFILES USED:")
        total_profiles = sum(stats['sender_profiles_used'].values())
        for profile, count in sorted(stats['sender_profiles_used'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_profiles) * 100
            print(f"   {profile}: {count} ({percentage:.1f}%)")


def display_prospects_by_status(notion_manager: NotionDataManager):
    """Display prospects grouped by email status."""
    
    print_separator("PROSPECTS BY EMAIL STATUS")
    
    statuses = ["Generated", "Not Generated", "Failed"]
    
    for status in statuses:
        try:
            prospects = notion_manager.get_prospects_by_email_status(generation_status=status)
            
            if prospects:
                print(f"\n📋 {status.upper()} EMAILS ({len(prospects)}):")
                
                for prospect in prospects[:10]:  # Show first 10
                    name = prospect['name'] or 'Unknown'
                    company = prospect['company'] or 'Unknown'
                    
                    print(f"   • {name} at {company}")
                    
                    if prospect['email_subject']:
                        print(f"     Subject: {prospect['email_subject']}")
                    
                    if prospect['email_template']:
                        print(f"     Template: {prospect['email_template']}")
                    
                    if prospect['personalization_score'] is not None:
                        print(f"     Personalization: {prospect['personalization_score']:.2f}")
                    
                    if prospect['generated_date']:
                        print(f"     Generated: {prospect['generated_date']}")
                    
                    if prospect['sent_date']:
                        print(f"     Sent: {prospect['sent_date']}")
                    
                    print()
                
                if len(prospects) > 10:
                    print(f"   ... and {len(prospects) - 10} more")
            else:
                print(f"\n📋 {status.upper()} EMAILS: None")
        
        except Exception as e:
            print(f"❌ Error getting {status} prospects: {str(e)}")


def display_delivery_status(notion_manager: NotionDataManager):
    """Display prospects grouped by delivery status."""
    
    print_separator("PROSPECTS BY DELIVERY STATUS")
    
    delivery_statuses = ["Sent", "Delivered", "Opened", "Clicked", "Bounced", "Failed"]
    
    for status in delivery_statuses:
        try:
            prospects = notion_manager.get_prospects_by_email_status(delivery_status=status)
            
            if prospects:
                print(f"\n📤 {status.upper()} EMAILS ({len(prospects)}):")
                
                for prospect in prospects[:5]:  # Show first 5
                    name = prospect['name'] or 'Unknown'
                    company = prospect['company'] or 'Unknown'
                    
                    print(f"   • {name} at {company}")
                    
                    if prospect['email_subject']:
                        print(f"     Subject: {prospect['email_subject']}")
                    
                    if prospect['sent_date']:
                        print(f"     Sent: {prospect['sent_date']}")
                    
                    if prospect['opened_date']:
                        print(f"     Opened: {prospect['opened_date']}")
                    
                    print()
                
                if len(prospects) > 5:
                    print(f"   ... and {len(prospects) - 5} more")
            else:
                print(f"\n📤 {status.upper()} EMAILS: None")
        
        except Exception as e:
            print(f"❌ Error getting {status} delivery prospects: {str(e)}")


def main():
    """Main function."""
    logger = setup_test_logging()
    
    print_separator("EMAIL STATISTICS DASHBOARD")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Load configuration
        config = Config.from_file("config.yaml")
        
        # Initialize Notion manager
        notion_manager = NotionDataManager(config)
        
        # Get email statistics
        logger.info("Retrieving email statistics...")
        stats = notion_manager.get_email_generation_stats()
        
        # Display statistics
        display_email_stats(stats)
        
        # Display prospects by status
        display_prospects_by_status(notion_manager)
        
        # Display delivery status
        display_delivery_status(notion_manager)
        
        print_separator("SUMMARY")
        
        print("✅ Email statistics retrieved successfully!")
        print("\n💡 INSIGHTS:")
        
        if stats['emails_generated'] == 0:
            print("   • No emails have been generated yet")
            print("   • Run 'python test_email_storage.py' to generate test emails")
        else:
            print(f"   • {stats['emails_generated']} emails generated with {stats['avg_personalization_score']:.2f} avg score")
            
            if stats['emails_sent'] > 0:
                print(f"   • {stats['emails_sent']} emails sent with {stats['delivery_success_rate']:.1%} delivery rate")
            else:
                print("   • No emails have been sent yet")
        
        print("\n🔄 NEXT ACTIONS:")
        print("   • Generate more emails: python test_email_pipeline.py")
        print("   • Send emails: python cli.py generate-emails --prospect-ids 'id1,id2' --send")
        print("   • View full pipeline: python test_full_pipeline.py")
        
    except Exception as e:
        logger.error(f"Failed to get email statistics: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()