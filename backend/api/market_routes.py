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
        adapter: 数据源适配器，用于获取K线数据
        cache: 缓存管理器，用于缓存K线数据提高性能
        validator: 数据验证器，用于验证K线数据质量
    """
    
    # 创建市场数据蓝图
    market_bp = Blueprint('market', __name__, url_prefix='/api')

    @market_bp.route("/symbols", methods=["GET"])
    def get_symbols():
        """
        获取支持的交易对列表
        
        返回系统支持的所有加密货币交易对
        这些交易对可以用于K线数据查询和策略回测
        
        返回:
            JSON响应，包含交易对列表
        """
        try:
            # 返回常用的加密货币交易对
            symbols = [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT",
                "XRPUSDT", "DOTUSDT", "DOGEUSDT", "AVAXUSDT", "SHIBUSDT",
                "MATICUSDT", "LTCUSDT", "UNIUSDT", "LINKUSDT", "ATOMUSDT"
            ]
            
            logger.info(f"返回 {len(symbols)} 个支持的交易对")
            
            return jsonify({
                "symbols": symbols
            })
        
        except Exception as e:
            logger.error(f"获取交易对列表错误: {e}")
            return jsonify({"error": "获取交易对列表失败"}), 500

    @market_bp.route("/intervals", methods=["GET"])
    def get_intervals():
        """
        获取支持的时间间隔列表
        
        返回K线数据支持的所有时间间隔
        用户可以根据需要选择不同的时间粒度进行分析
        
        返回:
            JSON响应，包含时间间隔列表
        """
        try:
            # 返回支持的K线时间间隔
            intervals = ["15m", "1h", "4h", "1d", "1w"]
            
            logger.info(f"返回 {len(intervals)} 个支持的时间间隔")
            
            return jsonify({
                "intervals": intervals
            })
        
        except Exception as e:
            logger.error(f"获取时间间隔列表错误: {e}")
            return jsonify({"error": "获取时间间隔列表失败"}), 500

    @market_bp.route("/klines", methods=["GET"])
    def get_klines():
        """
        获取K线数据
        
        根据交易对、时间间隔和天数获取历史K线数据
        支持缓存机制，提高数据获取效率
        
        查询参数:
            symbol: 交易对，如 BTCUSDT
            interval: 时间间隔，如 1h, 4h, 1d
            days: 获取天数，1-365天
        
        返回:
            JSON响应，包含K线数据数组
        """
        try:
            # 获取查询参数
            symbol = request.args.get('symbol', 'BTCUSDT')
            interval = request.args.get('interval', '1h')
            days = int(request.args.get('days', 30))
            
            # 转换符号格式：ETHUSDT -> ETH/USDT
            if '/' not in symbol:
                # 常见的转换规则
                if symbol.endswith('USDT'):
                    base = symbol[:-4]  # 移除USDT
                    symbol_formatted = f"{base}/USDT"
                elif symbol.endswith('BTC'):
                    base = symbol[:-3]  # 移除BTC
                    symbol_formatted = f"{base}/BTC"
                else:
                    symbol_formatted = symbol
            else:
                symbol_formatted = symbol
            
            # 验证参数
            if days < 1 or days > 365:
                return jsonify({"error": "天数必须在1到365之间"}), 400
            
            # 支持的时间间隔
            valid_intervals = ["15m", "1h", "4h", "1d", "1w"]
            if interval not in valid_intervals:
                return jsonify({"error": f"时间间隔必须是以下之一: {valid_intervals}"}), 400
            
            logger.info(f"获取K线数据: {symbol} -> {symbol_formatted}, 间隔: {interval}, 天数: {days}")
            
            # 计算时间范围
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            # 尝试从缓存获取数据
            cache_key = f"klines_{symbol}_{interval}_{days}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"从缓存返回K线数据: {symbol}")
                return jsonify(cached_data)
            
            # 从数据源获取K线数据
            klines = adapter.fetch_kline_data(symbol_formatted, interval, start_time, end_time)
            
            if not klines:
                return jsonify({"error": "无法获取K线数据"}), 404
            
            # 验证数据质量
            validation_results = validator.validate_batch(klines)
            valid_klines = [
                kline for kline, result in zip(klines, validation_results)
                if result.isValid
            ]
            
            if not valid_klines:
                return jsonify({"error": "没有有效的K线数据"}), 400
            
            # 序列化K线数据
            serialized_klines = [serialize_kline(kline) for kline in valid_klines]
            
            # 准备响应数据
            response_data = {
                "symbol": symbol,  # 返回原始格式
                "interval": interval,
                "data": serialized_klines,
                "count": len(serialized_klines),
                "start_time": start_time,
                "end_time": end_time
            }
            
            # 缓存数据（缓存1小时）
            cache.set(cache_key, response_data, ttl=60 * 60 * 1000)
            
            logger.info(f"返回 {len(serialized_klines)} 条K线数据")
            
            return jsonify(response_data)
        
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": f"参数错误: {str(e)}"}), 400
        except ParameterError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": str(e)}), 400
        except DataSourceError as e:
            logger.error(f"数据源错误: {e}")
            return jsonify({"error": str(e)}), 503
        except Exception as e:
            logger.error(f"获取K线数据错误: {e}")
            return jsonify({"error": "获取K线数据失败"}), 500

    @market_bp.route("/cache/stats", methods=["GET"])
    def get_cache_stats():
        """
        获取缓存统计信息
        
        返回缓存的使用情况，包括大小、命中率等指标
        用于监控系统性能和缓存效果
        
        返回:
            JSON响应，包含缓存统计数据
        """
        try:
            stats = cache.get_stats()
            
            logger.info("返回缓存统计信息")
            
            return jsonify({
                "size": stats["size"],
                "max_size": stats["max_size"],
                "hit_rate": stats["hit_rate"],
                "total_requests": stats["total_requests"],
                "cache_hits": stats["cache_hits"]
            })
        
        except Exception as e:
            logger.error(f"获取缓存统计错误: {e}")
            return jsonify({"error": "获取缓存统计失败"}), 500

    @market_bp.route("/cache/clear", methods=["POST"])
    def clear_cache():
        """
        清空缓存
        
        清除所有缓存的K线数据
        在数据更新或系统维护时使用
        
        返回:
            JSON响应，确认缓存已清空
        """
        try:
            cache.clear()
            
            logger.info("缓存已清空")
            
            return jsonify({
                "status": "ok",
                "message": "缓存已清空",
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            logger.error(f"清空缓存错误: {e}")
            return jsonify({"error": "清空缓存失败"}), 500

    return market_bp