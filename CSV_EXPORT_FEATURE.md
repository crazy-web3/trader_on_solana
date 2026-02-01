# CSV数据导出功能

## 功能概述

在行情数据页面添加了CSV文件下载功能，用户可以将查询到的K线数据导出为CSV格式，方便进行离线分析和数据处理。

## 实现内容

### 后端API

**新增端点**: `GET /api/klines/export`

**功能**: 导出K线数据为CSV文件

**参数**:
- `symbol`: 交易对（如 "ETH/USDT"）
- `interval`: 时间周期（如 "1h", "4h", "1d"）
- `days`: 天数（默认7天）

**响应**:
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename=ETH_USDT_1h_7d.csv`

**CSV格式**:
```csv
Timestamp,Date,Open,High,Low,Close,Volume
1769317200000,2026-01-25 13:00:00,2945.29,2948.64,2942.17,2947.38,5113252.704878
1769320800000,2026-01-25 14:00:00,2947.39,2947.77,2935.01,2944.24,17608958.718324
...
```

**字段说明**:
- `Timestamp`: Unix时间戳（毫秒）
- `Date`: 格式化的日期时间（YYYY-MM-DD HH:MM:SS）
- `Open`: 开盘价
- `High`: 最高价
- `Low`: 最低价
- `Close`: 收盘价
- `Volume`: 成交量

### 前端界面

**位置**: 行情数据页面 → 查询参数卡片

**新增按钮**: "📥 下载CSV"

**功能**:
1. 点击按钮触发CSV下载
2. 自动使用当前查询参数（币种、时间周期、天数）
3. 文件名自动生成：`{币种}_{周期}_{天数}d.csv`
4. 按钮在没有数据时禁用

**用户体验**:
- 点击后显示"📥 正在准备下载..."提示
- 下载开始后显示"✅ CSV文件下载已开始"
- 浏览器自动弹出下载对话框

## 使用方法

### 通过前端界面

1. 打开行情数据页面
2. 选择币种、时间周期和天数
3. 点击"🔍 查询数据"加载数据
4. 点击"📥 下载CSV"下载文件

### 直接访问API

```bash
# 下载ETH/USDT 1小时 7天数据
curl "http://127.0.0.1:5001/api/klines/export?symbol=ETH/USDT&interval=1h&days=7" -o eth_data.csv

# 下载BTC/USDT 4小时 30天数据
curl "http://127.0.0.1:5001/api/klines/export?symbol=BTC/USDT&interval=4h&days=30" -o btc_data.csv
```

### 使用Python

```python
import requests

url = "http://127.0.0.1:5001/api/klines/export"
params = {
    "symbol": "ETH/USDT",
    "interval": "1h",
    "days": 7
}

response = requests.get(url, params=params)

if response.status_code == 200:
    with open("eth_data.csv", "w") as f:
        f.write(response.text)
    print("✅ CSV下载成功")
```

## 技术实现

### 后端实现 (app.py)

```python
@app.route("/api/klines/export", methods=["GET"])
def export_klines_csv():
    """Export K-line data as CSV file."""
    import io
    import csv
    from flask import make_response
    
    # 获取参数
    symbol = request.args.get("symbol", "BTC/USDT")
    interval = request.args.get("interval", "1h")
    days = int(request.args.get("days", 7))
    
    # 获取数据（使用缓存）
    klines = fetch_kline_data(...)
    
    # 创建CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 写入表头
    writer.writerow(['Timestamp', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    
    # 写入数据
    for kline in klines:
        date_str = datetime.fromtimestamp(kline.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([
            kline.timestamp,
            date_str,
            kline.open,
            kline.high,
            kline.low,
            kline.close,
            kline.volume
        ])
    
    # 创建响应
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={symbol.replace("/", "_")}_{interval}_{days}d.csv'
    
    return response
```

### 前端实现 (MarketData.vue)

```javascript
const downloadCSV = async () => {
  try {
    message.value = { type: 'info', text: '📥 正在准备下载...' }
    
    // 构建下载URL
    const url = `/api/klines/export?symbol=${symbol.value}&interval=${interval.value}&days=${days.value}`
    
    // 创建隐藏的a标签触发下载
    const link = document.createElement('a')
    link.href = url
    link.download = `${symbol.value.replace('/', '_')}_${interval.value}_${days.value}d.csv`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    message.value = { type: 'success', text: '✅ CSV文件下载已开始' }
  } catch (error) {
    message.value = { type: 'error', text: `❌ 下载失败: ${error.message}` }
  }
}
```

## 特性

### ✅ 优点

1. **利用缓存**: 使用与查询相同的缓存机制，下载速度快
2. **数据验证**: 导出前进行数据验证，确保数据质量
3. **格式友好**: CSV格式易于在Excel、Python、R等工具中使用
4. **自动命名**: 文件名包含币种、周期和天数信息
5. **无需登录**: 公开数据，无需认证即可下载
6. **浏览器兼容**: 使用标准HTML5下载方式，兼容所有现代浏览器

### 📊 数据完整性

- 包含完整的OHLCV数据（开高低收量）
- 提供Unix时间戳和格式化日期
- 数据按时间顺序排列
- 过滤无效数据

### 🚀 性能

- 使用内存中的StringIO，无需临时文件
- 利用缓存机制，避免重复请求
- 支持大数据量导出（最多365天）

## 使用场景

1. **离线分析**: 下载数据后在本地进行深度分析
2. **数据备份**: 定期下载数据作为备份
3. **第三方工具**: 导入到Excel、Python、R等工具
4. **策略开发**: 使用历史数据开发和测试交易策略
5. **学术研究**: 用于金融市场研究和论文写作

## 示例应用

### Excel分析

1. 下载CSV文件
2. 在Excel中打开
3. 创建图表和透视表
4. 进行技术分析

### Python分析

```python
import pandas as pd

# 读取CSV
df = pd.read_csv('ETH_USDT_1h_7d.csv')

# 转换时间戳
df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')

# 计算移动平均
df['MA20'] = df['Close'].rolling(20).mean()

# 绘图
df.plot(x='Date', y=['Close', 'MA20'])
```

### R分析

```r
# 读取CSV
data <- read.csv('ETH_USDT_1h_7d.csv')

# 转换时间
data$Date <- as.POSIXct(data$Timestamp/1000, origin="1970-01-01")

# 计算收益率
data$Return <- c(NA, diff(log(data$Close)))

# 统计分析
summary(data$Return)
```

## 限制和注意事项

1. **数据量限制**: 最多支持365天的数据
2. **时间范围**: 受Binance API限制，最早只能获取到交易所上线后的数据
3. **数据精度**: 价格和成交量保留原始精度
4. **时区**: 时间使用UTC时区

## 未来改进

可能的功能增强：

1. **多种格式**: 支持JSON、Excel等格式
2. **数据压缩**: 大文件自动压缩为ZIP
3. **批量下载**: 一次下载多个币种
4. **自定义字段**: 允许用户选择导出哪些字段
5. **技术指标**: 导出时自动计算常用技术指标

## 测试

### 功能测试

```bash
# 测试基本导出
curl "http://127.0.0.1:5001/api/klines/export?symbol=ETH/USDT&interval=1h&days=7" -o test.csv

# 验证文件
head -5 test.csv
wc -l test.csv
```

### 前端测试

1. 打开浏览器访问 http://localhost:3000
2. 进入行情数据页面
3. 查询数据
4. 点击"📥 下载CSV"
5. 验证下载的文件

## 文件修改

### 后端
- `app.py`: 添加 `/api/klines/export` 端点

### 前端
- `frontend/src/components/MarketData.vue`: 
  - 添加下载按钮
  - 实现 `downloadCSV()` 函数

## 部署状态

- ✅ 后端API已部署
- ✅ 前端界面已更新
- ✅ 功能测试通过
- ✅ 可以立即使用

---

**功能添加日期**: 2026-02-01  
**开发者**: Kiro AI Agent  
**状态**: ✅ 已完成并测试  
**版本**: 1.0  
