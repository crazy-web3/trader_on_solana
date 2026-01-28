"""Backtest Engine - Comprehensive backtesting framework."""

from backtest_engine.models import (
    BacktestConfig,
    BacktestResult,
    GridSearchResult,
    PerformanceMetrics,
    StrategyMode,
)
from backtest_engine.engine import BacktestEngine
from backtest_engine.grid_search import GridSearchOptimizer
from backtest_engine.exceptions import (
    BacktestException,
    InvalidConfigError,
    DataError,
)

__version__ = "0.1.0"

__all__ = [
    "BacktestConfig",
    "BacktestResult",
    "GridSearchResult",
    "PerformanceMetrics",
    "StrategyMode",
    "BacktestEngine",
    "GridSearchOptimizer",
    "BacktestException",
    "InvalidConfigError",
    "DataError",
]
