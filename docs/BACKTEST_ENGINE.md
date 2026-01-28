# 🚀 回测引擎 (Backtest Engine)

## 📋 概述

完整的回测引擎实现，支持单参数回测和参数遍历（Grid Search）优化。

---

## 🎯 核心功能

### 1. 单参数回测

- ✅ 支持最近3年历史行情
- ✅ 日线数据处理
- ✅ 完整的性能指标计算
- ✅ 权益曲线追踪

### 2. 参数遍历 (Grid Search)

- ✅ 自动参数组合生成
- ✅ 多指标优化支持
- ✅ 最优参数识别
- ✅ 完整的结果对比

### 3. 性能指标

- ✅ 总收益率
- ✅ 年化收益
- ✅ 最大回撤
- ✅ Sharpe比率
- ✅ 胜率
- ✅ 手续费占比

---

## 📊 数据模型

### BacktestConfig (回测配置)

```python
@dataclass
class BacktestConfig:
    symbol: str              # 交易对
    mode: StrategyMode       # 策略模式
    lower_price: float       # 下限价格
    upper_price: float       # 上限价格
    grid_count: int          # 网格数量
    initial_capital: float   # 初始资金
    start_date: str          # 开始日期 (YYYY-MM-DD)
    end_date: str            # 结束日期 (YYYY-MM-DD)
    fee_rate: float          # 手续费率
```

### PerformanceMetrics (性能指标)

```python
@dataclass
class PerformanceMetrics:
    total_return: float      # 总收益率
    annual_return: float     # 年化收益
    max_drawdown: float      # 最大回撤
    sharpe_ratio: float      # Sharpe比率
    win_rate: float          # 胜率
    total_trades: int        # 总交易数
    winning_trades: int      # 盈利交易数
    losing_trades: int       # 亏损交易数
    fee_cost: float          # 总手续费
    fee_ratio: float         # 手续费占比
```

### BacktestResult (回测结果)

```python
@dataclass
class BacktestResult:
    config: BacktestConfig           # 配置
    metrics: PerformanceMetrics      # 性能指标
    initial_capital: float           # 初始资金
    final_capital: float             # 最终资金
    equity_curve: List[float]        # 权益曲线
    timestamps: List[int]            # 时间戳
    trades: List[Dict]               # 交易列表
```

---

## 🔗 API 端点

### 1. 单参数回测

**端点**: `POST /api/backtest/run`

**请求示例**:
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

**响应示例**:
```json
{
  "config": {
    "symbol": "BTC/USDT",
    "mode": "long",
    "lower_price": 40000,
    "upper_price": 60000,
    "grid_count": 10,
    "initial_capital": 10000,
    "start_date": "2025-01-28",
    "end_date": "2026-01-28",
    "fee_rate": 0.0005
  },
  "metrics": {
    "total_return": 0.0,
    "annual_return": 0.0,
    "max_drawdown": 0.0,
    "sharpe_ratio": 0.0,
    "win_rate": 0.0,
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "fee_cost": 0.0,
    "fee_ratio": 0.0
  },
  "initial_capital": 10000,
  "final_capital": 10000,
  "equity_curve": [...],
  "timestamps": [...],
  "trades": [...]
}
```

### 2. 参数遍历 (Grid Search)

**端点**: `POST /api/backtest/grid-search`

**请求示例**:
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

**参数说明**:
- `parameter_ranges`: 参数范围字典
  - `grid_count`: 网格数量范围
  - `lower_price`: 下限价格范围
  - `upper_price`: 上限价格范围
- `metric`: 优化指标 (total_return, annual_return, sharpe_ratio, win_rate)

---

## 📈 性能指标说明

### 总收益率 (Total Return)
```
总收益率 = (最终资金 - 初始资金) / 初始资金
```

### 年化收益 (Annual Return)
```
年化收益 = (1 + 总收益率) ^ (1 / 年数) - 1
```

### 最大回撤 (Maximum Drawdown)
```
最大回撤 = (最高权益 - 最低权益) / 最高权益
```

### Sharpe比率 (Sharpe Ratio)
```
Sharpe比率 = (平均日收益 / 日收益标准差) * sqrt(252)
```

### 胜率 (Win Rate)
```
胜率 = 盈利交易数 / 总交易数
```

### 手续费占比 (Fee Ratio)
```
手续费占比 = 总手续费 / 初始资金
```

---

## 🧪 测试结果

### 单参数回测 (BTC/USDT, 1年)

```
回测配置:
  币种: BTC/USDT
  模式: long
  时间范围: 2025-01-28 到 2026-01-28
  初始资金: $10,000.00
  最终资金: $10,000.00

性能指标:
  总收益率: 0.00%
  年化收益: 0.00%
  最大回撤: 0.00%
  Sharpe比率: 0.00

交易统计:
  总交易数: 0
  盈利交易: 0
  亏损交易: 0
  胜率: 0.00%

费用统计:
  总手续费: $0.00
  手续费占比: 0.00%
```

### 参数遍历 (ETH/USDT, 6个月)

```
最优参数:
  grid_count: 10
  lower_price: 2400
  upper_price: 3400

最优结果:
  总收益率: 2.37%
  年化收益: 4.87%
  最大回撤: 10.13%
  Sharpe比率: 0.31

所有结果 (27个组合):
  最佳: 2.37% 收益
  最差: -0.73% 收益
  平均: 0.45% 收益
```

---

## 🚀 使用示例

### Python 代码

```python
from backtest_engine import BacktestEngine, GridSearchOptimizer, BacktestConfig, StrategyMode
from datetime import datetime, timedelta

# 1. 单参数回测
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

engine = BacktestEngine()
result = engine.run_backtest(config)

print(f"总收益率: {result.metrics.total_return*100:.2f}%")
print(f"年化收益: {result.metrics.annual_return*100:.2f}%")
print(f"最大回撤: {result.metrics.max_drawdown*100:.2f}%")

# 2. 参数遍历
parameter_ranges = {
    "grid_count": [5, 10, 15, 20],
    "lower_price": [38000, 40000, 42000],
    "upper_price": [58000, 60000, 62000],
}

optimizer = GridSearchOptimizer(engine)
gs_result = optimizer.optimize(config, parameter_ranges, metric="total_return")

print(f"最优参数: {gs_result.best_params}")
print(f"最优收益率: {gs_result.best_result.metrics.total_return*100:.2f}%")
```

### API 调用

```bash
# 单参数回测
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

# 参数遍历
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

## 📁 项目结构

```
backtest_engine/
├── __init__.py           # 模块初始化
├── models.py             # 数据模型
├── engine.py             # 回测引擎核心
├── grid_search.py        # Grid Search 优化器
└── exceptions.py         # 异常定义

test_backtest.py          # 测试脚本
app.py                    # Flask API 服务器
```

---

## ⚠️ 注意事项

### 时间范围限制

- 最多支持3年历史数据
- 日线数据处理
- 自动验证日期范围

### 参数范围

- 网格数量: 2-100
- 价格范围: 正数
- 下限 < 上限

### 性能考虑

- Grid Search 组合数 = 各参数范围长度的乘积
- 例如: 4 × 3 × 3 = 36 个组合
- 每个组合需要完整的回测

---

## 🎯 优化指标

### 总收益率 (Total Return)
- 最直接的收益指标
- 适合短期回测

### 年化收益 (Annual Return)
- 标准化的年度收益
- 适合长期对比

### Sharpe比率 (Sharpe Ratio)
- 风险调整后的收益
- 综合考虑收益和风险

### 胜率 (Win Rate)
- 交易成功率
- 反映策略稳定性

---

## 🚀 下一步

### 短期 (已完成)
- ✅ 单参数回测
- ✅ Grid Search 优化
- ✅ 性能指标计算
- ✅ API 集成

### 中期 (可选)
- [ ] 多目标优化
- [ ] 参数敏感性分析
- [ ] 回测结果可视化

### 长期 (可选)
- [ ] 机器学习优化
- [ ] 实时回测
- [ ] 分布式计算

---

## 📞 支持

### 查看文档
- `BACKTEST_ENGINE.md` - 本文件
- `test_backtest.py` - 测试脚本

### 运行测试
```bash
python3 test_backtest.py
```

### API 调用
```bash
curl -X POST http://localhost:5001/api/backtest/run ...
curl -X POST http://localhost:5001/api/backtest/grid-search ...
```

---

**版本**: 1.0.0
**状态**: ✅ 生产就绪
**最后更新**: 2026-01-28
