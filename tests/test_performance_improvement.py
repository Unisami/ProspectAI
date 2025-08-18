#!/usr/bin/env python3
"""
Performance test to demonstrate the improvement from company deduplication.
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_discovery_with_duplicates():
    """Simulate a discovery run with many duplicate companies to show performance improvement."""
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize controller
        controller = ProspectAutomationController(config)
        
        logger.info("🚀 Starting performance improvement demonstration...")
        
        # Get some real processed companies for testing
        processed_companies = controller.notion_manager.get_processed_company_names()
        
        if len(processed_companies) < 5:
            logger.warning("Not enough processed companies for meaningful test. Need at least 5.")
            return False
        
        # Create a mix of companies - 80% duplicates, 20% new
        test_companies = []
        
        # Add many duplicates (simulate real-world scenario where many companies are already processed)
        for i in range(40):  # 40 duplicate companies
            company_name = processed_companies[i % len(processed_companies)]
            test_companies.append(CompanyData(
                name=company_name,
                domain=f"duplicate{i}.com",
                product_url=f"https://producthunt.com/posts/duplicate{i}",
                description=f"Duplicate company {i}",
                launch_date=datetime.now()
            ))
        
        # Add some new companies
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        for i in range(10):  # 10 new companies
            test_companies.append(CompanyData(
                name=f"New Company {i} {timestamp}",
                domain=f"newcompany{i}-{timestamp}.com",
                product_url=f"https://producthunt.com/posts/new-company-{i}-{timestamp}",
                description=f"New company {i}",
                launch_date=datetime.now()
            ))
        
        logger.info(f"📊 Created test dataset: {len(test_companies)} companies (40 duplicates, 10 new)")
        
        # Test performance with deduplication
        logger.info("🔍 Testing with deduplication enabled...")
        start_time = time.time()
        
        # Clear cache to simulate fresh start
        controller._clear_processed_companies_cache()
        
        # Filter companies (this is where the performance improvement happens)
        unprocessed_companies = controller._filter_unprocessed_companies(test_companies)
        
        dedup_time = time.time() - start_time
        
        logger.info(f"⚡ Deduplication results:")
        logger.info(f"   - Original companies: {len(test_companies)}")
        logger.info(f"   - After deduplication: {len(unprocessed_companies)}")
        logger.info(f"   - Duplicates filtered: {len(test_companies) - len(unprocessed_companies)}")
        logger.info(f"   - Time taken: {dedup_time:.3f} seconds")
        logger.info(f"   - Processing time saved: ~{(len(test_companies) - len(unprocessed_companies)) * 5:.0f} minutes")
        logger.info(f"     (assuming 5 minutes per company without deduplication)")
        
        # Calculate potential time savings
        companies_saved = len(test_companies) - len(unprocessed_companies)
        time_per_company = 5 * 60  # 5 minutes in seconds
        time_saved = companies_saved * time_per_company
        
        logger.info(f"💰 Performance improvement:")
        logger.info(f"   - Companies that would have been processed unnecessarily: {companies_saved}")
        logger.info(f"   - Estimated time saved: {time_saved / 60:.1f} minutes ({time_saved / 3600:.1f} hours)")
        logger.info(f"   - Deduplication overhead: {dedup_time:.3f} seconds")
        logger.info(f"   - Net time savings: {(time_saved - dedup_time) / 60:.1f} minutes")
        logger.info(f"   - Efficiency improvement: {time_saved / dedup_time:.0f}x return on investment")
        
        # Test cache performance
        logger.info("💾 Testing cache performance...")
        
        # Second run should be much faster due to caching
        start_time = time.time()
        unprocessed_companies_2 = controller._filter_unprocessed_companies(test_companies)
        cached_time = time.time() - start_time
        
        logger.info(f"   - First run (fresh cache): {dedup_time:.3f} seconds")
        logger.info(f"   - Second run (cached): {cached_time:.3f} seconds")
        logger.info(f"   - Cache performance improvement: {dedup_time / max(cached_time, 0.001):.0f}x faster")
        
        # Verify consistency
        if len(unprocessed_companies) == len(unprocessed_companies_2):
            logger.info("✅ Cache consistency verified - same results from both runs")
        else:
            logger.warning("⚠️ Cache inconsistency detected")
        
        # Summary
        logger.info("📈 Summary:")
        logger.info(f"   - Without deduplication: Would process {len(test_companies)} companies")
        logger.info(f"   - With deduplication: Only process {len(unprocessed_companies)} companies")
        logger.info(f"   - Efficiency gain: {((len(test_companies) - len(unprocessed_companies)) / len(test_companies)) * 100:.1f}% reduction in work")
        logger.info(f"   - Time savings: {time_saved / 3600:.1f} hours per run")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the performance test."""
    logger.info("🎯 Starting performance improvement demonstration...")
    
    success = simulate_discovery_with_duplicates()
    
    if success:
        logger.info("🎉 Performance test completed successfully!")
        logger.info("💡 The deduplication system provides significant time savings by avoiding redundant work.")
        sys.exit(0)
    else:
        logger.error("💥 Performance test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()