"""Tests for win rate calculation in strategy engine.

This module tests that win rate is calculated correctly according to requirement 6.5.
"""

import pytest
from strategy_engine.engine import GridStrategyEngine
from strategy_engine.models import StrategyConfig, StrategyMode
from market_data_layer.models import KlineData


class TestWinRateCalculation:
    """Test suite for win rate calculation."""
    
    def test_win_rate_with_mixed_trades(self):
        """Test win rate calculation with mixed winning and losing trades.
        
        Requirement 6.5: 胜率 = 盈利交易数 / 总交易数
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=30000,
            upper_price=40000,
            grid_count=5,
            initial_capital=10000,
            leverage=1,
            fee_rate=0.0005,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create K-line data that will trigger trades
        # Price oscillates to create both winning and losing trades
        klines = [
            KlineData(timestamp=1000, open=35000, high=35000, low=35000, close=35000, volume=100),
            KlineData(timestamp=2000, open=35000, high=37500, low=32500, close=37500, volume=100),  # Trigger trades
            KlineData(timestamp=3000, open=37500, high=37500, low=35000, close=35000, volume=100),  # Trigger trades
            KlineData(timestamp=4000, open=35000, high=40000, low=30000, close=35000, volume=100),  # Trigger trades
        ]
        
        result = engine.execute(klines)
        
        # Verify win rate calculation
        if result.total_trades > 0:
            expected_win_rate = result.winning_trades / result.total_trades
            assert abs(result.win_rate - expected_win_rate) < 1e-10
            
            # Verify that winning + losing trades <= total trades
            # (some trades might have zero PnL)
            assert result.winning_trades + result.losing_trades <= result.total_trades
            
            # Verify win rate is between 0 and 1
            assert 0 <= result.win_rate <= 1
    
    def test_win_rate_zero_trades(self):
        """Test win rate when no trades are executed.
        
        Requirement 6.5: When total_trades = 0, win_rate should be 0
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000,
            leverage=1,
            fee_rate=0.0005,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create K-line data with no price movement (no trades triggered)
        klines = [
            KlineData(timestamp=1000, open=35000, high=35000, low=35000, close=35000, volume=100),
        ]
        
        result = engine.execute(klines)
        
        # Verify win rate is 0 when no trades
        assert result.total_trades == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0
        assert result.win_rate == 0.0
    
    def test_win_rate_calculation_formula(self):
        """Test that win rate uses the correct formula.
        
        Requirement 6.5: 胜率 = 盈利交易数 / 总交易数
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=30000,
            upper_price=40000,
            grid_count=10,
            initial_capital=10000,
            leverage=1,
            fee_rate=0.0005,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create K-line data that will trigger multiple trades
        klines = [
            KlineData(timestamp=1000, open=35000, high=35000, low=35000, close=35000, volume=100),
            KlineData(timestamp=2000, open=35000, high=38000, low=32000, close=36000, volume=100),
            KlineData(timestamp=3000, open=36000, high=39000, low=33000, close=37000, volume=100),
            KlineData(timestamp=4000, open=37000, high=40000, low=34000, close=38000, volume=100),
        ]
        
        result = engine.execute(klines)
        
        # Manually verify the formula
        if result.total_trades > 0:
            # Count winning trades from trade records
            winning_count = sum(1 for trade in result.trades if trade.pnl > 0)
            
            # Verify the counts match
            assert result.winning_trades == winning_count
            
            # Verify the formula
            expected_win_rate = winning_count / result.total_trades
            assert abs(result.win_rate - expected_win_rate) < 1e-10
    
    def test_win_rate_with_zero_pnl_trades(self):
        """Test win rate calculation when some trades have zero PnL.
        
        Trades with zero PnL should not be counted as winning or losing.
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=30000,
            upper_price=40000,
            grid_count=5,
            initial_capital=10000,
            leverage=1,
            fee_rate=0.0,  # Zero fee to allow zero PnL trades
            funding_rate=0.0,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create K-line data
        klines = [
            KlineData(timestamp=1000, open=35000, high=35000, low=35000, close=35000, volume=100),
            KlineData(timestamp=2000, open=35000, high=37500, low=32500, close=35000, volume=100),
            KlineData(timestamp=3000, open=35000, high=37500, low=32500, close=35000, volume=100),
        ]
        
        result = engine.execute(klines)
        
        if result.total_trades > 0:
            # Verify that winning + losing <= total (some might be zero PnL)
            assert result.winning_trades + result.losing_trades <= result.total_trades
            
            # Verify win rate calculation
            expected_win_rate = result.winning_trades / result.total_trades
            assert abs(result.win_rate - expected_win_rate) < 1e-10
    
    def test_win_rate_consistency_across_modes(self):
        """Test that win rate calculation is consistent across all strategy modes."""
        modes = [StrategyMode.LONG, StrategyMode.SHORT, StrategyMode.NEUTRAL]
        
        for mode in modes:
            config = StrategyConfig(
                symbol="BTC/USDT",
                mode=mode,
                lower_price=30000,
                upper_price=40000,
                grid_count=10,
                initial_capital=10000,
                leverage=1,
                fee_rate=0.0005,
                funding_rate=0.0001,
                funding_interval=8,
            )
            
            engine = GridStrategyEngine(config)
            
            # Create K-line data
            klines = [
                KlineData(timestamp=1000, open=35000, high=35000, low=35000, close=35000, volume=100),
                KlineData(timestamp=2000, open=35000, high=38000, low=32000, close=36000, volume=100),
                KlineData(timestamp=3000, open=36000, high=39000, low=33000, close=35000, volume=100),
            ]
            
            result = engine.execute(klines)
            
            # Verify win rate calculation for each mode
            if result.total_trades > 0:
                expected_win_rate = result.winning_trades / result.total_trades
                assert abs(result.win_rate - expected_win_rate) < 1e-10
                assert 0 <= result.win_rate <= 1
                assert result.winning_trades + result.losing_trades <= result.total_trades
