"""Data models for backtest engine."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class StrategyMode(str, Enum):
    """Strategy mode."""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class BacktestConfig:
    """Backtest configuration.
    
    Attributes:
        symbol: Trading pair symbol
        mode: Strategy mode
        lower_price: Lower price boundary
        upper_price: Upper price boundary
        grid_count: Number of grid levels
        initial_capital: Initial capital
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        fee_rate: Trading fee rate
        leverage: Leverage multiplier
        funding_rate: Funding rate for perpetual contracts
        funding_interval: Funding interval in hours
    """
    symbol: str
    mode: StrategyMode
    lower_price: float
    upper_price: float
    grid_count: int
    initial_capital: float
    start_date: str
    end_date: str
    fee_rate: float = 0.0005
    leverage: float = 1.0
    funding_rate: float = 0.0
    funding_interval: int = 8


@dataclass
class PerformanceMetrics:
    """Performance metrics for backtest result.
    
    Attributes:
        total_return: Total return percentage
        annual_return: Annualized return percentage
        max_drawdown: Maximum drawdown percentage
        sharpe_ratio: Sharpe ratio
        win_rate: Win rate percentage
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        fee_cost: Total fee cost
        fee_ratio: Fee cost as percentage of initial capital
        funding_cost: Total funding cost
        funding_ratio: Funding cost as percentage of initial capital
    """
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    fee_cost: float
    fee_ratio: float
    funding_cost: float = 0.0
    funding_ratio: float = 0.0


@dataclass
class BacktestResult:
    """Result of a single backtest.
    
    Attributes:
        config: Backtest configuration
        metrics: Performance metrics
        initial_capital: Initial capital
        final_capital: Final capital
        equity_curve: Equity curve over time
        timestamps: Timestamps for equity curve
        trades: List of trades
    """
    config: BacktestConfig
    metrics: PerformanceMetrics
    initial_capital: float
    final_capital: float
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[int] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "config": {
                "symbol": self.config.symbol,
                "mode": self.config.mode.value,
                "lower_price": self.config.lower_price,
                "upper_price": self.config.upper_price,
                "grid_count": self.config.grid_count,
                "initial_capital": self.config.initial_capital,
                "start_date": self.config.start_date,
                "end_date": self.config.end_date,
                "fee_rate": self.config.fee_rate,
                "leverage": self.config.leverage,
                "funding_rate": self.config.funding_rate,
                "funding_interval": self.config.funding_interval,
            },
            "metrics": {
                "total_return": self.metrics.total_return,
                "annual_return": self.metrics.annual_return,
                "max_drawdown": self.metrics.max_drawdown,
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "win_rate": self.metrics.win_rate,
                "total_trades": self.metrics.total_trades,
                "winning_trades": self.metrics.winning_trades,
                "losing_trades": self.metrics.losing_trades,
                "fee_cost": self.metrics.fee_cost,
                "fee_ratio": self.metrics.fee_ratio,
                "funding_cost": self.metrics.funding_cost,
                "funding_ratio": self.metrics.funding_ratio,
            },
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "equity_curve": self.equity_curve,
            "timestamps": self.timestamps,
            "trades": self.trades,
        }


@dataclass
class GridSearchResult:
    """Result of grid search optimization.
    
    Attributes:
        best_result: Best backtest result
        all_results: All backtest results
        best_params: Best parameters
        parameter_ranges: Parameter ranges used
    """
    best_result: BacktestResult
    all_results: List[BacktestResult] = field(default_factory=list)
    best_params: Dict = field(default_factory=dict)
    parameter_ranges: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "best_result": self.best_result.to_dict(),
            "best_params": self.best_params,
            "parameter_ranges": self.parameter_ranges,
            "all_results": [r.to_dict() for r in self.all_results],
        }
