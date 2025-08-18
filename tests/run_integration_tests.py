#!/usr/bin/env python3
"""
Test runner script for integration tests.

This script provides an easy way to run the comprehensive integration tests
for the Job Prospect Automation system.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_integration_tests(test_pattern=None, verbose=False, coverage=False):
    """
    Run integration tests with optional filtering and coverage.
    
    Args:
        test_pattern: Optional pattern to filter tests (e.g., "test_email_generation")
        verbose: Whether to run tests in verbose mode
        coverage: Whether to run tests with coverage reporting
    """
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test files
    test_files = [
        Path(__file__).parent / "test_integration_e2e.py",
        Path(__file__).parent / "test_comprehensive_enhanced_features.py",
        Path(__file__).parent / "test_enhanced_workflow_integration.py",
        Path(__file__).parent / "test_ai_integration.py"
    ]
    
    # Only add files that exist
    for test_file in test_files:
        if test_file.exists():
            cmd.append(str(test_file))
    
    # Add test pattern if specified
    if test_pattern:
        cmd.extend(["-k", test_pattern])
    
    # Add verbose flag
    if verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=controllers", "--cov=services", "--cov=models", "--cov-report=html"])
    
    # Add other useful flags
    cmd.extend([
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "-x"  # Stop on first failure
    ])
    
    print(f"Running command: {' '.join(cmd)}")
    print("-" * 80)
    
    # Run the tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run integration tests for Job Prospect Automation system"
    )
    
    parser.add_argument(
        "-k", "--pattern",
        help="Run only tests matching this pattern (e.g., 'email_generation')"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available integration tests"
    )
    
    args = parser.parse_args()
    
    if args.list_tests:
        print("Available Integration Test Categories:")
        print("=" * 50)
        print("1. End-to-End Integration Tests:")
        print("   - test_complete_discovery_pipeline_workflow")
        print("   - test_email_generation_workflow")
        print("   - test_batch_processing_workflow")
        print("   - test_error_handling_and_recovery_scenarios")
        print("   - test_data_consistency_validation")
        print("   - test_workflow_status_and_monitoring")
        print()
        print("2. Enhanced Features Integration Tests:")
        print("   - test_ai_parsing_workflow_integration")
        print("   - test_complete_enhanced_pipeline_workflow")
        print("   - test_end_to_end_with_all_mock_apis")
        print("   - test_api_error_handling_and_fallbacks")
        print()
        print("3. AI Integration Tests:")
        print("   - test_linkedin_scraper_with_ai_parsing_success")
        print("   - test_product_hunt_scraper_with_ai_parsing_success")
        print("   - test_ai_parsing_fallback_mechanisms")
        print()
        print("4. Performance Integration Tests:")
        print("   - test_ai_parsing_performance_linkedin_profiles")
        print("   - test_ai_parsing_performance_concurrent_processing")
        print("   - test_email_generation_performance_bulk_processing")
        print("   - test_ai_parsing_memory_usage")
        print()
        print("5. Error Handling Integration Tests:")
        print("   - test_producthunt_scraping_failures")
        print("   - test_partial_company_processing_failures")
        print("   - test_api_rate_limiting_scenarios")
        print("   - test_notion_storage_failures")
        print()
        print("6. Batch Processing Integration Tests:")
        print("   - test_batch_processing_with_progress_tracking")
        print("   - test_batch_pause_and_resume_functionality")
        print("   - test_batch_error_recovery")
        print()
        print("7. Data Validation Integration Tests:")
        print("   - test_email_domain_consistency_validation")
        print("   - test_linkedin_profile_name_matching")
        print("   - test_required_fields_validation")
        print()
        print("Usage Examples:")
        print("  python run_integration_tests.py                    # Run all tests")
        print("  python run_integration_tests.py -k email           # Run email-related tests")
        print("  python run_integration_tests.py -k enhanced        # Run enhanced features tests")
        print("  python run_integration_tests.py -k ai_parsing      # Run AI parsing tests")
        print("  python run_integration_tests.py -k performance     # Run performance tests")
        print("  python run_integration_tests.py -k batch -v        # Run batch tests verbosely")
        print("  python run_integration_tests.py --coverage         # Run with coverage")
        return 0
    
    # Run the integration tests
    return run_integration_tests(
        test_pattern=args.pattern,
        verbose=args.verbose,
        coverage=args.coverage
    )


if __name__ == "__main__":
    sys.exit(main())