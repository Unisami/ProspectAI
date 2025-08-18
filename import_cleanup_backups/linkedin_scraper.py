"""
LinkedIn profile scraper using Selenium for extracting profile information.
"""

import time
import logging
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup

from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.logging_config import get_logger
from utils.error_handling import get_error_handler, ErrorCategory, retry_with_backoff
from utils.api_monitor import get_api_monitor
from utils.webdriver_manager import get_webdriver_manager
from services.ai_parser import AIParser, ParseResult


@dataclass
class LinkedInProfile:
    """Data model for LinkedIn profile information."""
    name: str
    current_role: str
    experience: List[str]
    skills: List[str]
    summary: str
    company: Optional[str] = None
    location: Optional[str] = None
    education: List[str] = None
    
    def __post_init__(self):
        if self.education is None:
            self.education = []


class LinkedInScraper:
    """
    LinkedIn profile scraper using Selenium with proper rate limiting and error handling.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize LinkedIn scraper.
        
        Args:
            config: Configuration object (deprecated, use ConfigurationService)
        """
        # Use ConfigurationService for centralized configuration management
        if config:
            # Backward compatibility: if config is provided, use it directly
            logging.warning("Direct config parameter is deprecated. Consider using ConfigurationService.")
            self.config = config
        else:
            # Use centralized configuration service
            config_service = get_configuration_service()
            self.config = config_service.get_config()
        self.logger = get_logger(__name__)
        self.error_handler = get_error_handler()
        self.api_monitor = get_api_monitor()
        self.last_request_time = 0
        self.min_delay = getattr(config, 'linkedin_scraping_delay', 3.0)  # 3 second delay between requests
        
        # Initialize WebDriver manager
        self.webdriver_manager = get_webdriver_manager(config)
        
        # Initialize AI parser for enhanced data extraction
        try:
            self.ai_parser = AIParser(config)
            self.use_ai_parsing = True
            self.logger.info("AI parsing enabled for LinkedIn scraper")
        except Exception as e:
            self.logger.warning(f"Failed to initialize AI parser: {e}. Falling back to traditional parsing.")
            self.ai_parser = None
            self.use_ai_parsing = False
    

    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            self.logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _is_valid_linkedin_url(self, url: str) -> bool:
        """Validate if the URL is a LinkedIn profile URL."""
        try:
            parsed = urlparse(url)
            return (
                parsed.netloc.lower() in ['linkedin.com', 'www.linkedin.com'] and
                '/in/' in parsed.path.lower()
            )
        except Exception:
            return False
    
    def _extract_text_safely(self, driver: webdriver.Chrome, selector: str, multiple: bool = False) -> Any:
        """Safely extract text from elements using CSS selector."""
        try:
            if multiple:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                return [elem.text.strip() for elem in elements if elem.text.strip()]
            else:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                return element.text.strip() if element else ""
        except (NoSuchElementException, TimeoutException):
            return [] if multiple else ""
    
    @retry_with_backoff(category=ErrorCategory.SCRAPING)
    def extract_profile_data(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """
        Extract profile data from a LinkedIn URL.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            LinkedInProfile object or None if extraction fails
        """
        if not self._is_valid_linkedin_url(linkedin_url):
            self.logger.warning(f"Invalid LinkedIn URL: {linkedin_url}")
            return None
        
        self._enforce_rate_limit()
        
        start_time = time.time()
        self.logger.info(f"Extracting LinkedIn profile data from: {linkedin_url}")
        
        try:
            with self.webdriver_manager.get_driver("linkedin_scraper") as driver:
                try:
                    driver.get(linkedin_url)
                except Exception as e:
                    self.logger.warning(f"Page load timeout for {linkedin_url}: {str(e)}")
                    return None
                
                # Wait for page to load (reduced timeout)
                try:
                    WebDriverWait(driver, 5).until(  # Reduced from 10 to 5 seconds
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except TimeoutException:
                    self.logger.warning(f"Page body load timeout for {linkedin_url}")
                    return None
                
                # PERFORMANCE OPTIMIZATION: Reduced scrolling and wait times
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(1)  # Reduced from 2 to 1 second
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)  # Reduced from 2 to 1 second
                
                # Get page HTML for AI parsing
                page_html = driver.page_source
                
                # Try AI parsing first if available
                profile = None
                if self.use_ai_parsing and self.ai_parser:
                    try:
                        self.logger.info("Attempting AI parsing of LinkedIn profile")
                        
                        # Prepare fallback data using traditional extraction
                        fallback_data = self._extract_traditional_profile_data(driver)
                        
                        # Use AI parser with fallback
                        ai_result = self.ai_parser.parse_linkedin_profile(page_html, fallback_data)
                        
                        if ai_result.success and ai_result.data:
                            # Convert AI parser LinkedInProfile to our LinkedInProfile format
                            ai_profile = ai_result.data
                            
                            # Extract company and clean current role
                            company = self._extract_company_from_role(ai_profile.current_role)
                            current_role = ai_profile.current_role
                            if company and " at " in current_role:
                                current_role = current_role.split(" at ", 1)[0].strip()
                            
                            profile = LinkedInProfile(
                                name=ai_profile.name,
                                current_role=current_role,
                                company=company,
                                location="",  # AI parser doesn't extract location yet
                                summary=ai_profile.summary,
                                experience=ai_profile.experience,
                                skills=ai_profile.skills,
                                education=[]  # AI parser doesn't extract education yet
                            )
                            
                            self.logger.info(f"AI parsing successful with confidence: {ai_result.confidence_score:.2f}")
                            
                            # If AI parsing confidence is low, enhance with traditional data
                            if ai_result.confidence_score < 0.7:
                                profile = self._enhance_profile_with_traditional_data(profile, driver)
                        else:
                            self.logger.warning(f"AI parsing failed: {ai_result.error_message}")
                            
                    except Exception as e:
                        self.logger.warning(f"AI parsing error: {e}. Falling back to traditional parsing.")
                
                # Fall back to traditional parsing if AI parsing failed or is disabled
                if not profile:
                    self.logger.info("Using traditional LinkedIn profile extraction")
                    fallback_data = self._extract_traditional_profile_data(driver)
                    
                    if not fallback_data.get('name'):
                        self.logger.warning("Could not extract name from LinkedIn profile")
                        return None
                    
                    profile = LinkedInProfile(
                        name=fallback_data['name'],
                        current_role=fallback_data['current_role'] or "Not specified",
                        company=fallback_data['company'],
                        location=fallback_data['location'],
                        summary=fallback_data['summary'],
                        experience=fallback_data['experience'],
                        skills=fallback_data['skills'],
                        education=fallback_data['education']
                    )
                
                if not profile or not profile.name:
                    self.logger.warning("Could not extract profile data")
                    return None
                
                # Record successful scraping operation
                response_time = time.time() - start_time
                self.api_monitor.record_api_call(
                    service='linkedin',
                    endpoint='profile_extraction',
                    response_time=response_time,
                    status_code=200,
                    success=True
                )
                
                self.logger.info(f"Successfully extracted profile for: {profile.name}")
                return profile
                        
        except WebDriverException as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='linkedin',
                endpoint='profile_extraction',
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
            
            self.error_handler.handle_error(
                e, 'linkedin', 'extract_profile_data',
                context={'url': linkedin_url}, category=ErrorCategory.SCRAPING
            )
            return None
        except Exception as e:
            response_time = time.time() - start_time
            self.api_monitor.record_api_call(
                service='linkedin',
                endpoint='profile_extraction',
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )
            
            self.error_handler.handle_error(
                e, 'linkedin', 'extract_profile_data',
                context={'url': linkedin_url}, category=ErrorCategory.SCRAPING
            )
            return None
    
    def get_experience_summary(self, profile: LinkedInProfile) -> str:
        """
        Generate a summary of the person's experience.
        
        Args:
            profile: LinkedInProfile object
            
        Returns:
            String summary of experience
        """
        if not profile.experience:
            return f"Currently {profile.current_role}" + (f" at {profile.company}" if profile.company else "")
        
        experience_text = f"Currently {profile.current_role}"
        if profile.company:
            experience_text += f" at {profile.company}"
        
        if len(profile.experience) > 0:
            experience_text += f". Previous experience includes: {', '.join(profile.experience[:3])}"
            if len(profile.experience) > 3:
                experience_text += f" and {len(profile.experience) - 3} more roles"
        
        return experience_text
    
    def get_skills(self, profile: LinkedInProfile) -> List[str]:
        """
        Get the list of skills from the profile.
        
        Args:
            profile: LinkedInProfile object
            
        Returns:
            List of skills
        """
        return profile.skills[:10]  # Return top 10 skills
    
    def extract_multiple_profiles(self, linkedin_urls: List[str]) -> Dict[str, Optional[LinkedInProfile]]:
        """
        Extract data from multiple LinkedIn profiles with proper rate limiting.
        
        Args:
            linkedin_urls: List of LinkedIn profile URLs
            
        Returns:
            Dictionary mapping URLs to LinkedInProfile objects
        """
        results = {}
        
        for url in linkedin_urls:
            try:
                profile = self.extract_profile_data(url)
                results[url] = profile
                
                if profile:
                    self.logger.info(f"Successfully extracted profile for: {profile.name}")
                else:
                    self.logger.warning(f"Failed to extract profile from: {url}")
                    
            except Exception as e:
                self.logger.error(f"Error processing LinkedIn URL {url}: {e}")
                results[url] = None
        
        return results
    
    def _extract_traditional_profile_data(self, driver: webdriver.Chrome) -> Dict[str, Any]:
        """
        Extract profile data using traditional scraping methods.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            Dictionary containing extracted profile data
        """
        try:
            # Extract profile information using various selectors
            name = self._extract_text_safely(driver, "h1.text-heading-xlarge, .pv-text-details__left-panel h1")
            
            # Try multiple selectors for current role
            current_role = (
                self._extract_text_safely(driver, ".text-body-medium.break-words") or
                self._extract_text_safely(driver, ".pv-text-details__left-panel .text-body-medium") or
                self._extract_text_safely(driver, "[data-generated-suggestion-target]")
            )
            
            # Extract location
            location = self._extract_text_safely(driver, ".text-body-small.inline.t-black--light.break-words")
            
            # Extract summary/about section
            summary = (
                self._extract_text_safely(driver, ".pv-shared-text-with-see-more .inline-show-more-text") or
                self._extract_text_safely(driver, ".pv-about-section .pv-about__summary-text") or
                ""
            )
            
            # Extract experience - this is more complex and may require scrolling
            experience_items = []
            try:
                # Look for experience section
                experience_elements = driver.find_elements(By.CSS_SELECTOR, 
                    ".pv-entity__summary-info h3, .pv-experience-section .pv-entity__summary-info h3")
                for elem in experience_elements[:5]:  # Limit to first 5 experiences
                    if elem.text.strip():
                        experience_items.append(elem.text.strip())
            except Exception as e:
                self.logger.debug(f"Could not extract experience: {e}")
            
            # Extract skills - LinkedIn often requires clicking to see all skills
            skills = []
            try:
                skill_elements = driver.find_elements(By.CSS_SELECTOR, 
                    ".pv-skill-category-entity__name span, .skill-category-entity__name")
                skills = [elem.text.strip() for elem in skill_elements[:10] if elem.text.strip()]
            except Exception as e:
                self.logger.debug(f"Could not extract skills: {e}")
            
            # Extract education
            education = []
            try:
                education_elements = driver.find_elements(By.CSS_SELECTOR, 
                    ".pv-education-entity h3, .pv-entity__school-name")
                education = [elem.text.strip() for elem in education_elements[:3] if elem.text.strip()]
            except Exception as e:
                self.logger.debug(f"Could not extract education: {e}")
            
            # Try to extract company from current role text
            company = self._extract_company_from_role(current_role)
            if company and " at " in current_role:
                current_role = current_role.split(" at ", 1)[0].strip()
            
            return {
                'name': name,
                'current_role': current_role,
                'company': company,
                'location': location,
                'summary': summary,
                'experience': experience_items,
                'skills': skills,
                'education': education
            }
            
        except Exception as e:
            self.logger.error(f"Error in traditional profile extraction: {e}")
            return {
                'name': '',
                'current_role': '',
                'company': None,
                'location': '',
                'summary': '',
                'experience': [],
                'skills': [],
                'education': []
            }
    
    def _extract_company_from_role(self, current_role: str) -> Optional[str]:
        """
        Extract company name from current role text.
        
        Args:
            current_role: Current role text that might contain company name
            
        Returns:
            Company name or None if not found
        """
        if not current_role:
            return None
            
        if " at " in current_role:
            parts = current_role.split(" at ", 1)
            if len(parts) == 2:
                return parts[1].strip()
        
        return None
    
    def _enhance_profile_with_traditional_data(self, ai_profile: LinkedInProfile, driver: webdriver.Chrome) -> LinkedInProfile:
        """
        Enhance AI-parsed profile with additional traditional extraction data.
        
        Args:
            ai_profile: Profile data from AI parsing
            driver: WebDriver instance for additional extraction
            
        Returns:
            Enhanced LinkedInProfile object
        """
        try:
            # Extract additional data that AI might have missed
            location = self._extract_text_safely(driver, ".text-body-small.inline.t-black--light.break-words")
            
            # Extract education if not present
            education = []
            if not ai_profile.education:
                try:
                    education_elements = driver.find_elements(By.CSS_SELECTOR, 
                        ".pv-education-entity h3, .pv-entity__school-name")
                    education = [elem.text.strip() for elem in education_elements[:3] if elem.text.strip()]
                except Exception as e:
                    self.logger.debug(f"Could not extract education: {e}")
            
            # Update profile with enhanced data
            ai_profile.location = location or ai_profile.location
            ai_profile.education = education if education else ai_profile.education
            
            # If company is not set, try to extract from current role
            if not ai_profile.company:
                ai_profile.company = self._extract_company_from_role(ai_profile.current_role)
            
            self.logger.info("Enhanced AI profile with traditional extraction data")
            return ai_profile
            
        except Exception as e:
            self.logger.warning(f"Error enhancing profile with traditional data: {e}")
            return ai_profile