#!/usr/bin/env python3
"""
Test script to fetch ProductHunt homepage and analyze its structure
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def test_producthunt_raw():
    """Test fetching ProductHunt homepage and analyze structure"""
    
    # Set up session with proper headers
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    
    try:
        print("Fetching ProductHunt homepage...")
        response = session.get("https://www.producthunt.com/", timeout=30)
        response.raise_for_status()
        
        print(f"Response status: {response.status_code}")
        print(f"Content length: {len(response.content)}")
        print(f"Content type: {response.headers.get('content-type', 'unknown')}")
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Analyze the page structure
        print("\n=== PAGE ANALYSIS ===")
        
        # Look for any links containing 'posts'
        post_links = soup.find_all('a', href=re.compile(r'/posts/'))
        print(f"Found {len(post_links)} links containing '/posts/'")
        
        # Show first few post links
        for i, link in enumerate(post_links[:5]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"  {i+1}. {href} -> '{text}'")
        
        # Look for ALL links to understand the structure
        all_links = soup.find_all('a', href=True)
        print(f"\nFound {len(all_links)} total links")
        
        # Show sample of all links
        for i, link in enumerate(all_links[:10]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            print(f"  {i+1}. {href} -> '{text}'")
        
        # Look for links that might be products
        product_like_links = [link for link in all_links if any(word in link.get('href', '').lower() for word in ['product', 'launch', 'today'])]
        print(f"\nFound {len(product_like_links)} product-like links")
        for i, link in enumerate(product_like_links[:5]):
            href = link.get('href', '')
            text = link.get_text(strip=True)[:50]
            print(f"  {i+1}. {href} -> '{text}'")
        
        # Look for common ProductHunt patterns
        print(f"\nLooking for common patterns...")
        
        # Check for data attributes
        data_elements = soup.find_all(attrs=lambda x: x and isinstance(x, dict) and any(k.startswith('data-') for k in x.keys()))
        print(f"Found {len(data_elements)} elements with data attributes")
        
        # Look for JSON data in script tags
        script_tags = soup.find_all('script')
        json_scripts = []
        for script in script_tags:
            if script.string and ('posts' in script.string.lower() or 'product' in script.string.lower()):
                json_scripts.append(script)
        
        print(f"Found {len(json_scripts)} script tags with product/posts data")
        
        # Try to find JSON data
        for i, script in enumerate(json_scripts[:3]):
            print(f"\nScript {i+1} content preview:")
            content = script.string[:500] if script.string else ""
            print(content)
        
        # Look for specific ProductHunt classes
        product_containers = soup.find_all(['div', 'article'], class_=re.compile(r'.*product.*|.*post.*|.*item.*', re.I))
        print(f"\nFound {len(product_containers)} potential product containers")
        
        # Save raw HTML for inspection
        with open('producthunt_raw.html', 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        print("\nSaved raw HTML to 'producthunt_raw.html' for inspection")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_producthunt_raw()