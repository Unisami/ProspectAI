"""
AI-powered team member extraction from ProductHunt pages.
"""

import logging
from typing import (
    List,
    Optional
)
import re

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from models.data_models import TeamMember
from services.ai_parser import AIParser
from utils.config import Config



logger = logging.getLogger(__name__)

class AITeamExtractor:
    """
    Extract team members from ProductHunt pages using AI.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the AI Team Extractor.
        
        Args:
            config: Configuration object
        """
        if not config:
            config = Config.from_env()
            
        self.config = config
        
        # Initialize AI parser
        try:
            self.ai_parser = AIParser(config)
            logger.info("AI Team Extractor initialized with AI parser")
        except Exception as e:
            logger.error(f"Failed to initialize AI parser: {e}")
            self.ai_parser = None
    
    def extract_team_from_product_url(self, product_url: str, company_name: str) -> List[TeamMember]:
        """
        Extract team members from a ProductHunt product URL using AI.
        
        Args:
            product_url: URL of the ProductHunt product page
            company_name: Name of the company
            
        Returns:
            List of TeamMember objects
        """
        if not self.ai_parser:
            logger.error("AI parser not available for team extraction")
            return []
        
        try:
            # Get raw HTML from the product page
            raw_html = self._get_product_page_html(product_url)
            if not raw_html:
                logger.warning(f"Failed to get HTML from {product_url}")
                return []
            
            # Extract team section from HTML
            team_html = self._extract_team_section(raw_html)
            if not team_html:
                logger.warning(f"No team section found in {product_url}")
                # Use the full HTML as fallback
                team_html = raw_html
            
            # Use AI to extract team members
            logger.debug(f"Team HTML content length: {len(team_html)} characters")
            logger.debug(f"Team HTML preview: {team_html[:500]}...")
            result = self.ai_parser.structure_team_data(team_html, company_name)
            
            if result.success and result.data:
                team_members = result.data
                logger.info(f"Successfully extracted {len(team_members)} team members using AI")
                return team_members
            else:
                error_msg = result.error_message or "Unknown error"
                logger.warning(f"AI team extraction failed: {error_msg}")
                logger.debug(f"AI response: {result.raw_response}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting team members: {e}")
            return []
    
    def _get_product_page_html(self, url: str) -> Optional[str]:
        """
        Get the raw HTML from a ProductHunt product page.
        
        Args:
            url: URL of the ProductHunt product page
            
        Returns:
            Raw HTML content or None if failed
        """
        # Try with Selenium first for JavaScript-rendered content
        try:
            logger.info(f"Getting HTML from {url} using Selenium")
            
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            try:
                driver.get(url)
                
                # Wait for page to load
                wait = WebDriverWait(driver, 15)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                
                # Get page source
                html = driver.page_source
                logger.info(f"Successfully got HTML from {url} using Selenium")
                return html
                
            except TimeoutException:
                logger.warning(f"Selenium timeout for {url}. Trying requests fallback.")
            except Exception as e:
                logger.warning(f"Selenium scraping failed for {url}: {e}. Trying requests fallback.")
            finally:
                driver.quit()
        
        except Exception as e:
            logger.warning(f"Failed to initialize Selenium: {e}")
        
        # Fallback to requests
        try:
            logger.info(f"Getting HTML from {url} using requests")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully got HTML from {url} using requests")
            return response.text
            
        except Exception as e:
            logger.error(f"Both Selenium and requests failed for {url}: {e}")
            return None
    
    def _extract_team_section(self, html: str) -> str:
        """
        Extract the team section from the HTML.
        
        Args:
            html: Raw HTML content
            
        Returns:
            HTML content of the team section or empty string if not found
        """
        try:
            
            soup = BeautifulSoup(html, 'html.parser')
            team_info = []
            
            # Strategy 1: Extract team data from Apollo GraphQL JSON using regex
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'ApolloSSRDataTransport' in script.string:
                    script_content = script.string
                    
                    # Look for User objects with name and headline using regex
                    user_pattern = r'"__typename":"User"[^}]*"name":"([^"]+)"[^}]*"headline":"([^"]*)"[^}]*"username":"([^"]*)"'
                    user_matches = re.findall(user_pattern, script_content)
                    
                    for name, headline, username in user_matches:
                        if name and any(role in headline.lower() for role in ['developer', 'engineer', 'designer', 'founder', 'ceo', 'cto', 'analyst', 'product']):
                            # Try to find LinkedIn URL for this user
                            linkedin_url = self._find_linkedin_url_for_user(username, script_content, soup)
                            team_info.append({
                                'name': name,
                                'role': headline,
                                'username': username,
                                'linkedin_url': linkedin_url,
                                'avatar': ''
                            })
                    
                    # Look for makers array pattern
                    makers_pattern = r'"makers":\[([^\]]+)\]'
                    makers_match = re.search(makers_pattern, script_content)
                    if makers_match:
                        makers_content = makers_match.group(1)
                        
                        # Extract individual maker objects
                        maker_pattern = r'"name":"([^"]+)"[^}]*"headline":"([^"]*)"[^}]*"username":"([^"]*)"'
                        maker_matches = re.findall(maker_pattern, makers_content)
                        
                        for name, headline, username in maker_matches:
                            if name:
                                # Try to find LinkedIn URL for this user
                                linkedin_url = self._find_linkedin_url_for_user(username, script_content, soup)
                                team_info.append({
                                    'name': name,
                                    'role': headline or 'Team Member',
                                    'username': username,
                                    'linkedin_url': linkedin_url,
                                    'avatar': ''
                                })
            
            # Strategy 2: Extract from user avatars and surrounding text
            user_images = soup.find_all('img', alt=True)
            for img in user_images:
                alt_text = img.get('alt', '')
                src = img.get('src', '')
                
                # Check if this looks like a user avatar
                if ('avatar' in src.lower() or 'ph-avatars' in src.lower()) and alt_text:
                    # Look for role information near the image
                    parent = img.parent
                    role = ''
                    linkedin_url = ''
                    
                    for _ in range(5):  # Go up a few levels
                        if parent:
                            text = parent.get_text()
                            # Look for role patterns
                            role_match = re.search(r'(developer|engineer|designer|founder|ceo|cto|analyst|product\s+designer)[^.]*', text.lower())
                            if role_match:
                                role = role_match.group(1).title()
                            
                            # Look for LinkedIn links in the parent element
                            linkedin_link = parent.find('a', href=re.compile(r'linkedin\.com', re.I))
                            if linkedin_link:
                                linkedin_url = linkedin_link.get('href', '')
                                break
                            parent = parent.parent
                        else:
                            break
                    
                    team_info.append({
                        'name': alt_text,
                        'role': role or 'Team Member',
                        'username': '',
                        'linkedin_url': linkedin_url,
                        'avatar': src
                    })
            
            # Strategy 3: Extract from text patterns and LinkedIn links
            text_content = soup.get_text()
            
            # Look for patterns like "— Name, role @ Company"
            name_role_patterns = [
                r'—\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*(developer|engineer|designer|founder)\s*@\s*\w+',
                r'I\'m\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),.*?(developer|engineer|designer|founder)',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\([^)]*(?:developer|engineer|designer|founder)[^)]*\)',
            ]
            
            for pattern in name_role_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple) and len(match) >= 2:
                        name, role = match[0], match[1]
                        # Try to find LinkedIn URL for this name
                        linkedin_url = self._find_linkedin_url_by_name(name.strip(), soup)
                        team_info.append({
                            'name': name.strip(),
                            'role': role.title(),
                            'username': '',
                            'linkedin_url': linkedin_url,
                            'avatar': ''
                        })
            
            # Strategy 4: Extract LinkedIn links directly and try to match with names
            linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
            for link in linkedin_links:
                linkedin_url = link.get('href', '')
                if linkedin_url:
                    # Try to find associated name
                    name = self._extract_name_from_linkedin_context(link)
                    if name:
                        # Check if we already have this person
                        existing = next((member for member in team_info if member['name'].lower() == name.lower()), None)
                        if existing:
                            # Update existing member with LinkedIn URL
                            existing['linkedin_url'] = linkedin_url
                        else:
                            # Add new member
                            team_info.append({
                                'name': name,
                                'role': 'Team Member',
                                'username': '',
                                'linkedin_url': linkedin_url,
                                'avatar': ''
                            })
            
            # Remove duplicates based on name
            unique_team = {}
            for member in team_info:
                name = member['name'].strip()
                if name and name not in unique_team:
                    unique_team[name] = member
            
            # Convert to HTML-like format for AI processing
            if unique_team:
                team_html = "<div class='team-section'>\n"
                for member in unique_team.values():
                    team_html += f"<div class='team-member'>\n"
                    team_html += f"  <div class='name'>{member['name']}</div>\n"
                    if member['role']:
                        team_html += f"  <div class='role'>{member['role']}</div>\n"
                    if member['username']:
                        team_html += f"  <div class='username'>@{member['username']}</div>\n"
                    if member.get('linkedin_url'):
                        team_html += f"  <div class='linkedin'>{member['linkedin_url']}</div>\n"
                    team_html += f"</div>\n"
                team_html += "</div>"
                
                logger.info(f"Extracted {len(unique_team)} team members from JSON and HTML data")
                return team_html
            
            logger.warning("No team information found in JSON or HTML data")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting team section: {e}")
            return ""
    
    def _find_linkedin_url_for_user(self, username: str, script_content: str, soup: BeautifulSoup) -> str:
        """
        Find LinkedIn URL for a specific user by username.
        
        Args:
            username: ProductHunt username
            script_content: JavaScript content to search
            soup: BeautifulSoup object of the page
            
        Returns:
            LinkedIn URL if found, empty string otherwise
        """
        if not username:
            return ""
        
        try:
            # Look for LinkedIn URL in the script content associated with this username
            linkedin_pattern = rf'"username":"{re.escape(username)}"[^}}]*"linkedin_url":"([^"]*)"'
            match = re.search(linkedin_pattern, script_content)
            if match:
                return match.group(1)
            
            # Look for LinkedIn links in HTML that might be associated with this username
            user_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
            for link in user_links:
                # Check if the link is near text containing the username
                parent = link.parent
                for _ in range(3):  # Check a few parent levels
                    if parent and username.lower() in parent.get_text().lower():
                        return link.get('href', '')
                    parent = parent.parent if parent else None
            
            return ""
        except Exception as e:
            logger.debug(f"Error finding LinkedIn URL for user {username}: {e}")
            return ""
    
    def _find_linkedin_url_by_name(self, name: str, soup: BeautifulSoup) -> str:
        """
        Find LinkedIn URL for a person by their name.
        
        Args:
            name: Person's name
            soup: BeautifulSoup object of the page
            
        Returns:
            LinkedIn URL if found, empty string otherwise
        """
        if not name:
            return ""
        
        try:
            # Look for LinkedIn links near text containing the person's name
            linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
            
            for link in linkedin_links:
                # Check if the link is near text containing the name
                parent = link.parent
                for _ in range(5):  # Check several parent levels
                    if parent:
                        text = parent.get_text()
                        # Check if name appears in the text (case insensitive)
                        if name.lower() in text.lower():
                            return link.get('href', '')
                        parent = parent.parent
                    else:
                        break
            
            return ""
        except Exception as e:
            logger.debug(f"Error finding LinkedIn URL for name {name}: {e}")
            return ""
    
    def _extract_name_from_linkedin_context(self, link_element) -> str:
        """
        Extract a person's name from the context around a LinkedIn link.
        
        Args:
            link_element: BeautifulSoup element containing the LinkedIn link
            
        Returns:
            Person's name if found, empty string otherwise
        """
        try:
            # Check link text first
            link_text = link_element.get_text().strip()
            if link_text and not link_text.lower().startswith('linkedin'):
                # If link text looks like a name (contains letters and spaces)
                if re.match(r'^[A-Za-z\s]+$', link_text) and len(link_text.split()) >= 2:
                    return link_text
            
            # Look in surrounding elements for names
            parent = link_element.parent
            for _ in range(3):  # Check a few parent levels
                if parent:
                    text = parent.get_text()
                    # Look for name patterns (First Last, First Middle Last, etc.)
                    name_patterns = [
                        r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',  # First Last or First Middle Last
                        r'@([A-Za-z]+(?:[A-Za-z0-9_]*[A-Za-z0-9])?)',  # @username pattern
                    ]
                    
                    for pattern in name_patterns:
                        matches = re.findall(pattern, text)
                        for match in matches:
                            # Skip common non-name words
                            if match.lower() not in ['linkedin', 'profile', 'connect', 'follow', 'view', 'team', 'about']:
                                return match.strip()
                    
                    parent = parent.parent
                else:
                    break
            
            return ""
        except Exception as e:
            logger.debug(f"Error extracting name from LinkedIn context: {e}")
            return ""
