# 🚀 前端部署指南

## 📋 概述

前端已独立为单独的 Vue 3 + Vite 项目，可以独立部署和扩展。

## 🏗️ 项目结构

```
frontend/                          # 前端项目根目录
├── src/
│   ├── components/               # Vue 组件
│   │   ├── MarketData.vue        # 行情数据
│   │   ├── StrategyBacktest.vue  # 策略回测
│   │   ├── FullBacktest.vue      # 完整回测
│   │   └── ParameterOptimize.vue # 参数优化
│   ├── App.vue                   # 主应用
│   ├── main.js                   # 入口
│   └── style.css                 # 样式
├── index.html                    # HTML 模板
├── vite.config.js                # Vite 配置
├── server.js                     # Node.js 服务器
├── package.json                  # 依赖配置
└── README.md                     # 项目文档
```

## 🛠️ 本地开发

### 1. 安装依赖
```bash
cd frontend
npm install
```

### 2. 启动开发服务器
```bash
npm run dev
```

访问 `http://localhost:3000`

### 3. 构建生产版本
```bash
npm run build
```

输出到 `frontend/dist` 目录

## 🌐 部署方式

### 方式1: Node.js 服务器 (推荐)

#### 本地运行
```bash
cd frontend
npm install
npm run build
npm run serve
```

服务器运行在 `http://localhost:3000`

#### 生产环境
```bash
# 使用 PM2 管理进程
npm install -g pm2

# 启动应用
pm2 start server.js --name "trading-dashboard"

# 查看日志
pm2 logs trading-dashboard

# 重启应用
pm2 restart trading-dashboard

# 停止应用
pm2 stop trading-dashboard
```

### 方式2: Nginx 反向代理

#### 配置文件 (`/etc/nginx/sites-available/trading-dashboard`)

```nginx
upstream frontend {
    server localhost:3000;
}

upstream backend {
    server localhost:5001;
}

server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API 代理
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 缓存静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### 启用配置
```bash
sudo ln -s /etc/nginx/sites-available/trading-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 方式3: Docker 容器

#### Dockerfile
```dockerfile
# 构建阶段
FROM node:18-alpine as builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend . .
RUN npm run build

# 运行阶段
FROM node:18-alpine

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install --production

COPY --from=builder /app/dist ./dist
COPY frontend/server.js .

EXPOSE 3000

ENV NODE_ENV=production
CMD ["node", "server.js"]
```

#### 构建和运行
```bash
# 构建镜像
docker build -t trading-dashboard:latest .

# 运行容器
docker run -d \
  --name trading-dashboard \
  -p 3000:3000 \
  -e API_URL=http://backend:5001 \
  trading-dashboard:latest

# 查看日志
docker logs -f trading-dashboard

# 停止容器
docker stop trading-dashboard
```

#### Docker Compose
```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://backend:5001
    depends_on:
      - backend
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
    restart: unless-stopped
```

运行:
```bash
docker-compose up -d
```

### 方式4: 云平台部署

#### Vercel
1. 推送代码到 GitHub
2. 在 Vercel 中导入项目
3. 设置构建命令: `npm run build`
4. 设置输出目录: `dist`
5. 设置环境变量:
   - `VITE_API_URL=https://your-api-domain.com`

#### Netlify
1. 推送代码到 GitHub
2. 在 Netlify 中连接仓库
3. 设置构建命令: `npm run build`
4. 设置发布目录: `dist`
5. 设置环境变量:
   - `VITE_API_URL=https://your-api-domain.com`

#### AWS S3 + CloudFront
```bash
# 构建
npm run build

# 上传到 S3
aws s3 sync dist/ s3://your-bucket-name/

# 清除 CloudFront 缓存
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

## 🔧 配置

### 环境变量

创建 `.env` 文件:

```env
# 开发环境
VITE_API_URL=http://localhost:5001
VITE_API_TIMEOUT=30000

# 生产环境
VITE_API_URL=https://api.your-domain.com
VITE_API_TIMEOUT=30000
```

### Vite 配置

编辑 `vite.config.js`:

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:5001',
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser'
  }
})
```

## 📊 性能优化

### 1. 代码分割
```javascript
// 动态导入组件
const MarketData = defineAsyncComponent(() => import('./components/MarketData.vue'))
```

### 2. 图片优化
```bash
# 使用 imagemin 压缩图片
npm install -D imagemin imagemin-mozjpeg imagemin-pngquant
```

### 3. 缓存策略
```nginx
# Nginx 缓存配置
location ~* \.(js|css)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

location ~* \.(html)$ {
    expires 1h;
    add_header Cache-Control "public, must-revalidate";
}
```

### 4. CDN 加速
```javascript
// 使用 CDN 加载第三方库
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
```

## 🔒 安全性

### 1. HTTPS
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 重定向 HTTP 到 HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }
}
```

### 2. CORS 配置
```javascript
// 后端 Flask 配置
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://your-domain.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

### 3. 环境变量保护
```bash
# 不要提交 .env 文件
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore
```

## 📈 监控和日志

### PM2 监控
```bash
# 启用监控
pm2 monit

# 查看日志
pm2 logs trading-dashboard

# 导出日志
pm2 logs trading-dashboard > logs.txt
```

### Nginx 日志
```bash
# 访问日志
tail -f /var/log/nginx/access.log

# 错误日志
tail -f /var/log/nginx/error.log
```

### Docker 日志
```bash
# 查看日志
docker logs -f trading-dashboard

# 导出日志
docker logs trading-dashboard > logs.txt
```

## 🚀 CI/CD 流程

### GitHub Actions
```yaml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: cd frontend && npm install
      
      - name: Build
        run: cd frontend && npm run build
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app/trading-dashboard
            git pull
            cd frontend
            npm install
            npm run build
            pm2 restart trading-dashboard
```

## 📝 检查清单

部署前检查:

- [ ] 后端服务运行在 `http://localhost:5001`
- [ ] 前端依赖已安装 (`npm install`)
- [ ] 环境变量已配置 (`.env`)
- [ ] 构建成功 (`npm run build`)
- [ ] 本地测试通过 (`npm run dev`)
- [ ] CORS 配置正确
- [ ] HTTPS 证书已配置
- [ ] 日志系统已设置
- [ ] 监控告警已配置
- [ ] 备份策略已制定

## 🆘 故障排除

### 连接失败
```bash
# 检查后端服务
curl http://localhost:5001/api/health

# 检查前端服务
curl http://localhost:3000

# 查看 Nginx 日志
tail -f /var/log/nginx/error.log
```

### 构建失败
```bash
# 清除缓存
rm -rf node_modules dist
npm install
npm run build

# 检查 Node 版本
node --version  # 应该 >= 16
```

### 性能问题
```bash
# 分析包大小
npm run build -- --analyze

# 检查网络
curl -I http://localhost:3000

# 查看资源加载
# 打开浏览器开发者工具 -> Network 标签
```

## 📞 支持

- 前端文档: `frontend/README.md`
- 后端文档: `DEPLOYMENT.md`
- 系统文档: `SYSTEM_COMPLETE.md`

---

**版本**: 1.0.0  
**最后更新**: 2026-01-28
