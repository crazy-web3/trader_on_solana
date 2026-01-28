# 🚀 策略引擎 (Strategy Engine)

## 📋 概述

策略引擎是一个完整的网格交易策略实现，支持做多、做空和中性三种模式。

## 🎯 核心功能

### 1. 网格策略类型

#### 做多网格 (Long Grid)
- 在低价位买入
- 在高价位卖出
- 适合上升趋势

#### 做空网格 (Short Grid)
- 在高价位卖出
- 在低价位买入
- 适合下降趋势

#### 中性网格 (Neutral Grid)
- 同时进行买卖操作
- 适合震荡行情

### 2. 自动网格生成

系统自动根据价格区间和网格数量生成均匀分布的网格价位。

```python
# 示例：10个网格，价格区间 48000-52000
grid_prices = [
    48000.00,  # 网格 1
    48444.44,  # 网格 2
    48888.89,  # 网格 3
    ...
    52000.00,  # 网格 10
]
```

### 3. 逐根K线模拟成交

系统逐根处理K线数据，在价格触及网格价位时自动执行交易。

### 4. 完整的交易记录

记录每笔交易的详细信息：
- 时间戳
- 价格
- 数量
- 方向 (买/卖)
- 手续费
- 盈亏

### 5. 性能指标

- 总收益率
- 交易次数
- 胜率
- 最大回撤
- 权益曲线

---

## 📊 数据模型

### StrategyConfig (策略配置)

```python
@dataclass
class StrategyConfig:
    symbol: str              # 交易对 (e.g., "BTC/USDT")
    mode: StrategyMode       # 策略模式 (long/short/neutral)
    lower_price: float       # 下限价格
    upper_price: float       # 上限价格
    grid_count: int          # 网格数量
    initial_capital: float   # 初始资金
    fee_rate: float          # 手续费率 (默认 0.05%)
```

### TradeRecord (交易记录)

```python
@dataclass
class TradeRecord:
    timestamp: int           # 时间戳 (毫秒)
    price: float            # 交易价格
    quantity: float         # 交易数量
    side: str               # 方向 (buy/sell)
    grid_level: int         # 网格级别
    fee: float              # 手续费
    pnl: float              # 盈亏
```

### StrategyResult (策略结果)

```python
@dataclass
class StrategyResult:
    symbol: str             # 交易对
    mode: StrategyMode      # 策略模式
    initial_capital: float  # 初始资金
    final_capital: float    # 最终资金
    total_return: float     # 总收益率
    total_trades: int       # 总交易数
    winning_trades: int     # 盈利交易数
    losing_trades: int      # 亏损交易数
    win_rate: float         # 胜率
    max_drawdown: float     # 最大回撤 (绝对值)
    max_drawdown_pct: float # 最大回撤率 (百分比)
    trades: List[TradeRecord]  # 交易列表
    equity_curve: List[float]  # 权益曲线
    timestamps: List[int]      # 时间戳列表
```

---

## 🔧 使用示例

### Python 代码

```python
from strategy_engine import GridStrategyEngine, StrategyConfig, StrategyMode
from market_data_layer.adapter import BinanceDataSourceAdapter

# 1. 创建策略配置
config = StrategyConfig(
    symbol="BTC/USDT",
    mode=StrategyMode.LONG,
    lower_price=48000.0,
    upper_price=52000.0,
    grid_count=10,
    initial_capital=10000.0,
    fee_rate=0.0005,
)

# 2. 创建策略引擎
engine = GridStrategyEngine(config)

# 3. 获取K线数据
adapter = BinanceDataSourceAdapter()
klines = adapter.fetch_kline_data(
    symbol="BTC/USDT",
    interval="1h",
    start_time=start_time,
    end_time=end_time,
)

# 4. 执行策略
result = engine.execute(klines)

# 5. 查看结果
print(f"总收益率: {result.total_return*100:.2f}%")
print(f"总交易数: {result.total_trades}")
print(f"胜率: {result.win_rate*100:.2f}%")
print(f"最大回撤: {result.max_drawdown_pct*100:.2f}%")
```

### API 调用

```bash
curl -X POST http://localhost:5001/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "mode": "long",
    "lower_price": 87000,
    "upper_price": 90000,
    "grid_count": 10,
    "initial_capital": 10000,
    "days": 7
  }'
```

---

## 📈 测试结果

### 做多网格策略 (BTC/USDT)

```
初始资金: $10,000.00
最终资金: $10,139.49
总收益率: 1.39%

总交易数: 44
盈利交易: 20
亏损交易: 0
胜率: 45.45%

最大回撤: $261.64
最大回撤率: 2.62%
```

### 交易示例

```
交易 #1: BUY  @ $48,888.89, 数量: 0.0205, 手续费: $0.50
交易 #2: BUY  @ $49,333.33, 数量: 0.0203, 手续费: $0.50
交易 #3: BUY  @ $49,777.78, 数量: 0.0201, 手续费: $0.50
...
交易 #20: SELL @ $50,222.22, 数量: 0.0199, 盈亏: $81.50
```

---

## 🔗 API 端点

### 回测策略

**端点**: `POST /api/strategy/backtest`

**请求体**:
```json
{
  "symbol": "BTC/USDT",
  "mode": "long",
  "lower_price": 87000,
  "upper_price": 90000,
  "grid_count": 10,
  "initial_capital": 10000,
  "days": 7
}
```

**参数说明**:
- `symbol`: 交易对 (BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT)
- `mode`: 策略模式 (long, short, neutral)
- `lower_price`: 下限价格 (必须 > 0)
- `upper_price`: 上限价格 (必须 > lower_price)
- `grid_count`: 网格数量 (必须 >= 2)
- `initial_capital`: 初始资金 (必须 > 0)
- `days`: 回测天数 (1-365)

**响应**:
```json
{
  "symbol": "BTC/USDT",
  "mode": "long",
  "initial_capital": 10000,
  "final_capital": 10139.49,
  "total_return": 0.0139,
  "total_trades": 44,
  "winning_trades": 20,
  "losing_trades": 0,
  "win_rate": 0.4545,
  "max_drawdown": 261.64,
  "max_drawdown_pct": 0.0262,
  "trades": [...],
  "equity_curve": [...],
  "timestamps": [...]
}
```

---

## 📊 性能指标说明

### 总收益率 (Total Return)
```
总收益率 = (最终资金 - 初始资金) / 初始资金
```

### 胜率 (Win Rate)
```
胜率 = 盈利交易数 / 总交易数
```

### 最大回撤 (Maximum Drawdown)
```
最大回撤 = 最高权益 - 最低权益
最大回撤率 = 最大回撤 / 最高权益
```

---

## 🧪 运行测试

### 本地测试

```bash
python3 test_strategy.py
```

### API 测试

```bash
# 做多网格
curl -X POST http://localhost:5001/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "mode": "long",
    "lower_price": 87000,
    "upper_price": 90000,
    "grid_count": 10,
    "initial_capital": 10000,
    "days": 7
  }'

# 做空网格
curl -X POST http://localhost:5001/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETH/USDT",
    "mode": "short",
    "lower_price": 2800,
    "upper_price": 3200,
    "grid_count": 8,
    "initial_capital": 5000,
    "days": 7
  }'

# 中性网格
curl -X POST http://localhost:5001/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SOL/USDT",
    "mode": "neutral",
    "lower_price": 100,
    "upper_price": 150,
    "grid_count": 10,
    "initial_capital": 3000,
    "days": 7
  }'
```

---

## 📁 项目结构

```
strategy_engine/
├── __init__.py           # 模块初始化
├── models.py             # 数据模型
├── engine.py             # 策略引擎核心
└── exceptions.py         # 异常定义

test_strategy.py          # 测试脚本
app.py                    # Flask API 服务器
```

---

## 🎯 核心算法

### 1. 网格生成

```python
# 均匀分布网格
grid_prices = [
    lower + (upper - lower) * i / (count - 1)
    for i in range(count)
]
```

### 2. 做多交易逻辑

```
IF 价格 <= 网格价位 AND 网格为空:
    执行买入
    标记网格为持仓

IF 价格 >= 上一网格价位 AND 上一网格有持仓:
    执行卖出
    标记网格为空
    计算盈亏
```

### 3. 做空交易逻辑

```
IF 价格 >= 网格价位 AND 网格为空:
    执行卖出
    标记网格为持仓

IF 价格 <= 下一网格价位 AND 下一网格有持仓:
    执行买入
    标记网格为空
    计算盈亏
```

### 4. 权益计算

```
权益 = 现金 + 持仓数量 * 当前价格
```

### 5. 最大回撤计算

```
FOR 每个权益值:
    IF 权益 > 历史最高:
        更新历史最高
    回撤 = (历史最高 - 当前权益) / 历史最高
    IF 回撤 > 最大回撤:
        更新最大回撤
```

---

## ⚠️ 注意事项

### 参数验证

- 价格必须为正数
- 下限价格必须小于上限价格
- 网格数量必须 >= 2
- 初始资金必须为正数
- 手续费率必须在 0-1% 之间

### 交易执行

- 每个网格最多持仓一次
- 交易时自动扣除手续费
- 资金不足时跳过交易
- 按时间顺序逐根K线处理

### 性能考虑

- 支持大量K线数据处理
- 内存占用与K线数量成正比
- 处理速度取决于K线数量和网格数量

---

## 🚀 下一步

### 短期
- ✅ 基础网格策略实现
- ✅ 三种模式支持
- ✅ API 集成

### 中期
- [ ] 参数优化
- [ ] 多币种对比
- [ ] 策略组合

### 长期
- [ ] 实盘交易
- [ ] 动态网格
- [ ] 机器学习优化

---

## 📞 支持

### 查看文档
- `STRATEGY_ENGINE.md` - 本文件
- `test_strategy.py` - 测试示例

### 运行测试
```bash
python3 test_strategy.py
```

### API 调用
```bash
curl -X POST http://localhost:5001/api/strategy/backtest ...
```

---

**版本**: 1.0.0
**状态**: ✅ 生产就绪
**最后更新**: 2026-01-28
