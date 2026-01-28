#!/usr/bin/env python3
"""Test script for strategy engine."""

from strategy_engine import (
    GridStrategyEngine,
    StrategyConfig,
    StrategyMode,
)
from market_data_layer.models import KlineData
from datetime import datetime, timedelta
import json


def generate_test_klines(symbol: str, count: int = 100) -> list:
    """Generate test K-line data.
    
    Args:
        symbol: Trading pair symbol
        count: Number of K-lines to generate
        
    Returns:
        List of KlineData objects
    """
    klines = []
    base_price = 50000.0 if "BTC" in symbol else 3000.0
    current_time = int(datetime.now().timestamp() * 1000)
    
    for i in range(count):
        # Generate price with some volatility
        price_change = (i % 20 - 10) * 100
        open_price = base_price + price_change
        high_price = open_price + 500
        low_price = open_price - 500
        close_price = open_price + (i % 5 - 2) * 100
        
        kline = KlineData(
            timestamp=current_time + i * 3600000,  # 1 hour intervals
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=1000000.0,
        )
        klines.append(kline)
    
    return klines


def test_long_strategy():
    """Test long grid strategy."""
    print("\n" + "="*60)
    print("  测试做多网格策略 (Long Grid Strategy)")
    print("="*60 + "\n")
    
    # Create strategy config
    config = StrategyConfig(
        symbol="BTC/USDT",
        mode=StrategyMode.LONG,
        lower_price=48000.0,
        upper_price=52000.0,
        grid_count=10,
        initial_capital=10000.0,
        fee_rate=0.0005,
    )
    
    # Create engine and execute
    engine = GridStrategyEngine(config)
    klines = generate_test_klines("BTC/USDT", 100)
    result = engine.execute(klines)
    
    # Print results
    print(f"📊 策略配置:")
    print(f"   币种: {result.symbol}")
    print(f"   模式: {result.mode.value}")
    print(f"   初始资金: ${result.initial_capital:,.2f}")
    print(f"   最终资金: ${result.final_capital:,.2f}")
    print(f"   总收益率: {result.total_return*100:.2f}%")
    print(f"\n📈 交易统计:")
    print(f"   总交易数: {result.total_trades}")
    print(f"   盈利交易: {result.winning_trades}")
    print(f"   亏损交易: {result.losing_trades}")
    print(f"   胜率: {result.win_rate*100:.2f}%")
    print(f"\n📉 风险指标:")
    print(f"   最大回撤: ${result.max_drawdown:,.2f}")
    print(f"   最大回撤率: {result.max_drawdown_pct*100:.2f}%")
    
    if result.trades:
        print(f"\n💰 前5笔交易:")
        for i, trade in enumerate(result.trades[:5]):
            timestamp = datetime.fromtimestamp(trade.timestamp / 1000)
            print(f"   交易 #{i+1}:")
            print(f"      时间: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"      方向: {trade.side.upper()}")
            print(f"      价格: ${trade.price:,.2f}")
            print(f"      数量: {trade.quantity:.4f}")
            print(f"      手续费: ${trade.fee:,.2f}")
            if trade.side == "sell":
                print(f"      盈亏: ${trade.pnl:,.2f}")


def test_short_strategy():
    """Test short grid strategy."""
    print("\n" + "="*60)
    print("  测试做空网格策略 (Short Grid Strategy)")
    print("="*60 + "\n")
    
    # Create strategy config
    config = StrategyConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.SHORT,
        lower_price=2800.0,
        upper_price=3200.0,
        grid_count=8,
        initial_capital=5000.0,
        fee_rate=0.0005,
    )
    
    # Create engine and execute
    engine = GridStrategyEngine(config)
    klines = generate_test_klines("ETH/USDT", 100)
    result = engine.execute(klines)
    
    # Print results
    print(f"📊 策略配置:")
    print(f"   币种: {result.symbol}")
    print(f"   模式: {result.mode.value}")
    print(f"   初始资金: ${result.initial_capital:,.2f}")
    print(f"   最终资金: ${result.final_capital:,.2f}")
    print(f"   总收益率: {result.total_return*100:.2f}%")
    print(f"\n📈 交易统计:")
    print(f"   总交易数: {result.total_trades}")
    print(f"   盈利交易: {result.winning_trades}")
    print(f"   亏损交易: {result.losing_trades}")
    print(f"   胜率: {result.win_rate*100:.2f}%")
    print(f"\n📉 风险指标:")
    print(f"   最大回撤: ${result.max_drawdown:,.2f}")
    print(f"   最大回撤率: {result.max_drawdown_pct*100:.2f}%")


def test_neutral_strategy():
    """Test neutral grid strategy."""
    print("\n" + "="*60)
    print("  测试中性网格策略 (Neutral Grid Strategy)")
    print("="*60 + "\n")
    
    # Create strategy config
    config = StrategyConfig(
        symbol="SOL/USDT",
        mode=StrategyMode.NEUTRAL,
        lower_price=100.0,
        upper_price=150.0,
        grid_count=10,
        initial_capital=3000.0,
        fee_rate=0.0005,
    )
    
    # Create engine and execute
    engine = GridStrategyEngine(config)
    klines = generate_test_klines("SOL/USDT", 100)
    result = engine.execute(klines)
    
    # Print results
    print(f"📊 策略配置:")
    print(f"   币种: {result.symbol}")
    print(f"   模式: {result.mode.value}")
    print(f"   初始资金: ${result.initial_capital:,.2f}")
    print(f"   最终资金: ${result.final_capital:,.2f}")
    print(f"   总收益率: {result.total_return*100:.2f}%")
    print(f"\n📈 交易统计:")
    print(f"   总交易数: {result.total_trades}")
    print(f"   盈利交易: {result.winning_trades}")
    print(f"   亏损交易: {result.losing_trades}")
    print(f"   胜率: {result.win_rate*100:.2f}%")
    print(f"\n📉 风险指标:")
    print(f"   最大回撤: ${result.max_drawdown:,.2f}")
    print(f"   最大回撤率: {result.max_drawdown_pct*100:.2f}%")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  🚀 策略引擎测试")
    print("="*60)
    
    try:
        test_long_strategy()
        test_short_strategy()
        test_neutral_strategy()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试完成！")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")


if __name__ == "__main__":
    main()
