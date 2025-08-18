#!/usr/bin/env python3
"""
Script to run performance regression tests.

This script provides an easy way to run performance tests separately
from the main test suite and generate performance reports.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_performance_tests():
    """Run all performance regression tests."""
    print("🚀 Running Performance Regression Tests")
    print("=" * 50)
    
    start_time = time.time()
    
    # Run performance tests with detailed output
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/test_performance_regression.py",
        "-v",
        "--tb=short",
        "-m", "performance"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n⏱️  Total execution time: {total_time:.2f} seconds")
        
        if result.returncode == 0:
            print("✅ All performance tests passed!")
        else:
            print("❌ Some performance tests failed!")
            print(f"Exit code: {result.returncode}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running performance tests: {e}")
        return False


def run_specific_performance_test(test_name):
    """Run a specific performance test."""
    print(f"🎯 Running specific performance test: {test_name}")
    print("=" * 50)
    
    cmd = [
        sys.executable, "-m", "pytest", 
        f"tests/test_performance_regression.py::{test_name}",
        "-v",
        "--tb=short"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running test {test_name}: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_performance_test(test_name)
    else:
        # Run all performance tests
        success = run_performance_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()