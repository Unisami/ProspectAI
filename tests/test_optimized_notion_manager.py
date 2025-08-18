#!/usr/bin/env python3
"""
Performance tests for the optimized Notion manager.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List

from services.notion_manager import OptimizedNotionDataManager, NotionDataManager, ConnectionPoolStats
from models.data_models import Prospect, ProspectStatus


class TestOptimizedNotionManager:
    """Test optimized Notion manager functionality."""
    
    @pytest.fixture
    def sample_prospects(self):
        """Create sample prospect data for testing."""
        return [
            Prospect(
                name=f"Test Person {i}",
                role="Software Engineer",
                company=f"Test Company {i}",
                email=f"test{i}@company.com",
                linkedin_url=f"https://linkedin.com/in/test{i}",
                created_at=datetime.now()
            )
            for i in range(5)
        ]
    
    def test_optimized_manager_initialization(self, mock_config, mock_notion_client):
        """Test optimized manager initialization."""
        manager = OptimizedNotionDataManager(
            mock_config,
            enable_caching=True,
            max_connections=3,
            batch_size=5
        )
        
        assert manager.max_connections == 3
        assert manager.batch_size == 5
        assert manager.enable_caching is True
        assert manager.cache is not None
        assert manager.connection_pool is not None
        
        manager.shutdown()
    
    def test_batch_prospect_storage(self, mock_config, mock_notion_client, sample_prospects):
        """Test batch prospect storage functionality."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=False)
        
        # Mock successful batch creation
        mock_notion_client.pages.create.return_value = {"id": "test_page_id"}
        
        results = manager.store_prospects_batch(sample_prospects)
        
        assert len(results) == len(sample_prospects)
        assert all(result == "test_page_id" for result in results if result)
        assert mock_notion_client.pages.create.call_count == len(sample_prospects)
        
        manager.shutdown()
    
    def test_batch_prospect_updates(self, mock_config, mock_notion_client):
        """Test batch prospect updates functionality."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=False)
        
        updates = [
            {
                'prospect_id': f'prospect_{i}',
                'properties': {'Status': {'select': {'name': 'Contacted'}}}
            }
            for i in range(3)
        ]
        
        results = manager.update_prospects_batch(updates)
        
        assert len(results) == len(updates)
        assert all(result for result in results)
        
        manager.shutdown()
    
    def test_caching_functionality(self, mock_config, mock_notion_client):
        """Test caching functionality."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=True)
        
        # Mock query response
        mock_response = {
            "results": [
                {
                    "id": "test_id",
                    "properties": {
                        "Name": {"title": [{"text": {"content": "Test Person"}}]},
                        "Role": {"rich_text": [{"text": {"content": "Engineer"}}]},
                        "Company": {"rich_text": [{"text": {"content": "Test Company"}}]},
                        "Contacted": {"checkbox": False},
                        "Status": {"select": {"name": "Not Contacted"}},
                        "Added Date": {"date": {"start": "2024-01-01T00:00:00.000Z"}}
                    }
                }
            ],
            "has_more": False
        }
        mock_notion_client.databases.query.return_value = mock_response
        
        # First call should hit the API
        prospects1 = manager.get_prospects_cached()
        assert len(prospects1) == 1
        assert mock_notion_client.databases.query.call_count == 1
        
        # Second call should use cache
        prospects2 = manager.get_prospects_cached()
        assert len(prospects2) == 1
        assert mock_notion_client.databases.query.call_count == 1  # No additional API call
        
        # Force refresh should hit API again
        prospects3 = manager.get_prospects_cached(force_refresh=True)
        assert len(prospects3) == 1
        assert mock_notion_client.databases.query.call_count == 2
        
        manager.shutdown()
    
    def test_bulk_email_status_update(self, mock_config, mock_notion_client):
        """Test bulk email status updates."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=False)
        
        updates = [
            {
                'prospect_id': f'prospect_{i}',
                'email_status': 'Sent',
                'email_id': f'email_{i}',
                'email_subject': f'Subject {i}'
            }
            for i in range(5)
        ]
        
        success_count = manager.bulk_update_email_status(updates)
        
        assert success_count == len(updates)
        assert mock_notion_client.pages.update.call_count == len(updates)
        
        manager.shutdown()
    
    def test_performance_monitoring(self, mock_config, mock_notion_client):
        """Test performance monitoring functionality."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=False)
        
        # Simulate some operations
        mock_notion_client.databases.query.return_value = {
            "results": [],
            "has_more": False
        }
        
        # Execute some queries
        for _ in range(3):
            manager._execute_single_query({"database_id": "test"})
        
        stats = manager.get_performance_stats()
        
        assert isinstance(stats, ConnectionPoolStats)
        assert stats.total_requests == 3
        assert stats.failed_requests == 0
        assert stats.avg_response_time > 0
        
        manager.shutdown()
    
    def test_connection_pool_utilization(self, mock_config, mock_notion_client):
        """Test connection pool utilization."""
        manager = OptimizedNotionDataManager(
            mock_config,
            enable_caching=False,
            max_connections=2
        )
        
        # Mock slow API response
        def slow_query(*args, **kwargs):
            time.sleep(0.05)  # 50ms delay per call
            return {"results": [], "has_more": False}
        
        mock_notion_client.databases.query.side_effect = slow_query
        
        # Submit multiple concurrent queries using the manager's connection pool
        start_time = time.time()
        
        # Use the manager's connection pool directly
        futures = []
        for _ in range(4):
            future = manager.connection_pool.submit(
                manager._execute_direct_query, {"database_id": "test"}
            )
            futures.append(future)
        
        # Wait for all to complete
        for future in futures:
            future.result()
        
        duration = time.time() - start_time
        
        # With 2 connections and 4 queries taking 0.05s each,
        # total time should be around 0.1s (2 batches of 2 parallel queries)
        assert duration < 0.15  # Allow some overhead
        assert duration > 0.08  # Should take at least 2 batches
        
        # Verify all queries were executed
        assert mock_notion_client.databases.query.call_count == 4
        
        manager.shutdown()
    
    def test_cached_company_lookup(self, mock_config, mock_notion_client):
        """Test cached company lookup performance."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=True)
        
        # Mock response with company data
        mock_response = {
            "results": [
                {
                    "properties": {
                        "Company": {"rich_text": [{"text": {"content": f"Company {i}"}}]}
                    }
                }
                for i in range(10)
            ],
            "has_more": False
        }
        mock_notion_client.databases.query.return_value = mock_response
        
        # First call should hit API
        companies1 = manager.get_processed_companies_cached()
        assert len(companies1) == 10
        assert mock_notion_client.databases.query.call_count == 1
        
        # Second call should use cache
        companies2 = manager.get_processed_companies_cached()
        assert len(companies2) == 10
        assert mock_notion_client.databases.query.call_count == 1  # No additional call
        
        manager.shutdown()
    
    def test_error_handling_in_batch_operations(self, mock_config, mock_notion_client, sample_prospects):
        """Test error handling in batch operations."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=False)
        
        # Mock some failures
        def create_with_failures(*args, **kwargs):
            # Fail every other call
            if mock_notion_client.pages.create.call_count % 2 == 0:
                raise Exception("Simulated API error")
            return {"id": "test_page_id"}
        
        mock_notion_client.pages.create.side_effect = create_with_failures
        
        results = manager.store_prospects_batch(sample_prospects)
        
        # Should have some successes and some failures (None)
        assert len(results) == len(sample_prospects)
        successes = [r for r in results if r is not None]
        failures = [r for r in results if r is None]
        
        assert len(successes) > 0
        assert len(failures) > 0
        
        manager.shutdown()
    
    def test_graceful_shutdown(self, mock_config, mock_notion_client):
        """Test graceful shutdown functionality."""
        manager = OptimizedNotionDataManager(mock_config, enable_caching=True)
        
        # Verify components are initialized
        assert manager.connection_pool is not None
        assert manager.batch_processor_thread is not None
        assert manager.cache is not None
        
        # Shutdown should complete without errors
        manager.shutdown()
        
        # Verify cleanup
        assert not manager.batch_processing_enabled


class TestBackwardCompatibility:
    """Test backward compatibility wrapper."""
    
    def test_backward_compatible_interface(self, mock_config, mock_notion_client):
        """Test that the backward compatible interface works."""
        manager = NotionDataManager(mock_config)
        
        # Test single prospect storage
        prospect = Prospect(
            name="Test Person",
            role="Engineer",
            company="Test Company",
            created_at=datetime.now()
        )
        
        prospect_id = manager.store_prospect(prospect)
        assert prospect_id == "test_page_id"
        
        # Test email status update
        success = manager.update_email_status(
            "test_id",
            "Sent",
            email_id="email_123",
            email_subject="Test Subject"
        )
        assert success is True
        
        # Test get prospects
        prospects = manager.get_prospects()
        assert isinstance(prospects, list)
        
        # Test get processed companies
        companies = manager.get_processed_company_names()
        assert isinstance(companies, list)
        
        manager.shutdown()


class TestPerformanceRegression:
    """Performance regression tests."""
    
    @pytest.fixture
    # Using shared mock_config fixture from conftest.py
    def test_batch_vs_individual_performance(self, mock_config):
        """Test that batch operations are faster than individual operations."""
        with patch('services.notion_manager.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock API delay
            def slow_create(*args, **kwargs):
                time.sleep(0.01)  # 10ms delay per call
                return {"id": "test_page_id"}
            
            mock_client.pages.create.side_effect = slow_create
            
            manager = OptimizedNotionDataManager(
                mock_config,
                enable_caching=False,
                max_connections=3
            )
            
            # Create test prospects
            prospects = [
                Prospect(
                    name=f"Person {i}",
                    role="Engineer",
                    company=f"Company {i}",
                    created_at=datetime.now()
                )
                for i in range(10)
            ]
            
            # Test batch operation
            start_time = time.time()
            batch_results = manager.store_prospects_batch(prospects)
            batch_duration = time.time() - start_time
            
            assert len(batch_results) == len(prospects)
            
            # Batch should be faster due to parallelization
            # With 3 connections and 10 prospects, should take ~4 batches * 10ms = ~40ms
            # Plus overhead, should be well under 100ms
            assert batch_duration < 0.1
            
            manager.shutdown()
    
    def test_caching_performance_improvement(self, mock_config):
        """Test that caching improves performance for repeated queries."""
        with patch('services.notion_manager.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Mock slow query
            def slow_query(*args, **kwargs):
                time.sleep(0.05)  # 50ms delay
                return {
                    "results": [
                        {
                            "id": "test_id",
                            "properties": {
                                "Name": {"title": [{"text": {"content": "Test"}}]},
                                "Role": {"rich_text": [{"text": {"content": "Engineer"}}]},
                                "Company": {"rich_text": [{"text": {"content": "Company"}}]},
                                "Contacted": {"checkbox": False},
                                "Status": {"select": {"name": "Not Contacted"}},
                                "Added Date": {"date": {"start": "2024-01-01T00:00:00.000Z"}}
                            }
                        }
                    ],
                    "has_more": False
                }
            
            mock_client.databases.query.side_effect = slow_query
            
            manager = OptimizedNotionDataManager(mock_config, enable_caching=True)
            
            # First call (should be slow)
            start_time = time.time()
            prospects1 = manager.get_prospects_cached()
            first_duration = time.time() - start_time
            
            # Second call (should be fast due to caching)
            start_time = time.time()
            prospects2 = manager.get_prospects_cached()
            second_duration = time.time() - start_time
            
            assert len(prospects1) == 1
            assert len(prospects2) == 1
            assert first_duration > 0.04  # Should take at least 40ms
            assert second_duration < 0.01  # Should be very fast (cached)
            
            # Verify only one API call was made
            assert mock_client.databases.query.call_count == 1
            
            manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])