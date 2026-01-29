#!/usr/bin/env python3
"""Test script for backtest engine."""

from backtest_engine import (
    BacktestEngine,
    GridSearchOptimizer,
    BacktestConfig,
    StrategyMode,
)
from datetime import datetime, timedelta


def test_single_backtest():
    """Test single backtest."""
    print("\n" + "="*60)
    print("  测试单参数回测 (Single Parameter Backtest)")
    print("="*60 + "\n")
    
    # Create backtest config
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 1 year
    
    config = BacktestConfig(
        symbol="BTC/USDT",
        mode=StrategyMode.LONG,
        lower_price=40000.0,
        upper_price=60000.0,
        grid_count=10,
        initial_capital=10000.0,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        fee_rate=0.0005,
    )
    
    # Run backtest
    engine = BacktestEngine()
    result = engine.run_backtest(config)
    
    # Print results
    print(f"📊 回测配置:")
    print(f"   币种: {result.config.symbol}")
    print(f"   模式: {result.config.mode.value}")
    print(f"   时间范围: {result.config.start_date} 到 {result.config.end_date}")
    print(f"   初始资金: ${result.initial_capital:,.2f}")
    print(f"   最终资金: ${result.final_capital:,.2f}")
    
    print(f"\n📈 性能指标:")
    print(f"   总收益率: {result.metrics.total_return*100:.2f}%")
    print(f"   年化收益: {result.metrics.annual_return*100:.2f}%")
    print(f"   最大回撤: {result.metrics.max_drawdown*100:.2f}%")
    print(f"   Sharpe比率: {result.metrics.sharpe_ratio:.2f}")
    
    print(f"\n💰 交易统计:")
    print(f"   总交易数: {result.metrics.total_trades}")
    print(f"   盈利交易: {result.metrics.winning_trades}")
    print(f"   亏损交易: {result.metrics.losing_trades}")
    print(f"   胜率: {result.metrics.win_rate*100:.2f}%")
    
    print(f"\n💸 费用统计:")
    print(f"   总手续费: ${result.metrics.fee_cost:,.2f}")
    print(f"   手续费占比: {result.metrics.fee_ratio*100:.2f}%")


def test_grid_search():
    """Test grid search optimization."""
    print("\n" + "="*60)
    print("  测试参数遍历 (Grid Search Optimization)")
    print("="*60 + "\n")
    
    # Create base config
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months
    
    base_config = BacktestConfig(
        symbol="ETH/USDT",
        mode=StrategyMode.LONG,
        lower_price=2500.0,
        upper_price=3500.0,
        grid_count=10,
        initial_capital=5000.0,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        fee_rate=0.0005,
    )
    
    # Define parameter ranges
    parameter_ranges = {
        "grid_count": [5, 10, 15],
        "lower_price": [2400, 2500, 2600],
        "upper_price": [3400, 3500, 3600],
    }
    
    # Run grid search
    optimizer = GridSearchOptimizer()
    result = optimizer.optimize(
        base_config,
        parameter_ranges,
        metric="total_return",
    )
    
    # Print results
    print(f"📊 最优参数:")
    for param, value in result.best_params.items():
        print(f"   {param}: {value}")
    
    print(f"\n📈 最优结果:")
    print(f"   总收益率: {result.best_result.metrics.total_return*100:.2f}%")
    print(f"   年化收益: {result.best_result.metrics.annual_return*100:.2f}%")
    print(f"   最大回撤: {result.best_result.metrics.max_drawdown*100:.2f}%")
    print(f"   Sharpe比率: {result.best_result.metrics.sharpe_ratio:.2f}%")
    
    print(f"\n📋 所有结果 (前5个):")
    for i, res in enumerate(result.all_results[:5]):
        print(f"   结果 #{i+1}:")
        print(f"      网格数: {res.config.grid_count}")
        print(f"      收益率: {res.metrics.total_return*100:.2f}%")
        print(f"      最大回撤: {res.metrics.max_drawdown*100:.2f}%")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("  🚀 回测引擎测试")
    print("="*60)
    
    try:
        test_single_backtest()
        test_grid_search()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试完成！")
        print("="*60 + "\n")
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}\n")


if __name__ == "__main__":
    main()
