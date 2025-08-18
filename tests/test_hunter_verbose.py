#!/usr/bin/env python3

import logging
from services.email_finder import EmailFinder
from utils.config import Config

def test_hunter_verbose():
    """Test Hunter.io API with verbose logging"""
    
    # Set up verbose logging
    logging.basicConfig(level=logging.DEBUG)
    
    config = Config.from_env()
    email_finder = EmailFinder(config)
    
    print("=== Testing Hunter.io API Call ===")
    
    # Test with a simple name and domain
    name = "Charu Chaturvedi"
    domain = "quicko.pro"
    
    print(f"Testing: {name} at {domain}")
    
    try:
        result = email_finder.find_person_email(name, domain)
        
        if result:
            print(f"✅ Found email: {result.email}")
            print(f"   Confidence: {result.confidence}")
            print(f"   Sources: {result.sources}")
        else:
            print("❌ No email found")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hunter_verbose()