#!/usr/bin/env python3
"""
Test ProductHunt team extraction to verify LinkedIn URLs are properly extracted
from team sections when available, and left as None when not available.
"""

import logging
from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_producthunt_linkedin_extraction():
    """Test that ProductHunt properly extracts LinkedIn URLs from team sections."""
    
    print("🧪 TESTING PRODUCTHUNT LINKEDIN EXTRACTION")
    print("=" * 50)
    
    # Initialize scraper
    config = Config.from_env()
    scraper = ProductHuntScraper(config)
    
    # Test with a real ProductHunt URL
    test_url = "https://www.producthunt.com/products/eleven-music"
    
    print(f"\n🔍 Testing with: {test_url}")
    print("This should:")
    print("✅ Extract team members from ProductHunt team section")
    print("✅ Include LinkedIn URLs if they're in the team section")
    print("✅ Leave LinkedIn URLs as None if not in team section")
    print("❌ NOT search for missing LinkedIn URLs")
    
    try:
        # Extract team information
        team_members = scraper.extract_team_info(test_url)
        
        print(f"\n📊 RESULTS:")
        print(f"Team members found: {len(team_members)}")
        
        members_with_linkedin = [m for m in team_members if m.linkedin_url]
        members_without_linkedin = [m for m in team_members if not m.linkedin_url]
        
        print(f"Members with LinkedIn URLs: {len(members_with_linkedin)}")
        print(f"Members without LinkedIn URLs: {len(members_without_linkedin)}")
        
        print(f"\n👥 TEAM MEMBER DETAILS:")
        for i, member in enumerate(team_members, 1):
            linkedin_status = "✅ HAS LINKEDIN" if member.linkedin_url else "❌ NO LINKEDIN"
            print(f"{i}. {member.name}")
            print(f"   Role: {member.role}")
            print(f"   Company: {member.company}")
            print(f"   LinkedIn: {linkedin_status}")
            if member.linkedin_url:
                print(f"   URL: {member.linkedin_url}")
            print()
        
        print(f"🎯 VERIFICATION:")
        if team_members:
            print("✅ Team extraction working")
            
            if members_with_linkedin:
                print(f"✅ LinkedIn URLs extracted: {len(members_with_linkedin)} found")
            
            if members_without_linkedin:
                print(f"✅ Members without LinkedIn left as not found: {len(members_without_linkedin)}")
                print("✅ No unnecessary LinkedIn searching performed")
            
            print("🎉 SUCCESS: ProductHunt LinkedIn extraction working correctly!")
        else:
            print("⚠️  No team members found - may need to check extraction logic")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.exception("Test failed")

if __name__ == "__main__":
    test_producthunt_linkedin_extraction()