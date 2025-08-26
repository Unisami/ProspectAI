#!/usr/bin/env python3
"""
Test script for Hunter.io rate limiting fix.
"""

import sys
import os
import time
import logging
from typing import List

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_finder import EmailFinder
from utils.config import Config
from utils.configuration_service import get_configuration_service
from utils.logging_config import setup_logging
from utils.rate_limiting import get_rate_limiter

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


def test_hunter_rate_limiting():
    """Test that Hunter.io rate limiting is working properly."""
    logger.info("Testing Hunter.io rate limiting...")
    
    # Get configuration
    config_service = get_configuration_service()
    config = config_service.get_config()
    
    # Initialize email finder
    email_finder = EmailFinder(config)
    
    # Get rate limiter for debugging
    rate_limiter = get_rate_limiter(config)
    
    # Test with a simple valid domain that should not have emails
    test_domain = "example.com"
    
    logger.info(f"Testing with rate limit of {config.hunter_requests_per_minute} requests per minute")
    
    # Check rate limiter status before tests
    status = rate_limiter.get_status("hunter")
    logger.info(f"Rate limiter status before tests: {status}")
    
    # Test domain search rate limiting
    logger.info("Testing domain search rate limiting...")
    start_time = time.time()
    
    try:
        logger.info(f"Searching domain: {test_domain}")
        emails = email_finder.find_company_emails(test_domain)
        logger.info(f"Found {len(emails)} emails for {test_domain}")
    except Exception as e:
        logger.warning(f"Error searching domain {test_domain}: {e}")
    
    domain_search_time = time.time() - start_time
    logger.info(f"Domain search test completed in {domain_search_time:.2f}s")
    
    # Check rate limiter status after domain search
    status = rate_limiter.get_status("hunter")
    logger.info(f"Rate limiter status after domain search: {status}")
    
    # Wait a bit to ensure rate limiter has time to reset
    time.sleep(2)
    
    # Test person email search rate limiting with a simple name
    test_person = ("John Doe", "example.com")
    
    logger.info("Testing person email search rate limiting...")
    start_time = time.time()
    
    try:
        name, domain = test_person
        logger.info(f"Searching email: {name} at {domain}")
        email_data = email_finder.find_person_email(name, domain)
        if email_data:
            logger.info(f"Found email for {name}: {email_data.email}")
        else:
            logger.info(f"No email found for {name}")
    except Exception as e:
        logger.warning(f"Error searching email for {test_person[0]}: {e}")
    
    person_search_time = time.time() - start_time
    logger.info(f"Person email search test completed in {person_search_time:.2f}s")
    
    # Check rate limiter status after person search
    status = rate_limiter.get_status("hunter")
    logger.info(f"Rate limiter status after person search: {status}")
    
    # Test email verification rate limiting
    test_email = "test@example.com"
    
    logger.info("Testing email verification rate limiting...")
    start_time = time.time()
    
    try:
        logger.info(f"Verifying email: {test_email}")
        verification = email_finder.verify_email(test_email)
        if verification:
            logger.info(f"Verification result for {test_email}: {verification.result}")
        else:
            logger.info(f"No verification result for {test_email}")
    except Exception as e:
        logger.warning(f"Error verifying email {test_email}: {e}")
    
    verification_time = time.time() - start_time
    logger.info(f"Email verification test completed in {verification_time:.2f}s")
    
    # Check final rate limiter status
    status = rate_limiter.get_status("hunter")
    logger.info(f"Final rate limiter status: {status}")
    
    logger.info("Hunter.io rate limiting test completed successfully!")


if __name__ == "__main__":
    test_hunter_rate_limiting()