"""
合约网格交易系统 - Flask API 服务器

提供市场数据获取、策略回测、钱包认证等功能的RESTful API服务
支持做多、做空、中性三种网格交易策略的回测和优化

主要功能模块：
- 钱包认证：支持Web3钱包签名认证和白名单管理
- 市场数据：从币安获取K线数据，支持缓存和数据验证
- 策略回测：网格交易策略的历史数据回测分析
- 回测引擎：综合回测和参数优化功能

API文档：
- Swagger UI: http://localhost:5001/docs/
- OpenAPI JSON: http://localhost:5001/swagger.json
"""

import logging
from datetime import datetime
from flask import Flask, jsonify, redirect
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


@app.route("/")
def index():
    """
    根路径重定向到API文档
    
    访问根路径时自动跳转到API文档页面
    方便开发者快速查看API接口列表
    """
    return jsonify({
        "message": "合约网格交易系统API服务",
        "version": "1.0.0",
        "health": "/api/health",
        "endpoints": {
            "auth": "/api/auth/*",
            "market": "/api/*",
            "strategy": "/api/strategy/*", 
            "backtest": "/api/backtest/*"
        }
    })


@app.route("/swagger.json")
def swagger_json():
    """
    OpenAPI规范JSON文件
    
    提供符合OpenAPI 3.0规范的API文档JSON
    可以导入到Apifox、Postman等API客户端工具
    """
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "合约网格交易系统 API",
            "version": "1.0.0",
            "description": "提供网格交易策略回测和分析功能的RESTful API",
            "contact": {
                "name": "合约网格交易系统开发团队",
                "email": "dev@gridtrading.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "servers": [
            {
                "url": "http://localhost:5001",
                "description": "开发环境"
            }
        ],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "在请求头中添加JWT令牌: Bearer <token>"
                }
            },
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "错误信息"
                        }
                    }
                },
                "KlineData": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "integer", "description": "时间戳（毫秒）"},
                        "open": {"type": "number", "description": "开盘价"},
                        "high": {"type": "number", "description": "最高价"},
                        "low": {"type": "number", "description": "最低价"},
                        "close": {"type": "number", "description": "收盘价"},
                        "volume": {"type": "number", "description": "成交量"}
                    }
                },
                "StrategyBacktestRequest": {
                    "type": "object",
                    "required": ["symbol", "mode", "initial_capital", "days"],
                    "properties": {
                        "symbol": {"type": "string", "example": "BTCUSDT"},
                        "mode": {"type": "string", "enum": ["long", "short", "neutral"]},
                        "initial_capital": {"type": "number", "minimum": 100},
                        "days": {"type": "integer", "minimum": 1, "maximum": 365},
                        "leverage": {"type": "number", "minimum": 1.0, "maximum": 100.0, "default": 1.0},
                        "funding_rate": {"type": "number", "minimum": -0.01, "maximum": 0.01, "default": 0.0},
                        "auto_calculate_range": {"type": "boolean", "default": True}
                    }
                }
            }
        },
        "paths": {
            "/api/health": {
                "get": {
                    "summary": "健康检查",
                    "description": "检查API服务器的运行状态",
                    "responses": {
                        "200": {
                            "description": "服务正常",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "timestamp": {"type": "string"},
                                            "message": {"type": "string"},
                                            "version": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/klines": {
                "get": {
                    "summary": "获取K线数据",
                    "description": "根据交易对、时间间隔和天数获取历史K线数据",
                    "parameters": [
                        {
                            "name": "symbol",
                            "in": "query",
                            "description": "交易对",
                            "required": False,
                            "schema": {"type": "string", "default": "BTCUSDT"}
                        },
                        {
                            "name": "interval",
                            "in": "query",
                            "description": "时间间隔",
                            "required": False,
                            "schema": {"type": "string", "enum": ["15m", "1h", "4h", "1d", "1w"], "default": "1h"}
                        },
                        {
                            "name": "days",
                            "in": "query",
                            "description": "获取天数",
                            "required": False,
                            "schema": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "成功返回K线数据",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "symbol": {"type": "string"},
                                            "interval": {"type": "string"},
                                            "data": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/KlineData"}
                                            },
                                            "count": {"type": "integer"},
                                            "start_time": {"type": "integer"},
                                            "end_time": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "参数错误",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/strategy/backtest": {
                "post": {
                    "summary": "执行网格交易策略回测",
                    "description": "对指定的网格交易策略进行历史数据回测",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/StrategyBacktestRequest"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "回测成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "strategy_mode": {"type": "string"},
                                            "symbol": {"type": "string"},
                                            "initial_capital": {"type": "number"},
                                            "final_capital": {"type": "number"},
                                            "total_return": {"type": "number"},
                                            "total_trades": {"type": "integer"},
                                            "win_rate": {"type": "number"}
                                        }
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "参数错误",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Error"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/auth/challenge": {
                "post": {
                    "summary": "获取认证挑战消息",
                    "description": "为指定的钱包公钥生成一个需要签名的挑战消息",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["public_key"],
                                    "properties": {
                                        "public_key": {
                                            "type": "string",
                                            "description": "钱包公钥",
                                            "example": "0x1234567890abcdef..."
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "成功生成挑战消息",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "message": {"type": "string"},
                                            "public_key": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/auth/login": {
                "post": {
                    "summary": "钱包登录认证",
                    "description": "验证用户的钱包签名并生成JWT认证令牌",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["public_key", "message", "signature"],
                                    "properties": {
                                        "public_key": {"type": "string"},
                                        "message": {"type": "string"},
                                        "signature": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "登录成功",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "success": {"type": "boolean"},
                                            "token": {"type": "string"},
                                            "expires_at": {"type": "string"},
                                            "user": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "security": [
            {
                "BearerAuth": []
            }
        ]
    }
    
    return jsonify(openapi_spec)


@app.route("/docs/")
def docs():
    """
    API文档页面
    
    提供API接口的简单文档说明
    """
    return jsonify({
        "title": "合约网格交易系统 API 文档",
        "version": "1.0.0",
        "description": "提供网格交易策略回测和分析功能的RESTful API",
        "base_url": "http://localhost:5001",
        "swagger_json": "http://localhost:5001/swagger.json",
        "openapi_spec": "OpenAPI 3.0.0",
        "endpoints": {
            "认证接口": {
                "POST /api/auth/challenge": "获取认证挑战消息",
                "POST /api/auth/login": "钱包登录认证",
                "GET /api/auth/verify": "验证认证令牌",
                "GET /api/auth/whitelist": "获取白名单用户列表",
                "POST /api/auth/logout": "用户登出"
            },
            "市场数据接口": {
                "GET /api/symbols": "获取支持的交易对列表",
                "GET /api/intervals": "获取支持的时间间隔列表",
                "GET /api/klines": "获取K线数据",
                "GET /api/cache/stats": "获取缓存统计信息",
                "POST /api/cache/clear": "清空缓存"
            },
            "策略回测接口": {
                "POST /api/strategy/calculate-from-range": "根据选定时间区间计算策略参数",
                "POST /api/strategy/price-range": "获取交易对的价格区间和网格数量计算",
                "POST /api/strategy/backtest": "执行网格交易策略回测"
            },
            "回测引擎接口": {
                "POST /api/backtest/run": "运行综合回测分析",
                "POST /api/backtest/grid-search": "运行网格搜索优化"
            }
        },
        "examples": {
            "获取K线数据": "GET /api/klines?symbol=ETHUSDT&interval=4h&days=30",
            "策略回测": "POST /api/strategy/backtest",
            "综合回测": "POST /api/backtest/run"
        }
    })


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
        "message": "合约网格交易系统API服务正常运行",
        "version": "1.0.0"
    })


if __name__ == "__main__":
    logger.info("启动合约网格交易系统API服务器...")
    logger.info("服务地址: http://0.0.0.0:5001")
    logger.info("健康检查: http://0.0.0.0:5001/api/health")
    logger.info("API文档: http://0.0.0.0:5001/docs/")
    logger.info("Swagger JSON: http://0.0.0.0:5001/swagger.json")
    app.run(debug=True, host="0.0.0.0", port=5001)
