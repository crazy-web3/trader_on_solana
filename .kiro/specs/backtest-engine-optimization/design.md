# 设计文档

## 概述

本文档描述了合约网格交易回测系统优化的技术设计方案。优化的核心目标是提高算法准确性、改善代码可维护性和增强系统性能。

### 优化目标

1. **算法准确性**：修复网格订单执行、保证金管理、盈亏计算中的逻辑错误
2. **代码可维护性**：将706行的单一类重构为职责清晰的多个组件
3. **性能优化**：优化数据结构和算法，提高回测速度
4. **可测试性**：为所有核心算法提供基于属性的测试

### 当前问题分析

通过代码审查，识别出以下主要问题：

1. **初始化逻辑混乱**：存在三个初始化方法（`_initialize_grid`、`_place_initial_orders`、`_place_initial_positions_from_start`），职责不清
2. **保证金计算错误**：开仓时重复计算保证金，平仓时未正确释放保证金
3. **订单配对逻辑复杂**：买卖单配对逻辑嵌套在订单执行中，难以理解和维护
4. **盈亏计算不准确**：网格收益和未实现盈亏的计算存在偏差
5. **资金费率处理简化**：未考虑多空仓位的资金费率方向差异
6. **代码重复**：三种策略模式的逻辑大量重复

## 架构设计

### 组件分层

采用分层架构，将复杂的策略引擎分解为职责单一的组件：

```
GridStrategyEngine (协调器)
├── OrderManager (订单管理)
├── PositionManager (仓位管理)
├── MarginCalculator (保证金计算)
├── PnLCalculator (盈亏计算)
└── FundingFeeCalculator (资金费率计算)
```

### 组件职责

**GridStrategyEngine（协调器）**
- 协调各组件完成策略执行
- 处理K线数据流
- 维护策略状态和结果

**OrderManager（订单管理器）**
- 管理挂单队列
- 检查订单触发条件
- 执行订单成交逻辑
- 根据策略模式放置对手订单

**PositionManager（仓位管理器）**
- 维护每个网格的仓位记录
- 处理开仓和平仓操作
- 查找配对仓位
- 计算净仓位

**MarginCalculator（保证金计算器）**
- 计算开仓所需保证金
- 追踪已用保证金
- 计算可用资金
- 验证保证金充足性

**PnLCalculator（盈亏计算器）**
- 计算已实现盈亏
- 计算未实现盈亏
- 计算权益
- 维护盈亏守恒

**FundingFeeCalculator（资金费率计算器）**
- 追踪资金费率结算时间
- 计算资金费用
- 处理多空仓位的费率方向

## 组件和接口

### OrderManager

```python
class OrderManager:
    """订单管理器，负责管理网格订单的生命周期"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.pending_orders: Dict[int, GridOrder] = {}
        self.grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    def place_initial_orders(self, current_price: float, strategy_mode: StrategyMode) -> None:
        """根据策略模式放置初始订单"""
        pass
    
    def check_order_fills(self, kline: KlineData) -> List[GridOrder]:
        """检查哪些订单应该成交，返回成交的订单列表"""
        pass
    
    def place_counter_order(self, filled_order: GridOrder, strategy_mode: StrategyMode) -> None:
        """在订单成交后放置对手订单"""
        pass
    
    def get_pending_orders(self) -> Dict[int, GridOrder]:
        """获取所有挂单"""
        pass
```

### PositionManager

```python
class PositionManager:
    """仓位管理器，负责追踪和管理每个网格的仓位"""
    
    def __init__(self):
        self.grid_positions: Dict[int, Position] = {}
    
    def open_position(self, grid_idx: int, quantity: float, price: float, side: str) -> None:
        """开仓"""
        pass
    
    def close_position(self, grid_idx: int, quantity: float) -> Optional[Position]:
        """平仓，返回被平掉的仓位信息"""
        pass
    
    def find_matching_position(self, grid_idx: int, side: str, strategy_mode: StrategyMode) -> Optional[Tuple[int, Position]]:
        """查找配对仓位"""
        pass
    
    def get_net_position(self) -> float:
        """计算净仓位（正数为多仓，负数为空仓）"""
        pass
    
    def get_all_positions(self) -> Dict[int, Position]:
        """获取所有仓位"""
        pass
```

### MarginCalculator

```python
class MarginCalculator:
    """保证金计算器，负责保证金相关的所有计算"""
    
    def __init__(self, leverage: float):
        self.leverage = leverage
        self.used_margin = 0.0
    
    def calculate_required_margin(self, quantity: float, price: float) -> float:
        """计算开仓所需保证金"""
        return quantity * price / self.leverage
    
    def allocate_margin(self, amount: float) -> bool:
        """分配保证金，返回是否成功"""
        pass
    
    def release_margin(self, amount: float) -> None:
        """释放保证金"""
        pass
    
    def get_available_capital(self, total_capital: float) -> float:
        """计算可用资金"""
        return total_capital - self.used_margin
    
    def get_used_margin(self) -> float:
        """获取已用保证金"""
        return self.used_margin
```

### PnLCalculator

```python
class PnLCalculator:
    """盈亏计算器，负责所有盈亏相关的计算"""
    
    def __init__(self):
        self.grid_profit = 0.0  # 已实现盈亏
    
    def calculate_realized_pnl(self, open_price: float, close_price: float, 
                               quantity: float, side: str) -> float:
        """计算已实现盈亏"""
        if side == "long":
            return (close_price - open_price) * quantity
        else:  # short
            return (open_price - close_price) * quantity
    
    def calculate_unrealized_pnl(self, positions: Dict[int, Position], 
                                 current_price: float, grid_gap: float, 
                                 lower_price: float) -> float:
        """计算未实现盈亏"""
        pass
    
    def calculate_equity(self, capital: float, unrealized_pnl: float) -> float:
        """计算权益"""
        return capital + unrealized_pnl
    
    def add_realized_pnl(self, pnl: float) -> None:
        """累加已实现盈亏"""
        self.grid_profit += pnl
    
    def get_grid_profit(self) -> float:
        """获取网格收益"""
        return self.grid_profit
```

### FundingFeeCalculator

```python
class FundingFeeCalculator:
    """资金费率计算器，负责资金费率的计算和结算"""
    
    def __init__(self, funding_rate: float, funding_interval: int):
        self.funding_rate = funding_rate
        self.funding_interval_ms = funding_interval * 60 * 60 * 1000
        self.last_funding_time = 0
        self.total_funding_fees = 0.0
    
    def should_settle_funding(self, current_time: int) -> bool:
        """判断是否应该结算资金费率"""
        if self.last_funding_time == 0:
            self.last_funding_time = current_time
            return False
        return current_time - self.last_funding_time >= self.funding_interval_ms
    
    def calculate_funding_fee(self, position_size: float, current_price: float) -> float:
        """计算资金费用（正数表示支付，负数表示收取）"""
        # 多仓支付资金费率，空仓收取资金费率
        return position_size * current_price * self.funding_rate
    
    def settle_funding(self, current_time: int) -> None:
        """更新资金费率结算时间"""
        self.last_funding_time = current_time
    
    def add_funding_fee(self, fee: float) -> None:
        """累加资金费用"""
        self.total_funding_fees += abs(fee)
    
    def get_total_funding_fees(self) -> float:
        """获取总资金费用"""
        return self.total_funding_fees
```

## 数据模型

### Position（仓位）

```python
@dataclass
class Position:
    """仓位信息"""
    grid_idx: int          # 网格索引
    quantity: float        # 数量（正数为多仓，负数为空仓）
    entry_price: float     # 开仓价格
    side: str             # "long" 或 "short"
    timestamp: int        # 开仓时间
```

### GridOrder（网格订单）

```python
@dataclass
class GridOrder:
    """网格订单"""
    grid_idx: int         # 网格索引
    price: float          # 订单价格
    side: str            # "buy" 或 "sell"
    quantity: float      # 订单数量
    is_filled: bool      # 是否已成交
```

## 正确性属性

*属性是一个特征或行为，应该在系统的所有有效执行中保持为真——本质上是关于系统应该做什么的形式化陈述。属性是人类可读规范和机器可验证正确性保证之间的桥梁。*

### 属性 1：订单初始化正确性

*对于任何*策略配置和初始价格，初始化后的订单应该符合策略模式的规则：
- 做多网格：当前价以下挂买单，以上挂卖单
- 做空网格：当前价以上挂卖单，以下挂买单
- 中性网格：当前价附近挂买卖单平衡

**验证：需求 1.1**

### 属性 2：订单触发准确性

*对于任何*挂单和K线数据，当且仅当价格触及订单价格时，订单应该被执行：
- 买单：当K线最低价 <= 订单价格时成交
- 卖单：当K线最高价 >= 订单价格时成交

**验证：需求 1.2**

### 属性 3：对手订单放置正确性

*对于任何*成交的订单，系统应该在正确的对手网格上放置新订单：
- 做多网格：买单成交后在上一网格挂卖单，卖单成交后在下一网格挂买单
- 做空网格：卖单成交后在下一网格挂买单，买单成交后在上一网格挂卖单
- 中性网格：订单成交后在对手网格挂平仓订单

**验证：需求 1.3, 1.4, 1.5, 1.6**

### 属性 4：保证金计算正确性

*对于任何*开仓操作，所需保证金应该等于（合约价值 / 杠杆倍数），且可用资金应该等于（总资金 - 已用保证金）

**验证：需求 2.1, 2.4**

### 属性 5：保证金不变式

*对于任何*系统状态，已用保证金应该始终小于等于总资金，即：used_margin <= total_capital

**验证：需求 2.5**

### 属性 6：保证金不足拒绝

*对于任何*保证金不足的开仓请求，系统应该拒绝开仓并保持当前状态不变

**验证：需求 2.2**

### 属性 7：保证金释放正确性

*对于任何*平仓操作，系统应该释放对应的保证金，且释放后的已用保证金应该减少相应的金额

**验证：需求 2.3**

### 属性 8：已实现盈亏计算正确性

*对于任何*平仓操作，已实现盈亏应该等于：
- 做多：(平仓价格 - 开仓价格) × 数量
- 做空：(开仓价格 - 平仓价格) × 数量

**验证：需求 3.1**

### 属性 9：未实现盈亏计算正确性

*对于任何*未平仓头寸集合和当前价格，未实现盈亏应该等于所有头寸的 (当前价格 - 开仓价格) × 数量 的总和

**验证：需求 3.2, 3.3**

### 属性 10：资金守恒定律

*对于任何*完整的回测过程，最终资金应该等于：初始资金 + 已实现盈亏 - 手续费 - 资金费用

**验证：需求 3.6**

### 属性 11：盈亏更新正确性

*对于任何*订单配对成交，已实现盈亏应该立即累加到网格收益中，且当前资金应该立即增加相应的盈亏金额

**验证：需求 3.4, 3.5**

### 属性 12：订单配对正确性

*对于任何*成交的订单，系统应该根据策略模式查找正确的配对仓位：
- 做多网格卖单：查找下一网格的多仓
- 做空网格买单：查找上一网格的空仓
- 中性网格订单：查找对手网格的反向仓位

**验证：需求 4.1, 4.2, 4.3**

### 属性 13：无配对仓位处理

*对于任何*无法找到配对仓位的订单，系统应该将其视为开仓，并在对应网格创建新仓位

**验证：需求 4.4**

### 属性 14：仓位独立性

*对于任何*网格索引，该网格的仓位应该独立于其他网格的仓位，修改一个网格的仓位不应影响其他网格

**验证：需求 4.5**

### 属性 15：仓位清理正确性

*对于任何*完全平仓的网格，该网格应该从仓位记录中移除，且净仓位应该相应减少

**验证：需求 4.6**

### 属性 16：资金费率计算正确性

*对于任何*持有仓位且达到结算时间的情况，资金费用应该等于（仓位价值 × 资金费率），且多仓支付、空仓收取

**验证：需求 5.1, 5.2, 5.3**

### 属性 17：资金费率结算时间正确性

*对于任何*时间序列，资金费率应该按照配置的间隔（默认8小时）结算，且每次结算后更新结算时间

**验证：需求 5.4**

### 属性 18：资金费用累加正确性

*对于任何*资金费率结算，费用应该累加到总资金费用中，且总资金费用应该始终为非负数

**验证：需求 5.5**

### 属性 19：零仓位无费用

*对于任何*净仓位为零的时刻，系统不应该计算或扣除资金费用

**验证：需求 5.6**

### 属性 20：性能指标计算正确性

*对于任何*回测结果，各项性能指标应该按照正确的公式计算：
- 总收益率 = (最终资金 - 初始资金) / 初始资金
- 年化收益率 = ((1 + 总收益率) ^ (365 / 天数)) - 1
- 最大回撤 = max((峰值 - 当前值) / 峰值)
- 夏普比率 = (日收益率均值 / 日收益率标准差) × sqrt(252)
- 胜率 = 盈利交易数 / 总交易数

**验证：需求 6.1, 6.2, 6.3, 6.4, 6.5**

### 属性 21：权益曲线更新正确性

*对于任何*K线处理，权益曲线应该在处理后立即更新，且权益曲线的长度应该等于已处理的K线数量

**验证：需求 6.6**

## 错误处理

### 保证金不足

当开仓所需保证金超过可用资金时：
1. 拒绝开仓请求
2. 保持当前状态不变
3. 记录警告日志
4. 不抛出异常，继续处理后续K线

### 无效订单

当订单参数无效时（如价格为负、数量为零）：
1. 拒绝订单
2. 记录错误日志
3. 抛出 `InvalidOrderError` 异常

### 数据异常

当K线数据异常时（如高价低于低价）：
1. 跳过该K线
2. 记录警告日志
3. 继续处理后续K线

### 配置错误

当策略配置无效时（如上界低于下界）：
1. 在初始化时立即检测
2. 抛出 `InvalidParameterError` 异常
3. 阻止策略执行

## 测试策略

### 双重测试方法

系统采用单元测试和基于属性的测试相结合的方法：

**单元测试**：
- 验证特定示例和边界情况
- 测试错误条件和异常处理
- 测试组件之间的集成点
- 快速反馈，易于调试

**基于属性的测试**：
- 验证跨所有输入的通用属性
- 通过随机化实现全面的输入覆盖
- 每个属性测试至少运行100次迭代
- 捕获边界情况和意外的输入组合

### 属性测试配置

使用 Hypothesis 库进行基于属性的测试：

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)  # 至少100次迭代
@given(
    config=strategy_config_strategy(),
    klines=kline_list_strategy()
)
def test_property_margin_invariant(config, klines):
    """
    Feature: backtest-engine-optimization, Property 5: 保证金不变式
    
    对于任何系统状态，已用保证金应该始终小于等于总资金
    """
    engine = GridStrategyEngine(config)
    
    for kline in klines:
        engine._process_kline(kline)
        # 验证不变式
        assert engine.margin_calculator.get_used_margin() <= engine.capital
```

### 测试覆盖目标

- 核心算法：100% 属性测试覆盖
- 边界情况：100% 单元测试覆盖
- 错误处理：100% 单元测试覆盖
- 集成点：100% 单元测试覆盖

### 测试数据生成策略

使用 Hypothesis 的组合策略生成测试数据：

```python
from hypothesis.strategies import composite

@composite
def strategy_config_strategy(draw):
    """生成有效的策略配置"""
    lower_price = draw(st.floats(min_value=1000, max_value=50000))
    upper_price = draw(st.floats(min_value=lower_price * 1.1, max_value=lower_price * 2))
    
    return StrategyConfig(
        symbol="BTC/USDT",
        mode=draw(st.sampled_from([StrategyMode.LONG, StrategyMode.SHORT, StrategyMode.NEUTRAL])),
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=draw(st.integers(min_value=5, max_value=20)),
        initial_capital=draw(st.floats(min_value=1000, max_value=100000)),
        leverage=draw(st.floats(min_value=1, max_value=10)),
        fee_rate=0.0005,
        funding_rate=draw(st.floats(min_value=-0.001, max_value=0.001)),
    )

@composite
def kline_list_strategy(draw, min_size=10, max_size=100):
    """生成有效的K线数据列表"""
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    klines = []
    
    for i in range(size):
        open_price = draw(st.floats(min_value=1000, max_value=100000))
        close_price = draw(st.floats(min_value=1000, max_value=100000))
        high = max(open_price, close_price) * draw(st.floats(min_value=1.0, max_value=1.05))
        low = min(open_price, close_price) * draw(st.floats(min_value=0.95, max_value=1.0))
        
        kline = KlineData(
            timestamp=1609459200000 + i * 86400000,  # 每天一根K线
            open=open_price,
            high=high,
            low=low,
            close=close_price,
            volume=draw(st.floats(min_value=100, max_value=1000000)),
        )
        klines.append(kline)
    
    return klines
```

### 关键测试场景

**往返属性测试**：
- 开仓 → 平仓 → 保证金应该完全释放
- 买入 → 卖出 → 仓位应该归零

**不变式测试**：
- 已用保证金 <= 总资金（在所有操作后）
- 净仓位 = 所有网格仓位之和（在所有操作后）

**守恒定律测试**：
- 最终资金 = 初始资金 + 已实现盈亏 - 手续费 - 资金费用

**幂等性测试**：
- 重复计算未实现盈亏应该得到相同结果
- 重复查询可用资金应该得到相同结果

## 性能优化

### 数据结构优化

1. **使用字典而非列表存储仓位**：O(1) 查找时间
2. **使用字典存储挂单**：O(1) 订单查找和删除
3. **预计算网格价格**：避免重复计算

### 算法优化

1. **批量处理订单检查**：减少循环次数
2. **延迟计算未实现盈亏**：仅在需要时计算
3. **缓存权益曲线**：避免重复计算

### 内存优化

1. **及时清理已平仓位**：减少内存占用
2. **使用生成器处理大量K线**：流式处理
3. **限制交易记录数量**：可选的记录限制

## 实施计划

### 阶段 1：核心组件重构

1. 创建新的组件类（OrderManager、PositionManager等）
2. 实现基本功能
3. 编写单元测试

### 阶段 2：集成和迁移

1. 重构 GridStrategyEngine 使用新组件
2. 迁移现有逻辑到新组件
3. 保持向后兼容

### 阶段 3：算法修复

1. 修复保证金计算逻辑
2. 修复订单配对逻辑
3. 修复盈亏计算逻辑
4. 修复资金费率处理

### 阶段 4：测试和验证

1. 编写基于属性的测试
2. 运行回归测试
3. 性能基准测试
4. 修复发现的问题

### 阶段 5：优化和文档

1. 性能优化
2. 代码审查
3. 更新文档
4. 发布新版本
