#!/usr/bin/env python3
"""
LinkedIn profile caching service to avoid re-scraping the same profiles.
This can provide massive performance improvements by caching successful extractions.
"""

import json
import hashlib
import time
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

from models.data_models import LinkedInProfile
from utils.logging_config import get_logger


class LinkedInProfileCache:
    """Cache for LinkedIn profile data to avoid re-scraping."""
    
    def __init__(self, cache_dir: str = ".cache/linkedin_profiles", cache_ttl_hours: int = 24):
        """
        Initialize LinkedIn profile cache.
        
        Args:
            cache_dir: Directory to store cached profiles
            cache_ttl_hours: Time-to-live for cached profiles in hours
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.logger = get_logger(__name__)
        
        # In-memory cache for frequently accessed profiles
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.max_memory_cache_size = 100
    
    def _get_cache_key(self, linkedin_url: str) -> str:
        """Generate cache key from LinkedIn URL."""
        # Normalize URL and create hash
        normalized_url = linkedin_url.lower().strip().rstrip('/')
        return hashlib.md5(normalized_url.encode()).hexdigest()
    
    def _get_cache_file(self, cache_key: str) -> Path:
        """Get cache file path for a given cache key."""
        return self.cache_dir / f"{cache_key}.json"
    
    def get_cached_profile(self, linkedin_url: str) -> Optional[LinkedInProfile]:
        """
        Get cached LinkedIn profile if available and not expired.
        
        Args:
            linkedin_url: LinkedIn profile URL
            
        Returns:
            LinkedInProfile if cached and valid, None otherwise
        """
        cache_key = self._get_cache_key(linkedin_url)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            cached_data = self.memory_cache[cache_key]
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            
            if datetime.now() - cached_time < self.cache_ttl:
                self.logger.debug(f"Found profile in memory cache: {linkedin_url}")
                return LinkedInProfile.from_dict(cached_data['profile'])
            else:
                # Remove expired entry from memory cache
                del self.memory_cache[cache_key]
        
        # Check file cache
        cache_file = self._get_cache_file(cache_key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cached_data['cached_at'])
                
                if datetime.now() - cached_time < self.cache_ttl:
                    # Add to memory cache for faster future access
                    if len(self.memory_cache) < self.max_memory_cache_size:
                        self.memory_cache[cache_key] = cached_data
                    
                    self.logger.info(f"Found cached LinkedIn profile: {linkedin_url}")
                    return LinkedInProfile.from_dict(cached_data['profile'])
                else:
                    # Remove expired cache file
                    cache_file.unlink()
                    self.logger.debug(f"Removed expired cache for: {linkedin_url}")
                    
            except (json.JSONDecodeError, KeyError, Exception) as e:
                self.logger.warning(f"Error reading cache file {cache_file}: {e}")
                # Remove corrupted cache file
                cache_file.unlink(missing_ok=True)
        
        return None
    
    def cache_profile(self, linkedin_url: str, profile: LinkedInProfile) -> None:
        """
        Cache a LinkedIn profile.
        
        Args:
            linkedin_url: LinkedIn profile URL
            profile: LinkedInProfile object to cache
        """
        cache_key = self._get_cache_key(linkedin_url)
        
        cached_data = {
            'linkedin_url': linkedin_url,
            'profile': profile.to_dict(),
            'cached_at': datetime.now().isoformat(),
            'cache_key': cache_key
        }
        
        # Save to file cache
        cache_file = self._get_cache_file(cache_key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, indent=2, ensure_ascii=False)
            
            # Add to memory cache if there's space
            if len(self.memory_cache) < self.max_memory_cache_size:
                self.memory_cache[cache_key] = cached_data
            
            self.logger.info(f"Cached LinkedIn profile: {profile.name} ({linkedin_url})")
            
        except Exception as e:
            self.logger.error(f"Error caching profile {linkedin_url}: {e}")
    
    def clear_expired_cache(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        cleared_count = 0
        current_time = datetime.now()
        
        # Clear memory cache
        expired_keys = []
        for cache_key, cached_data in self.memory_cache.items():
            cached_time = datetime.fromisoformat(cached_data['cached_at'])
            if current_time - cached_time >= self.cache_ttl:
                expired_keys.append(cache_key)
        
        for key in expired_keys:
            del self.memory_cache[key]
            cleared_count += 1
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                cached_time = datetime.fromisoformat(cached_data['cached_at'])
                if current_time - cached_time >= self.cache_ttl:
                    cache_file.unlink()
                    cleared_count += 1
                    
            except Exception as e:
                self.logger.warning(f"Error checking cache file {cache_file}: {e}")
                # Remove corrupted files
                cache_file.unlink(missing_ok=True)
                cleared_count += 1
        
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} expired cache entries")
        
        return cleared_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        file_cache_count = len(list(self.cache_dir.glob("*.json")))
        memory_cache_count = len(self.memory_cache)
        
        return {
            'file_cache_entries': file_cache_count,
            'memory_cache_entries': memory_cache_count,
            'cache_directory': str(self.cache_dir),
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600,
            'max_memory_cache_size': self.max_memory_cache_size
        }
    
    def clear_all_cache(self) -> int:
        """Clear all cache entries."""
        cleared_count = 0
        
        # Clear memory cache
        cleared_count += len(self.memory_cache)
        self.memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            cleared_count += 1
        
        self.logger.info(f"Cleared all cache entries: {cleared_count} total")
        return cleared_count


# Global cache instance
_linkedin_cache = None


def get_linkedin_cache() -> LinkedInProfileCache:
    """Get the global LinkedIn profile cache instance."""
    global _linkedin_cache
    if _linkedin_cache is None:
        _linkedin_cache = LinkedInProfileCache()
    return _linkedin_cache