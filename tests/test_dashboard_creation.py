#!/usr/bin/env python3
"""
Test script to isolate the dashboard creation issue.
"""

from utils.config import Config
from services.notion_manager import NotionDataManager
import traceback

def test_step_by_step():
    """Test each step of dashboard creation separately."""
    print("🔧 Testing dashboard creation step by step...")
    
    try:
        # Step 1: Load config
        print("1. Loading configuration...")
        config = Config.from_env()
        print("✅ Configuration loaded")
        
        # Step 2: Initialize Notion manager
        print("2. Initializing Notion manager...")
        notion_manager = NotionDataManager(config)
        print("✅ Notion manager initialized")
        
        # Step 3: Get parent page ID
        print("3. Getting parent page ID...")
        parent_page_id = notion_manager._get_parent_page_id()
        print(f"✅ Parent page ID: {parent_page_id}")
        
        # Step 4: Test page creation
        print("4. Testing dashboard page creation...")
        dashboard_page = notion_manager.client.pages.create(
            parent={"type": "page_id", "page_id": parent_page_id},
            properties={
                "title": [
                    {
                        "text": {
                            "content": "🧪 Test Dashboard Page"
                        }
                    }
                ]
            }
        )
        print(f"✅ Dashboard page created: {dashboard_page['id']}")
        
        # Step 5: Test database creation
        print("5. Testing campaign database creation...")
        properties = {
            "Campaign Name": {"title": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Running", "color": "yellow"},
                        {"name": "Completed", "color": "green"}
                    ]
                }
            }
        }
        
        campaigns_db = notion_manager.client.databases.create(
            parent={"type": "page_id", "page_id": dashboard_page["id"]},
            title=[{"type": "text", "text": {"content": "🧪 Test Campaign Database"}}],
            properties=properties
        )
        print(f"✅ Campaign database created: {campaigns_db['id']}")
        
        print("\n🎉 All tests passed! The issue might be elsewhere.")
        
        # Cleanup
        print("6. Cleaning up test objects...")
        # Note: Notion doesn't have a delete API, so we'll leave the test objects
        print("✅ Test completed successfully")
        
    except Exception as e:
        print(f"❌ Error at step: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_step_by_step()