"""Tests for the CacheManager."""

import pytest
import time
from market_data_layer.models import KlineData
from market_data_layer.cache import CacheManager
from market_data_layer.exceptions import CacheError


class TestCacheManagerBasic:
    """Basic tests for CacheManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
    
    def test_cache_manager_initialization(self):
        """Test CacheManager initialization."""
        assert self.cache.max_size == CacheManager.MAX_CACHE_SIZE
        assert self.cache.default_ttl == CacheManager.DEFAULT_TTL
        assert self.cache.get_cache_size() == 0
    
    def test_cache_manager_custom_initialization(self):
        """Test CacheManager with custom parameters."""
        cache = CacheManager(max_size=100, default_ttl=3600000)
        
        assert cache.max_size == 100
        assert cache.default_ttl == 3600000
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        key = CacheManager.generate_key("BTC/USDT", "1h", 1000, 2000)
        
        assert key == "BTC/USDT:1h:1000:2000"
    
    def test_cache_info(self):
        """Test getting cache info."""
        info = self.cache.get_cache_info()
        
        assert "size" in info
        assert "max_size" in info
        assert "default_ttl" in info
        assert info["size"] == 0
        assert info["max_size"] == CacheManager.MAX_CACHE_SIZE


class TestCacheSetAndGet:
    """Tests for cache set and get operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_set_and_get_single_entry(self):
        """Test setting and getting a single cache entry."""
        key = "BTC/USDT:1h:1000:2000"
        data = [self.kline]
        
        self.cache.set(key, data)
        result = self.cache.get(key)
        
        assert result is not None
        assert len(result) == 1
        assert result[0] == self.kline
    
    def test_get_nonexistent_entry(self):
        """Test getting a non-existent cache entry."""
        result = self.cache.get("nonexistent:key")
        
        assert result is None
    
    def test_set_multiple_entries(self):
        """Test setting multiple cache entries."""
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 60000,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + i,
            )
            for i in range(5)
        ]
        
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, klines)
        result = self.cache.get(key)
        
        assert result is not None
        assert len(result) == 5
        assert result == klines
    
    def test_set_empty_list(self):
        """Test setting an empty list."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [])
        result = self.cache.get(key)
        
        assert result is not None
        assert len(result) == 0
    
    def test_cache_size_increases(self):
        """Test that cache size increases when entries are added."""
        assert self.cache.get_cache_size() == 0
        
        self.cache.set("key1", [self.kline])
        assert self.cache.get_cache_size() == 1
        
        self.cache.set("key2", [self.kline])
        assert self.cache.get_cache_size() == 2


class TestCacheDelete:
    """Tests for cache delete operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_delete_existing_entry(self):
        """Test deleting an existing cache entry."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [self.kline])
        
        assert self.cache.get(key) is not None
        
        self.cache.delete(key)
        
        assert self.cache.get(key) is None
    
    def test_delete_nonexistent_entry(self):
        """Test deleting a non-existent entry (should not raise error)."""
        self.cache.delete("nonexistent:key")
        
        assert self.cache.get_cache_size() == 0
    
    def test_delete_reduces_cache_size(self):
        """Test that delete reduces cache size."""
        key1 = "key1"
        key2 = "key2"
        
        self.cache.set(key1, [self.kline])
        self.cache.set(key2, [self.kline])
        
        assert self.cache.get_cache_size() == 2
        
        self.cache.delete(key1)
        
        assert self.cache.get_cache_size() == 1


class TestCacheClear:
    """Tests for cache clear operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_clear_empty_cache(self):
        """Test clearing an empty cache."""
        self.cache.clear()
        
        assert self.cache.get_cache_size() == 0
    
    def test_clear_non_empty_cache(self):
        """Test clearing a non-empty cache."""
        self.cache.set("key1", [self.kline])
        self.cache.set("key2", [self.kline])
        
        assert self.cache.get_cache_size() == 2
        
        self.cache.clear()
        
        assert self.cache.get_cache_size() == 0
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None


class TestCacheTTL:
    """Tests for cache TTL (Time To Live) expiration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create cache with very short TTL for testing
        self.cache = CacheManager(default_ttl=100)  # 100ms TTL
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [self.kline], ttl=100)  # 100ms TTL
        
        # Entry should be available immediately
        assert self.cache.get(key) is not None
        
        # Wait for TTL to expire
        time.sleep(0.15)
        
        # Entry should be expired
        assert self.cache.get(key) is None
    
    def test_custom_ttl(self):
        """Test setting custom TTL."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [self.kline], ttl=1000)  # 1 second TTL
        
        # Entry should be available
        assert self.cache.get(key) is not None
    
    def test_default_ttl(self):
        """Test using default TTL."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [self.kline])  # Use default TTL
        
        # Entry should be available
        assert self.cache.get(key) is not None


class TestCacheLRU:
    """Tests for LRU (Least Recently Used) eviction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create cache with small max size and long TTL for testing
        self.cache = CacheManager(max_size=3, default_ttl=60000)  # 60 second TTL
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_lru_eviction_when_full(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size with delays to ensure different timestamps
        self.cache.set("key1", [self.kline])
        time.sleep(0.01)
        self.cache.set("key2", [self.kline])
        time.sleep(0.01)
        self.cache.set("key3", [self.kline])
        
        assert self.cache.get_cache_size() == 3
        
        # Access key1 to make it recently used
        self.cache.get("key1")
        
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        
        # Add new entry, should evict key2 (least recently used)
        self.cache.set("key4", [self.kline])
        
        assert self.cache.get_cache_size() == 3
        assert self.cache.get("key1") is not None
        assert self.cache.get("key2") is None
        assert self.cache.get("key3") is not None
        assert self.cache.get("key4") is not None
    
    def test_lru_eviction_order(self):
        """Test that LRU eviction removes the least recently used entry."""
        # Fill cache
        self.cache.set("key1", [self.kline])
        time.sleep(0.01)
        self.cache.set("key2", [self.kline])
        time.sleep(0.01)
        self.cache.set("key3", [self.kline])
        
        # key1 is the least recently used
        # Add new entry, should evict key1
        self.cache.set("key4", [self.kline])
        
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is not None
        assert self.cache.get("key3") is not None
        assert self.cache.get("key4") is not None
    
    def test_lru_access_updates_timestamp(self):
        """Test that accessing an entry updates its last access time."""
        self.cache.set("key1", [self.kline])
        time.sleep(0.01)
        self.cache.set("key2", [self.kline])
        time.sleep(0.01)
        self.cache.set("key3", [self.kline])
        
        # Access key1 to make it recently used
        self.cache.get("key1")
        time.sleep(0.01)
        
        # Add new entry, should evict key2 (not key1)
        self.cache.set("key4", [self.kline])
        
        assert self.cache.get("key1") is not None
        assert self.cache.get("key2") is None
        assert self.cache.get("key3") is not None
        assert self.cache.get("key4") is not None


class TestCacheAccessCount:
    """Tests for cache access count tracking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
        self.kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
    
    def test_access_count_increments(self):
        """Test that access count increments on each get."""
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, [self.kline])
        
        # Get the entry multiple times
        self.cache.get(key)
        self.cache.get(key)
        self.cache.get(key)
        
        # Access count should be 4 (1 from set + 3 from get)
        entry = self.cache._cache[key]
        assert entry.accessCount == 4


class TestCacheEdgeCases:
    """Tests for edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = CacheManager()
    
    def test_cache_with_large_data(self):
        """Test caching large amounts of data."""
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 60000,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + i,
            )
            for i in range(1000)
        ]
        
        key = "BTC/USDT:1h:1000:2000"
        self.cache.set(key, klines)
        result = self.cache.get(key)
        
        assert len(result) == 1000
        assert result == klines
    
    def test_cache_with_special_characters_in_key(self):
        """Test cache with special characters in key."""
        key = "BTC/USDT:1h:1000:2000"
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        self.cache.set(key, [kline])
        result = self.cache.get(key)
        
        assert result is not None
        assert len(result) == 1
