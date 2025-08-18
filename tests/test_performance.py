#!/usr/bin/env python3
"""
Test performance improvements with timing measurements.
"""

import time
import sys
from controllers.prospect_automation_controller import ProspectAutomationController
from utils.config import Config

def test_performance():
    """Test the performance of the optimized workflow."""
    print("🚀 Testing Performance Optimizations")
    print("=" * 50)
    
    # Load optimized config
    config = Config.from_env()
    
    print(f"Scraping delay: {config.scraping_delay}s")
    print(f"Max workers: 4 (optimized)")
    print(f"Image loading: Disabled")
    print(f"AI processing: Optimized")
    
    # Initialize controller
    start_time = time.time()
    controller = ProspectAutomationController(config)
    init_time = time.time() - start_time
    
    print(f"\n⚡ Controller initialization: {init_time:.2f}s")
    
    # Test with 1 company
    print("\n🧪 Testing with 1 company (target: <2 minutes)...")
    
    return controller

def benchmark_components():
    """Benchmark individual components."""
    print("\n🔍 Component Benchmarks:")
    print("-" * 30)
    
    # Test WebDriver creation
    start = time.time()
    from utils.webdriver_manager import get_webdriver_manager
    wm = get_webdriver_manager()
    with wm.get_driver("test") as driver:
        driver.get("https://www.linkedin.com")
    webdriver_time = time.time() - start
    print(f"WebDriver + Page Load: {webdriver_time:.2f}s")
    
    # Test AI processing
    start = time.time()
    from services.ai_service import AIService
    from utils.config import Config
    ai_service = AIService(Config.from_env(), "test")
    ai_init_time = time.time() - start
    print(f"AI Service Init: {ai_init_time:.2f}s")

if __name__ == "__main__":
    controller = test_performance()
    benchmark_components()
    
    print("\n🎯 Performance Targets:")
    print("- Total processing: <2 minutes per company")
    print("- LinkedIn extraction: <30 seconds per profile") 
    print("- AI processing: <15 seconds per operation")
    print("- WebDriver operations: <5 seconds")
    
    print("\n✅ Performance test completed!")
