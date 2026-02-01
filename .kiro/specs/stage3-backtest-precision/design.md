# 设计文档：阶段3 - 回测精度增强

## 概述

本文档描述阶段3的技术设计方案，重点是通过多时间框架支持、滑点模拟和改进的订单成交逻辑来提升回测精度。

### 设计目标

1. **多时间框架支持**：支持1m、5m、15m、1h、4h、1d等常见时间框架
2. **滑点模拟**：基于订单大小、流动性和波动率的真实滑点计算
3. **订单成交优化**：更精确的K线匹配和部分成交模拟
4. **向后兼容**：不破坏现有功能，支持渐进式采用
5. **性能目标**：1年1分钟数据在30秒内完成，精度提升到±1%

### 当前状态分析

**已完成（阶段1-2）：**
- ✅ 核心逻辑修复（中性网格、订单配对）
- ✅ 动态仓位管理（标准差权重、ATR自适应）
- ✅ 完整的组件化架构
- ✅ 340个测试用例，100%通过率

**待改进（阶段3）：**
- ⚠️ 仅支持单一时间框架（默认1d）
- ⚠️ 无滑点模拟，成交价格过于理想化
- ⚠️ 订单成交逻辑简化，仅检查high/low
- ⚠️ 回测误差约±5%，与实盘有差距

## 架构设计

### 新增组件

```
backtest_engine/
├── engine.py                    # 主引擎（需修改）
├── models.py                    # 数据模型（需扩展）
├── slippage_simulator.py        # 新增：滑点模拟器
├── order_fill_simulator.py      # 新增：订单成交模拟器
└── order_book_simulator.py      # 新增：订单簿模拟器（可选）

market_data_layer/
├── adapter.py                   # 数据适配器（需修改）
└── models.py                    # K线数据模型
```

### 组件交互流程

```
BacktestEngine
    ↓
MarketDataAdapter (获取指定时间框架的K线数据)
    ↓
GridStrategyEngine (处理K线)
    ↓
OrderFillSimulator (检查订单成交)
    ↓
SlippageSimulator (计算滑点)
    ↓
PositionManager (更新仓位)
```

## 组件设计

### 1. TimeframeConfig（时间框架配置）

```python
from enum import Enum
from dataclasses import dataclass

class Timeframe(Enum):
    """支持的时间框架"""
    M1 = "1m"   # 1分钟
    M5 = "5m"   # 5分钟
    M15 = "15m" # 15分钟
    H1 = "1h"   # 1小时
    H4 = "4h"   # 4小时
    D1 = "1d"   # 1天
    
    @property
    def milliseconds(self) -> int:
        """返回时间框架对应的毫秒数"""
        mapping = {
            "1m": 60_000,
            "5m": 300_000,
            "15m": 900_000,
            "1h": 3_600_000,
            "4h": 14_400_000,
            "1d": 86_400_000,
        }
        return mapping[self.value]
```

### 2. SlippageSimulator（滑点模拟器）

```python
@dataclass
class SlippageConfig:
    """滑点配置"""
    enabled: bool = True
    base_slippage: float = 0.0001  # 基础滑点 0.01%
    size_impact_factor: float = 0.001  # 订单大小影响系数
    volatility_impact_factor: float = 0.0005  # 波动率影响系数
    max_slippage: float = 0.005  # 最大滑点 0.5%
    model: str = "linear"  # 滑点模型：linear, sqrt, volatility

class SlippageSimulator:
    """滑点模拟器"""
    
    def __init__(self, config: SlippageConfig):
        self.config = config
        self.total_slippage_cost = 0.0
    
    def calculate_slippage(
        self,
        order_size: float,
        order_price: float,
        market_volume: float,
        volatility: float
    ) -> float:
        """
        计算滑点
        
        Args:
            order_size: 订单数量
            order_price: 订单价格
            market_volume: 市场成交量
            volatility: 市场波动率
            
        Returns:
            滑点比例（如0.0001表示0.01%）
        """
        if not self.config.enabled:
            return 0.0
        
        # 基础滑点
        slippage = self.config.base_slippage
        
        # 订单大小影响
        order_value = order_size * order_price
        size_ratio = order_value / (market_volume * order_price) if market_volume > 0 else 0.1
        
        if self.config.model == "linear":
            slippage += size_ratio * self.config.size_impact_factor
        elif self.config.model == "sqrt":
            slippage += (size_ratio ** 0.5) * self.config.size_impact_factor
        
        # 波动率影响
        slippage += volatility * self.config.volatility_impact_factor
        
        # 限制最大滑点
        slippage = min(slippage, self.config.max_slippage)
        
        return slippage
    
    def apply_slippage(
        self,
        order_price: float,
        slippage: float,
        side: str
    ) -> float:
        """
        应用滑点到订单价格
        
        Args:
            order_price: 原始订单价格
            slippage: 滑点比例
            side: 订单方向 "buy" 或 "sell"
            
        Returns:
            考虑滑点后的实际成交价格
        """
        if side == "buy":
            # 买单滑点向上
            actual_price = order_price * (1 + slippage)
        else:
            # 卖单滑点向下
            actual_price = order_price * (1 - slippage)
        
        # 记录滑点成本
        slippage_cost = abs(actual_price - order_price) * 1  # 假设1单位数量
        self.total_slippage_cost += slippage_cost
        
        return actual_price
    
    def get_total_slippage_cost(self) -> float:
        """获取总滑点成本"""
        return self.total_slippage_cost
```

### 3. OrderFillSimulator（订单成交模拟器）

```python
@dataclass
class OrderFillConfig:
    """订单成交配置"""
    enable_partial_fill: bool = False  # 是否启用部分成交
    enable_realistic_timing: bool = True  # 是否启用真实时间模拟
    min_fill_ratio: float = 0.1  # 最小成交比例

class OrderFillSimulator:
    """订单成交模拟器"""
    
    def __init__(self, config: OrderFillConfig):
        self.config = config
    
    def check_limit_order_fill(
        self,
        order: GridOrder,
        kline: KlineData
    ) -> tuple[bool, float, int]:
        """
        检查限价单是否成交
        
        Args:
            order: 网格订单
            kline: K线数据
            
        Returns:
            (是否成交, 成交价格, 成交时间戳)
        """
        if order.side == "buy":
            # 买单：当最低价触及或低于订单价格时成交
            if kline.low <= order.price:
                fill_price = order.price
                # 估算成交时间（在K线内的相对位置）
                fill_time = self._estimate_fill_time(
                    kline, order.price, "buy"
                )
                return True, fill_price, fill_time
        else:  # sell
            # 卖单：当最高价触及或高于订单价格时成交
            if kline.high >= order.price:
                fill_price = order.price
                fill_time = self._estimate_fill_time(
                    kline, order.price, "sell"
                )
                return True, fill_price, fill_time
        
        return False, 0.0, 0
    
    def _estimate_fill_time(
        self,
        kline: KlineData,
        fill_price: float,
        side: str
    ) -> int:
        """
        估算订单在K线内的成交时间
        
        基于价格在K线内的相对位置估算
        """
        if not self.config.enable_realistic_timing:
            return kline.timestamp
        
        # 简化模型：假设价格在K线内线性变化
        # 实际可以使用更复杂的模型
        price_range = kline.high - kline.low
        if price_range == 0:
            return kline.timestamp
        
        if side == "buy":
            # 买单在价格下跌时成交
            ratio = (kline.high - fill_price) / price_range
        else:
            # 卖单在价格上涨时成交
            ratio = (fill_price - kline.low) / price_range
        
        # 假设K线时间跨度（需要从配置获取）
        kline_duration = 86400000  # 1天，实际应该从timeframe获取
        fill_time = kline.timestamp + int(kline_duration * ratio)
        
        return fill_time
    
    def simulate_partial_fill(
        self,
        order: GridOrder,
        available_liquidity: float
    ) -> float:
        """
        模拟部分成交
        
        Args:
            order: 网格订单
            available_liquidity: 可用流动性
            
        Returns:
            实际成交数量
        """
        if not self.config.enable_partial_fill:
            return order.quantity
        
        # 如果流动性充足，全部成交
        if available_liquidity >= order.quantity:
            return order.quantity
        
        # 部分成交，但至少成交最小比例
        min_fill = order.quantity * self.config.min_fill_ratio
        actual_fill = max(available_liquidity, min_fill)
        actual_fill = min(actual_fill, order.quantity)
        
        return actual_fill
```

### 4. OrderBookSimulator（订单簿模拟器 - 可选）

```python
@dataclass
class OrderBookConfig:
    """订单簿配置"""
    enabled: bool = False
    depth_levels: int = 10  # 订单簿深度层级
    liquidity_per_level: float = 1000.0  # 每层流动性
    spread_bps: float = 10.0  # 买卖价差（基点）

class OrderBookSimulator:
    """订单簿模拟器（简化版）"""
    
    def __init__(self, config: OrderBookConfig):
        self.config = config
        self.bid_levels: dict[float, float] = {}  # 价格 -> 数量
        self.ask_levels: dict[float, float] = {}
    
    def initialize_order_book(
        self,
        mid_price: float,
        tick_size: float = 0.01
    ) -> None:
        """
        初始化订单簿
        
        Args:
            mid_price: 中间价格
            tick_size: 最小价格变动单位
        """
        if not self.config.enabled:
            return
        
        spread = mid_price * self.config.spread_bps / 10000
        best_bid = mid_price - spread / 2
        best_ask = mid_price + spread / 2
        
        # 初始化买单簿
        for i in range(self.config.depth_levels):
            price = best_bid - i * tick_size
            self.bid_levels[price] = self.config.liquidity_per_level
        
        # 初始化卖单簿
        for i in range(self.config.depth_levels):
            price = best_ask + i * tick_size
            self.ask_levels[price] = self.config.liquidity_per_level
    
    def estimate_market_impact(
        self,
        order_size: float,
        side: str
    ) -> float:
        """
        估算市场冲击
        
        Args:
            order_size: 订单数量
            side: 订单方向
            
        Returns:
            平均成交价格
        """
        if not self.config.enabled:
            return 0.0
        
        levels = self.ask_levels if side == "buy" else self.bid_levels
        remaining_size = order_size
        total_cost = 0.0
        
        for price in sorted(levels.keys()):
            available = levels[price]
            filled = min(remaining_size, available)
            total_cost += filled * price
            remaining_size -= filled
            
            if remaining_size <= 0:
                break
        
        if remaining_size > 0:
            # 流动性不足，使用最后价格
            last_price = list(levels.keys())[-1]
            total_cost += remaining_size * last_price
        
        avg_price = total_cost / order_size
        return avg_price
    
    def consume_liquidity(
        self,
        order_size: float,
        side: str
    ) -> None:
        """
        消耗流动性
        
        Args:
            order_size: 订单数量
            side: 订单方向
        """
        if not self.config.enabled:
            return
        
        levels = self.ask_levels if side == "buy" else self.bid_levels
        remaining_size = order_size
        
        for price in sorted(levels.keys()):
            if remaining_size <= 0:
                break
            
            available = levels[price]
            consumed = min(remaining_size, available)
            levels[price] -= consumed
            remaining_size -= consumed
```

## 数据模型扩展

### BacktestConfig 扩展

```python
@dataclass
class BacktestConfig:
    """回测配置（扩展）"""
    # 现有字段...
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    
    # 新增字段
    timeframe: Timeframe = Timeframe.D1  # 时间框架
    slippage_config: SlippageConfig = None  # 滑点配置
    order_fill_config: OrderFillConfig = None  # 订单成交配置
    order_book_config: OrderBookConfig = None  # 订单簿配置（可选）
    
    def __post_init__(self):
        """初始化默认配置"""
        if self.slippage_config is None:
            self.slippage_config = SlippageConfig()
        if self.order_fill_config is None:
            self.order_fill_config = OrderFillConfig()
        if self.order_book_config is None:
            self.order_book_config = OrderBookConfig()
```

### BacktestResult 扩展

```python
@dataclass
class BacktestResult:
    """回测结果（扩展）"""
    # 现有字段...
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    
    # 新增字段
    total_slippage_cost: float = 0.0  # 总滑点成本
    slippage_impact_pct: float = 0.0  # 滑点影响百分比
    avg_slippage_bps: float = 0.0  # 平均滑点（基点）
    partial_fills_count: int = 0  # 部分成交次数
    timeframe_used: str = "1d"  # 使用的时间框架
```

## 集成方案

### MarketDataAdapter 修改

```python
class MarketDataAdapter:
    """市场数据适配器（修改）"""
    
    def get_klines(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: Timeframe = Timeframe.D1  # 新增参数
    ) -> List[KlineData]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对
            start_date: 开始日期
            end_date: 结束日期
            timeframe: 时间框架
            
        Returns:
            K线数据列表
        """
        # 实现根据时间框架获取数据的逻辑
        # 可能需要聚合更小时间框架的数据
        pass
```

### BacktestEngine 修改

```python
class BacktestEngine:
    """回测引擎（修改）"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        # 初始化新组件
        self.slippage_simulator = SlippageSimulator(config.slippage_config)
        self.order_fill_simulator = OrderFillSimulator(config.order_fill_config)
        self.order_book_simulator = OrderBookSimulator(config.order_book_config)
        
        # 现有组件...
        self.strategy_engine = None
        self.market_data = None
    
    def run(self, strategy_config: StrategyConfig) -> BacktestResult:
        """
        运行回测
        
        Args:
            strategy_config: 策略配置
            
        Returns:
            回测结果
        """
        # 1. 获取指定时间框架的K线数据
        klines = self.market_data.get_klines(
            self.config.symbol,
            self.config.start_date,
            self.config.end_date,
            self.config.timeframe  # 使用配置的时间框架
        )
        
        # 2. 初始化策略引擎
        self.strategy_engine = GridStrategyEngine(strategy_config)
        
        # 3. 初始化订单簿（如果启用）
        if self.config.order_book_config.enabled:
            self.order_book_simulator.initialize_order_book(
                klines[0].close
            )
        
        # 4. 处理每根K线
        for kline in klines:
            self._process_kline_with_precision(kline)
        
        # 5. 计算结果（包含滑点影响）
        result = self._calculate_result_with_slippage()
        
        return result
    
    def _process_kline_with_precision(self, kline: KlineData) -> None:
        """
        使用精确模拟处理K线
        
        Args:
            kline: K线数据
        """
        # 检查订单成交（使用新的成交模拟器）
        pending_orders = self.strategy_engine.order_manager.get_pending_orders()
        
        for order in pending_orders.values():
            # 1. 检查是否成交
            is_filled, fill_price, fill_time = \
                self.order_fill_simulator.check_limit_order_fill(order, kline)
            
            if not is_filled:
                continue
            
            # 2. 计算滑点
            slippage = self.slippage_simulator.calculate_slippage(
                order.quantity,
                fill_price,
                kline.volume,
                self._calculate_volatility(kline)
            )
            
            # 3. 应用滑点
            actual_price = self.slippage_simulator.apply_slippage(
                fill_price,
                slippage,
                order.side
            )
            
            # 4. 模拟部分成交（如果启用）
            actual_quantity = order.quantity
            if self.config.order_fill_config.enable_partial_fill:
                available_liquidity = self._estimate_liquidity(kline, order)
                actual_quantity = self.order_fill_simulator.simulate_partial_fill(
                    order,
                    available_liquidity
                )
            
            # 5. 执行订单
            self.strategy_engine._fill_order(
                order,
                actual_price,
                actual_quantity,
                fill_time
            )
```

## 性能优化策略

### 1. 数据预处理

```python
class KlinePreprocessor:
    """K线数据预处理器"""
    
    @staticmethod
    def precompute_volatility(klines: List[KlineData], window: int = 20) -> List[float]:
        """
        预计算波动率
        
        避免在每次订单成交时重复计算
        """
        volatilities = []
        prices = [k.close for k in klines]
        
        for i in range(len(prices)):
            if i < window:
                volatilities.append(0.01)  # 默认波动率
            else:
                window_prices = prices[i-window:i]
                returns = [
                    (window_prices[j] - window_prices[j-1]) / window_prices[j-1]
                    for j in range(1, len(window_prices))
                ]
                volatility = np.std(returns)
                volatilities.append(volatility)
        
        return volatilities
```

### 2. 缓存机制

```python
from functools import lru_cache

class CachedSlippageSimulator(SlippageSimulator):
    """带缓存的滑点模拟器"""
    
    @lru_cache(maxsize=1000)
    def calculate_slippage_cached(
        self,
        order_size: float,
        order_price: float,
        market_volume: float,
        volatility: float
    ) -> float:
        """缓存滑点计算结果"""
        return self.calculate_slippage(
            order_size,
            order_price,
            market_volume,
            volatility
        )
```

### 3. 向量化计算

```python
import numpy as np

class VectorizedOrderFillChecker:
    """向量化订单成交检查"""
    
    @staticmethod
    def batch_check_fills(
        orders: List[GridOrder],
        klines: List[KlineData]
    ) -> np.ndarray:
        """
        批量检查订单成交
        
        使用NumPy向量化操作提高性能
        """
        order_prices = np.array([o.price for o in orders])
        kline_highs = np.array([k.high for k in klines])
        kline_lows = np.array([k.low for k in klines])
        
        # 向量化比较
        buy_fills = kline_lows[:, np.newaxis] <= order_prices
        sell_fills = kline_highs[:, np.newaxis] >= order_prices
        
        return buy_fills, sell_fills
```

## 测试策略

### 1. 单元测试

```python
# tests/test_slippage_simulator.py
def test_slippage_calculation():
    """测试滑点计算"""
    config = SlippageConfig(
        base_slippage=0.0001,
        size_impact_factor=0.001,
        model="linear"
    )
    simulator = SlippageSimulator(config)
    
    # 小订单，低滑点
    slippage = simulator.calculate_slippage(
        order_size=1.0,
        order_price=50000.0,
        market_volume=1000.0,
        volatility=0.01
    )
    assert 0.0001 <= slippage <= 0.001
    
    # 大订单，高滑点
    slippage = simulator.calculate_slippage(
        order_size=100.0,
        order_price=50000.0,
        market_volume=1000.0,
        volatility=0.01
    )
    assert slippage > 0.001

def test_slippage_application():
    """测试滑点应用"""
    config = SlippageConfig()
    simulator = SlippageSimulator(config)
    
    # 买单滑点向上
    actual_price = simulator.apply_slippage(50000.0, 0.0001, "buy")
    assert actual_price > 50000.0
    
    # 卖单滑点向下
    actual_price = simulator.apply_slippage(50000.0, 0.0001, "sell")
    assert actual_price < 50000.0
```

### 2. 属性测试

```python
from hypothesis import given, strategies as st

@given(
    order_size=st.floats(min_value=0.1, max_value=100.0),
    order_price=st.floats(min_value=1000.0, max_value=100000.0),
    market_volume=st.floats(min_value=100.0, max_value=10000.0),
    volatility=st.floats(min_value=0.001, max_value=0.1)
)
def test_slippage_properties(order_size, order_price, market_volume, volatility):
    """
    属性：滑点应该随订单大小和波动率增加而增加
    """
    config = SlippageConfig()
    simulator = SlippageSimulator(config)
    
    slippage = simulator.calculate_slippage(
        order_size, order_price, market_volume, volatility
    )
    
    # 属性1：滑点应该非负
    assert slippage >= 0
    
    # 属性2：滑点应该不超过最大值
    assert slippage <= config.max_slippage
    
    # 属性3：更大的订单应该有更大的滑点
    larger_slippage = simulator.calculate_slippage(
        order_size * 2, order_price, market_volume, volatility
    )
    assert larger_slippage >= slippage
```

### 3. 集成测试

```python
def test_backtest_with_slippage():
    """测试带滑点的完整回测"""
    # 配置
    backtest_config = BacktestConfig(
        symbol="BTC/USDT",
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=10000.0,
        timeframe=Timeframe.H1,
        slippage_config=SlippageConfig(enabled=True)
    )
    
    strategy_config = StrategyConfig(
        mode=StrategyMode.NEUTRAL,
        lower_price=40000.0,
        upper_price=60000.0,
        grid_count=10,
        initial_capital=10000.0,
        leverage=1.0
    )
    
    # 运行回测
    engine = BacktestEngine(backtest_config)
    result = engine.run(strategy_config)
    
    # 验证滑点影响
    assert result.total_slippage_cost > 0
    assert result.slippage_impact_pct > 0
    
    # 验证收益率降低（因为滑点）
    # 与无滑点版本对比
    backtest_config_no_slippage = BacktestConfig(
        symbol="BTC/USDT",
        start_date="2024-01-01",
        end_date="2024-12-31",
        initial_capital=10000.0,
        timeframe=Timeframe.H1,
        slippage_config=SlippageConfig(enabled=False)
    )
    
    engine_no_slippage = BacktestEngine(backtest_config_no_slippage)
    result_no_slippage = engine_no_slippage.run(strategy_config)
    
    # 有滑点的收益应该更低
    assert result.total_return < result_no_slippage.total_return
```

## 向后兼容性

### 默认行为保持不变

```python
# 不指定新参数时，行为与阶段2相同
config = BacktestConfig(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=10000.0
    # timeframe 默认为 D1
    # slippage_config 默认禁用
    # order_fill_config 使用简单模式
)

# 这将产生与阶段2完全相同的结果
```

### 渐进式采用

```python
# 用户可以逐步启用新功能

# 1. 只改变时间框架
config1 = BacktestConfig(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=10000.0,
    timeframe=Timeframe.H1  # 只改这个
)

# 2. 添加滑点模拟
config2 = BacktestConfig(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=10000.0,
    timeframe=Timeframe.H1,
    slippage_config=SlippageConfig(enabled=True)  # 添加这个
)

# 3. 启用所有高级功能
config3 = BacktestConfig(
    symbol="BTC/USDT",
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_capital=10000.0,
    timeframe=Timeframe.M5,
    slippage_config=SlippageConfig(enabled=True),
    order_fill_config=OrderFillConfig(enable_partial_fill=True),
    order_book_config=OrderBookConfig(enabled=True)
)
```

## 性能基准

### 目标性能

| 时间框架 | 数据量（1年） | 目标时间 | 内存使用 |
|----------|---------------|----------|----------|
| 1m | ~525,600条 | <30秒 | <2GB |
| 5m | ~105,120条 | <15秒 | <1GB |
| 15m | ~35,040条 | <10秒 | <500MB |
| 1h | ~8,760条 | <5秒 | <200MB |
| 4h | ~2,190条 | <3秒 | <100MB |
| 1d | ~365条 | <2秒 | <50MB |

### 优化措施

1. **数据预处理**：预计算波动率、成交量等指标
2. **缓存机制**：缓存重复的滑点计算结果
3. **向量化**：使用NumPy批量处理订单检查
4. **延迟计算**：仅在需要时计算复杂指标
5. **内存管理**：及时清理不需要的数据

## 错误处理

### 配置验证

```python
class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_backtest_config(config: BacktestConfig) -> None:
        """验证回测配置"""
        # 验证时间框架
        if not isinstance(config.timeframe, Timeframe):
            raise ValueError(f"Invalid timeframe: {config.timeframe}")
        
        # 验证滑点配置
        if config.slippage_config.enabled:
            if config.slippage_config.base_slippage < 0:
                raise ValueError("Base slippage must be non-negative")
            if config.slippage_config.max_slippage < config.slippage_config.base_slippage:
                raise ValueError("Max slippage must be >= base slippage")
        
        # 验证订单成交配置
        if config.order_fill_config.enable_partial_fill:
            if not 0 < config.order_fill_config.min_fill_ratio <= 1:
                raise ValueError("Min fill ratio must be in (0, 1]")
```

### 数据异常处理

```python
class DataValidator:
    """数据验证器"""
    
    @staticmethod
    def validate_kline(kline: KlineData) -> bool:
        """验证K线数据"""
        # 检查价格关系
        if kline.high < kline.low:
            logger.warning(f"Invalid kline: high < low at {kline.timestamp}")
            return False
        
        if kline.high < kline.open or kline.high < kline.close:
            logger.warning(f"Invalid kline: high < open/close at {kline.timestamp}")
            return False
        
        if kline.low > kline.open or kline.low > kline.close:
            logger.warning(f"Invalid kline: low > open/close at {kline.timestamp}")
            return False
        
        # 检查成交量
        if kline.volume < 0:
            logger.warning(f"Invalid kline: negative volume at {kline.timestamp}")
            return False
        
        return True
```

## 实施计划

### 第1步：多时间框架支持（2-3天）

**任务：**
1. 创建 `Timeframe` 枚举类
2. 修改 `BacktestConfig` 添加 `timeframe` 字段
3. 修改 `MarketDataAdapter` 支持不同时间框架
4. 更新 `BacktestEngine` 使用配置的时间框架
5. 编写单元测试和集成测试

**文件：**
- `backtest_engine/models.py`（修改）
- `market_data_layer/adapter.py`（修改）
- `backtest_engine/engine.py`（修改）
- `tests/test_multi_timeframe.py`（新增）

### 第2步：滑点模拟器（2-3天）

**任务：**
1. 创建 `SlippageConfig` 数据类
2. 实现 `SlippageSimulator` 类
3. 集成到 `BacktestEngine`
4. 添加滑点影响分析
5. 编写单元测试和属性测试

**文件：**
- `backtest_engine/slippage_simulator.py`（新增）
- `backtest_engine/models.py`（修改）
- `backtest_engine/engine.py`（修改）
- `tests/test_slippage_simulator.py`（新增）

### 第3步：订单成交优化（2-3天）

**任务：**
1. 创建 `OrderFillConfig` 数据类
2. 实现 `OrderFillSimulator` 类
3. 改进K线匹配逻辑
4. 实现部分成交模拟
5. 编写单元测试和集成测试

**文件：**
- `backtest_engine/order_fill_simulator.py`（新增）
- `backtest_engine/models.py`（修改）
- `backtest_engine/engine.py`（修改）
- `tests/test_order_fill_simulator.py`（新增）

### 第4步：订单簿模拟器（可选，2-3天）

**任务：**
1. 创建 `OrderBookConfig` 数据类
2. 实现 `OrderBookSimulator` 类
3. 集成到 `BacktestEngine`
4. 编写单元测试

**文件：**
- `backtest_engine/order_book_simulator.py`（新增）
- `backtest_engine/models.py`（修改）
- `backtest_engine/engine.py`（修改）
- `tests/test_order_book_simulator.py`（新增）

### 第5步：集成测试和文档（1-2天）

**任务：**
1. 编写完整的集成测试
2. 性能基准测试
3. 编写演示脚本
4. 更新文档
5. 创建阶段3完成报告

**文件：**
- `tests/test_stage3_integration.py`（新增）
- `demo_backtest_precision.py`（新增）
- `STAGE3_COMPLETE.md`（新增）
- `docs/BACKTEST_ENGINE.md`（更新）

## 风险和缓解措施

### 风险1：性能下降

**描述：** 增加精度可能导致回测速度显著下降

**缓解措施：**
- 使用向量化计算（NumPy）
- 实现数据缓存机制
- 预计算常用指标
- 提供性能配置选项（用户可以在精度和速度间权衡）

### 风险2：复杂度增加

**描述：** 新增功能可能增加系统复杂度，影响可维护性

**缓解措施：**
- 保持模块化设计
- 清晰的接口定义
- 完整的文档和示例
- 渐进式采用策略

### 风险3：向后兼容性

**描述：** 修改可能破坏现有功能

**缓解措施：**
- 默认配置保持向后兼容
- 完整的回归测试
- 新功能通过配置启用
- 保留旧接口

## 成功标准

### 功能完整性
- [ ] 支持所有6种时间框架
- [ ] 滑点模拟准确且可配置
- [ ] 订单成交逻辑改进
- [ ] 所有测试通过（预计>380个测试）

### 性能达标
- [ ] 1年1分钟数据在30秒内完成
- [ ] 内存使用在2GB以内
- [ ] 回测精度提升到±1%

### 文档完整
- [ ] API文档完整
- [ ] 使用示例清晰
- [ ] 演示脚本可运行
- [ ] 阶段完成报告详细

---

**文档版本：** 1.0  
**创建日期：** 2026-02-01  
**最后更新：** 2026-02-01  
**状态：** 待审核
