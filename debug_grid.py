#!/usr/bin/env python3
"""Debug grid strategy order filling."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def debug_order_filling():
    """Debug order filling logic."""
    print("=== Debugging Order Filling ===")
    
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,
        initial_capital=10000,
        leverage=1.0
    )
    
    engine = GridStrategyEngine(config)
    
    # Initialize with price 3200
    kline1 = KlineData(timestamp=1000, open=3200, high=3200, low=3200, close=3200, volume=1000)
    engine._process_kline(kline1)
    
    print("After initialization at 3200:")
    print(f"Pending orders: {len(engine.pending_orders)}")
    for grid_idx, order in engine.pending_orders.items():
        print(f"  Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")
    print()
    
    # Test price 3300
    print("Testing price 3300:")
    kline2 = KlineData(timestamp=2000, open=3300, high=3300, low=3300, close=3300, volume=1000)
    
    # Manually check which orders should fill
    current_price = 3300
    print(f"Current price: {current_price}")
    for grid_idx, order in engine.pending_orders.items():
        should_fill = False
        if order.side == "buy" and current_price <= order.price:
            should_fill = True
        elif order.side == "sell" and current_price >= order.price:
            should_fill = True
        print(f"  Grid {grid_idx}: {order.side} @ {order.price} -> should fill: {should_fill}")
    
    print("\nProcessing kline...")
    before_trades = len(engine.trades)
    engine._process_kline(kline2)
    after_trades = len(engine.trades)
    
    print(f"New trades: {after_trades - before_trades}")
    if after_trades > before_trades:
        for trade in engine.trades[before_trades:]:
            print(f"  {trade.side} {trade.quantity:.4f} @ {trade.price}")
    
    print(f"Remaining pending orders: {len(engine.pending_orders)}")
    for grid_idx, order in engine.pending_orders.items():
        print(f"  Grid {grid_idx}: {order.side} {order.quantity:.4f} @ {order.price}")

if __name__ == "__main__":
    debug_order_filling()