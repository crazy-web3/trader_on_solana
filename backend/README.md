# 合约网格交易系统 - 后端服务

## 📁 项目结构

```
backend/
├── api/                    # API路由模块
│   ├── auth_routes.py     # 认证相关路由
│   ├── market_routes.py   # 市场数据路由
│   ├── strategy_routes.py # 策略回测路由
│   └── backtest_routes.py # 回测引擎路由
├── backtest_engine/       # 回测引擎模块
├── strategy_engine/       # 策略引擎模块
├── market_data_layer/     # 市场数据层
├── wallet_auth/          # 钱包认证模块
├── utils/                # 工具函数
├── tests/                # 测试文件
├── app.py               # 主应用入口
├── requirements.txt     # Python依赖
├── swagger_config.py    # Swagger配置
└── *.json              # 配置文件
```

## 🚀 快速启动

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动服务
```bash
python app.py
```

### 3. 访问服务
- **API服务**: http://localhost:5001
- **健康检查**: http://localhost:5001/api/health
- **API文档**: http://localhost:5001/docs/
- **Swagger JSON**: http://localhost:5001/swagger.json

## 📋 API接口

### 认证接口 (`/api/auth`)
- `POST /api/auth/challenge` - 获取认证挑战消息
- `POST /api/auth/login` - 钱包登录认证
- `GET /api/auth/verify` - 验证认证令牌
- `GET /api/auth/whitelist` - 获取白名单用户列表
- `POST /api/auth/logout` - 用户登出

### 市场数据接口 (`/api`)
- `GET /api/symbols` - 获取支持的交易对列表
- `GET /api/intervals` - 获取支持的时间间隔列表
- `GET /api/klines` - 获取K线数据
- `GET /api/cache/stats` - 获取缓存统计信息
- `POST /api/cache/clear` - 清空缓存

### 策略回测接口 (`/api/strategy`)
- `POST /api/strategy/calculate-from-range` - 根据选定时间区间计算策略参数
- `POST /api/strategy/price-range` - 获取交易对的价格区间和网格数量计算
- `POST /api/strategy/backtest` - 执行网格交易策略回测

### 回测引擎接口 (`/api/backtest`)
- `POST /api/backtest/run` - 运行综合回测分析
- `POST /api/backtest/grid-search` - 运行网格搜索优化（需要认证）

## 🔧 开发说明

### 环境要求
- Python 3.8+
- Flask 2.0+
- 其他依赖见 requirements.txt

### 配置文件
- `wallet_whitelist.json` - 钱包白名单配置
- `openapi_manual.json` - OpenAPI规范文件
- `swagger_config.py` - Swagger文档配置

### 测试
```bash
cd backend
python -m pytest tests/
```