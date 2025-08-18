#!/usr/bin/env python3
"""
Caching service for expensive operations with in-memory and persistent caching.
Provides TTL support, cache invalidation strategies, and cache warming.
"""

import pickle
import hashlib
import logging
import threading
from datetime import (
    datetime,
    timedelta
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
    Union,
    Callable,
    List
)
from dataclasses import (
    dataclass,
    asdict
)
from abc import (
    ABC,
    abstractmethod
)
import fnmatch

from concurrent.futures import ThreadPoolExecutor

from utils.base_service import BaseService




@dataclass
class CacheEntry:
    """Represents a cached entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if cache entry is valid (not expired)."""
        return not self.is_expired()
    
    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStats:
    """Cache statistics for monitoring and optimization."""
    total_entries: int = 0
    memory_usage_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    expired_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    @property
    def memory_usage_mb(self) -> float:
        """Get memory usage in MB."""
        return self.memory_usage_bytes / (1024 * 1024)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all cache keys."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: Dict[str, CacheEntry] = {}
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self.lock:
            entry = self.cache.get(key)
            if entry and entry.is_valid():
                entry.touch()
                return entry
            elif entry and entry.is_expired():
                # Remove expired entry
                del self.cache[key]
            return None
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry with eviction if needed."""
        with self.lock:
            # Calculate entry size
            entry.size_bytes = self._calculate_size(entry.value)
            
            # Check if we need to evict entries
            self._evict_if_needed(entry.size_bytes)
            
            # Store the entry
            self.cache[key] = entry
            return True
    
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            return True
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        with self.lock:
            return list(self.cache.keys())
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value."""
        try:
            return len(pickle.dumps(value))
        except Exception:
            # Fallback to string representation size
            return len(str(value).encode('utf-8'))
    
    def _evict_if_needed(self, new_entry_size: int):
        """Evict entries if cache limits are exceeded."""
        current_memory = sum(entry.size_bytes for entry in self.cache.values())
        
        # Evict by memory limit
        while (current_memory + new_entry_size > self.max_memory_bytes and 
               len(self.cache) > 0):
            self._evict_lru_entry()
            current_memory = sum(entry.size_bytes for entry in self.cache.values())
        
        # Evict by count limit
        while len(self.cache) >= self.max_size:
            self._evict_lru_entry()
    
    def _evict_lru_entry(self):
        """Evict least recently used entry."""
        if not self.cache:
            return
        
        # Find LRU entry (least recently accessed or oldest if never accessed)
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (
                self.cache[k].last_accessed or self.cache[k].created_at,
                self.cache[k].access_count
            )
        )
        
        del self.cache[lru_key]
        self.logger.debug(f"Evicted LRU cache entry: {lru_key}")


class PersistentCacheBackend(CacheBackend):
    """File-based persistent cache backend."""
    
    def __init__(self, cache_dir: Union[str, Path] = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry from file."""
        cache_file = self._get_cache_file(key)
        
        with self.lock:
            if not cache_file.exists():
                return None
            
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_valid():
                    entry.touch()
                    # Update file with new access metadata
                    with open(cache_file, 'wb') as f:
                        pickle.dump(entry, f)
                    return entry
                else:
                    # Remove expired file
                    cache_file.unlink(missing_ok=True)
                    return None
                    
            except Exception as e:
                self.logger.warning(f"Failed to load cache entry {key}: {e}")
                cache_file.unlink(missing_ok=True)
                return None
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry to file."""
        cache_file = self._get_cache_file(key)
        
        with self.lock:
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry, f)
                return True
            except Exception as e:
                self.logger.error(f"Failed to save cache entry {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete cache entry file."""
        cache_file = self._get_cache_file(key)
        
        with self.lock:
            if cache_file.exists():
                cache_file.unlink()
                return True
            return False
    
    def clear(self) -> bool:
        """Clear all cache files."""
        with self.lock:
            try:
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
                return True
            except Exception as e:
                self.logger.error(f"Failed to clear cache: {e}")
                return False
    
    def keys(self) -> List[str]:
        """Get all cache keys from files."""
        with self.lock:
            keys = []
            for cache_file in self.cache_dir.glob("*.cache"):
                # Extract key from filename (remove .cache extension)
                key = cache_file.stem
                keys.append(key)
            return keys
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        # Use hash of key to avoid filesystem issues with special characters
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def _get_cache_file_by_name(self, filename: str) -> Path:
        """Get cache file path by filename (for corrupted file test)."""
        return self.cache_dir / f"{filename}.cache"


class CachingService(BaseService):
    """
    Comprehensive caching service with multiple backends and advanced features.
    """
    
    def __init__(self, config, memory_backend: bool = True, persistent_backend: bool = True,
                 max_memory_entries: int = 1000, max_memory_mb: int = 100,
                 cache_dir: Union[str, Path] = ".cache"):
        """
        Initialize caching service.
        
        Args:
            config: Configuration object
            memory_backend: Enable in-memory caching
            persistent_backend: Enable persistent file caching
            max_memory_entries: Maximum entries in memory cache
            max_memory_mb: Maximum memory usage in MB
            cache_dir: Directory for persistent cache files
        """
        # Store initialization parameters
        self.memory_backend = memory_backend
        self.persistent_backend = persistent_backend
        self.max_memory_entries = max_memory_entries
        self.max_memory_mb = max_memory_mb
        self.cache_dir = cache_dir
        
        super().__init__(config)
    
    def _initialize_service(self) -> None:
        """Initialize service-specific components."""
        self.backends: Dict[str, CacheBackend] = {}
        self.stats = CacheStats()
        self.warming_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cache-warmer")
        
        # Initialize backends
        if self.memory_backend:
            self.backends['memory'] = MemoryCacheBackend(
                max_size=self.max_memory_entries,
                max_memory_mb=self.max_memory_mb
            )
        
        if self.persistent_backend:
            self.backends['persistent'] = PersistentCacheBackend(self.cache_dir)
        
        # Default backend priority (memory first, then persistent)
        self.backend_priority = ['memory', 'persistent']
        
        self.logger.info(f"Initialized caching service with backends: {list(self.backends.keys())}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get cached value by key.
        
        Args:
            key: Cache key
            default: Default value if not found
            
        Returns:
            Cached value or default
        """
        cache_key = self._normalize_key(key)
        
        # Try backends in priority order
        for backend_name in self.backend_priority:
            if backend_name not in self.backends:
                continue
                
            backend = self.backends[backend_name]
            entry = backend.get(cache_key)
            
            if entry is not None:
                self.stats.hit_count += 1
                self.logger.debug(f"Cache hit for key '{key}' in {backend_name} backend")
                
                # If found in non-primary backend, promote to primary
                if backend_name != self.backend_priority[0] and 'memory' in self.backends:
                    self.backends['memory'].set(cache_key, entry)
                
                return entry.value
        
        # Cache miss
        self.stats.miss_count += 1
        self.logger.debug(f"Cache miss for key '{key}'")
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set cached value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successfully cached
        """
        cache_key = self._normalize_key(key)
        
        # Create cache entry
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        entry = CacheEntry(
            key=cache_key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at
        )
        
        # Store in all available backends
        success = True
        for backend_name, backend in self.backends.items():
            try:
                if not backend.set(cache_key, entry):
                    success = False
                    self.logger.warning(f"Failed to cache key '{key}' in {backend_name} backend")
            except Exception as e:
                success = False
                self.logger.error(f"Error caching key '{key}' in {backend_name} backend: {e}")
        
        if success:
            self.stats.total_entries += 1
            self.logger.debug(f"Cached key '{key}' with TTL {ttl}")
        
        return success
    
    def delete(self, key: str) -> bool:
        """
        Delete cached value.
        
        Args:
            key: Cache key
            
        Returns:
            True if successfully deleted
        """
        cache_key = self._normalize_key(key)
        
        success = True
        for backend_name, backend in self.backends.items():
            try:
                if not backend.delete(cache_key):
                    success = False
            except Exception as e:
                success = False
                self.logger.error(f"Error deleting key '{key}' from {backend_name} backend: {e}")
        
        if success:
            self.logger.debug(f"Deleted cached key '{key}'")
        
        return success
    
    def clear(self, backend_name: Optional[str] = None) -> bool:
        """
        Clear cache entries.
        
        Args:
            backend_name: Specific backend to clear, or all if None
            
        Returns:
            True if successfully cleared
        """
        if backend_name:
            if backend_name in self.backends:
                return self.backends[backend_name].clear()
            return False
        
        # Clear all backends
        success = True
        for backend in self.backends.values():
            try:
                if not backend.clear():
                    success = False
            except Exception as e:
                success = False
                self.logger.error(f"Error clearing cache backend: {e}")
        
        if success:
            self.stats = CacheStats()  # Reset stats
            self.logger.info("Cleared all cache backends")
        
        return success
    
    def get_or_set(self, key: str, factory: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        """
        Get cached value or set it using factory function.
        
        Args:
            key: Cache key
            factory: Function to generate value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or newly generated value
        """
        # Try to get from cache first
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Generate new value
        try:
            new_value = factory()
            self.set(key, new_value, ttl)
            return new_value
        except Exception as e:
            self.logger.error(f"Error generating value for key '{key}': {e}")
            raise
    
    def warm_cache(self, warming_config: Dict[str, Dict[str, Any]]):
        """
        Warm cache with frequently accessed data.
        
        Args:
            warming_config: Dict mapping cache keys to warming configuration
                          Format: {key: {'factory': callable, 'ttl': int, 'priority': int}}
        """
        self.logger.info(f"Starting cache warming for {len(warming_config)} keys")
        
        # Sort by priority (higher priority first)
        sorted_keys = sorted(
            warming_config.keys(),
            key=lambda k: warming_config[k].get('priority', 0),
            reverse=True
        )
        
        # Submit warming tasks
        futures = []
        for key in sorted_keys:
            config = warming_config[key]
            future = self.warming_executor.submit(
                self._warm_single_key,
                key,
                config['factory'],
                config.get('ttl')
            )
            futures.append((key, future))
        
        # Wait for completion and log results
        warmed_count = 0
        for key, future in futures:
            try:
                future.result(timeout=30)  # 30 second timeout per key
                warmed_count += 1
                self.logger.debug(f"Successfully warmed cache key: {key}")
            except Exception as e:
                self.logger.warning(f"Failed to warm cache key '{key}': {e}")
        
        self.logger.info(f"Cache warming completed: {warmed_count}/{len(warming_config)} keys warmed")
    
    def _warm_single_key(self, key: str, factory: Callable[[], Any], ttl: Optional[int]):
        """Warm a single cache key."""
        try:
            value = factory()
            self.set(key, value, ttl)
        except Exception as e:
            self.logger.error(f"Error warming cache key '{key}': {e}")
            raise
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate cache keys matching a pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcard)
        """
        
        # Normalize the pattern but preserve wildcards
        # First normalize without wildcards, then restore them
        temp_pattern = pattern.replace('*', '___WILDCARD___')
        normalized_pattern = self._normalize_key(temp_pattern)
        normalized_pattern = normalized_pattern.replace('___wildcard___', '*')
        
        invalidated_count = 0
        
        for backend_name, backend in self.backends.items():
            try:
                keys = backend.keys()
                matching_keys = [key for key in keys if fnmatch.fnmatch(key, normalized_pattern)]
                
                for key in matching_keys:
                    if backend.delete(key):
                        invalidated_count += 1
                        
            except Exception as e:
                self.logger.error(f"Error invalidating pattern '{pattern}' in {backend_name}: {e}")
        
        self.logger.info(f"Invalidated {invalidated_count} cache entries matching pattern '{pattern}'")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        # Update memory usage from backends
        if 'memory' in self.backends:
            memory_backend = self.backends['memory']
            if hasattr(memory_backend, 'cache'):
                self.stats.memory_usage_bytes = sum(
                    entry.size_bytes for entry in memory_backend.cache.values()
                )
                self.stats.total_entries = len(memory_backend.cache)
        
        return self.stats
    
    def _normalize_key(self, key: str) -> str:
        """Normalize cache key to ensure consistency."""
        # Remove whitespace and convert to lowercase
        normalized = key.strip().lower()
        
        # Replace problematic characters for filesystem compatibility
        normalized = normalized.replace('/', '_').replace('\\', '_')
        normalized = normalized.replace(':', '_').replace('*', '_')
        normalized = normalized.replace('?', '_').replace('<', '_')
        normalized = normalized.replace('>', '_').replace('|', '_')
        
        return normalized
    
    def cleanup_expired(self):
        """Clean up expired cache entries."""
        cleaned_count = 0
        
        for backend_name, backend in self.backends.items():
            try:
                keys = backend.keys()
                for key in keys:
                    entry = backend.get(key)
                    if entry and entry.is_expired():
                        backend.delete(key)
                        cleaned_count += 1
                        
            except Exception as e:
                self.logger.error(f"Error cleaning expired entries in {backend_name}: {e}")
        
        if cleaned_count > 0:
            self.stats.expired_count += cleaned_count
            self.logger.info(f"Cleaned up {cleaned_count} expired cache entries")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.warming_executor.shutdown(wait=True)
