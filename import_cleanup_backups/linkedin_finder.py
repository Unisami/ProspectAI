"""
Enhanced LinkedIn profile finder service for team members without LinkedIn URLs.
"""

import logging
import time
import re
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from models.data_models import TeamMember
from utils.config import Config

logger = logging.getLogger(__name__)


class LinkedInFinder:
    """
    Service to find LinkedIn profiles for team members who don't have LinkedIn URLs.
    Uses multiple search strategies including Google search, company website crawling,
    and social media profile discovery.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the LinkedIn finder.
        
        Args:
            config: Configuration object
        """
        self.config = config or Config.from_env()
        
        # Rate limiting
        self.last_request_time = 0
        self.request_delay = 2.0  # Delay between requests
        
        # HTTP session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Selenium options for JavaScript-heavy sites
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        
        logger.info("LinkedIn finder initialized")
    
    def find_linkedin_urls_for_team(self, team_members: List[TeamMember]) -> List[TeamMember]:
        """
        Find LinkedIn URLs for team members who don't have them.
        
        Args:
            team_members: List of TeamMember objects
            
        Returns:
            Updated list of TeamMember objects with LinkedIn URLs where found
        """
        updated_members = []
        members_without_linkedin = [m for m in team_members if not m.linkedin_url]
        
        logger.info(f"Finding LinkedIn URLs for {len(members_without_linkedin)} team members")
        
        for member in team_members:
            if member.linkedin_url:
                # Already has LinkedIn URL
                updated_members.append(member)
                continue
            
            logger.info(f"Searching for LinkedIn profile: {member.name} at {member.company}")
            
            # Try multiple search strategies
            linkedin_url = self._find_linkedin_url_for_member(member)
            
            if linkedin_url:
                logger.info(f"Found LinkedIn URL for {member.name}: {linkedin_url}")
                # Create updated member with LinkedIn URL
                updated_member = TeamMember(
                    name=member.name,
                    role=member.role,
                    company=member.company,
                    linkedin_url=linkedin_url
                )
                updated_members.append(updated_member)
            else:
                logger.warning(f"Could not find LinkedIn URL for {member.name}")
                updated_members.append(member)
            
            # Rate limiting
            self._wait_if_needed()
        
        found_count = len([m for m in updated_members if m.linkedin_url]) - len([m for m in team_members if m.linkedin_url])
        logger.info(f"Found {found_count} new LinkedIn URLs")
        
        return updated_members
    
    def _find_linkedin_url_for_member(self, member: TeamMember) -> Optional[str]:
        """
        Find LinkedIn URL for a specific team member using multiple strategies.
        
        Args:
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        # Strategy 1: Google search for LinkedIn profile
        linkedin_url = self._search_google_for_linkedin(member)
        if linkedin_url:
            return linkedin_url
        
        # Strategy 2: Search company website for team page with LinkedIn links
        linkedin_url = self._search_company_website(member)
        if linkedin_url:
            return linkedin_url
        
        # Strategy 3: Search social media aggregators
        linkedin_url = self._search_social_aggregators(member)
        if linkedin_url:
            return linkedin_url
        
        # Strategy 4: Try alternative name variations
        linkedin_url = self._search_name_variations(member)
        if linkedin_url:
            return linkedin_url
        
        return None
    
    def _search_google_for_linkedin(self, member: TeamMember) -> Optional[str]:
        """
        Search Google for LinkedIn profile of the team member.
        
        Args:
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        try:
            # Construct search query
            search_queries = [
                f'"{member.name}" {member.company} site:linkedin.com/in',
                f'"{member.name}" "{member.role}" {member.company} linkedin',
                f'{member.name} {member.company} linkedin profile',
            ]
            
            for query in search_queries:
                logger.debug(f"Google search query: {query}")
                
                # Use DuckDuckGo as it's more scraping-friendly than Google
                search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
                
                try:
                    response = self.session.get(search_url, timeout=15)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for LinkedIn URLs in search results
                    linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
                    
                    for link in linkedin_links:
                        href = link.get('href', '')
                        if self._is_valid_linkedin_profile_url(href):
                            # Verify this LinkedIn profile matches the person
                            if self._verify_linkedin_profile_match(href, member):
                                return self._clean_linkedin_url(href)
                    
                except Exception as e:
                    logger.debug(f"Search query failed: {query} - {str(e)}")
                    continue
                
                # Rate limiting between queries
                time.sleep(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Google search failed for {member.name}: {str(e)}")
            return None
    
    def _search_company_website(self, member: TeamMember) -> Optional[str]:
        """
        Search the company website for team pages with LinkedIn links.
        
        Args:
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        try:
            # Try to find company website
            company_domains = self._get_company_domains(member.company)
            
            for domain in company_domains:
                # Common team page URLs
                team_urls = [
                    f"https://{domain}/team",
                    f"https://{domain}/about",
                    f"https://{domain}/about-us",
                    f"https://{domain}/people",
                    f"https://{domain}/leadership",
                    f"https://{domain}/founders",
                ]
                
                for url in team_urls:
                    try:
                        response = self.session.get(url, timeout=15)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            
                            # Look for the person's name and nearby LinkedIn links
                            linkedin_url = self._find_linkedin_in_team_page(soup, member)
                            if linkedin_url:
                                return linkedin_url
                    
                    except Exception as e:
                        logger.debug(f"Failed to check {url}: {str(e)}")
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"Company website search failed for {member.name}: {str(e)}")
            return None
    
    def _search_social_aggregators(self, member: TeamMember) -> Optional[str]:
        """
        Search social media aggregator sites for LinkedIn profiles.
        
        Args:
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        try:
            # Sites that aggregate social media profiles
            aggregator_searches = [
                f"https://www.crunchbase.com/person/{member.name.lower().replace(' ', '-')}",
                f"https://angel.co/u/{member.name.lower().replace(' ', '-')}",
            ]
            
            for url in aggregator_searches:
                try:
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for LinkedIn links
                        linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
                        
                        for link in linkedin_links:
                            href = link.get('href', '')
                            if self._is_valid_linkedin_profile_url(href):
                                return self._clean_linkedin_url(href)
                
                except Exception as e:
                    logger.debug(f"Aggregator search failed for {url}: {str(e)}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Social aggregator search failed for {member.name}: {str(e)}")
            return None
    
    def _search_name_variations(self, member: TeamMember) -> Optional[str]:
        """
        Try searching with name variations (nicknames, initials, etc.).
        
        Args:
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        try:
            name_parts = member.name.split()
            if len(name_parts) < 2:
                return None
            
            # Generate name variations
            variations = []
            
            # First name + last name initial
            if len(name_parts) >= 2:
                variations.append(f"{name_parts[0]} {name_parts[-1][0]}")
            
            # First initial + last name
            if len(name_parts) >= 2:
                variations.append(f"{name_parts[0][0]} {name_parts[-1]}")
            
            # Common nickname variations
            nickname_map = {
                'william': 'bill', 'robert': 'bob', 'richard': 'rick', 'james': 'jim',
                'michael': 'mike', 'david': 'dave', 'christopher': 'chris', 'matthew': 'matt',
                'anthony': 'tony', 'daniel': 'dan', 'joseph': 'joe', 'thomas': 'tom'
            }
            
            first_name = name_parts[0].lower()
            if first_name in nickname_map:
                variations.append(f"{nickname_map[first_name].title()} {name_parts[-1]}")
            
            # Try each variation
            for variation in variations:
                logger.debug(f"Trying name variation: {variation}")
                
                # Create temporary member with variation
                temp_member = TeamMember(
                    name=variation,
                    role=member.role,
                    company=member.company,
                    linkedin_url=None
                )
                
                # Search with variation
                linkedin_url = self._search_google_for_linkedin(temp_member)
                if linkedin_url:
                    return linkedin_url
            
            return None
            
        except Exception as e:
            logger.error(f"Name variation search failed for {member.name}: {str(e)}")
            return None
    
    def _get_company_domains(self, company_name: str) -> List[str]:
        """
        Get possible domain names for a company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            List of possible domain names
        """
        domains = []
        
        # Clean company name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name.lower())
        clean_name = clean_name.replace(' ', '')
        
        # Common domain patterns
        domains.extend([
            f"{clean_name}.com",
            f"{clean_name}.io",
            f"{clean_name}.co",
            f"get{clean_name}.com",
            f"use{clean_name}.com",
        ])
        
        # If company name has multiple words, try combinations
        words = company_name.lower().split()
        if len(words) > 1:
            # First word only
            domains.append(f"{words[0]}.com")
            domains.append(f"{words[0]}.io")
            
            # Acronym
            acronym = ''.join([word[0] for word in words])
            domains.append(f"{acronym}.com")
            domains.append(f"{acronym}.io")
        
        return domains
    
    def _find_linkedin_in_team_page(self, soup: BeautifulSoup, member: TeamMember) -> Optional[str]:
        """
        Find LinkedIn URL for a specific member in a team page.
        
        Args:
            soup: BeautifulSoup object of the team page
            member: TeamMember object
            
        Returns:
            LinkedIn URL if found, None otherwise
        """
        try:
            # Look for the person's name in the page
            name_elements = soup.find_all(string=re.compile(re.escape(member.name), re.I))
            
            for name_element in name_elements:
                # Look for LinkedIn links near the name
                parent = name_element.parent
                
                # Check several parent levels
                for _ in range(5):
                    if parent:
                        linkedin_links = parent.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
                        
                        for link in linkedin_links:
                            href = link.get('href', '')
                            if self._is_valid_linkedin_profile_url(href):
                                return self._clean_linkedin_url(href)
                        
                        parent = parent.parent
                    else:
                        break
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding LinkedIn in team page: {str(e)}")
            return None
    
    def _is_valid_linkedin_profile_url(self, url: str) -> bool:
        """
        Check if a URL is a valid LinkedIn profile URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if valid LinkedIn profile URL, False otherwise
        """
        if not url:
            return False
        
        # Must contain linkedin.com/in/
        if 'linkedin.com/in/' not in url.lower():
            return False
        
        # Should not be a company page or other LinkedIn page type
        invalid_patterns = [
            'linkedin.com/company/',
            'linkedin.com/school/',
            'linkedin.com/groups/',
            'linkedin.com/showcase/',
        ]
        
        for pattern in invalid_patterns:
            if pattern in url.lower():
                return False
        
        return True
    
    def _clean_linkedin_url(self, url: str) -> str:
        """
        Clean and normalize LinkedIn URL.
        
        Args:
            url: Raw LinkedIn URL
            
        Returns:
            Cleaned LinkedIn URL
        """
        # Remove tracking parameters and fragments
        url = url.split('?')[0].split('#')[0]
        
        # Ensure https
        if url.startswith('http://'):
            url = url.replace('http://', 'https://')
        elif not url.startswith('https://'):
            url = 'https://' + url
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        return url
    
    def _verify_linkedin_profile_match(self, linkedin_url: str, member: TeamMember) -> bool:
        """
        Verify that a LinkedIn profile matches the team member.
        
        Args:
            linkedin_url: LinkedIn profile URL
            member: TeamMember object
            
        Returns:
            True if profile matches, False otherwise
        """
        try:
            # For now, we'll do basic verification
            # In a more advanced implementation, we could scrape the LinkedIn profile
            # to verify name and company match
            
            # Extract username from URL
            username = linkedin_url.split('/in/')[-1].split('/')[0]
            
            # Check if username contains parts of the person's name
            name_parts = member.name.lower().split()
            username_lower = username.lower()
            
            # If username contains significant parts of the name, consider it a match
            matches = 0
            for part in name_parts:
                if len(part) > 2 and part in username_lower:
                    matches += 1
            
            # Consider it a match if at least one significant name part is in the username
            return matches > 0
            
        except Exception as e:
            logger.debug(f"Profile verification failed: {str(e)}")
            return True  # Default to accepting the profile
    
    def _wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()