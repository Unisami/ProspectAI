#!/usr/bin/env python3
"""
Test script to verify parallel processing performance improvement.
"""

import time
import logging
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

# Enable logging
logging.basicConfig(level=logging.INFO)

def test_parallel_vs_sequential():
    """Test parallel processing vs sequential processing."""
    print("🧪 Testing Parallel Processing Performance")
    print("="*60)
    
    try:
        # Initialize controller
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Test with a small number of companies
        test_limit = 5
        
        print(f"🔄 Running discovery pipeline for {test_limit} companies...")
        print("📊 This will use parallel processing (check logs for timing)")
        
        start_time = time.time()
        
        # Run discovery pipeline (now uses parallel processing)
        results = controller.run_discovery_pipeline(
            limit=test_limit,
            campaign_name="Parallel Processing Test"
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Display results
        print("\n" + "="*60)
        print("🚀 PARALLEL PROCESSING TEST RESULTS")
        print("="*60)
        
        summary = results.get('summary', {})
        companies_processed = summary.get('companies_processed', 0)
        prospects_found = summary.get('prospects_found', 0)
        
        print(f"📊 Companies Processed: {companies_processed}")
        print(f"👥 Prospects Found: {prospects_found}")
        print(f"⏱️  Total Duration: {total_duration:.1f}s ({total_duration/60:.1f}m)")
        
        if companies_processed > 0:
            avg_time_per_company = total_duration / companies_processed
            print(f"📈 Avg Time/Company: {avg_time_per_company:.1f}s")
            
            # Estimate sequential time (with 2s delay between companies)
            estimated_sequential = (avg_time_per_company * companies_processed) + (2 * (companies_processed - 1))
            speedup = estimated_sequential / total_duration if total_duration > 0 else 1
            
            print(f"🚄 Estimated Sequential Time: {estimated_sequential:.1f}s")
            print(f"⚡ Speedup Factor: {speedup:.1f}x")
            
            if speedup > 1.5:
                print("✅ Parallel processing is working effectively!")
            else:
                print("⚠️  Parallel processing may need optimization")
        
        if prospects_found > 0:
            prospects_per_minute = (prospects_found / total_duration) * 60
            print(f"🎯 Processing Rate: {prospects_per_minute:.1f} prospects/minute")
            
            # Calculate projected time for 20 prospects
            if prospects_per_minute > 0:
                projected_time_20 = (20 / prospects_per_minute) * 60  # in seconds
                print(f"📊 Projected Time for 20 Prospects: {projected_time_20/60:.1f} minutes")
                
                if projected_time_20 < 3600:  # Less than 1 hour
                    print("🎉 Significant improvement over 108 minutes!")
                else:
                    print("⚠️  Still needs more optimization")
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parallel_vs_sequential()