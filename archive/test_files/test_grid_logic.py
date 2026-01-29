#!/usr/bin/env python3
"""Test grid strategy logic with simple scenarios."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode, GridStrategy
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_basic_grid_setup():
    """Test basic grid setup."""
    print("=== Testing Basic Grid Setup ===")
    
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,  # Simple 5-level grid
        initial_capital=10000,
        leverage=1.0
    )
    
    strategy = GridStrategy(config)
    print(f"Grid prices: {strategy.grid_prices}")
    print(f"Grid spacing: {strategy.grid_prices[1] - strategy.grid_prices[0]}")
    print(f"Expected spacing: {(3400-3000)/(5-1)} = 100")
    print()

def test_long_strategy_step_by_step():
    """Test long strategy step by step with detailed analysis."""
    print("=== Testing Long Strategy Step by Step ===")
    
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
    print("Expected behavior:")
    print("- At price 3200: should buy at grids where 3200 <= grid_price (i.e., 3200)")
    print("- At price 3100: should buy at grids where 3100 <= grid_price (i.e., 3100, 3200, 3300, 3400)")
    print("- At price 3300: should sell positions where 3300 > grid_price")
    print()
    
    # Test case 1: Price starts at 3200
    print("Test 1: Price = 3200 (should trigger buy at grid 3200 only)")
    kline = KlineData(timestamp=1000, open=3200, high=3200, low=3200, close=3200, volume=1000)
    
    print("Before trade:")
    print(f"  Capital: {engine.capital}")
    print(f"  Position: {engine.position_size}")
    print(f"  Grid status: {engine.strategy.grid_status}")
    
    engine._process_kline(kline)
    
    print("After trade:")
    print(f"  Capital: {engine.capital}")
    print(f"  Position: {engine.position_size}")
    print(f"  Grid status: {engine.strategy.grid_status}")
    print(f"  Trades: {len(engine.trades)}")
    
    for i, trade in enumerate(engine.trades):
        print(f"    Trade {i+1}: {trade.side} {trade.quantity:.4f} @ {trade.price}")
    
    print()

def test_grid_logic_manually():
    """Manually test what should happen at each price level."""
    print("=== Manual Grid Logic Test ===")
    
    grid_prices = [3000, 3100, 3200, 3300, 3400]
    current_price = 3200
    
    print(f"Grid prices: {grid_prices}")
    print(f"Current price: {current_price}")
    print()
    
    print("For LONG strategy at price 3200:")
    print("  Logic: Buy when current_price <= grid_price (buy at or below grid level)")
    for i, grid_price in enumerate(grid_prices):
        should_buy = current_price <= grid_price
        print(f"  Grid {i} (${grid_price}): Should buy = {should_buy} ({current_price} <= {grid_price})")
    
    print()
    print("For SHORT strategy at price 3200:")
    print("  Logic: Sell when current_price >= grid_price (sell at or above grid level)")
    for i, grid_price in enumerate(grid_prices):
        should_sell = current_price >= grid_price
        print(f"  Grid {i} (${grid_price}): Should sell = {should_sell} ({current_price} >= {grid_price})")

if __name__ == "__main__":
    test_basic_grid_setup()
    test_grid_logic_manually()
    test_long_strategy_step_by_step()