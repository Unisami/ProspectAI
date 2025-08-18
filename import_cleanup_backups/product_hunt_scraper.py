"""
ProductHunt scraper using requests and BeautifulSoup for web scraping.
"""

import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import re
from functools import wraps
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from models.data_models import CompanyData, TeamMember
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.webdriver_manager import get_webdriver_manager
from services.ai_parser import AIParser, ParseResult


logger = logging.getLogger(__name__)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


@dataclass
class ProductData:
    """Data structure for ProductHunt product information."""
    name: str
    company_name: str
    website_url: str
    product_url: str
    description: str
    launch_date: datetime
    team_section_url: Optional[str] = None


class RateLimiter:
    """Simple rate limiter for web scraping."""
    
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.last_request_time = 0.0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


class ProductHuntScraper:
    """
    ProductHunt scraper using requests and BeautifulSoup for web scraping.
    
    This class handles:
    - Scraping ProductHunt for new product launches
    - Extracting company information and team details
    - Rate limiting and retry mechanisms
    - Error handling for failed scraping attempts
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the ProductHunt scraper.
        
        Args:
            config: Configuration object (deprecated, use ConfigurationService)
        """
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            logger.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            self.config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            self.config = config_service.get_config()
        
        self.rate_limiter = RateLimiter(delay=self.config.scraping_delay)
        
        # HTTP session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize WebDriver manager
        self.webdriver_manager = get_webdriver_manager(self.config)
        
        # Initialize AI parser for enhanced team extraction
        try:
            self.ai_parser = AIParser(self.config)
            self.use_ai_parsing = True
            logger.info("AI parsing enabled for ProductHunt scraper")
        except Exception as e:
            logger.warning(f"Failed to initialize AI parser: {e}. Falling back to traditional parsing.")
            self.ai_parser = None
            self.use_ai_parsing = False
        
        logger.info("ProductHuntScraper initialized with requests and BeautifulSoup")
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def get_latest_products(self, limit: int = 50) -> List[ProductData]:
        """
        Scrape ProductHunt for the latest product launches using raw HTTP requests.
        
        Args:
            limit: Maximum number of products to retrieve
            
        Returns:
            List of ProductData objects containing product information
            
        Raises:
            Exception: If scraping fails after all retry attempts
        """
        logger.info(f"Scraping ProductHunt for latest {limit} products using raw HTTP")
        
        self.rate_limiter.wait_if_needed()
        
        # ProductHunt URL for latest products
        url = "https://www.producthunt.com/"
        
        try:
            # Use raw GET request instead of Selenium
            logger.info("Making raw GET request to ProductHunt homepage")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully fetched ProductHunt page, content length: {len(response.content)}")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product information from the page
            products = self._extract_products_from_raw_html(soup, limit)
            
            # If we didn't get any products, try alternative extraction methods
            if not products:
                logger.warning("No products found with primary method, trying alternative extraction")
                products = self._extract_products_alternative_raw(soup, limit)
            
            # If still no products, try the API approach
            if not products:
                logger.warning("No products found with HTML parsing, trying API approach")
                products = self._try_api_approach(limit)
            
            logger.info(f"Successfully scraped {len(products)} products from ProductHunt")
            return products
            
        except requests.RequestException as e:
            logger.error(f"HTTP request error while scraping ProductHunt: {str(e)}")
            # Fallback to Selenium if HTTP fails
            logger.info("Falling back to Selenium approach")
            return self._get_products_with_selenium(limit)
        except Exception as e:
            logger.error(f"Failed to scrape ProductHunt: {str(e)}")
            raise
    
    @retry_with_backoff(max_retries=3, base_delay=1.5)
    def extract_team_info(self, product_url: str) -> List[TeamMember]:
        """
        Extract team member information from a product's page using AI parsing with fallback.
        Enhanced with LinkedIn URL finding for members without LinkedIn profiles.
        
        Args:
            product_url: URL of the ProductHunt product page
            
        Returns:
            List of TeamMember objects with LinkedIn URLs where possible
            
        Raises:
            Exception: If team extraction fails after all retry attempts
        """
        logger.info(f"Extracting team info from: {product_url}")
        
        self.rate_limiter.wait_if_needed()
        
        try:
            # Extract company name for team members
            company_name = self._extract_company_from_url(product_url)
            
            # Use our dedicated AI team extractor
            from services.ai_team_extractor import AITeamExtractor
            team_extractor = AITeamExtractor(self.config)
            team_members = team_extractor.extract_team_from_product_url(product_url, company_name)
            
            if not team_members:
                # Fall back to traditional parsing if AI extraction failed
                logger.info("AI team extraction failed, using traditional team extraction")
                
                # Get the raw HTML using requests
                response = self.session.get(product_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Use traditional extraction method
                team_members = self._extract_team_from_soup(soup, product_url)
            
            if team_members:
                logger.info(f"Successfully extracted {len(team_members)} team members")
                
                # Find LinkedIn URLs for members who don't have them
                members_without_linkedin = [m for m in team_members if not m.linkedin_url]
                if members_without_linkedin:
                    logger.info(f"Finding LinkedIn URLs for {len(members_without_linkedin)} team members")
                    
                    try:
                        from services.linkedin_finder import LinkedInFinder
                        linkedin_finder = LinkedInFinder(self.config)
                        team_members = linkedin_finder.find_linkedin_urls_for_team(team_members)
                        
                        # Log results
                        members_with_linkedin = [m for m in team_members if m.linkedin_url]
                        logger.info(f"LinkedIn URL discovery complete: {len(members_with_linkedin)}/{len(team_members)} members now have LinkedIn URLs")
                        
                    except Exception as e:
                        logger.warning(f"LinkedIn URL finding failed: {str(e)}")
                        # Continue with original team members if LinkedIn finding fails
                
                return team_members
            else:
                logger.warning(f"No team members found for {product_url}")
                return []
            
        except Exception as e:
            logger.error(f"Failed to extract team info from {product_url}: {str(e)}")
            raise
    
    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def extract_company_domain(self, product_data: ProductData) -> str:
        """
        Extract the company domain from product information.
        
        Args:
            product_data: ProductData object containing product information
            
        Returns:
            Company domain string (e.g., "example.com")
            
        Raises:
            Exception: If domain extraction fails
        """
        logger.info(f"Extracting domain for company: {product_data.company_name}")
        
        # If we don't have a website URL, try to extract it from the product page
        if not product_data.website_url:
            from services.website_extractor import WebsiteExtractor
            website_extractor = WebsiteExtractor()
            website_url = website_extractor.extract_website_url(product_data.product_url)
            if website_url:
                logger.info(f"Found website URL: {website_url}")
                product_data.website_url = website_url
        
        # Try to extract domain from website URL
        if product_data.website_url:
            try:
                parsed_url = urlparse(product_data.website_url)
                domain = parsed_url.netloc.lower()
                
                # Remove www. prefix if present
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                logger.info(f"Extracted domain: {domain}")
                return domain
                
            except Exception as e:
                logger.warning(f"Failed to parse URL {product_data.website_url}: {str(e)}")
        
        # If no website URL or parsing failed, try to scrape the product page for links
        self.rate_limiter.wait_if_needed()
        
        try:
            # Use requests to get the product page
            response = self.session.get(product_data.product_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for external links that might be the company website
            domain = self._find_company_domain_in_soup(soup, product_data.company_name)
            
            if domain:
                logger.info(f"Successfully extracted domain: {domain}")
                return domain
            else:
                logger.warning(f"Could not extract domain for {product_data.company_name}")
                return ""
                
        except Exception as e:
            logger.error(f"Failed to extract domain: {str(e)}")
            raise
    
    def _parse_product_results(self, result: Dict[str, Any], limit: int) -> List[ProductData]:
        """
        Parse the raw scraping results into ProductData objects.
        
        Args:
            result: Raw result from ScrapeGraphAI
            limit: Maximum number of products to return
            
        Returns:
            List of ProductData objects
        """
        products = []
        
        try:
            # The exact structure depends on what ScrapeGraphAI returns
            # This is a basic implementation that may need adjustment
            if isinstance(result, dict) and 'products' in result:
                product_list = result['products']
            elif isinstance(result, list):
                product_list = result
            else:
                # If result is a string, try to parse it
                logger.warning("Unexpected result format, attempting to parse as text")
                return self._parse_text_result(str(result), limit)
            
            for i, product_info in enumerate(product_list[:limit]):
                if isinstance(product_info, dict):
                    product = ProductData(
                        name=product_info.get('name', ''),
                        company_name=product_info.get('company_name', product_info.get('name', '')),
                        website_url=product_info.get('website_url', ''),
                        product_url=product_info.get('product_url', ''),
                        description=product_info.get('description', ''),
                        launch_date=self._parse_date(product_info.get('launch_date', ''))
                    )
                    products.append(product)
                    
        except Exception as e:
            logger.error(f"Error parsing product results: {str(e)}")
            # Return empty list rather than failing completely
            return []
        
        return products
    
    def _parse_team_results(self, result: Dict[str, Any], product_url: str) -> List[TeamMember]:
        """
        Parse the raw team extraction results into TeamMember objects.
        
        Args:
            result: Raw result from ScrapeGraphAI
            product_url: URL of the product page
            
        Returns:
            List of TeamMember objects
        """
        team_members = []
        
        try:
            # Extract company name from URL for team members
            company_name = self._extract_company_from_url(product_url)
            
            # Parse team member information
            if isinstance(result, dict) and 'team_members' in result:
                member_list = result['team_members']
            elif isinstance(result, list):
                member_list = result
            else:
                # If result is a string, try to parse it
                logger.warning("Unexpected team result format, attempting to parse as text")
                return self._parse_team_text_result(str(result), company_name)
            
            for member_info in member_list:
                if isinstance(member_info, dict):
                    team_member = TeamMember(
                        name=member_info.get('name', ''),
                        role=member_info.get('role', member_info.get('title', '')),
                        linkedin_url=member_info.get('linkedin_url', ''),
                        company=company_name
                    )
                    team_members.append(team_member)
                    
        except Exception as e:
            logger.error(f"Error parsing team results: {str(e)}")
            return []
        
        return team_members
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string into datetime object."""
        if not date_str:
            return datetime.now()
        
        try:
            # Try common date formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        
        # Default to current date if parsing fails
        return datetime.now()
    
    def _extract_company_from_url(self, product_url: str) -> str:
        """Extract company name from ProductHunt URL."""
        try:
            # ProductHunt URLs now follow pattern: /products/product-name
            parts = product_url.split('/')
            if 'products' in parts:
                idx = parts.index('products')
                if idx + 1 < len(parts):
                    return parts[idx + 1].replace('-', ' ').title()
            # Fallback for old /posts/ pattern
            elif 'posts' in parts:
                idx = parts.index('posts')
                if idx + 1 < len(parts):
                    return parts[idx + 1].replace('-', ' ').title()
        except Exception:
            pass
        
        return "Unknown Company"
    
    def _extract_domain_from_result(self, result: Any) -> str:
        """Extract domain from scraping result."""
        if isinstance(result, dict):
            return result.get('domain', '')
        elif isinstance(result, str):
            # Simple regex to find domain-like strings
            import re
            domain_pattern = r'([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}'
            matches = re.findall(domain_pattern, result)
            if matches:
                return matches[0]
        
        return ""
    
    def _parse_text_result(self, text: str, limit: int) -> List[ProductData]:
        """Fallback method to parse text results."""
        # This is a simplified implementation
        # In practice, you might want more sophisticated text parsing
        logger.warning("Using fallback text parsing for products")
        return []
    
    def _parse_team_text_result(self, text: str, company_name: str) -> List[TeamMember]:
        """Fallback method to parse team text results."""
        # This is a simplified implementation
        # In practice, you might want more sophisticated text parsing
        logger.warning("Using fallback text parsing for team members")
        return []
    
    def _extract_products_from_soup(self, soup: BeautifulSoup, limit: int) -> List[ProductData]:
        """
        Extract product information from ProductHunt homepage BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object of the ProductHunt homepage
            limit: Maximum number of products to extract
            
        Returns:
            List of ProductData objects
        """
        products = []
        
        try:
            # Look for product cards on the homepage
            # ProductHunt structure may change, so we'll look for common patterns
            product_elements = soup.find_all(['div', 'article'], class_=re.compile(r'.*product.*|.*item.*', re.I))
            
            if not product_elements:
                # Try alternative selectors - look for links to posts
                product_elements = soup.find_all('a', href=re.compile(r'/posts/'))
            
            logger.debug(f"Found {len(product_elements)} potential product elements")
            
            for element in product_elements[:limit]:
                try:
                    product_data = self._extract_single_product_from_element(element)
                    if product_data:
                        products.append(product_data)
                        logger.debug(f"Successfully extracted product: {product_data.name}")
                except Exception as e:
                    logger.warning(f"Failed to extract product from element: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting products from soup: {str(e)}")
        
        return products
    
    def _extract_single_product_from_element(self, element) -> Optional[ProductData]:
        """
        Extract product data from a single HTML element.
        
        Args:
            element: BeautifulSoup element containing product information
            
        Returns:
            ProductData object or None if extraction fails
        """
        try:
            # If the element itself is an 'a' tag with href to posts, extract from it
            if element.name == 'a' and element.get('href', '').startswith('/posts/'):
                # Extract product name from h3 within the link
                name_element = element.find(['h1', 'h2', 'h3', 'h4'])
                product_name = name_element.get_text(strip=True) if name_element else ""
                
                # Extract product URL
                href = element.get('href', '')
                product_url = f"https://www.producthunt.com{href}" if href.startswith('/') else href
                
                # Extract description from p within the link
                desc_element = element.find('p')
                description = desc_element.get_text(strip=True) if desc_element else ""
                
            else:
                # Extract product name
                name_element = element.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'.*name.*|.*title.*', re.I))
                if not name_element:
                    name_element = element.find(['h1', 'h2', 'h3', 'h4'])
                
                product_name = name_element.get_text(strip=True) if name_element else ""
                
                # Extract product URL
                link_element = element.find('a', href=re.compile(r'/posts/'))
                product_url = ""
                if link_element:
                    href = link_element.get('href', '')
                    if href.startswith('/'):
                        product_url = f"https://www.producthunt.com{href}"
                    else:
                        product_url = href
                
                # Extract description
                desc_element = element.find(['p', 'div'], class_=re.compile(r'.*desc.*|.*summary.*', re.I))
                if not desc_element:
                    desc_element = element.find('p')
                description = desc_element.get_text(strip=True) if desc_element else ""
            
            # Extract company name (often same as product name for new products)
            company_name = product_name
            
            # Try to find website URL (this might not be available on the homepage)
            website_url = ""
            
            if product_name and product_url:
                return ProductData(
                    name=product_name,
                    company_name=company_name,
                    website_url=website_url,
                    product_url=product_url,
                    description=description,
                    launch_date=datetime.now()  # Default to current date
                )
                
        except Exception as e:
            logger.warning(f"Failed to extract product data: {str(e)}")
        
        return None
    
    def _extract_team_from_soup(self, soup: BeautifulSoup, product_url: str) -> List[TeamMember]:
        """
        Extract team member information from ProductHunt product page BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            
        Returns:
            List of TeamMember objects
        """
        team_members = []
        company_name = self._extract_company_from_url(product_url)
        
        try:
            # Multiple strategies to find team information
            team_sections = []
            
            # Strategy 1: Look for team/maker sections by class
            team_sections.extend(soup.find_all(['div', 'section'], class_=re.compile(r'.*team.*|.*maker.*|.*creator.*', re.I)))
            
            # Strategy 2: Look for sections with team-related text
            text_elements = soup.find_all(string=re.compile(r'team|maker|creator|founder|co-founder', re.I))
            for text_elem in text_elements:
                if text_elem.parent and text_elem.parent not in team_sections:
                    # Get the parent container that might contain team info
                    parent = text_elem.parent
                    while parent and parent.name not in ['div', 'section', 'article']:
                        parent = parent.parent
                    if parent:
                        team_sections.append(parent)
            
            # Strategy 3: Look for common ProductHunt team section patterns
            team_sections.extend(soup.find_all(['div'], attrs={'data-test': re.compile(r'.*team.*|.*maker.*', re.I)}))
            
            # Strategy 4: Look for sections containing LinkedIn links (often team sections)
            linkedin_sections = soup.find_all(['div', 'section'], string=re.compile(r'linkedin', re.I))
            for section in linkedin_sections:
                if section not in team_sections:
                    team_sections.append(section)
            
            # Remove duplicates while preserving order
            unique_sections = []
            for section in team_sections:
                if section not in unique_sections:
                    unique_sections.append(section)
            
            logger.debug(f"Found {len(unique_sections)} potential team sections")
            
            for section in unique_sections:
                try:
                    members = self._extract_team_members_from_section(section, company_name)
                    # Avoid duplicates
                    for member in members:
                        if not any(existing.name == member.name and existing.company == member.company 
                                 for existing in team_members):
                            team_members.append(member)
                except Exception as e:
                    logger.warning(f"Failed to extract team from section: {str(e)}")
                    continue
            
            # If no team members found, try to extract from any LinkedIn links on the page
            if not team_members:
                team_members = self._extract_team_from_linkedin_links(soup, company_name)
                    
        except Exception as e:
            logger.error(f"Error extracting team from soup: {str(e)}")
        
        logger.info(f"Extracted {len(team_members)} team members from {product_url}")
        return team_members
    
    def _extract_team_members_from_section(self, section, company_name: str) -> List[TeamMember]:
        """
        Extract team members from a specific section of the page.
        
        Args:
            section: BeautifulSoup element containing team information
            company_name: Name of the company
            
        Returns:
            List of TeamMember objects
        """
        team_members = []
        
        try:
            # Look for individual team member elements
            member_elements = section.find_all(['div', 'li', 'span'], class_=re.compile(r'.*member.*|.*person.*|.*user.*', re.I))
            
            if not member_elements:
                # Try to find links that might be team member profiles
                member_elements = section.find_all('a', href=re.compile(r'/@|/users/|linkedin\.com', re.I))
            
            for element in member_elements:
                try:
                    member = self._extract_single_team_member(element, company_name)
                    if member:
                        team_members.append(member)
                except Exception as e:
                    logger.warning(f"Failed to extract team member: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting team members from section: {str(e)}")
        
        return team_members
    
    def _extract_single_team_member(self, element, company_name: str) -> Optional[TeamMember]:
        """
        Extract a single team member from an HTML element.
        
        Args:
            element: BeautifulSoup element containing team member information
            company_name: Name of the company
            
        Returns:
            TeamMember object or None if extraction fails
        """
        try:
            # Extract name
            name = ""
            name_element = element.find(['span', 'div', 'h1', 'h2', 'h3', 'h4'], class_=re.compile(r'.*name.*', re.I))
            if name_element:
                name = name_element.get_text(strip=True)
            elif element.get_text(strip=True):
                # Use the element's text as name if no specific name element found
                potential_name = element.get_text(strip=True)
                # Skip if the text is just "LinkedIn" or similar generic text
                if potential_name.lower() not in ['linkedin', 'profile', 'connect', 'follow', 'view profile']:
                    name = potential_name
            
            # Extract role/title
            role = ""
            role_element = element.find(['span', 'div'], class_=re.compile(r'.*role.*|.*title.*|.*position.*', re.I))
            if role_element:
                role = role_element.get_text(strip=True)
            
            # Provide default role if none found
            if not role:
                role = "Team Member"
            
            # Extract LinkedIn URL
            linkedin_url = ""
            # Check if the element itself is a LinkedIn link
            if element.name == 'a' and element.get('href', '') and 'linkedin.com' in element.get('href', '').lower():
                linkedin_url = element.get('href', '')
            else:
                # Look for LinkedIn links within the element
                linkedin_link = element.find('a', href=re.compile(r'linkedin\.com', re.I))
                if linkedin_link:
                    linkedin_url = linkedin_link.get('href', '')
            
            if name:
                return TeamMember(
                    name=name,
                    role=role,
                    linkedin_url=linkedin_url,
                    company=company_name
                )
                
        except Exception as e:
            logger.warning(f"Failed to extract team member data: {str(e)}")
        
        return None
    
    def _find_company_domain_in_soup(self, soup: BeautifulSoup, company_name: str) -> str:
        """
        Find company domain from links in the BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object of the page
            company_name: Name of the company to look for
            
        Returns:
            Company domain string or empty string if not found
        """
        try:
            # Look for external links that might be the company website
            external_links = soup.find_all('a', href=re.compile(r'^https?://(?!.*producthunt\.com)'))
            
            for link in external_links:
                href = link.get('href', '')
                try:
                    parsed_url = urlparse(href)
                    domain = parsed_url.netloc.lower()
                    
                    # Remove www. prefix if present
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    
                    # Skip common social media and other non-company domains
                    skip_domains = ['twitter.com', 'facebook.com', 'instagram.com', 'youtube.com', 'github.com']
                    if not any(skip_domain in domain for skip_domain in skip_domains):
                        return domain
                        
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding company domain: {str(e)}")
        
        return ""
    
    def _extract_products_from_raw_html(self, soup: BeautifulSoup, limit: int) -> List[ProductData]:
        """
        Extract products from raw HTML using improved selectors for current ProductHunt structure.
        
        Args:
            soup: BeautifulSoup object of the ProductHunt homepage
            limit: Maximum number of products to extract
            
        Returns:
            List of ProductData objects
        """
        products = []
        
        try:
            logger.info("Extracting products from raw HTML using updated ProductHunt structure")
            
            # ProductHunt now uses /products/ instead of /posts/
            product_links = []
            
            # Strategy 1: Find all links containing '/products/'
            all_links = soup.find_all('a', href=True)
            product_links.extend([link for link in all_links if '/products/' in link.get('href', '')])
            
            logger.info(f"Found {len(product_links)} potential product links")
            
            # Extract unique products
            seen_urls = set()
            for link in product_links:
                if len(products) >= limit:
                    break
                    
                try:
                    href = link.get('href', '')
                    if not href or '/products/' not in href:
                        continue
                        
                    # Build full URL
                    if href.startswith('/'):
                        product_url = f"https://www.producthunt.com{href}"
                    else:
                        product_url = href
                    
                    if product_url in seen_urls:
                        continue
                    seen_urls.add(product_url)
                    
                    # Extract product information using updated structure
                    product_data = self._extract_product_from_current_structure(link, product_url, soup)
                    if product_data:
                        products.append(product_data)
                        logger.debug(f"Extracted product: {product_data.name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract product from link: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in raw HTML extraction: {str(e)}")
        
        return products
    
    def _extract_product_from_current_structure(self, link, product_url: str, soup: BeautifulSoup) -> Optional[ProductData]:
        """
        Extract product data from current ProductHunt structure.
        
        Args:
            link: BeautifulSoup link element
            product_url: Full URL to the product
            soup: Full page soup for context
            
        Returns:
            ProductData object or None
        """
        try:
            # Extract product name from link text
            product_name = link.get_text(strip=True)
            
            # If the link text is just a number (like "1. Trickle - Magic Canvas"), clean it
            if product_name:
                # Remove numbering like "1. ", "2. ", etc.
                product_name = re.sub(r'^\d+\.\s*', '', product_name)
                product_name = product_name.strip()
            
            # If we still don't have a good name, try to find it in the aria-label
            if not product_name or len(product_name) < 2:
                aria_label = link.get('aria-label', '')
                if aria_label:
                    product_name = aria_label.strip()
            
            # Look for description in nearby elements
            description = ""
            
            # Try to find the description link that follows the name link
            # Based on the HTML structure, description links have class "text-16 font-normal text-dark-gray text-secondary"
            parent_container = link.parent
            if parent_container:
                # Go up to find the container that holds both name and description
                for _ in range(5):  # Search up to 5 levels
                    if parent_container:
                        desc_link = parent_container.find('a', class_=re.compile(r'.*text-16.*font-normal.*text-dark-gray.*text-secondary.*', re.I))
                        if desc_link and desc_link != link:
                            description = desc_link.get_text(strip=True)
                            break
                        parent_container = parent_container.parent
                    else:
                        break
            
            # Try alternative description extraction if not found
            if not description:
                # Look for any text that might be a description near this link
                if link.parent and link.parent.parent:
                    container = link.parent.parent
                    # Look for any text elements that might be descriptions
                    text_elements = container.find_all(['p', 'div', 'span'], string=True)
                    for elem in text_elements:
                        text = elem.get_text(strip=True)
                        # Skip if it's the product name or too short
                        if text and text != product_name and len(text) > 20 and not text.isdigit():
                            description = text
                            break
            
            # Extract website URL if available (will be done later in the pipeline)
            website_url = ""
            
            # Clean up product name
            if product_name:
                # Remove common artifacts
                product_name = re.sub(r'\s+', ' ', product_name)  # Normalize whitespace
                product_name = product_name.strip()
                
                if len(product_name) >= 2:  # Minimum reasonable length
                    return ProductData(
                        name=product_name,
                        company_name=product_name,  # Default to same as product name
                        website_url=website_url,
                        product_url=product_url,
                        description=description,
                        launch_date=datetime.now()
                    )
                    
        except Exception as e:
            logger.warning(f"Failed to extract product data from current structure: {str(e)}")
        
        return None
    
    def _extract_products_alternative_raw(self, soup: BeautifulSoup, limit: int) -> List[ProductData]:
        """
        Alternative method to extract products from raw HTML when primary method fails.
        
        Args:
            soup: BeautifulSoup object of the ProductHunt homepage
            limit: Maximum number of products to extract
            
        Returns:
            List of ProductData objects
        """
        products = []
        
        try:
            logger.info("Using alternative raw HTML extraction")
            
            # Look for any text that might contain product URLs
            page_text = soup.get_text()
            
            # Use regex to find ProductHunt product URLs in the text (updated pattern)
            url_pattern = r'https?://(?:www\.)?producthunt\.com/products/([a-zA-Z0-9-]+)'
            matches = re.findall(url_pattern, page_text)
            
            # Also try to find /products/ paths directly
            path_pattern = r'/products/([a-zA-Z0-9-]+)'
            path_matches = re.findall(path_pattern, page_text)
            matches.extend(path_matches)
            
            logger.info(f"Found {len(matches)} product URLs in page text")
            
            # Create products from found URLs
            seen_slugs = set()
            for match in matches[:limit]:
                if match in seen_slugs:
                    continue
                seen_slugs.add(match)
                
                product_url = f"https://www.producthunt.com/products/{match}"
                product_name = match.replace('-', ' ').title()
                
                product = ProductData(
                    name=product_name,
                    company_name=product_name,
                    website_url="",
                    product_url=product_url,
                    description="",
                    launch_date=datetime.now()
                )
                products.append(product)
                logger.debug(f"Alternative extraction found: {product_name}")
                
        except Exception as e:
            logger.error(f"Error in alternative raw HTML extraction: {str(e)}")
        
        return products
    
    def _try_api_approach(self, limit: int) -> List[ProductData]:
        """
        Try to use ProductHunt's API or API-like endpoints.
        
        Args:
            limit: Maximum number of products to retrieve
            
        Returns:
            List of ProductData objects
        """
        products = []
        
        try:
            logger.info("Attempting API approach for ProductHunt")
            
            # Try the GraphQL endpoint that ProductHunt might use
            api_url = "https://www.producthunt.com/frontend/graphql"
            
            # Simple query to get posts (this might need adjustment based on actual API)
            query = {
                "query": """
                query GetPosts($first: Int) {
                    posts(first: $first, order: VOTES) {
                        edges {
                            node {
                                id
                                name
                                tagline
                                url
                                website
                                createdAt
                            }
                        }
                    }
                }
                """,
                "variables": {"first": limit}
            }
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = self.session.post(api_url, json=query, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'posts' in data['data']:
                    posts = data['data']['posts']['edges']
                    
                    for post in posts[:limit]:
                        node = post['node']
                        product = ProductData(
                            name=node.get('name', ''),
                            company_name=node.get('name', ''),
                            website_url=node.get('website', ''),
                            product_url=f"https://www.producthunt.com/products/{node.get('id', '')}",
                            description=node.get('tagline', ''),
                            launch_date=self._parse_date(node.get('createdAt', ''))
                        )
                        products.append(product)
                        
                    logger.info(f"API approach successful, found {len(products)} products")
                    
        except Exception as e:
            logger.warning(f"API approach failed: {str(e)}")
        
        return products
    
    def _get_products_with_selenium(self, limit: int) -> List[ProductData]:
        """
        Fallback method using Selenium when HTTP requests fail.
        
        Args:
            limit: Maximum number of products to retrieve
            
        Returns:
            List of ProductData objects
        """
        logger.info("Using Selenium fallback approach")
        
        try:
            with self.webdriver_manager.get_driver("product_hunt_scraper") as driver:
                driver.get("https://www.producthunt.com/")
                
                # Wait for products to load
                wait = WebDriverWait(driver, 15)
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/products/']")))
                except TimeoutException:
                    logger.warning("Selenium: Could not find expected elements, proceeding with current page state")
                
                # Get page source and parse with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Use the raw HTML extraction method
                products = self._extract_products_from_raw_html(soup, limit)
                
                if not products:
                    products = self._extract_products_alternative_raw(soup, limit)
                
                return products
            
        except Exception as e:
            logger.error(f"Selenium fallback also failed: {str(e)}")
            return []
    
    def _extract_team_from_linkedin_links(self, soup: BeautifulSoup, company_name: str) -> List[TeamMember]:
        """
        Extract team members from LinkedIn links found on the page.
        
        Args:
            soup: BeautifulSoup object of the page
            company_name: Name of the company
            
        Returns:
            List of TeamMember objects
        """
        team_members = []
        
        try:
            # Find all LinkedIn links on the page
            linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com/in/', re.I))
            
            logger.debug(f"Found {len(linkedin_links)} LinkedIn links for team extraction")
            
            for link in linkedin_links:
                try:
                    linkedin_url = link.get('href', '')
                    
                    # Try to extract name from link text or nearby elements
                    name = link.get_text(strip=True)
                    
                    # Skip if the link text is just "LinkedIn" or similar generic text
                    if name.lower() in ['linkedin', 'profile', 'connect', 'follow']:
                        name = ""
                    
                    if not name:
                        # Look for name in parent or sibling elements
                        parent = link.parent
                        if parent:
                            # Try to find name in nearby text
                            name_candidates = parent.find_all(['span', 'div', 'p'], string=True)
                            for candidate in name_candidates:
                                text = candidate.get_text(strip=True)
                                # Simple heuristic: if it looks like a name (2-3 words, capitalized)
                                if text and len(text.split()) in [2, 3] and text.replace(' ', '').isalpha():
                                    name = text
                                    break
                    
                    # Try to extract role from nearby elements
                    role = ""
                    if link.parent:
                        role_candidates = link.parent.find_all(['span', 'div', 'p'], 
                                                             class_=re.compile(r'.*role.*|.*title.*|.*position.*', re.I))
                        if role_candidates:
                            role = role_candidates[0].get_text(strip=True)
                    
                    # Provide default role if none found
                    if not role:
                        role = "Team Member"
                    
                    if name and linkedin_url:
                        team_member = TeamMember(
                            name=name,
                            role=role,
                            linkedin_url=linkedin_url,
                            company=company_name
                        )
                        team_members.append(team_member)
                        logger.debug(f"Extracted team member from LinkedIn link: {name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract team member from LinkedIn link: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting team from LinkedIn links: {str(e)}")
        
        return team_members
    
    def _extract_team_content_for_ai(self, soup: BeautifulSoup) -> str:
        """
        Extract relevant team content from the page for AI parsing.
        
        Args:
            soup: BeautifulSoup object of the product page
            
        Returns:
            String containing team-related content for AI parsing
        """
        try:
            team_content_parts = []
            
            # Strategy 1: Look for team/maker sections by class
            team_sections = soup.find_all(['div', 'section'], class_=re.compile(r'.*team.*|.*maker.*|.*creator.*', re.I))
            
            for section in team_sections:
                content = section.get_text(separator=' ', strip=True)
                if content and len(content) > 10:  # Only include substantial content
                    team_content_parts.append(content)
            
            # Strategy 1b: Look for any content that mentions team-related keywords
            if not team_content_parts:
                # Get all text content and look for team-related sections
                all_text = soup.get_text(separator='\n', strip=True)
                lines = all_text.split('\n')
                
                team_section_found = False
                current_section = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this line indicates start of team section
                    if re.search(r'\b(team|maker|creator|founder|co-founder|built by|made by)\b', line, re.I):
                        team_section_found = True
                        current_section = [line]
                    elif team_section_found:
                        # Continue collecting lines until we hit a clear section break
                        if len(line) > 100 or re.search(r'\b(feature|pricing|about|contact|privacy)\b', line, re.I):
                            # Likely moved to a different section
                            break
                        current_section.append(line)
                        
                        # Stop if we have enough content
                        if len(current_section) > 10:
                            break
                
                if current_section:
                    team_content_parts.append(' '.join(current_section))
            
            # Strategy 2: Look for sections with team-related text
            text_elements = soup.find_all(string=re.compile(r'team|maker|creator|founder|co-founder', re.I))
            for text_elem in text_elements:
                if text_elem.parent:
                    # Get the parent container that might contain team info
                    parent = text_elem.parent
                    while parent and parent.name not in ['div', 'section', 'article']:
                        parent = parent.parent
                    if parent:
                        content = parent.get_text(separator=' ', strip=True)
                        if content and len(content) > 20 and content not in team_content_parts:
                            team_content_parts.append(content)
            
            # Strategy 3: Extract content around LinkedIn links
            linkedin_links = soup.find_all('a', href=re.compile(r'linkedin\.com', re.I))
            for link in linkedin_links:
                if link.parent:
                    parent_content = link.parent.get_text(separator=' ', strip=True)
                    if parent_content and len(parent_content) > 10 and parent_content not in team_content_parts:
                        team_content_parts.append(parent_content)
            
            # Combine all team content
            combined_content = '\n\n'.join(team_content_parts)
            
            # Limit content length to avoid token limits
            if len(combined_content) > 4000:
                combined_content = combined_content[:4000] + "..."
            
            logger.debug(f"Extracted {len(combined_content)} characters of team content for AI parsing")
            return combined_content
            
        except Exception as e:
            logger.error(f"Error extracting team content for AI: {e}")
            return ""
    
    def _merge_team_data(self, ai_members: List[TeamMember], traditional_members: List[TeamMember]) -> List[TeamMember]:
        """
        Merge AI-parsed team data with traditional extraction data.
        
        Args:
            ai_members: Team members from AI parsing
            traditional_members: Team members from traditional parsing
            
        Returns:
            Merged list of TeamMember objects
        """
        try:
            merged_members = list(ai_members)  # Start with AI members
            
            # Add traditional members that aren't already in AI results
            for trad_member in traditional_members:
                # Check if this member is already in AI results (by name similarity)
                is_duplicate = False
                for ai_member in ai_members:
                    if (self._names_similar(ai_member.name, trad_member.name) or
                        (ai_member.linkedin_url and trad_member.linkedin_url and 
                         ai_member.linkedin_url == trad_member.linkedin_url)):
                        is_duplicate = True
                        # Enhance AI member with traditional data if missing
                        if not ai_member.linkedin_url and trad_member.linkedin_url:
                            ai_member.linkedin_url = trad_member.linkedin_url
                        break
                
                if not is_duplicate:
                    merged_members.append(trad_member)
            
            logger.info(f"Merged team data: {len(ai_members)} AI + {len(traditional_members)} traditional = {len(merged_members)} total")
            return merged_members
            
        except Exception as e:
            logger.error(f"Error merging team data: {e}")
            return ai_members  # Return AI members as fallback
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """
        Check if two names are similar (simple similarity check).
        
        Args:
            name1: First name to compare
            name2: Second name to compare
            
        Returns:
            True if names are similar, False otherwise
        """
        if not name1 or not name2:
            return False
        
        # Simple similarity check - normalize and compare
        name1_norm = name1.lower().strip()
        name2_norm = name2.lower().strip()
        
        # Exact match
        if name1_norm == name2_norm:
            return True
        
        # Check if one name contains the other (for cases like "John" vs "John Doe")
        if name1_norm in name2_norm or name2_norm in name1_norm:
            return True
        
        # Check if names share significant common words
        words1 = set(name1_norm.split())
        words2 = set(name2_norm.split())
        
        if len(words1) > 0 and len(words2) > 0:
            common_words = words1.intersection(words2)
            # If at least one significant word is common, consider similar
            # But require at least 50% overlap for multi-word names
            if len(common_words) > 0:
                similarity_ratio = len(common_words) / min(len(words1), len(words2))
                # For single word names, any common word is enough
                if min(len(words1), len(words2)) == 1:
                    return True
                # For multi-word names, require at least 50% overlap
                return similarity_ratio >= 0.5
        
        return False