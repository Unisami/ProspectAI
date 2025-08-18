#!/usr/bin/env python3
"""Simple test to verify ProductHunt LinkedIn extraction."""

print("🧪 SIMPLE TEST: ProductHunt LinkedIn Extraction")
print("=" * 50)

try:
    from services.product_hunt_scraper import ProductHuntScraper
    from utils.config import Config
    
    print("✅ Imports successful")
    
    # Initialize scraper
    config = Config.from_env()
    scraper = ProductHuntScraper(config)
    
    print("✅ Scraper initialized")
    
    # Test URL
    test_url = "https://www.producthunt.com/products/eleven-music"
    print(f"🔍 Testing with: {test_url}")
    
    # Extract team
    team_members = scraper.extract_team_info(test_url)
    
    print(f"📊 Results: {len(team_members)} team members found")
    
    for member in team_members:
        linkedin_status = "✅" if member.linkedin_url else "❌"
        print(f"{linkedin_status} {member.name} - {member.role}")
        if member.linkedin_url:
            print(f"   LinkedIn: {member.linkedin_url}")
    
    print("🎉 Test completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()