# 优化版本快速开始指南

## 概述

本指南帮助你快速使用优化后的合约网格交易回测引擎。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 基础使用

### 1. 简单回测

```python
from backtest_engine.optimized_engine import OptimizedBacktestEngine
from backtest_engine.models import BacktestConfig, StrategyMode
from strategy_engine.models import GridType

# 创建回测配置
config = BacktestConfig(
    symbol="BTCUSDT",
    mode=StrategyMode.LONG,  # 做多网格
    lower_price=40000,
    upper_price=50000,
    grid_count=20,
    initial_capital=10000,
    start_date="2023-01-01",
    end_date="2023-12-31",
    fee_rate=0.0005,  # 0.05% 手续费
    leverage=2.0,  # 2倍杠杆
)

# 运行回测
engine = OptimizedBacktestEngine()
result = engine.run_backtest(config, grid_type=GridType.ARITHMETIC)

# 查看结果
print(f"初始资本: {result.initial_capital:.2f}")
print(f"最终资本: {result.final_capital:.2f}")
print(f"总收益率: {result.metrics.total_return:.2%}")
print(f"年化收益率: {result.metrics.annual_return:.2%}")
print(f"最大回撤: {result.metrics.max_drawdown:.2%}")
print(f"夏普比率: {result.metrics.sharpe_ratio:.2f}")
print(f"胜率: {result.metrics.win_rate:.2%}")
print(f"交易数: {result.metrics.total_trades}")
print(f"已撮合收益: {result.metrics.grid_profit:.2f}")
print(f"未撮合盈亏: {result.metrics.unrealized_pnl:.2f}")
print(f"手续费: {result.metrics.fee_cost:.2f}")
```

### 2. 不同网格类型

#### 等差网格
```python
# 价差相等，适合价格波动较小的情况
result = engine.run_backtest(config, grid_type=GridType.ARITHMETIC)
```

#### 等比网格
```python
# 价格比率相等，适合价格波动较大的情况
result = engine.run_backtest(config, grid_type=GridType.GEOMETRIC)
```

### 3. 不同交易模式

#### 做多网格
```python
config.mode = StrategyMode.LONG
# 低价买入，高价卖出
# 适合看涨行情
```

#### 做空网格
```python
config.mode = StrategyMode.SHORT
# 高价卖出，低价买入
# 适合看跌行情
```

#### 中性网格
```python
config.mode = StrategyMode.NEUTRAL
# 低买高卖，不预判方向
# 适合震荡行情
```

## 高级使用

### 1. 网格搜索优化

```python
# 搜索最优的网格数和杠杆
search_results = engine.run_grid_search(
    config,
    grid_count_range=(5, 50),      # 网格数范围
    leverage_range=(1.0, 10.0),    # 杠杆范围
    grid_type=GridType.ARITHMETIC,
)

# 获取最优结果
best_result = search_results["best_result"]
best_params = search_results["best_params"]

print(f"最优网格数: {best_params['grid_count']}")
print(f"最优杠杆: {best_params['leverage']}")
print(f"最优收益率: {best_result.metrics.total_return:.2%}")
```

### 2. 多个交易对对比

```python
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
results = {}

for symbol in symbols:
    config.symbol = symbol
    result = engine.run_backtest(config)
    results[symbol] = result
    print(f"{symbol}: {result.metrics.total_return:.2%}")
```

### 3. 参数敏感性分析

```python
# 测试不同的网格数
grid_counts = [5, 10, 15, 20, 25, 30]
results = []

for grid_count in grid_counts:
    config.grid_count = grid_count
    result = engine.run_backtest(config)
    results.append({
        "grid_count": grid_count,
        "return": result.metrics.total_return,
        "sharpe": result.metrics.sharpe_ratio,
    })

# 找到最优网格数
best = max(results, key=lambda x: x["return"])
print(f"最优网格数: {best['grid_count']}")
```

## 关键参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `symbol` | 交易对 | "BTCUSDT" |
| `mode` | 交易模式 | StrategyMode.LONG |
| `lower_price` | 网格下限 | 40000 |
| `upper_price` | 网格上限 | 50000 |
| `grid_count` | 网格数量 | 20 |
| `initial_capital` | 初始资本 | 10000 |
| `start_date` | 开始日期 | "2023-01-01" |
| `end_date` | 结束日期 | "2023-12-31" |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `fee_rate` | 0.0005 | 手续费率（0.05%） |
| `leverage` | 1.0 | 杠杆倍数 |
| `funding_rate` | 0.0 | 资金费率 |
| `funding_interval` | 8 | 资金费间隔（小时） |
| `grid_type` | ARITHMETIC | 网格类型 |

## 常见问题

### Q1: 如何选择网格数？

**A**: 
- 网格数越多，交易频率越高，每笔收益越低
- 网格数越少，交易频率越低，每笔收益越高
- 建议使用网格搜索找到最优值

```python
# 快速测试
for grid_count in [5, 10, 15, 20, 25]:
    config.grid_count = grid_count
    result = engine.run_backtest(config)
    print(f"网格数 {grid_count}: {result.metrics.total_return:.2%}")
```

### Q2: 等差和等比网格有什么区别？

**A**:
- **等差网格**：价差相等，适合价格波动较小的情况
- **等比网格**：价格比率相等，适合价格波动较大的情况

```python
# 等差网格：1000, 1100, 1200, 1300...（差100）
result_arithmetic = engine.run_backtest(config, grid_type=GridType.ARITHMETIC)

# 等比网格：1000, 1100, 1210, 1331...（比10%）
result_geometric = engine.run_backtest(config, grid_type=GridType.GEOMETRIC)
```

### Q3: 杠杆应该设置多少？

**A**:
- 杠杆放大收益，也放大风险
- 建议从1倍开始，逐步增加
- 注意风险率不要低于1.0

```python
# 测试不同杠杆
for leverage in [1.0, 2.0, 3.0, 5.0]:
    config.leverage = leverage
    result = engine.run_backtest(config)
    print(f"杠杆 {leverage}x: {result.metrics.total_return:.2%}")
```

### Q4: 如何理解已撮合收益和未撮合盈亏？

**A**:
- **已撮合收益**：已完成的买卖配对的利润
- **未撮合盈亏**：当前未平仓头寸的浮动盈亏
- **总收益** = 已撮合收益 + 未撮合盈亏 + 资金费用

```python
print(f"已撮合收益: {result.metrics.grid_profit:.2f}")
print(f"未撮合盈亏: {result.metrics.unrealized_pnl:.2f}")
print(f"资金费用: {result.metrics.funding_cost:.2f}")
print(f"总收益: {result.final_capital - result.initial_capital:.2f}")
```

## 性能优化建议

### 1. 减少回测时间范围
```python
# 从1年改为3个月
config.start_date = "2023-10-01"
config.end_date = "2023-12-31"
```

### 2. 使用更大的时间间隔
```python
# 使用周线而不是日线（需要修改数据获取）
# 这样可以减少数据点数量
```

### 3. 并行化网格搜索
```python
# 使用多进程加速网格搜索
from multiprocessing import Pool

def run_config(params):
    config.grid_count = params[0]
    config.leverage = params[1]
    return engine.run_backtest(config)

# 并行执行
with Pool(4) as p:
    results = p.map(run_config, parameter_combinations)
```

## 导出结果

### 导出为JSON
```python
import json

result_dict = result.to_dict()
with open("backtest_result.json", "w") as f:
    json.dump(result_dict, f, indent=2)
```

### 导出为CSV
```python
import pandas as pd

# 交易记录
trades_df = pd.DataFrame(result.trades)
trades_df.to_csv("trades.csv", index=False)

# 权益曲线
equity_df = pd.DataFrame({
    "timestamp": result.timestamps,
    "equity": result.equity_curve,
})
equity_df.to_csv("equity_curve.csv", index=False)
```

## 下一步

1. 阅读 **OPTIMIZATION_DETAILS.md** 了解详细的算法说明
2. 查看 **OPTIMIZATION_SUMMARY.md** 了解优化内容
3. 运行单元测试验证功能
4. 在实盘前充分回测和优化参数

## 获取帮助

- 查看 **OPTIMIZATION_DETAILS.md** 中的公式和算法
- 查看源代码中的注释
- 运行示例代码学习用法

---

**提示**：优化版本与原始版本的API基本兼容，但建议使用新的 `OptimizedBacktestEngine` 和 `OptimizedGridStrategyEngine` 以获得最佳效果。
