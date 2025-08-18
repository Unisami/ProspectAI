#!/usr/bin/env python3
"""
Migration script to add new email storage fields to existing Notion database.
"""

import sys
from typing import Dict, Any

from services.notion_manager import NotionDataManager
from utils.config import Config
from utils.logging_config import setup_logging, get_logger


def setup_test_logging():
    """Setup logging."""
    setup_logging("INFO")
    return get_logger(__name__)


def add_email_storage_properties(notion_manager: NotionDataManager) -> bool:
    """
    Add new email storage properties to existing Notion database.
    
    Returns:
        bool: True if successful
    """
    logger = get_logger(__name__)
    
    try:
        # Define new properties to add
        new_properties = {
            "Email Content": {
                "rich_text": {}
            },
            "Email Body": {
                "rich_text": {}
            },
            "Email Template": {
                "select": {
                    "options": [
                        {"name": "cold_outreach", "color": "blue"},
                        {"name": "referral_followup", "color": "green"},
                        {"name": "product_interest", "color": "purple"},
                        {"name": "networking", "color": "orange"}
                    ]
                }
            },
            "Personalization Score": {
                "number": {}
            },
            "Email Generated Date": {
                "date": {}
            },
            "Email Generation Status": {
                "select": {
                    "options": [
                        {"name": "Not Generated", "color": "gray"},
                        {"name": "Generated", "color": "green"},
                        {"name": "Failed", "color": "red"},
                        {"name": "Reviewed", "color": "blue"},
                        {"name": "Approved", "color": "purple"}
                    ]
                }
            },
            "Sender Profile Used": {
                "rich_text": {}
            },
            "Email Delivery Status": {
                "select": {
                    "options": [
                        {"name": "Not Sent", "color": "gray"},
                        {"name": "Queued", "color": "yellow"},
                        {"name": "Sent", "color": "blue"},
                        {"name": "Delivered", "color": "green"},
                        {"name": "Opened", "color": "purple"},
                        {"name": "Clicked", "color": "orange"},
                        {"name": "Bounced", "color": "red"},
                        {"name": "Complained", "color": "red"},
                        {"name": "Failed", "color": "red"}
                    ]
                }
            },
            "Email Provider ID": {
                "rich_text": {}
            },
            "Email Delivery Date": {
                "date": {}
            },
            "Email Open Date": {
                "date": {}
            },
            "Email Click Date": {
                "date": {}
            },
            "Email Bounce Reason": {
                "rich_text": {}
            },
            "Email Generation Model": {
                "rich_text": {}
            },
            "Email Generation Time": {
                "number": {}
            },
            "Email Word Count": {
                "number": {}
            },
            "Email Character Count": {
                "number": {}
            }
        }
        
        logger.info(f"Adding {len(new_properties)} new properties to Notion database...")
        
        # Update database schema
        response = notion_manager.client.databases.update(
            database_id=notion_manager.database_id,
            properties=new_properties
        )
        
        logger.info("Successfully added new email storage properties to Notion database")
        
        # List the properties that were added
        print("✅ Added the following properties:")
        for prop_name in new_properties.keys():
            print(f"   • {prop_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to add email storage properties: {str(e)}")
        print(f"❌ Migration failed: {str(e)}")
        return False


def update_existing_prospects(notion_manager: NotionDataManager) -> bool:
    """
    Update existing prospects with default values for new fields.
    
    Returns:
        bool: True if successful
    """
    logger = get_logger(__name__)
    
    try:
        logger.info("Updating existing prospects with default values...")
        
        # Get all prospects
        prospects = notion_manager.get_prospects()
        
        if not prospects:
            logger.info("No existing prospects to update")
            return True
        
        logger.info(f"Updating {len(prospects)} existing prospects...")
        
        updated_count = 0
        
        for prospect in prospects:
            try:
                # Set default values for new fields
                properties = {
                    "Email Generation Status": {"select": {"name": "Not Generated"}},
                    "Email Delivery Status": {"select": {"name": "Not Sent"}}
                }
                
                notion_manager.client.pages.update(
                    page_id=prospect.id,
                    properties=properties
                )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update prospect {prospect.name}: {str(e)}")
                continue
        
        logger.info(f"Successfully updated {updated_count} prospects with default values")
        print(f"✅ Updated {updated_count} existing prospects with default values")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to update existing prospects: {str(e)}")
        print(f"❌ Failed to update existing prospects: {str(e)}")
        return False


def main():
    """Main migration function."""
    logger = setup_test_logging()
    
    print("="*80)
    print(" NOTION DATABASE MIGRATION - EMAIL STORAGE FIELDS")
    print("="*80)
    
    try:
        # Load configuration
        config = Config.from_file("config.yaml")
        
        # Initialize Notion manager
        notion_manager = NotionDataManager(config)
        
        if not notion_manager.database_id:
            print("❌ No Notion database ID found. Please run discovery first to create database.")
            sys.exit(1)
        
        print(f"🔗 Connected to Notion database: {notion_manager.database_id}")
        
        # Step 1: Add new properties
        print("\n📝 Step 1: Adding new email storage properties...")
        if not add_email_storage_properties(notion_manager):
            sys.exit(1)
        
        # Step 2: Update existing prospects
        print("\n🔄 Step 2: Updating existing prospects with default values...")
        if not update_existing_prospects(notion_manager):
            sys.exit(1)
        
        print("\n" + "="*80)
        print(" MIGRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        
        print("\n✅ Your Notion database now supports:")
        print("   • Complete email content storage")
        print("   • Email generation metadata")
        print("   • Delivery status tracking")
        print("   • Performance analytics")
        print("   • Template and model usage tracking")
        
        print("\n🚀 Next steps:")
        print("   1. Run: python test_email_storage.py")
        print("   2. Generate emails: python test_email_pipeline.py")
        print("   3. View statistics: python email_stats.py")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()