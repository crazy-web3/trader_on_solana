"""Tests for data models."""

import pytest
from market_data_layer.models import (
    KlineData,
    CacheEntry,
    ValidationResult,
    TimeInterval,
)


class TestTimeInterval:
    """Tests for TimeInterval enum."""
    
    def test_time_interval_values(self):
        """Test that all time intervals have correct values."""
        assert TimeInterval.ONE_MINUTE.value == "1m"
        assert TimeInterval.FIVE_MINUTES.value == "5m"
        assert TimeInterval.FIFTEEN_MINUTES.value == "15m"
        assert TimeInterval.ONE_HOUR.value == "1h"
        assert TimeInterval.FOUR_HOURS.value == "4h"
        assert TimeInterval.ONE_DAY.value == "1d"
        assert TimeInterval.ONE_WEEK.value == "1w"
    
    def test_time_interval_count(self):
        """Test that all required time intervals are defined."""
        intervals = list(TimeInterval)
        assert len(intervals) == 7


class TestKlineData:
    """Tests for KlineData model."""
    
    def test_kline_data_creation(self):
        """Test creating a KlineData instance."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        assert kline.timestamp == 1609459200000
        assert kline.open == 100.0
        assert kline.high == 105.0
        assert kline.low == 95.0
        assert kline.close == 102.0
        assert kline.volume == 1000.0
    
    def test_kline_data_with_zero_values(self):
        """Test creating KlineData with zero values."""
        kline = KlineData(
            timestamp=0,
            open=0.0,
            high=0.0,
            low=0.0,
            close=0.0,
            volume=0.0,
        )
        
        assert kline.timestamp == 0
        assert kline.open == 0.0
        assert kline.volume == 0.0
    
    def test_kline_data_with_large_values(self):
        """Test creating KlineData with large values."""
        kline = KlineData(
            timestamp=9999999999999,
            open=999999.99,
            high=1000000.0,
            low=999999.0,
            close=999999.99,
            volume=999999999.0,
        )
        
        assert kline.timestamp == 9999999999999
        assert kline.open == 999999.99


class TestCacheEntry:
    """Tests for CacheEntry model."""
    
    def test_cache_entry_creation(self):
        """Test creating a CacheEntry instance."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        cache_entry = CacheEntry(
            data=[kline],
            createdAt=1609459200000,
            ttl=86400000,  # 24 hours in milliseconds
            accessCount=1,
            lastAccessTime=1609459200000,
        )
        
        assert len(cache_entry.data) == 1
        assert cache_entry.data[0] == kline
        assert cache_entry.createdAt == 1609459200000
        assert cache_entry.ttl == 86400000
        assert cache_entry.accessCount == 1
        assert cache_entry.lastAccessTime == 1609459200000
    
    def test_cache_entry_default_values(self):
        """Test CacheEntry with default values."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        cache_entry = CacheEntry(
            data=[kline],
            createdAt=1609459200000,
            ttl=86400000,
        )
        
        assert cache_entry.accessCount == 0
        assert cache_entry.lastAccessTime == 0
    
    def test_cache_entry_with_multiple_klines(self):
        """Test CacheEntry with multiple K-line data."""
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 60000,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + i,
            )
            for i in range(10)
        ]
        
        cache_entry = CacheEntry(
            data=klines,
            createdAt=1609459200000,
            ttl=86400000,
        )
        
        assert len(cache_entry.data) == 10


class TestValidationResult:
    """Tests for ValidationResult model."""
    
    def test_validation_result_valid(self):
        """Test ValidationResult for valid data."""
        result = ValidationResult(isValid=True)
        
        assert result.isValid is True
        assert result.errors == []
    
    def test_validation_result_invalid(self):
        """Test ValidationResult for invalid data."""
        errors = ["high < low", "volume < 0"]
        result = ValidationResult(isValid=False, errors=errors)
        
        assert result.isValid is False
        assert result.errors == errors
        assert len(result.errors) == 2
    
    def test_validation_result_with_single_error(self):
        """Test ValidationResult with a single error."""
        result = ValidationResult(
            isValid=False,
            errors=["price is negative"],
        )
        
        assert result.isValid is False
        assert len(result.errors) == 1
        assert result.errors[0] == "price is negative"
