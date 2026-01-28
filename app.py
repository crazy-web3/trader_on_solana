"""Flask API server for market data layer."""

from flask import Flask, jsonify, request
from flask_cors import CORS
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
import logging
from datetime import datetime, timedelta

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


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


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


@app.route("/api/strategy/backtest", methods=["POST"])
def backtest_strategy():
    """Backtest a grid strategy.
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "mode": "long",  # long, short, neutral
        "lower_price": 48000,
        "upper_price": 52000,
        "grid_count": 10,
        "initial_capital": 10000,
        "days": 30
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ["symbol", "mode", "lower_price", "upper_price", 
                          "grid_count", "initial_capital", "days"]
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
        days = int(data["days"])
        
        # Validate parameters
        if lower_price <= 0 or upper_price <= 0:
            return jsonify({"error": "Prices must be positive"}), 400
        
        if lower_price >= upper_price:
            return jsonify({"error": "Lower price must be less than upper price"}), 400
        
        if grid_count < 2:
            return jsonify({"error": "Grid count must be at least 2"}), 400
        
        if initial_capital <= 0:
            return jsonify({"error": "Initial capital must be positive"}), 400
        
        if days < 1 or days > 365:
            return jsonify({"error": "Days must be between 1 and 365"}), 400
        
        # Fetch K-line data
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
        
        logger.info(f"Backtesting strategy with {len(valid_klines)} K-lines")
        
        # Create strategy config
        config = StrategyConfig(
            symbol=symbol,
            mode=mode,
            lower_price=lower_price,
            upper_price=upper_price,
            grid_count=grid_count,
            initial_capital=initial_capital,
            fee_rate=0.0005,
        )
        
        # Execute strategy
        engine = GridStrategyEngine(config)
        result = engine.execute(valid_klines)
        
        # Return result
        return jsonify(result.to_dict())
    
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
    """Run a comprehensive backtest with historical data.
    
    Request body:
    {
        "symbol": "BTC/USDT",
        "mode": "long",
        "lower_price": 40000,
        "upper_price": 60000,
        "grid_count": 10,
        "initial_capital": 10000,
        "start_date": "2025-01-28",
        "end_date": "2026-01-28"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required parameters
        required_fields = ["symbol", "mode", "lower_price", "upper_price",
                          "grid_count", "initial_capital", "start_date", "end_date"]
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
        
        # Create backtest config
        config = BacktestConfig(
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
        
        # Run backtest
        logger.info(f"Running backtest for {symbol} from {start_date} to {end_date}")
        backtest_engine = BacktestEngine(adapter)
        result = backtest_engine.run_backtest(config)
        
        # Return result
        return jsonify(result.to_dict())
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest/grid-search", methods=["POST"])
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
