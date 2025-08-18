#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import re

def test_team_extraction():
    """Test team extraction from ProductHunt page"""
    
    url = "https://www.producthunt.com/products/quicko-pro"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    print(f"Fetching: {url}")
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print(f"Page title: {soup.title.string if soup.title else 'No title'}")
    
    # Look for team/maker information
    print("\n=== Looking for team-related text ===")
    team_keywords = ['maker', 'team', 'founder', 'developer', 'engineer', 'designer']
    
    for keyword in team_keywords:
        elements = soup.find_all(string=lambda text: text and keyword.lower() in text.lower())
        if elements:
            print(f"\nFound '{keyword}' in {len(elements)} places:")
            for i, element in enumerate(elements[:3]):  # Show first 3
                print(f"  {i+1}. {element.strip()[:100]}...")
    
    # Look for LinkedIn links
    print("\n=== Looking for LinkedIn links ===")
    linkedin_links = soup.find_all('a', href=lambda href: href and 'linkedin.com/in/' in href.lower())
    print(f"Found {len(linkedin_links)} LinkedIn links:")
    for link in linkedin_links[:5]:  # Show first 5
        print(f"  - {link.get('href')} (text: {link.get_text().strip()[:50]})")
    
    # Look for user avatars/images
    print("\n=== Looking for user images ===")
    user_images = soup.find_all('img', src=lambda src: src and any(keyword in src.lower() for keyword in ['avatar', 'user', 'profile']))
    print(f"Found {len(user_images)} user images:")
    for img in user_images[:5]:  # Show first 5
        print(f"  - {img.get('src')} (alt: {img.get('alt', 'No alt')})")
    
    # Look for JSON data that might contain team info
    print("\n=== Looking for JSON data ===")
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and ('maker' in script.string.lower() or 'team' in script.string.lower()):
            content = script.string[:500]
            print(f"Found script with team data: {content}...")
            
            # Try to extract JSON
            try:
                # Look for JSON objects
                json_matches = re.findall(r'\{[^{}]*"name"[^{}]*\}', script.string)
                for match in json_matches[:3]:
                    try:
                        data = json.loads(match)
                        if 'name' in data:
                            print(f"  JSON object: {data}")
                    except:
                        pass
            except:
                pass
    
    # Look for specific patterns that might indicate team members
    print("\n=== Looking for name patterns ===")
    # Look for patterns like "Name (Role)" or "Name - Role"
    text_content = soup.get_text()
    name_patterns = [
        r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\([^)]*(?:developer|engineer|designer|founder|ceo|cto)[^)]*\)',
        r'([A-Z][a-z]+ [A-Z][a-z]+)\s*-\s*(?:developer|engineer|designer|founder|ceo|cto)',
        r'([A-Z][a-z]+ [A-Z][a-z]+)\s*,\s*(?:developer|engineer|designer|founder|ceo|cto)',
    ]
    
    for pattern in name_patterns:
        matches = re.findall(pattern, text_content, re.IGNORECASE)
        if matches:
            print(f"Pattern matches: {matches}")

if __name__ == "__main__":
    test_team_extraction()