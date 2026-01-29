#!/usr/bin/env python3
"""Test leverage and initial position functionality."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_leverage_and_initial_position():
    """Test leverage effect and initial position setup."""
    print("=== Testing Leverage and Initial Position ===")
    
    # Test with 2x leverage
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,  # [3000, 3100, 3200, 3300, 3400]
        initial_capital=10000,
        leverage=2.0  # 2x leverage
    )
    
    engine = GridStrategyEngine(config)
    print(f"Grid prices: {engine.strategy.grid_prices}")
    print(f"Grid gap: {engine.grid_gap}")
    print(f"Capital per grid: {engine.capital_per_grid}")
    print(f"Leverage: {engine.config.leverage}x")
    print()
    
    # Start at 3200 (middle of range) to test initial position setup
    start_price = 3200
    print(f"Starting at price: {start_price}")
    
    kline = KlineData(
        timestamp=1000,
        open=start_price,
        high=start_price,
        low=start_price,
        close=start_price,
        volume=1000
    )
    
    # Initialize
    engine._place_initial_orders(start_price)
    
    print(f"Initial position size: {engine.position_size:.4f}")
    print(f"Initial capital: {engine.capital:.2f}")
    
    print("\nInitial grid positions:")
    for grid_idx, position in engine.grid_positions.items():
        grid_price = config.lower_price + grid_idx * engine.grid_gap
        print(f"  Grid {grid_idx} @ {grid_price}: {position:.4f}")
    
    print("\nInitial pending orders:")
    for grid_idx, order in engine.pending_orders.items():
        print(f"  Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")
    
    # Test a price movement to see leverage effect
    print(f"\n--- Price moves to 3100 ---")
    kline2 = KlineData(
        timestamp=2000,
        open=3100,
        high=3100,
        low=3100,
        close=3100,
        volume=1000
    )
    
    before_capital = engine.capital
    before_position = engine.position_size
    before_trades = len(engine.trades)
    
    engine._process_kline(kline2)
    
    new_trades = len(engine.trades) - before_trades
    print(f"Capital change: {before_capital:.2f} -> {engine.capital:.2f} ({engine.capital - before_capital:.2f})")
    print(f"Position change: {before_position:.4f} -> {engine.position_size:.4f}")
    print(f"New trades: {new_trades}")
    
    if new_trades > 0:
        print("Recent trades:")
        for trade in engine.trades[-new_trades:]:
            print(f"  {trade.side} {trade.quantity:.4f} @ {trade.price} (PnL: {trade.pnl:.2f})")
    
    # Compare with 1x leverage
    print("\n" + "="*50)
    print("=== Comparing with 1x Leverage ===")
    
    config_1x = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,
        initial_capital=10000,
        leverage=1.0  # 1x leverage
    )
    
    engine_1x = GridStrategyEngine(config_1x)
    engine_1x._place_initial_orders(start_price)
    
    print(f"1x Leverage - Initial position: {engine_1x.position_size:.4f}")
    print(f"2x Leverage - Initial position: {engine.position_size:.4f}")
    ratio = engine.position_size / engine_1x.position_size if engine_1x.position_size != 0 else "N/A"
    if isinstance(ratio, str):
        print(f"Position ratio: {ratio}")
    else:
        print(f"Position ratio: {ratio:.2f}")
    
    print("\n1x Leverage - Pending orders:")
    for grid_idx, order in engine_1x.pending_orders.items():
        print(f"  Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")
    
    print("\n2x Leverage - Pending orders:")
    for grid_idx, order in engine.pending_orders.items():
        print(f"  Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")

if __name__ == "__main__":
    test_leverage_and_initial_position()