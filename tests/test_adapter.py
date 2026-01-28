"""Tests for the DataSourceAdapter."""

import pytest
from market_data_layer.adapter import DataSourceAdapter, MockDataSourceAdapter
from market_data_layer.exceptions import ParameterError, DataSourceError


class TestDataSourceAdapterInterface:
    """Tests for DataSourceAdapter interface."""
    
    def test_supported_symbols(self):
        """Test that supported symbols are defined."""
        symbols = DataSourceAdapter.get_supported_symbols()
        
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "BTC/USDT" in symbols
        assert "ETH/USDT" in symbols
        assert "BNB/USDT" in symbols
        assert "SOL/USDT" in symbols
    
    def test_supported_intervals(self):
        """Test that supported intervals are defined."""
        intervals = DataSourceAdapter.get_supported_intervals()
        
        assert isinstance(intervals, list)
        assert len(intervals) == 7
        assert "1m" in intervals
        assert "5m" in intervals
        assert "15m" in intervals
        assert "1h" in intervals
        assert "4h" in intervals
        assert "1d" in intervals
        assert "1w" in intervals


class TestParameterValidation:
    """Tests for parameter validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockDataSourceAdapter()
    
    def test_validate_valid_parameters(self):
        """Test validation of valid parameters."""
        # Should not raise any exception
        self.adapter.validate_parameters(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=2000,
        )
    
    def test_validate_invalid_symbol(self):
        """Test validation of invalid symbol."""
        with pytest.raises(ParameterError) as exc_info:
            self.adapter.validate_parameters(
                symbol="INVALID/USDT",
                interval="1h",
                start_time=1000,
                end_time=2000,
            )
        
        assert "Unsupported symbol" in str(exc_info.value)
    
    def test_validate_invalid_interval(self):
        """Test validation of invalid interval."""
        with pytest.raises(ParameterError) as exc_info:
            self.adapter.validate_parameters(
                symbol="BTC/USDT",
                interval="2h",
                start_time=1000,
                end_time=2000,
            )
        
        assert "Unsupported interval" in str(exc_info.value)
    
    def test_validate_negative_start_time(self):
        """Test validation of negative start time."""
        with pytest.raises(ParameterError) as exc_info:
            self.adapter.validate_parameters(
                symbol="BTC/USDT",
                interval="1h",
                start_time=-1000,
                end_time=2000,
            )
        
        assert "start_time" in str(exc_info.value)
    
    def test_validate_negative_end_time(self):
        """Test validation of negative end time."""
        with pytest.raises(ParameterError) as exc_info:
            self.adapter.validate_parameters(
                symbol="BTC/USDT",
                interval="1h",
                start_time=1000,
                end_time=-2000,
            )
        
        assert "end_time" in str(exc_info.value)
    
    def test_validate_start_time_greater_than_end_time(self):
        """Test validation when start_time > end_time."""
        with pytest.raises(ParameterError) as exc_info:
            self.adapter.validate_parameters(
                symbol="BTC/USDT",
                interval="1h",
                start_time=2000,
                end_time=1000,
            )
        
        assert "start_time" in str(exc_info.value) and "end_time" in str(exc_info.value)


class TestMockDataSourceAdapter:
    """Tests for MockDataSourceAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockDataSourceAdapter()
    
    def test_fetch_kline_data_returns_list(self):
        """Test that fetch_kline_data returns a list."""
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=5000,
        )
        
        assert isinstance(result, list)
    
    def test_fetch_kline_data_returns_valid_klines(self):
        """Test that fetch_kline_data returns valid K-line data."""
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=5000,
        )
        
        assert len(result) > 0
        
        for kline in result:
            assert hasattr(kline, "timestamp")
            assert hasattr(kline, "open")
            assert hasattr(kline, "high")
            assert hasattr(kline, "low")
            assert hasattr(kline, "close")
            assert hasattr(kline, "volume")
    
    def test_fetch_kline_data_respects_time_range(self):
        """Test that fetch_kline_data respects the time range."""
        start_time = 1000
        end_time = 5000
        
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=start_time,
            end_time=end_time,
        )
        
        # All timestamps should be within the range
        for kline in result:
            assert kline.timestamp >= start_time
            assert kline.timestamp < end_time
    
    def test_fetch_kline_data_different_intervals(self):
        """Test fetch_kline_data with different intervals."""
        intervals = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]
        
        for interval in intervals:
            result = self.adapter.fetch_kline_data(
                symbol="BTC/USDT",
                interval=interval,
                start_time=1000,
                end_time=100000,
            )
            
            assert len(result) > 0
    
    def test_fetch_kline_data_different_symbols(self):
        """Test fetch_kline_data with different symbols."""
        symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
        
        for symbol in symbols:
            result = self.adapter.fetch_kline_data(
                symbol=symbol,
                interval="1h",
                start_time=1000,
                end_time=5000,
            )
            
            assert len(result) > 0
    
    def test_fetch_kline_data_empty_range(self):
        """Test fetch_kline_data with empty time range."""
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=1000,
        )
        
        # Should return empty list for empty range
        assert len(result) == 0
    
    def test_fetch_kline_data_single_interval(self):
        """Test fetch_kline_data with single interval."""
        # 1 hour interval
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=1000 + 60 * 60 * 1000,  # 1 hour
        )
        
        # Should have at least 1 K-line
        assert len(result) >= 1
    
    def test_fetch_kline_data_multiple_intervals(self):
        """Test fetch_kline_data with multiple intervals."""
        # 24 hours of 1 hour intervals
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=1000 + 24 * 60 * 60 * 1000,  # 24 hours
        )
        
        # Should have approximately 24 K-lines
        assert len(result) >= 24
    
    def test_fetch_kline_data_invalid_symbol_raises_error(self):
        """Test that invalid symbol raises ParameterError."""
        with pytest.raises(ParameterError):
            self.adapter.fetch_kline_data(
                symbol="INVALID/USDT",
                interval="1h",
                start_time=1000,
                end_time=5000,
            )
    
    def test_fetch_kline_data_invalid_interval_raises_error(self):
        """Test that invalid interval raises ParameterError."""
        with pytest.raises(ParameterError):
            self.adapter.fetch_kline_data(
                symbol="BTC/USDT",
                interval="2h",
                start_time=1000,
                end_time=5000,
            )
    
    def test_fetch_kline_data_price_relationships(self):
        """Test that fetched data has valid price relationships."""
        result = self.adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1000,
            end_time=10000,
        )
        
        for kline in result:
            # high >= low
            assert kline.high >= kline.low
            # low >= 0
            assert kline.low >= 0
            # All prices should be positive
            assert kline.open > 0
            assert kline.high > 0
            assert kline.close > 0
            # volume should be non-negative
            assert kline.volume >= 0


class TestDataSourceAdapterCopying:
    """Tests for ensuring supported lists are copied."""
    
    def test_supported_symbols_is_copy(self):
        """Test that get_supported_symbols returns a copy."""
        symbols1 = DataSourceAdapter.get_supported_symbols()
        symbols2 = DataSourceAdapter.get_supported_symbols()
        
        # Should be equal but not the same object
        assert symbols1 == symbols2
        assert symbols1 is not symbols2
    
    def test_supported_intervals_is_copy(self):
        """Test that get_supported_intervals returns a copy."""
        intervals1 = DataSourceAdapter.get_supported_intervals()
        intervals2 = DataSourceAdapter.get_supported_intervals()
        
        # Should be equal but not the same object
        assert intervals1 == intervals2
        assert intervals1 is not intervals2
