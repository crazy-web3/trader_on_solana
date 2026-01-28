#!/bin/bash

# 启动脚本 - 运行后端API服务

echo "🚀 启动行情数据层 API 服务..."
echo ""
echo "📋 说明:"
echo "  - 后端 API 运行在: http://localhost:5000"
echo "  - 前端页面: 在浏览器中打开 index.html"
echo ""
echo "⚙️  安装依赖 (如果需要):"
echo "  pip install -r requirements.txt"
echo ""
echo "🔗 API 端点:"
echo "  - GET  /api/health          - 健康检查"
echo "  - GET  /api/symbols         - 获取支持的币种"
echo "  - GET  /api/intervals       - 获取支持的时间周期"
echo "  - GET  /api/klines          - 获取K线数据"
echo "  - GET  /api/cache/stats     - 获取缓存统计"
echo "  - POST /api/cache/clear     - 清空缓存"
echo ""
echo "📊 查询示例:"
echo "  curl 'http://localhost:5000/api/klines?symbol=BTC/USDT&interval=1h&days=7'"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，创建中..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -q -r requirements.txt

# 运行Flask应用
python app.py
