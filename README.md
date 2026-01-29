# trader_on_solana

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- Virtual environment (venv)

### Backend Setup & Run
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Configure wallet whitelist (optional)
python manage_whitelist.py add <wallet_address> --nickname "User Name" --role user

# Start backend server
python3 app.py
```
Backend runs on: **http://localhost:5001**

### Frontend Setup & Run
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if needed)
npm install

# Start frontend development server
npm run dev
```
Frontend runs on: **http://localhost:3000**

### Access the Application
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:5001
- **API Documentation**: Check endpoints in `app.py`
- **Wallet Authentication**: See `docs/WALLET_AUTH.md` for setup guide

### Wallet Setup
1. Install a Solana wallet (Phantom or Solflare)
2. Add your wallet address to the whitelist using `manage_whitelist.py`
3. Connect your wallet on the frontend to access trading features

### Available Features
- 📊 **Market Data**: Real-time K-line data from Binance API
- 📈 **Strategy Backtest**: Quick backtesting with configurable parameters
- 🔍 **Full Backtest**: Historical backtesting up to 3 years
- ⚙️ **Parameter Optimization**: Grid Search for optimal parameters
- 🔐 **Wallet Authentication**: Solana wallet login with whitelist control
- 💰 **Perpetual Contracts**: Support for leveraged trading with funding rates

---

## **一、项目背景**

**赛道**：交易与策略机器人（Trading & Strategy Bots）

**目标**：基于 Solana 链生态，构建一个可回测、可配置的永续合约网格交易机器人 MVP，支持杠杆交易和资金费率计算，用于学习与实践，不以收益承诺为导向。

**核心理念**：

- 真实行情数据 + 可解释策略
- 参数遍历回测（而非“拍脑袋”参数）
- MVP 优先，先跑通再打磨

---

## **二、整体方案概述**

### **1. 支持资产**

- BTC
- ETH
- SOL

### **2. 行情维度**

- K 线周期：15min / 1h / 4h / 1D
- 数据来源：
    - Jupiter / Solana 生态
    - TradingView（对齐验证）
    - OpenAPI 行情接口（自建封装）

### **3. 策略类型**

- 永续合约网格策略（方向可选）
    - 做多网格（杠杆1-100倍）
    - 做空网格（杠杆1-100倍）
    - 中性网格（双向交易）

### **4. 成本假设**

- 单边手续费：0.05%
- 资金费率：默认0%（可配置）
- 资金费率周期：8小时（可配置1-24小时）
- 回测中显式计入手续费、资金费用与滑点（MVP 简化为固定值）

---

## **三、功能拆解（MVP 范围）**

### **1. 行情模块（Data Layer）**

**功能**：

- 拉取历史 K 线
- 支持多周期、多币种

**输出**：

```
{
  "timestamp": 1234567890,
  "open": 0,
  "high": 0,
  "low": 0,
  "close": 0,
  "volume": 0
}
```

---

### **2. 策略引擎（Strategy Engine）**

**输入参数**：

- 价格区间（upper / lower）
- 网格数量（N）
- 方向（long / short / neutral）
- 初始资金

**核心逻辑**：

- 自动生成网格价位
- 逐根 K 线模拟成交
- 记录：
    - 成交次数
    - 盈亏曲线
    - 最大回撤

---

### **3. 回测模块（Backtest Engine）**

**回测范围**：

- 最近 3 年历史行情

**模式**：

- 单参数回测
- 参数遍历（Grid Search）

**输出指标**：

- 总收益率
- 年化收益
- 最大回撤
- 手续费占比

---

### **4. 前端界面（Frontend MVP）**

**功能**：

- 网格参数配置面板
- K 线图展示
- 回测结果可视化

**核心组件**：

- TradingView Chart
- 参数输入（区间 / 网格数 / 方向）
- 结果表格 + 简单曲线

---

## **四、技术选型建议**

| **模块** | **技术建议** |
| --- | --- |
| 行情 API | Jupiter API + 自建封装 |
| 回测引擎 | Node.js / Python（偏快速验证） |
| 前端 | React + TradingView Chart |
| 区块链交互 | Solana Web3.js（预留） |
| 部署 | tryNoah.ai / Vercel |

---

## **五、团队分工建议**

### **角色 1：行情 & 回测工程师**

- 行情 API 封装
- K 线数据清洗
- 回测核心逻辑实现

### **角色 2：策略 & 参数研究**

- 网格策略建模
- 参数区间设计
- 回测结果分析

### **角色 3：前端 & 产品**

- 网格参数 UI
- 回测结果可视化
- Demo 体验优化

---

## **六、开发节奏（黑客松节奏）**

### **Day 1**

- 明确策略公式
- 跑通历史 K 线拉取

### **Day 2**

- 完成基础网格回测
- 输出第一版结果

### **Day 3**

- 接入前端
- Demo 可操作

### **Day 4（加分项）**

- 参数遍历
- 不同币种横向对比

---

## **七、MVP 交付物**

- ✅ 可运行的网格回测 Demo
- ✅ 参数可配置
- ✅ 清晰的策略说明文档
- ✅ 一份学习导向的黑客松展示

---

## **八、后续可扩展方向（非本次必做）**

- 实盘交易（Solana 合约）
- 动态区间 / ATR 网格
- 多策略对比
- 链上数据因子（Funding / OI）

---

**项目定位总结**：

> 用真实数据，把“网格策略到底怎么赚/怎么亏”讲清楚。
>
