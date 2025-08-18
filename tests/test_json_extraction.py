#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import json
import re

def test_json_extraction():
    """Test JSON extraction from ProductHunt page"""
    
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
    
    # Look for Apollo GraphQL data using regex patterns
    scripts = soup.find_all('script')
    team_members = []
    
    for script in scripts:
        if script.string and 'ApolloSSRDataTransport' in script.string:
            script_content = script.string
            
            # Look for User objects with name and headline
            user_pattern = r'"__typename":"User"[^}]*"name":"([^"]+)"[^}]*"headline":"([^"]*)"[^}]*"username":"([^"]*)"'
            user_matches = re.findall(user_pattern, script_content)
            
            print(f"Found {len(user_matches)} User objects:")
            for name, headline, username in user_matches:
                print(f"  - {name}: {headline} (@{username})")
                team_members.append({
                    'name': name,
                    'role': headline,
                    'username': username
                })
            
            # Look for makers array pattern
            makers_pattern = r'"makers":\[([^\]]+)\]'
            makers_match = re.search(makers_pattern, script_content)
            if makers_match:
                makers_content = makers_match.group(1)
                print(f"Found makers array content: {len(makers_content)} characters")
                
                # Extract individual maker objects
                maker_pattern = r'"name":"([^"]+)"[^}]*"headline":"([^"]*)"[^}]*"username":"([^"]*)"'
                maker_matches = re.findall(maker_pattern, makers_content)
                
                print(f"Found {len(maker_matches)} makers:")
                for name, headline, username in maker_matches:
                    print(f"  - {name}: {headline} (@{username})")
                    team_members.append({
                        'name': name,
                        'role': headline,
                        'username': username
                    })
    
    print(f"\nTotal team members found: {len(team_members)}")
    
    # Remove duplicates
    unique_members = {}
    for member in team_members:
        name = member['name']
        if name and name not in unique_members:
            unique_members[name] = member
    
    print(f"Unique team members: {len(unique_members)}")
    for name, member in unique_members.items():
        print(f"  - {name}: {member['role']} (@{member['username']})")

if __name__ == "__main__":
    test_json_extraction()