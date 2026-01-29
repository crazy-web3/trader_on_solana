#!/usr/bin/env python3
"""Test the short grid strategy implementation."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_short_grid():
    """Test short grid with correct logic."""
    print("=== Testing Short Grid Strategy ===")
    
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.SHORT,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,  # [3000, 3100, 3200, 3300, 3400]
        initial_capital=10000,
        leverage=1.0
    )
    
    engine = GridStrategyEngine(config)
    print(f"Grid prices: {engine.strategy.grid_prices}")
    print(f"Grid gap: {engine.grid_gap}")
    print(f"Capital per grid: {engine.capital_per_grid}")
    print()
    
    # Test scenario for short grid: start at 3200, oscillate to show profit
    # Short grid should: sell high, buy low (cover)
    test_scenario = [
        (3200, "Start at 3200 - should place initial sell orders above current price"),
        (3300, "Rise to 3300 - should fill sell order at 3300"),
        (3200, "Drop to 3200 - should fill buy order at 3200 (profit: 100 * quantity)"),
        (3300, "Rise to 3300 - should fill sell order at 3300 again"),
        (3100, "Drop to 3100 - should fill buy orders (profit on both)"),
        (3200, "Rise to 3200 - should fill sell order at 3200"),
    ]
    
    for i, (price, description) in enumerate(test_scenario):
        print(f"Step {i+1}: {description}")
        print(f"Price: {price}")
        
        kline = KlineData(
            timestamp=i * 1000,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000
        )
        
        before_capital = engine.capital
        before_position = engine.position_size
        before_trades = len(engine.trades)
        before_orders = len(engine.pending_orders)
        
        engine._process_kline(kline)
        
        new_trades = len(engine.trades) - before_trades
        
        print(f"  Capital: {before_capital:.2f} -> {engine.capital:.2f} (change: {engine.capital - before_capital:.2f})")
        print(f"  Position: {before_position:.4f} -> {engine.position_size:.4f}")
        print(f"  Pending orders: {before_orders} -> {len(engine.pending_orders)}")
        print(f"  New trades: {new_trades}")
        
        if new_trades > 0:
            print("  Recent trades:")
            for trade in engine.trades[-new_trades:]:
                print(f"    {trade.side} {trade.quantity:.4f} @ {trade.price} (PnL: {trade.pnl:.2f}, Fee: {trade.fee:.2f})")
        
        print(f"  Grid positions:")
        for grid_idx, position in engine.grid_positions.items():
            grid_price = config.lower_price + grid_idx * engine.grid_gap
            print(f"    Grid {grid_idx} @ {grid_price}: {position:.4f}")
        
        print(f"  Pending orders:")
        for grid_idx, order in engine.pending_orders.items():
            print(f"    Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")
        
        print()
    
    # Final summary
    final_result = engine._calculate_result()
    print("=== Final Results ===")
    print(f"Initial capital: {config.initial_capital}")
    print(f"Final capital: {final_result.final_capital:.2f}")
    print(f"Total return: {final_result.total_return:.2%}")
    print(f"Total trades: {final_result.total_trades}")
    print(f"Winning trades: {final_result.winning_trades}")
    print(f"Total fees: {final_result.total_fees:.2f}")
    
    # Show all trades
    print("\n=== All Trades ===")
    for i, trade in enumerate(engine.trades):
        print(f"{i+1}. {trade.side} {trade.quantity:.4f} @ {trade.price} (PnL: {trade.pnl:.2f}, Fee: {trade.fee:.2f})")

if __name__ == "__main__":
    test_short_grid()