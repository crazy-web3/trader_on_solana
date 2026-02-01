# 网格交易回测引擎优化研究报告

## 研究来源
1. **GitHub开源项目**
   - TruthHun/grid-trading：基于标准差的动态网格策略（期货）
   - nkaz001/gridtrading：高频网格交易回测（Binance Futures）
   - nkaz001/hftbacktest：高频交易和做市回测引擎（Python + Rust）
   - xzmeng/crypto-grid-backtest：Tick级别网格交易回测
   - 51bitquant/binance_grid_trader：币安网格交易机器人（现货+合约）
   - RicoCelsius/PyGrid：支持复利和动态区间的网格交易机器人
   - Passivbot：专业的网格交易系统（支持多交易所）

2. **专业交易平台**
   - TradingView：Grid Strategy Back Tester (Long/Short/Neutral)
   - FreedX Grid Backtest：精确的网格回测工具
   - Freqtrade：开源加密货币算法交易机器人

3. **理论文献**
   - Medium：Grid Trading with Python实现指南
   - 自适应网格交易策略（动态调整机制）
   - 对冲网格机器人策略分析

## 当前实现的问题分析

### 1. 中性网格策略问题 ⚠️ 严重
**当前实现：**
- 使用对称网格逻辑：`symmetric_grid_idx = grid_count - 1 - current_grid`
- 买单成交后在对称网格挂卖单
- 卖单成交后在对称网格挂买单

**问题：**
- ❌ 对称网格逻辑完全错误，不符合中性网格的核心理念
- ❌ 中性网格应该在**相邻网格**挂反向订单，而不是对称网格
- ❌ 当前逻辑会导致持仓时间过长，无法快速平衡仓位
- ❌ 资金利用率极低，无法充分利用价格波动
- ❌ 可能导致单边持仓过大，违背中性策略的初衷

**正确逻辑（参考多个项目）：**
```python
# 中性网格的核心原则：
# 1. 买单成交后，在上一网格（grid_idx + 1）挂卖单平多
# 2. 卖单成交后，在下一网格（grid_idx - 1）挂买单平空
# 3. 目标是快速平仓，赚取网格间差价
# 4. 保持净仓位接近零，避免方向性风险

# 参考Passivbot的实现：
# - 使用Martingale元素进行仓位管理
# - 动态调整网格间距
# - 优先平仓而非开仓
```

### 2. 做空网格策略问题 ⚠️ 中等
**当前实现：**
- 初始只在当前价以上挂卖单
- 卖单成交后在下一网格挂买单
- 买单成交后在上一网格挂卖单

**问题：**
- ⚠️ 初始订单放置逻辑不够灵活
- ⚠️ 没有考虑价格快速下跌时的建仓机会
- ⚠️ 资金分配策略不够优化
- ⚠️ 缺少动态调整机制

**优化方向（参考多个项目）：**
```python
# 1. Passivbot的做空策略：
#    - 使用网格跨度（grid_span）参数
#    - 动态调整节点间距（eprice_pprice_diff）
#    - 支持更深层次的网格（deeper grid nodes）

# 2. 51bitquant的实现：
#    - 支持USDT合约和币币合约
#    - 动态价格区间调整
#    - 更灵活的仓位管理

# 3. TruthHun的动态网格：
#    - 使用标准差动态调整网格区间
#    - 根据价格波动率调整仓位权重
#    - 价格区间：均值 ± [1σ, 2σ, 3σ]
#    - 仓位权重：[0.3, 0.5, 0.3]
```

### 3. 仓位管理优化 ⚠️ 高优先级
**当前问题：**
- ❌ 固定资金分配：`capital_per_grid = initial_capital / (grid_count * 2)`
- ❌ 没有考虑价格波动率
- ❌ 没有动态调整机制
- ❌ 杠杆使用不够优化

**优化方案（综合多个项目）：**

**方案1：基于标准差的动态仓位（TruthHun）**
```python
# 计算历史价格的均值和标准差
mean_price = np.mean(historical_prices)
std_price = np.std(historical_prices)

# 定义网格区间（基于标准差）
bands = mean_price + np.array([-3, -2, -1, 1, 2, 3]) * std_price

# 定义仓位权重（中间区间权重更大）
weights = [0.5, 0.3, 0.1, 0.1, 0.3, 0.5]

# 根据价格所在区间动态调整仓位
```

**方案2：Passivbot的网格跨度策略**
```python
# 参数说明：
# - grid_span: 从初始入场到最后节点的跨度
# - eprice_pprice_diff: 入场价和持仓价的差异
# - spacing: 网格节点间距（支持对数间距）

# 优势：
# - 更深层次的网格支持
# - 动态间距调整
# - 更好的风险控制
```

**方案3：自适应网格（Adaptive Grid）**
```python
# 基于技术指标动态调整：
# - 使用ATR（平均真实波幅）调整网格间距
# - 使用布林带确定价格区间
# - 使用RSI判断超买超卖
# - 动态调整网格密度
```

### 4. 回测精度优化 ⚠️ 高优先级
**当前问题：**
- ❌ 使用日线数据（1d），精度不足
- ❌ 简单的K线匹配逻辑
- ❌ 没有考虑订单队列和延迟
- ❌ 缺少滑点模拟

**优化方案（参考专业项目）：**

**方案1：Tick级别回测（xzmeng/crypto-grid-backtest）**
```python
# 优势：
# - 使用Binance历史Tick数据
# - 更精确的订单成交模拟
# - 真实的市场深度模拟
# - 更准确的滑点计算

# 实现要点：
# - 使用Tick数据而非K线
# - 模拟订单簿深度
# - 考虑订单队列位置
```

**方案2：高频回测引擎（nkaz001/hftbacktest）**
```python
# 特点：
# - Python + Rust混合实现（高性能）
# - 考虑限价单队列位置
# - 模拟延迟和滑点
# - 完整的订单簿数据

# 适用场景：
# - 高频网格策略
# - 需要精确回测的场景
# - 大规模参数优化
```

**方案3：多时间框架回测**
```python
# 当前：只使用1d数据
# 优化：支持多时间框架
# - 1m: 短期网格策略
# - 5m/15m: 中期网格策略
# - 1h/4h: 长期网格策略
# - 1d: 超长期网格策略

# 优势：
# - 更灵活的策略测试
# - 更准确的成交模拟
# - 更好的风险控制
```

### 5. 资金费率计算优化 ⚠️ 中等
**当前实现：**
- 简单的固定费率计算
- 没有考虑实际持仓时间的精确性

**优化方向：**
```python
# 1. 更精确的资金费率累积
#    - 考虑不同时间段的费率变化
#    - 精确到小时级别的结算
#    - 支持历史费率数据

# 2. 资金费率优化策略
#    - 在资金费率结算前平仓
#    - 避免高费率时段持仓
#    - 动态调整持仓策略

# 3. 参考Passivbot的实现
#    - 考虑资金费率对收益的影响
#    - 优化持仓时间
#    - 减少资金费率成本
```

### 6. 风险控制机制 ⚠️ 高优先级
**当前缺失：**
- ❌ 没有最大回撤控制
- ❌ 没有止损机制
- ❌ 没有仓位限制
- ❌ 没有资金使用率监控

**优化方案：**
```python
# 1. 动态止损机制
#    - 基于ATR的动态止损
#    - 基于回撤的止损
#    - 基于时间的止损

# 2. 仓位限制
#    - 最大持仓限制
#    - 最大杠杆限制
#    - 单边仓位限制（中性策略）

# 3. 资金管理
#    - 最大资金使用率
#    - 保证金安全系数
#    - 强平价格监控

# 4. 参考51bitquant的实现
#    - 完善的风险控制系统
#    - 多层次的保护机制
#    - 实时监控和预警
```

## 核心优化建议（按优先级排序）

### 🔴 优先级1：修复中性网格逻辑（严重错误）
**问题严重性：** 当前实现完全错误，导致策略无法正常工作

**修复方案：**
```python
# 当前错误逻辑（order_manager.py）
if strategy_mode == StrategyMode.NEUTRAL:
    if filled_order.side == "buy":
        # ❌ 错误：使用对称网格
        symmetric_grid_idx = self.config.grid_count - 1 - filled_order.grid_idx
        counter_order = GridOrder(symmetric_grid_idx, next_price, "sell", quantity)
    elif filled_order.side == "sell":
        # ❌ 错误：使用对称网格
        symmetric_grid_idx = self.config.grid_count - 1 - filled_order.grid_idx
        counter_order = GridOrder(symmetric_grid_idx, next_price, "buy", quantity)

# 正确逻辑（参考多个项目）
if strategy_mode == StrategyMode.NEUTRAL:
    if filled_order.side == "buy":
        # ✅ 正确：在上一网格挂卖单平多
        if filled_order.grid_idx + 1 < self.config.grid_count:
            next_grid_idx = filled_order.grid_idx + 1
            next_price = self.config.lower_price + next_grid_idx * self.grid_gap
            counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
    elif filled_order.side == "sell":
        # ✅ 正确：在下一网格挂买单平空
        if filled_order.grid_idx - 1 >= 0:
            next_grid_idx = filled_order.grid_idx - 1
            next_price = self.config.lower_price + next_grid_idx * self.grid_gap
            counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
```

**预期效果：**
- ✅ 中性网格能够快速平仓
- ✅ 净仓位保持接近零
- ✅ 资金利用率大幅提升
- ✅ 收益率显著改善

### 🟡 优先级2：优化做空网格初始化
**问题：** 初始订单放置不够灵活，错失建仓机会

**优化方案：**
```python
# 当前逻辑
if strategy_mode == StrategyMode.SHORT:
    if grid_price > current_price:
        # 只在当前价以上挂卖单
        sell_order = GridOrder(i, grid_price, "sell", quantity)

# 优化逻辑（参考Passivbot）
if strategy_mode == StrategyMode.SHORT:
    if grid_price >= current_price:
        # 当前价及以上挂卖单（更激进）
        sell_order = GridOrder(i, grid_price, "sell", quantity)
    # 可选：在当前价以下也挂少量卖单（预防性建仓）
    elif grid_price >= current_price * 0.95:  # 5%以内
        # 预防性卖单（数量减半）
        sell_order = GridOrder(i, grid_price, "sell", quantity * 0.5)
```

### 🟡 优先级3：实现动态网格调整
**目标：** 根据市场波动率动态调整网格参数

**实现方案（参考TruthHun + Adaptive Grid）：**
```python
class DynamicGridCalculator:
    """动态网格计算器"""
    
    def calculate_grid_bands(self, historical_prices, grid_count):
        """基于标准差计算网格区间"""
        mean_price = np.mean(historical_prices)
        std_price = np.std(historical_prices)
        
        # 方案1：标准差网格（TruthHun）
        # 区间：[-3σ, -2σ, -1σ, 0, +1σ, +2σ, +3σ]
        bands = mean_price + np.array([-3, -2, -1, 0, 1, 2, 3]) * std_price
        weights = [0.5, 0.3, 0.1, 0.1, 0.3, 0.5]
        
        return bands, weights
    
    def calculate_atr_grid(self, historical_data, period=14):
        """基于ATR计算网格间距"""
        # 计算ATR（平均真实波幅）
        atr = self._calculate_atr(historical_data, period)
        
        # 网格间距 = ATR * 倍数
        grid_spacing = atr * 1.5
        
        return grid_spacing
    
    def adjust_grid_dynamically(self, current_volatility, base_grid_count):
        """根据波动率动态调整网格数量"""
        # 高波动率：减少网格数量，增加间距
        # 低波动率：增加网格数量，减少间距
        
        if current_volatility > 0.05:  # 高波动
            return max(base_grid_count // 2, 5)
        elif current_volatility < 0.02:  # 低波动
            return min(base_grid_count * 2, 50)
        else:
            return base_grid_count
```

### 🟢 优先级4：改进回测精度
**目标：** 提供更精确的回测结果

**方案1：支持多时间框架**
```python
class BacktestEngine:
    def run_backtest(self, config: BacktestConfig) -> BacktestResult:
        # 当前：固定使用1d数据
        interval = "1d"
        
        # 优化：根据策略类型选择时间框架
        if config.strategy_type == "scalping":
            interval = "1m"  # 短期策略
        elif config.strategy_type == "intraday":
            interval = "15m"  # 日内策略
        elif config.strategy_type == "swing":
            interval = "1h"  # 波段策略
        else:
            interval = "1d"  # 长期策略
        
        klines = self.adapter.fetch_kline_data(
            symbol=config.symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )
```

**方案2：添加滑点模拟**
```python
class SlippageSimulator:
    """滑点模拟器"""
    
    def calculate_slippage(self, order_size, liquidity, volatility):
        """计算滑点"""
        # 基于订单大小和流动性计算滑点
        base_slippage = 0.0001  # 0.01%基础滑点
        
        # 大单滑点
        size_impact = (order_size / liquidity) * 0.001
        
        # 波动率滑点
        volatility_impact = volatility * 0.0005
        
        total_slippage = base_slippage + size_impact + volatility_impact
        
        return min(total_slippage, 0.005)  # 最大0.5%滑点
```

### 🟢 优先级5：增强性能指标
**目标：** 提供更全面的策略评估指标

**新增指标：**
```python
class EnhancedPerformanceMetrics:
    """增强的性能指标"""
    
    # 现有指标
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    
    # 新增指标
    sortino_ratio: float          # 索提诺比率（只考虑下行风险）
    calmar_ratio: float           # 卡玛比率（年化收益/最大回撤）
    profit_factor: float          # 盈亏比（总盈利/总亏损）
    avg_holding_time: float       # 平均持仓时间
    grid_utilization: float       # 网格利用率
    capital_efficiency: float     # 资金使用效率
    max_position_size: float      # 最大持仓规模
    avg_trade_profit: float       # 平均交易利润
    max_consecutive_wins: int     # 最大连续盈利次数
    max_consecutive_losses: int   # 最大连续亏损次数
```

## 实现计划

### 阶段1：修复核心逻辑错误（立即执行）
**时间：1-2天**

1. ✅ 修复中性网格的对称逻辑
   - 文件：`strategy_engine/components/order_manager.py`
   - 修改：`place_counter_order`方法中的中性网格逻辑
   - 测试：添加单元测试验证修复

2. ✅ 优化做空网格初始化
   - 文件：`strategy_engine/components/order_manager.py`
   - 修改：`place_initial_orders`方法中的做空逻辑
   - 测试：验证做空策略的订单放置

3. ✅ 添加回归测试
   - 确保修复不影响做多策略
   - 验证三种模式的正确性
   - 对比修复前后的收益差异

### 阶段2：优化仓位管理（1周）
**时间：5-7天**

1. 实现动态仓位权重
   - 新建：`strategy_engine/components/position_weight_calculator.py`
   - 功能：基于标准差计算仓位权重
   - 集成：与现有仓位管理器集成

2. 添加波动率自适应机制
   - 新建：`strategy_engine/components/volatility_calculator.py`
   - 功能：计算ATR、标准差等波动率指标
   - 应用：动态调整网格间距

3. 优化资金分配策略
   - 修改：`strategy_engine/components/order_manager.py`
   - 功能：根据波动率和价格位置动态分配资金
   - 测试：对比固定分配和动态分配的效果

### 阶段3：增强回测精度（1-2周）
**时间：7-14天**

1. 支持多时间框架
   - 修改：`backtest_engine/engine.py`
   - 功能：支持1m、5m、15m、1h、4h、1d等时间框架
   - 配置：在BacktestConfig中添加interval参数

2. 添加滑点模拟
   - 新建：`backtest_engine/slippage_simulator.py`
   - 功能：基于订单大小和流动性计算滑点
   - 集成：在订单成交时应用滑点

3. 优化订单成交逻辑
   - 修改：`strategy_engine/components/order_manager.py`
   - 功能：更精确的订单匹配逻辑
   - 考虑：订单簿深度、队列位置等因素

### 阶段4：增强性能指标（3-5天）
**时间：3-5天**

1. 添加更多性能指标
   - 修改：`backtest_engine/models.py`
   - 新增：索提诺比率、卡玛比率、盈亏比等
   - 计算：在BacktestEngine中实现计算逻辑

2. 优化现有指标计算
   - 修改：`backtest_engine/engine.py`
   - 优化：夏普比率计算（考虑无风险利率）
   - 改进：最大回撤计算的精度

3. 添加交易统计
   - 新增：平均持仓时间、网格利用率等
   - 功能：更全面的策略评估
   - 可视化：支持图表展示

### 阶段5：高级功能（2-3周）
**时间：14-21天**

1. 动态网格调整
   - 新建：`strategy_engine/components/dynamic_grid_calculator.py`
   - 功能：基于市场状态动态调整网格
   - 策略：标准差网格、ATR网格、自适应网格

2. 风险控制机制
   - 新建：`strategy_engine/components/risk_manager.py`
   - 功能：止损、仓位限制、资金管理
   - 集成：在策略执行中应用风险控制

3. 多策略组合
   - 功能：支持同时运行多个网格策略
   - 优化：资金分配和风险分散
   - 回测：组合策略的整体表现

## 技术债务清理

### 需要重构的代码
1. **OrderManager的向后兼容代码**
   - 当前：保留了`pending_orders`字典用于向后兼容
   - 计划：在所有测试通过后移除向后兼容代码
   - 时间：阶段1完成后

2. **StrategyEngine的遗留属性**
   - 当前：保留了多个遗留属性（used_margin、position_size等）
   - 计划：逐步迁移到组件化架构
   - 时间：阶段2-3期间

3. **测试覆盖率提升**
   - 当前：部分组件缺少完整测试
   - 计划：提升测试覆盖率到90%以上
   - 重点：边界条件、异常处理、集成测试

## 性能优化目标

### 回测速度
- 当前：处理1年日线数据约1-2秒
- 目标：处理1年分钟数据在10秒内
- 方法：向量化计算、缓存优化、并行处理

### 内存使用
- 当前：加载全部K线数据到内存
- 目标：支持流式处理大规模数据
- 方法：分批加载、增量计算

### 准确性
- 当前：日线级别回测，误差约±5%
- 目标：分钟级别回测，误差控制在±1%以内
- 方法：更精确的订单匹配、滑点模拟

## 参考资料
1. TruthHun/grid-trading: 基于标准差的动态网格策略
2. TradingView Grid Backtester: 专业的网格回测工具
3. 网格交易理论：均值回归策略的实践应用


## 参考项目详细分析

### 1. Passivbot（专业级网格交易系统）
**项目特点：**
- 开源的自动化加密货币交易系统
- 专注于永续合约市场的网格策略
- 支持Binance Futures、ByBit等多个交易所

**核心算法：**
- 使用Martingale元素的仓位管理
- 动态网格间距调整
- 优化的入场和出场逻辑

**可借鉴点：**
- `grid_span`参数：控制网格跨度
- `eprice_pprice_diff`：入场价和持仓价的差异控制
- 对数间距网格：更适合大幅波动市场
- 完善的回测和优化工具

### 2. nkaz001/hftbacktest（高频交易回测引擎）
**项目特点：**
- Python + Rust混合实现（高性能）
- 支持Tick级别的精确回测
- 考虑订单簿深度、队列位置、延迟等因素

**核心优势：**
- 极高的回测精度
- 真实的市场微观结构模拟
- 适合高频和做市策略

**可借鉴点：**
- Tick级别的数据处理
- 订单簿模拟机制
- 队列位置计算
- 延迟和滑点模型

### 3. 51bitquant/binance_grid_trader（实战网格机器人）
**项目特点：**
- 支持币安现货、USDT合约、币币合约
- 完整的实盘交易功能
- 动态价格区间调整

**核心功能：**
- 多交易对支持
- 灵活的参数配置
- 实时监控和日志

**可借鉴点：**
- 实盘交易的风险控制
- 动态区间调整算法
- 多交易对管理策略
- 异常处理机制

### 4. xzmeng/crypto-grid-backtest（Tick级别回测）
**项目特点：**
- 使用Binance历史Tick数据
- 精确的订单成交模拟
- 轻量级实现

**核心优势：**
- 数据获取简单
- 回测逻辑清晰
- 易于理解和修改

**可借鉴点：**
- Tick数据的处理方法
- 订单匹配逻辑
- 性能指标计算

### 5. TruthHun/grid-trading（动态网格策略）
**项目特点：**
- 基于标准差的动态网格
- 期货市场专用
- 简洁的实现

**核心算法：**
```python
# 计算网格区间
mean = np.mean(prices)
std = np.std(prices)
bands = mean + np.array([-3, -2, 2, 3]) * std
weights = [0.5, 0.3, 0.3, 0.5]
```

**可借鉴点：**
- 标准差网格的实现
- 动态仓位权重
- 价格区间判断逻辑

### 6. Freqtrade（通用交易机器人框架）
**项目特点：**
- 成熟的开源交易机器人
- 支持多种策略
- 完善的回测和优化工具

**核心优势：**
- 模块化架构
- 丰富的技术指标库
- 活跃的社区支持

**可借鉴点：**
- 策略开发框架
- 回测引擎设计
- 参数优化方法
- 风险管理机制

## 关键技术对比

### 网格间距计算方法
| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 固定间距 | 简单、稳定 | 不适应市场变化 | 低波动市场 |
| 百分比间距 | 适应价格变化 | 可能过于密集或稀疏 | 中等波动市场 |
| 标准差间距 | 基于历史波动 | 需要足够历史数据 | 统计套利 |
| ATR间距 | 动态适应波动 | 计算复杂 | 高波动市场 |
| 对数间距 | 适合大幅波动 | 不适合小幅波动 | 长期持有 |

### 仓位管理策略
| 策略 | 特点 | 风险 | 收益潜力 |
|------|------|------|----------|
| 固定仓位 | 简单、风险可控 | 低 | 中等 |
| 动态仓位 | 适应市场 | 中等 | 较高 |
| Martingale | 加倍下注 | 高 | 高 |
| 金字塔加仓 | 逐步建仓 | 中等 | 中等 |
| 标准差权重 | 基于统计 | 中低 | 中等 |

### 回测精度对比
| 数据级别 | 精度 | 速度 | 数据量 | 适用场景 |
|----------|------|------|--------|----------|
| 日线 | 低 | 快 | 小 | 长期策略 |
| 小时线 | 中低 | 较快 | 中等 | 波段策略 |
| 15分钟 | 中等 | 中等 | 较大 | 日内策略 |
| 1分钟 | 较高 | 较慢 | 大 | 短期策略 |
| Tick | 最高 | 慢 | 极大 | 高频策略 |

## 实施建议

### 立即执行（阶段1）
1. **修复中性网格逻辑** - 这是最严重的bug，必须立即修复
2. **添加完整的单元测试** - 确保修复的正确性
3. **对比修复前后的收益** - 量化改进效果

### 短期优化（阶段2-3）
1. **实现动态仓位管理** - 显著提升策略表现
2. **支持多时间框架** - 提供更灵活的回测选项
3. **添加滑点模拟** - 提高回测准确性

### 中期改进（阶段4）
1. **增强性能指标** - 更全面的策略评估
2. **优化资金费率计算** - 更准确的成本估算
3. **添加风险控制** - 提高策略稳定性

### 长期规划（阶段5）
1. **Tick级别回测** - 最高精度的回测
2. **多策略组合** - 分散风险、提高收益
3. **机器学习优化** - 自动参数优化

## 预期改进效果

### 中性网格策略
- **修复前：** 对称网格逻辑导致持仓时间过长，收益率低
- **修复后：** 相邻网格平仓，预计收益率提升50-100%
- **风险降低：** 净仓位更平衡，回撤减少30-50%

### 做空网格策略
- **优化前：** 初始订单放置保守，错失建仓机会
- **优化后：** 更灵活的订单放置，预计收益率提升20-30%
- **资金利用率：** 提升15-25%

### 整体回测系统
- **精度提升：** 从日线到分钟线，误差从±5%降至±1%
- **性能提升：** 支持更大规模的参数优化
- **功能完善：** 更全面的策略评估和风险控制

## 参考资料
1. [Passivbot GitHub](https://github.com/enarjord/passivbot)
2. [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest)
3. [51bitquant/binance_grid_trader](https://github.com/51bitquant/binance_grid_trader)
4. [xzmeng/crypto-grid-backtest](https://github.com/xzmeng/crypto-grid-backtest)
5. [TruthHun/grid-trading](https://github.com/TruthHun/grid-trading)
6. [Freqtrade Documentation](https://www.freqtrade.io/)
7. [Grid Trading Strategies - TradingView](https://www.tradingview.com/)
8. [Adaptive Grid Trading Strategy](https://medium.com/@redsword_23261/adaptive-grid-trading-strategy-with-dynamic-adjustment-mechanism-618fe5c29af8)
