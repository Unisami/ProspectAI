#!/usr/bin/env python3
"""
Clean test script for Hunter.io rate limiting.
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
from utils.error_handling import get_error_handler

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)


def test_clean_request():
    """Test a single request with clean error tracking."""
    logger.info("Testing clean Hunter.io request...")
    
    # Get configuration
    config_service = get_configuration_service()
    config = config_service.get_config()
    
    # Initialize email finder
    email_finder = EmailFinder(config)
    
    # Test with a simple valid domain that should not have emails
    test_domain = "nonexistentdomain12345.com"
    
    logger.info(f"Testing with rate limit of {config.hunter_requests_per_minute} requests per minute")
    
    try:
        logger.info(f"Searching domain: {test_domain}")
        start_time = time.time()
        emails = email_finder.find_company_emails(test_domain)
        end_time = time.time()
        logger.info(f"Found {len(emails)} emails for {test_domain} in {end_time - start_time:.2f}s")
        return True
    except Exception as e:
        logger.error(f"Error searching domain {test_domain}: {e}")
        return False


if __name__ == "__main__":
    # Clear error tracking
    error_handler = get_error_handler()
    error_handler.errors.clear()
    error_handler.error_counts.clear()
    
    success = test_clean_request()
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!")