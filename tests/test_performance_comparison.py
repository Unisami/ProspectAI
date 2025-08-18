#!/usr/bin/env python3
"""
Performance comparison test to measure the impact of optimizations.
"""

import time
import logging
from utils.config import Config
from controllers.prospect_automation_controller import ProspectAutomationController

# Enable detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_performance():
    """Test current performance with optimizations."""
    print("🚀 Performance Test - Optimized Parallel Processing")
    print("="*70)
    
    try:
        config = Config.from_env()
        controller = ProspectAutomationController(config)
        
        # Test with 3 companies to compare with previous results
        test_limit = 3
        
        print(f"🔄 Running discovery pipeline for {test_limit} companies...")
        print("📊 Measuring performance with optimizations:")
        print("   • Increased parallel workers: 2-6 (was 1-3)")
        print("   • Reduced scraping delay: 1.0s (was 2.0s)")
        print("   • Increased Hunter rate limit: 15/min (was 10/min)")
        print("   • Quality maintained: Full token limits preserved")
        
        start_time = time.time()
        
        results = controller.run_discovery_pipeline(
            limit=test_limit,
            campaign_name="Performance Optimization Test"
        )
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Display results
        print("\n" + "="*70)
        print("📊 PERFORMANCE TEST RESULTS")
        print("="*70)
        
        summary = results.get('summary', {})
        companies_processed = summary.get('companies_processed', 0)
        prospects_found = summary.get('prospects_found', 0)
        
        print(f"📈 Results:")
        print(f"   Companies Processed: {companies_processed}")
        print(f"   Prospects Found: {prospects_found}")
        print(f"   Total Duration: {total_duration:.1f}s ({total_duration/60:.1f}m)")
        
        if companies_processed > 0:
            avg_time_per_company = total_duration / companies_processed
            print(f"   Avg Time/Company: {avg_time_per_company:.1f}s ({avg_time_per_company/60:.1f}m)")
            
        if prospects_found > 0:
            avg_time_per_prospect = total_duration / prospects_found
            prospects_per_minute = (prospects_found / total_duration) * 60
            print(f"   Avg Time/Prospect: {avg_time_per_prospect:.1f}s ({avg_time_per_prospect/60:.1f}m)")
            print(f"   Processing Rate: {prospects_per_minute:.1f} prospects/minute")
            
            # Compare with previous performance
            print(f"\n📊 Performance Comparison:")
            print(f"   Previous (before parallel): ~1.9 min/prospect")
            print(f"   Previous (broken parallel): ~6.4 min/prospect")
            print(f"   Current (optimized): {avg_time_per_prospect/60:.1f} min/prospect")
            
            if avg_time_per_prospect < 6.4 * 60:
                improvement = (6.4 * 60) / avg_time_per_prospect
                print(f"   ✅ Improvement: {improvement:.1f}x faster than broken parallel")
            
            if avg_time_per_prospect < 1.9 * 60:
                improvement = (1.9 * 60) / avg_time_per_prospect
                print(f"   🚀 Improvement: {improvement:.1f}x faster than original!")
            
            # Project performance for larger batches
            projected_20_prospects = (20 / prospects_per_minute) * 60  # seconds
            print(f"\n🎯 Projected Performance:")
            print(f"   20 prospects: {projected_20_prospects/60:.1f} minutes")
            print(f"   Original target: <30 minutes")
            
            if projected_20_prospects < 30 * 60:
                print(f"   ✅ TARGET ACHIEVED!")
            else:
                print(f"   ⚠️  Still needs optimization")
        
        print("="*70)
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_performance()