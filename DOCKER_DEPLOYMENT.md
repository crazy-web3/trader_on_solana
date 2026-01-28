# 🐳 Docker 部署指南

## 📋 概述

使用 Docker 和 Docker Compose 快速部署完整的交易系统。

---

## 🚀 快速开始 (5分钟)

### 1. 前置要求

- Docker 已安装 (v20.10+)
- Docker Compose 已安装 (v2.0+)

### 2. 启动所有服务

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 访问应用

- 前端: `http://localhost:3000`
- 后端 API: `http://localhost:5001`
- Nginx: `http://localhost` (如果启用)

### 4. 停止服务

```bash
docker-compose down
```

---

## 📦 服务说明

### 后端服务 (Backend)

```yaml
backend:
  build: Dockerfile.backend
  ports:
    - "5001:5001"
  environment:
    - FLASK_ENV=production
```

**功能**:
- Flask API 服务器
- 行情数据层
- 策略引擎
- 回测引擎

**健康检查**: `http://localhost:5001/api/health`

### 前端服务 (Frontend)

```yaml
frontend:
  build: ./frontend/Dockerfile
  ports:
    - "3000:3000"
  depends_on:
    - backend
```

**功能**:
- Vue 3 应用
- Node.js 服务器
- 静态文件服务
- API 代理

**健康检查**: `http://localhost:3000`

### Nginx 反向代理 (可选)

```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
```

**功能**:
- 反向代理
- 负载均衡
- HTTPS 支持
- 缓存管理

---

## 🔧 常用命令

### 查看服务状态

```bash
# 查看所有容器
docker-compose ps

# 查看容器日志
docker-compose logs backend
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f
```

### 管理服务

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重启特定服务
docker-compose restart frontend

# 查看服务资源使用
docker stats
```

### 进入容器

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh

# 执行命令
docker-compose exec backend python -c "import sys; print(sys.version)"
```

### 查看日志

```bash
# 查看最后 100 行日志
docker-compose logs --tail=100

# 查看特定时间的日志
docker-compose logs --since 10m

# 导出日志到文件
docker-compose logs > logs.txt
```

---

## 🔐 安全配置

### 环境变量

创建 `.env` 文件:

```env
# 后端配置
FLASK_ENV=production
FLASK_DEBUG=0

# 前端配置
NODE_ENV=production
VITE_API_URL=http://localhost:5001

# Nginx 配置
NGINX_PORT=80
NGINX_SSL_PORT=443
```

### 网络隔离

```yaml
networks:
  trading-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 卷挂载

```yaml
volumes:
  backend_data:
    driver: local
  frontend_data:
    driver: local
```

---

## 📊 监控和日志

### 查看容器资源使用

```bash
docker stats
```

### 查看容器进程

```bash
docker-compose top backend
docker-compose top frontend
```

### 查看容器网络

```bash
docker network inspect trading_default
```

### 导出日志

```bash
# 导出所有日志
docker-compose logs > all-logs.txt

# 导出特定服务日志
docker-compose logs backend > backend-logs.txt
```

---

## 🚀 生产部署

### 1. 使用生产配置

创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: always
    environment:
      - FLASK_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: always
    environment:
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
```

启动:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 2. 配置 HTTPS

创建 SSL 证书:

```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/private.key \
  -out ssl/certificate.crt
```

### 3. 配置 Nginx

创建 `nginx.conf`:

```nginx
upstream backend {
    server backend:5001;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;

    # 前端
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 4. 自动重启

```yaml
services:
  backend:
    restart: always
  frontend:
    restart: always
  nginx:
    restart: always
```

---

## 🔄 CI/CD 集成

### GitHub Actions

创建 `.github/workflows/deploy.yml`:

```yaml
name: Deploy with Docker

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1

      - name: Build and push
        uses: docker/build-push-action@v2
        with:
          context: .
          push: true
          tags: your-registry/trading-system:latest

      - name: Deploy
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.USERNAME }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app/trading-system
            docker-compose pull
            docker-compose up -d
```

---

## 📈 性能优化

### 1. 多阶段构建

```dockerfile
# 构建阶段
FROM node:18 as builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 运行阶段
FROM node:18-alpine
COPY --from=builder /app/dist ./dist
```

### 2. 缓存优化

```dockerfile
# 先复制 package 文件
COPY package*.json ./
RUN npm install

# 再复制源代码
COPY . .
```

### 3. 资源限制

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

---

## 🐛 故障排除

### 容器无法启动

```bash
# 查看错误日志
docker-compose logs backend

# 检查镜像
docker images

# 重新构建
docker-compose build --no-cache
```

### 连接失败

```bash
# 检查网络
docker network ls
docker network inspect trading_default

# 检查 DNS
docker-compose exec backend nslookup frontend
```

### 性能问题

```bash
# 查看资源使用
docker stats

# 查看进程
docker-compose top backend

# 查看日志
docker-compose logs --tail=100
```

---

## 📝 检查清单

### 部署前
- [ ] Docker 已安装
- [ ] Docker Compose 已安装
- [ ] 代码已提交
- [ ] 环境变量已配置
- [ ] SSL 证书已准备

### 部署中
- [ ] 镜像构建成功
- [ ] 容器启动成功
- [ ] 健康检查通过
- [ ] 日志无错误

### 部署后
- [ ] 前端可访问
- [ ] 后端 API 可访问
- [ ] 数据库连接正常
- [ ] 监控告警已配置

---

## 🚀 常见场景

### 场景1: 更新代码

```bash
# 拉取最新代码
git pull

# 重新构建
docker-compose build

# 重启服务
docker-compose up -d
```

### 场景2: 查看日志

```bash
# 查看实时日志
docker-compose logs -f

# 查看特定服务
docker-compose logs -f backend

# 导出日志
docker-compose logs > logs.txt
```

### 场景3: 备份数据

```bash
# 备份数据卷
docker run --rm -v trading_backend_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/backup.tar.gz -C /data .

# 恢复数据
docker run --rm -v trading_backend_data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/backup.tar.gz -C /data
```

### 场景4: 扩展服务

```yaml
# 运行多个后端实例
services:
  backend:
    deploy:
      replicas: 3
```

---

## 📞 支持

- Docker 文档: https://docs.docker.com
- Docker Compose 文档: https://docs.docker.com/compose
- 项目文档: `SYSTEM_COMPLETE.md`

---

**版本**: 1.0.0  
**最后更新**: 2026-01-28

🐳 **Docker 部署完成！**
