#!/usr/bin/env python3
"""
Simple test script for Hunter.io rate limiting.
"""

import sys
import os
import time
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_finder import EmailFinder
from utils.configuration_service import get_configuration_service
from utils.logging_config import setup_logging

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


def test_single_request():
    """Test a single request to see if rate limiting works."""
    logger.info("Testing single Hunter.io request...")
    
    # Get configuration
    config_service = get_configuration_service()
    config = config_service.get_config()
    
    # Initialize email finder
    email_finder = EmailFinder(config)
    
    # Test with a simple valid domain that should not have emails
    test_domain = "example.com"
    
    logger.info(f"Testing with rate limit of {config.hunter_requests_per_minute} requests per minute")
    
    try:
        logger.info(f"Searching domain: {test_domain}")
        start_time = time.time()
        emails = email_finder.find_company_emails(test_domain)
        end_time = time.time()
        logger.info(f"Found {len(emails)} emails for {test_domain} in {end_time - start_time:.2f}s")
    except Exception as e:
        logger.error(f"Error searching domain {test_domain}: {e}")
        return False
    
    return True


if __name__ == "__main__":
    test_single_request()