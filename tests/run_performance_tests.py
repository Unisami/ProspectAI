#!/usr/bin/env python3
"""
Performance test runner for enhanced features.

This script runs performance tests for AI parsing, email generation, and other enhanced features
to ensure they meet performance requirements.
"""

import sys
import subprocess
import argparse
import time
from pathlib import Path
import json


def run_performance_tests(test_pattern=None, verbose=False, output_file=None):
    """
    Run performance tests for enhanced features.
    
    Args:
        test_pattern: Optional pattern to filter tests
        verbose: Whether to run tests in verbose mode
        output_file: Optional file to save performance results
    """
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test file
    test_file = Path(__file__).parent / "test_comprehensive_enhanced_features.py"
    cmd.append(str(test_file))
    
    # Filter to performance tests only
    if test_pattern:
        cmd.extend(["-k", f"performance and {test_pattern}"])
    else:
        cmd.extend(["-k", "performance"])
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add performance-specific flags
    cmd.extend([
        "--tb=short",  # Short traceback format
        "--durations=10",  # Show 10 slowest tests
        "-x"  # Stop on first failure
    ])
    
    print(f"Running performance tests: {' '.join(cmd)}")
    print("-" * 80)
    
    # Capture start time
    start_time = time.time()
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent, capture_output=True, text=True)
    
    # Capture end time
    end_time = time.time()
    total_time = end_time - start_time
    
    # Print results
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print(f"\nTotal test execution time: {total_time:.2f} seconds")
    
    # Save results if requested
    if output_file:
        performance_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time": total_time,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        with open(output_file, 'w') as f:
            json.dump(performance_results, f, indent=2)
        
        print(f"Performance results saved to: {output_file}")
    
    return result.returncode


def run_ai_parsing_benchmarks():
    """Run specific AI parsing performance benchmarks."""
    print("Running AI Parsing Performance Benchmarks")
    print("=" * 50)
    
    # Run AI parsing performance tests
    cmd = [
        "python", "-m", "pytest",
        str(Path(__file__).parent / "test_comprehensive_enhanced_features.py"),
        "-k", "ai_parsing_performance",
        "-v", "--durations=0"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def run_email_generation_benchmarks():
    """Run specific email generation performance benchmarks."""
    print("Running Email Generation Performance Benchmarks")
    print("=" * 50)
    
    # Run email generation performance tests
    cmd = [
        "python", "-m", "pytest",
        str(Path(__file__).parent / "test_comprehensive_enhanced_features.py"),
        "-k", "email_generation_performance",
        "-v", "--durations=0"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def run_memory_usage_tests():
    """Run memory usage tests."""
    print("Running Memory Usage Tests")
    print("=" * 50)
    
    # Run memory usage tests
    cmd = [
        "python", "-m", "pytest",
        str(Path(__file__).parent / "test_comprehensive_enhanced_features.py"),
        "-k", "memory_usage",
        "-v", "--durations=0"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def run_concurrent_processing_tests():
    """Run concurrent processing performance tests."""
    print("Running Concurrent Processing Tests")
    print("=" * 50)
    
    # Run concurrent processing tests
    cmd = [
        "python", "-m", "pytest",
        str(Path(__file__).parent / "test_comprehensive_enhanced_features.py"),
        "-k", "concurrent_processing",
        "-v", "--durations=0"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """Main entry point for the performance test runner."""
    parser = argparse.ArgumentParser(
        description="Run performance tests for enhanced features"
    )
    
    parser.add_argument(
        "-k", "--pattern",
        help="Run only tests matching this pattern"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    parser.add_argument(
        "--output",
        help="Save performance results to file"
    )
    
    parser.add_argument(
        "--benchmark",
        choices=["ai-parsing", "email-generation", "memory", "concurrent", "all"],
        help="Run specific benchmark suite"
    )
    
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available performance tests"
    )
    
    args = parser.parse_args()
    
    if args.list_tests:
        print("Available Performance Test Categories:")
        print("=" * 50)
        print("1. AI Parsing Performance Tests:")
        print("   - test_ai_parsing_performance_linkedin_profiles")
        print("   - test_ai_parsing_performance_concurrent_processing")
        print("   - test_ai_parsing_memory_usage")
        print()
        print("2. Email Generation Performance Tests:")
        print("   - test_email_generation_performance_bulk_processing")
        print()
        print("3. Memory Usage Tests:")
        print("   - test_ai_parsing_memory_usage")
        print()
        print("4. Concurrent Processing Tests:")
        print("   - test_ai_parsing_performance_concurrent_processing")
        print()
        print("Usage Examples:")
        print("  python run_performance_tests.py                    # Run all performance tests")
        print("  python run_performance_tests.py -k ai_parsing      # Run AI parsing tests")
        print("  python run_performance_tests.py --benchmark all    # Run all benchmarks")
        print("  python run_performance_tests.py --output results.json  # Save results")
        return 0
    
    if args.benchmark:
        if args.benchmark == "ai-parsing":
            return run_ai_parsing_benchmarks()
        elif args.benchmark == "email-generation":
            return run_email_generation_benchmarks()
        elif args.benchmark == "memory":
            return run_memory_usage_tests()
        elif args.benchmark == "concurrent":
            return run_concurrent_processing_tests()
        elif args.benchmark == "all":
            results = []
            results.append(run_ai_parsing_benchmarks())
            results.append(run_email_generation_benchmarks())
            results.append(run_memory_usage_tests())
            results.append(run_concurrent_processing_tests())
            return max(results)  # Return worst result
    
    # Run the performance tests
    return run_performance_tests(
        test_pattern=args.pattern,
        verbose=args.verbose,
        output_file=args.output
    )


if __name__ == "__main__":
    sys.exit(main())