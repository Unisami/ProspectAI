"""
Website URL extraction from ProductHunt pages.
"""

import logging
import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)

class WebsiteExtractor:
    """Extract website URLs from ProductHunt product pages."""
    
    def __init__(self):
        """Initialize the website extractor."""
        # Set up Chrome options for Selenium
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
    
    def extract_website_url(self, product_url: str) -> str:
        """
        Extract the website URL from a ProductHunt product page.
        
        Args:
            product_url: URL of the ProductHunt product page
            
        Returns:
            Website URL or empty string if not found
        """
        try:
            logger.info(f"Extracting website URL from {product_url}")
            
            # Try with Selenium first for JavaScript-rendered content
            website_url = self._extract_with_selenium(product_url)
            if website_url:
                logger.info(f"Found website URL with Selenium: {website_url}")
                return website_url
            
            # Fall back to requests
            website_url = self._extract_with_requests(product_url)
            if website_url:
                logger.info(f"Found website URL with requests: {website_url}")
                return website_url
            
            logger.warning(f"Could not find website URL for {product_url}")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting website URL: {e}")
            return ""
    
    def _extract_with_selenium(self, product_url: str) -> str:
        """Extract website URL using Selenium."""
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.set_page_load_timeout(30)
            driver.get(product_url)
            
            # Wait for page to load
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            
            # Look for website link - ProductHunt usually has a "Visit Website" button
            website_elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'Visit') or contains(text(), 'Website')]")
            
            for element in website_elements:
                href = element.get_attribute("href")
                if href and "producthunt.com" not in href:
                    return href
            
            # Look for any external links
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href")
                if href and href.startswith("http") and "producthunt.com" not in href:
                    # Check if it looks like a company website
                    if self._is_likely_company_website(href):
                        return href
            
            return ""
            
        except Exception as e:
            logger.warning(f"Selenium extraction failed: {e}")
            return ""
        finally:
            if driver:
                driver.quit()
    
    def _extract_with_requests(self, product_url: str) -> str:
        """Extract website URL using requests."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            response = requests.get(product_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for website link - ProductHunt usually has a "Visit Website" button
            website_links = soup.find_all('a', string=re.compile(r'Visit|Website', re.I))
            
            for link in website_links:
                href = link.get('href')
                if href and "producthunt.com" not in href:
                    return href
            
            # Look for any external links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href')
                if href and href.startswith("http") and "producthunt.com" not in href:
                    # Check if it looks like a company website
                    if self._is_likely_company_website(href):
                        return href
            
            return ""
            
        except Exception as e:
            logger.warning(f"Requests extraction failed: {e}")
            return ""
    
    def _is_likely_company_website(self, url: str) -> bool:
        """Check if a URL is likely to be a company website."""
        # Exclude common non-company websites
        excluded_domains = [
            'twitter.com', 'facebook.com', 'linkedin.com', 'instagram.com',
            'github.com', 'youtube.com', 'medium.com', 'reddit.com',
            'google.com', 'apple.com', 'microsoft.com', 'amazon.com'
        ]
        
        for domain in excluded_domains:
            if domain in url:
                return False
        
        return True