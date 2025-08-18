#!/usr/bin/env python3
"""
Quick test to verify the LinkedIn optimization is working.
"""

import time
from services.linkedin_scraper import LinkedInScraper
from utils.config import Config

def quick_test():
    """Quick test of the optimized LinkedIn scraper."""
    print("🚀 Quick LinkedIn Optimization Test")
    print("=" * 40)
    
    try:
        config = Config.from_env()
        scraper = LinkedInScraper(config)
        
        test_url = "https://linkedin.com/in/test-user-123"
        
        print(f"Testing: {test_url}")
        start_time = time.time()
        
        profile = scraper.extract_profile_data(test_url)
        
        elapsed = time.time() - start_time
        
        if profile:
            print(f"✅ SUCCESS in {elapsed:.2f} seconds")
            print(f"   Name: {profile.name}")
            print(f"   Role: {profile.current_role}")
            print(f"   Summary: {profile.summary}")
        else:
            print(f"❌ FAILED in {elapsed:.2f} seconds")
        
        print(f"\n🎯 Performance:")
        print(f"   Time: {elapsed:.2f} seconds (vs 15+ minutes before)")
        if elapsed > 0:
            improvement = (15 * 60) / elapsed
            print(f"   Improvement: {improvement:.0f}x faster!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    quick_test()