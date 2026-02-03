"""Market Data Layer - A module for managing K-line data from multiple sources."""

from market_data_layer.models import (
    KlineData,
    CacheEntry,
    ValidationResult,
    TimeInterval,
)
from market_data_layer.exceptions import (
    MarketDataLayerException,
    DataSourceError,
    ValidationError,
    ParameterError,
    TimeoutError,
    CacheError,
)
from market_data_layer.adapter import (
    DataSourceAdapter,
    MockDataSourceAdapter,
    BinanceDataSourceAdapter,
)

__version__ = "0.1.0"

__all__ = [
    "KlineData",
    "CacheEntry",
    "ValidationResult",
    "TimeInterval",
    "MarketDataLayerException",
    "DataSourceError",
    "ValidationError",
    "ParameterError",
    "TimeoutError",
    "CacheError",
    "DataSourceAdapter",
    "MockDataSourceAdapter",
    "BinanceDataSourceAdapter",
]
