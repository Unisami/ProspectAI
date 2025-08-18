#!/usr/bin/env python3
"""
Test script for interactive campaign controls.
"""

import time
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController
from services.interactive_controls import InteractiveControlManager

def test_interactive_controls():
    """Test the interactive control system."""
    print("🎮 Testing Interactive Campaign Controls...")
    
    try:
        # Load config
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        control_manager = InteractiveControlManager(config, controller.notion_manager)
        
        campaigns_db_id = config.campaigns_db_id
        if not campaigns_db_id:
            print("❌ No campaigns database configured!")
            return
        
        print(f"📊 Campaigns DB ID: {campaigns_db_id}")
        
        # Check for existing campaigns
        print("1. Checking for active campaigns...")
        try:
            response = controller.notion_manager.client.databases.query(
                database_id=campaigns_db_id,
                filter={
                    "property": "Status",
                    "select": {
                        "equals": "Running"
                    }
                }
            )
            
            active_campaigns = response["results"]
            print(f"   Found {len(active_campaigns)} active campaigns")
            
            if not active_campaigns:
                print("   No active campaigns found. Start a campaign first!")
                return
            
            # Test control checking for the first active campaign
            campaign = active_campaigns[0]
            campaign_name = controller.notion_manager._extract_title(
                campaign["properties"].get("Campaign Name", {})
            )
            
            print(f"   Testing controls for: {campaign_name}")
            
        except Exception as e:
            print(f"❌ Failed to query campaigns: {str(e)}")
            return
        
        # Test control command detection
        print("2. Testing control command detection...")
        
        for i in range(5):  # Check 5 times with delays
            print(f"   Check {i+1}/5...")
            
            try:
                commands = control_manager.check_control_commands(campaign_name, campaigns_db_id)
                
                if commands:
                    print(f"   🎮 Found {len(commands)} control commands:")
                    for cmd in commands:
                        print(f"      - Action: {cmd.action.value}")
                        print(f"      - Parameters: {cmd.parameters}")
                        print(f"      - Requested by: {cmd.requested_by}")
                        
                        # Test command execution
                        print(f"      - Executing command...")
                        success = control_manager.execute_control_command(cmd, controller)
                        print(f"      - Result: {'✅ Success' if success else '❌ Failed'}")
                else:
                    print("   No control commands detected")
                
            except Exception as e:
                print(f"   ❌ Error checking commands: {str(e)}")
            
            if i < 4:  # Don't sleep on the last iteration
                print("   Waiting 10 seconds before next check...")
                time.sleep(10)
        
        print("\n📋 Instructions for manual testing:")
        print("1. Go to your Notion 'Campaign Runs' database")
        print("2. Find the active campaign")
        print("3. Try these actions:")
        print("   • Change Status to 'Paused' to pause the campaign")
        print("   • Change Status to 'Failed' to stop the campaign")
        print("   • Change 'Current Company' to 'PRIORITY: TestCompany' to add priority")
        print("4. Run this script again to see if commands are detected")
        
        print(f"\n🔗 Direct link to campaigns database:")
        print(f"https://notion.so/{campaigns_db_id.replace('-', '')}")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_interactive_controls()