# 🚀 回测引擎快速开始指南

## 📋 概述

回测引擎支持两种模式：
1. **单参数回测** - 用固定参数回测历史数据
2. **参数遍历** - 自动测试多个参数组合，找到最优参数

---

## 🔧 安装与启动

### 1. 安装依赖
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 启动 Flask 服务器
```bash
python3 app.py
```

服务器将在 `http://localhost:5001` 启动

### 3. 运行测试
```bash
python3 test_backtest.py
```

---

## 💻 使用方式

### 方式1: Python 代码

#### 单参数回测
```python
from backtest_engine import BacktestEngine, BacktestConfig, StrategyMode
from datetime import datetime, timedelta

# 创建回测配置
end_date = datetime.now()
start_date = end_date - timedelta(days=365)

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

# 运行回测
engine = BacktestEngine()
result = engine.run_backtest(config)

# 查看结果
print(f"总收益率: {result.metrics.total_return*100:.2f}%")
print(f"年化收益: {result.metrics.annual_return*100:.2f}%")
print(f"最大回撤: {result.metrics.max_drawdown*100:.2f}%")
print(f"Sharpe比率: {result.metrics.sharpe_ratio:.2f}")
print(f"胜率: {result.metrics.win_rate*100:.2f}%")
print(f"手续费占比: {result.metrics.fee_ratio*100:.2f}%")
```

#### 参数遍历 (Grid Search)
```python
from backtest_engine import GridSearchOptimizer

# 定义参数范围
parameter_ranges = {
    "grid_count": [5, 10, 15, 20],
    "lower_price": [38000, 40000, 42000],
    "upper_price": [58000, 60000, 62000],
}

# 运行 Grid Search
optimizer = GridSearchOptimizer(engine)
gs_result = optimizer.optimize(
    config,
    parameter_ranges,
    metric="total_return"  # 优化指标
)

# 查看最优结果
print(f"最优参数: {gs_result.best_params}")
print(f"最优收益率: {gs_result.best_result.metrics.total_return*100:.2f}%")

# 查看所有结果
for i, result in enumerate(gs_result.all_results):
    print(f"结果 #{i+1}: {result.metrics.total_return*100:.2f}%")
```

---

### 方式2: API 调用

#### 单参数回测
```bash
curl -X POST http://localhost:5001/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "mode": "long",
    "lower_price": 40000,
    "upper_price": 60000,
    "grid_count": 10,
    "initial_capital": 10000,
    "start_date": "2025-01-28",
    "end_date": "2026-01-28"
  }'
```

#### 参数遍历
```bash
curl -X POST http://localhost:5001/api/backtest/grid-search \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "mode": "long",
    "lower_price": 40000,
    "upper_price": 60000,
    "grid_count": 10,
    "initial_capital": 10000,
    "start_date": "2025-01-28",
    "end_date": "2026-01-28",
    "parameter_ranges": {
      "grid_count": [5, 10, 15, 20],
      "lower_price": [38000, 40000, 42000],
      "upper_price": [58000, 60000, 62000]
    },
    "metric": "total_return"
  }'
```

---

## 📊 参数说明

### 回测配置参数

| 参数 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `symbol` | string | 交易对 | "BTC/USDT" |
| `mode` | string | 策略模式 | "long", "short", "neutral" |
| `lower_price` | float | 下限价格 | 40000 |
| `upper_price` | float | 上限价格 | 60000 |
| `grid_count` | int | 网格数量 | 10 |
| `initial_capital` | float | 初始资金 | 10000 |
| `start_date` | string | 开始日期 | "2025-01-28" |
| `end_date` | string | 结束日期 | "2026-01-28" |
| `fee_rate` | float | 手续费率 | 0.0005 |

### 优化指标

| 指标 | 说明 |
|------|------|
| `total_return` | 总收益率 (最直接) |
| `annual_return` | 年化收益 (标准化) |
| `sharpe_ratio` | Sharpe比率 (风险调整) |
| `win_rate` | 胜率 (稳定性) |

---

## 📈 输出指标

### 性能指标

| 指标 | 说明 | 公式 |
|------|------|------|
| `total_return` | 总收益率 | (最终资金 - 初始资金) / 初始资金 |
| `annual_return` | 年化收益 | (1 + 总收益率) ^ (1 / 年数) - 1 |
| `max_drawdown` | 最大回撤 | (最高权益 - 最低权益) / 最高权益 |
| `sharpe_ratio` | Sharpe比率 | (平均日收益 / 日收益标准差) * sqrt(252) |
| `win_rate` | 胜率 | 盈利交易数 / 总交易数 |
| `fee_ratio` | 手续费占比 | 总手续费 / 初始资金 |

### 交易统计

| 指标 | 说明 |
|------|------|
| `total_trades` | 总交易数 |
| `winning_trades` | 盈利交易数 |
| `losing_trades` | 亏损交易数 |
| `fee_cost` | 总手续费 |

---

## 🎯 常见用例

### 用例1: 测试单个策略
```python
# 用固定参数回测一个策略
config = BacktestConfig(
    symbol="BTC/USDT",
    mode=StrategyMode.LONG,
    lower_price=40000,
    upper_price=60000,
    grid_count=10,
    initial_capital=10000,
    start_date="2025-01-28",
    end_date="2026-01-28",
)

engine = BacktestEngine()
result = engine.run_backtest(config)
```

### 用例2: 找到最优网格数量
```python
# 测试不同的网格数量
parameter_ranges = {
    "grid_count": [5, 10, 15, 20, 25],
}

optimizer = GridSearchOptimizer(engine)
result = optimizer.optimize(config, parameter_ranges, metric="total_return")
```

### 用例3: 优化价格范围
```python
# 测试不同的价格范围
parameter_ranges = {
    "lower_price": [38000, 40000, 42000],
    "upper_price": [58000, 60000, 62000],
}

optimizer = GridSearchOptimizer(engine)
result = optimizer.optimize(config, parameter_ranges, metric="sharpe_ratio")
```

### 用例4: 全面参数优化
```python
# 同时优化所有参数
parameter_ranges = {
    "grid_count": [5, 10, 15, 20],
    "lower_price": [38000, 40000, 42000],
    "upper_price": [58000, 60000, 62000],
}

optimizer = GridSearchOptimizer(engine)
result = optimizer.optimize(config, parameter_ranges, metric="total_return")

# 查看最优参数
print(f"最优参数: {result.best_params}")
print(f"最优收益率: {result.best_result.metrics.total_return*100:.2f}%")
```

---

## ⚠️ 注意事项

### 时间范围
- 最多支持3年历史数据
- 日期格式: YYYY-MM-DD
- 开始日期 < 结束日期

### 参数范围
- 网格数量: 2-100
- 价格: 必须为正数
- 下限价格 < 上限价格

### Grid Search 性能
- 组合数 = 各参数范围长度的乘积
- 例如: 4 × 3 × 3 = 36 个组合
- 每个组合需要完整的回测
- 建议参数范围不要过大

---

## 🐛 常见问题

### Q: 回测没有交易怎么办？
A: 检查价格范围是否与历史数据相符。如果价格范围太窄或太宽，可能没有交易。

### Q: Grid Search 太慢怎么办？
A: 减少参数范围的长度。例如，从 4 个值减少到 3 个值。

### Q: 如何选择优化指标？
A: 
- `total_return`: 最直接，适合短期
- `annual_return`: 标准化，适合长期对比
- `sharpe_ratio`: 风险调整，综合考虑收益和风险
- `win_rate`: 稳定性，反映交易成功率

### Q: 手续费如何计算？
A: 每次交易时自动扣除，费率默认为 0.0005 (0.05%)

---

## 📚 更多信息

- 详细文档: `BACKTEST_ENGINE.md`
- 测试脚本: `test_backtest.py`
- API 集成: `app.py`

---

**版本**: 1.0.0  
**最后更新**: 2026-01-28
