# 行情数据层设计文档

## 概述

行情数据层是一个分层架构的数据管理系统，负责从外部数据源获取K线数据，进行验证和缓存，最后提供统一的接口供上层应用使用。系统采用分层设计，包括数据源层、缓存层、验证层和API层。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    应用层 (API)                          │
│              MarketDataService                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  验证层 (Validator)                      │
│            KlineDataValidator                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  缓存层 (Cache)                          │
│         CacheManager (LRU + TTL)                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                数据源层 (Data Source)                    │
│    DataSourceAdapter (API/Database)                     │
└─────────────────────────────────────────────────────────┘
```

## 组件和接口

### 1. MarketDataService (主服务)

**职责**: 提供统一的K线数据查询接口，协调各层组件

**接口**:
```
getKlineData(symbol: string, interval: string, startTime: number, endTime: number): Promise<KlineData[]>
getSupportedSymbols(): Promise<string[]>
getSupportedIntervals(): Promise<string[]>
```

### 2. CacheManager (缓存管理器)

**职责**: 管理K线数据的本地缓存，实现LRU淘汰和TTL过期策略

**接口**:
```
get(key: string): KlineData[] | null
set(key: string, value: KlineData[], ttl: number): void
delete(key: string): void
clear(): void
```

**缓存键格式**: `{symbol}:{interval}:{startTime}:{endTime}`

### 3. KlineDataValidator (数据验证器)

**职责**: 验证K线数据的完整性和有效性

**接口**:
```
validate(data: KlineData): ValidationResult
validateBatch(data: KlineData[]): ValidationResult[]
```

**验证规则**:
- high >= low >= 0
- open, high, low, close 在合理范围内
- volume >= 0
- timestamp 是有效的Unix时间戳

### 4. DataSourceAdapter (数据源适配器)

**职责**: 从外部数据源获取K线数据，处理网络请求和错误

**接口**:
```
fetchKlineData(symbol: string, interval: string, startTime: number, endTime: number): Promise<KlineData[]>
```

## 数据模型

### KlineData (K线数据)

```typescript
interface KlineData {
  timestamp: number;      // Unix时间戳（毫秒）
  open: number;          // 开盘价
  high: number;          // 最高价
  low: number;           // 最低价
  close: number;         // 收盘价
  volume: number;        // 成交量
}
```

### CacheEntry (缓存条目)

```typescript
interface CacheEntry {
  data: KlineData[];
  createdAt: number;     // 创建时间戳
  ttl: number;           // 生存时间（毫秒）
  accessCount: number;   // 访问次数（用于LRU）
  lastAccessTime: number; // 最后访问时间
}
```

### ValidationResult (验证结果)

```typescript
interface ValidationResult {
  isValid: boolean;
  errors: string[];
}
```

### TimeInterval (时间周期)

```typescript
enum TimeInterval {
  ONE_MINUTE = "1m",
  FIVE_MINUTES = "5m",
  FIFTEEN_MINUTES = "15m",
  ONE_HOUR = "1h",
  FOUR_HOURS = "4h",
  ONE_DAY = "1d",
  ONE_WEEK = "1w"
}
```

## 错误处理

### 错误类型

1. **DataSourceError**: 数据源连接或请求失败
2. **ValidationError**: 数据验证失败
3. **ParameterError**: 请求参数无效
4. **TimeoutError**: 请求超时
5. **CacheError**: 缓存操作失败

### 错误处理流程

```
请求 → 参数验证 → 缓存查询 → 数据源请求 → 数据验证 → 缓存存储 → 返回结果
                                    ↓
                            错误处理和日志记录
```

## 缓存策略

### 缓存配置

- **最大缓存条目数**: 1000
- **单条目TTL**: 24小时
- **淘汰策略**: LRU (最近最少使用)
- **缓存键**: `{symbol}:{interval}:{startTime}:{endTime}`

### 缓存流程

1. 请求到达时，先检查缓存
2. 缓存命中且未过期，直接返回
3. 缓存未命中或已过期，从数据源获取
4. 验证数据后存入缓存
5. 返回数据给调用者

## 性能优化

### 并发处理

- 使用连接池管理数据源连接
- 支持并发请求处理
- 实现请求去重（相同请求合并）

### 响应时间目标

- 缓存命中: < 100ms
- 单个请求: < 500ms
- 1000条数据: < 1s
- 100并发: 支持

### 优化措施

1. 缓存热数据（常用币种和周期）
2. 批量请求优化
3. 连接复用
4. 异步处理

## 正确性属性

属性是一种特征或行为，应该在系统的所有有效执行中保持真实——本质上是关于系统应该做什么的正式陈述。属性充当人类可读规范和机器可验证正确性保证之间的桥梁。

### 属性定义

**属性 1: 返回数据包含所有必需字段**

*对于任何* K线数据查询请求，返回的每个K线对象都应该包含timestamp、open、high、low、close、volume这六个字段。

**验证: 需求 1.4**

**属性 2: K线数据按时间戳升序排列**

*对于任何* K线数据查询请求，返回的数据列表应该按时间戳升序排列。

**验证: 需求 1.2**

**属性 3: 支持的时间周期返回数据**

*对于任何* 支持的时间周期（1m、5m、15m、1h、4h、1d、1w），系统应该能够返回该周期的K线数据。

**验证: 需求 2.1**

**属性 4: 支持的币种返回数据**

*对于任何* 支持的币种（BTC/USDT、ETH/USDT、BNB/USDT、SOL/USDT），系统应该能够返回该币种的K线数据。

**验证: 需求 3.1**

**属性 5: 数据缓存后可被检索**

*对于任何* 成功获取的K线数据，将其缓存后，使用相同的查询参数再次请求应该返回相同的数据。

**验证: 需求 4.1**

**属性 6: 缓存命中返回相同数据**

*对于任何* 已缓存的K线数据，第二次请求应该返回与第一次相同的数据，而不是重新从数据源获取。

**验证: 需求 4.2**

**属性 7: 缓存过期后更新**

*对于任何* 缓存条目，当其生存时间（TTL）超过24小时后，下一次请求应该从数据源重新获取数据而不是返回过期的缓存。

**验证: 需求 4.3**

**属性 8: LRU淘汰策略**

*对于任何* 缓存容量达到限制的情况，添加新数据时应该删除最久未使用的条目，而不是删除最近使用的条目。

**验证: 需求 4.4**

**属性 9: 无效参数返回验证错误**

*对于任何* 无效的请求参数（如不支持的币种、不支持的周期、无效的时间范围），系统应该返回参数验证错误而不是其他错误。

**验证: 需求 5.2**

**属性 10: 无效数据被拒绝**

*对于任何* 从数据源返回的无效K线数据（如high < low、volume < 0、价格为负数），系统应该拒绝该数据并不将其返回给调用者。

**验证: 需求 5.3**

**属性 11: 价格关系验证 (high >= low >= 0)**

*对于任何* 接收的K线数据，high应该大于等于low，low应该大于等于0。

**验证: 需求 7.1**

**属性 12: 价格范围验证**

*对于任何* 接收的K线数据，open、high、low、close都应该在合理的价格范围内（> 0且 < 某个最大值）。

**验证: 需求 7.2**

**属性 13: 成交量非负验证**

*对于任何* 接收的K线数据，volume应该大于等于0。

**验证: 需求 7.3**

## 测试策略

### 单元测试

- 数据验证器的验证规则测试（属性 11、12、13）
- 缓存管理器的LRU和TTL逻辑测试（属性 7、8）
- 参数验证测试（属性 9）
- 错误处理测试（特定错误场景）
- 数据结构测试（属性 1）

### 属性测试

使用属性测试库（如 fast-check for TypeScript/JavaScript、Hypothesis for Python）来验证以下属性：

- **属性 1**: 验证返回数据的结构完整性
- **属性 2**: 验证数据排序正确性
- **属性 3**: 验证所有支持的时间周期都能返回数据
- **属性 4**: 验证所有支持的币种都能返回数据
- **属性 5**: 验证缓存存储和检索的一致性
- **属性 6**: 验证缓存命中返回相同数据（往返属性）
- **属性 7**: 验证缓存TTL过期机制
- **属性 8**: 验证LRU淘汰策略
- **属性 9**: 验证参数验证的完整性
- **属性 10**: 验证数据验证的完整性
- **属性 11-13**: 验证数据验证规则

**属性测试配置**:
- 每个属性测试最少运行100次迭代
- 使用随机生成的输入数据
- 标签格式: **Feature: market-data-layer, Property N: [属性标题]**

### 集成测试

- 完整的数据获取流程测试
- 缓存和数据源的交互测试
- 错误恢复测试
- 边界情况测试（空数据、大数据量等）
