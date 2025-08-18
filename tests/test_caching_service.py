#!/usr/bin/env python3
"""
Unit tests for the caching service.
"""

import pytest
import tempfile
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from services.caching_service import (
    CachingService, CacheEntry, CacheStats, 
    MemoryCacheBackend, PersistentCacheBackend
)


class TestCacheEntry:
    """Test CacheEntry functionality."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and basic properties."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
            expires_at=None
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.access_count == 0
        assert entry.last_accessed is None
        assert not entry.is_expired()
        assert entry.is_valid()
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration logic."""
        # Create expired entry
        expired_entry = CacheEntry(
            key="expired",
            value="value",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        assert expired_entry.is_expired()
        assert not expired_entry.is_valid()
        
        # Create non-expired entry
        valid_entry = CacheEntry(
            key="valid",
            value="value",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert not valid_entry.is_expired()
        assert valid_entry.is_valid()
    
    def test_cache_entry_touch(self):
        """Test cache entry access tracking."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=datetime.now(),
            expires_at=None
        )
        
        assert entry.access_count == 0
        assert entry.last_accessed is None
        
        entry.touch()
        
        assert entry.access_count == 1
        assert entry.last_accessed is not None
        
        entry.touch()
        assert entry.access_count == 2


class TestCacheStats:
    """Test CacheStats functionality."""
    
    def test_cache_stats_creation(self):
        """Test cache stats creation and properties."""
        stats = CacheStats()
        
        assert stats.total_entries == 0
        assert stats.memory_usage_bytes == 0
        assert stats.hit_count == 0
        assert stats.miss_count == 0
        assert stats.hit_rate == 0.0
        assert stats.memory_usage_mb == 0.0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hit_count=7, miss_count=3)
        assert stats.hit_rate == 0.7
        
        stats = CacheStats(hit_count=0, miss_count=0)
        assert stats.hit_rate == 0.0
    
    def test_memory_usage_conversion(self):
        """Test memory usage conversion to MB."""
        stats = CacheStats(memory_usage_bytes=1024 * 1024 * 5)  # 5 MB
        assert stats.memory_usage_mb == 5.0


class TestMemoryCacheBackend:
    """Test MemoryCacheBackend functionality."""
    
    def test_memory_backend_basic_operations(self):
        """Test basic get/set/delete operations."""
        backend = MemoryCacheBackend(max_size=10, max_memory_mb=1)
        
        # Test set and get
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now(),
            expires_at=None
        )
        
        assert backend.set("test_key", entry)
        retrieved = backend.get("test_key")
        
        assert retrieved is not None
        assert retrieved.value == "test_value"
        assert retrieved.access_count == 1  # Should be touched on get
        
        # Test delete
        assert backend.delete("test_key")
        assert backend.get("test_key") is None
        assert not backend.delete("nonexistent")
    
    def test_memory_backend_expiration(self):
        """Test automatic expiration handling."""
        backend = MemoryCacheBackend()
        
        # Create expired entry
        expired_entry = CacheEntry(
            key="expired",
            value="value",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        
        backend.set("expired", expired_entry)
        
        # Should return None and remove expired entry
        assert backend.get("expired") is None
        assert "expired" not in backend.cache
    
    def test_memory_backend_lru_eviction(self):
        """Test LRU eviction when max size is reached."""
        backend = MemoryCacheBackend(max_size=2, max_memory_mb=100)
        
        # Add entries up to limit
        for i in range(3):
            entry = CacheEntry(
                key=f"key_{i}",
                value=f"value_{i}",
                created_at=datetime.now(),
                expires_at=None
            )
            backend.set(f"key_{i}", entry)
        
        # Should only have 2 entries (LRU evicted)
        assert len(backend.cache) == 2
        assert backend.get("key_0") is None  # First entry should be evicted
        assert backend.get("key_1") is not None
        assert backend.get("key_2") is not None
    
    def test_memory_backend_clear(self):
        """Test clearing all entries."""
        backend = MemoryCacheBackend()
        
        # Add some entries
        for i in range(3):
            entry = CacheEntry(
                key=f"key_{i}",
                value=f"value_{i}",
                created_at=datetime.now(),
                expires_at=None
            )
            backend.set(f"key_{i}", entry)
        
        assert len(backend.cache) == 3
        assert backend.clear()
        assert len(backend.cache) == 0
    
    def test_memory_backend_keys(self):
        """Test getting all keys."""
        backend = MemoryCacheBackend()
        
        keys = ["key_1", "key_2", "key_3"]
        for key in keys:
            entry = CacheEntry(
                key=key,
                value=f"value_{key}",
                created_at=datetime.now(),
                expires_at=None
            )
            backend.set(key, entry)
        
        retrieved_keys = backend.keys()
        assert set(retrieved_keys) == set(keys)


class TestPersistentCacheBackend:
    """Test PersistentCacheBackend functionality."""
    
    def test_persistent_backend_basic_operations(self):
        """Test basic file-based operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = PersistentCacheBackend(temp_dir)
            
            # Test set and get
            entry = CacheEntry(
                key="test_key",
                value={"data": "test_value"},
                created_at=datetime.now(),
                expires_at=None
            )
            
            assert backend.set("test_key", entry)
            retrieved = backend.get("test_key")
            
            assert retrieved is not None
            assert retrieved.value == {"data": "test_value"}
            assert retrieved.access_count == 1  # Should be touched on get
            
            # Test delete
            assert backend.delete("test_key")
            assert backend.get("test_key") is None
    
    def test_persistent_backend_expiration(self):
        """Test file-based expiration handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = PersistentCacheBackend(temp_dir)
            
            # Create expired entry
            expired_entry = CacheEntry(
                key="expired",
                value="value",
                created_at=datetime.now() - timedelta(hours=2),
                expires_at=datetime.now() - timedelta(hours=1)
            )
            
            backend.set("expired", expired_entry)
            
            # Should return None and remove expired file
            assert backend.get("expired") is None
            
            # File should be deleted
            cache_files = list(Path(temp_dir).glob("*.cache"))
            assert len(cache_files) == 0
    
    def test_persistent_backend_corrupted_file(self):
        """Test handling of corrupted cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = PersistentCacheBackend(temp_dir)
            
            # Create a corrupted cache file with the correct hash-based name
            test_key = "corrupted"
            cache_file = backend._get_cache_file(test_key)
            cache_file.write_text("corrupted data")
            
            # Should handle gracefully and remove corrupted file
            assert backend.get(test_key) is None
            assert not cache_file.exists()
    
    def test_persistent_backend_clear(self):
        """Test clearing all cache files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = PersistentCacheBackend(temp_dir)
            
            # Add some entries
            for i in range(3):
                entry = CacheEntry(
                    key=f"key_{i}",
                    value=f"value_{i}",
                    created_at=datetime.now(),
                    expires_at=None
                )
                backend.set(f"key_{i}", entry)
            
            # Should have 3 cache files
            cache_files = list(Path(temp_dir).glob("*.cache"))
            assert len(cache_files) == 3
            
            assert backend.clear()
            
            # Should have no cache files
            cache_files = list(Path(temp_dir).glob("*.cache"))
            assert len(cache_files) == 0


class TestCachingService:
    """Test CachingService functionality."""
    
    @pytest.fixture
    def caching_service(self, mock_config):
        """Create caching service for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = CachingService(
                mock_config,
                memory_backend=True,
                persistent_backend=True,
                max_memory_entries=10,
                max_memory_mb=1,
                cache_dir=temp_dir
            )
            yield service
    
    @pytest.fixture
    def memory_only_caching_service(self, mock_config):
        """Create memory-only caching service for testing."""
        service = CachingService(
            mock_config,
            memory_backend=True,
            persistent_backend=False,
            max_memory_entries=10,
            max_memory_mb=1
        )
        yield service
    
    def test_caching_service_initialization(self, mock_config):
        """Test caching service initialization."""
        service = CachingService(
            mock_config,
            memory_backend=True,
            persistent_backend=False
        )
        
        assert 'memory' in service.backends
        assert 'persistent' not in service.backends
        assert service.backend_priority == ['memory', 'persistent']
    
    def test_basic_get_set_operations(self, caching_service):
        """Test basic get/set operations."""
        # Test set and get
        assert caching_service.set("test_key", "test_value", ttl=3600)
        
        value = caching_service.get("test_key")
        assert value == "test_value"
        
        # Test cache hit stats
        stats = caching_service.get_stats()
        assert stats.hit_count == 1
        assert stats.miss_count == 0
    
    def test_cache_miss(self, caching_service):
        """Test cache miss behavior."""
        value = caching_service.get("nonexistent_key", default="default_value")
        assert value == "default_value"
        
        # Test cache miss stats
        stats = caching_service.get_stats()
        assert stats.miss_count == 1
    
    def test_ttl_expiration(self, caching_service):
        """Test TTL expiration."""
        # Set with very short TTL
        caching_service.set("short_ttl", "value", ttl=1)
        
        # Should be available immediately
        assert caching_service.get("short_ttl") == "value"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert caching_service.get("short_ttl") is None
    
    def test_delete_operation(self, caching_service):
        """Test delete operation."""
        caching_service.set("delete_me", "value")
        assert caching_service.get("delete_me") == "value"
        
        assert caching_service.delete("delete_me")
        assert caching_service.get("delete_me") is None
    
    def test_clear_operation(self, caching_service):
        """Test clear operation."""
        # Add multiple entries
        for i in range(3):
            caching_service.set(f"key_{i}", f"value_{i}")
        
        # Verify they exist
        for i in range(3):
            assert caching_service.get(f"key_{i}") == f"value_{i}"
        
        # Clear all
        assert caching_service.clear()
        
        # Verify they're gone
        for i in range(3):
            assert caching_service.get(f"key_{i}") is None
    
    def test_get_or_set(self, caching_service):
        """Test get_or_set functionality."""
        factory_called = False
        
        def factory():
            nonlocal factory_called
            factory_called = True
            return "generated_value"
        
        # First call should generate value
        value = caching_service.get_or_set("factory_key", factory, ttl=3600)
        assert value == "generated_value"
        assert factory_called
        
        # Second call should use cached value
        factory_called = False
        value = caching_service.get_or_set("factory_key", factory, ttl=3600)
        assert value == "generated_value"
        assert not factory_called  # Factory should not be called again
    
    def test_key_normalization(self, caching_service):
        """Test key normalization."""
        # Test with problematic characters
        problematic_key = "Key With/Spaces:And*Special?Chars"
        caching_service.set(problematic_key, "value")
        
        # Should be able to retrieve with same key
        assert caching_service.get(problematic_key) == "value"
    
    def test_invalidate_pattern(self, memory_only_caching_service):
        """Test pattern-based invalidation."""
        # Set up test data
        memory_only_caching_service.set("user_123_profile", "profile_data")
        memory_only_caching_service.set("user_123_settings", "settings_data")
        memory_only_caching_service.set("user_456_profile", "other_profile")
        memory_only_caching_service.set("product_789", "product_data")
        
        # Invalidate user_123 entries
        memory_only_caching_service.invalidate_pattern("user_123_*")
        
        # Check results
        assert memory_only_caching_service.get("user_123_profile") is None
        assert memory_only_caching_service.get("user_123_settings") is None
        assert memory_only_caching_service.get("user_456_profile") == "other_profile"
        assert memory_only_caching_service.get("product_789") == "product_data"
    
    def test_cache_warming(self, caching_service):
        """Test cache warming functionality."""
        warming_config = {
            "warm_key_1": {
                "factory": lambda: "warm_value_1",
                "ttl": 3600,
                "priority": 1
            },
            "warm_key_2": {
                "factory": lambda: "warm_value_2",
                "ttl": 1800,
                "priority": 2
            }
        }
        
        caching_service.warm_cache(warming_config)
        
        # Give warming time to complete
        time.sleep(0.1)
        
        # Check that values were warmed
        assert caching_service.get("warm_key_1") == "warm_value_1"
        assert caching_service.get("warm_key_2") == "warm_value_2"
    
    def test_cleanup_expired(self, caching_service):
        """Test cleanup of expired entries."""
        # Add expired and valid entries
        caching_service.set("expired_key", "value", ttl=1)
        caching_service.set("valid_key", "value", ttl=3600)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Run cleanup
        caching_service.cleanup_expired()
        
        # Check results
        assert caching_service.get("expired_key") is None
        assert caching_service.get("valid_key") == "value"
    
    def test_backend_promotion(self, caching_service):
        """Test promotion from persistent to memory backend."""
        # Disable memory backend temporarily to force persistent storage
        memory_backend = caching_service.backends.pop('memory')
        
        # Store in persistent backend only
        caching_service.set("promote_me", "value")
        
        # Re-enable memory backend
        caching_service.backends['memory'] = memory_backend
        
        # Get should promote to memory backend
        value = caching_service.get("promote_me")
        assert value == "value"
        
        # Should now be in memory backend
        memory_entry = caching_service.backends['memory'].get("promote_me")
        assert memory_entry is not None
        assert memory_entry.value == "value"
    
    def test_context_manager(self, mock_config):
        """Test context manager functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with CachingService(mock_config, cache_dir=temp_dir) as service:
                service.set("test", "value")
                assert service.get("test") == "value"
            
            # Service should be properly cleaned up
            assert service.warming_executor._shutdown
    
    def test_concurrent_access(self, caching_service):
        """Test thread-safe concurrent access."""
        def worker(worker_id):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                caching_service.set(key, value)
                retrieved = caching_service.get(key)
                assert retrieved == value
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all data is present
        for worker_id in range(5):
            for i in range(10):
                key = f"worker_{worker_id}_key_{i}"
                expected_value = f"worker_{worker_id}_value_{i}"
                assert caching_service.get(key) == expected_value


if __name__ == "__main__":
    pytest.main([__file__])