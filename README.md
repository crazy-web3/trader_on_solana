# 合约网格交易系统

一个基于Python Flask和Vue.js的网格交易策略回测系统，支持做多、做空、中性三种网格交易策略的历史数据回测和参数优化。

## 🏗️ 项目结构

```
trader_on_solana/
├── backend/                # 后端服务 (Python Flask)
│   ├── api/               # API路由模块
│   ├── backtest_engine/   # 回测引擎
│   ├── strategy_engine/   # 策略引擎
│   ├── market_data_layer/ # 市场数据层
│   ├── wallet_auth/       # 钱包认证
│   ├── utils/            # 工具函数
│   ├── tests/            # 测试文件
│   ├── app.py            # 主应用入口
│   └── requirements.txt  # Python依赖
├── frontend/              # 前端应用 (Vue.js)
│   ├── src/              # 源代码
│   ├── public/           # 静态资源
│   ├── package.json      # 项目配置
│   └── vite.config.js    # 构建配置
├── docs_zh/              # 中文文档
│   ├── 合约网格交易说明文档.md
│   ├── API_ENDPOINTS.md
│   ├── QUICKSTART_OPTIMIZED.md
│   └── ...
├── docs/                 # 英文文档 (原有)
├── archive/              # 归档文件
└── README.md            # 项目说明 (本文件)
```

## 🚀 快速启动

### 1. 启动后端服务
```bash
cd backend
pip install -r requirements.txt
python app.py
```
后端服务将运行在: http://localhost:5001

### 2. 启动前端应用
```bash
cd frontend
npm install
npm run dev
```
前端应用将运行在: http://localhost:3001

### 3. 访问服务
- **前端界面**: http://localhost:3001
- **后端API**: http://localhost:5001
- **API文档**: http://localhost:5001/docs/
- **Swagger JSON**: http://localhost:5001/swagger.json

## 📋 主要功能

### 🤖 网格交易策略
- **做多网格**: 适合上涨趋势市场
- **做空网格**: 适合下跌趋势市场  
- **中性网格**: 适合震荡市场

### 📊 回测分析
- 历史数据回测
- 多策略对比分析
- 参数优化搜索
- 详细性能指标

### 🔐 钱包认证
- Web3钱包连接
- 签名验证
- 白名单权限控制

### 📈 数据支持
- 币安K线数据
- 多时间周期
- 智能缓存机制

## 🛠️ 技术栈

### 后端
- **框架**: Python Flask
- **数据**: 币安API
- **认证**: Web3钱包签名
- **文档**: Swagger/OpenAPI

### 前端  
- **框架**: Vue.js 3
- **构建**: Vite
- **图表**: Chart.js
- **样式**: CSS3

## 📚 文档

详细文档请查看 [docs_zh/](./docs_zh/) 目录：

- [快速启动指南](./docs_zh/QUICKSTART_OPTIMIZED.md)
- [API接口文档](./docs_zh/API_ENDPOINTS.md)
- [网格交易策略说明](./docs_zh/合约网格交易说明文档.md)
- [Swagger集成说明](./docs_zh/SWAGGER_INTEGRATION_SUMMARY.md)

## 🔧 开发

### 后端开发
```bash
cd backend
# 安装依赖
pip install -r requirements.txt
# 运行测试
python -m pytest tests/
# 启动服务
python app.py
```

### 前端开发
```bash
cd frontend
# 安装依赖
npm install
# 开发模式
npm run dev
# 构建生产版本
npm run build
```

## 📊 API接口

系统提供完整的RESTful API接口：

- **认证接口**: 钱包登录、令牌验证
- **市场数据**: K线数据、交易对查询
- **策略回测**: 单策略回测、参数计算
- **回测引擎**: 综合回测、参数优化

详细API文档: http://localhost:5001/docs/

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

## 📄 许可证

MIT License