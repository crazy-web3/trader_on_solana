"""
合约网格交易系统 - Flask API 服务器

提供市场数据获取、策略回测、钱包认证等功能的RESTful API服务
支持做多、做空、中性三种网格交易策略的回测和优化

主要功能模块：
- 钱包认证：支持Web3钱包签名认证和白名单管理
- 市场数据：从币安获取K线数据，支持缓存和数据验证
- 策略回测：网格交易策略的历史数据回测分析
- 回测引擎：综合回测和参数优化功能
"""

import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS

# 导入核心组件
from market_data_layer.adapter import BinanceDataSourceAdapter
from market_data_layer.cache import CacheManager
from market_data_layer.validator import KlineDataValidator
from wallet_auth import WalletAuth, WhitelistManager

# 导入路由模块
from api.auth_routes import init_auth_routes
from api.market_routes import init_market_routes
from api.strategy_routes import init_strategy_routes
from api.backtest_routes import init_backtest_routes

# 创建Flask应用实例
app = Flask(__name__)

# 配置CORS跨域访问
# 允许前端（通常运行在3000/3001端口）访问后端API
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],  # 允许所有来源（生产环境应限制具体域名）
        "methods": ["GET", "POST", "OPTIONS"],  # 允许的HTTP方法
        "allow_headers": ["Content-Type"],  # 允许的请求头
        "supports_credentials": True  # 支持携带认证信息
    }
})

# 配置日志系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化核心组件
adapter = BinanceDataSourceAdapter()  # 币安数据源适配器
cache = CacheManager(max_size=1000, default_ttl=24 * 60 * 60 * 1000)  # 缓存管理器，默认24小时过期
validator = KlineDataValidator()  # K线数据验证器

# 初始化钱包认证系统
whitelist_manager = WhitelistManager()  # 白名单管理器
wallet_auth = WalletAuth(whitelist_manager)  # 钱包认证管理器

# 初始化路由模块
auth_bp, require_auth = init_auth_routes(wallet_auth, whitelist_manager)
market_bp = init_market_routes(adapter, cache, validator)
strategy_bp = init_strategy_routes(adapter, validator, require_auth)
backtest_bp = init_backtest_routes(adapter, validator, require_auth)

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(market_bp)
app.register_blueprint(strategy_bp)
app.register_blueprint(backtest_bp)

@app.route("/api/health", methods=["GET"])
def health():
    """
    健康检查接口
    
    用于检查API服务器的运行状态
    前端可以通过此接口确认后端服务是否正常运行
    
    返回:
        JSON响应，包含状态和时间戳
    """
    return jsonify({
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "message": "合约网格交易系统API服务正常运行"
    })


if __name__ == "__main__":
    logger.info("启动合约网格交易系统API服务器...")
    logger.info("服务地址: http://0.0.0.0:5001")
    logger.info("健康检查: http://0.0.0.0:5001/api/health")
    app.run(debug=True, host="0.0.0.0", port=5001)
