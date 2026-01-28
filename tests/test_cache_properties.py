"""Property-based tests for the CacheManager.

**Feature: market-data-layer**

These tests verify the correctness properties of the CacheManager
using property-based testing with Hypothesis.
"""

from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
import time
from market_data_layer.models import KlineData
from market_data_layer.cache import CacheManager


@composite
def valid_kline_list(draw, min_size=1, max_size=100):
    """Generate a list of valid K-line data."""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    klines = []
    for i in range(size):
        price1 = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
        price2 = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
        high = max(price1, price2)
        low = min(price1, price2)
        
        kline = KlineData(
            timestamp=1609459200000 + i * 60000,
            open=draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False)),
            high=high,
            low=low,
            close=draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False)),
            volume=draw(st.floats(min_value=0.0, max_value=999_999_999.0, allow_nan=False, allow_infinity=False)),
        )
        klines.append(kline)
    
    return klines


class TestCacheProperty5:
    """Property 5: 数据缓存后可被检索
    
    **Validates: Requirements 4.1**
    
    For any K-line data that is successfully cached, retrieving it with the same
    key should return the same data.
    """
    
    @given(valid_kline_list(), st.text(min_size=1, max_size=100))
    def test_property_5_cached_data_retrievable(self, klines, key):
        """Test that cached data can be retrieved.
        
        For any K-line data that is cached, retrieving it should return the same data.
        """
        cache = CacheManager()
        
        # Cache the data
        cache.set(key, klines)
        
        # Retrieve the data
        retrieved = cache.get(key)
        
        # Should return the same data
        assert retrieved is not None
        assert len(retrieved) == len(klines)
        assert retrieved == klines


class TestCacheProperty6:
    """Property 6: 缓存命中返回相同数据
    
    **Validates: Requirements 4.2**
    
    For any cached K-line data, multiple retrievals should return the same data
    without re-fetching from the data source.
    """
    
    @given(valid_kline_list(), st.text(min_size=1, max_size=100))
    def test_property_6_cache_hit_returns_same_data(self, klines, key):
        """Test that cache hits return the same data.
        
        For any cached data, multiple retrievals should return identical data.
        """
        cache = CacheManager()
        
        # Cache the data
        cache.set(key, klines)
        
        # Retrieve multiple times
        retrieved1 = cache.get(key)
        retrieved2 = cache.get(key)
        retrieved3 = cache.get(key)
        
        # All retrievals should return the same data
        assert retrieved1 == retrieved2
        assert retrieved2 == retrieved3
        assert retrieved1 == klines


class TestCacheProperty7:
    """Property 7: 缓存过期后更新
    
    **Validates: Requirements 4.3**
    
    For any cache entry with a TTL, after the TTL expires, the entry should be
    removed and subsequent retrievals should return None.
    """
    
    @given(valid_kline_list(), st.text(min_size=1, max_size=100))
    def test_property_7_ttl_expiration(self, klines, key):
        """Test that cache entries expire after TTL.
        
        For any cache entry with TTL, after expiration, it should be removed.
        """
        # Create cache with short TTL
        cache = CacheManager(default_ttl=50)  # 50ms TTL
        
        # Cache the data
        cache.set(key, klines, ttl=50)
        
        # Should be available immediately
        assert cache.get(key) is not None
        
        # Wait for TTL to expire
        time.sleep(0.1)
        
        # Should be expired
        assert cache.get(key) is None


class TestCacheProperty8:
    """Property 8: LRU淘汰策略
    
    **Validates: Requirements 4.4**
    
    For any cache at maximum capacity, when a new entry is added, the least
    recently used entry should be evicted, not the most recently used.
    """
    
    @given(st.lists(valid_kline_list(min_size=1, max_size=10), min_size=2, max_size=5))
    def test_property_8_lru_eviction(self, kline_lists):
        """Test that LRU eviction removes least recently used entries.
        
        For any cache at max capacity, adding a new entry should evict the LRU entry.
        """
        # Create cache with small max size
        cache = CacheManager(max_size=len(kline_lists), default_ttl=60000)
        
        # Add entries
        keys = [f"key_{i}" for i in range(len(kline_lists))]
        for i, (key, klines) in enumerate(zip(keys, kline_lists)):
            cache.set(key, klines)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Cache should be full
        assert cache.get_cache_size() == len(kline_lists)
        
        # Access the first key to make it recently used
        cache.get(keys[0])
        time.sleep(0.01)
        
        # Add a new entry
        new_key = "new_key"
        new_klines = kline_lists[0]
        cache.set(new_key, new_klines)
        
        # Cache should still be at max size
        assert cache.get_cache_size() == len(kline_lists)
        
        # The first key should still be there (it was accessed)
        assert cache.get(keys[0]) is not None
        
        # The second key should be evicted (it was least recently used)
        assert cache.get(keys[1]) is None


class TestCachePropertyCombined:
    """Combined property tests for cache operations."""
    
    @given(valid_kline_list(), st.text(min_size=1, max_size=100))
    def test_property_combined_set_get_delete(self, klines, key):
        """Test combined set, get, and delete operations.
        
        For any cache operation sequence, the cache should maintain consistency.
        """
        cache = CacheManager()
        
        # Initially, key should not exist
        assert cache.get(key) is None
        
        # After set, key should exist
        cache.set(key, klines)
        assert cache.get(key) is not None
        
        # After delete, key should not exist
        cache.delete(key)
        assert cache.get(key) is None
    
    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10, unique=True))
    def test_property_combined_multiple_keys(self, keys):
        """Test cache with multiple keys.
        
        For any set of keys, each key should maintain its own data independently.
        """
        cache = CacheManager()
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        # Set data for each key
        for key in keys:
            cache.set(key, [kline])
        
        # Verify each key has its data
        for key in keys:
            retrieved = cache.get(key)
            assert retrieved is not None
            assert len(retrieved) == 1
            assert retrieved[0] == kline
        
        # Cache size should match number of keys
        assert cache.get_cache_size() == len(keys)
    
    @given(valid_kline_list(), st.text(min_size=1, max_size=100))
    def test_property_combined_clear_operation(self, klines, key):
        """Test that clear operation removes all entries.
        
        For any cache state, clear should remove all entries.
        """
        cache = CacheManager()
        
        # Add multiple entries
        cache.set(key, klines)
        cache.set(key + "_2", klines)
        cache.set(key + "_3", klines)
        
        assert cache.get_cache_size() == 3
        
        # Clear cache
        cache.clear()
        
        # All entries should be gone
        assert cache.get_cache_size() == 0
        assert cache.get(key) is None
        assert cache.get(key + "_2") is None
        assert cache.get(key + "_3") is None
