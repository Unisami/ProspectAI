#!/usr/bin/env python3
"""
Update existing prospects in Notion database with correct email field defaults.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.notion_manager import NotionManager
from utils.config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_existing_prospects():
    """Update existing prospects with correct email field defaults."""
    print("🔄 UPDATING EXISTING PROSPECTS WITH EMAIL DEFAULTS")
    print("=" * 60)
    print("Starting update process...")
    
    try:
        # Initialize Notion manager
        config = Config()
        notion_manager = NotionManager(config)
        
        # Get all prospects
        print("📋 Fetching all prospects...")
        prospects = notion_manager.get_prospects()
        print(f"Found {len(prospects)} prospects")
        
        # Filter prospects that need updates (empty email status fields)
        prospects_to_update = []
        for prospect in prospects:
            needs_update = (
                not prospect.email_generation_status or 
                not prospect.email_delivery_status
            )
            if needs_update:
                prospects_to_update.append(prospect)
        
        print(f"📝 {len(prospects_to_update)} prospects need email field updates")
        
        if not prospects_to_update:
            print("✅ All prospects already have correct email field values!")
            return True
        
        # Update prospects with correct defaults
        updates = []
        for prospect in prospects_to_update:
            # Set default values if empty
            if not prospect.email_generation_status:
                prospect.email_generation_status = "Not Generated"
            if not prospect.email_delivery_status:
                prospect.email_delivery_status = "Not Sent"
            
            # Prepare update data
            update_data = {
                "prospect_id": prospect.id,
                "properties": {
                    "Email Generation Status": {"select": {"name": prospect.email_generation_status}},
                    "Email Delivery Status": {"select": {"name": prospect.email_delivery_status}}
                }
            }
            updates.append(update_data)
        
        # Execute batch update
        print(f"🚀 Updating {len(updates)} prospects...")
        results = notion_manager.update_prospects_batch(updates)
        
        success_count = sum(1 for result in results if result)
        print(f"✅ Successfully updated {success_count}/{len(updates)} prospects")
        
        if success_count == len(updates):
            print("🎉 All prospects updated successfully!")
            return True
        else:
            print(f"⚠️  {len(updates) - success_count} prospects failed to update")
            return False
            
    except Exception as e:
        print(f"❌ Failed to update prospects: {e}")
        logger.exception("Update failed")
        return False

if __name__ == "__main__":
    success = update_existing_prospects()
    sys.exit(0 if success else 1)