#!/usr/bin/env python3
"""
Check Hunter.io account limits and current usage.
"""

import sys
import os
import requests
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.configuration_service import get_configuration_service


def check_hunter_limits():
    """Check Hunter.io account limits."""
    # Get configuration
    config_service = get_configuration_service()
    config = config_service.get_config()
    
    api_key = config.hunter_api_key
    base_url = "https://api.hunter.io/v2"
    
    try:
        # Test with account info endpoint
        url = f"{base_url}/account"
        params = {'api_key': api_key}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("Hunter.io Account Information:")
            print(json.dumps(data, indent=2))
            
            # Extract rate limit information if available
            if 'data' in data:
                account_data = data['data']
                print(f"\nAccount Plan: {account_data.get('plan_name', 'Unknown')}")
                print(f"Requests available: {account_data.get('requests', {}).get('available', 'Unknown')}")
                print(f"Requests used: {account_data.get('requests', {}).get('used', 'Unknown')}")
                
        elif response.status_code == 401:
            print("Hunter.io API key is invalid")
        else:
            print(f"Hunter.io API returned status {response.status_code}")
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Hunter.io API connection failed: {str(e)}")


if __name__ == "__main__":
    check_hunter_limits()