"""Data models for strategy engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from datetime import datetime


class StrategyMode(str, Enum):
    """Strategy trading mode."""
    LONG = "long"      # 做多网格
    SHORT = "short"    # 做空网格
    NEUTRAL = "neutral"  # 中性网格


@dataclass
class StrategyConfig:
    """Strategy configuration parameters.
    
    Attributes:
        symbol: Trading pair symbol (e.g., "BTC/USDT")
        mode: Strategy mode (long, short, neutral)
        lower_price: Lower price boundary
        upper_price: Upper price boundary
        grid_count: Number of grid levels
        initial_capital: Initial capital in USDT
        fee_rate: Trading fee rate (default 0.05%)
    """
    symbol: str
    mode: StrategyMode
    lower_price: float
    upper_price: float
    grid_count: int
    initial_capital: float
    fee_rate: float = 0.0005  # 0.05%


@dataclass
class TradeRecord:
    """Record of a single trade.
    
    Attributes:
        timestamp: Trade timestamp (milliseconds)
        price: Trade price
        quantity: Trade quantity
        side: Trade side (buy/sell)
        grid_level: Grid level index
        fee: Trading fee
        pnl: Profit/loss for this trade
    """
    timestamp: int
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    grid_level: int
    fee: float
    pnl: float = 0.0


@dataclass
class StrategyResult:
    """Result of strategy execution.
    
    Attributes:
        symbol: Trading pair symbol
        mode: Strategy mode
        initial_capital: Initial capital
        final_capital: Final capital
        total_return: Total return percentage
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
        win_rate: Win rate percentage
        max_drawdown: Maximum drawdown percentage
        max_drawdown_pct: Maximum drawdown percentage
        trades: List of all trades
        equity_curve: Equity curve over time
        timestamps: Timestamps for equity curve
    """
    symbol: str
    mode: StrategyMode
    initial_capital: float
    final_capital: float
    total_return: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    max_drawdown: float
    max_drawdown_pct: float
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    timestamps: List[int] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "mode": self.mode.value,
            "initial_capital": self.initial_capital,
            "final_capital": self.final_capital,
            "total_return": self.total_return,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "trades": [
                {
                    "timestamp": t.timestamp,
                    "price": t.price,
                    "quantity": t.quantity,
                    "side": t.side,
                    "grid_level": t.grid_level,
                    "fee": t.fee,
                    "pnl": t.pnl,
                }
                for t in self.trades
            ],
            "equity_curve": self.equity_curve,
            "timestamps": self.timestamps,
        }


@dataclass
class GridStrategy:
    """Grid strategy configuration and state.
    
    Attributes:
        config: Strategy configuration
        grid_prices: List of grid price levels
        grid_status: Status of each grid level (0=empty, 1=holding)
        grid_quantities: Quantity held at each grid level
        grid_entry_prices: Entry price for each grid level
    """
    config: StrategyConfig
    grid_prices: List[float] = field(default_factory=list)
    grid_status: List[int] = field(default_factory=list)
    grid_quantities: List[float] = field(default_factory=list)
    grid_entry_prices: List[float] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize grid after creation."""
        self._initialize_grid()
    
    def _initialize_grid(self):
        """Initialize grid price levels."""
        lower = self.config.lower_price
        upper = self.config.upper_price
        count = self.config.grid_count
        
        # Generate grid prices
        self.grid_prices = [
            lower + (upper - lower) * i / (count - 1)
            for i in range(count)
        ]
        
        # Initialize grid status (0 = empty, 1 = holding)
        self.grid_status = [0] * count
        self.grid_quantities = [0.0] * count
        self.grid_entry_prices = [0.0] * count
