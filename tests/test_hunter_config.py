#!/usr/bin/env python3

from utils.config import Config
import os

def test_hunter_config():
    """Test Hunter.io API configuration"""
    
    print("=== Hunter.io API Configuration Test ===")
    
    # Check environment variable
    hunter_key = os.getenv("HUNTER_API_KEY")
    print(f"HUNTER_API_KEY environment variable: {'✅ Set' if hunter_key else '❌ Not set'}")
    if hunter_key:
        print(f"Key length: {len(hunter_key)} characters")
        print(f"Key preview: {hunter_key[:10]}...{hunter_key[-5:] if len(hunter_key) > 15 else hunter_key}")
    
    # Check config loading
    try:
        config = Config.from_env()
        print(f"Config hunter_api_key: {'✅ Loaded' if config.hunter_api_key else '❌ Not loaded'}")
        if config.hunter_api_key:
            print(f"Config key length: {len(config.hunter_api_key)} characters")
        
        # Validate config
        validation = config.validate()
        print(f"Hunter API key validation: {'✅ Valid' if validation.get('hunter_api_key') else '❌ Invalid'}")
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")

if __name__ == "__main__":
    test_hunter_config()