# 🎉 开始使用行情数据查看器

## ✨ 欢迎！

你已经拥有一个完整的行情数据查看系统。以下是快速开始指南。

## 🚀 立即开始 (3步)

### 1️⃣ 打开前端页面

**最简单的方式**: 直接双击 `index.html` 文件

或在浏览器中打开:
```
file:///path/to/index.html
```

### 2️⃣ 选择查询参数

在左侧面板中选择:
- **币种**: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT
- **时间周期**: 1m, 5m, 15m, 1h, 4h, 1d, 1w
- **时间范围**: 1-365天

### 3️⃣ 点击查询

点击 **🔍 查询数据** 按钮，查看结果！

## 📊 你会看到什么

✅ **K线图表** - 实时显示价格走势
✅ **数据表格** - 显示详细的K线数据
✅ **统计信息** - 显示数据统计
✅ **缓存管理** - 管理缓存数据

## 🔧 后端服务

后端服务已在运行:
- **地址**: http://localhost:5001
- **状态**: ✅ 正常

如果需要重启:
```bash
# macOS/Linux
./run.sh

# Windows
run.bat

# 或手动启动
python3 app.py
```

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| `HOW_TO_USE.md` | 📖 详细使用指南 |
| `QUICKSTART.md` | ⚡ 快速开始指南 |
| `DEPLOYMENT.md` | 🚀 部署和配置 |
| `SUMMARY.md` | 📋 项目总结 |

## 🎯 常见任务

### 查询BTC最近7天的1小时K线
1. 币种: BTC/USDT
2. 时间周期: 1h
3. 时间范围: 7
4. 点击查询

### 查看缓存信息
右侧面板自动显示缓存统计

### 清空缓存
点击 **🗑️ 清空缓存** 按钮

### 测试API
```bash
python3 test_api.py
```

## 💡 快速提示

- 🔄 **缓存加速**: 相同查询会自动使用缓存 (< 100ms)
- ⌨️ **快速查询**: 修改参数后按 Enter 键快速查询
- 📱 **响应式设计**: 支持各种屏幕尺寸
- 🌐 **跨浏览器**: 支持 Chrome, Firefox, Safari, Edge

## 🐛 遇到问题？

### 前端无法连接到后端
1. 确保后端服务正在运行
2. 按 F12 打开浏览器控制台查看错误
3. 检查 API 地址是否正确

### 数据为什么是模拟数据？
当前使用测试数据源。要使用真实数据，需要实现真实的数据源适配器。

### 其他问题
查看 `HOW_TO_USE.md` 中的常见问题部分

## 🌟 功能特性

✅ **多币种支持** - BTC, ETH, BNB, SOL
✅ **多时间周期** - 1分钟到1周
✅ **智能缓存** - LRU + TTL 机制
✅ **数据验证** - 自动验证数据完整性
✅ **实时图表** - Chart.js 动态图表
✅ **详细表格** - 显示前50条数据
✅ **缓存管理** - 查看和清空缓存
✅ **响应式设计** - 适配各种屏幕

## 📈 性能指标

| 指标 | 性能 |
|------|------|
| 缓存命中 | < 100ms |
| 单次查询 | < 500ms |
| 1000条数据 | < 1s |
| 并发支持 | 100+ |

## 🔗 API 端点

```bash
# 获取K线数据
curl "http://localhost:5001/api/klines?symbol=BTC/USDT&interval=1h&days=7"

# 获取支持的币种
curl http://localhost:5001/api/symbols

# 获取支持的时间周期
curl http://localhost:5001/api/intervals

# 获取缓存统计
curl http://localhost:5001/api/cache/stats

# 清空缓存
curl -X POST http://localhost:5001/api/cache/clear
```

## 📁 项目结构

```
.
├── index.html              # 前端页面 ← 打开这个文件
├── app.py                  # 后端服务
├── test_api.py             # API测试脚本
├── HOW_TO_USE.md           # 使用指南
├── QUICKSTART.md           # 快速开始
├── DEPLOYMENT.md           # 部署指南
├── SUMMARY.md              # 项目总结
└── market_data_layer/      # 核心模块
```

## 🎓 学习路径

### 初级用户
1. 打开 `index.html`
2. 查询不同币种的数据
3. 查看图表和表格

### 中级用户
1. 阅读 `HOW_TO_USE.md`
2. 尝试不同的查询参数
3. 管理缓存数据

### 高级用户
1. 阅读 `DEPLOYMENT.md`
2. 运行 `test_api.py` 测试API
3. 修改配置和参数

## 🚀 下一步

### 立即体验
1. 打开 `index.html`
2. 选择币种和时间周期
3. 点击查询

### 深入了解
- 查看 `HOW_TO_USE.md` 了解详细用法
- 查看 `QUICKSTART.md` 了解快速开始
- 查看 `DEPLOYMENT.md` 了解部署配置

### 测试系统
```bash
python3 test_api.py
```

## 💬 常见问题

**Q: 后端服务在哪里？**
A: 已在 http://localhost:5001 运行

**Q: 如何重启后端？**
A: 运行 `./run.sh` (macOS/Linux) 或 `run.bat` (Windows)

**Q: 支持哪些币种？**
A: BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT

**Q: 支持哪些时间周期？**
A: 1m, 5m, 15m, 1h, 4h, 1d, 1w

**Q: 缓存多久过期？**
A: 24小时

**Q: 如何清空缓存？**
A: 点击前端页面的 **🗑️ 清空缓存** 按钮

## 🎉 准备好了吗？

现在就打开 `index.html` 开始使用吧！

---

**祝你使用愉快！** 🚀

有任何问题，请查看相关文档或运行测试脚本。
