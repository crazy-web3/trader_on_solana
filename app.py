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
import logging
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

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


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
