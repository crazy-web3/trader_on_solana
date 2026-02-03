"""
回测引擎相关API路由

提供综合回测、网格搜索优化等高级回测功能
支持多策略对比分析和参数优化
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from strategy_engine import (
    GridStrategyEngine,
    StrategyConfig,
    StrategyMode,
)
from backtest_engine import (
    BacktestEngine,
    GridSearchOptimizer,
    BacktestConfig,
)
from market_data_layer.exceptions import (
    ParameterError,
    ValidationError,
    DataSourceError,
)
from utils.price_utils import calculate_adaptive_price_range, calculate_grid_count, get_optimal_grid_spacing

# 创建蓝图
backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')
logger = logging.getLogger(__name__)


def init_backtest_routes(adapter, validator, require_auth):
    """
    初始化回测引擎路由
    
    Args:
        adapter: 数据源适配器
        validator: 数据验证器
        require_auth: 认证装饰器函数
    """

    @backtest_bp.route("/run", methods=["POST"])
    def run_backtest():
        """
        运行综合回测分析
        
        同时对做多、做空、中性三种策略进行回测
        提供策略间的对比分析，帮助用户选择最优策略
        
        请求体（与单策略回测相同，但不需要mode参数）:
        {
            "symbol": "ETHUSDT",
            "lower_price": 2400,   # 可选，自动计算
            "upper_price": 2800,   # 可选，自动计算
            "grid_count": 10,      # 可选，自动计算
            "initial_capital": 10000,
            "days": 30,
            "leverage": 1.0,       # 杠杆倍数（可选，默认1倍）
            "funding_rate": 0.0,   # 资金费率（可选，默认0）
            "funding_interval": 8, # 资金费率间隔（可选，默认8小时）
            "entry_price": 2600,   # 入场价格（可选）
            "auto_calculate_range": true
        }
        
        返回:
        {
            "symbol": "ETHUSDT",
            "backtest_period": {
                "days": 30,
                "data_points": 720,
                "start_time": 1706889300000,
                "end_time": 1706975700000
            },
            "parameters": {
                "lower_price": 2400.0,
                "upper_price": 2800.0,
                "grid_count": 10,
                "grid_spacing": 44.44,
                "initial_capital": 10000.0,
                "leverage": 1.0,
                "funding_rate": 0.0,
                "funding_interval": 8,
                "entry_price": 2600.0,
                "auto_calculated": true,
                "price_range": 400.0
            },
            "strategies": {
                "long": {策略回测结果},
                "short": {策略回测结果},
                "neutral": {策略回测结果}
            },
            "comparison": {
                "best_strategy": "long",
                "worst_strategy": "short",
                "returns_comparison": {
                    "long": 0.15,
                    "short": -0.05,
                    "neutral": 0.08
                },
                "final_capital_comparison": {...},
                "total_trades_comparison": {...},
                "win_rate_comparison": {...},
                "max_drawdown_comparison": {...}
            }
        }
        """
        try:
            data = request.get_json()
            
            # 验证必需参数（与单策略回测相同，但不需要mode）
            required_fields = ["symbol", "initial_capital", "days"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"缺少必需字段: {field}"}), 400
            
            # 解析参数
            symbol = data["symbol"]
            initial_capital = float(data["initial_capital"])
            days = int(data["days"])
            leverage = float(data.get("leverage", 1.0))
            funding_rate = float(data.get("funding_rate", 0.0))
            funding_interval = int(data.get("funding_interval", 8))
            auto_calculate_range = data.get("auto_calculate_range", True)
            entry_price = float(data.get("entry_price", 0.0))
            
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
            
            logger.info(f"开始综合回测: {symbol}, 资金: {initial_capital}, 天数: {days}, 杠杆: {leverage}x")
            
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
            
            logger.info(f"运行综合回测，使用 {len(valid_klines)} 个K线数据点，杠杆: {leverage}x，资金费率: {funding_rate}")
            
            # 对三种策略分别进行回测
            strategies = ["long", "short", "neutral"]
            results = {}
            
            for strategy_mode in strategies:
                logger.info(f"执行 {strategy_mode} 策略回测")
                
                # 创建策略配置
                config = StrategyConfig(
                    symbol=symbol,
                    mode=StrategyMode(strategy_mode),
                    lower_price=lower_price,
                    upper_price=upper_price,
                    grid_count=grid_count,
                    initial_capital=initial_capital,
                    fee_rate=0.0005,  # 0.05% 手续费率
                    leverage=leverage,
                    funding_rate=funding_rate,
                    funding_interval=funding_interval,
                    entry_price=entry_price if entry_price > 0 else valid_klines[0].close,
                )
                
                # 执行策略回测
                engine = GridStrategyEngine(config)
                result = engine.execute(valid_klines)
                
                # 转换为字典并添加计算参数
                result_dict = result.to_dict()
                result_dict["calculated_params"] = {
                    "lower_price": lower_price,
                    "upper_price": upper_price,
                    "grid_count": grid_count,
                    "auto_calculated": auto_calculate_range,
                    "grid_spacing": grid_spacing,
                    "price_range": upper_price - lower_price,
                }
                
                # 存储结果
                results[strategy_mode] = result_dict
                logger.info(f"{strategy_mode} 策略完成 - 收益: {result.total_return:.2%}, 交易: {result.total_trades}次")
            
            # 添加对比分析
            comparison = {
                "best_strategy": max(results.keys(), key=lambda k: results[k]["total_return"]),
                "worst_strategy": min(results.keys(), key=lambda k: results[k]["total_return"]),
                "returns_comparison": {
                    strategy: results[strategy]["total_return"] 
                    for strategy in strategies
                },
                "final_capital_comparison": {
                    strategy: results[strategy]["final_capital"] 
                    for strategy in strategies
                },
                "total_trades_comparison": {
                    strategy: results[strategy]["total_trades"] 
                    for strategy in strategies
                },
                "win_rate_comparison": {
                    strategy: results[strategy]["win_rate"] 
                    for strategy in strategies
                },
                "max_drawdown_comparison": {
                    strategy: results[strategy]["max_drawdown_pct"] 
                    for strategy in strategies
                }
            }
            
            # 准备响应数据
            response = {
                "symbol": symbol,
                "backtest_period": {
                    "days": days,
                    "data_points": len(valid_klines),
                    "start_time": start_time,
                    "end_time": end_time
                },
                "parameters": {
                    "lower_price": lower_price,
                    "upper_price": upper_price,
                    "grid_count": grid_count,
                    "grid_spacing": grid_spacing,
                    "initial_capital": initial_capital,
                    "leverage": leverage,
                    "funding_rate": funding_rate,
                    "funding_interval": funding_interval,
                    "entry_price": entry_price if entry_price > 0 else valid_klines[0].close,
                    "auto_calculated": auto_calculate_range,
                    "price_range": upper_price - lower_price
                },
                "strategies": results,
                "comparison": comparison
            }
            
            logger.info(f"综合回测完成 - 最佳策略: {comparison['best_strategy']}")
            
            return jsonify(response)
        
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
            logger.error(f"综合回测错误: {e}")
            return jsonify({"error": "综合回测失败"}), 500

    @backtest_bp.route("/grid-search", methods=["POST"])
    @require_auth
    def grid_search_backtest():
        """
        运行网格搜索优化
        
        对策略参数进行网格搜索，找到最优的参数组合
        支持多个参数的同时优化，如网格数量、价格区间等
        
        请求体:
        {
            "symbol": "BTCUSDT",
            "mode": "long",
            "lower_price": 40000,
            "upper_price": 60000,
            "grid_count": 10,
            "initial_capital": 10000,
            "start_date": "2025-01-28",
            "end_date": "2026-01-28",
            "parameter_ranges": {
                "grid_count": [5, 10, 15, 20],        # 要测试的网格数量
                "lower_price": [38000, 40000, 42000], # 要测试的下边界价格
                "upper_price": [58000, 60000, 62000]  # 要测试的上边界价格
            },
            "metric": "total_return"  # 优化目标指标
        }
        
        返回:
        {
            "optimization_results": {
                "best_params": {
                    "grid_count": 15,
                    "lower_price": 40000,
                    "upper_price": 60000
                },
                "best_score": 0.25,
                "total_combinations": 36,
                "completed_combinations": 36
            },
            "parameter_analysis": {
                "grid_count_impact": {...},
                "price_range_impact": {...}
            },
            "detailed_results": [
                {
                    "params": {...},
                    "score": 0.25,
                    "backtest_result": {...}
                }
            ]
        }
        """
        try:
            data = request.get_json()
            
            # 验证必需参数
            required_fields = ["symbol", "mode", "lower_price", "upper_price",
                              "grid_count", "initial_capital", "start_date", "end_date",
                              "parameter_ranges"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"缺少必需字段: {field}"}), 400
            
            # 解析参数
            symbol = data["symbol"]
            mode = StrategyMode(data["mode"])
            lower_price = float(data["lower_price"])
            upper_price = float(data["upper_price"])
            grid_count = int(data["grid_count"])
            initial_capital = float(data["initial_capital"])
            start_date = data["start_date"]
            end_date = data["end_date"]
            parameter_ranges = data["parameter_ranges"]
            metric = data.get("metric", "total_return")
            
            # 验证参数范围
            if initial_capital <= 0:
                return jsonify({"error": "初始资金必须为正数"}), 400
            
            if lower_price >= upper_price:
                return jsonify({"error": "下边界价格必须小于上边界价格"}), 400
            
            if grid_count < 2:
                return jsonify({"error": "网格数量至少为2"}), 400
            
            # 验证参数范围格式
            if not isinstance(parameter_ranges, dict):
                return jsonify({"error": "parameter_ranges必须是字典格式"}), 400
            
            # 验证优化指标
            valid_metrics = ["total_return", "sharpe_ratio", "win_rate", "max_drawdown_pct"]
            if metric not in valid_metrics:
                return jsonify({"error": f"优化指标必须是以下之一: {valid_metrics}"}), 400
            
            logger.info(f"开始网格搜索优化: {symbol} {mode.value}, 指标: {metric}")
            logger.info(f"参数范围: {parameter_ranges}")
            
            # 创建基础配置
            base_config = BacktestConfig(
                symbol=symbol,
                mode=mode,
                lower_price=lower_price,
                upper_price=upper_price,
                grid_count=grid_count,
                initial_capital=initial_capital,
                start_date=start_date,
                end_date=end_date,
                fee_rate=0.0005,  # 0.05% 手续费率
            )
            
            # 运行网格搜索
            logger.info(f"运行网格搜索优化: {symbol}")
            backtest_engine = BacktestEngine(adapter)
            optimizer = GridSearchOptimizer(backtest_engine)
            result = optimizer.optimize(base_config, parameter_ranges, metric)
            
            logger.info(f"网格搜索完成 - 最佳参数: {result.best_params}, 最佳得分: {result.best_score:.4f}")
            
            # 返回结果
            return jsonify(result.to_dict())
        
        except ValueError as e:
            logger.error(f"参数错误: {e}")
            return jsonify({"error": f"参数错误: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"网格搜索错误: {e}")
            return jsonify({"error": f"网格搜索失败: {str(e)}"}), 500

    return backtest_bp