# 网格逻辑修复规格说明

## 问题总结

当前实现在价格快速跨越多个网格时，只在相邻网格产生交易，导致收益计算不完整。

## 修复目标

确保价格跨越每个网格时都产生相应的交易和收益。

## 修复方案

### 方案选择

采用**混合方案**：
- 保持订单管理和仓位管理的框架（真实交易模拟）
- 但在价格跨越多个网格时，自动在所有中间网格产生交易

### 实现策略

在`strategy_engine/engine.py`的`_process_kline`方法中添加逻辑：

```python
def _process_kline(self, kline: KlineData) -> None:
    """处理单个K线"""
    
    # 1. 初始化网格
    if not self.pending_orders:
        self._place_initial_orders(kline.close)
        self.last_price = kline.close
        return
    
    # 2. 检测价格跨越的网格
    crossed_grids = self._detect_crossed_grids(self.last_price, kline)
    
    # 3. 对每个跨越的网格产生交易
    for grid_info in crossed_grids:
        self._execute_grid_trade(grid_info, kline)
    
    # 4. 更新最后价格
    self.last_price = kline.close
```

### 核心方法

#### 1. 检测跨越的网格

```python
def _detect_crossed_grids(self, prev_price: float, kline: KlineData) -> List[Dict]:
    """检测价格跨越了哪些网格
    
    Returns:
        List of dicts with grid info: {
            'grid_idx': int,
            'grid_price': float,
            'direction': 'up' or 'down',
            'entry_price': float,
            'exit_price': float
        }
    """
    crossed = []
    
    # 找到前一个价格和当前价格所在的网格索引
    prev_idx = self._find_grid_index(prev_price)
    
    # 检查K线的高低点
    high_idx = self._find_grid_index(kline.high)
    low_idx = self._find_grid_index(kline.low)
    
    # 价格下跌：从prev_idx到low_idx
    if low_idx < prev_idx:
        for idx in range(low_idx, prev_idx):
            crossed.append({
                'grid_idx': idx,
                'grid_price': self.strategy.grid_prices[idx],
                'direction': 'down',
                'entry_price': self.strategy.grid_prices[idx + 1],
                'exit_price': self.strategy.grid_prices[idx]
            })
    
    # 价格上涨：从prev_idx到high_idx
    elif high_idx > prev_idx:
        for idx in range(prev_idx + 1, high_idx + 1):
            crossed.append({
                'grid_idx': idx,
                'grid_price': self.strategy.grid_prices[idx],
                'direction': 'up',
                'entry_price': self.strategy.grid_prices[idx - 1],
                'exit_price': self.strategy.grid_prices[idx]
            })
    
    return crossed
```

#### 2. 执行网格交易

```python
def _execute_grid_trade(self, grid_info: Dict, kline: KlineData) -> None:
    """在指定网格执行交易"""
    
    grid_idx = grid_info['grid_idx']
    direction = grid_info['direction']
    
    if self.config.mode == StrategyMode.SHORT:
        if direction == 'down':
            # 做空网格：价格下跌时盈利
            # 在上一个网格卖出，在当前网格买入
            quantity = self.capital_per_grid / grid_info['entry_price']
            profit = (grid_info['entry_price'] - grid_info['exit_price']) * quantity
            
            # 扣除手续费
            fee = profit * self.config.fee_rate * 2  # 开仓+平仓
            profit -= fee
            
            # 更新资金
            self.capital += profit
            self.grid_profit += profit
            self.total_fees += fee
            
            # 记录交易
            self._record_trade(grid_info, quantity, profit, fee, kline)
    
    elif self.config.mode == StrategyMode.LONG:
        if direction == 'up':
            # 做多网格：价格上涨时盈利
            quantity = self.capital_per_grid / grid_info['entry_price']
            profit = (grid_info['exit_price'] - grid_info['entry_price']) * quantity
            
            # 扣除手续费
            fee = profit * self.config.fee_rate * 2
            profit -= fee
            
            # 更新资金
            self.capital += profit
            self.grid_profit += profit
            self.total_fees += fee
            
            # 记录交易
            self._record_trade(grid_info, quantity, profit, fee, kline)
    
    elif self.config.mode == StrategyMode.NEUTRAL:
        # 中性网格：双向都交易
        quantity = self.capital_per_grid / grid_info['entry_price']
        profit = abs(grid_info['exit_price'] - grid_info['entry_price']) * quantity
        
        # 扣除手续费
        fee = profit * self.config.fee_rate * 2
        profit -= fee
        
        # 更新资金
        self.capital += profit
        self.grid_profit += profit
        self.total_fees += fee
        
        # 记录交易
        self._record_trade(grid_info, quantity, profit, fee, kline)
```

## 实现步骤

### 第1步：添加辅助方法

在`GridStrategyEngine`类中添加：
- `_find_grid_index(price)`: 找到价格所在的网格索引
- `_detect_crossed_grids(prev_price, kline)`: 检测跨越的网格
- `_execute_grid_trade(grid_info, kline)`: 执行网格交易
- `_record_trade(grid_info, quantity, profit, fee, kline)`: 记录交易

### 第2步：修改_process_kline方法

添加跨网格检测和交易逻辑。

### 第3步：保持向后兼容

- 保留现有的订单管理系统（用于更复杂的场景）
- 新逻辑作为补充，确保不遗漏任何网格交易

### 第4步：测试验证

1. 单元测试：测试网格检测逻辑
2. 集成测试：测试完整回测流程
3. 对比测试：与DeepSeek的理论模型对比
4. 真实数据测试：使用ETH 90天数据验证

## 预期结果

修复后，使用相同的测试数据：
- 价格: 3000 → 2900 → 2800 → 2700 → 2600 → 2500
- 应该产生4笔交易（而不是2笔）
- 收益应该接近$242.83（而不是$27.78）

## 风险评估

### 风险

1. **破坏现有功能**: 修改核心逻辑可能影响其他功能
2. **测试覆盖不足**: 需要大量测试确保正确性
3. **性能影响**: 新逻辑可能影响性能

### 缓解措施

1. **渐进式修改**: 先添加新方法，再逐步集成
2. **完整测试**: 运行所有422个现有测试
3. **性能测试**: 确保性能不降级
4. **回滚计划**: 保留旧代码，出问题可以回滚

## 时间估算

- 实现: 2-3小时
- 测试: 1-2小时
- 验证: 1小时
- 总计: 4-6小时

## 优先级

**紧急** - 这是影响核心功能的严重bug，需要立即修复。

---

**创建日期**: 2026-02-01  
**状态**: 待实施  
**负责人**: Kiro AI Agent  
