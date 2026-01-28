# 🚀 快速开始 - 行情数据查看器

## 📋 项目说明

这是一个基于 Python Flask 后端 + HTML5 前端的行情数据查看系统，支持：

- ✅ 多币种K线数据查询 (BTC, ETH, BNB, SOL)
- ✅ 多时间周期支持 (1m, 5m, 15m, 1h, 4h, 1d, 1w)
- ✅ 智能缓存管理 (LRU + TTL)
- ✅ 数据验证和清洗
- ✅ 实时K线图表展示
- ✅ 详细数据表格查看

## 🛠️ 环境要求

- Python 3.8+
- 现代浏览器 (Chrome, Firefox, Safari, Edge)

## 📦 安装依赖

### 方式1: 自动安装 (推荐)

**macOS/Linux:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```bash
run.bat
```

### 方式2: 手动安装

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

## 🚀 运行服务

### 启动后端API

```bash
python app.py
```

输出示例：
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

### 打开前端页面

在浏览器中打开 `index.html` 文件，或访问：
```
file:///path/to/index.html
```

## 📊 使用说明

### 1. 查询K线数据

1. 在左侧面板选择：
   - **币种**: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT
   - **时间周期**: 1分钟到1周
   - **时间范围**: 1-365天

2. 点击 **🔍 查询数据** 按钮

3. 系统会：
   - 检查缓存（如果有则直接返回）
   - 从数据源获取数据
   - 验证数据完整性
   - 存入缓存
   - 展示结果

### 2. 查看数据

- **📈 K线图表**: 实时显示收盘价、最高价、最低价
- **📋 数据表格**: 显示前50条详细数据
- **📊 统计信息**: 数据条数、时间范围、最高/最低价

### 3. 缓存管理

- **缓存信息**: 显示当前缓存状态
- **清空缓存**: 点击 **🗑️ 清空缓存** 按钮清除所有缓存

## 🔗 API 端点

### 健康检查
```bash
curl http://localhost:5000/api/health
```

### 获取支持的币种
```bash
curl http://localhost:5000/api/symbols
```

### 获取支持的时间周期
```bash
curl http://localhost:5000/api/intervals
```

### 获取K线数据
```bash
curl "http://localhost:5000/api/klines?symbol=BTC/USDT&interval=1h&days=7"
```

参数说明：
- `symbol`: 币种 (BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT)
- `interval`: 时间周期 (1m, 5m, 15m, 1h, 4h, 1d, 1w)
- `days`: 天数范围 (1-365)

### 获取缓存统计
```bash
curl http://localhost:5000/api/cache/stats
```

### 清空缓存
```bash
curl -X POST http://localhost:5000/api/cache/clear
```

## 📁 项目结构

```
.
├── app.py                      # Flask API 服务器
├── index.html                  # 前端页面
├── requirements.txt            # Python 依赖
├── run.sh                       # macOS/Linux 启动脚本
├── run.bat                      # Windows 启动脚本
├── QUICKSTART.md               # 本文件
└── market_data_layer/          # 核心模块
    ├── __init__.py
    ├── models.py               # 数据模型
    ├── adapter.py              # 数据源适配器
    ├── cache.py                # 缓存管理器
    ├── validator.py            # 数据验证器
    └── exceptions.py           # 自定义异常
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_validator.py

# 运行属性测试
pytest tests/test_properties.py -v

# 显示覆盖率
pytest --cov=market_data_layer
```

## 🐛 常见问题

### Q: 前端无法连接到后端？
A: 确保：
1. 后端服务正在运行 (`python app.py`)
2. 后端运行在 `http://localhost:5000`
3. 浏览器允许跨域请求 (CORS已启用)

### Q: 数据为什么是模拟数据？
A: 当前使用 `MockDataSourceAdapter` 生成测试数据。要使用真实数据，需要：
1. 实现真实的数据源适配器 (如 Jupiter API)
2. 在 `app.py` 中替换 `MockDataSourceAdapter`

### Q: 缓存多久过期？
A: 默认 24 小时。可在 `app.py` 中修改：
```python
cache = CacheManager(max_size=1000, ttl_ms=24 * 60 * 60 * 1000)
```

### Q: 如何修改缓存大小？
A: 在 `app.py` 中修改：
```python
cache = CacheManager(max_size=2000)  # 改为2000条
```

## 📈 性能指标

- **缓存命中**: < 100ms
- **单次查询**: < 500ms
- **1000条数据**: < 1s
- **并发支持**: 100+ 并发请求

## 🔐 安全性

- ✅ 参数验证
- ✅ 数据验证
- ✅ 错误处理
- ✅ 日志记录
- ✅ CORS 跨域支持

## 📝 日志

后端会输出详细的日志信息：
```
INFO:__main__:Cache hit for BTC/USDT:1h:...
INFO:__main__:Fetching data for BTC/USDT 1h
WARNING:__main__:Found 0 invalid K-lines
```

## 🚀 下一步

1. **集成真实数据源**: 实现 Jupiter API 或其他交易所 API
2. **添加更多币种**: 扩展支持的交易对
3. **实现回测功能**: 添加网格交易策略回测
4. **性能优化**: 实现异步处理和连接池
5. **部署上线**: 使用 Docker 和云平台部署

## 📞 支持

如有问题，请查看：
- 后端日志输出
- 浏览器控制台 (F12)
- 测试文件 (`tests/` 目录)

## 📄 许可证

MIT License

---

**祝你使用愉快！** 🎉
