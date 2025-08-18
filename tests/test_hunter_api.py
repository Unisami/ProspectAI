#!/usr/bin/env python3
"""
Test Hunter.io API connectivity
"""

import requests

def test_hunter_api():
    """Test Hunter.io API connectivity"""
    
    api_key = "bd6eedb2c639840d083b5905de41e0540e90cd25"
    
    try:
        # Test with a simple domain search
        url = f"https://api.hunter.io/v2/domain-search"
        params = {
            'domain': 'google.com',
            'api_key': api_key,
            'limit': 5
        }
        
        response = requests.get(url, params=params)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            print("Hunter.io API test successful!")
            return True
        else:
            print(f"Hunter.io API test failed with status {response.status_code}")
            return False
        
    except Exception as e:
        print(f"Hunter.io API test failed: {e}")
        return False

if __name__ == "__main__":
    test_hunter_api()