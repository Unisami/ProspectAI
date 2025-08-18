#!/usr/bin/env python3
"""
Test the integrated fast LinkedIn scraper.
"""

from services.linkedin_scraper import LinkedInScraper
from utils.config import Config
import time

def test_fast_linkedin_integration():
    """Test the fast LinkedIn integration."""
    print("🚀 Testing Fast LinkedIn Integration")
    print("=" * 40)
    
    config = Config.from_env()
    scraper = LinkedInScraper(config)
    
    # Test URLs
    test_urls = [
        "https://linkedin.com/in/john-doe-123",
        "https://linkedin.com/in/jane-smith-ceo",
        "https://linkedin.com/in/tech-founder-456"
    ]
    
    total_start = time.time()
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📋 Test {i}/{len(test_urls)}: {url}")
        start = time.time()
        
        profile = scraper.extract_profile_data(url)
        
        elapsed = time.time() - start
        
        if profile:
            print(f"   ✅ Success in {elapsed:.1f}s")
            print(f"   👤 Name: {profile.name}")
            print(f"   💼 Role: {profile.current_role}")
        else:
            print(f"   ❌ Failed in {elapsed:.1f}s")
    
    total_time = time.time() - total_start
    
    print(f"\n🎯 RESULTS:")
    print(f"   ⏱️  Total time: {total_time:.1f} seconds")
    print(f"   📊 Profiles: {len(test_urls)}")
    print(f"   🚀 Speed: {len(test_urls)/total_time:.1f} profiles/second")
    print(f"   💡 vs Old system (15 min/profile): {(15*60*len(test_urls))/total_time:.0f}x faster!")

if __name__ == "__main__":
    test_fast_linkedin_integration()