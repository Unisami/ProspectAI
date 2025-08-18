#!/usr/bin/env python3
"""
Debug script to verify that prospects are being stored in Notion during parallel processing.
"""

import logging
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def debug_notion_storage():
    """Debug Notion storage during parallel processing."""
    print("🔍 Debugging Notion Storage During Parallel Processing")
    print("="*70)
    
    try:
        # Initialize controller
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Get current prospect count before processing
        print("📊 Checking current prospects in Notion...")
        existing_prospects = controller.notion_manager.get_prospects()
        initial_count = len(existing_prospects)
        print(f"Initial prospect count: {initial_count}")
        
        # Run a small test campaign
        print(f"\n🔄 Running test campaign with 2 companies...")
        
        results = controller.run_discovery_pipeline(
            limit=2,
            campaign_name="Notion Storage Debug Test"
        )
        
        # Check prospect count after processing
        print(f"\n📊 Checking prospects after processing...")
        updated_prospects = controller.notion_manager.get_prospects()
        final_count = len(updated_prospects)
        new_prospects = final_count - initial_count
        
        print(f"Final prospect count: {final_count}")
        print(f"New prospects added: {new_prospects}")
        
        # Display results summary
        summary = results.get('summary', {})
        print(f"\n📈 Campaign Results:")
        print(f"  • Companies Processed: {summary.get('companies_processed', 0)}")
        print(f"  • Prospects Found (reported): {summary.get('prospects_found', 0)}")
        print(f"  • Prospects Found (actual in Notion): {new_prospects}")
        
        # Check if there's a mismatch
        reported_prospects = summary.get('prospects_found', 0)
        if new_prospects != reported_prospects:
            print(f"\n⚠️  MISMATCH DETECTED!")
            print(f"   Reported: {reported_prospects} prospects")
            print(f"   Actually stored: {new_prospects} prospects")
            print(f"   Difference: {reported_prospects - new_prospects}")
            
            if new_prospects == 0:
                print(f"\n❌ NO PROSPECTS STORED IN NOTION!")
                print(f"   This indicates the Notion storage is broken in parallel processing")
            else:
                print(f"\n⚠️  Some prospects may not have been stored properly")
        else:
            print(f"\n✅ SUCCESS: All reported prospects were stored in Notion!")
        
        # Show some details of new prospects
        if new_prospects > 0:
            print(f"\n👥 New Prospects Added:")
            recent_prospects = updated_prospects[-new_prospects:]
            for i, prospect in enumerate(recent_prospects[:5], 1):  # Show first 5
                email_status = "✅" if prospect.email else "❌"
                print(f"  {i}. {prospect.name} at {prospect.company} {email_status}")
        
        print("="*70)
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_notion_storage()