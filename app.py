"""Flask API server for market data layer."""

import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
from market_data_layer.adapter import BinanceDataSourceAdapter
from market_data_layer.cache import CacheManager
from market_data_layer.validator import KlineDataValidator
from market_data_layer.exceptions import (
    ParameterError,
    ValidationError,
    DataSourceError,
)
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
from wallet_auth import (
    WalletAuth,
    WhitelistManager,
    WalletAuthError,
    WhitelistError
)
from wallet_auth.exceptions import (
    InvalidSignatureError,
    TokenExpiredError,
    InvalidTokenError
)
from utils.price_utils import calculate_adaptive_price_range, calculate_grid_count, get_optimal_grid_spacing

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
adapter = BinanceDataSourceAdapter()
cache = CacheManager(max_size=1000, default_ttl=24 * 60 * 60 * 1000)
validator = KlineDataValidator()

# Initialize wallet authentication
whitelist_manager = WhitelistManager()
wallet_auth = WalletAuth(whitelist_manager)


def serialize_kline(kline):
    """Convert KlineData to dict for JSON serialization."""
    return {
        "timestamp": kline.timestamp,
        "open": kline.open,
        "high": kline.high,
        "low": kline.low,
        "close": kline.close,
        "volume": kline.volume,
    }


def require_auth(f):
    """Decorator to require wallet authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Missing authorization header"}), 401
        
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            public_key = wallet_auth.verify_token(token)
            
            # Add public_key to request context
            request.wallet_public_key = public_key
            return f(*args, **kwargs)
            
        except (TokenExpiredError, InvalidTokenError) as e:
            return jsonify({"error": str(e)}), 401
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return jsonify({"error": "Authentication failed"}), 401
    
    return decorated_function


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# Wallet Authentication Endpoints

@app.route("/api/auth/challenge", methods=["POST"])
def get_auth_challenge():
    """Get authentication challenge message for wallet signing.
    
    Request body:
    {
        "public_key": "wallet_public_key"
    }
    """
    try:
        data = request.get_json()
        public_key = data.get("public_key")
        
        if not public_key:
            return jsonify({"error": "Missing public_key"}), 400
        
        # Generate challenge message
        message = wallet_auth.generate_challenge_message(public_key)
        
        return jsonify({
            "message": message,
            "public_key": public_key
        })
    
    except Exception as e:
        logger.error(f"Challenge generation error: {e}")
        return jsonify({"error": "Failed to generate challenge"}), 500


@app.route("/api/auth/login", methods=["POST"])
def wallet_login():
    """Authenticate wallet with signature.
    
    Request body:
    {
        "public_key": "wallet_public_key",
        "message": "signed_message",
        "signature": "wallet_signature"
    }
    """
    try:
        data = request.get_json()
        public_key = data.get("public_key")
        message = data.get("message")
        signature = data.get("signature")
        
        if not all([public_key, message, signature]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Authenticate wallet
        wallet_user = wallet_auth.authenticate_wallet(public_key, message, signature)
        
        # Generate auth token
        auth_token = wallet_auth.generate_auth_token(public_key)
        
        return jsonify({
            "success": True,
            "token": auth_token.token,
            "expires_at": auth_token.expires_at.isoformat(),
            "user": wallet_user.to_dict()
        })
    
    except InvalidSignatureError as e:
        logger.warning(f"Invalid signature: {e}")
        return jsonify({"error": "Invalid wallet signature"}), 401
    except WhitelistError as e:
        logger.warning(f"Wallet not whitelisted: {e}")
        return jsonify({"error": "Wallet not authorized"}), 403
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"error": "Authentication failed"}), 500


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def wallet_logout():
    """Logout and revoke authentication token."""
    try:
        auth_header = request.headers.get('Authorization')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
        
        # Revoke token
        wallet_auth.revoke_token(token)
        
        return jsonify({"success": True, "message": "Logged out successfully"})
    
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({"error": "Logout failed"}), 500


@app.route("/api/auth/verify", methods=["GET"])
@require_auth
def verify_auth():
    """Verify current authentication status."""
    try:
        public_key = request.wallet_public_key
        wallet_info = whitelist_manager.get_wallet_info(public_key)
        
        return jsonify({
            "authenticated": True,
            "public_key": public_key,
            "wallet_info": wallet_info
        })
    
    except Exception as e:
        logger.error(f"Auth verification error: {e}")
        return jsonify({"error": "Verification failed"}), 500


@app.route("/api/auth/whitelist", methods=["GET"])
@require_auth
def get_whitelist():
    """Get whitelist information (admin only)."""
    try:
        public_key = request.wallet_public_key
        wallet_info = whitelist_manager.get_wallet_info(public_key)
        
        # Check if user is admin
        if not wallet_info or wallet_info.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        
        wallets = whitelist_manager.list_wallets()
        return jsonify({"wallets": wallets})
    
    except Exception as e:
        logger.error(f"Whitelist error: {e}")
        return jsonify({"error": "Failed to get whitelist"}), 500


@app.route("/api/symbols", methods=["GET"])
def get_symbols():
    """Get supported symbols."""
    try:
        symbols = adapter.get_supported_symbols()
        return jsonify({"symbols": symbols})
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/intervals", methods=["GET"])
def get_intervals():
    """Get supported intervals."""
    try:
        intervals = adapter.get_supported_intervals()
        return jsonify({"intervals": intervals})
    except Exception as e:
        logger.error(f"Error getting intervals: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/klines", methods=["GET"])
def get_klines():
    """Get K-line data.
    
    Query parameters:
    - symbol: Trading pair (e.g., "BTC/USDT")
    - interval: Time interval (e.g., "1h")
    - days: Number of days to fetch (default: 7)
    """
    try:
        symbol = request.args.get("symbol", "BTC/USDT")
        interval = request.args.get("interval", "1h")
        days = int(request.args.get("days", 7))
        
        # Validate parameters
        adapter.validate_parameters(symbol, interval, 0, 1)
        
        # Calculate time range
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        # Check cache first
        cache_key = f"{symbol}:{interval}:{start_time}:{end_time}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"Cache hit for {cache_key}")
            klines = cached_data
        else:
            logger.info(f"Fetching data for {symbol} {interval}")
            # Fetch from data source
            klines = adapter.fetch_kline_data(symbol, interval, start_time, end_time)
            
            # Validate data
            validation_results = validator.validate_batch(klines)
            invalid_count = sum(1 for r in validation_results if not r.isValid)
            
            if invalid_count > 0:
                logger.warning(f"Found {invalid_count} invalid K-lines")
            
            # Filter valid data
            valid_klines = [
                kline for kline, result in zip(klines, validation_results)
                if result.isValid
            ]
            
            # Cache the data
            cache.set(cache_key, valid_klines)
            klines = valid_klines
        
        # Serialize response
        kline_dicts = [serialize_kline(k) for k in klines]
        
        return jsonify({
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "count": len(kline_dicts),
            "data": kline_dicts,
        })
    
    except ParameterError as e:
        logger.error(f"Parameter error: {e}")
        return jsonify({"error": str(e)}), 400
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"error": str(e)}), 400
    except DataSourceError as e:
        logger.error(f"Data source error: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/cache/stats", methods=["GET"])
def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = cache.get_cache_info()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    """Clear the cache."""
    try:
        cache.clear()
        return jsonify({"message": "Cache cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/strategy/calculate-from-range", methods=["POST"])
def calculate_strategy_from_range():
    """Calculate strategy parameters from selected time range."""
    try:
        data = request.get_json()
        symbol = data.get('symbol', 'ETH/USDT')
        start_timestamp = data.get('start_timestamp')  # 选中区间的开始时间
        end_timestamp = data.get('end_timestamp')      # 选中区间的结束时间
        
        if not start_timestamp or not end_timestamp:
            return jsonify({'error': 'Start and end timestamps are required'}), 400
        
        # 获取选中区间的K线数据
        adapter = MarketDataAdapter()
        
        # 计算需要多少天的数据
        time_diff_ms = end_timestamp - start_timestamp
        days = max(1, int(time_diff_ms / (24 * 60 * 60 * 1000)) + 1)
        
        klines = adapter.get_klines(symbol, '4h', days)
        
        # 过滤出选中区间内的数据
        selected_klines = [
            kline for kline in klines 
            if start_timestamp <= kline.timestamp <= end_timestamp
        ]
        
        if not selected_klines:
            return jsonify({'error': 'No data found in selected range'}), 400
        
        # 计算参数
        high_prices = [kline.high for kline in selected_klines]
        low_prices = [kline.low for kline in selected_klines]
        
        historical_high = max(high_prices)
        historical_low = min(low_prices)
        entry_price = selected_klines[0].close  # 时间序列最早的价格
        current_price = selected_klines[-1].close  # 时间序列最晚的价格
        
        # 计算价格区间（向上向下取整到100的倍数）
        lower_price = math.floor(historical_low / 100) * 100
        upper_price = math.ceil(historical_high / 100) * 100
        
        # 计算网格数量（基于100的间距）
        grid_spacing = get_optimal_grid_spacing(symbol, current_price)
        grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
        
        result = {
            'selected_range': {
                'start_timestamp': start_timestamp,
                'end_timestamp': end_timestamp,
                'start_time': datetime.fromtimestamp(start_timestamp / 1000).isoformat(),
                'end_time': datetime.fromtimestamp(end_timestamp / 1000).isoformat(),
                'data_points': len(selected_klines)
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
        logger.error(f"Calculate from range error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/strategy/price-range", methods=["POST"])
def get_price_range():
    """Get calculated price range and grid count for a symbol.
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "days": 30
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ["symbol", "days"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        symbol = data["symbol"]
        days = int(data["days"])
        
        if days < 1 or days > 365:
            return jsonify({"error": "Days must be between 1 and 365"}), 400
        
        # Fetch K-line data
        logger.info(f"Calculating price range for {symbol}")
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        klines = adapter.fetch_kline_data(symbol, "1h", start_time, end_time)
        
        if not klines:
            return jsonify({"error": "No K-line data available"}), 404
        
        # Validate data
        validation_results = validator.validate_batch(klines)
        valid_klines = [
            kline for kline, result in zip(klines, validation_results)
            if result.isValid
        ]
        
        if not valid_klines:
            return jsonify({"error": "No valid K-line data"}), 400
        
        # Calculate price range
        lower_price, upper_price = calculate_adaptive_price_range(valid_klines)
        
        # Get current price for optimal spacing calculation
        current_price = valid_klines[-1].close
        grid_spacing = get_optimal_grid_spacing(symbol, current_price)
        
        # Calculate grid count
        grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
        
        # Calculate statistics
        high_prices = [kline.high for kline in valid_klines]
        low_prices = [kline.low for kline in valid_klines]
        earliest_price = valid_klines[0].close  # 时间序列最早的价格
        
        return jsonify({
            "symbol": symbol,
            "days": days,
            "data_points": len(valid_klines),
            "current_price": current_price,
            "historical_high": max(high_prices),
            "historical_low": min(low_prices),
            "earliest_price": earliest_price,  # 添加最早价格
            "calculated_range": {
                "lower_price": lower_price,
                "upper_price": upper_price,
                "grid_count": grid_count,
                "grid_spacing": grid_spacing,
                "price_range": upper_price - lower_price,
            },
            "grid_levels": [
                lower_price + i * grid_spacing 
                for i in range(grid_count)
            ][:10]  # Show first 10 levels as preview
        })
    
    except Exception as e:
        logger.error(f"Price range calculation error: {e}")
        return jsonify({"error": "Price range calculation failed"}), 500


@app.route("/api/strategy/backtest", methods=["POST"])
def backtest_strategy():
    """Backtest a grid strategy.
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "mode": "long",  # long, short, neutral
        "lower_price": 48000,  # optional, will auto-calculate if not provided
        "upper_price": 52000,  # optional, will auto-calculate if not provided
        "grid_count": 10,      # optional, will auto-calculate if not provided
        "initial_capital": 10000,
        "days": 30,
        "leverage": 1.0,  # leverage multiplier (optional, default 1.0)
        "funding_rate": 0.0,  # funding rate (optional, default 0.0)
        "funding_interval": 8,  # funding interval in hours (optional, default 8)
        "auto_calculate_range": true  # auto-calculate price range and grid count
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ["symbol", "mode", "initial_capital", "days"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse parameters
        symbol = data["symbol"]
        mode = StrategyMode(data["mode"])
        initial_capital = float(data["initial_capital"])
        days = int(data["days"])
        leverage = float(data.get("leverage", 1.0))
        funding_rate = float(data.get("funding_rate", 0.0))
        funding_interval = int(data.get("funding_interval", 8))
        auto_calculate_range = data.get("auto_calculate_range", True)
        
        # Validate basic parameters
        if initial_capital <= 0:
            return jsonify({"error": "Initial capital must be positive"}), 400
        
        if days < 1 or days > 365:
            return jsonify({"error": "Days must be between 1 and 365"}), 400
        
        if leverage <= 0 or leverage > 100:
            return jsonify({"error": "Leverage must be between 1x and 100x"}), 400
        
        if funding_rate < -0.01 or funding_rate > 0.01:
            return jsonify({"error": "Funding rate must be between -1% and 1%"}), 400
        
        if funding_interval <= 0 or funding_interval > 24:
            return jsonify({"error": "Funding interval must be between 1 and 24 hours"}), 400
        
        # Fetch K-line data first
        logger.info(f"Fetching K-line data for {symbol}")
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        klines = adapter.fetch_kline_data(symbol, "1h", start_time, end_time)
        
        if not klines:
            return jsonify({"error": "No K-line data available"}), 404
        
        # Validate data
        validation_results = validator.validate_batch(klines)
        valid_klines = [
            kline for kline, result in zip(klines, validation_results)
            if result.isValid
        ]
        
        if not valid_klines:
            return jsonify({"error": "No valid K-line data"}), 400
        
        # Calculate price range and grid count
        if auto_calculate_range:
            # Auto-calculate price range
            lower_price, upper_price = calculate_adaptive_price_range(valid_klines)
            
            # Get current price for optimal spacing calculation
            current_price = valid_klines[-1].close
            grid_spacing = get_optimal_grid_spacing(symbol, current_price)
            
            # Calculate grid count
            grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
            
            logger.info(f"Auto-calculated price range: {lower_price} - {upper_price}, grid count: {grid_count}, spacing: {grid_spacing}")
        else:
            # Use provided values
            lower_price = float(data.get("lower_price", 0))
            upper_price = float(data.get("upper_price", 0))
            grid_count = int(data.get("grid_count", 10))
            
            if lower_price <= 0 or upper_price <= 0:
                return jsonify({"error": "Prices must be positive when not auto-calculating"}), 400
            
            if lower_price >= upper_price:
                return jsonify({"error": "Lower price must be less than upper price"}), 400
            
            if grid_count < 2:
                return jsonify({"error": "Grid count must be at least 2"}), 400
        
        logger.info(f"Backtesting perpetual contract strategy with {len(valid_klines)} K-lines, leverage: {leverage}x, funding rate: {funding_rate}")
        
        # Create strategy config
        entry_price = float(data.get("entry_price", valid_klines[0].close))  # 默认使用第一个K线的收盘价
        
        config = StrategyConfig(
            symbol=symbol,
            mode=mode,
            lower_price=lower_price,
            upper_price=upper_price,
            grid_count=grid_count,
            initial_capital=initial_capital,
            fee_rate=0.0005,
            leverage=leverage,
            funding_rate=funding_rate,
            funding_interval=funding_interval,
            entry_price=entry_price,
        )
        
        # Execute strategy
        engine = GridStrategyEngine(config)
        result = engine.execute(valid_klines)
        
        # Add calculated parameters to result
        result_dict = result.to_dict()
        result_dict["calculated_params"] = {
            "lower_price": lower_price,
            "upper_price": upper_price,
            "grid_count": grid_count,
            "auto_calculated": auto_calculate_range,
            "grid_spacing": grid_spacing if auto_calculate_range else (upper_price - lower_price) / (grid_count - 1),
            "price_range": upper_price - lower_price,
        }
        
        return jsonify(result_dict)
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except ParameterError as e:
        logger.error(f"Parameter error: {e}")
        return jsonify({"error": str(e)}), 400
    except DataSourceError as e:
        logger.error(f"Data source error: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({"error": "Backtest failed"}), 500


@app.route("/api/backtest/run", methods=["POST"])
def run_backtest():
    """Run comprehensive backtest comparing long, short, and neutral strategies.
    
    Request body (same as strategy backtest except no mode parameter):
    {
        "symbol": "ETH/USDT",
        "lower_price": 48000,  # optional, will auto-calculate if not provided
        "upper_price": 52000,  # optional, will auto-calculate if not provided
        "grid_count": 10,      # optional, will auto-calculate if not provided
        "initial_capital": 10000,
        "days": 30,
        "leverage": 1.0,  # leverage multiplier (optional, default 1.0)
        "funding_rate": 0.0,  # funding rate (optional, default 0.0)
        "funding_interval": 8,  # funding interval in hours (optional, default 8)
        "auto_calculate_range": true  # auto-calculate price range and grid count
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters (same as strategy backtest except no mode)
        required_fields = ["symbol", "initial_capital", "days"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse parameters (same as strategy backtest)
        symbol = data["symbol"]
        initial_capital = float(data["initial_capital"])
        days = int(data["days"])
        leverage = float(data.get("leverage", 1.0))
        funding_rate = float(data.get("funding_rate", 0.0))
        funding_interval = int(data.get("funding_interval", 8))
        auto_calculate_range = data.get("auto_calculate_range", True)
        entry_price = float(data.get("entry_price", 0.0))  # Entry price parameter
        
        # Validate basic parameters (same as strategy backtest)
        if initial_capital <= 0:
            return jsonify({"error": "Initial capital must be positive"}), 400
        
        if days < 1 or days > 365:
            return jsonify({"error": "Days must be between 1 and 365"}), 400
        
        if leverage <= 0 or leverage > 100:
            return jsonify({"error": "Leverage must be between 1x and 100x"}), 400
        
        if funding_rate < -0.01 or funding_rate > 0.01:
            return jsonify({"error": "Funding rate must be between -1% and 1%"}), 400
        
        if funding_interval <= 0 or funding_interval > 24:
            return jsonify({"error": "Funding interval must be between 1 and 24 hours"}), 400
        
        # Fetch K-line data (same as strategy backtest)
        logger.info(f"Fetching K-line data for {symbol}")
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        klines = adapter.fetch_kline_data(symbol, "1h", start_time, end_time)
        
        if not klines:
            return jsonify({"error": "No K-line data available"}), 404
        
        # Validate data (same as strategy backtest)
        validation_results = validator.validate_batch(klines)
        valid_klines = [
            kline for kline, result in zip(klines, validation_results)
            if result.isValid
        ]
        
        if not valid_klines:
            return jsonify({"error": "No valid K-line data"}), 400
        
        # Calculate price range and grid count (same as strategy backtest)
        if auto_calculate_range:
            # Auto-calculate price range
            lower_price, upper_price = calculate_adaptive_price_range(valid_klines)
            
            # Get current price for optimal spacing calculation
            current_price = valid_klines[-1].close
            grid_spacing = get_optimal_grid_spacing(symbol, current_price)
            
            # Calculate grid count
            grid_count = calculate_grid_count(lower_price, upper_price, grid_spacing)
            
            logger.info(f"Auto-calculated price range: {lower_price} - {upper_price}, grid count: {grid_count}, spacing: {grid_spacing}")
        else:
            # Use provided values
            lower_price = float(data.get("lower_price", 0))
            upper_price = float(data.get("upper_price", 0))
            grid_count = int(data.get("grid_count", 10))
            
            if lower_price <= 0 or upper_price <= 0:
                return jsonify({"error": "Prices must be positive when not auto-calculating"}), 400
            
            if lower_price >= upper_price:
                return jsonify({"error": "Lower price must be less than upper price"}), 400
            
            if grid_count < 2:
                return jsonify({"error": "Grid count must be at least 2"}), 400
            
            grid_spacing = (upper_price - lower_price) / (grid_count - 1)
        
        logger.info(f"Running comparative backtest with {len(valid_klines)} K-lines, leverage: {leverage}x, funding rate: {funding_rate}")
        
        # Run backtest for all three strategies
        strategies = ["long", "short", "neutral"]
        results = {}
        
        for strategy_mode in strategies:
            logger.info(f"Running {strategy_mode} strategy backtest")
            
            # Create strategy config (same as strategy backtest)
            config = StrategyConfig(
                symbol=symbol,
                mode=StrategyMode(strategy_mode),
                lower_price=lower_price,
                upper_price=upper_price,
                grid_count=grid_count,
                initial_capital=initial_capital,
                fee_rate=0.0005,
                leverage=leverage,
                funding_rate=funding_rate,
                funding_interval=funding_interval,
                entry_price=entry_price if entry_price > 0 else valid_klines[0].close,  # Use earliest price if not provided
            )
            
            # Execute strategy
            engine = GridStrategyEngine(config)
            result = engine.execute(valid_klines)
            
            # Convert to dict and add calculated parameters (same as strategy backtest)
            result_dict = result.to_dict()
            result_dict["calculated_params"] = {
                "lower_price": lower_price,
                "upper_price": upper_price,
                "grid_count": grid_count,
                "auto_calculated": auto_calculate_range,
                "grid_spacing": grid_spacing,
                "price_range": upper_price - lower_price,
            }
            
            # Store result
            results[strategy_mode] = result_dict
        
        # Add comparison metrics
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
        
        # Prepare response
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
        
        return jsonify(response)
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except ParameterError as e:
        logger.error(f"Parameter error: {e}")
        return jsonify({"error": str(e)}), 400
    except DataSourceError as e:
        logger.error(f"Data source error: {e}")
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({"error": "Backtest failed"}), 500
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest/grid-search", methods=["POST"])
@require_auth
def grid_search_backtest():
    """Run grid search optimization.
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "mode": "long",
        "lower_price": 40000,
        "upper_price": 60000,
        "grid_count": 10,
        "initial_capital": 10000,
        "start_date": "2025-01-28",
        "end_date": "2026-01-28",
        "parameter_ranges": {
            "grid_count": [5, 10, 15, 20],
            "lower_price": [38000, 40000, 42000],
            "upper_price": [58000, 60000, 62000]
        },
        "metric": "total_return"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ["symbol", "mode", "lower_price", "upper_price",
                          "grid_count", "initial_capital", "start_date", "end_date",
                          "parameter_ranges"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Parse parameters
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
        
        # Create base config
        base_config = BacktestConfig(
            symbol=symbol,
            mode=mode,
            lower_price=lower_price,
            upper_price=upper_price,
            grid_count=grid_count,
            initial_capital=initial_capital,
            start_date=start_date,
            end_date=end_date,
            fee_rate=0.0005,
        )
        
        # Run grid search
        logger.info(f"Running grid search for {symbol}")
        backtest_engine = BacktestEngine(adapter)
        optimizer = GridSearchOptimizer(backtest_engine)
        result = optimizer.optimize(base_config, parameter_ranges, metric)
        
        # Return result
        return jsonify(result.to_dict())
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Grid search error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
