#!/usr/bin/env python3
"""Test the new initialization logic: start from earliest price to current position."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_start_from_earliest_price():
    """Test initialization from earliest price in time series."""
    print("=== Testing Start From Earliest Price ===")
    
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=3000,
        upper_price=3400,
        grid_count=5,  # [3000, 3100, 3200, 3300, 3400]
        initial_capital=10000,
        leverage=2.0
    )
    
    engine = GridStrategyEngine(config)
    print(f"Grid prices: {engine.strategy.grid_prices}")
    print(f"Grid gap: {engine.grid_gap}")
    print()
    
    # 创建测试数据：从3150开始，到3250结束
    test_prices = [3150, 3180, 3200, 3220, 3250]  # 时间序列价格
    klines = []
    
    for i, price in enumerate(test_prices):
        kline = KlineData(
            timestamp=i * 1000,
            open=price,
            high=price + 10,
            low=price - 10,
            close=price,
            volume=1000
        )
        klines.append(kline)
    
    print(f"Price series: {test_prices}")
    print(f"Start price (earliest): {test_prices[0]}")
    print(f"End price (current): {test_prices[-1]}")
    print()
    
    # 执行策略
    result = engine.execute(klines)
    
    print("=== Strategy Results ===")
    print(f"Initial capital: ${result.initial_capital:,.2f}")
    print(f"Final capital: ${result.final_capital:,.2f}")
    print(f"Total return: {result.total_return:.2%}")
    print(f"Total trades: {result.total_trades}")
    print(f"Final position: {engine.position_size:.4f}")
    
    print("\n=== Grid Positions Built ===")
    for grid_idx, position in engine.grid_positions.items():
        grid_price = config.lower_price + grid_idx * engine.grid_gap
        if position != 0:
            print(f"  Grid {grid_idx} @ ${grid_price}: {position:.4f}")
    
    print("\n=== All Trades ===")
    for i, trade in enumerate(result.trades):
        print(f"{i+1}. {trade.side} {trade.quantity:.4f} @ ${trade.price} (PnL: ${trade.pnl:.2f})")

if __name__ == "__main__":
    test_start_from_earliest_price()