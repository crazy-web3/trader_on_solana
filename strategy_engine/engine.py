"""Grid strategy engine implementation."""

from typing import List, Tuple
import math
from strategy_engine.models import (
    GridStrategy,
    StrategyConfig,
    StrategyMode,
    TradeRecord,
    StrategyResult,
)
from strategy_engine.exceptions import (
    InvalidParameterError,
    InsufficientFundsError,
    ExecutionError,
)
from market_data_layer.models import KlineData


class GridStrategyEngine:
    """Grid trading strategy engine.
    
    Implements grid trading strategy with support for:
    - Long grid (buy low, sell high)
    - Short grid (sell high, buy low)
    - Neutral grid (both buy and sell)
    """
    
    def __init__(self, config: StrategyConfig):
        """Initialize strategy engine.
        
        Args:
            config: Strategy configuration
            
        Raises:
            InvalidParameterError: If configuration is invalid
        """
        self._validate_config(config)
        self.config = config
        self.strategy = GridStrategy(config)
        self.trades: List[TradeRecord] = []
        self.capital = config.initial_capital
        self.holdings = 0.0  # Current holdings in base asset
        self.equity_curve: List[float] = [config.initial_capital]
        self.timestamps: List[int] = []
        self.max_equity = config.initial_capital
        self.min_equity = config.initial_capital
    
    def _validate_config(self, config: StrategyConfig) -> None:
        """Validate strategy configuration.
        
        Args:
            config: Strategy configuration
            
        Raises:
            InvalidParameterError: If configuration is invalid
        """
        if config.lower_price <= 0:
            raise InvalidParameterError("Lower price must be positive")
        
        if config.upper_price <= 0:
            raise InvalidParameterError("Upper price must be positive")
        
        if config.lower_price >= config.upper_price:
            raise InvalidParameterError("Lower price must be less than upper price")
        
        if config.grid_count < 2:
            raise InvalidParameterError("Grid count must be at least 2")
        
        if config.initial_capital <= 0:
            raise InvalidParameterError("Initial capital must be positive")
        
        if config.fee_rate < 0 or config.fee_rate > 0.01:
            raise InvalidParameterError("Fee rate must be between 0 and 1%")
    
    def execute(self, klines: List[KlineData]) -> StrategyResult:
        """Execute strategy on K-line data.
        
        Args:
            klines: List of K-line data
            
        Returns:
            Strategy execution result
            
        Raises:
            ExecutionError: If execution fails
        """
        if not klines:
            raise ExecutionError("No K-line data provided")
        
        try:
            # Process each K-line
            for kline in klines:
                self._process_kline(kline)
            
            # Calculate final result
            result = self._calculate_result()
            return result
        
        except Exception as e:
            raise ExecutionError(f"Strategy execution failed: {str(e)}")
    
    def _process_kline(self, kline: KlineData) -> None:
        """Process a single K-line.
        
        Args:
            kline: K-line data
        """
        # Check for trades at different price levels
        self._check_trades(kline)
        
        # Update equity curve
        current_equity = self._calculate_current_equity(kline.close)
        self.equity_curve.append(current_equity)
        self.timestamps.append(kline.timestamp)
        
        # Update max/min equity for drawdown calculation
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        if current_equity < self.min_equity:
            self.min_equity = current_equity
    
    def _check_trades(self, kline: KlineData) -> None:
        """Check for potential trades at current price.
        
        Args:
            kline: K-line data
        """
        price = kline.close
        
        # Check each grid level
        for i, grid_price in enumerate(self.strategy.grid_prices):
            if self.config.mode == StrategyMode.LONG:
                self._check_long_trade(i, grid_price, price, kline)
            elif self.config.mode == StrategyMode.SHORT:
                self._check_short_trade(i, grid_price, price, kline)
            elif self.config.mode == StrategyMode.NEUTRAL:
                self._check_neutral_trade(i, grid_price, price, kline)
    
    def _check_long_trade(self, grid_idx: int, grid_price: float, 
                         current_price: float, kline: KlineData) -> None:
        """Check for long grid trades (buy low, sell high).
        
        Args:
            grid_idx: Grid level index
            grid_price: Grid price level
            current_price: Current price
            kline: K-line data
        """
        # Buy at grid price if price drops to it
        if current_price <= grid_price and self.strategy.grid_status[grid_idx] == 0:
            self._execute_buy(grid_idx, grid_price, kline)
        
        # Sell at next grid level if price rises
        if grid_idx > 0 and current_price >= grid_price and \
           self.strategy.grid_status[grid_idx - 1] == 1:
            self._execute_sell(grid_idx - 1, grid_price, kline)
    
    def _check_short_trade(self, grid_idx: int, grid_price: float,
                          current_price: float, kline: KlineData) -> None:
        """Check for short grid trades (sell high, buy low).
        
        Args:
            grid_idx: Grid level index
            grid_price: Grid price level
            current_price: Current price
            kline: K-line data
        """
        # Sell at grid price if price rises to it
        if current_price >= grid_price and self.strategy.grid_status[grid_idx] == 0:
            self._execute_sell(grid_idx, grid_price, kline)
        
        # Buy at next grid level if price falls
        if grid_idx > 0 and current_price <= grid_price and \
           self.strategy.grid_status[grid_idx - 1] == 1:
            self._execute_buy(grid_idx - 1, grid_price, kline)
    
    def _check_neutral_trade(self, grid_idx: int, grid_price: float,
                            current_price: float, kline: KlineData) -> None:
        """Check for neutral grid trades (both buy and sell).
        
        Args:
            grid_idx: Grid level index
            grid_price: Grid price level
            current_price: Current price
            kline: K-line data
        """
        # Buy at lower half of grid
        if grid_idx < len(self.strategy.grid_prices) // 2:
            if current_price <= grid_price and self.strategy.grid_status[grid_idx] == 0:
                self._execute_buy(grid_idx, grid_price, kline)
            if grid_idx > 0 and current_price >= grid_price and \
               self.strategy.grid_status[grid_idx - 1] == 1:
                self._execute_sell(grid_idx - 1, grid_price, kline)
        
        # Sell at upper half of grid
        else:
            if current_price >= grid_price and self.strategy.grid_status[grid_idx] == 0:
                self._execute_sell(grid_idx, grid_price, kline)
            if grid_idx > 0 and current_price <= grid_price and \
               self.strategy.grid_status[grid_idx - 1] == 1:
                self._execute_buy(grid_idx - 1, grid_price, kline)
    
    def _execute_buy(self, grid_idx: int, price: float, kline: KlineData) -> None:
        """Execute a buy order.
        
        Args:
            grid_idx: Grid level index
            price: Buy price
            kline: K-line data
        """
        # Calculate quantity based on available capital
        quantity_per_grid = self.config.initial_capital / self.config.grid_count
        quantity = quantity_per_grid / price
        
        # Check if we have enough capital
        cost = quantity * price * (1 + self.config.fee_rate)
        if self.capital < cost:
            return
        
        # Execute trade
        fee = quantity * price * self.config.fee_rate
        self.capital -= (quantity * price + fee)
        self.holdings += quantity
        
        # Update grid status
        self.strategy.grid_status[grid_idx] = 1
        self.strategy.grid_quantities[grid_idx] = quantity
        self.strategy.grid_entry_prices[grid_idx] = price
        
        # Record trade
        trade = TradeRecord(
            timestamp=kline.timestamp,
            price=price,
            quantity=quantity,
            side="buy",
            grid_level=grid_idx,
            fee=fee,
            pnl=0.0,
        )
        self.trades.append(trade)
    
    def _execute_sell(self, grid_idx: int, price: float, kline: KlineData) -> None:
        """Execute a sell order.
        
        Args:
            grid_idx: Grid level index
            price: Sell price
            kline: K-line data
        """
        if self.strategy.grid_status[grid_idx] == 0:
            return
        
        quantity = self.strategy.grid_quantities[grid_idx]
        entry_price = self.strategy.grid_entry_prices[grid_idx]
        
        # Execute trade
        revenue = quantity * price
        fee = revenue * self.config.fee_rate
        pnl = revenue - fee - (quantity * entry_price)
        
        self.capital += revenue - fee
        self.holdings -= quantity
        
        # Update grid status
        self.strategy.grid_status[grid_idx] = 0
        self.strategy.grid_quantities[grid_idx] = 0.0
        self.strategy.grid_entry_prices[grid_idx] = 0.0
        
        # Record trade
        trade = TradeRecord(
            timestamp=kline.timestamp,
            price=price,
            quantity=quantity,
            side="sell",
            grid_level=grid_idx,
            fee=fee,
            pnl=pnl,
        )
        self.trades.append(trade)
    
    def _calculate_current_equity(self, current_price: float) -> float:
        """Calculate current equity.
        
        Args:
            current_price: Current price
            
        Returns:
            Current equity value
        """
        return self.capital + self.holdings * current_price
    
    def _calculate_result(self) -> StrategyResult:
        """Calculate strategy result.
        
        Returns:
            Strategy execution result
        """
        final_capital = self.equity_curve[-1] if self.equity_curve else self.config.initial_capital
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital
        
        # Calculate trade statistics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.side == "sell" and t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.side == "sell" and t.pnl <= 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate maximum drawdown
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        if self.equity_curve:
            peak = self.equity_curve[0]
            for equity in self.equity_curve:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown
                    max_drawdown = peak - equity
        
        return StrategyResult(
            symbol=self.config.symbol,
            mode=self.config.mode,
            initial_capital=self.config.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            max_drawdown_pct=max_drawdown_pct,
            trades=self.trades,
            equity_curve=self.equity_curve,
            timestamps=self.timestamps,
        )
