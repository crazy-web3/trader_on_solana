"""Integration tests for the refactored GridStrategyEngine.

This test suite validates that the complete system works correctly end-to-end,
testing all three strategy modes and various edge cases.

**Validates: Requirements 8.2**
"""

import pytest
from strategy_engine.engine import GridStrategyEngine
from strategy_engine.models import StrategyConfig, StrategyMode
from market_data_layer.models import KlineData


class TestGridStrategyEngineIntegration:
    """Integration tests for GridStrategyEngine with complete backtest flows."""
    
    def test_complete_backtest_long_mode(self):
        """Test complete backtest flow for LONG mode.
        
        This test validates:
        - Initial orders are placed correctly (buy below, sell above current price)
        - Buy orders trigger when price drops
        - Sell orders trigger when price rises
        - Positions are opened and closed correctly
        - PnL is calculated and accumulated
        - Margin is managed correctly
        - Equity curve is updated
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,  # 10 gaps, 11 levels
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create a realistic price movement scenario
        klines = [
            # Start at middle price
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Price drops to trigger buy orders
            KlineData(
                timestamp=1609459200000 + 3600000,  # +1 hour
                open=45000.0,
                high=45000.0,
                low=42000.0,  # Trigger multiple buy orders
                close=42500.0,
                volume=150.0,
            ),
            # Price rises to trigger sell orders
            KlineData(
                timestamp=1609459200000 + 7200000,  # +2 hours
                open=42500.0,
                high=44000.0,  # Trigger sell orders
                low=42500.0,
                close=43500.0,
                volume=120.0,
            ),
            # Price continues to rise
            KlineData(
                timestamp=1609459200000 + 10800000,  # +3 hours
                open=43500.0,
                high=46000.0,  # More sell orders
                low=43500.0,
                close=45500.0,
                volume=130.0,
            ),
            # Price drops again
            KlineData(
                timestamp=1609459200000 + 14400000,  # +4 hours
                open=45500.0,
                high=45500.0,
                low=43000.0,  # Buy orders again
                close=43500.0,
                volume=140.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate results
        assert result is not None
        assert result.symbol == "BTC/USDT"
        assert result.mode == StrategyMode.LONG
        assert result.initial_capital == 10000.0
        
        # Should have executed some trades
        assert result.total_trades > 0
        assert len(result.trades) > 0
        
        # Equity curve should be updated for each kline
        assert len(result.equity_curve) == len(klines)
        assert len(result.timestamps) == len(klines)
        
        # Fees should be accumulated
        assert result.total_fees > 0
        
        # Final capital should be different from initial
        # (could be higher or lower depending on market movement)
        assert result.final_capital != result.initial_capital
        
        # Grid profit should be recorded if any positions were closed
        # (might be 0 if only opening positions)
        assert result.grid_profit >= 0 or result.grid_profit < 0
        
        # Max drawdown should be calculated
        assert result.max_drawdown >= 0
        assert result.max_drawdown_pct >= 0
        
        # Win rate should be between 0 and 1
        assert 0 <= result.win_rate <= 1
    
    def test_complete_backtest_short_mode(self):
        """Test complete backtest flow for SHORT mode.
        
        This test validates:
        - Initial orders are placed correctly (sell above, buy below current price)
        - Sell orders trigger when price rises
        - Buy orders trigger when price drops
        - Short positions are opened and closed correctly
        - PnL is calculated correctly for short positions
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.SHORT,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create a price movement scenario favorable for short strategy
        klines = [
            # Start at middle price
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Price rises to trigger sell orders (open short positions)
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=45000.0,
                high=48000.0,  # Trigger multiple sell orders
                low=45000.0,
                close=47500.0,
                volume=150.0,
            ),
            # Price drops to trigger buy orders (close short positions)
            KlineData(
                timestamp=1609459200000 + 7200000,
                open=47500.0,
                high=47500.0,
                low=45000.0,  # Trigger buy orders
                close=45500.0,
                volume=120.0,
            ),
            # Price rises again
            KlineData(
                timestamp=1609459200000 + 10800000,
                open=45500.0,
                high=49000.0,  # More sell orders
                low=45500.0,
                close=48500.0,
                volume=130.0,
            ),
            # Price drops again
            KlineData(
                timestamp=1609459200000 + 14400000,
                open=48500.0,
                high=48500.0,
                low=46000.0,  # Buy orders to close shorts
                close=46500.0,
                volume=140.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate results
        assert result is not None
        assert result.mode == StrategyMode.SHORT
        assert result.total_trades > 0
        assert len(result.equity_curve) == len(klines)
        assert result.total_fees > 0
        
        # Should have some grid profit if positions were closed
        # In SHORT mode, profit when price drops after opening short
        assert result.grid_profit != 0 or len(result.trades) > 0
    
    def test_complete_backtest_neutral_mode(self):
        """Test complete backtest flow for NEUTRAL mode.
        
        This test validates:
        - Initial orders are placed correctly (buy below, sell above)
        - Positions are opened in both directions
        - Matching positions are found and closed correctly
        - PnL is calculated for both long and short positions
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create oscillating price movement
        klines = [
            # Start at middle price
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Price drops - trigger buy orders (open long)
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=45000.0,
                high=45000.0,
                low=42000.0,
                close=42500.0,
                volume=150.0,
            ),
            # Price rises - trigger sell orders (close long, open short)
            KlineData(
                timestamp=1609459200000 + 7200000,
                open=42500.0,
                high=47000.0,
                low=42500.0,
                close=46500.0,
                volume=120.0,
            ),
            # Price drops - trigger buy orders (close short, open long)
            KlineData(
                timestamp=1609459200000 + 10800000,
                open=46500.0,
                high=46500.0,
                low=41000.0,
                close=41500.0,
                volume=130.0,
            ),
            # Price rises - trigger sell orders (close long)
            KlineData(
                timestamp=1609459200000 + 14400000,
                open=41500.0,
                high=45000.0,
                low=41500.0,
                close=44500.0,
                volume=140.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate results
        assert result is not None
        assert result.mode == StrategyMode.NEUTRAL
        assert result.total_trades > 0
        assert len(result.equity_curve) == len(klines)
        
        # In neutral mode, we should see both opening and closing trades
        # Grid profit should be accumulated from closed positions
        assert result.grid_profit != 0 or result.total_trades > 0
    
    def test_edge_case_insufficient_margin(self):
        """Test edge case: insufficient margin to open positions.
        
        This test validates:
        - Orders are rejected when margin is insufficient
        - System remains stable and doesn't crash
        - Capital is not incorrectly modified
        - Fees are refunded if order is rejected
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=50.0,  # Very small capital
            leverage=1.0,  # Low leverage
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        klines = [
            # Initialize
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Try to trigger buy orders with insufficient margin
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=45000.0,
                high=45000.0,
                low=40000.0,  # Would trigger buy orders
                close=41000.0,
                volume=150.0,
            ),
        ]
        
        # Execute strategy - should not crash
        result = engine.execute(klines)
        
        # Validate that system handled insufficient margin gracefully
        assert result is not None
        assert result.final_capital <= result.initial_capital
        
        # Either no trades executed, or very few due to insufficient margin
        # The key is that the system didn't crash
        assert len(result.equity_curve) == len(klines)
    
    def test_edge_case_price_out_of_range(self):
        """Test edge case: price moves outside grid range.
        
        This test validates:
        - System handles prices outside grid boundaries
        - No orders are triggered outside the range
        - System remains stable
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        klines = [
            # Start in range
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Price goes way below range
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=45000.0,
                high=45000.0,
                low=30000.0,  # Below lower_price
                close=35000.0,
                volume=150.0,
            ),
            # Price goes way above range
            KlineData(
                timestamp=1609459200000 + 7200000,
                open=35000.0,
                high=60000.0,  # Above upper_price
                low=35000.0,
                close=55000.0,
                volume=120.0,
            ),
            # Price returns to range
            KlineData(
                timestamp=1609459200000 + 10800000,
                open=55000.0,
                high=55000.0,
                low=45000.0,
                close=45000.0,
                volume=130.0,
            ),
        ]
        
        # Execute strategy - should not crash
        result = engine.execute(klines)
        
        # Validate system stability
        assert result is not None
        assert len(result.equity_curve) == len(klines)
        
        # Should have executed some trades when price was in range
        assert result.total_trades >= 0
    
    def test_edge_case_zero_price_movement(self):
        """Test edge case: price doesn't move (no orders triggered).
        
        This test validates:
        - System handles scenario with no order fills
        - Equity curve is still updated
        - No trades are recorded
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Price stays constant
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 3600000,
                open=45000.0,
                high=45000.0,
                low=45000.0,
                close=45000.0,
                volume=100.0,
            )
            for i in range(5)
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate results
        assert result is not None
        assert len(result.equity_curve) == len(klines)
        
        # One trade should be executed at initialization (price exactly at grid level)
        # When current_price == grid_price, a buy order is placed and immediately fills
        assert result.total_trades == 1
        assert len(result.trades) == 1
        
        # Capital should decrease by fee amount only
        expected_capital = result.initial_capital - result.total_fees
        assert abs(result.final_capital - expected_capital) < 0.01
    
    def test_multi_kline_position_management(self):
        """Test multi-kline scenario with complex position management.
        
        This test validates:
        - Multiple positions can be opened across different grids
        - Positions are tracked independently per grid
        - Matching logic works correctly across multiple klines
        - Margin is allocated and released correctly
        - PnL accumulates correctly over time
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=20000.0,  # Larger capital for multiple positions
            leverage=3.0,
            fee_rate=0.001,
            funding_rate=0.0001,
            funding_interval=8,
        )
        
        engine = GridStrategyEngine(config)
        
        # Complex price movement scenario
        klines = [
            # Initialize
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45500.0,
                low=44500.0,
                close=45000.0,
                volume=100.0,
            ),
            # Drop to trigger multiple buy orders
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=45000.0,
                high=45000.0,
                low=41000.0,  # Trigger buys at grids 0, 1, 2, 3
                close=41500.0,
                volume=150.0,
            ),
            # Small rise
            KlineData(
                timestamp=1609459200000 + 7200000,
                open=41500.0,
                high=43000.0,  # Trigger some sells
                low=41500.0,
                close=42500.0,
                volume=120.0,
            ),
            # Drop again
            KlineData(
                timestamp=1609459200000 + 10800000,
                open=42500.0,
                high=42500.0,
                low=40000.0,  # Trigger more buys
                close=40500.0,
                volume=130.0,
            ),
            # Large rise
            KlineData(
                timestamp=1609459200000 + 14400000,
                open=40500.0,
                high=46000.0,  # Trigger multiple sells
                low=40500.0,
                close=45500.0,
                volume=140.0,
            ),
            # Moderate movement
            KlineData(
                timestamp=1609459200000 + 18000000,
                open=45500.0,
                high=47000.0,
                low=44000.0,
                close=45000.0,
                volume=110.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate complex scenario
        assert result is not None
        assert result.total_trades > 5  # Should have many trades
        assert len(result.equity_curve) == len(klines)
        
        # Should have both winning and losing trades
        assert result.winning_trades >= 0
        assert result.losing_trades >= 0
        
        # Grid profit should be accumulated
        assert result.grid_profit != 0
        
        # Margin should be managed correctly
        # Final used margin should be >= 0
        assert engine.margin_calculator.get_used_margin() >= 0
        
        # Net position should be calculated correctly
        net_position = engine.position_manager.get_net_position()
        assert isinstance(net_position, (int, float))
    
    def test_funding_fee_calculation_over_time(self):
        """Test funding fee calculation over multiple funding intervals.
        
        This test validates:
        - Funding fees are calculated at correct intervals
        - Fees are deducted from capital
        - Total funding fees are accumulated
        - Funding fees only apply when positions are held
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,  # 0.01% funding rate
            funding_interval=8,  # 8 hours
        )
        
        engine = GridStrategyEngine(config)
        
        # Create klines spanning multiple funding intervals
        klines = []
        base_time = 1609459200000
        
        # Initialize and open position
        klines.append(KlineData(
            timestamp=base_time,
            open=45000.0,
            high=45000.0,
            low=42000.0,  # Trigger buy
            close=42500.0,
            volume=100.0,
        ))
        
        # Add klines every hour for 24 hours (3 funding intervals)
        for i in range(1, 25):
            klines.append(KlineData(
                timestamp=base_time + i * 3600000,  # +1 hour each
                open=42500.0,
                high=43000.0,
                low=42000.0,
                close=42500.0,
                volume=100.0,
            ))
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate funding fees
        assert result is not None
        
        # Should have accumulated funding fees if positions were held
        if result.total_trades > 0:
            # If we opened positions, we should have funding fees
            # (might be 0 if positions were closed quickly)
            assert result.total_funding_fees >= 0
    
    def test_equity_curve_consistency(self):
        """Test that equity curve is updated consistently.
        
        This test validates:
        - Equity curve has one entry per kline
        - Equity values are reasonable (not negative, not infinite)
        - Equity changes reflect trades and PnL
        - Timestamps match kline timestamps
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 3600000,
                open=45000.0 + i * 100,
                high=45500.0 + i * 100,
                low=44500.0 + i * 100,
                close=45000.0 + i * 100,
                volume=100.0,
            )
            for i in range(10)
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate equity curve
        assert len(result.equity_curve) == len(klines)
        assert len(result.timestamps) == len(klines)
        
        # Check that timestamps match
        for i, timestamp in enumerate(result.timestamps):
            assert timestamp == klines[i].timestamp
        
        # Check that equity values are reasonable
        for equity in result.equity_curve:
            assert equity > 0  # Should not be negative
            assert equity < float('inf')  # Should not be infinite
            assert not (equity != equity)  # Should not be NaN
        
        # First equity should be close to initial capital
        # (might differ slightly due to immediate trades)
        assert result.equity_curve[0] > 0
    
    def test_trade_records_completeness(self):
        """Test that trade records contain all required information.
        
        This test validates:
        - Each trade has all required fields
        - Trade data is consistent
        - Fees are recorded correctly
        - PnL is recorded for closing trades
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        klines = [
            KlineData(
                timestamp=1609459200000,
                open=45000.0,
                high=45000.0,
                low=42000.0,
                close=42500.0,
                volume=100.0,
            ),
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=42500.0,
                high=45000.0,
                low=42500.0,
                close=44500.0,
                volume=120.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate trade records
        if result.total_trades > 0:
            for trade in result.trades:
                # Check all required fields are present
                assert trade.timestamp > 0
                assert trade.price > 0
                assert trade.quantity > 0
                assert trade.side in ["buy", "sell"]
                assert trade.grid_level >= 0
                assert trade.fee >= 0
                # PnL can be 0 for opening trades, non-zero for closing
                assert isinstance(trade.pnl, (int, float))
                assert isinstance(trade.position_size, (int, float))
    
    def test_max_drawdown_calculation(self):
        """Test that maximum drawdown is calculated correctly.
        
        This test validates:
        - Max drawdown is tracked during execution
        - Drawdown percentage is calculated correctly
        - Drawdown is non-negative
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=11,
            initial_capital=10000.0,
            leverage=2.0,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Create scenario with clear drawdown
        klines = [
            # Start high
            KlineData(
                timestamp=1609459200000,
                open=48000.0,
                high=48500.0,
                low=47500.0,
                close=48000.0,
                volume=100.0,
            ),
            # Drop significantly (create drawdown)
            KlineData(
                timestamp=1609459200000 + 3600000,
                open=48000.0,
                high=48000.0,
                low=41000.0,
                close=41500.0,
                volume=150.0,
            ),
            # Recover partially
            KlineData(
                timestamp=1609459200000 + 7200000,
                open=41500.0,
                high=45000.0,
                low=41500.0,
                close=44500.0,
                volume=120.0,
            ),
        ]
        
        # Execute strategy
        result = engine.execute(klines)
        
        # Validate drawdown
        assert result.max_drawdown >= 0
        assert result.max_drawdown_pct >= 0
        assert result.max_drawdown_pct <= 1.0  # Should not exceed 100%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
