#!/usr/bin/env python3
"""
Test script to verify that new Prospect objects have correct default values.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.data_models import Prospect, ProspectStatus
from datetime import datetime

def test_prospect_defaults():
    """Test that new Prospect objects have correct default values."""
    print("🧪 TESTING PROSPECT DEFAULT VALUES")
    print("=" * 50)
    
    # Create a new prospect with minimal required fields
    try:
        prospect = Prospect(
            name="Test User",
            role="Software Engineer", 
            company="Test Company"
        )
        
        print(f"✅ Created prospect: {prospect.name}")
        print(f"📧 Email-related field defaults:")
        print(f"  email_generation_status: '{prospect.email_generation_status}'")
        print(f"  email_delivery_status: '{prospect.email_delivery_status}'")
        print(f"  email_subject: '{prospect.email_subject}'")
        print(f"  email_content: '{prospect.email_content}'")
        print(f"  email_generated_date: {prospect.email_generated_date}")
        print(f"  email_sent_date: {prospect.email_sent_date}")
        
        # Verify expected defaults
        expected_defaults = {
            'email_generation_status': 'Not Generated',
            'email_delivery_status': 'Not Sent',
            'email_subject': '',
            'email_content': '',
            'email_generated_date': None,
            'email_sent_date': None
        }
        
        print(f"\n🎯 VERIFYING DEFAULTS:")
        all_correct = True
        for field, expected in expected_defaults.items():
            actual = getattr(prospect, field)
            if actual == expected:
                print(f"  ✅ {field}: '{actual}' (correct)")
            else:
                print(f"  ❌ {field}: '{actual}' (expected: '{expected}')")
                all_correct = False
        
        if all_correct:
            print(f"\n🎉 All default values are correct!")
        else:
            print(f"\n⚠️  Some default values are incorrect!")
            
        return all_correct
        
    except Exception as e:
        print(f"❌ Failed to create prospect: {e}")
        return False

if __name__ == "__main__":
    success = test_prospect_defaults()
    sys.exit(0 if success else 1)