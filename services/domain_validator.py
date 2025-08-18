"""
Domain validation utilities for email finding.
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse


logger = logging.getLogger(__name__)

# List of invalid or problematic domains (only obvious test/placeholder domains)
INVALID_DOMAINS = {
    'example.com',
    'test.com',
    'localhost',
    'domain.com',
    'yourcompany.com',
    'company.com',
    'website.com',
    'placeholder.com',
    'sample.com',
}

# List of common TLDs (top-level domains)
VALID_TLDS = {
    'com', 'org', 'net', 'io', 'co', 'ai', 'app', 
    'dev', 'tech', 'info', 'biz', 'us', 'uk', 'ca',
    'au', 'de', 'fr', 'jp', 'cn', 'in', 'ru', 'br',
    'es', 'it', 'nl', 'se', 'no', 'dk', 'fi', 'ch',
    'at', 'be', 'pl', 'cz', 'hu', 'ro', 'gr', 'pt',
    'ie', 'nz', 'sg', 'hk', 'kr', 'tw', 'vn', 'th',
    'id', 'my', 'ph', 'mx', 'ar', 'cl', 'co', 'pe',
    'za', 'ng', 'ke', 'eg', 'sa', 'ae', 'il', 'tr',
    'so', 'me', 'xyz', 'gg', 'fm', 'tv', 'to', 'sh',
    'art'
}

def is_valid_domain(domain: str) -> bool:
    """
    Check if a domain is valid for email finding.
    
    Args:
        domain: Domain to validate
        
    Returns:
        True if domain is valid, False otherwise
    """
    if not domain:
        return False
    
    # Check if domain is in the invalid list (only obvious invalid ones)
    if domain.lower() in INVALID_DOMAINS:
        logger.warning(f"Domain {domain} is in the invalid domains list")
        return False
    
    # Very permissive domain format - accept almost anything that looks like a domain
    # Allow: domain.com, sub.domain.com, domain.app.link, meet-ting.com, etc.
    domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{1,61}[a-zA-Z0-9])?$'
    if not re.match(domain_pattern, domain):
        logger.warning(f"Domain {domain} has invalid format")
        return False
    
    # Must contain at least one dot
    if '.' not in domain:
        logger.warning(f"Domain {domain} must contain at least one dot")
        return False
    
    # Check minimum length (very permissive)
    if len(domain) < 3:  # Allow very short domains like x.ai
        logger.warning(f"Domain {domain} is too short")
        return False
    
    # Must end with a valid TLD (at least 2 characters)
    tld = domain.split('.')[-1].lower()
    if len(tld) < 2 or not tld.isalpha():
        logger.warning(f"Domain {domain} has invalid TLD: {tld}")
        return False
    
    logger.info(f"Domain {domain} is valid")
    return True

def extract_valid_domain(company_name: str, website_url: Optional[str] = None) -> str:
    """
    Extract a valid domain from company name or website URL.
    
    Args:
        company_name: Company name
        website_url: Optional website URL
        
    Returns:
        Valid domain or empty string if no valid domain could be extracted
    """
    domain = ""
    
    # Try to extract from website URL first
    if website_url:
        try:
            parsed = urlparse(website_url)
            if parsed.netloc:
                domain = parsed.netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                if is_valid_domain(domain):
                    return domain
        except Exception as e:
            logger.warning(f"Failed to extract domain from URL {website_url}: {e}")
    
    # Try to create domain from company name
    if company_name:
        # Remove common suffixes
        name = company_name.lower()
        for suffix in [' inc', ' llc', ' ltd', ' limited', ' corp', ' corporation', ' co']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        
        # Remove special characters and spaces
        name = re.sub(r'[^a-z0-9]', '', name)
        
        # Try to create a realistic domain from the company name
        # This is a fallback when we can't extract a domain from the website
        name_clean = re.sub(r'[^a-z0-9]', '', name.lower())
        
        # Check if the company name contains a domain-like string
        domain_pattern = r'([a-z0-9-]+\.[a-z]{2,})'
        domain_match = re.search(domain_pattern, company_name.lower())
        if domain_match:
            potential_domain = domain_match.group(1)
            if is_valid_domain(potential_domain):
                logger.info(f"Found domain-like string in company name: {potential_domain}")
                return potential_domain
        
        # For now, skip email finding entirely since we don't have reliable domain information
        # This avoids wasting API calls on domains that don't exist
        logger.warning(f"Skipping email finding for {company_name} - no valid domain available")
        return ""
    
    return ""
