#!/usr/bin/env python3
"""
Debug team extraction to see what's happening with LinkedIn URLs.
"""

import logging
from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_team_extraction():
    """Debug the team extraction process."""
    
    print("🔍 DEBUGGING TEAM EXTRACTION")
    print("=" * 50)
    
    # Initialize scraper
    config = Config.from_env()
    scraper = ProductHuntScraper(config)
    
    # Test with CourseCorrect (the company from the logs)
    test_url = "https://www.producthunt.com/products/coursecorrect"
    
    print(f"\n🎯 Testing with: {test_url}")
    
    try:
        # Extract team information
        team_members = scraper.extract_team_info(test_url)
        
        print(f"\n📊 RAW EXTRACTION RESULTS:")
        print(f"Team members found: {len(team_members)}")
        
        for i, member in enumerate(team_members, 1):
            print(f"\n{i}. {member.name}")
            print(f"   Role: {member.role}")
            print(f"   Company: {member.company}")
            print(f"   LinkedIn URL: {member.linkedin_url or 'NOT FOUND'}")
            
            if member.linkedin_url:
                print(f"   ✅ LinkedIn URL found in ProductHunt team section!")
            else:
                print(f"   ❌ No LinkedIn URL in ProductHunt team section")
        
        # Show what would be passed to AI
        print(f"\n🤖 RAW CONTENT THAT WOULD BE PASSED TO AI:")
        raw_team_content = "\n".join([
            f"Name: {getattr(tm, 'name', 'Unknown')}, Role: {getattr(tm, 'role', 'Unknown')}, Company: {getattr(tm, 'company', 'Unknown')}, LinkedIn: {getattr(tm, 'linkedin_url', None) or 'N/A'}"
            for tm in team_members
        ])
        print(raw_team_content)
        
        # Analysis
        members_with_linkedin = [m for m in team_members if m.linkedin_url]
        print(f"\n📈 ANALYSIS:")
        print(f"Members with LinkedIn URLs: {len(members_with_linkedin)}/{len(team_members)}")
        
        if members_with_linkedin:
            print("✅ LinkedIn URLs are being extracted from ProductHunt team section!")
            print("✅ The fix is working correctly!")
        else:
            print("❌ No LinkedIn URLs found in ProductHunt team section")
            print("❌ Either the team section doesn't have LinkedIn URLs, or extraction needs improvement")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logger.exception("Debug failed")

if __name__ == "__main__":
    debug_team_extraction()