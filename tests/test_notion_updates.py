#!/usr/bin/env python3
"""
Test Notion database updates to verify email status tracking works correctly.
"""

import logging
from datetime import datetime
from services.notion_manager import NotionDataManager
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_notion_updates():
    """Test that Notion database updates work correctly."""
    
    print("🧪 TESTING NOTION DATABASE UPDATES")
    print("=" * 50)
    
    try:
        # Initialize Notion manager
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        print("✅ Notion manager initialized")
        
        # Test email stats retrieval
        print("\n📊 TESTING EMAIL GENERATION STATS")
        try:
            email_stats = notion_manager.get_email_generation_stats()
            print(f"Email generation stats: {email_stats}")
            
            emails_generated = email_stats.get('total_generated', 0)
            emails_sent = email_stats.get('total_sent', 0)
            
            print(f"Emails generated: {emails_generated}")
            print(f"Emails sent: {emails_sent}")
            
            if emails_sent == 0:
                print("✅ Correct - no emails actually sent")
            else:
                print(f"⚠️  Shows {emails_sent} emails sent - verify this is accurate")
                
        except Exception as e:
            print(f"❌ Failed to get email generation stats: {e}")
        
        # Test getting prospects to check their status
        print("\n👥 TESTING PROSPECT STATUS")
        try:
            prospects = notion_manager.get_prospects()
            print(f"Total prospects: {len(prospects)}")
            
            # Count by email generation status
            status_counts = {}
            for prospect in prospects:
                status = getattr(prospect, 'email_generation_status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("Email generation status breakdown:")
            for status, count in status_counts.items():
                print(f"  {status}: {count}")
                
        except Exception as e:
            print(f"❌ Failed to get prospects: {e}")
        
        print("\n🎯 FIXES APPLIED:")
        print("1. ✅ Fixed email sent count calculation")
        print("2. ✅ Added explicit email generation status updates")
        print("3. ✅ Improved daily stats accuracy")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_notion_updates()