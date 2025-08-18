#!/usr/bin/env python3
"""
Test LinkedIn extraction optimization logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.data_models import TeamMember

def should_extract_linkedin_profile(team_member):
    """
    Test version of the LinkedIn extraction logic.
    """
    # Skip if no LinkedIn URL
    if not team_member.linkedin_url:
        return False
        
    # Skip if URL looks invalid or generic
    url_lower = team_member.linkedin_url.lower()
    if any(skip_pattern in url_lower for skip_pattern in [
        'linkedin.com/company',  # Company page, not person
        'linkedin.com/school',   # School page
        'linkedin.com/showcase', # Showcase page
        '/pub/',                 # Old public profile format (often broken)
    ]):
        print(f"  ⏭️ Skipping - invalid URL pattern: {team_member.linkedin_url}")
        return False
        
    # Skip if name is too generic or incomplete
    if not team_member.name or len(team_member.name.strip()) < 3:
        print(f"  ⏭️ Skipping - insufficient name data: {team_member.name}")
        return False
        
    # Skip if name contains generic terms
    name_lower = team_member.name.lower()
    if any(generic in name_lower for generic in [
        'team', 'support', 'admin', 'info', 'contact', 'sales', 'marketing'
    ]):
        print(f"  ⏭️ Skipping - generic name: {team_member.name}")
        return False
        
    # Only proceed if we have a reasonable chance of success
    return True

def main():
    print("🧪 Testing LinkedIn extraction optimization...")
    print("=" * 60)
    
    # Test cases
    test_members = [
        TeamMember(name='John Doe', role='CEO', company='TestCorp', linkedin_url='https://linkedin.com/in/johndoe'),
        TeamMember(name='Support Team', role='Support', company='TestCorp', linkedin_url='https://linkedin.com/in/support'),
        TeamMember(name='J', role='Dev', company='TestCorp', linkedin_url='https://linkedin.com/in/j'),
        TeamMember(name='Jane Smith', role='CTO', company='TestCorp', linkedin_url='https://linkedin.com/company/test'),
        TeamMember(name='Marketing Dept', role='Marketing', company='TestCorp', linkedin_url='https://linkedin.com/in/marketing'),
        TeamMember(name='Alice Johnson', role='Engineer', company='TestCorp', linkedin_url='https://linkedin.com/in/alice-johnson'),
        TeamMember(name='Bob Wilson', role='Designer', company='TestCorp', linkedin_url=''),  # No URL
    ]
    
    extract_count = 0
    skip_count = 0
    
    for i, member in enumerate(test_members, 1):
        print(f"\n{i}. Testing: {member.name}")
        should_extract = should_extract_linkedin_profile(member)
        
        if should_extract:
            print(f"  ✅ EXTRACT - Good candidate for LinkedIn scraping")
            extract_count += 1
        else:
            skip_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Results: {extract_count} extractions, {skip_count} skips")
    print(f"⚡ Performance gain: ~{skip_count * 8} seconds saved per company")
    print(f"💡 Efficiency: {(skip_count / len(test_members)) * 100:.1f}% of LinkedIn operations skipped")

if __name__ == "__main__":
    main()