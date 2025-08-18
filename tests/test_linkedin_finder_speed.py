#!/usr/bin/env python3
"""
Quick test to verify the optimized LinkedIn finder performance.
"""

import time
from models.data_models import TeamMember
from services.linkedin_finder import LinkedInFinder
from utils.config import Config

def test_linkedin_finder_speed():
    """Test the optimized LinkedIn finder speed."""
    print("🚀 Testing optimized LinkedIn finder speed...")
    
    # Create test team members
    test_members = [
        TeamMember(
            name="Ankit Sharma",
            role="Software Engineer", 
            company="Eleven Music",
            linkedin_url=None
        ),
        TeamMember(
            name="John Smith",
            role="Product Manager",
            company="TechCorp",
            linkedin_url=None
        ),
        TeamMember(
            name="Sarah Johnson", 
            role="Designer",
            company="StartupXYZ",
            linkedin_url=None
        )
    ]
    
    # Initialize finder
    config = Config.from_env()
    finder = LinkedInFinder(config)
    
    # Time the search
    start_time = time.time()
    
    print(f"Searching for {len(test_members)} team members...")
    updated_members = finder.find_linkedin_urls_for_team(test_members)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Results
    found_count = len([m for m in updated_members if m.linkedin_url])
    
    print(f"\n📊 RESULTS:")
    print(f"⏱️  Total time: {total_time:.2f} seconds")
    print(f"🎯 Found LinkedIn URLs: {found_count}/{len(test_members)}")
    print(f"⚡ Average time per member: {total_time/len(test_members):.2f} seconds")
    
    # Show results
    for member in updated_members:
        status = "✅ FOUND" if member.linkedin_url else "❌ NOT FOUND"
        url = member.linkedin_url or "None"
        print(f"{status}: {member.name} -> {url}")
    
    # Performance assessment
    if total_time < 60:  # Under 1 minute for 3 members
        print(f"\n🎉 EXCELLENT! Search completed in {total_time:.1f}s (vs 6-7 minutes before)")
    elif total_time < 120:  # Under 2 minutes
        print(f"\n✅ GOOD! Search completed in {total_time:.1f}s (much better than before)")
    else:
        print(f"\n⚠️  Still slow: {total_time:.1f}s - needs more optimization")

if __name__ == "__main__":
    test_linkedin_finder_speed()