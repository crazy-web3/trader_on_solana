#!/usr/bin/env python3
"""Test complete grid strategy cycle."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_complete_long_cycle():
    """Test a complete long strategy cycle."""
    print("=== Testing Complete Long Strategy Cycle ===")
    
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,  # [3000, 3100, 3200, 3300, 3400]
        initial_capital=10000,
        leverage=1.0
    )
    
    engine = GridStrategyEngine(config)
    print(f"Grid prices: {engine.strategy.grid_prices}")
    print(f"Initial capital: {engine.capital}")
    print()
    
    # Simulate a complete cycle: start middle, go down, then up
    test_scenario = [
        (3200, "Start at middle price"),
        (3100, "Price drops - should trigger more buys"),
        (3000, "Price drops further - should trigger more buys"),
        (3100, "Price rises - should trigger some sells"),
        (3200, "Price rises more - should trigger more sells"),
        (3300, "Price rises further - should trigger more sells"),
        (3200, "Price drops - should trigger some buys"),
        (3100, "Price drops more - should trigger more buys"),
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
        
        engine._process_kline(kline)
        
        new_trades = len(engine.trades) - before_trades
        
        print(f"  Capital: {before_capital:.2f} -> {engine.capital:.2f} (change: {engine.capital - before_capital:.2f})")
        print(f"  Position: {before_position:.4f} -> {engine.position_size:.4f}")
        print(f"  New trades: {new_trades}")
        print(f"  Grid status: {engine.strategy.grid_status}")
        
        if new_trades > 0:
            print("  Recent trades:")
            for trade in engine.trades[-new_trades:]:
                print(f"    {trade.side} {trade.quantity:.4f} @ {trade.price} (PnL: {trade.pnl:.2f})")
        
        print()
    
    # Final summary
    final_result = engine._calculate_result()
    print("=== Final Results ===")
    print(f"Initial capital: {config.initial_capital}")
    print(f"Final capital: {final_result.final_capital:.2f}")
    print(f"Total return: {final_result.total_return:.2%}")
    print(f"Total trades: {final_result.total_trades}")
    print(f"Winning trades: {final_result.winning_trades}")
    print(f"Losing trades: {final_result.losing_trades}")

if __name__ == "__main__":
    test_complete_long_cycle()