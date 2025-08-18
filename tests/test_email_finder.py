#!/usr/bin/env python3
"""
Test the updated email finder with individual email finding
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.email_finder import EmailFinder
from models.data_models import TeamMember
from utils.config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_email_finder():
    """Test the email finder with individual email finding"""
    
    try:
        # Load config
        config = Config.from_env()
        
        # Create email finder
        email_finder = EmailFinder(config)
        
        print("Testing individual email finder...")
        
        # Test with a known person and domain
        test_name = "Alexis Ohanian"
        test_domain = "reddit.com"
        
        print(f"Looking for email: {test_name} at {test_domain}")
        
        # Test individual email finding
        email_data = email_finder.find_person_email(test_name, test_domain)
        
        if email_data:
            print(f"Found email: {email_data.email}")
            print(f"Confidence: {email_data.confidence}")
            print(f"Position: {email_data.position}")
        else:
            print("No email found")
        
        # Test with team members
        team_members = [
            TeamMember(name="Alexis Ohanian", role="Co-founder", company="Reddit", linkedin_url=None)
        ]
        
        print(f"\nTesting team email finding...")
        results = email_finder.find_and_verify_team_emails(team_members, test_domain)
        
        print(f"Results: {len(results)} emails found")
        for name, result in results.items():
            email_data = result['email_data']
            verification = result['verification']
            print(f"{name}: {email_data.email} (verified: {verification.result if verification else 'not verified'})")
        
        return True
        
    except Exception as e:
        print(f"Error testing email finder: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_email_finder()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")