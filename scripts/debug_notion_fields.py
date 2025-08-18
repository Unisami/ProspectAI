#!/usr/bin/env python3
"""
Debug script to check raw Notion field data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.notion_manager import NotionDataManager
from utils.config import Config
import json

def debug_notion_fields():
    """Debug raw Notion field data."""
    print("🔍 DEBUGGING NOTION FIELD DATA")
    print("=" * 40)
    
    try:
        # Initialize Notion manager
        config = Config.from_env()
        notion_manager = NotionDataManager(config)
        
        # Get raw page data from Notion
        query_params = {
            "database_id": notion_manager.database_id,
            "page_size": 1
        }
        
        response = notion_manager.client.databases.query(**query_params)
        
        if response["results"]:
            page = response["results"][0]
            properties = page["properties"]
            
            print(f"📋 Sample page properties:")
            print(f"Name: {properties.get('Name', {})}")
            
            # Check email-related fields
            email_fields = [
                "Email Generation Status",
                "Email Delivery Status", 
                "Email Subject",
                "Email Content"
            ]
            
            for field in email_fields:
                if field in properties:
                    print(f"\n{field}:")
                    print(f"  Raw data: {properties[field]}")
                    
                    # Try extraction
                    if field.endswith("Status"):
                        extracted = notion_manager._extract_select(properties[field])
                        print(f"  Extracted: '{extracted}'")
                    else:
                        extracted = notion_manager._extract_rich_text(properties[field])
                        print(f"  Extracted: '{extracted}'")
                else:
                    print(f"\n{field}: NOT FOUND")
        else:
            print("No pages found in database")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_notion_fields()