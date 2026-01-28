"""Cache management module for K-line data."""

import time
from typing import Dict, List, Optional
from market_data_layer.models import KlineData, CacheEntry
from market_data_layer.exceptions import CacheError


class CacheManager:
    """Manager for caching K-line data with LRU eviction and TTL expiration.
    
    This cache manager implements:
    - LRU (Least Recently Used) eviction strategy
    - TTL (Time To Live) expiration mechanism
    - Maximum cache size limit (1000 entries)
    - Cache key generation based on symbol, interval, and time range
    """
    
    # Maximum number of cache entries
    MAX_CACHE_SIZE = 1000
    
    # Default TTL in milliseconds (24 hours)
    DEFAULT_TTL = 24 * 60 * 60 * 1000
    
    def __init__(self, max_size: int = MAX_CACHE_SIZE, default_ttl: int = DEFAULT_TTL):
        """Initialize the cache manager.
        
        Args:
            max_size: Maximum number of cache entries (default: 1000)
            default_ttl: Default time to live in milliseconds (default: 24 hours)
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
    
    def get(self, key: str) -> Optional[List[KlineData]]:
        """Retrieve data from cache.
        
        Args:
            key: Cache key in format "{symbol}:{interval}:{startTime}:{endTime}"
            
        Returns:
            List of KlineData if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        
        # Check if entry has expired
        current_time = int(time.time() * 1000)  # Current time in milliseconds
        if current_time - entry.createdAt > entry.ttl:
            # Entry has expired, remove it
            del self._cache[key]
            return None
        
        # Update access information for LRU
        entry.accessCount += 1
        entry.lastAccessTime = current_time
        
        return entry.data
    
    def set(self, key: str, value: List[KlineData], ttl: Optional[int] = None) -> None:
        """Store data in cache.
        
        Args:
            key: Cache key in format "{symbol}:{interval}:{startTime}:{endTime}"
            value: List of KlineData to cache
            ttl: Time to live in milliseconds (default: DEFAULT_TTL)
            
        Raises:
            CacheError: If cache operation fails
        """
        if ttl is None:
            ttl = self.default_ttl
        
        try:
            current_time = int(time.time() * 1000)  # Current time in milliseconds
            
            # If cache is at max size, evict LRU entry
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # Create and store cache entry
            entry = CacheEntry(
                data=value,
                createdAt=current_time,
                ttl=ttl,
                accessCount=1,
                lastAccessTime=current_time,
            )
            
            self._cache[key] = entry
        except Exception as e:
            raise CacheError(f"Failed to set cache entry: {str(e)}")
    
    def delete(self, key: str) -> None:
        """Delete a cache entry.
        
        Args:
            key: Cache key to delete
        """
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
    
    def _evict_lru(self) -> None:
        """Evict the least recently used cache entry.
        
        This method finds the entry with the smallest lastAccessTime
        and removes it from the cache.
        """
        if not self._cache:
            return
        
        # Find the entry with the smallest lastAccessTime
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].lastAccessTime)
        del self._cache[lru_key]
    
    def get_cache_size(self) -> int:
        """Get the current number of cache entries.
        
        Returns:
            Number of entries in the cache
        """
        return len(self._cache)
    
    def get_cache_info(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
        }
    
    @staticmethod
    def generate_key(symbol: str, interval: str, start_time: int, end_time: int) -> str:
        """Generate a cache key from query parameters.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            interval: Time interval (e.g., "1h")
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            Cache key in format "{symbol}:{interval}:{startTime}:{endTime}"
        """
        return f"{symbol}:{interval}:{start_time}:{end_time}"
