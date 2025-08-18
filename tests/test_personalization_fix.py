#!/usr/bin/env python3
"""
Test script to verify that personalization data is no longer being truncated.
"""

import logging
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_personalization_data_length():
    """Test that personalization data is properly generated without truncation."""
    print("🧪 Testing Personalization Data Generation (No Truncation)")
    print("="*70)
    
    try:
        # Initialize controller
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Run a small test to generate personalization data
        print("🔄 Running test campaign to check personalization data...")
        
        results = controller.run_discovery_pipeline(
            limit=1,  # Just 1 company to test
            campaign_name="Personalization Data Test"
        )
        
        # Check if any prospects were found
        summary = results.get('summary', {})
        prospects_found = summary.get('prospects_found', 0)
        
        if prospects_found == 0:
            print("❌ No prospects found to test personalization data")
            return
        
        print(f"✅ Found {prospects_found} prospects")
        
        # Get the most recent prospects to check their personalization data
        prospects = controller.notion_manager.get_prospects()
        if not prospects:
            print("❌ No prospects in database")
            return
        
        # Get the most recent prospect
        recent_prospect = prospects[-1]
        print(f"📊 Checking personalization data for: {recent_prospect.name} at {recent_prospect.company}")
        
        # Get the full prospect data including AI-structured data
        prospect_data = controller.notion_manager.get_prospect_data_for_email(recent_prospect.id)
        
        personalization_data = prospect_data.get('personalization_data', '')
        product_summary = prospect_data.get('product_summary', '')
        business_insights = prospect_data.get('business_insights', '')
        linkedin_summary = prospect_data.get('linkedin_summary', '')
        
        print(f"\n📝 AI-Generated Data Analysis:")
        print(f"="*50)
        
        # Analyze Personalization Data
        print(f"🎯 Personalization Data:")
        print(f"   Length: {len(personalization_data)} characters")
        print(f"   Word count: {len(personalization_data.split()) if personalization_data else 0} words")
        if personalization_data:
            print(f"   Preview: {personalization_data[:200]}...")
            
            # Check if it contains the expected structure
            if "personalization points" in personalization_data.lower():
                print("   ✅ Contains 'personalization points' - good structure")
            else:
                print("   ⚠️  May not have expected structure")
                
            # Count bullet points or numbered items
            bullet_count = personalization_data.count('•') + personalization_data.count('-') + personalization_data.count('*')
            numbered_count = len([line for line in personalization_data.split('\n') if line.strip() and line.strip()[0].isdigit()])
            total_points = max(bullet_count, numbered_count)
            
            print(f"   📋 Estimated points: {total_points}")
            
            if total_points >= 3:
                print("   ✅ Has 3+ personalization points - truncation fixed!")
            elif total_points >= 2:
                print("   ⚠️  Has 2 points - may still be slightly truncated")
            else:
                print("   ❌ Has <2 points - still truncated")
        else:
            print("   ❌ No personalization data found")
        
        # Analyze other AI-generated fields
        print(f"\n📊 Product Summary:")
        print(f"   Length: {len(product_summary)} characters")
        print(f"   Word count: {len(product_summary.split()) if product_summary else 0} words")
        if len(product_summary) > 300:
            print("   ✅ Good length - not truncated")
        elif len(product_summary) > 100:
            print("   ⚠️  Moderate length - may be slightly truncated")
        else:
            print("   ❌ Short length - likely truncated")
        
        print(f"\n💼 Business Insights:")
        print(f"   Length: {len(business_insights)} characters")
        print(f"   Word count: {len(business_insights.split()) if business_insights else 0} words")
        if len(business_insights) > 200:
            print("   ✅ Good length - not truncated")
        elif len(business_insights) > 100:
            print("   ⚠️  Moderate length - may be slightly truncated")
        else:
            print("   ❌ Short length - likely truncated")
        
        print(f"\n👤 LinkedIn Summary:")
        print(f"   Length: {len(linkedin_summary)} characters")
        print(f"   Word count: {len(linkedin_summary.split()) if linkedin_summary else 0} words")
        if len(linkedin_summary) > 200:
            print("   ✅ Good length - not truncated")
        elif len(linkedin_summary) > 100:
            print("   ⚠️  Moderate length - may be slightly truncated")
        else:
            print("   ❌ Short length - likely truncated")
        
        # Overall assessment
        print(f"\n🎯 Overall Assessment:")
        total_chars = len(personalization_data) + len(product_summary) + len(business_insights) + len(linkedin_summary)
        print(f"   Total AI-generated content: {total_chars} characters")
        
        if total_chars > 1500:
            print("   ✅ EXCELLENT: Rich, detailed AI-generated content")
        elif total_chars > 800:
            print("   ✅ GOOD: Adequate AI-generated content")
        elif total_chars > 400:
            print("   ⚠️  MODERATE: Some content but may be truncated")
        else:
            print("   ❌ POOR: Very little content - likely truncated")
        
        print("="*70)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_personalization_data_length()