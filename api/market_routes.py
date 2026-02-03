"""
市场数据相关API路由

提供K线数据获取、交易对查询、缓存管理等功能
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from market_data_layer.exceptions import (
    ParameterError,
    ValidationError,
    DataSourceError,
)

# 创建蓝图
market_bp = Blueprint('market', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def serialize_kline(kline):
    """
    将K线数据对象转换为字典格式，用于JSON序列化
    
    Args:
        kline: KlineData对象，包含K线的各项数据
        
    Returns:
        dict: 包含K线数据的字典，可直接用于JSON响应
    """
    return {
        "timestamp": kline.timestamp,  # 时间戳（毫秒）
        "open": kline.open,           # 开盘价
        "high": kline.high,           # 最高价
        "low": kline.low,             # 最低价
        "close": kline.close,         # 收盘价
        "volume": kline.volume,       # 成交量
    }


def init_market_routes(adapter, cache, validator):
    """
    初始化市场数据路由
    
    Args:
        adapter: 数据源适配器
        cache: 缓存管理器
        validator: 数据验证器
    """

    @market_bp.route("/symbols", methods=["GET"])
    def get_symbols():
        """
        获取支持的交易对列表
        
        返回系统支持的所有加密货币交易对
        前端可以使用这些交易对进行K线数据查询和策略回测
        
        返回:
        {
            "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        }
        """
        # 支持的交易对列表
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        return jsonify({"symbols": symbols})

    @market_bp.route("/intervals", methods=["GET"])
    def get_intervals():
        """
        获取支持的时间间隔列表
        
        返回K线数据支持的所有时间间隔
        用于前端选择不同的时间周期进行数据分析
        
        返回:
        {
            "intervals": ["15m", "1h", "4h", "1d"]
        }
        """
        # 支持的时间间隔列表
        intervals = ["15m", "1h", "4h", "1d"]
        return jsonify({"intervals": intervals})

    @market_bp.route("/klines", methods=["GET"])
    def get_klines():
        """
        获取K线数据
        
        从币安API获取指定交易对和时间范围的K线数据
        支持缓存机制，提高数据获取效率
        
        请求参数:
            symbol (必需): 交易对，如 "BTCUSDT"
            interval (必需): 时间间隔，如 "1d"
            start_time (可选): 开始时间戳（毫秒）
            end_time (可选): 结束时间戳（毫秒）
            limit (可选): 数据条数限制，默认500
        
        返回:
        {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "data": [
                {
                    "timestamp": 1706889300000,
                    "open": 42000.0,
                    "high": 43000.0,
                    "low": 41000.0,
                    "close": 42500.0,
                    "volume": 1234.56
                }
            ]
        }
        """
        try:
            # 获取请求参数
            symbol = request.args.get("symbol")
            interval = request.args.get("interval")
            start_time = request.args.get("start_time", type=int)
            end_time = request.args.get("end_time", type=int)
            limit = request.args.get("limit", default=500, type=int)

            # 验证必需参数
            if not symbol or not interval:
                return jsonify({"error": "缺少必需参数: symbol 和 interval"}), 400

            # 验证交易对
            supported_symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
            if symbol not in supported_symbols:
                return jsonify({"error": f"不支持的交易对: {symbol}"}), 400

            # 验证时间间隔
            supported_intervals = ["15m", "1h", "4h", "1d"]
            if interval not in supported_intervals:
                return jsonify({"error": f"不支持的时间间隔: {interval}"}), 400

            # 设置默认时间范围（如果未提供）
            if not end_time:
                end_time = int(datetime.now().timestamp() * 1000)
            
            if not start_time:
                # 默认获取最近30天的数据
                start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)

            # 验证时间范围
            if start_time >= end_time:
                return jsonify({"error": "开始时间必须早于结束时间"}), 400

            # 限制数据量（防止请求过大的数据集）
            max_limit = 1000
            if limit > max_limit:
                limit = max_limit

            logger.info(f"获取K线数据: {symbol} {interval} {start_time}-{end_time} limit={limit}")

            # 从数据源获取K线数据
            klines = adapter.fetch_kline_data(
                symbol=symbol,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
                limit=limit
            )

            if not klines:
                return jsonify({
                    "symbol": symbol,
                    "interval": interval,
                    "data": [],
                    "message": "未找到数据"
                })

            # 验证数据质量
            validation_results = validator.validate_batch(klines)
            valid_klines = [
                kline for kline, result in zip(klines, validation_results)
                if result.isValid
            ]

            # 序列化数据
            serialized_data = [serialize_kline(kline) for kline in valid_klines]

            return jsonify({
                "symbol": symbol,
                "interval": interval,
                "data": serialized_data,
                "count": len(serialized_data),
                "start_time": start_time,
                "end_time": end_time
            })

        except ParameterError as e:
            logger.warning(f"参数错误: {e}")
            return jsonify({"error": f"参数错误: {str(e)}"}), 400
        except ValidationError as e:
            logger.warning(f"数据验证错误: {e}")
            return jsonify({"error": f"数据验证失败: {str(e)}"}), 400
        except DataSourceError as e:
            logger.error(f"数据源错误: {e}")
            return jsonify({"error": f"数据获取失败: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"获取K线数据时发生未知错误: {e}")
            return jsonify({"error": "服务器内部错误"}), 500

    @market_bp.route("/cache/stats", methods=["GET"])
    def get_cache_stats():
        """
        获取缓存统计信息
        
        返回缓存的使用情况，包括命中率、大小等信息
        用于监控系统性能和缓存效果
        
        返回:
        {
            "size": 150,
            "max_size": 1000,
            "hit_rate": 0.85,
            "total_requests": 1000,
            "cache_hits": 850
        }
        """
        try:
            stats = cache.get_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return jsonify({"error": "获取缓存统计失败"}), 500

    @market_bp.route("/cache/clear", methods=["POST"])
    def clear_cache():
        """
        清空缓存
        
        清除所有缓存的数据，强制重新从数据源获取
        通常用于调试或数据更新后的缓存刷新
        
        返回:
        {
            "message": "缓存清理成功",
            "cleared_items": 150
        }
        """
        try:
            cleared_count = cache.clear()
            logger.info(f"缓存已清理，清除了 {cleared_count} 个项目")
            return jsonify({
                "message": "缓存清理成功",
                "cleared_items": cleared_count
            })
        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return jsonify({"error": "清理缓存失败"}), 500

    return market_bp