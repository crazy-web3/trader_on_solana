"""
策略回测相关API路由

提供网格交易策略回测、价格区间计算、参数优化等功能
支持做多、做空、中性三种网格交易策略的回测分析
"""

import logging
import math
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from strategy_engine import (
    GridStrategyEngine,
    StrategyConfig,
    StrategyMode,
)
from market_data_layer.exceptions import (
    ParameterError,
    ValidationError,
    DataSourceError,
)
from utils.price_utils import calculate_adaptive_price_range, calculate_grid_count, get_optimal_grid_spacing

# 创建蓝图
strategy_bp = Blueprint('strategy', __name__, url_prefix='/api/strategy')
logger = logging.getLogger(__name__)


def init_strategy_routes(adapter, validator, require_auth):
    """
    初始化策略回测路由
    
    Args:
        adapter: 数据源适配器
        validator: 数据验证器
        require_auth: 认证装饰器函数
    """

    @strategy_bp.route("/calculate-from-range", methods=["POST"])
    def calculate_strategy_from_range():
        """
        根据选定时间区间计算策略参数
        
        用户在前端图表上选择一个时间区间后，系统会分析该区间内的价格波动
        自动计算出适合的网格交易参数，包括价格区间、网格数量等
        
        请求体:
        {
            "symbol": "ETHUSDT",
            "start_timestamp": 1706889300000,  # 选中区间开始时间戳（毫秒）
            "end_timestamp": 1706975700000     # 选中区间结束时间戳（毫秒）
        }
        
        返回:
        {
            "selected_range": {
                "start_timestamp": 1706889300000,
                "end_timestamp": 1706975700000,
                "start_time": "2024-02-02T10:15:00",
                "end_time": "2024-02-03T10:15:00",
                "data_points": 24
            },
            "price_analysis": {
                "historical_high": 2650.0,
                "historical_low": 2580.0,
                "entry_price": 2600.0,
                "current_price": 2620.0,
                "price_range": 100.0
            },
            "calculated_params": {
                "lower_price": 2500.0,
                "upper_price": 2700.0,
                "grid_count": 10,
                "grid_spacing": 22.22,
                "entry_price": 2600.0
            }
        }
        """
        try:
            data = request.get_json()
            symbol = data.get('symbol', 'ETHUSDT')
            start_timestamp = data.get('start_timestamp')
            end_timestamp = data.get('end_timestamp')
            
            # 验证必需参数
            if not start_timestamp or not end_timestamp:
                return jsonify({'error': '缺少开始和结束时间戳参数'}), 400
            
            if start_timestamp >= end_timestamp:
                return jsonify({'error': '开始时间必须早于结束时间'}), 400
            
            # 计算时间范围并获取K线数据
            time_diff_ms = end_timestamp - start_timestamp
            days = max(1, int(time_diff_ms / (24 * 60 * 60 * 1000)) + 1)
            
            logger.info(f"根据选定区间计算策略参数: {symbol}, 时间范围: {days}天")
            
            # 获取K线数据（使用4小时周期获得更精确的分析）
            klines = adapter.fetch_kline_data(symbol, '4h', start_timestamp, end_timestamp)
            
            if not klines:
                return jsonify({'error': '未找到指定时间区间的数据'}), 404
            
            # 过滤出选中区间内的数据
            selected_klines = [
                kline for kline in klines 
                if start_timestamp <= kline.timestamp <= end_timestamp
            ]
            
            if not selected_klines:
                return jsonify({'error': '选定区间内没有有效数据'}), 400
            
            # 验证数据质量
            validation_results = validator.validate_batch(selected_klines)
            valid_klines = [
                kline for kline, result in zip(selected_klines, validation_results)
                if result.isValid
            ]
            
            if not valid_klines:
                return jsonify({'error': '选定区间内没有有效的K线数据'}), 400
            
            # 分析价格数据
            high_prices = [kline.high for kline in valid_klines]
            low_prices = [kline.low for kline in valid_klines]
            
            historical_high = max(high_prices)
            historical_low = min(low_prices)
            entry_price = valid_klines[0].close  # 时间序列最早的价格作为入场价格
            current_price = valid_klines[-1].close  # 时间序列最晚的价格
            
            # 计算价格区间（向上向下取整到合适的倍数）
            # 根据价格大小选择合适的取整单位
            if current_price > 10000:
                # 高价币种（如BTC），取整到1000
                round_unit = 1000
            elif current_price > 1000:
                # 中价币种（如ETH），取整到100
                round_unit = 100
            elif current_price > 100:
                # 低价币种，取整到10
                round_unit = 10
            else:
                # 极低价币种，取整到1
                round_unit = 1
            
            lower_price = math.floor(historical_low / round_unit) * round_unit
            upper_price = math.ceil(historical_high / round_unit) * round_unit
            
            # 计算最优网格间距和数量
            grid_spacing = get_optimal_grid_spacing(symbol, current_price)
            grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
            
            # 确保网格数量在合理范围内（5-50个网格）
            if grid_count < 5:
                grid_count = 5
                grid_spacing = (upper_price - lower_price) / (grid_count - 1)
            elif grid_count > 50:
                grid_count = 50
                grid_spacing = (upper_price - lower_price) / (grid_count - 1)
            
            logger.info(f"计算完成 - 价格区间: {lower_price}-{upper_price}, 网格数: {grid_count}, 间距: {grid_spacing:.2f}")
            
            result = {
                'selected_range': {
                    'start_timestamp': start_timestamp,
                    'end_timestamp': end_timestamp,
                    'start_time': datetime.fromtimestamp(start_timestamp / 1000).isoformat(),
                    'end_time': datetime.fromtimestamp(end_timestamp / 1000).isoformat(),
                    'data_points': len(valid_klines)
                },
                'price_analysis': {
                    'historical_high': historical_high,
                    'historical_low': historical_low,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'price_range': upper_price - lower_price
                },
                'calculated_params': {
                    'lower_price': lower_price,
                    'upper_price': upper_price,
                    'grid_count': grid_count,
                    'grid_spacing': grid_spacing,
                    'entry_price': entry_price
                }
            }
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"根据区间计算策略参数错误: {str(e)}")
            return jsonify({'error': f'计算失败: {str(e)}'}), 500

    @strategy_bp.route("/price-range", methods=["POST"])
    def get_price_range():
        """
        获取交易对的价格区间和网格数量计算
        
        基于历史数据分析，自动计算适合的网格交易价格区间
        考虑价格波动范围、当前价格位置等因素
        
        请求体:
        {
            "symbol": "BTCUSDT",
            "days": 30  # 分析的历史天数
        }
        
        返回:
        {
            "symbol": "BTCUSDT",
            "days": 30,
            "data_points": 720,
            "current_price": 42500.0,
            "historical_high": 45000.0,
            "historical_low": 40000.0,
            "earliest_price": 41000.0,
            "calculated_range": {
                "lower_price": 40000.0,
                "upper_price": 45000.0,
                "grid_count": 10,
                "grid_spacing": 555.56,
                "price_range": 5000.0
            },
            "grid_levels": [40000.0, 40555.56, 41111.12, ...]
        }
        """
        try:
            data = request.get_json()
            
            # 验证必需参数
            required_fields = ["symbol", "days"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"缺少必需字段: {field}"}), 400
            
            symbol = data["symbol"]
            days = int(data["days"])
            
            # 验证参数范围
            if days < 1 or days > 365:
                return jsonify({"error": "天数必须在1到365之间"}), 400
            
            logger.info(f"计算价格区间: {symbol}, 分析天数: {days}")
            
            # 获取K线数据
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            klines = adapter.fetch_kline_data(symbol, "1h", start_time, end_time)
            
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
            
            # 计算自适应价格区间
            lower_price, upper_price = calculate_adaptive_price_range(valid_klines)
            
            # 获取当前价格用于最优间距计算
            current_price = valid_klines[-1].close
            grid_spacing = get_optimal_grid_spacing(symbol, current_price)
            
            # 计算网格数量
            grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
            
            # 计算统计数据
            high_prices = [kline.high for kline in valid_klines]
            low_prices = [kline.low for kline in valid_klines]
            earliest_price = valid_klines[0].close  # 时间序列最早的价格
            
            # 生成网格价位预览（显示前10个价位）
            grid_levels = [
                lower_price + i * grid_spacing 
                for i in range(min(grid_count, 10))
            ]
            
            logger.info(f"价格区间计算完成 - 区间: {lower_price:.2f}-{upper_price:.2f}, 网格数: {grid_count}")
            
            return jsonify({
                "symbol": symbol,
                "days": days,
                "data_points": len(valid_klines),
                "current_price": current_price,
                "historical_high": max(high_prices),
                "historical_low": min(low_prices),
                "earliest_price": earliest_price,
                "calculated_range": {
                    "lower_price": lower_price,
                    "upper_price": upper_price,
                    "grid_count": grid_count,
                    "grid_spacing": grid_spacing,
                    "price_range": upper_price - lower_price,
                },
                "grid_levels": grid_levels
            })
        
        except Exception as e:
            logger.error(f"价格区间计算错误: {e}")
            return jsonify({"error": "价格区间计算失败"}), 500

    @strategy_bp.route("/backtest", methods=["POST"])
    def backtest_strategy():
        """
        执行网格交易策略回测
        
        对指定的网格交易策略进行历史数据回测
        支持做多、做空、中性三种策略模式
        支持杠杆交易和资金费率计算
        
        请求体:
        {
            "symbol": "BTCUSDT",
            "mode": "long",  # long(做多), short(做空), neutral(中性)
            "lower_price": 48000,  # 网格下边界价格（可选，自动计算）
            "upper_price": 52000,  # 网格上边界价格（可选，自动计算）
            "grid_count": 10,      # 网格数量（可选，自动计算）
            "initial_capital": 10000,  # 初始资金
            "days": 30,            # 回测天数
            "leverage": 1.0,       # 杠杆倍数（可选，默认1倍）
            "funding_rate": 0.0,   # 资金费率（可选，默认0）
            "funding_interval": 8, # 资金费率收取间隔小时数（可选，默认8小时）
            "entry_price": 50000,  # 入场价格（可选，默认使用第一个K线收盘价）
            "auto_calculate_range": true  # 是否自动计算价格区间和网格数量
        }
        
        返回:
        {
            "strategy_mode": "long",
            "symbol": "BTCUSDT",
            "initial_capital": 10000.0,
            "final_capital": 11500.0,
            "total_return": 0.15,
            "total_return_pct": 15.0,
            "total_trades": 45,
            "winning_trades": 30,
            "losing_trades": 15,
            "win_rate": 0.67,
            "max_drawdown": 500.0,
            "max_drawdown_pct": 5.0,
            "sharpe_ratio": 1.25,
            "equity_curve": [...],
            "trade_history": [...],
            "calculated_params": {
                "lower_price": 48000.0,
                "upper_price": 52000.0,
                "grid_count": 10,
                "grid_spacing": 444.44,
                "auto_calculated": true,
                "price_range": 4000.0
            }
        }
        """
        try:
            data = request.get_json()
            
            # 验证必需参数
            required_fields = ["symbol", "mode", "initial_capital", "days"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"缺少必需字段: {field}"}), 400
            
            # 解析参数
            symbol = data["symbol"]
            mode = StrategyMode(data["mode"])
            initial_capital = float(data["initial_capital"])
            days = int(data["days"])
            leverage = float(data.get("leverage", 1.0))
            funding_rate = float(data.get("funding_rate", 0.0))
            funding_interval = int(data.get("funding_interval", 8))
            auto_calculate_range = data.get("auto_calculate_range", True)
            
            # 验证基本参数
            if initial_capital <= 0:
                return jsonify({"error": "初始资金必须为正数"}), 400
            
            if days < 1 or days > 365:
                return jsonify({"error": "回测天数必须在1到365之间"}), 400
            
            if leverage <= 0 or leverage > 100:
                return jsonify({"error": "杠杆倍数必须在1到100倍之间"}), 400
            
            if funding_rate < -0.01 or funding_rate > 0.01:
                return jsonify({"error": "资金费率必须在-1%到1%之间"}), 400
            
            if funding_interval <= 0 or funding_interval > 24:
                return jsonify({"error": "资金费率间隔必须在1到24小时之间"}), 400
            
            logger.info(f"开始策略回测: {symbol} {mode.value}, 资金: {initial_capital}, 天数: {days}, 杠杆: {leverage}x")
            
            # 获取K线数据
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            klines = adapter.fetch_kline_data(symbol, "1h", start_time, end_time)
            
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
            
            # 计算价格区间和网格数量
            if auto_calculate_range:
                # 自动计算价格区间
                lower_price, upper_price = calculate_adaptive_price_range(valid_klines)
                
                # 获取当前价格用于最优间距计算
                current_price = valid_klines[-1].close
                grid_spacing = get_optimal_grid_spacing(symbol, current_price)
                
                # 计算网格数量
                grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
                
                logger.info(f"自动计算价格区间: {lower_price:.2f} - {upper_price:.2f}, 网格数: {grid_count}, 间距: {grid_spacing:.2f}")
            else:
                # 使用用户提供的参数
                lower_price = float(data.get("lower_price", 0))
                upper_price = float(data.get("upper_price", 0))
                grid_count = int(data.get("grid_count", 10))
                
                if lower_price <= 0 or upper_price <= 0:
                    return jsonify({"error": "未启用自动计算时，价格区间必须为正数"}), 400
                
                if lower_price >= upper_price:
                    return jsonify({"error": "下边界价格必须小于上边界价格"}), 400
                
                if grid_count < 2:
                    return jsonify({"error": "网格数量至少为2"}), 400
                
                grid_spacing = (upper_price - lower_price) / (grid_count - 1)
            
            # 创建策略配置
            entry_price = float(data.get("entry_price", valid_klines[0].close))
            
            config = StrategyConfig(
                symbol=symbol,
                mode=mode,
                lower_price=lower_price,
                upper_price=upper_price,
                grid_count=grid_count,
                initial_capital=initial_capital,
                fee_rate=0.0005,  # 0.05% 手续费率
                leverage=leverage,
                funding_rate=funding_rate,
                funding_interval=funding_interval,
                entry_price=entry_price,
            )
            
            logger.info(f"执行策略回测，使用 {len(valid_klines)} 个K线数据点")
            
            # 执行策略回测
            engine = GridStrategyEngine(config)
            result = engine.execute(valid_klines)
            
            # 将结果转换为字典并添加计算参数
            result_dict = result.to_dict()
            result_dict["calculated_params"] = {
                "lower_price": lower_price,
                "upper_price": upper_price,
                "grid_count": grid_count,
                "auto_calculated": auto_calculate_range,
                "grid_spacing": grid_spacing,
                "price_range": upper_price - lower_price,
            }
            
            logger.info(f"策略回测完成 - 总收益: {result.total_return:.2%}, 交易次数: {result.total_trades}")
            
            return jsonify(result_dict)
        
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
            logger.error(f"回测错误: {e}")
            return jsonify({"error": "策略回测失败"}), 500

    return strategy_bp