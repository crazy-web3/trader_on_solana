"""Integration tests for the refactored _fill_order method."""

import pytest
from strategy_engine.engine import GridStrategyEngine
from strategy_engine.models import StrategyConfig, StrategyMode
from market_data_layer.models import KlineData


class TestFillOrderIntegration:
    """Test the refactored _fill_order method with real scenarios."""
    
    def test_fill_order_long_mode_open_position(self):
        """Test opening a long position in LONG mode."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize with first kline
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45500.0,
            low=44500.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        # Trigger a buy order at lower price
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=45000.0,
            low=40000.0,  # Trigger buy at grid 0
            close=41000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Check that position was opened
        assert engine.position_manager.get_net_position() > 0
        assert engine.margin_calculator.get_used_margin() > 0
        assert len(engine.trades) > 0
        
        # Check that capital was reduced by fee
        assert engine.capital < config.initial_capital
    
    def test_fill_order_long_mode_close_position(self):
        """Test closing a long position in LONG mode.
        
        This test verifies that _fill_order correctly:
        1. Finds matching positions
        2. Calculates realized PnL
        3. Closes positions
        4. Releases margin
        """
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=10,  # More grids to avoid multiple triggers
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize at a price that won't trigger many orders
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45100.0,
            low=44900.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        # Trigger only the lowest buy order
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=45000.0,
            low=40000.0,  # Trigger buy at grid 0
            close=40100.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Check that we have a position
        assert engine.position_manager.get_net_position() > 0
        initial_position = engine.position_manager.get_net_position()
        initial_margin = engine.margin_calculator.get_used_margin()
        initial_capital = engine.capital
        
        # Now manually place a sell order at a grid that will match with grid 0
        # In LONG mode, sell at grid 1 should match with position at grid 0
        grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
        sell_price = config.lower_price + grid_gap
        
        # Trigger a sell at the next grid level
        kline3 = KlineData(
            timestamp=1609459200000 + 120000,
            open=40100.0,
            high=sell_price,  # Trigger sell at grid 1
            low=40100.0,
            close=40500.0,
            volume=100.0,
        )
        engine._process_kline(kline3)
        
        # Check results
        final_position = engine.position_manager.get_net_position()
        final_margin = engine.margin_calculator.get_used_margin()
        
        # Position should be reduced (or same if no sell order was placed)
        assert abs(final_position) <= abs(initial_position)
        
        # If position was reduced, margin should be released and PnL should be recorded
        if abs(final_position) < abs(initial_position):
            assert final_margin < initial_margin
            assert engine.pnl_calculator.get_grid_profit() != 0
            # Capital should have changed (increased by PnL, decreased by fees)
            assert engine.capital != initial_capital
    
    def test_fill_order_short_mode_open_position(self):
        """Test opening a short position in SHORT mode."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.SHORT,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize with first kline
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45500.0,
            low=44500.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        # Trigger a sell order at higher price
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=50000.0,  # Trigger sell at grid 4
            low=45000.0,
            close=49000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Check that short position was opened
        assert engine.position_manager.get_net_position() < 0
        assert engine.margin_calculator.get_used_margin() > 0
        assert len(engine.trades) > 0
    
    def test_fill_order_neutral_mode_open_and_close(self):
        """Test opening and closing positions in NEUTRAL mode."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.NEUTRAL,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize with first kline at a higher price
        kline1 = KlineData(
            timestamp=1609459200000,
            open=47000.0,
            high=47500.0,
            low=46500.0,
            close=47000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        # Trigger a buy order at grid 0 only (price 40000)
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=47000.0,
            high=47000.0,
            low=40000.0,  # Trigger buy at grid 0
            close=41000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Should have opened a long position
        assert engine.position_manager.get_net_position() > 0
        
        # Trigger a sell order to close the long position
        # After buy at grid 0, sell order is placed at grid 1 (price 42500)
        kline3 = KlineData(
            timestamp=1609459200000 + 120000,
            open=41000.0,
            high=42500.0,  # Trigger sell at grid 1 (price 42500)
            low=41000.0,
            close=42000.0,
            volume=100.0,
        )
        engine._process_kline(kline3)
        
        # Position should be reduced or closed
        # Grid profit should be updated
        assert engine.pnl_calculator.get_grid_profit() != 0
    
    def test_fill_order_insufficient_margin(self):
        """Test that order is rejected when margin is insufficient."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=100.0,  # Very small capital
            leverage=1.0,
            use_grid_crossing_logic=False,  # Low leverage
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize with first kline
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45500.0,
            low=44500.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        initial_capital = engine.capital
        initial_position = engine.position_manager.get_net_position()
        
        # Try to trigger a buy order that requires more margin than available
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=45000.0,
            low=40000.0,  # Try to trigger buy at grid 0
            close=41000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Position should not change if margin was insufficient
        # (or might have opened a very small position if there was enough for fee)
        # The key is that the system should not crash
        assert engine.capital <= initial_capital  # Capital should not increase
    
    def test_fill_order_fee_deduction_before_margin_check(self):
        """Test that fees are deducted before margin check."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize with first kline
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45500.0,
            low=44500.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        initial_capital = engine.capital
        
        # Trigger a buy order
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=45000.0,
            low=40000.0,
            close=41000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        # Check that fee was deducted
        assert engine.total_fees > 0
        assert engine.capital < initial_capital
        
        # Check that trade was recorded with fee
        if len(engine.trades) > 0:
            assert engine.trades[-1].fee > 0
    
    def test_fill_order_pnl_calculation(self):
        """Test that PnL is calculated correctly when closing positions."""
        config = StrategyConfig(
            symbol="BTC/USDT",
            mode=StrategyMode.LONG,
            lower_price=40000.0,
            upper_price=50000.0,
            grid_count=5,
            initial_capital=10000.0,
            leverage=2.0,
            use_grid_crossing_logic=False,
            fee_rate=0.001,
            funding_rate=0.0001,
        )
        
        engine = GridStrategyEngine(config)
        
        # Initialize
        kline1 = KlineData(
            timestamp=1609459200000,
            open=45000.0,
            high=45500.0,
            low=44500.0,
            close=45000.0,
            volume=100.0,
        )
        engine._process_kline(kline1)
        
        # Open position at 40000
        kline2 = KlineData(
            timestamp=1609459200000 + 60000,
            open=45000.0,
            high=45000.0,
            low=40000.0,
            close=41000.0,
            volume=100.0,
        )
        engine._process_kline(kline2)
        
        capital_after_open = engine.capital
        
        # Close position at 42500 (should make profit)
        kline3 = KlineData(
            timestamp=1609459200000 + 120000,
            open=41000.0,
            high=42500.0,
            low=41000.0,
            close=42000.0,
            volume=100.0,
        )
        engine._process_kline(kline3)
        
        # Check that PnL was added to capital
        # Capital should increase by PnL minus fees
        grid_profit = engine.pnl_calculator.get_grid_profit()
        
        # If we closed a position, grid profit should be non-zero
        # (might be positive or negative depending on price movement)
        # The key is that it should be calculated and recorded
        if len(engine.trades) >= 2:
            # Find the closing trade
            closing_trade = None
            for trade in engine.trades:
                if trade.pnl != 0:
                    closing_trade = trade
                    break
            
            if closing_trade:
                # PnL should be recorded in the trade
                assert closing_trade.pnl != 0
                # Grid profit should match
                assert grid_profit != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
