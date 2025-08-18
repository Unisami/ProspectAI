"""
Performance regression tests for the job prospect automation system.

This module provides automated tests for API response times, resource usage,
and performance monitoring for critical operations to detect regressions.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from tests.test_utilities import (
    TestUtilities, MockExternalServices, PerformanceTestUtilities
)


class TestPerformanceRegression:
    """Performance regression tests for critical system operations."""
    
    # Performance benchmarks (in seconds)
    BENCHMARKS = {
        'config_loading': 0.1,
        'data_validation': 0.05,
        'mock_api_call': 0.1,
        'data_serialization': 0.05,
        'fixture_creation': 0.01
    }
    
    @PerformanceTestUtilities.create_performance_benchmark(
        "config_loading", BENCHMARKS['config_loading']
    )
    def test_config_loading_performance(self):
        """Test configuration loading performance."""
        # Simulate config loading with various overrides
        configs = []
        for i in range(10):
            config = TestUtilities.create_mock_config(
                notion_token=f'token_{i}',
                hunter_api_key=f'key_{i}',
                scraping_delay=i * 0.1
            )
            configs.append(config)
        
        # Verify all configs were created
        assert len(configs) == 10
    
    @PerformanceTestUtilities.create_performance_benchmark(
        "data_validation", BENCHMARKS['data_validation']
    )
    def test_data_validation_performance(self):
        """Test data validation performance."""
        # Create multiple test data objects
        companies = []
        for i in range(5):
            company = TestUtilities.create_test_company_data(
                name=f'Company {i}',
                domain=f'company{i}.com'
            )
            companies.append(company)
        
        # Create team members
        members = []
        for i in range(10):
            member = TestUtilities.create_test_team_member(
                name=f'Member {i}',
                email=f'member{i}@test.com'
            )
            members.append(member)
        
        assert len(companies) == 5
        assert len(members) == 10
    
    @PerformanceTestUtilities.create_performance_benchmark(
        "mock_api_call", BENCHMARKS['mock_api_call']
    )
    def test_mock_api_call_performance(self):
        """Test mock API call performance."""
        # Test multiple mock service calls
        openai_client = MockExternalServices.mock_openai_client()
        hunter_client = MockExternalServices.mock_hunter_client()
        notion_client = MockExternalServices.mock_notion_client()
        
        # Simulate multiple API calls
        results = []
        for i in range(5):
            # OpenAI call
            openai_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"test {i}"}]
            )
            results.append(openai_response)
            
            # Hunter call
            hunter_response = hunter_client.email_finder(
                f'user{i}', 'test', 'example.com'
            )
            results.append(hunter_response)
            
            # Notion call
            notion_response = notion_client.databases.query(
                database_id=f'db-{i}'
            )
            results.append(notion_response)
        
        assert len(results) == 15  # 5 * 3 services
    
    @PerformanceTestUtilities.create_performance_benchmark(
        "data_serialization", BENCHMARKS['data_serialization']
    )
    def test_data_serialization_performance(self):
        """Test data serialization performance."""
        # Create test data
        company = TestUtilities.create_test_company_data()
        profile = TestUtilities.create_test_linkedin_profile()
        prospect = TestUtilities.create_test_prospect()
        
        # Simulate serialization operations
        serialized_data = []
        for i in range(20):
            # Simulate converting to dict (serialization)
            data = {
                'company': {
                    'name': company.name,
                    'domain': company.domain,
                    'description': company.description
                },
                'profile': {
                    'name': profile.name,
                    'title': profile.title,
                    'company': profile.company
                },
                'prospect': {
                    'name': prospect.name,
                    'email': prospect.email,
                    'title': prospect.title
                }
            }
            serialized_data.append(data)
        
        assert len(serialized_data) == 20
    
    def test_fixture_creation_performance(self, mock_config, test_company_data):
        """Test fixture creation performance using pytest fixtures."""
        def fixture_operations():
            # Access fixture properties multiple times
            configs = []
            companies = []
            
            for i in range(10):
                # Access config properties
                config_data = {
                    'token': mock_config.notion_token,
                    'key': mock_config.hunter_api_key,
                    'delay': mock_config.scraping_delay
                }
                configs.append(config_data)
                
                # Access company data properties
                company_data = {
                    'name': test_company_data.name,
                    'domain': test_company_data.domain,
                    'description': test_company_data.description
                }
                companies.append(company_data)
            
            return configs, companies
        
        # Measure execution time manually
        result, execution_time = PerformanceTestUtilities.measure_execution_time(
            fixture_operations
        )
        
        configs, companies = result
        assert len(configs) == 10
        assert len(companies) == 10
        
        # Check performance
        benchmark = self.BENCHMARKS['fixture_creation']
        assert execution_time <= benchmark, (
            f"Fixture creation too slow: {execution_time:.3f}s > {benchmark}s"
        )


class TestConcurrentPerformance:
    """Test performance under concurrent load."""
    
    def test_concurrent_fixture_usage(self):
        """Test fixture usage under concurrent load."""
        results = []
        errors = []
        
        def create_test_data(thread_id):
            try:
                # Create test data in parallel
                config = TestUtilities.create_mock_config(
                    notion_token=f'token_{thread_id}'
                )
                company = TestUtilities.create_test_company_data(
                    name=f'Company {thread_id}'
                )
                member = TestUtilities.create_test_team_member(
                    name=f'Member {thread_id}'
                )
                
                results.append({
                    'thread_id': thread_id,
                    'config': config,
                    'company': company,
                    'member': member
                })
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_test_data, i) 
                for i in range(10)
            ]
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # Verify data integrity
        for result in results:
            assert result['config'].notion_token.startswith('token_')
            assert result['company'].name.startswith('Company ')
            assert result['member'].name.startswith('Member ')
    
    def test_concurrent_mock_service_calls(self):
        """Test mock service calls under concurrent load."""
        results = []
        errors = []
        
        def make_service_calls(thread_id):
            try:
                # Create mock services
                openai_client = MockExternalServices.mock_openai_client()
                hunter_client = MockExternalServices.mock_hunter_client()
                
                # Make concurrent calls
                openai_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": f"thread {thread_id}"}]
                )
                
                hunter_response = hunter_client.email_finder(
                    f'user{thread_id}', 'test', 'example.com'
                )
                
                results.append({
                    'thread_id': thread_id,
                    'openai_response': openai_response,
                    'hunter_response': hunter_response
                })
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(make_service_calls, i) 
                for i in range(6)
            ]
            
            # Wait for all to complete
            for future in futures:
                future.result()
        
        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 6
        
        # Verify response integrity
        for result in results:
            assert hasattr(result['openai_response'], 'choices')
            assert 'data' in result['hunter_response']


class TestMemoryUsageRegression:
    """Test memory usage patterns to detect memory leaks."""
    
    def test_memory_usage_fixture_creation(self, performance_monitor):
        """Test memory usage during fixture creation."""
        with performance_monitor:
            # Create many test objects
            configs = [
                TestUtilities.create_mock_config() 
                for _ in range(100)
            ]
            companies = [
                TestUtilities.create_test_company_data() 
                for _ in range(50)
            ]
            members = [
                TestUtilities.create_test_team_member() 
                for _ in range(50)
            ]
        
        memory_usage = performance_monitor.get_memory_usage_mb()
        
        # Memory usage should be reasonable (less than 50MB for this test)
        # Note: This might be 0 if psutil is not available (mock monitor)
        assert memory_usage >= 0
        if memory_usage > 0:  # Only check if real monitoring is available
            assert memory_usage < 50, f"Memory usage too high: {memory_usage}MB"
        
        # Verify objects were created
        assert len(configs) == 100
        assert len(companies) == 50
        assert len(members) == 50
    
    def test_memory_usage_mock_services(self, performance_monitor):
        """Test memory usage during mock service operations."""
        with performance_monitor:
            # Create and use many mock services
            for i in range(20):
                openai_client = MockExternalServices.mock_openai_client()
                hunter_client = MockExternalServices.mock_hunter_client()
                notion_client = MockExternalServices.mock_notion_client()
                
                # Make calls to each service
                openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": f"test {i}"}]
                )
                hunter_client.email_finder(f'user{i}', 'test', 'example.com')
                notion_client.databases.query(database_id=f'db-{i}')
        
        memory_usage = performance_monitor.get_memory_usage_mb()
        
        # Memory usage should be reasonable
        assert memory_usage >= 0
        if memory_usage > 0:  # Only check if real monitoring is available
            assert memory_usage < 30, f"Memory usage too high: {memory_usage}MB"


class TestPerformanceMonitoring:
    """Test the performance monitoring utilities themselves."""
    
    def test_execution_time_measurement_accuracy(self):
        """Test that execution time measurement is accurate."""
        def test_function(delay):
            time.sleep(delay)
            return f"slept for {delay}s"
        
        # Test different delays
        delays = [0.01, 0.05, 0.1]
        
        for delay in delays:
            result, execution_time = PerformanceTestUtilities.measure_execution_time(
                test_function, delay
            )
            
            # Execution time should be close to the delay (within 50% tolerance)
            assert result == f"slept for {delay}s"
            assert execution_time >= delay * 0.5
            assert execution_time <= delay * 2.0  # Allow for system overhead
    
    def test_performance_benchmark_thresholds(self):
        """Test that performance benchmarks work correctly."""
        # Test passing benchmark
        @PerformanceTestUtilities.create_performance_benchmark("fast_test", 0.1)
        def fast_function():
            time.sleep(0.01)  # Well under limit
            return "fast"
        
        result = fast_function()
        assert result == "fast"
        
        # Test failing benchmark
        @PerformanceTestUtilities.create_performance_benchmark("slow_test", 0.01)
        def slow_function():
            time.sleep(0.05)  # Over limit
            return "slow"
        
        with pytest.raises(pytest.fail.Exception) as exc_info:
            slow_function()
        
        assert "Performance benchmark 'slow_test' failed" in str(exc_info.value)
    
    def test_memory_monitor_context_manager(self, performance_monitor):
        """Test memory monitor context manager behavior."""
        # Test that context manager works
        with performance_monitor:
            # Allocate some memory
            data = list(range(1000))
            assert len(data) == 1000
        
        # Should be able to get memory usage
        memory_usage = performance_monitor.get_memory_usage_mb()
        assert isinstance(memory_usage, (int, float))
        assert memory_usage >= 0


# Performance test configuration
pytestmark = pytest.mark.performance