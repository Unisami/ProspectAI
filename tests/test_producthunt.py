#!/usr/bin/env python3
"""
Test ProductHunt scraper to see what products it's returning.
"""

from services.product_hunt_scraper import ProductHuntScraper
from utils.config import Config

def test_producthunt():
    """Test ProductHunt scraper."""
    print("🔍 Testing ProductHunt Scraper")
    print("=" * 40)
    
    config = Config.from_env()
    scraper = ProductHuntScraper(config)
    
    # Get products multiple times to see if we get different results
    for attempt in range(3):
        print(f"\n🔄 Attempt {attempt + 1}:")
        try:
            products = scraper.get_latest_products(limit=10)
            print(f"📦 Found {len(products)} products")
            
            for i, product in enumerate(products[:5]):
                print(f"  {i+1}. {product.name} - {product.website_url}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_producthunt()