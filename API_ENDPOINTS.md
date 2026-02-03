# 后端 API 接口文档

## 基础信息
- **基础URL**: http://localhost:5001
- **内容类型**: application/json
- **认证方式**: Bearer Token (部分接口需要)

## 接口列表

### 1. 健康检查

#### GET /api/health
检查服务器状态

**请求**：
```http
GET /api/health
```

**响应**：
```json
{
  "status": "ok",
  "timestamp": "2026-02-02T18:15:00.000Z"
}
```

---

### 2. 钱包认证接口

#### POST /api/auth/challenge
获取钱包签名挑战消息

**请求**：
```json
{
  "publicKey": "wallet_public_key_here"
}
```

**响应**：
```json
{
  "challenge": "challenge_message_to_sign",
  "timestamp": 1706889300000
}
```

#### POST /api/auth/login
钱包登录认证

**请求**：
```json
{
  "publicKey": "wallet_public_key_here",
  "signature": "signed_challenge_message",
  "challenge": "original_challenge_message"
}
```

**响应**：
```json
{
  "token": "jwt_token_here",
  "publicKey": "wallet_public_key_here",
  "expiresIn": 86400
}
```

#### POST /api/auth/logout
钱包登出 🔒

**请求头**：
```
Authorization: Bearer <token>
```

**响应**：
```json
{
  "message": "Logged out successfully"
}
```

#### GET /api/auth/verify
验证认证状态 🔒

**请求头**：
```
Authorization: Bearer <token>
```

**响应**：
```json
{
  "valid": true,
  "publicKey": "wallet_public_key_here"
}
```

#### GET /api/auth/whitelist
获取白名单信息 🔒

**请求头**：
```
Authorization: Bearer <token>
```

**响应**：
```json
{
  "whitelist": [
    {
      "address": "wallet_address",
      "nickname": "User Name",
      "role": "user",
      "created_at": "2026-02-02T10:00:00Z"
    }
  ]
}
```

---

### 3. 市场数据接口

#### GET /api/symbols
获取支持的交易对

**请求**：
```http
GET /api/symbols
```

**响应**：
```json
{
  "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
}
```

#### GET /api/intervals
获取支持的时间间隔

**请求**：
```http
GET /api/intervals
```

**响应**：
```json
{
  "intervals": ["15m", "1h", "4h", "1d"]
}
```

#### GET /api/klines
获取K线数据

**请求参数**：
- `symbol` (必需): 交易对，如 "BTCUSDT"
- `interval` (必需): 时间间隔，如 "1d"
- `start_time` (可选): 开始时间戳（毫秒）
- `end_time` (可选): 结束时间戳（毫秒）
- `limit` (可选): 数据条数限制，默认500

**请求**：
```http
GET /api/klines?symbol=BTCUSDT&interval=1d&limit=100
```

**响应**：
```json
{
  "symbol": "BTCUSDT",
  "interval": "1d",
  "data": [
    {
      "timestamp": 1706889300000,
      "open": 42000.0,
      "high": 43000.0,
      "low": 41000.0,
      "close": 42500.0,
      "volume": 1234.56
    }
  ]
}
```

---

### 4. 缓存管理接口

#### GET /api/cache/stats
获取缓存统计信息

**请求**：
```http
GET /api/cache/stats
```

**响应**：
```json
{
  "size": 150,
  "max_size": 1000,
  "hit_rate": 0.85,
  "total_requests": 1000,
  "cache_hits": 850
}
```

#### POST /api/cache/clear
清空缓存

**请求**：
```http
POST /api/cache/clear
```

**响应**：
```json
{
  "message": "Cache cleared successfully",
  "cleared_items": 150
}
```

---

### 5. 策略计算接口

#### POST /api/strategy/calculate-from-range
根据时间范围计算策略参数

**请求**：
```json
{
  "symbol": "BTCUSDT",
  "interval": "1d",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "volatility_factor": 1.5,
  "grid_density": "medium"
}
```

**响应**：
```json
{
  "symbol": "BTCUSDT",
  "price_range": {
    "lower": 25000.0,
    "upper": 65000.0,
    "current": 42500.0
  },
  "suggested_grids": 20,
  "volatility": 0.65,
  "recommended_capital": 10000
}
```

#### POST /api/strategy/price-range
获取价格范围和网格数建议

**请求**：
```json
{
  "symbol": "BTCUSDT",
  "days": 365,
  "volatility_multiplier": 1.2
}
```

**响应**：
```json
{
  "symbol": "BTCUSDT",
  "current_price": 42500.0,
  "price_range": {
    "lower": 30000.0,
    "upper": 55000.0
  },
  "suggested_grid_count": 25,
  "volatility": 0.58
}
```

---

### 6. 回测接口

#### POST /api/strategy/backtest
单策略回测

**请求**：
```json
{
  "symbol": "BTCUSDT",
  "mode": "long",
  "lower_price": 40000,
  "upper_price": 50000,
  "grid_count": 20,
  "initial_capital": 10000,
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "fee_rate": 0.0005,
  "leverage": 2.0,
  "funding_rate": 0.0001,
  "funding_interval": 8
}
```

**响应**：
```json
{
  "config": {
    "symbol": "BTCUSDT",
    "mode": "long",
    "lower_price": 40000,
    "upper_price": 50000,
    "grid_count": 20,
    "initial_capital": 10000,
    "leverage": 2.0
  },
  "metrics": {
    "total_return": 0.15,
    "annual_return": 0.12,
    "max_drawdown": 0.08,
    "sharpe_ratio": 1.25,
    "win_rate": 0.65,
    "total_trades": 156,
    "winning_trades": 101,
    "losing_trades": 55,
    "fee_cost": 125.50,
    "fee_ratio": 0.01255
  },
  "initial_capital": 10000,
  "final_capital": 11500,
  "equity_curve": [10000, 10050, 10100, ...],
  "timestamps": [1672531200000, 1672617600000, ...],
  "trades": [
    {
      "timestamp": 1672531200000,
      "price": 41000,
      "quantity": 0.5,
      "side": "buy",
      "fee": 10.25,
      "pnl": 0,
      "grid_level": 5
    }
  ]
}
```

#### POST /api/backtest/run
综合回测（对比三种策略）

**请求**：
```json
{
  "symbol": "BTCUSDT",
  "lower_price": 40000,
  "upper_price": 50000,
  "grid_count": 20,
  "initial_capital": 10000,
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "fee_rate": 0.0005,
  "leverage": 2.0
}
```

**响应**：
```json
{
  "long_result": { /* 做多网格结果 */ },
  "short_result": { /* 做空网格结果 */ },
  "neutral_result": { /* 中性网格结果 */ },
  "comparison": {
    "best_strategy": "long",
    "performance_ranking": ["long", "neutral", "short"]
  }
}
```

#### POST /api/backtest/grid-search
网格搜索优化 🔒

**请求头**：
```
Authorization: Bearer <token>
```

**请求**：
```json
{
  "symbol": "BTCUSDT",
  "mode": "long",
  "base_config": {
    "lower_price": 40000,
    "upper_price": 50000,
    "initial_capital": 10000,
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  },
  "search_params": {
    "grid_count": [10, 15, 20, 25, 30],
    "leverage": [1, 2, 3, 5]
  }
}
```

**响应**：
```json
{
  "best_result": { /* 最优结果 */ },
  "best_params": {
    "grid_count": 20,
    "leverage": 2
  },
  "all_results": [
    {
      "params": {"grid_count": 10, "leverage": 1},
      "metrics": { /* 性能指标 */ }
    }
  ],
  "optimization_summary": {
    "total_combinations": 20,
    "best_return": 0.18,
    "optimization_time": 15.2
  }
}
```

---

## 错误响应格式

所有接口在出错时返回统一格式：

```json
{
  "error": "错误描述信息",
  "code": "ERROR_CODE",
  "details": "详细错误信息（可选）"
}
```

**常见错误码**：
- `400`: 请求参数错误
- `401`: 未认证或认证失败
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

---

## 使用示例

### JavaScript/Axios
```javascript
// 获取K线数据
const response = await axios.get('/api/klines', {
  params: {
    symbol: 'BTCUSDT',
    interval: '1d',
    limit: 100
  }
});

// 运行回测
const backtestResult = await axios.post('/api/strategy/backtest', {
  symbol: 'BTCUSDT',
  mode: 'long',
  lower_price: 40000,
  upper_price: 50000,
  grid_count: 20,
  initial_capital: 10000,
  start_date: '2023-01-01',
  end_date: '2023-12-31'
});
```

### Python/Requests
```python
import requests

# 获取K线数据
response = requests.get('http://localhost:5001/api/klines', params={
    'symbol': 'BTCUSDT',
    'interval': '1d',
    'limit': 100
})

# 运行回测
backtest_data = {
    'symbol': 'BTCUSDT',
    'mode': 'long',
    'lower_price': 40000,
    'upper_price': 50000,
    'grid_count': 20,
    'initial_capital': 10000,
    'start_date': '2023-01-01',
    'end_date': '2023-12-31'
}
response = requests.post('http://localhost:5001/api/strategy/backtest', json=backtest_data)
```

---

## 接口统计

| 类别 | 接口数量 | 需要认证 |
|------|----------|----------|
| 健康检查 | 1 | ❌ |
| 钱包认证 | 5 | 3个需要 🔒 |
| 市场数据 | 3 | ❌ |
| 缓存管理 | 2 | ❌ |
| 策略计算 | 2 | ❌ |
| 回测功能 | 3 | 1个需要 🔒 |
| **总计** | **16** | **4个需要认证** |

**图例**：
- 🔒 = 需要钱包认证
- ❌ = 无需认证

---

**最后更新**: 2026-02-02  
**API版本**: v1.0  
**服务地址**: http://localhost:5001