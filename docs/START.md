# 🚀 启动行情数据查看器

## ✅ 后端已启动

后端 API 服务已在运行：
- **地址**: http://localhost:5001
- **状态**: ✅ 正常运行

## 📖 使用步骤

### 1️⃣ 打开前端页面

在浏览器中打开 `index.html` 文件：
- 直接双击 `index.html` 文件
- 或在浏览器地址栏输入: `file:///path/to/index.html`

### 2️⃣ 查询行情数据

在前端页面中：
1. 选择币种 (BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT)
2. 选择时间周期 (1m, 5m, 15m, 1h, 4h, 1d, 1w)
3. 设置时间范围 (1-365天)
4. 点击 **🔍 查询数据** 按钮

### 3️⃣ 查看结果

- **📈 K线图表**: 实时显示价格走势
- **📋 数据表格**: 显示详细的K线数据
- **📊 统计信息**: 显示数据统计

## 🔗 API 端点

### 查询K线数据
```bash
curl "http://localhost:5001/api/klines?symbol=BTC/USDT&interval=1h&days=7"
```

### 获取支持的币种
```bash
curl http://localhost:5001/api/symbols
```

### 获取支持的时间周期
```bash
curl http://localhost:5001/api/intervals
```

### 获取缓存统计
```bash
curl http://localhost:5001/api/cache/stats
```

### 清空缓存
```bash
curl -X POST http://localhost:5001/api/cache/clear
```

## 📊 功能特性

✅ **多币种支持**: BTC, ETH, BNB, SOL
✅ **多时间周期**: 1分钟到1周
✅ **智能缓存**: LRU + TTL 机制
✅ **数据验证**: 自动验证数据完整性
✅ **实时图表**: Chart.js 动态图表
✅ **详细表格**: 显示前50条数据
✅ **缓存管理**: 查看和清空缓存

## 🛠️ 技术栈

- **后端**: Python Flask + CORS
- **前端**: HTML5 + CSS3 + JavaScript
- **图表**: Chart.js 4.4.0
- **缓存**: LRU + TTL 策略
- **验证**: 数据完整性验证

## 📝 数据说明

当前使用 **模拟数据源** (MockDataSourceAdapter)，生成的是测试数据。

要使用真实数据，需要：
1. 实现真实的数据源适配器 (如 Jupiter API)
2. 在 `app.py` 中替换 `MockDataSourceAdapter`

## 🔧 配置修改

### 修改API端口
编辑 `app.py`:
```python
app.run(debug=True, host="0.0.0.0", port=5001)  # 改为其他端口
```

### 修改缓存大小
编辑 `app.py`:
```python
cache = CacheManager(max_size=2000)  # 改为2000条
```

### 修改缓存过期时间
编辑 `app.py`:
```python
cache = CacheManager(default_ttl=48 * 60 * 60 * 1000)  # 改为48小时
```

## 📱 浏览器兼容性

✅ Chrome 90+
✅ Firefox 88+
✅ Safari 14+
✅ Edge 90+

## 🐛 故障排除

### 前端无法连接到后端？
- 确保后端服务正在运行
- 检查浏览器控制台 (F12) 的错误信息
- 确认API地址是否正确 (http://localhost:5001)

### 数据为什么是模拟数据？
- 当前使用测试数据源，这是正常的
- 要使用真实数据，需要实现真实的数据源适配器

### 缓存不工作？
- 检查后端日志输出
- 尝试清空缓存后重新查询

## 📞 获取帮助

查看以下文件获取更多信息：
- `QUICKSTART.md` - 详细的快速开始指南
- `README.md` - 项目背景和整体方案
- 后端日志输出 - 查看详细的错误信息

## 🎉 开始使用

现在你可以：
1. 打开 `index.html` 文件
2. 选择币种和时间周期
3. 点击查询按钮
4. 查看K线图表和数据

祝你使用愉快！ 🚀
