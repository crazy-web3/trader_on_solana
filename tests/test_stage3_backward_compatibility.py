"""Backward compatibility tests for Stage 3 features."""

import pytest
from backtest_engine.models import BacktestConfig, StrategyMode, Timeframe
from backtest_engine.slippage_simulator import SlippageConfig
from backtest_engine.order_fill_simulator import OrderFillConfig


class TestBackwardCompatibility:
    """Tests to ensure Stage 3 features don't break existing functionality."""
    
    def test_backtest_config_without_new_fields(self):
        """Test that BacktestConfig works without specifying new fields."""
        # This should work exactly as before Stage 3
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
        
        # Should have default values
        assert config.timeframe == Timeframe.D1
        assert config.slippage_config is None
    
    def test_default_timeframe_is_1d(self):
        """Test that default timeframe is 1d for backward compatibility."""
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
        assert config.timeframe.value == "1d"
    
    def test_slippage_disabled_by_default(self):
        """Test that slippage is disabled by default."""
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
        
        # Slippage config should be None (disabled)
        assert config.slippage_config is None
    
    def test_gradual_adoption_timeframe_only(self):
        """Test that users can adopt timeframe feature independently."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            timeframe=Timeframe.H1  # Only change timeframe
        )
        
        assert config.timeframe == Timeframe.H1
        assert config.slippage_config is None
    
    def test_gradual_adoption_slippage_only(self):
        """Test that users can adopt slippage feature independently."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            slippage_config=SlippageConfig(enabled=True)  # Only add slippage
        )
        
        assert config.timeframe == Timeframe.D1  # Still default
        assert config.slippage_config is not None
        assert config.slippage_config.enabled is True
    
    def test_all_new_features_together(self):
        """Test that all new features can be used together."""
        config = BacktestConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=60000.0,
            grid_count=10,
            initial_capital=10000.0,
            start_date="2024-01-01",
            end_date="2024-12-31",
            timeframe=Timeframe.M5,
            slippage_config=SlippageConfig(enabled=True)
        )
        
        assert config.timeframe == Timeframe.M5
        assert config.slippage_config is not None
        assert config.slippage_config.enabled is True


class TestFeatureDefaults:
    """Test that new features have sensible defaults."""
    
    def test_slippage_config_defaults(self):
        """Test SlippageConfig default values."""
        config = SlippageConfig()
        
        assert config.enabled is True
        assert config.base_slippage == 0.0001
        assert config.size_impact_factor == 0.001
        assert config.volatility_impact_factor == 0.0005
        assert config.max_slippage == 0.005
        assert config.model == 'linear'
    
    def test_order_fill_config_defaults(self):
        """Test OrderFillConfig default values."""
        config = OrderFillConfig()
        
        assert config.enable_partial_fill is False
        assert config.enable_realistic_timing is True
        assert config.min_fill_ratio == 0.1
    
    def test_disabled_features_have_no_impact(self):
        """Test that disabled features don't affect results."""
        # Slippage disabled
        slippage_config = SlippageConfig(enabled=False)
        assert slippage_config.enabled is False
        
        # Partial fill disabled
        fill_config = OrderFillConfig(enable_partial_fill=False)
        assert fill_config.enable_partial_fill is False


class TestAPIStability:
    """Test that existing APIs remain stable."""
    
    def test_backtest_config_to_dict_includes_new_fields(self):
        """Test that to_dict includes new fields."""
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
        
        # Should include timeframe
        assert 'timeframe' in result_dict['config']
        assert result_dict['config']['timeframe'] == '1h'
        
        # Should include slippage metrics
        assert 'total_slippage_cost' in result_dict['metrics']
        assert 'slippage_impact_pct' in result_dict['metrics']
        assert 'avg_slippage_bps' in result_dict['metrics']
