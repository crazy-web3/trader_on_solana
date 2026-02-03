"""
Swagger API文档配置

使用Flask-RESTX为合约网格交易系统生成Swagger API文档
支持导入到Apifox、Postman等API客户端工具
"""

from flask_restx import Api, fields
from flask import Blueprint

# 创建API文档蓝图
api_doc = Blueprint('api_doc', __name__)

# 配置Swagger API文档
api = Api(
    api_doc,
    version='1.0.0',
    title='合约网格交易系统 API',
    description='''
    ## 合约网格交易系统 RESTful API 文档
    
    本系统提供完整的网格交易策略回测和分析功能，支持：
    
    ### 🔐 认证功能
    - Web3钱包签名认证
    - JWT令牌管理
    - 白名单权限控制
    
    ### 📊 市场数据
    - 币安K线数据获取
    - 多时间周期支持
    - 智能缓存机制
    
    ### 🤖 策略回测
    - 做多/做空/中性网格策略
    - 自动参数计算
    - 历史数据回测分析
    
    ### 🔍 高级分析
    - 多策略对比回测
    - 网格搜索参数优化
    - 详细性能指标
    
    ### 📝 使用说明
    1. 大部分接口需要钱包认证，请先调用认证接口获取token
    2. 在请求头中添加 `Authorization: Bearer <token>`
    3. 所有时间戳使用毫秒级Unix时间戳
    4. 价格和金额使用浮点数格式
    
    ### 🌐 服务地址
    - 开发环境: http://localhost:5001
    - 健康检查: http://localhost:5001/api/health
    ''',
    doc='/docs/',  # Swagger UI 路径
    prefix='/api',
    contact='合约网格交易系统开发团队',
    contact_email='dev@gridtrading.com',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT',
    authorizations={
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': '在请求头中添加JWT令牌: Bearer <token>'
        }
    },
    security='Bearer'
)

# ==================== 数据模型定义 ====================

# 基础响应模型
base_response = api.model('BaseResponse', {
    'status': fields.String(description='响应状态', example='ok'),
    'message': fields.String(description='响应消息', example='操作成功'),
    'timestamp': fields.String(description='响应时间戳', example='2026-02-03T10:00:00')
})

# 错误响应模型
error_response = api.model('ErrorResponse', {
    'error': fields.String(description='错误信息', example='参数错误')
})

# 健康检查响应模型
health_response = api.model('HealthResponse', {
    'status': fields.String(description='服务状态', example='ok'),
    'timestamp': fields.String(description='响应时间戳', example='2026-02-03T10:00:00'),
    'message': fields.String(description='状态消息', example='合约网格交易系统API服务正常运行'),
    'version': fields.String(description='版本号', example='1.0.0'),
    'docs': fields.String(description='文档地址', example='/docs/'),
    'swagger_json': fields.String(description='Swagger JSON地址', example='/swagger.json')
})

# K线数据模型
kline_data = api.model('KlineData', {
    'timestamp': fields.Integer(description='时间戳（毫秒）', example=1706889300000),
    'open': fields.Float(description='开盘价', example=42000.0),
    'high': fields.Float(description='最高价', example=43000.0),
    'low': fields.Float(description='最低价', example=41000.0),
    'close': fields.Float(description='收盘价', example=42500.0),
    'volume': fields.Float(description='成交量', example=1234.56)
})

# 认证相关模型
auth_challenge_request = api.model('AuthChallengeRequest', {
    'public_key': fields.String(required=True, description='钱包公钥', example='0x1234567890abcdef...')
})

auth_challenge_response = api.model('AuthChallengeResponse', {
    'message': fields.String(description='需要签名的挑战消息', example='Please sign this message to authenticate: 1706889300'),
    'public_key': fields.String(description='钱包公钥', example='0x1234567890abcdef...')
})

auth_login_request = api.model('AuthLoginRequest', {
    'public_key': fields.String(required=True, description='钱包公钥', example='0x1234567890abcdef...'),
    'message': fields.String(required=True, description='挑战消息', example='Please sign this message to authenticate: 1706889300'),
    'signature': fields.String(required=True, description='签名', example='0xabcdef1234567890...')
})

auth_login_response = api.model('AuthLoginResponse', {
    'success': fields.Boolean(description='登录是否成功', example=True),
    'token': fields.String(description='JWT认证令牌', example='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'),
    'expires_at': fields.String(description='令牌过期时间', example='2026-02-04T10:00:00'),
    'user': fields.Raw(description='用户信息')
})

auth_verify_response = api.model('AuthVerifyResponse', {
    'authenticated': fields.Boolean(description='是否已认证', example=True),
    'public_key': fields.String(description='用户钱包公钥', example='0x1234567890abcdef...'),
    'wallet_info': fields.Raw(description='钱包信息')
})

whitelist_response = api.model('WhitelistResponse', {
    'wallets': fields.List(fields.Raw, description='白名单用户列表')
})

# 市场数据相关模型
symbols_response = api.model('SymbolsResponse', {
    'symbols': fields.List(fields.String, description='支持的交易对列表', example=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'])
})

intervals_response = api.model('IntervalsResponse', {
    'intervals': fields.List(fields.String, description='支持的时间间隔列表', example=['15m', '1h', '4h', '1d'])
})

klines_response = api.model('KlinesResponse', {
    'symbol': fields.String(description='交易对', example='BTCUSDT'),
    'interval': fields.String(description='时间间隔', example='1h'),
    'data': fields.List(fields.Nested(kline_data), description='K线数据列表'),
    'count': fields.Integer(description='数据条数', example=24),
    'start_time': fields.Integer(description='开始时间戳', example=1706889300000),
    'end_time': fields.Integer(description='结束时间戳', example=1706975700000)
})

cache_stats_response = api.model('CacheStatsResponse', {
    'size': fields.Integer(description='缓存大小', example=150),
    'max_size': fields.Integer(description='最大缓存大小', example=1000),
    'hit_rate': fields.Float(description='命中率', example=0.85),
    'total_requests': fields.Integer(description='总请求数', example=1000),
    'cache_hits': fields.Integer(description='缓存命中数', example=850)
})

# 策略回测相关模型
calculate_from_range_request = api.model('CalculateFromRangeRequest', {
    'symbol': fields.String(required=True, description='交易对', example='ETHUSDT'),
    'start_timestamp': fields.Integer(required=True, description='选中区间开始时间戳（毫秒）', example=1706889300000),
    'end_timestamp': fields.Integer(required=True, description='选中区间结束时间戳（毫秒）', example=1706975700000)
})

calculate_from_range_response = api.model('CalculateFromRangeResponse', {
    'selected_range': fields.Raw(description='选中区间信息'),
    'price_analysis': fields.Raw(description='价格分析结果'),
    'calculated_params': fields.Raw(description='计算的策略参数')
})

price_range_request = api.model('PriceRangeRequest', {
    'symbol': fields.String(required=True, description='交易对', example='BTCUSDT'),
    'days': fields.Integer(required=True, description='分析天数', example=30, min=1, max=365)
})

price_range_response = api.model('PriceRangeResponse', {
    'symbol': fields.String(description='交易对', example='BTCUSDT'),
    'days': fields.Integer(description='分析天数', example=30),
    'data_points': fields.Integer(description='数据点数量', example=720),
    'current_price': fields.Float(description='当前价格', example=42500.0),
    'historical_high': fields.Float(description='历史最高价', example=45000.0),
    'historical_low': fields.Float(description='历史最低价', example=40000.0),
    'earliest_price': fields.Float(description='最早价格', example=41000.0),
    'calculated_range': fields.Raw(description='计算的价格区间参数'),
    'grid_levels': fields.List(fields.Float, description='网格价位预览')
})

strategy_backtest_request = api.model('StrategyBacktestRequest', {
    'symbol': fields.String(required=True, description='交易对', example='BTCUSDT'),
    'mode': fields.String(required=True, description='策略模式', enum=['long', 'short', 'neutral'], example='long'),
    'initial_capital': fields.Float(required=True, description='初始资金', example=10000.0, min=100),
    'days': fields.Integer(required=True, description='回测天数', example=30, min=1, max=365),
    'lower_price': fields.Float(description='网格下边界价格（可选）', example=40000.0),
    'upper_price': fields.Float(description='网格上边界价格（可选）', example=45000.0),
    'grid_count': fields.Integer(description='网格数量（可选）', example=10, min=2, max=100),
    'leverage': fields.Float(description='杠杆倍数', example=1.0, min=1.0, max=100.0),
    'funding_rate': fields.Float(description='资金费率', example=0.0, min=-0.01, max=0.01),
    'funding_interval': fields.Integer(description='资金费率间隔（小时）', example=8, min=1, max=24),
    'entry_price': fields.Float(description='入场价格（可选）', example=42000.0),
    'auto_calculate_range': fields.Boolean(description='是否自动计算价格区间', example=True)
})

strategy_backtest_response = api.model('StrategyBacktestResponse', {
    'strategy_mode': fields.String(description='策略模式', example='long'),
    'symbol': fields.String(description='交易对', example='BTCUSDT'),
    'initial_capital': fields.Float(description='初始资金', example=10000.0),
    'final_capital': fields.Float(description='最终资金', example=11500.0),
    'total_return': fields.Float(description='总收益率', example=0.15),
    'total_return_pct': fields.Float(description='总收益率百分比', example=15.0),
    'total_trades': fields.Integer(description='总交易次数', example=45),
    'winning_trades': fields.Integer(description='盈利交易次数', example=30),
    'losing_trades': fields.Integer(description='亏损交易次数', example=15),
    'win_rate': fields.Float(description='胜率', example=0.67),
    'max_drawdown': fields.Float(description='最大回撤', example=500.0),
    'max_drawdown_pct': fields.Float(description='最大回撤百分比', example=5.0),
    'sharpe_ratio': fields.Float(description='夏普比率', example=1.25),
    'equity_curve': fields.List(fields.Raw, description='权益曲线数据'),
    'trade_history': fields.List(fields.Raw, description='交易历史记录'),
    'calculated_params': fields.Raw(description='计算的参数')
})

# 综合回测相关模型
comprehensive_backtest_request = api.model('ComprehensiveBacktestRequest', {
    'symbol': fields.String(required=True, description='交易对', example='BTCUSDT'),
    'initial_capital': fields.Float(required=True, description='初始资金', example=10000.0, min=100),
    'days': fields.Integer(required=True, description='回测天数', example=30, min=1, max=365),
    'lower_price': fields.Float(description='网格下边界价格（可选）', example=40000.0),
    'upper_price': fields.Float(description='网格上边界价格（可选）', example=45000.0),
    'grid_count': fields.Integer(description='网格数量（可选）', example=10, min=2, max=100),
    'leverage': fields.Float(description='杠杆倍数', example=1.0, min=1.0, max=100.0),
    'funding_rate': fields.Float(description='资金费率', example=0.0, min=-0.01, max=0.01),
    'funding_interval': fields.Integer(description='资金费率间隔（小时）', example=8, min=1, max=24),
    'entry_price': fields.Float(description='入场价格（可选）', example=42000.0),
    'auto_calculate_range': fields.Boolean(description='是否自动计算价格区间', example=True)
})

comprehensive_backtest_response = api.model('ComprehensiveBacktestResponse', {
    'symbol': fields.String(description='交易对', example='BTCUSDT'),
    'backtest_period': fields.Raw(description='回测周期信息'),
    'parameters': fields.Raw(description='回测参数'),
    'strategies': fields.Raw(description='各策略回测结果'),
    'comparison': fields.Raw(description='策略对比分析')
})

# 网格搜索相关模型
grid_search_request = api.model('GridSearchRequest', {
    'symbol': fields.String(required=True, description='交易对', example='BTCUSDT'),
    'mode': fields.String(required=True, description='策略模式', enum=['long', 'short', 'neutral'], example='long'),
    'lower_price': fields.Float(required=True, description='网格下边界价格', example=40000.0),
    'upper_price': fields.Float(required=True, description='网格上边界价格', example=60000.0),
    'grid_count': fields.Integer(required=True, description='网格数量', example=10),
    'initial_capital': fields.Float(required=True, description='初始资金', example=10000.0),
    'start_date': fields.String(required=True, description='开始日期', example='2025-01-28'),
    'end_date': fields.String(required=True, description='结束日期', example='2026-01-28'),
    'parameter_ranges': fields.Raw(required=True, description='参数范围', example={
        'grid_count': [5, 10, 15, 20],
        'lower_price': [38000, 40000, 42000],
        'upper_price': [58000, 60000, 62000]
    }),
    'metric': fields.String(description='优化目标指标', example='total_return', enum=['total_return', 'sharpe_ratio', 'win_rate', 'max_drawdown_pct'])
})

grid_search_response = api.model('GridSearchResponse', {
    'optimization_results': fields.Raw(description='优化结果'),
    'parameter_analysis': fields.Raw(description='参数分析'),
    'detailed_results': fields.List(fields.Raw, description='详细结果列表')
})

# 导出所有模型，供路由模块使用
__all__ = [
    'api', 'api_doc',
    'base_response', 'error_response', 'health_response', 'kline_data',
    'auth_challenge_request', 'auth_challenge_response',
    'auth_login_request', 'auth_login_response', 'auth_verify_response', 'whitelist_response',
    'symbols_response', 'intervals_response', 'klines_response', 'cache_stats_response',
    'calculate_from_range_request', 'calculate_from_range_response',
    'price_range_request', 'price_range_response',
    'strategy_backtest_request', 'strategy_backtest_response',
    'comprehensive_backtest_request', 'comprehensive_backtest_response',
    'grid_search_request', 'grid_search_response'
]