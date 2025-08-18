#!/usr/bin/env python3
"""
Simple script to check personalization data for recent prospects.
"""

from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

def check_recent_personalization():
    """Check personalization data for recent prospects."""
    print("🔍 Checking Personalization Data for Recent Prospects")
    print("="*60)
    
    try:
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Get all prospects
        prospects = controller.notion_manager.get_prospects()
        print(f"Total prospects in database: {len(prospects)}")
        
        # Check the last 3 prospects (most recent)
        recent_prospects = prospects[-3:]
        
        for i, prospect in enumerate(recent_prospects, 1):
            print(f"\n{i}. {prospect.name} at {prospect.company}")
            print(f"   ID: {prospect.id}")
            
            # Get detailed data
            prospect_data = controller.notion_manager.get_prospect_data_for_email(prospect.id)
            
            personalization_data = prospect_data.get('personalization_data', '')
            product_summary = prospect_data.get('product_summary', '')
            business_insights = prospect_data.get('business_insights', '')
            linkedin_summary = prospect_data.get('linkedin_summary', '')
            
            print(f"   📊 Data Lengths:")
            print(f"      Personalization: {len(personalization_data)} chars")
            print(f"      Product Summary: {len(product_summary)} chars")
            print(f"      Business Insights: {len(business_insights)} chars")
            print(f"      LinkedIn Summary: {len(linkedin_summary)} chars")
            
            # Show personalization data if it exists
            if personalization_data:
                print(f"   🎯 Personalization Data:")
                print(f"      {personalization_data[:200]}...")
                
                # Count points
                lines = personalization_data.split('\n')
                bullet_points = [line for line in lines if line.strip().startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.'))]
                print(f"      📋 Estimated points: {len(bullet_points)}")
                
                if len(bullet_points) >= 3:
                    print(f"      ✅ Good: Has {len(bullet_points)} personalization points")
                else:
                    print(f"      ⚠️  Limited: Only {len(bullet_points)} points found")
            else:
                print(f"   ❌ No personalization data")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_recent_personalization()