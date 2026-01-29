#!/usr/bin/env python3
"""Test the final corrected grid strategy with leverage and initial positions."""

import sys
sys.path.append('.')

from strategy_engine.models import StrategyConfig, StrategyMode
from strategy_engine.engine import GridStrategyEngine
from market_data_layer.models import KlineData

def test_all_strategies():
    """Test all three strategies with leverage."""
    print("=== Testing All Grid Strategies with 2x Leverage ===")
    
    strategies = [
        ("Long Grid", StrategyMode.LONG),
        ("Short Grid", StrategyMode.SHORT),
        ("Neutral Grid", StrategyMode.NEUTRAL)
    ]
    
    # Test scenario: oscillating market
    test_prices = [3200, 3100, 3200, 3300, 3200, 3100, 3300, 3200]
    
    for strategy_name, mode in strategies:
        print(f"\n{'='*60}")
        print(f"Testing {strategy_name}")
        print('='*60)
        
        config = StrategyConfig(
            symbol="ETH/USDT",
            mode=mode,
            lower_price=3000,
            upper_price=3400,
            grid_count=5,
            initial_capital=10000,
            leverage=2.0
        )
        
        engine = GridStrategyEngine(config)
        
        # Create klines for the test scenario
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
        
        # Execute strategy
        result = engine.execute(klines)
        
        print(f"Initial capital: ${result.initial_capital:,.2f}")
        print(f"Final capital: ${result.final_capital:,.2f}")
        print(f"Total return: {result.total_return:.2%}")
        print(f"Total trades: {result.total_trades}")
        print(f"Winning trades: {result.winning_trades}")
        print(f"Win rate: {result.win_rate:.1%}")
        print(f"Total fees: ${result.total_fees:.2f}")
        print(f"Max drawdown: {result.max_drawdown_pct:.2%}")
        
        # Show profitable trades
        profitable_trades = [t for t in result.trades if t.pnl > 0]
        if profitable_trades:
            print(f"\nProfitable trades ({len(profitable_trades)}):")
            for trade in profitable_trades:
                print(f"  {trade.side} {trade.quantity:.4f} @ ${trade.price} -> PnL: ${trade.pnl:.2f}")
        
        print(f"\nFinal position size: {engine.position_size:.4f}")

if __name__ == "__main__":
    test_all_strategies()