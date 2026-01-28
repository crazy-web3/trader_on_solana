# 🚀 交易系统前端 - Trading Dashboard Frontend

独立部署的前端应用，支持行情数据查看、策略回测、完整回测和参数优化。

## 📋 功能特性

- ✅ **行情数据** - 实时K线数据查看与分析
- ✅ **策略回测** - 快速策略回测 (最近7-365天)
- ✅ **完整回测** - 历史数据回测 (最近3年)
- ✅ **参数优化** - Grid Search 参数优化
- ✅ **响应式设计** - 支持桌面和移动设备
- ✅ **深色主题** - 专业的深色UI设计

## 🛠️ 技术栈

- **Vue 3** - 前端框架
- **Vite** - 构建工具
- **Chart.js** - 图表库
- **Lightweight Charts** - K线图表
- **Axios** - HTTP 客户端

## 📦 安装

### 前置要求
- Node.js 16+
- npm 或 yarn

### 安装依赖
```bash
cd frontend
npm install
```

## 🚀 开发

### 启动开发服务器
```bash
npm run dev
```

访问 `http://localhost:3000`

### 构建生产版本
```bash
npm run build
```

输出目录: `frontend/dist`

## 🌐 部署

### 方式1: 使用 Node.js 服务器

```bash
# 构建
npm run build

# 启动服务器
npm run serve
```

服务器运行在 `http://localhost:3000`

### 方式2: 使用 Nginx

```nginx
server {
    listen 3000;
    server_name localhost;

    root /path/to/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 方式3: 使用 Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "serve"]
```

构建和运行:
```bash
docker build -t trading-dashboard .
docker run -p 3000:3000 -e API_URL=http://localhost:5001 trading-dashboard
```

### 方式4: 使用 Vercel/Netlify

1. 推送代码到 GitHub
2. 连接 Vercel/Netlify
3. 设置构建命令: `npm run build`
4. 设置输出目录: `dist`
5. 设置环境变量: `VITE_API_URL=http://your-api-url`

## 🔧 配置

### 环境变量

创建 `.env` 文件:

```env
VITE_API_URL=http://localhost:5001
VITE_API_TIMEOUT=30000
```

### API 配置

在 `vite.config.js` 中配置 API 代理:

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:5001',
    changeOrigin: true,
    rewrite: (path) => path
  }
}
```

## 📱 页面说明

### 1. 行情数据 (Market Data)
- 查看实时K线数据
- 支持多个交易对和时间周期
- 显示K线图表和数据表格
- 缓存管理

### 2. 策略回测 (Strategy Backtest)
- 快速策略回测
- 支持 Long/Short/Neutral 三种模式
- 显示权益曲线和交易记录
- 实时性能指标

### 3. 完整回测 (Full Backtest)
- 历史数据回测 (最近3年)
- 完整的性能指标
- 年化收益、最大回撤、Sharpe比率等
- 详细的交易记录

### 4. 参数优化 (Parameter Optimize)
- Grid Search 参数优化
- 自定义参数范围
- 多指标优化支持
- 结果对比分析

## 🎨 UI 特性

- **深色主题** - 专业的深色设计
- **响应式布局** - 自适应各种屏幕
- **实时状态** - API 连接状态指示
- **交互反馈** - 加载、成功、错误提示
- **数据可视化** - 图表和表格展示

## 📊 API 集成

前端通过以下 API 与后端通信:

### 行情数据
- `GET /api/symbols` - 获取支持的交易对
- `GET /api/intervals` - 获取支持的时间周期
- `GET /api/klines` - 获取K线数据
- `GET /api/cache/stats` - 获取缓存统计
- `POST /api/cache/clear` - 清空缓存

### 策略回测
- `POST /api/strategy/backtest` - 策略回测

### 完整回测
- `POST /api/backtest/run` - 单参数回测
- `POST /api/backtest/grid-search` - 参数优化

## 🐛 故障排除

### 连接失败
- 检查后端服务是否运行在 `http://localhost:5001`
- 检查 CORS 配置
- 查看浏览器控制台错误信息

### 图表不显示
- 确保 Chart.js 和 Lightweight Charts 库已加载
- 检查数据是否正确返回
- 查看浏览器控制台错误

### 性能问题
- 减少查询数据范围
- 优化参数范围大小
- 使用浏览器开发者工具分析

## 📚 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── MarketData.vue          # 行情数据组件
│   │   ├── StrategyBacktest.vue    # 策略回测组件
│   │   ├── FullBacktest.vue        # 完整回测组件
│   │   └── ParameterOptimize.vue   # 参数优化组件
│   ├── App.vue                     # 主应用组件
│   ├── main.js                     # 入口文件
│   └── style.css                   # 全局样式
├── index.html                      # HTML 模板
├── vite.config.js                  # Vite 配置
├── server.js                       # Node.js 服务器
├── package.json                    # 项目配置
└── README.md                       # 本文件
```

## 🚀 快速开始

### 本地开发
```bash
cd frontend
npm install
npm run dev
```

### 生产部署
```bash
cd frontend
npm install
npm run build
npm run serve
```

### Docker 部署
```bash
docker build -t trading-dashboard frontend/
docker run -p 3000:3000 trading-dashboard
```

## 📝 许可证

MIT

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**版本**: 1.0.0  
**最后更新**: 2026-01-28
