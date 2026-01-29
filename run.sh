#!/bin/bash

# 启动脚本 - 运行完整的交易系统

echo "🚀 启动交易系统..."
echo ""
echo "📋 说明:"
echo "  - 后端 API 运行在: http://localhost:5001"
echo "  - 前端界面运行在: http://localhost:3000"
echo ""
echo "⚙️  安装依赖 (如果需要):"
echo "  pip install -r requirements.txt"
echo "  cd frontend && npm install"
echo ""
echo "🔗 主要功能:"
echo "  - 📊 行情数据 - 实时K线图表"
echo "  - 📈 策略回测 - 网格策略回测"
echo "  - 🔍 完整回测 - 多策略对比"
echo "  - ⚡ 参数优化 - 需要钱包连接"
echo "  - 🔐 钱包认证 - Solana钱包登录"
echo "  - 🎨 深色主题 - 支持主题切换"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，创建中..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装后端依赖
echo "📦 安装后端依赖..."
pip install -q -r requirements.txt

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 安装前端依赖..."
    cd frontend
    npm install
    cd ..
fi

# 启动后端服务（后台运行）
echo "🚀 启动后端服务..."
python3 app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 3

# 启动前端服务
echo "🚀 启动前端服务..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# 等待用户中断
echo ""
echo "✅ 系统启动完成!"
echo "   - 前端: http://localhost:3000"
echo "   - 后端: http://localhost:5001"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获中断信号，清理进程
trap 'echo ""; echo "🛑 正在停止服务..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT

# 等待
wait
