# 快速启动指南

## 🚀 当前系统状态

### ✅ 运行中的服务
- **后端服务**: http://localhost:5001 (Flask)
- **前端服务**: http://localhost:3000 (Vue.js + Vite)

### 📊 可访问的页面
1. **市场数据** - http://localhost:3000/ (默认页面)
2. **策略回测** - http://localhost:3000/#/strategy-backtest
3. **完整回测** - http://localhost:3000/#/full-backtest
4. **参数优化** - http://localhost:3000/#/parameter-optimize

## 🔧 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue.js)                         │
│              http://localhost:3000                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • 市场数据展示                                    │   │
│  │ • 策略回测界面                                    │   │
│  │ • 完整回测对比                                    │   │
│  │ • 参数优化配置                                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↕ API
┌─────────────────────────────────────────────────────────┐
│                   后端 (Flask)                           │
│              http://localhost:5001                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ • 市场数据获取 (Binance API)                      │   │
│  │ • 策略回测引擎 (修正版)                           │   │
│  │ • 完整回测对比                                    │   │
│  │ • 参数网格搜索                                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 📝 核心功能

### 1. 市场数据 (Market Data)
- 实时 K 线图表
- 支持多币种 (ETH/USDT, BTC/USDT, SOL/USDT)
- 支持多时间周期 (4小时默认)
- 默认 90 天历史数据

### 2. 策略回测 (Strategy Backtest)
- 单策略回测
- 支持三种模式: 做多/做空/中性
- 自动价格区间计算
- 网格收益和未配对收益追踪
- 权益曲线自动刷新 (2次)

### 3. 完整回测 (Full Backtest)
- 三策略同时对比
- 参数与策略回测对齐
- 多线权益曲线对比
- 策略性能排名

### 4. 参数优化 (Parameter Optimize)
- 网格搜索参数优化
- 需要钱包认证
- 自动找到最优参数组合

## 🧪 测试回测引擎

### 快速测试命令
```bash
# 测试策略回测 API
curl -X POST http://localhost:5001/api/strategy/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETH/USDT",
    "mode": "long",
    "initial_capital": 10000,
    "days": 30,
    "leverage": 1,
    "funding_rate": 0,
    "auto_calculate_range": true
  }'

# 测试完整回测 API
curl -X POST http://localhost:5001/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETH/USDT",
    "initial_capital": 10000,
    "days": 30,
    "leverage": 1,
    "funding_rate": 0,
    "auto_calculate_range": true
  }'
```

## 📊 最近测试结果

### 做多网格策略 (30天)
- 初始资金: $10,000
- 最终资金: $9,481.99
- 总收益率: -5.18%
- 总交易数: 17
- 胜率: 23.53%
- 网格收益: $41.50
- 未配对收益: $84.15

## 🎨 UI 特性

- ✅ 深色/浅色主题切换
- ✅ 响应式设计 (移动端友好)
- ✅ 实时图表更新
- ✅ 自动刷新机制
- ✅ 参数对齐

## 🔐 认证

- 市场数据: 无需认证
- 策略回测: 无需认证
- 完整回测: 无需认证
- 参数优化: 需要 Solana 钱包认证

## 📚 文档

- `README.md` - 项目总体说明
- `TEST_REPORT_CORRECTED_ENGINE.md` - 修正版引擎测试报告
- `ARCHIVE_SUMMARY.md` - 文件归档说明
- `archive/README.md` - 归档文件索引

## 🛠️ 故障排除

### 前端无法连接后端
```bash
# 检查后端是否运行
curl http://localhost:5001/api/health

# 检查前端代理配置
cat frontend/vite.config.js
```

### 图表不显示
- 清除浏览器缓存
- 点击"强制刷新"按钮
- 检查浏览器控制台错误

### 回测速度慢
- 减少回测天数
- 检查系统资源使用
- 查看后端日志

## 📞 支持

如有问题，请检查:
1. 后端日志: `http://localhost:5001`
2. 前端控制台: 浏览器 F12
3. 测试报告: `TEST_REPORT_CORRECTED_ENGINE.md`

---

**最后更新**: 2026年1月30日  
**系统状态**: 🟢 生产就绪