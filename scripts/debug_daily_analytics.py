#!/usr/bin/env python3
"""
Debug script to check daily analytics creation.
"""

from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController
from datetime import date

def debug_daily_analytics():
    """Debug the daily analytics creation process."""
    print("🔍 Debugging daily analytics creation...")
    
    try:
        # Load config
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        print(f"Analytics DB ID: {config.analytics_db_id}")
        
        if not config.analytics_db_id:
            print("❌ No analytics database ID configured!")
            return
        
        # Check if database exists and is accessible
        print("1. Testing database access...")
        try:
            response = controller.notion_manager.client.databases.retrieve(
                database_id=config.analytics_db_id
            )
            print(f"✅ Database accessible: {response['title'][0]['text']['content']}")
        except Exception as e:
            print(f"❌ Database access failed: {str(e)}")
            return
        
        # Check current entries in database
        print("2. Checking existing entries...")
        try:
            response = controller.notion_manager.client.databases.query(
                database_id=config.analytics_db_id
            )
            print(f"📊 Found {len(response['results'])} existing entries")
            
            for i, entry in enumerate(response['results'][:3]):  # Show first 3
                properties = entry['properties']
                date_prop = properties.get('Date', {})
                if 'title' in date_prop and date_prop['title']:
                    date_text = date_prop['title'][0]['text']['content']
                    print(f"   Entry {i+1}: {date_text}")
                else:
                    print(f"   Entry {i+1}: No date found")
        except Exception as e:
            print(f"❌ Failed to query database: {str(e)}")
            return
        
        # Test creating a new entry
        print("3. Testing daily summary creation...")
        today = date.today()
        
        # Get daily stats
        daily_stats = controller._calculate_daily_stats()
        print(f"📈 Daily stats calculated: {daily_stats}")
        
        # Create the entry
        success = controller.create_daily_summary(config.analytics_db_id)
        print(f"✅ Creation result: {success}")
        
        # Check if entry was created
        print("4. Verifying entry creation...")
        try:
            response = controller.notion_manager.client.databases.query(
                database_id=config.analytics_db_id,
                filter={
                    "property": "Date",
                    "title": {
                        "equals": today.strftime("%Y-%m-%d")
                    }
                }
            )
            
            if response['results']:
                print(f"✅ Found today's entry: {today.strftime('%Y-%m-%d')}")
                entry = response['results'][0]
                properties = entry['properties']
                
                # Show the entry details
                print("📊 Entry details:")
                for prop_name, prop_data in properties.items():
                    if prop_name == 'Date' and 'title' in prop_data:
                        value = prop_data['title'][0]['text']['content'] if prop_data['title'] else 'N/A'
                    elif 'number' in prop_data:
                        value = prop_data['number'] if prop_data['number'] is not None else 0
                    elif 'rich_text' in prop_data:
                        value = prop_data['rich_text'][0]['text']['content'] if prop_data['rich_text'] else 'N/A'
                    else:
                        value = 'Unknown format'
                    
                    print(f"   {prop_name}: {value}")
            else:
                print(f"❌ No entry found for today: {today.strftime('%Y-%m-%d')}")
                
        except Exception as e:
            print(f"❌ Failed to verify entry: {str(e)}")
        
        print(f"\n🔗 Check your Daily Analytics database:")
        print(f"https://notion.so/{config.analytics_db_id.replace('-', '')}")
        
    except Exception as e:
        print(f"❌ Error during debugging: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_daily_analytics()