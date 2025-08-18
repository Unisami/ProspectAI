#!/usr/bin/env python3

from services.email_finder import EmailFinder
from utils.config import Config
from models.data_models import TeamMember

def test_email_debug():
    """Test email finding with debug info"""
    
    config = Config.from_env()
    email_finder = EmailFinder(config)
    
    # Test with the team members we found
    team_members = [
        TeamMember(name="Charu Chaturvedi", role="Product Designer", company="Quicko Pro"),
        TeamMember(name="Parth Choksi", role="Software Engineer", company="Quicko Pro"),
        TeamMember(name="Sarthak Thakkar", role="Engineer, Builder", company="Quicko Pro"),
    ]
    
    domain = "quicko.pro"
    
    print(f"Testing email finding for {len(team_members)} team members at {domain}")
    
    for team_member in team_members:
        print(f"\n--- Testing: {team_member.name} ---")
        
        # Check name parsing
        name_parts = team_member.name.strip().split()
        print(f"Name parts: {name_parts} (count: {len(name_parts)})")
        
        if len(name_parts) < 2:
            print("❌ Name validation failed - less than 2 parts")
            continue
        
        first_name = name_parts[0]
        last_name = name_parts[-1]
        print(f"First name: '{first_name}', Last name: '{last_name}'")
        
        # Test the actual email finding
        try:
            print("🔍 Calling find_person_email...")
            result = email_finder.find_person_email(team_member.name, domain)
            
            if result:
                print(f"✅ Found email: {result.email}")
            else:
                print("❌ No email found")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_email_debug()