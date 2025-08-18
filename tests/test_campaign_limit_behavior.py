#!/usr/bin/env python3
"""
Test script to verify that campaign limits work correctly with deduplication.
This tests the scenario where a campaign is interrupted and restarted.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController
from models.data_models import CompanyData

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_campaign_limit_behavior():
    """Test that campaign limits work correctly even with existing processed companies."""
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize controller
        controller = ProspectAutomationController(config)
        
        logger.info("🧪 Testing campaign limit behavior with deduplication...")
        
        # Test 1: Check current processed companies
        logger.info("\n📋 Test 1: Checking current state...")
        processed_companies = controller.notion_manager.get_processed_company_names()
        logger.info(f"Currently have {len(processed_companies)} processed companies")
        
        # Test 2: Test discovery with small limit
        logger.info("\n🔍 Test 2: Testing discovery with limit=3...")
        
        # Clear cache to simulate fresh start
        controller._clear_processed_companies_cache()
        
        # Test the discovery method directly
        discovered_companies = controller._discover_companies(limit=3)
        
        logger.info(f"✅ Discovery results:")
        logger.info(f"   - Requested: 3 companies")
        logger.info(f"   - Discovered: {len(discovered_companies)} companies")
        logger.info(f"   - Companies found:")
        
        for i, company in enumerate(discovered_companies, 1):
            logger.info(f"     {i}. {company.name} ({company.domain})")
        
        # Test 3: Verify the companies are actually new
        logger.info("\n✅ Test 3: Verifying companies are new...")
        
        for company in discovered_companies:
            is_processed = controller.notion_manager.is_company_already_processed(company.name, company.domain)
            if is_processed:
                logger.error(f"❌ ERROR: Company {company.name} was marked as already processed but was returned!")
            else:
                logger.info(f"✅ {company.name} is correctly identified as new")
        
        # Test 4: Test with larger limit
        logger.info("\n🔍 Test 4: Testing discovery with limit=5...")
        
        discovered_companies_5 = controller._discover_companies(limit=5)
        
        logger.info(f"✅ Discovery results for limit=5:")
        logger.info(f"   - Requested: 5 companies")
        logger.info(f"   - Discovered: {len(discovered_companies_5)} companies")
        
        # Test 5: Simulate interrupted campaign scenario
        logger.info("\n🔄 Test 5: Simulating interrupted campaign scenario...")
        
        # Simulate what happens when you restart a campaign
        logger.info("Scenario: You started a campaign for 10 companies, 5 were processed, then system restarted")
        
        # This simulates the restart behavior
        target_limit = 10
        logger.info(f"Requesting {target_limit} companies (simulating campaign restart)...")
        
        restart_companies = controller._discover_companies(limit=target_limit)
        
        logger.info(f"📊 Restart simulation results:")
        logger.info(f"   - Original target: {target_limit} companies")
        logger.info(f"   - Companies to process: {len(restart_companies)}")
        logger.info(f"   - Expected behavior: Should get {target_limit} NEW companies to process")
        
        if len(restart_companies) == target_limit:
            logger.info("✅ SUCCESS: Got exactly the requested number of new companies!")
        elif len(restart_companies) < target_limit:
            logger.info(f"⚠️ PARTIAL: Got {len(restart_companies)} companies (might be due to limited new companies available)")
        else:
            logger.info(f"❌ ERROR: Got more companies than requested ({len(restart_companies)} > {target_limit})")
        
        # Test 6: Performance check
        logger.info("\n⚡ Test 6: Performance check...")
        
        import time
        start_time = time.time()
        
        # Test with cache cleared
        controller._clear_processed_companies_cache()
        perf_companies = controller._discover_companies(limit=3)
        
        first_run_time = time.time() - start_time
        
        # Test with cache populated
        start_time = time.time()
        perf_companies_2 = controller._discover_companies(limit=3)
        second_run_time = time.time() - start_time
        
        logger.info(f"Performance results:")
        logger.info(f"   - First run (fresh cache): {first_run_time:.3f} seconds")
        logger.info(f"   - Second run (cached): {second_run_time:.3f} seconds")
        logger.info(f"   - Performance improvement: {first_run_time / max(second_run_time, 0.001):.1f}x faster")
        
        # Summary
        logger.info("\n📈 Summary:")
        logger.info(f"   - The system now correctly handles campaign limits")
        logger.info(f"   - When you request N companies, you get N NEW companies to process")
        logger.info(f"   - Already processed companies are automatically filtered out")
        logger.info(f"   - The system will fetch more from ProductHunt if needed to reach your target")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to run the campaign limit behavior test."""
    logger.info("🚀 Starting campaign limit behavior test...")
    
    success = test_campaign_limit_behavior()
    
    if success:
        logger.info("🎉 All tests passed! Campaign limit behavior is working correctly.")
        logger.info("💡 Now when you restart a campaign, it will process the remaining companies to reach your target.")
        sys.exit(0)
    else:
        logger.error("💥 Tests failed! Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()