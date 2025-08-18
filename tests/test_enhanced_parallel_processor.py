#!/usr/bin/env python3
"""
Performance tests for the enhanced parallel processing service.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from typing import List

from services.parallel_processor import (
    EnhancedParallelProcessor, ParallelProcessor, ProcessingResult, 
    ProgressInfo, BatchConfig, ResourceUsage
)
from models.data_models import CompanyData, Prospect


class TestEnhancedParallelProcessor:
    """Test enhanced parallel processor functionality."""
    
    @pytest.fixture
    def processor(self, mock_config):
        """Create enhanced parallel processor for testing."""
        processor = EnhancedParallelProcessor(mock_config, max_workers=2, enable_monitoring=False)
        yield processor
        processor.shutdown()
    
    @pytest.fixture
    def sample_companies(self):
        """Create sample company data for testing."""
        from datetime import datetime
        return [
            CompanyData(
                name=f"Company {i}",
                domain=f"company{i}.com",
                product_url=f"https://company{i}.com",
                description=f"Description for company {i}",
                launch_date=datetime(2024, 1, 1)
            )
            for i in range(5)
        ]
    
    @pytest.fixture
    def sample_prospects(self):
        """Create sample prospect data."""
        return [
            Prospect(
                name="John Doe",
                role="CEO",
                company="Test Company",
                email="john@company.com",
                linkedin_url="https://linkedin.com/in/johndoe"
            )
        ]
    
    def test_processor_initialization(self, mock_config):
        """Test processor initialization."""
        processor = EnhancedParallelProcessor(mock_config, max_workers=3, enable_monitoring=True)
        
        assert processor.max_workers == 3
        assert processor.enable_monitoring is True
        assert processor.rate_limiter is not None
        assert processor.processing_stats['total_companies'] == 0
        
        processor.shutdown()
    
    def test_basic_parallel_processing(self, processor, sample_companies, sample_prospects):
        """Test basic parallel processing functionality."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(0.1)  # Simulate processing time
            return sample_prospects
        
        results = processor.process_companies_parallel(sample_companies, mock_process_function)
        
        assert len(results) == len(sample_companies)
        assert all(result.success for result in results)
        assert all(len(result.prospects) == 1 for result in results)
        assert processor.processing_stats['successful_companies'] == len(sample_companies)
        assert processor.processing_stats['total_prospects'] == len(sample_companies)
    
    def test_error_handling_and_retries(self, processor, sample_companies):
        """Test error handling and retry logic."""
        call_count = 0
        
        def failing_process_function(company: CompanyData) -> List[Prospect]:
            nonlocal call_count
            call_count += 1
            if call_count <= 2:  # Fail first two attempts
                raise Exception(f"Simulated error for {company.name}")
            return []
        
        config = BatchConfig(max_retries=2, retry_delay=0.1)
        results = processor.process_companies_parallel(sample_companies, failing_process_function, config)
        
        # Should have original results plus retry results
        assert len(results) >= len(sample_companies)  # At least as many as original companies
        assert processor.processing_stats['total_retries'] > 0
        
        # Check that we have both failed and successful results
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        assert len(successful_results) > 0  # Some should succeed after retries
        assert len(failed_results) > 0  # Some should fail initially
    
    def test_progress_tracking(self, processor, sample_companies, sample_prospects):
        """Test progress tracking functionality."""
        progress_updates = []
        
        def progress_callback(progress: ProgressInfo):
            progress_updates.append(progress)
        
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(0.05)
            return sample_prospects
        
        config = BatchConfig(progress_callback=progress_callback)
        results = processor.process_companies_parallel(sample_companies, mock_process_function, config)
        
        assert len(results) == len(sample_companies)
        assert len(progress_updates) > 0
        
        # Check that progress updates are meaningful
        final_progress = progress_updates[-1]
        assert final_progress.total_items == len(sample_companies)
        assert final_progress.completed_items <= len(sample_companies)
        assert final_progress.completion_percentage <= 100.0
    
    def test_batch_processing(self, processor, sample_companies, sample_prospects):
        """Test batch processing functionality."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(0.05)
            return sample_prospects
        
        config = BatchConfig(batch_size=2, delay_between_batches=0.1)
        results = processor.process_companies_with_batching(sample_companies, mock_process_function, config)
        
        assert len(results) == len(sample_companies)
        assert all(result.success for result in results)
    
    def test_rate_limited_processing(self, processor, sample_companies, sample_prospects):
        """Test rate-limited processing."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            return sample_prospects
        
        start_time = time.time()
        results = processor.process_with_rate_limiting(
            sample_companies[:3], 
            mock_process_function, 
            "test_service",
            max_concurrent=1
        )
        duration = time.time() - start_time
        
        assert len(results) == 3
        assert all(result.success for result in results)
        # Should take some time due to rate limiting
        assert duration > 0.1
    
    def test_resource_monitoring(self, mock_config):
        """Test resource monitoring functionality."""
        processor = EnhancedParallelProcessor(mock_config, max_workers=2, enable_monitoring=True)
        
        # Give monitoring thread time to start
        time.sleep(0.1)
        
        resource_usage = processor.get_resource_usage()
        assert isinstance(resource_usage, ResourceUsage)
        assert resource_usage.memory_mb >= 0
        
        processor.shutdown()
    
    def test_graceful_shutdown(self, processor, sample_companies):
        """Test graceful shutdown functionality."""
        def slow_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(1.0)  # Long processing time
            return []
        
        # Start processing in background thread
        def background_processing():
            processor.process_companies_parallel(sample_companies, slow_process_function)
        
        thread = threading.Thread(target=background_processing)
        thread.start()
        
        # Give it time to start
        time.sleep(0.1)
        
        # Shutdown should stop processing
        processor.shutdown()
        
        # Thread should finish quickly after shutdown
        thread.join(timeout=2.0)
        assert not thread.is_alive()
    
    def test_memory_usage_tracking(self, processor, sample_companies, sample_prospects):
        """Test memory usage tracking."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            # Create some data to use memory
            large_data = [i for i in range(1000)]
            return sample_prospects
        
        results = processor.process_companies_parallel(sample_companies, mock_process_function)
        
        assert len(results) == len(sample_companies)
        assert processor.processing_stats['peak_memory_mb'] >= 0
        
        # Check that individual results have memory tracking
        for result in results:
            assert hasattr(result, 'memory_usage_mb')
            assert result.memory_usage_mb >= 0
    
    def test_error_callback(self, processor, sample_companies):
        """Test error callback functionality."""
        error_reports = []
        
        def error_callback(item_name: str, error: Exception):
            error_reports.append((item_name, str(error)))
        
        def failing_process_function(company: CompanyData) -> List[Prospect]:
            raise Exception(f"Test error for {company.name}")
        
        config = BatchConfig(error_callback=error_callback, max_retries=0)
        results = processor.process_companies_parallel(sample_companies, failing_process_function, config)
        
        assert len(results) == len(sample_companies)
        assert all(not result.success for result in results)
        assert len(error_reports) == len(sample_companies)
    
    def test_concurrent_processing_safety(self, processor, sample_companies, sample_prospects):
        """Test thread safety of concurrent processing."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(0.01)
            return sample_prospects
        
        # Run multiple processing operations concurrently
        threads = []
        results_list = []
        
        def run_processing():
            results = processor.process_companies_parallel(sample_companies[:2], mock_process_function)
            results_list.append(results)
        
        for _ in range(3):
            thread = threading.Thread(target=run_processing)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All operations should complete successfully
        assert len(results_list) == 3
        for results in results_list:
            assert len(results) == 2
            assert all(result.success for result in results)


class TestBackwardCompatibility:
    """Test backward compatibility with the original ParallelProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create backward compatible processor."""
        processor = ParallelProcessor(max_workers=2, respect_rate_limits=True)
        yield processor
        processor.shutdown()
    
    @pytest.fixture
    def sample_companies(self):
        """Create sample company data for testing."""
        from datetime import datetime
        return [
            CompanyData(
                name=f"Company {i}",
                domain=f"company{i}.com",
                product_url=f"https://company{i}.com",
                description=f"Description for company {i}",
                launch_date=datetime(2024, 1, 1)
            )
            for i in range(3)
        ]
    
    def test_backward_compatible_interface(self, processor, sample_companies):
        """Test that old interface still works."""
        progress_calls = []
        
        def progress_callback(name: str, completed: int, total: int):
            progress_calls.append((name, completed, total))
        
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            return []
        
        results = processor.process_companies_parallel(
            sample_companies, 
            mock_process_function,
            progress_callback
        )
        
        assert len(results) == len(sample_companies)
        assert len(progress_calls) > 0
    
    def test_backward_compatible_batching(self, processor, sample_companies):
        """Test that old batching interface still works."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            return []
        
        results = processor.process_companies_with_batching(
            sample_companies,
            mock_process_function,
            batch_size=2,
            delay_between_batches=0.1
        )
        
        assert len(results) == len(sample_companies)
    
    def test_processing_stats_compatibility(self, processor, sample_companies):
        """Test that processing stats are still available."""
        def mock_process_function(company: CompanyData) -> List[Prospect]:
            return []
        
        processor.process_companies_parallel(sample_companies, mock_process_function)
        
        stats = processor.get_processing_stats()
        assert 'total_companies' in stats
        assert 'successful_companies' in stats
        assert 'failed_companies' in stats
        assert stats['total_companies'] == len(sample_companies)


class TestPerformanceRegression:
    """Performance regression tests."""
    
    @pytest.fixture
    # Using shared mock_config fixture from conftest.py
    def test_processing_throughput(self, mock_config):
        """Test processing throughput meets minimum requirements."""
        from datetime import datetime
        processor = EnhancedParallelProcessor(mock_config, max_workers=4, enable_monitoring=False)
        
        # Create larger dataset for throughput testing
        companies = [
            CompanyData(
                name=f"Company {i}",
                domain=f"company{i}.com",
                product_url=f"https://company{i}.com",
                description=f"Description for company {i}",
                launch_date=datetime(2024, 1, 1)
            )
            for i in range(20)
        ]
        
        def fast_process_function(company: CompanyData) -> List[Prospect]:
            time.sleep(0.01)  # Minimal processing time
            return []
        
        start_time = time.time()
        results = processor.process_companies_parallel(companies, fast_process_function)
        duration = time.time() - start_time
        
        throughput = len(companies) / duration
        
        assert len(results) == len(companies)
        assert throughput > 10  # Should process at least 10 companies per second
        
        processor.shutdown()
    
    def test_memory_efficiency(self, mock_config):
        """Test memory usage stays within reasonable bounds."""
        from datetime import datetime
        processor = EnhancedParallelProcessor(mock_config, max_workers=2, enable_monitoring=True)
        
        companies = [
            CompanyData(
                name=f"Company {i}",
                domain=f"company{i}.com",
                product_url=f"https://company{i}.com",
                description=f"Description for company {i}",
                launch_date=datetime(2024, 1, 1)
            )
            for i in range(10)
        ]
        
        def memory_intensive_function(company: CompanyData) -> List[Prospect]:
            # Create some temporary data
            temp_data = [i for i in range(1000)]
            time.sleep(0.01)
            return []
        
        initial_memory = processor.get_resource_usage().memory_mb
        results = processor.process_companies_parallel(companies, memory_intensive_function)
        final_memory = processor.get_resource_usage().memory_mb
        
        memory_increase = final_memory - initial_memory
        
        assert len(results) == len(companies)
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100
        
        processor.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])