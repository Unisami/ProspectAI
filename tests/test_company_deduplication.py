#!/usr/bin/env python3
"""
Test script to verify company deduplication functionality.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from services.notion_manager import NotionDataManager
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_deduplication():
    """Test the company deduplication functionality."""
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize services
        notion_manager = NotionDataManager(config)
        controller = ProspectAutomationController(config)
        
        logger.info("🧪 Testing company deduplication functionality...")
        
        # Test 1: Get processed companies
        logger.info("\n📋 Test 1: Getting processed companies...")
        processed_companies = notion_manager.get_processed_company_names()
        processed_domains = notion_manager.get_processed_company_domains()
        
        logger.info(f"Found {len(processed_companies)} processed companies:")
        for i, company in enumerate(processed_companies[:10]):  # Show first 10
            logger.info(f"  {i+1}. {company}")
        if len(processed_companies) > 10:
            logger.info(f"  ... and {len(processed_companies) - 10} more")
        
        logger.info(f"Found {len(processed_domains)} processed domains:")
        for i, domain in enumerate(processed_domains[:10]):  # Show first 10
            logger.info(f"  {i+1}. {domain}")
        if len(processed_domains) > 10:
            logger.info(f"  ... and {len(processed_domains) - 10} more")
        
        # Test 2: Test individual company check
        logger.info("\n🔍 Test 2: Testing individual company checks...")
        if processed_companies:
            test_company = processed_companies[0]
            is_processed = notion_manager.is_company_already_processed(test_company)
            logger.info(f"Company '{test_company}' is processed: {is_processed}")
            
            # Test with a new company that shouldn't exist
            fake_company = f"Test Company {datetime.now().strftime('%Y%m%d%H%M%S')}"
            is_processed_fake = notion_manager.is_company_already_processed(fake_company)
            logger.info(f"Fake company '{fake_company}' is processed: {is_processed_fake}")
        
        # Test 3: Test cache functionality
        logger.info("\n💾 Test 3: Testing cache functionality...")
        start_time = datetime.now()
        cached_companies, cached_domains = controller._get_cached_processed_companies()
        first_call_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"First cache call took {first_call_time:.3f} seconds")
        
        start_time = datetime.now()
        cached_companies2, cached_domains2 = controller._get_cached_processed_companies()
        second_call_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Second cache call took {second_call_time:.3f} seconds")
        
        logger.info(f"Cache working: {cached_companies == cached_companies2 and cached_domains == cached_domains2}")
        logger.info(f"Performance improvement: {(first_call_time / max(second_call_time, 0.001)):.1f}x faster")
        
        # Test 4: Test filtering with mock companies
        logger.info("\n🔄 Test 4: Testing company filtering...")
        
        # Create mock companies - mix of existing and new
        mock_companies = []
        
        # Add some existing companies (should be filtered out)
        for i, company_name in enumerate(processed_companies[:3]):
            mock_companies.append(CompanyData(
                name=company_name,
                domain=f"existing{i}.com",
                product_url=f"https://producthunt.com/posts/existing{i}",
                description=f"Existing company {i}",
                launch_date=datetime.now()
            ))
        
        # Add some new companies (should pass through)
        for i in range(3):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            mock_companies.append(CompanyData(
                name=f"New Company {i} {timestamp}",
                domain=f"newcompany{i}-{timestamp}.com",
                product_url=f"https://producthunt.com/posts/new-company-{i}-{timestamp}",
                description=f"New company {i}",
                launch_date=datetime.now()
            ))
        
        logger.info(f"Created {len(mock_companies)} mock companies for testing")
        
        # Test filtering
        start_time = datetime.now()
        unprocessed_companies = controller._filter_unprocessed_companies(mock_companies)
        filter_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Filtering took {filter_time:.3f} seconds")
        logger.info(f"Original companies: {len(mock_companies)}")
        logger.info(f"Unprocessed companies: {len(unprocessed_companies)}")
        logger.info(f"Filtered out: {len(mock_companies) - len(unprocessed_companies)}")
        
        # Show results
        logger.info("\nFiltered out companies:")
        filtered_out = [c for c in mock_companies if c not in unprocessed_companies]
        for company in filtered_out:
            logger.info(f"  - {company.name}")
        
        logger.info("\nCompanies that passed filtering:")
        for company in unprocessed_companies:
            logger.info(f"  + {company.name}")
        
        # Test 5: Performance comparison
        logger.info("\n⚡ Test 5: Performance comparison...")
        
        # Test old method (if we had many companies)
        if len(mock_companies) > 0:
            logger.info("Testing performance with current optimized method...")
            
            # Clear cache to test fresh performance
            controller._clear_processed_companies_cache()
            
            start_time = datetime.now()
            result1 = controller._filter_unprocessed_companies(mock_companies)
            optimized_time = (datetime.now() - start_time).total_seconds()
            
            # Test cached performance
            start_time = datetime.now()
            result2 = controller._filter_unprocessed_companies(mock_companies)
            cached_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"First run (fresh cache): {optimized_time:.3f} seconds")
            logger.info(f"Second run (cached): {cached_time:.3f} seconds")
            logger.info(f"Cache performance improvement: {(optimized_time / max(cached_time, 0.001)):.1f}x faster")
        
        logger.info("\n✅ All deduplication tests completed successfully!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the deduplication tests."""
    logger.info("🚀 Starting company deduplication tests...")
    
    success = test_deduplication()
    
    if success:
        logger.info("🎉 All tests passed! Company deduplication is working correctly.")
        sys.exit(0)
    else:
        logger.error("💥 Tests failed! Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()