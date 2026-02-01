"""Tests for multi-timeframe support.

Feature: stage3-backtest-precision
Tests for Requirement 1: Multi-Timeframe Support
"""

import pytest
from backtest_engine.models import Timeframe, BacktestConfig, StrategyMode


class TestTimeframeEnum:
    """Test Timeframe enumeration."""
    
    def test_timeframe_values(self):
        """Test that all timeframe values are correct."""
        assert Timeframe.M1.value == "1m"
        assert Timeframe.M5.value == "5m"
        assert Timeframe.M15.value == "15m"
        assert Timeframe.H1.value == "1h"
        assert Timeframe.H4.value == "4h"
        assert Timeframe.D1.value == "1d"
    
    def test_timeframe_milliseconds(self):
        """Test that timeframe milliseconds are calculated correctly."""
        assert Timeframe.M1.milliseconds == 60_000
        assert Timeframe.M5.milliseconds == 300_000
        assert Timeframe.M15.milliseconds == 900_000
        assert Timeframe.H1.milliseconds == 3_600_000
        assert Timeframe.H4.milliseconds == 14_400_000
        assert Timeframe.D1.milliseconds == 86_400_000
    
    def test_timeframe_seconds(self):
        """Test that timeframe seconds are calculated correctly."""
        assert Timeframe.M1.seconds == 60
        assert Timeframe.M5.seconds == 300
        assert Timeframe.M15.seconds == 900
        assert Timeframe.H1.seconds == 3_600
        assert Timeframe.H4.seconds == 14_400
        assert Timeframe.D1.seconds == 86_400
    
    def test_timeframe_recommend_scalping(self):
        """Test timeframe recommendation for scalping strategy."""
        assert Timeframe.recommend("scalping") == Timeframe.M1
    
    def test_timeframe_recommend_day_trading(self):
        """Test timeframe recommendation for day trading strategy."""
        assert Timeframe.recommend("day_trading") == Timeframe.M5
    
    def test_timeframe_recommend_intraday(self):
        """Test timeframe recommendation for intraday strategy."""
        assert Timeframe.recommend("intraday") == Timeframe.M15
    
    def test_timeframe_recommend_swing(self):
        """Test timeframe recommendation for swing trading strategy."""
        assert Timeframe.recommend("swing") == Timeframe.H1
    
    def test_timeframe_recommend_position(self):
        """Test timeframe recommendation for position trading strategy."""
        assert Timeframe.recommend("position") == Timeframe.D1
    
    def test_timeframe_recommend_unknown_defaults_to_d1(self):
        """Test that unknown strategy types default to D1."""
        assert Timeframe.recommend("unknown") == Timeframe.D1
        assert Timeframe.recommend("") == Timeframe.D1
        assert Timeframe.recommend("random_strategy") == Timeframe.D1


class TestBacktestConfigTimeframe:
    """Test BacktestConfig with timeframe support."""
    
    def test_backtest_config_default_timeframe(self):
        """Test that BacktestConfig defaults to D1 timeframe."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31"
        )
        assert config.timeframe == Timeframe.D1
    
    def test_backtest_config_custom_timeframe(self):
        """Test that BacktestConfig accepts custom timeframe."""
        for timeframe in [Timeframe.M1, Timeframe.M5, Timeframe.M15, 
                         Timeframe.H1, Timeframe.H4, Timeframe.D1]:
            config = BacktestConfig(
                symbol="BTC/USDT",
                mode=StrategyMode.NEUTRAL,
                lower_price=40000.0,
                upper_price=60000.0,
                grid_count=10,
                initial_capital=10000.0,
                start_date="2024-01-01",
                end_date="2024-12-31",
                timeframe=timeframe
            )
            assert config.timeframe == timeframe
    
    def test_backtest_config_timeframe_in_to_dict(self):
        """Test that timeframe is included in BacktestResult.to_dict()."""
        from backtest_engine.models import BacktestResult, PerformanceMetrics
        
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            timeframe=Timeframe.H1
        )
        
        metrics = PerformanceMetrics(
            total_return=0.1,
            annual_return=0.12,
            max_drawdown=0.05,
            sharpe_ratio=1.5,
            win_rate=0.6,
            total_trades=100,
            winning_trades=60,
            losing_trades=40,
            fee_cost=50.0,
            fee_ratio=0.005
        )
        
        result = BacktestResult(
            config=config,
            metrics=metrics,
            initial_capital=10000.0,
            final_capital=11000.0
        )
        
        result_dict = result.to_dict()
        assert "timeframe" in result_dict["config"]
        assert result_dict["config"]["timeframe"] == "1h"


class TestTimeframeProperties:
    """Test timeframe properties and relationships."""
    
    def test_timeframe_ordering_by_duration(self):
        """Test that timeframes can be ordered by duration."""
        timeframes = [
            (Timeframe.M1, 60_000),
            (Timeframe.M5, 300_000),
            (Timeframe.M15, 900_000),
            (Timeframe.H1, 3_600_000),
            (Timeframe.H4, 14_400_000),
            (Timeframe.D1, 86_400_000),
        ]
        
        for i in range(len(timeframes) - 1):
            tf1, ms1 = timeframes[i]
            tf2, ms2 = timeframes[i + 1]
            assert tf1.milliseconds < tf2.milliseconds
            assert ms1 < ms2
    
    def test_timeframe_conversion_consistency(self):
        """Test that milliseconds and seconds conversions are consistent."""
        for timeframe in Timeframe:
            assert timeframe.milliseconds == timeframe.seconds * 1000
    
    def test_timeframe_enum_membership(self):
        """Test that all expected timeframes are in the enum."""
        expected_values = {"1m", "5m", "15m", "1h", "4h", "1d"}
        actual_values = {tf.value for tf in Timeframe}
        assert actual_values == expected_values
    
    def test_timeframe_string_representation(self):
        """Test that timeframes have correct string representation."""
        assert str(Timeframe.M1.value) == "1m"
        assert str(Timeframe.H1.value) == "1h"
        assert str(Timeframe.D1.value) == "1d"


class TestTimeframeBackwardCompatibility:
    """Test backward compatibility with existing code."""
    
    def test_existing_config_without_timeframe_still_works(self):
        """Test that existing BacktestConfig creation without timeframe still works."""
        # This simulates existing code that doesn't specify timeframe
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            fee_rate=0.0005,
            leverage=1.0
        )
        # Should default to D1
        assert config.timeframe == Timeframe.D1
    
    def test_config_with_all_original_fields_plus_timeframe(self):
        """Test that config works with all original fields plus new timeframe."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.SHORT,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            fee_rate=0.0005,
            leverage=2.0,
            funding_rate=0.0001,
            funding_interval=8,
            timeframe=Timeframe.M5
        )
        assert config.timeframe == Timeframe.M5
        assert config.leverage == 2.0
        assert config.funding_rate == 0.0001



class TestMarketDataAdapterTimeframeSupport:
    """Test MarketDataAdapter support for Timeframe enum."""
    
    def test_mock_adapter_accepts_timeframe_enum(self):
        """Test that MockDataSourceAdapter accepts Timeframe enum."""
        from market_data_layer.adapter import MockDataSourceAdapter
        
        adapter = MockDataSourceAdapter()
        
        # Test with Timeframe enum
        klines = adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval=Timeframe.H1,
            start_time=1609459200000,  # 2021-01-01
            end_time=1609545600000,    # 2021-01-02
        )
        
        assert len(klines) > 0
        assert all(isinstance(k.timestamp, int) for k in klines)
    
    def test_mock_adapter_accepts_string_interval(self):
        """Test that MockDataSourceAdapter still accepts string interval."""
        from market_data_layer.adapter import MockDataSourceAdapter
        
        adapter = MockDataSourceAdapter()
        
        # Test with string interval (backward compatibility)
        klines = adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=1609459200000,
            end_time=1609545600000,
        )
        
        assert len(klines) > 0
    
    def test_mock_adapter_timeframe_and_string_produce_same_result(self):
        """Test that Timeframe enum and string produce same results."""
        from market_data_layer.adapter import MockDataSourceAdapter
        
        adapter = MockDataSourceAdapter()
        
        start_time = 1609459200000
        end_time = 1609545600000
        
        # Fetch with Timeframe enum
        klines_enum = adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval=Timeframe.H1,
            start_time=start_time,
            end_time=end_time,
        )
        
        # Fetch with string
        klines_str = adapter.fetch_kline_data(
            symbol="BTC/USDT",
            interval="1h",
            start_time=start_time,
            end_time=end_time,
        )
        
        # Should produce same number of klines
        assert len(klines_enum) == len(klines_str)
        
        # Should have same timestamps
        for k1, k2 in zip(klines_enum, klines_str):
            assert k1.timestamp == k2.timestamp
    
    def test_mock_adapter_all_timeframes(self):
        """Test that MockDataSourceAdapter works with all Timeframe values."""
        from market_data_layer.adapter import MockDataSourceAdapter
        
        adapter = MockDataSourceAdapter()
        
        start_time = 1609459200000  # 2021-01-01
        end_time = 1609545600000    # 2021-01-02 (1 day)
        
        for timeframe in [Timeframe.M1, Timeframe.M5, Timeframe.M15, 
                         Timeframe.H1, Timeframe.H4, Timeframe.D1]:
            klines = adapter.fetch_kline_data(
                symbol="BTC/USDT",
                interval=timeframe,
                start_time=start_time,
                end_time=end_time,
            )
            
            # Should return some klines
            assert len(klines) > 0
            
            # Verify kline count matches expected for timeframe
            expected_count = (end_time - start_time) // timeframe.milliseconds
            assert len(klines) == expected_count
    
    def test_adapter_normalize_interval_method(self):
        """Test the _normalize_interval method."""
        from market_data_layer.adapter import MockDataSourceAdapter
        
        adapter = MockDataSourceAdapter()
        
        # Test with Timeframe enum
        assert adapter._normalize_interval(Timeframe.M1) == "1m"
        assert adapter._normalize_interval(Timeframe.H1) == "1h"
        assert adapter._normalize_interval(Timeframe.D1) == "1d"
        
        # Test with string (should pass through)
        assert adapter._normalize_interval("1m") == "1m"
        assert adapter._normalize_interval("1h") == "1h"
        assert adapter._normalize_interval("1d") == "1d"
