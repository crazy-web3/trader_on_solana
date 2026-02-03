"""
API路由模块

包含合约网格交易系统的所有API路由模块：
- auth_routes: 钱包认证相关路由
- market_routes: 市场数据相关路由  
- strategy_routes: 策略回测相关路由
- backtest_routes: 回测引擎相关路由

每个模块都使用Flask蓝图(Blueprint)组织，便于模块化管理和扩展。
"""

__version__ = "1.0.0"
__author__ = "合约网格交易系统开发团队"