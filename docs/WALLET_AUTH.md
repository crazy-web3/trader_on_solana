# 钱包登录模块使用说明

## 概述

本项目集成了 Solana 钱包登录功能，支持 Phantom 和 Solflare 钱包。只有在白名单中的钱包地址才能成功登录和使用系统功能。

## 功能特性

- 🔐 **安全认证**: 基于钱包签名的无密码登录
- 📝 **白名单控制**: 只有授权钱包才能访问系统
- 🎫 **Token 管理**: JWT 风格的认证令牌，24小时有效期
- 👥 **角色管理**: 支持管理员和普通用户角色
- 🔄 **自动重连**: 支持页面刷新后自动恢复登录状态

## 支持的钱包

- **Phantom**: 最流行的 Solana 浏览器钱包
- **Solflare**: 功能丰富的 Solana 钱包

## 安装和配置

### 1. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
```

### 2. 配置白名单

编辑 `wallet_whitelist.json` 文件或使用管理工具：

```bash
# 查看当前白名单
python manage_whitelist.py list

# 添加钱包到白名单
python manage_whitelist.py add <钱包地址> --nickname "用户名" --role user

# 移除钱包
python manage_whitelist.py remove <钱包地址>
```

### 3. 启动服务

```bash
# 启动后端
python app.py

# 启动前端
cd frontend
npm run dev
```

## API 接口

### 认证相关接口

#### 获取认证挑战
```http
POST /api/auth/challenge
Content-Type: application/json

{
  "public_key": "钱包公钥"
}
```

#### 钱包登录
```http
POST /api/auth/login
Content-Type: application/json

{
  "public_key": "钱包公钥",
  "message": "签名消息",
  "signature": "钱包签名"
}
```

#### 验证认证状态
```http
GET /api/auth/verify
Authorization: Bearer <token>
```

#### 登出
```http
POST /api/auth/logout
Authorization: Bearer <token>
```

### 受保护的接口

以下接口需要在请求头中包含认证令牌：

- `POST /api/strategy/backtest` - 策略回测
- `POST /api/backtest/run` - 完整回测
- `POST /api/backtest/grid-search` - 参数优化

## 前端集成

### 钱包连接组件

```vue
<template>
  <WalletConnect @connected="onWalletConnected" />
</template>

<script>
import WalletConnect from './components/WalletConnect.vue'

export default {
  components: { WalletConnect },
  setup() {
    const onWalletConnected = (data) => {
      console.log('钱包已连接:', data.user)
      console.log('认证令牌:', data.token)
    }
    
    return { onWalletConnected }
  }
}
</script>
```

### 发送认证请求

```javascript
// 在需要认证的请求中添加 Authorization 头
const response = await fetch('/api/strategy/backtest', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`
  },
  body: JSON.stringify(requestData)
})
```

## 白名单管理

### 使用管理工具

```bash
# 查看所有钱包
python manage_whitelist.py list

# 添加新钱包
python manage_whitelist.py add So11111111111111111111111111111111111111112 \
  --nickname "Alice" --role user

# 查看钱包信息
python manage_whitelist.py info So11111111111111111111111111111111111111112

# 停用钱包（保留在列表中但禁止登录）
python manage_whitelist.py deactivate So11111111111111111111111111111111111111112

# 重新激活钱包
python manage_whitelist.py activate So11111111111111111111111111111111111111112

# 完全移除钱包
python manage_whitelist.py remove So11111111111111111111111111111111111111112
```

### 直接编辑配置文件

编辑 `wallet_whitelist.json`:

```json
{
  "wallets": {
    "钱包公钥": {
      "nickname": "用户昵称",
      "role": "user",
      "added_at": "2025-01-29T00:00:00",
      "active": true
    }
  },
  "created_at": "2025-01-29T00:00:00"
}
```

## 安全考虑

1. **签名验证**: 每次登录都需要钱包签名验证
2. **白名单控制**: 只有预授权的钱包才能访问
3. **令牌过期**: 认证令牌24小时后自动过期
4. **HTTPS**: 生产环境必须使用 HTTPS
5. **CORS**: 配置适当的跨域策略

## 故障排除

### 常见问题

1. **钱包未安装**
   - 确保浏览器已安装 Phantom 或 Solflare 扩展

2. **签名失败**
   - 检查钱包是否已解锁
   - 确认用户点击了签名确认

3. **白名单错误**
   - 验证钱包地址是否在白名单中
   - 检查钱包状态是否为激活状态

4. **令牌过期**
   - 重新连接钱包获取新令牌
   - 检查系统时间是否正确

### 调试模式

启用调试日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 开发指南

### 添加新钱包支持

1. 在 `WalletConnect.vue` 中添加新钱包的连接逻辑
2. 确保新钱包支持 Solana 标准的签名接口
3. 更新钱包检测逻辑

### 自定义认证流程

1. 修改 `wallet_auth/auth.py` 中的认证逻辑
2. 更新挑战消息格式
3. 调整令牌有效期设置

### 扩展用户角色

1. 在白名单配置中定义新角色
2. 在后端 API 中添加角色检查
3. 更新前端权限控制逻辑

## 许可证

本模块遵循项目主许可证。