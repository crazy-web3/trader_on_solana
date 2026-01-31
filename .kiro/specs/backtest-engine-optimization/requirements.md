# 需求文档

## 引言

本文档定义了合约网格交易回测系统优化项目的需求。该系统是一个永续合约网格交易回测平台，支持做多、做空和中性三种网格策略。当前系统存在算法准确性、代码可维护性和性能方面的问题，需要进行全面优化。

## 术语表

- **System**: 回测引擎系统，包括策略引擎和回测引擎
- **Grid_Strategy_Engine**: 网格策略引擎，负责执行网格交易逻辑
- **Backtest_Engine**: 回测引擎，负责历史数据回测和性能指标计算
- **Grid_Order**: 网格订单，表示在特定价格网格上的买入或卖出订单
- **Position**: 仓位，表示持有的合约数量（正数为多仓，负数为空仓）
- **Margin**: 保证金，开仓所需的资金（合约价值/杠杆倍数）
- **Unrealized_PnL**: 未实现盈亏，未平仓头寸的浮动盈亏
- **Grid_Profit**: 网格收益，已配对交易的实现收益
- **Funding_Fee**: 资金费率，永续合约的持仓费用
- **Equity**: 权益，当前资金 + 未实现盈亏
- **Drawdown**: 回撤，从峰值到谷值的权益下降幅度

## 需求

### 需求 1：网格订单初始化和执行

**用户故事：** 作为交易者，我希望网格订单能够正确初始化和执行，以便系统能够准确模拟网格交易策略。

#### 验收标准

1. WHEN 系统初始化网格时，THE Grid_Strategy_Engine SHALL 根据策略模式（做多/做空/中性）在正确的价格网格上放置初始订单
2. WHEN 市场价格触及网格订单价格时，THE Grid_Strategy_Engine SHALL 执行订单并更新仓位
3. WHEN 订单成交后，THE Grid_Strategy_Engine SHALL 在相应的对手网格上放置新订单
4. WHEN 做多网格买单成交时，THE Grid_Strategy_Engine SHALL 在上一网格放置卖单
5. WHEN 做空网格卖单成交时，THE Grid_Strategy_Engine SHALL 在下一网格放置买单
6. WHEN 中性网格订单成交时，THE Grid_Strategy_Engine SHALL 在对手网格放置平仓订单

### 需求 2：保证金和资金管理

**用户故事：** 作为交易者，我希望系统能够准确计算和管理保证金，以便真实反映杠杆交易的资金使用情况。

#### 验收标准

1. WHEN 开仓时，THE Grid_Strategy_Engine SHALL 计算所需保证金为（合约价值 / 杠杆倍数）
2. WHEN 保证金不足时，THE Grid_Strategy_Engine SHALL 拒绝开仓并保持当前状态
3. WHEN 平仓时，THE Grid_Strategy_Engine SHALL 释放对应的保证金
4. WHEN 计算可用资金时，THE Grid_Strategy_Engine SHALL 返回（总资金 - 已用保证金）
5. THE Grid_Strategy_Engine SHALL 在任何时刻保持（已用保证金 <= 总资金）的不变式
6. WHEN 订单成交时，THE Grid_Strategy_Engine SHALL 先扣除手续费，再检查保证金是否充足

### 需求 3：盈亏计算

**用户故事：** 作为交易者，我希望系统能够准确计算已实现和未实现盈亏，以便了解策略的真实表现。

#### 验收标准

1. WHEN 平仓时，THE Grid_Strategy_Engine SHALL 计算已实现盈亏为（平仓价格 - 开仓价格）× 数量（做多）或（开仓价格 - 平仓价格）× 数量（做空）
2. WHEN 计算未实现盈亏时，THE Grid_Strategy_Engine SHALL 对所有未平仓头寸计算（当前价格 - 开仓价格）× 数量
3. WHEN 计算权益时，THE Grid_Strategy_Engine SHALL 返回（当前资金 + 未实现盈亏）
4. THE Grid_Strategy_Engine SHALL 将已实现盈亏累加到网格收益（Grid_Profit）中
5. WHEN 订单配对成交时，THE Grid_Strategy_Engine SHALL 将盈亏立即加入当前资金
6. THE Grid_Strategy_Engine SHALL 确保（最终资金 = 初始资金 + 已实现盈亏 - 手续费 - 资金费率）

### 需求 4：订单配对逻辑

**用户故事：** 作为开发者，我希望订单配对逻辑清晰准确，以便正确追踪仓位和计算盈亏。

#### 验收标准

1. WHEN 做多网格卖单成交时，THE Grid_Strategy_Engine SHALL 查找下一网格的多仓并配对平仓
2. WHEN 做空网格买单成交时，THE Grid_Strategy_Engine SHALL 查找上一网格的空仓并配对平仓
3. WHEN 中性网格订单成交时，THE Grid_Strategy_Engine SHALL 查找对手网格的反向仓位并配对平仓
4. WHEN 无法找到配对仓位时，THE Grid_Strategy_Engine SHALL 将订单视为开仓
5. THE Grid_Strategy_Engine SHALL 为每个网格维护独立的仓位记录
6. WHEN 仓位完全平仓时，THE Grid_Strategy_Engine SHALL 从仓位记录中移除该网格

### 需求 5：资金费率处理

**用户故事：** 作为交易者，我希望系统能够准确计算资金费率，以便真实反映永续合约的持仓成本。

#### 验收标准

1. WHEN 持有仓位且达到资金费率结算时间时，THE Grid_Strategy_Engine SHALL 计算资金费用为（仓位价值 × 资金费率）
2. WHEN 资金费率为正且持有多仓时，THE Grid_Strategy_Engine SHALL 从资金中扣除资金费用
3. WHEN 资金费率为正且持有空仓时，THE Grid_Strategy_Engine SHALL 向资金中增加资金费用
4. THE Grid_Strategy_Engine SHALL 按照配置的资金费率间隔（默认8小时）结算资金费用
5. THE Grid_Strategy_Engine SHALL 累计所有资金费用到总资金费用（Total_Funding_Fees）中
6. WHEN 仓位为零时，THE Grid_Strategy_Engine SHALL 不计算资金费用

### 需求 6：性能指标计算

**用户故事：** 作为交易者，我希望系统能够准确计算各项性能指标，以便评估策略表现。

#### 验收标准

1. WHEN 计算总收益率时，THE Backtest_Engine SHALL 返回（最终资金 - 初始资金）/ 初始资金
2. WHEN 计算年化收益率时，THE Backtest_Engine SHALL 返回（(1 + 总收益率) ^ (365 / 天数) - 1）
3. WHEN 计算最大回撤时，THE Backtest_Engine SHALL 追踪权益曲线的峰值，并计算（峰值 - 当前值）/ 峰值的最大值
4. WHEN 计算夏普比率时，THE Backtest_Engine SHALL 使用日收益率的均值除以标准差，再乘以 sqrt(252)
5. WHEN 计算胜率时，THE Backtest_Engine SHALL 返回盈利交易数 / 总交易数
6. THE Backtest_Engine SHALL 在每个K线处理后更新权益曲线

### 需求 7：代码结构优化

**用户故事：** 作为开发者，我希望代码结构清晰、模块化，以便于维护和扩展。

#### 验收标准

1. THE System SHALL 将订单管理逻辑封装在独立的 Order_Manager 类中
2. THE System SHALL 将仓位管理逻辑封装在独立的 Position_Manager 类中
3. THE System SHALL 将保证金计算逻辑封装在独立的 Margin_Calculator 类中
4. THE System SHALL 将盈亏计算逻辑封装在独立的 PnL_Calculator 类中
5. THE System SHALL 确保每个类的职责单一且明确
6. THE System SHALL 使用依赖注入模式，使各组件可独立测试

### 需求 8：测试覆盖

**用户故事：** 作为开发者，我希望系统具有全面的测试覆盖，以便确保代码质量和正确性。

#### 验收标准

1. THE System SHALL 为所有核心算法提供基于属性的测试（Property-Based Tests）
2. THE System SHALL 为边界条件和错误情况提供单元测试
3. THE System SHALL 为订单配对逻辑提供往返属性测试（Round-trip Property）
4. THE System SHALL 为保证金管理提供不变式测试（Invariant Property）
5. THE System SHALL 为盈亏计算提供守恒定律测试（Conservation Property）
6. THE System SHALL 确保所有属性测试至少运行100次迭代
