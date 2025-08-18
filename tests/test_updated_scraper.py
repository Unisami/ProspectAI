#!/usr/bin/env python3
"""
Test the updated ProductHunt scraper
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_updated_scraper():
    """Test the updated ProductHunt scraper"""
    
    try:
        # Load config from environment
        config = Config.from_env()
        
        # Create scraper
        scraper = ProductHuntScraper(config)
        
        print("Testing updated ProductHunt scraper...")
        
        # Test getting latest products
        products = scraper.get_latest_products(limit=10)
        
        print(f"\n=== RESULTS ===")
        print(f"Found {len(products)} products")
        
        for i, product in enumerate(products, 1):
            print(f"\n{i}. {product.name}")
            print(f"   Company: {product.company_name}")
            print(f"   URL: {product.product_url}")
            print(f"   Description: {product.description}")
            print(f"   Website: {product.website_url}")
        
        return len(products) > 0
        
    except Exception as e:
        print(f"Error testing scraper: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_updated_scraper()
    print(f"\nTest {'PASSED' if success else 'FAILED'}")