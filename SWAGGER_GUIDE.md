# Swagger API文档使用指南

## 📋 概述

合约网格交易系统已集成Swagger API文档，支持导入到Apifox、Postman等API客户端工具进行接口测试和调试。

## 🌐 访问方式

### 在线访问
- **Swagger UI**: http://localhost:5001/docs/
- **OpenAPI JSON**: http://localhost:5001/api/swagger.json
- **健康检查**: http://localhost:5001/api/health

### 本地文件
- **手动OpenAPI规范**: `openapi_manual.json`（推荐使用）
- **自动生成规范**: `openapi.json`

## 🔧 导入到API客户端工具

### 1. Apifox 导入步骤

1. **打开Apifox**，创建新项目或选择现有项目

2. **导入API文档**：
   - 点击"导入数据"
   - 选择"OpenAPI/Swagger"
   - 选择导入方式：
     - **URL导入**：输入 `http://localhost:5001/api/swagger.json`
     - **文件导入**：选择 `openapi_manual.json` 文件

3. **配置环境**：
   - 添加环境变量：`base_url = http://localhost:5001`
   - 设置认证方式：Bearer Token

4. **测试接口**：
   - 先调用 `/api/auth/challenge` 获取挑战消息
   - 再调用 `/api/auth/login` 获取JWT令牌
   - 在其他接口中使用Bearer Token认证

### 2. Postman 导入步骤

1. **打开Postman**，创建新的Collection

2. **导入API文档**：
   - 点击"Import"
   - 选择"Link"或"File"
   - **URL导入**：输入 `http://localhost:5001/api/swagger.json`
   - **文件导入**：选择 `openapi_manual.json` 文件

3. **配置环境**：
   - 创建Environment，添加变量：
     - `baseUrl`: `http://localhost:5001`
     - `token`: `{{token}}`（用于存储JWT令牌）

4. **设置认证**：
   - 在Collection级别设置Authorization
   - 类型选择"Bearer Token"
   - Token值使用 `{{token}}`

### 3. Insomnia 导入步骤

1. **打开Insomnia**，创建新的Workspace

2. **导入API文档**：
   - 点击"Create" → "Import From"
   - 选择"URL"或"File"
   - 输入URL或选择文件

3. **配置Base Environment**：
   - 添加 `base_url`: `http://localhost:5001`

## 📚 API接口分类

### 🔐 认证接口 (`/api/auth/`)
- `POST /api/auth/challenge` - 获取钱包签名挑战消息
- `POST /api/auth/login` - 钱包登录认证
- `POST /api/auth/logout` - 钱包登出
- `GET /api/auth/verify` - 验证认证状态
- `GET /api/auth/whitelist` - 获取白名单信息（管理员）

### 📊 市场数据接口 (`/api/`)
- `GET /api/symbols` - 获取支持的交易对
- `GET /api/intervals` - 获取支持的时间间隔
- `GET /api/klines` - 获取K线数据
- `GET /api/cache/stats` - 获取缓存统计
- `POST /api/cache/clear` - 清空缓存

### 🤖 策略回测接口 (`/api/strategy/`)
- `POST /api/strategy/calculate-from-range` - 根据时间区间计算策略参数
- `POST /api/strategy/price-range` - 计算价格区间和网格数量
- `POST /api/strategy/backtest` - 执行单策略回测

### 🔍 回测引擎接口 (`/api/backtest/`)
- `POST /api/backtest/run` - 运行综合回测分析
- `POST /api/backtest/grid-search` - 网格搜索优化（需认证）

## 🔑 认证流程

### 1. 获取挑战消息
```http
POST /api/auth/challenge
Content-Type: application/json

{
  "public_key": "0x1234567890abcdef..."
}
```

### 2. 登录获取令牌
```http
POST /api/auth/login
Content-Type: application/json

{
  "public_key": "0x1234567890abcdef...",
  "message": "Please sign this message to authenticate: 1706889300",
  "signature": "0xabcdef1234567890..."
}
```

### 3. 使用令牌访问受保护接口
```http
GET /api/auth/verify
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 📝 使用示例

### 示例1：获取K线数据
```http
GET /api/klines?symbol=BTCUSDT&interval=1h&limit=100
```

### 示例2：执行策略回测
```http
POST /api/strategy/backtest
Content-Type: application/json

{
  "symbol": "BTCUSDT",
  "mode": "long",
  "initial_capital": 10000,
  "days": 30,
  "auto_calculate_range": true
}
```

### 示例3：综合回测分析
```http
POST /api/backtest/run
Content-Type: application/json

{
  "symbol": "ETHUSDT",
  "initial_capital": 10000,
  "days": 30,
  "auto_calculate_range": true
}
```

## ⚠️ 注意事项

1. **服务器启动**：确保后端服务已启动（`python app.py`）
2. **CORS配置**：已配置允许跨域访问，支持前端调用
3. **认证要求**：大部分接口需要JWT令牌认证
4. **参数验证**：请按照API文档提供正确的参数类型和范围
5. **错误处理**：注意查看HTTP状态码和错误信息

## 🚀 快速开始

1. **启动后端服务**：
   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **访问Swagger UI**：
   打开浏览器访问 http://localhost:5001/docs/

3. **导入到API工具**：
   使用 `openapi_manual.json` 文件导入到你喜欢的API客户端工具

4. **开始测试**：
   从健康检查接口开始，逐步测试各个功能模块

## 📞 技术支持

如果在使用过程中遇到问题，请检查：
- 后端服务是否正常启动
- 网络连接是否正常
- API参数是否正确
- 认证令牌是否有效

---

**文档版本**: 1.0.0  
**更新时间**: 2026年2月3日  
**维护团队**: 合约网格交易系统开发团队