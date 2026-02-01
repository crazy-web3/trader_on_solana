"""对比DeepSeek的网格逻辑和我们的实现"""

import numpy as np
from strategy_engine import GridStrategyEngine, StrategyConfig, StrategyMode
from market_data_layer.models import KlineData

# 创建简单的测试数据：价格从3000下跌到2500
# 使用更合理的K线数据：high=low=close（无内部波动）
prices = [3000, 2900, 2800, 2700, 2600, 2500]
klines = [
    KlineData(
        timestamp=i*3600000,
        open=price,
        high=price,  # 改为等于close，避免K线内部波动
        low=price,   # 改为等于close
        close=price,
        volume=100.0
    )
    for i, price in enumerate(prices)
]

print("=" * 80)
print("网格逻辑对比测试")
print("=" * 80)
print(f"价格序列: {prices}")
print(f"价格变化: {prices[0]} -> {prices[-1]} (下跌 {(prices[-1]-prices[0])/prices[0]*100:.2f}%)")
print()

# ============================================================================
# DeepSeek的简化逻辑
# ============================================================================
print("=" * 80)
print("DeepSeek的网格逻辑（简化版）")
print("=" * 80)

grid_low = 2500
grid_high = 3000
grid_step = 100
grids = np.arange(grid_low, grid_high + grid_step, grid_step)
initial_capital = 10000
grid_capital = initial_capital / len(grids)

print(f"网格: {grids}")
print(f"每个网格资金: ${grid_capital:.2f}")
print()

# 做空网格逻辑
capital_short = initial_capital
trades_short = []

for i in range(1, len(prices)):
    price = prices[i]
    prev_price = prices[i-1]
    
    # 找到当前和上一个价格所在的网格索引
    current_index = np.searchsorted(grids, price) - 1
    prev_index = np.searchsorted(grids, prev_price) - 1
    
    if current_index < 0:
        current_index = 0
    if prev_index < 0:
        prev_index = 0
    
    print(f"步骤 {i}: 价格 {prev_price} -> {price}")
    print(f"  网格索引: {prev_index} -> {current_index}")
    
    # 做空网格：价格下跌时盈利
    if current_index < prev_index:  # 修正：索引变小=价格下跌
        # 价格下跌，跨越了网格
        for idx in range(current_index, prev_index):
            if idx >= 0 and idx < len(grids) - 1:
                # 计算这个网格的收益
                # 做空：在上一个网格卖出，在当前网格买入
                sell_price = grids[idx+1]
                buy_price = grids[idx]
                profit = (sell_price - buy_price) * (grid_capital / sell_price)
                capital_short += profit
                trades_short.append({
                    'grid': idx,
                    'sell': sell_price,
                    'buy': buy_price,
                    'profit': profit
                })
                print(f"  ✓ 做空网格 {idx}: 卖@{sell_price} 买@{buy_price}, 收益=${profit:.2f}")
    
    print(f"  当前资金: ${capital_short:.2f}")
    print()

print(f"DeepSeek做空网格最终资金: ${capital_short:.2f}")
print(f"DeepSeek做空网格收益: ${capital_short - initial_capital:.2f} ({(capital_short/initial_capital-1)*100:.2f}%)")
print(f"交易次数: {len(trades_short)}")
print()

# ============================================================================
# 我们的实现
# ============================================================================
print("=" * 80)
print("我们的网格实现")
print("=" * 80)

config = StrategyConfig(
    symbol="TEST/USDT",
    mode=StrategyMode.SHORT,
    lower_price=grid_low,
    upper_price=grid_high,
    grid_count=len(grids),
    initial_capital=initial_capital,
    fee_rate=0.0,
    leverage=1.0,
    funding_rate=0.0,
    funding_interval=8,
    entry_price=prices[0]
)

engine = GridStrategyEngine(config)
result = engine.execute(klines)

print(f"我们的做空网格最终资金: ${result.final_capital:.2f}")
print(f"我们的做空网格收益: ${result.final_capital - initial_capital:.2f} ({result.total_return:.2f}%)")
print(f"网格收益: ${result.grid_profit:.2f}")
print(f"未实现盈亏: ${result.unrealized_pnl:.2f}")
print(f"交易次数: {result.total_trades}")
print()

print("交易详情:")
for i, trade in enumerate(result.trades):
    print(f"  {i+1}. {trade.side} {trade.quantity:.6f} @ ${trade.price:.2f}, PnL=${trade.pnl:.2f}")
print()

# ============================================================================
# 对比分析
# ============================================================================
print("=" * 80)
print("对比分析")
print("=" * 80)

diff = result.final_capital - capital_short
print(f"资金差异: ${diff:.2f}")
print(f"收益差异: {(result.total_return - (capital_short/initial_capital-1))*100:.2f}%")
print()

if abs(diff) > 1:
    print("⚠️  两种实现的结果不一致！")
    print()
    print("可能的原因:")
    print("1. 订单成交逻辑不同")
    print("2. 仓位配对逻辑不同")
    print("3. 收益计算方式不同")
    print()
    print("DeepSeek的逻辑更简单直接：")
    print("- 价格跨越网格时直接计算收益")
    print("- 不需要复杂的订单管理")
    print("- 更接近理论收益")
    print()
    print("我们的逻辑更接近实际交易：")
    print("- 模拟真实的订单成交")
    print("- 考虑仓位管理")
    print("- 但可能在某些情况下计算不准确")
else:
    print("✅ 两种实现的结果一致！")
