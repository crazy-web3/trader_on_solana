# 合约网格交易回测算法优化详细说明

## 优化概述

根据《合约网格交易说明文档》，我们对回测引擎进行了全面优化，实现了更准确的网格交易模拟。

## 核心优化内容

### 1. 网格类型支持

#### 等差网格（Arithmetic Grid）
```
价差 = (上限 - 下限) / 网格数量
价格序列：price_i = 下限 + 价差 * (i-1)
```

**实现**：
- `_calculate_arithmetic_grid()` 计算等差网格参数
- `_get_grid_price()` 根据网格索引获取价格

#### 等比网格（Geometric Grid）
```
价格比率 = (上限 / 下限) ^ (1 / 网格数量)
价格序列：price_i = 下限 * 价格比率 ^ (i-1)
```

**实现**：
- `_calculate_geometric_grid()` 计算等比网格参数
- 支持更精确的价格分布

### 2. 网格关闭机制

**文档规定**：
> 网格更新是指在每次触及价格点（即限价单成交）时，网格限价单将及时更新。最近成交订单的价格点位将"关闭"，即该价格不会再触发任何订单。

**实现**：
```python
class GridLevel:
    def __init__(self, level_idx: int, price: float):
        self.is_closed = False  # 网格关闭标志
    
    def close_grid(self):
        """关闭此网格（不再在此价格下单）"""
        self.is_closed = True
```

**工作流程**：
1. 订单成交时，该网格被标记为已关闭
2. 后续不会在该价格点再次下单
3. 确保网格交易的正确性

### 3. 初始仓位建立

#### 做多网格（Long Mode）
```
- 起始价格及以下：建立多仓
- 起始价格以上：挂卖单
- 目标：在价格下跌时买入，上涨时卖出
```

#### 做空网格（Short Mode）
```
- 起始价格及以上：建立空仓
- 起始价格以下：挂买单
- 目标：在价格上涨时卖出，下跌时买入
```

#### 中性网格（Neutral Mode）
```
- 起始价格下方：偏向多仓
- 起始价格上方：偏向空仓
- 起始价格处：平衡多空
- 目标：低买高卖，不预判方向
```

**实现**：
- `_place_long_initial_orders()` - 做多网格初始化
- `_place_short_initial_orders()` - 做空网格初始化
- `_place_neutral_initial_orders()` - 中性网格初始化

### 4. 订单执行优化

#### 改进点

**原始实现问题**：
- 只检查收盘价，忽略K线高低价
- 没有考虑多个订单同时成交的情况
- 订单填充逻辑过于简化

**优化实现**：
```python
def _check_order_fills(self, kline: KlineData) -> None:
    """检查订单是否应该成交"""
    for level_idx, grid in self.grid_levels.items():
        if grid.is_closed:
            continue
        
        # 检查买单：价格跌至或低于订单价格时成交
        for order in grid.pending_buy_orders[:]:
            if kline.low <= order.price:
                self._fill_order(order, kline, order.price)
        
        # 检查卖单：价格涨至或高于订单价格时成交
        for order in grid.pending_sell_orders[:]:
            if kline.high >= order.price:
                self._fill_order(order, kline, order.price)
```

**关键改进**：
1. 使用K线的高低价而不仅仅是收盘价
2. 正确处理多个订单同时成交
3. 实现网格关闭机制

### 5. 收益计算分离

#### 已撮合收益（Grid Profit）
```
已撮合收益 = 已完成的买卖配对的利润
计算方式：
- 买单成交价 < 卖单成交价 → 利润 = (卖价 - 买价) * 数量
- 考虑杠杆倍数：利润 *= 杠杆
```

#### 未撮合盈亏（Unrealized PnL）
```
未撮合盈亏 = 当前未平仓头寸的浮动盈亏
计算方式：
- 多头：(当前价格 - 入场价格) * 头寸数量
- 空头：(入场价格 - 当前价格) * 头寸数量
```

**实现**：
```python
# 已撮合收益
self.grid_profit += max(0, pnl)

# 未撮合盈亏
unrealized_pnl = 0.0
if self.total_long_position > 0:
    unrealized_pnl += self.total_long_position * (current_price - avg_entry_price)
if self.total_short_position > 0:
    unrealized_pnl += self.total_short_position * (avg_entry_price - current_price)
```

### 6. 保证金和风险管理

#### 占用保证金计算
```
当前名义价值 = max(|多头名义价值 + 买单挂单名义价值|, 
                    |空头名义价值 - 卖单挂单名义价值|)
占用保证金 = 当前名义价值 / 杠杆倍数
```

#### 机器人风险率（BRR）
```
BRR = 保证金余额 / 占用保证金
BRR < 1.0 时，网格将过期（强平）
```

**实现计划**（Phase 2）：
- 动态计算占用保证金
- 实时计算机器人风险率
- 实现强平价格计算

### 7. 资金费用计算

#### 资金费用公式
```
资金费用 = 头寸名义价值 * 资金费率
- 多头支付资金费用
- 空头收取资金费用
```

**实现**：
```python
def _process_funding_fees(self, kline: KlineData) -> None:
    """处理永续合约资金费用"""
    current_position = self.total_long_position - self.total_short_position
    
    if abs(current_position) < 1e-10:
        return
    
    # 计算资金费用
    position_notional = abs(current_position) * kline.close
    funding_amount = position_notional * self.config.funding_rate
    
    if current_position > 0:
        # 多头支付资金费用
        self.capital -= funding_amount
    else:
        # 空头收取资金费用
        self.capital += funding_amount
```

### 8. 数据精度验证

#### 最小变动价位检查
```
对于最小报价单位 ≤ 0.00001 的交易对：
  最小差价 = 20 * 最小报价单位

对于最小报价单位 = 0.0001 的交易对：
  最小差价 = 5 * 最小报价单位

对于最小报价单位 > 0.0001 的交易对：
  无差价限制
```

**实现**：
```python
def _calculate_grid_parameters(self) -> None:
    """计算网格参数并验证最小价差"""
    if self.config.grid_type == GridType.ARITHMETIC:
        self.grid_gap = (upper - lower) / (count - 1)
        if self.grid_gap < self.config.min_price_tick:
            raise InvalidParameterError(...)
    else:
        self.price_ratio = (upper / lower) ** (1 / (count - 1))
        min_gap = lower * (self.price_ratio - 1)
        if min_gap < self.config.min_price_tick:
            raise InvalidParameterError(...)
```

## 性能指标改进

### 原始指标
- 总收益率
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率
- 交易数量

### 新增指标
- **已撮合收益**：已完成的网格交易利润
- **未撮合盈亏**：当前未平仓头寸的浮动盈亏
- **资金费用**：永续合约资金费用总额
- **资金费用率**：资金费用占初始资本的比例
- **机器人风险率**：实时风险评估指标

## 使用示例

### 基础回测
```python
from backtest_engine.optimized_engine import OptimizedBacktestEngine
from backtest_engine.models import BacktestConfig, StrategyMode
from strategy_engine.models import GridType

# 创建回测配置
config = BacktestConfig(
    symbol="BTCUSDT",
    mode=StrategyMode.LONG,
    lower_price=40000,
    upper_price=50000,
    grid_count=20,
    initial_capital=10000,
    start_date="2023-01-01",
    end_date="2023-12-31",
    fee_rate=0.0005,
    leverage=2.0,
)

# 运行回测
engine = OptimizedBacktestEngine()
result = engine.run_backtest(config, grid_type=GridType.ARITHMETIC)

# 查看结果
print(f"总收益率: {result.metrics.total_return:.2%}")
print(f"年化收益率: {result.metrics.annual_return:.2%}")
print(f"最大回撤: {result.metrics.max_drawdown:.2%}")
print(f"已撮合收益: {result.metrics.grid_profit:.2f}")
print(f"未撮合盈亏: {result.metrics.unrealized_pnl:.2f}")
```

### 网格搜索优化
```python
# 运行网格搜索
search_results = engine.run_grid_search(
    config,
    grid_count_range=(5, 50),
    leverage_range=(1.0, 10.0),
    grid_type=GridType.ARITHMETIC,
)

# 获取最优参数
best_result = search_results["best_result"]
best_params = search_results["best_params"]
print(f"最优网格数: {best_params['grid_count']}")
print(f"最优杠杆: {best_params['leverage']}")
```

## 后续优化计划

### Phase 2: 保证金和风险管理
- [ ] 实现动态保证金追加机制
- [ ] 计算机器人风险率
- [ ] 实现杠杆区间调整
- [ ] 计算强平价格

### Phase 3: 高级功能
- [ ] 触发价格支持
- [ ] 终止条件支持
- [ ] 市价建仓选项
- [ ] 创建时全部平仓功能

### Phase 4: 性能优化
- [ ] 缓存网格价格计算
- [ ] 优化订单查询性能
- [ ] 并行化回测执行
- [ ] 添加详细日志

## 测试建议

1. **单元测试**：
   - 测试等差和等比网格计算
   - 测试网格关闭机制
   - 测试订单执行逻辑

2. **集成测试**：
   - 测试完整的回测流程
   - 验证收益计算准确性
   - 对比原始实现结果

3. **性能测试**：
   - 测试大规模数据处理
   - 测试网格搜索性能
   - 内存使用情况

## 参考文档

- 《合约网格交易说明文档》
- Binance 网格交易官方文档
- 永续合约交易规则
