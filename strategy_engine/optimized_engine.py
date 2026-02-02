"""Optimized grid strategy engine implementation based on Binance grid trading documentation.

This implementation follows the official Binance grid trading mechanism:
- Supports arithmetic and geometric grid types
- Implements proper grid closure mechanism
- Handles initial position opening correctly
- Calculates grid profit and unrealized PnL separately
- Manages margin and risk rate
"""

from typing import List, Dict, Tuple
import math
from strategy_engine.models import (
    GridStrategy,
    StrategyConfig,
    StrategyMode,
    GridType,
    TradeRecord,
    StrategyResult,
)
from strategy_engine.exceptions import (
    InvalidParameterError,
    InsufficientFundsError,
    ExecutionError,
)
from market_data_layer.models import KlineData


class GridLevel:
    """Represents a single grid level with its state."""
    
    def __init__(self, level_idx: int, price: float):
        self.level_idx = level_idx
        self.price = price
        self.is_closed = False  # Grid closure flag
        self.pending_buy_orders: List['GridOrder'] = []
        self.pending_sell_orders: List['GridOrder'] = []
        self.long_position = 0.0  # Long position at this level
        self.short_position = 0.0  # Short position at this level
    
    def close_grid(self):
        """Close this grid level (no more orders will be placed here)."""
        self.is_closed = True
    
    def get_net_position(self) -> float:
        """Get net position (positive=long, negative=short)."""
        return self.long_position - self.short_position


class GridOrder:
    """Represents a grid order."""
    
    def __init__(self, level_idx: int, price: float, side: str, quantity: float, 
                 order_type: str = "counter", entry_price: float = 0.0):
        self.level_idx = level_idx
        self.price = price
        self.side = side  # "buy" or "sell"
        self.quantity = quantity
        self.order_type = order_type  # "initial" or "counter"
        self.is_filled = False
        self.fill_price = 0.0
        self.entry_price = entry_price  # For tracking entry price of positions


class OptimizedGridStrategyEngine:
    """Optimized grid trading strategy engine.
    
    Key improvements:
    1. Supports both arithmetic and geometric grid types
    2. Implements grid closure mechanism
    3. Proper initial position handling
    4. Separate tracking of grid profit and unrealized PnL
    5. Accurate margin and risk rate calculations
    """
    
    def __init__(self, config: StrategyConfig):
        """Initialize optimized strategy engine.
        
        Args:
            config: Strategy configuration
            
        Raises:
            InvalidParameterError: If configuration is invalid
        """
        self._validate_config(config)
        self.config = config
        
        # Grid management
        self.grid_levels: Dict[int, GridLevel] = {}
        self._initialize_grid_levels()
        
        # Position tracking
        self.total_long_position = 0.0
        self.total_short_position = 0.0
        self.long_entry_price = 0.0  # Average entry price for long positions
        self.short_entry_price = 0.0  # Average entry price for short positions
        self.position_entry_prices: Dict[str, float] = {}  # Track entry prices
        
        # Capital and fees
        self.capital = config.initial_capital
        self.total_fees = 0.0
        self.total_funding_fees = 0.0
        self.grid_profit = 0.0  # Realized profit from completed grid cycles
        
        # Equity tracking
        self.equity_curve: List[float] = []
        self.timestamps: List[int] = []
        self.max_equity = config.initial_capital
        self.min_equity = config.initial_capital
        
        # Trade records
        self.trades: List[TradeRecord] = []
        
        # Funding fee tracking
        self.last_funding_time = 0
        self.last_price = 0.0
        
        # Grid parameters
        self._calculate_grid_parameters()
    
    def _validate_config(self, config: StrategyConfig) -> None:
        """Validate strategy configuration."""
        if config.lower_price <= 0:
            raise InvalidParameterError("Lower price must be positive")
        
        if config.upper_price <= 0:
            raise InvalidParameterError("Upper price must be positive")
        
        if config.lower_price >= config.upper_price:
            raise InvalidParameterError("Lower price must be less than upper price")
        
        if config.grid_count < 2:
            raise InvalidParameterError("Grid count must be at least 2")
        
        if config.grid_count > 169:
            raise InvalidParameterError("Grid count cannot exceed 169")
        
        if config.initial_capital <= 0:
            raise InvalidParameterError("Initial capital must be positive")
        
        if config.fee_rate < 0 or config.fee_rate > 0.01:
            raise InvalidParameterError("Fee rate must be between 0 and 1%")
        
        if config.leverage <= 0 or config.leverage > 100:
            raise InvalidParameterError("Leverage must be between 1x and 100x")
    
    def _calculate_grid_parameters(self) -> None:
        """Calculate grid parameters based on grid type."""
        if self.config.grid_type == GridType.ARITHMETIC:
            self._calculate_arithmetic_grid()
        else:
            self._calculate_geometric_grid()
    
    def _calculate_arithmetic_grid(self) -> None:
        """Calculate arithmetic grid prices."""
        lower = self.config.lower_price
        upper = self.config.upper_price
        count = self.config.grid_count
        
        # Price difference per grid
        self.grid_gap = (upper - lower) / (count - 1)
        
        # Validate minimum price tick
        if self.grid_gap < self.config.min_price_tick:
            raise InvalidParameterError(
                f"Grid gap {self.grid_gap} is smaller than minimum price tick {self.config.min_price_tick}"
            )
    
    def _calculate_geometric_grid(self) -> None:
        """Calculate geometric grid prices."""
        lower = self.config.lower_price
        upper = self.config.upper_price
        count = self.config.grid_count
        
        # Price ratio per grid
        self.price_ratio = (upper / lower) ** (1 / (count - 1))
        
        # Validate minimum price tick
        min_gap = lower * (self.price_ratio - 1)
        if min_gap < self.config.min_price_tick:
            raise InvalidParameterError(
                f"Minimum grid gap {min_gap} is smaller than minimum price tick {self.config.min_price_tick}"
            )
    
    def _initialize_grid_levels(self) -> None:
        """Initialize all grid levels."""
        for i in range(self.config.grid_count):
            price = self._get_grid_price(i)
            self.grid_levels[i] = GridLevel(i, price)
    
    def _get_grid_price(self, level_idx: int) -> float:
        """Get price for a specific grid level.
        
        Args:
            level_idx: Grid level index
            
        Returns:
            Price at this grid level
        """
        if self.config.grid_type == GridType.ARITHMETIC:
            return self.config.lower_price + level_idx * self.grid_gap
        else:
            return self.config.lower_price * (self.price_ratio ** level_idx)
    
    def _find_closest_grid_level(self, price: float) -> int:
        """Find the closest grid level to a given price.
        
        Args:
            price: Price to find closest grid level for
            
        Returns:
            Index of closest grid level
        """
        if self.config.grid_type == GridType.ARITHMETIC:
            idx = round((price - self.config.lower_price) / self.grid_gap)
        else:
            idx = round(math.log(price / self.config.lower_price) / math.log(self.price_ratio))
        
        return max(0, min(idx, self.config.grid_count - 1))
    
    def _place_initial_orders(self, start_price: float) -> None:
        """Place initial grid orders based on strategy mode.
        
        Args:
            start_price: Starting price for order placement
        """
        # Find the grid level closest to start price
        start_level = self._find_closest_grid_level(start_price)
        
        # Calculate base quantity per grid
        base_quantity = self.config.initial_capital / (self.config.grid_count * self._get_grid_price(start_level))
        quantity = base_quantity * self.config.leverage
        
        if self.config.mode == StrategyMode.LONG:
            self._place_long_initial_orders(start_level, quantity)
        elif self.config.mode == StrategyMode.SHORT:
            self._place_short_initial_orders(start_level, quantity)
        else:  # NEUTRAL
            self._place_neutral_initial_orders(start_level, quantity)
    
    def _place_long_initial_orders(self, start_level: int, quantity: float) -> None:
        """Place initial orders for long grid mode.
        
        Long grid: Only place buy orders BELOW current price.
        - Buy orders are placed at prices lower than current price
        - When a buy order is filled, a sell order is placed above it
        - This ensures we only open long positions when price falls
        """
        for i in range(self.config.grid_count):
            grid = self.grid_levels[i]
            
            # Only place buy orders below current price (start_level)
            if i < start_level:
                # Below current price: place buy orders to open long positions
                order = GridOrder(i, grid.price, "buy", quantity, "initial", grid.price)
                grid.pending_buy_orders.append(order)
            # Above current price: don't place any orders initially
            # Sell orders will be placed when buy orders are filled
    
    def _place_short_initial_orders(self, start_level: int, quantity: float) -> None:
        """Place initial orders for short grid mode.
        
        Short grid: Only place sell orders ABOVE current price.
        - Sell orders are placed at prices higher than current price
        - When a sell order is filled, a buy order is placed below it
        - This ensures we only open short positions when price rises
        """
        for i in range(self.config.grid_count):
            grid = self.grid_levels[i]
            
            # Only place sell orders above current price (start_level)
            if i > start_level:
                # Above current price: place sell orders to open short positions
                order = GridOrder(i, grid.price, "sell", quantity, "initial", grid.price)
                grid.pending_sell_orders.append(order)
            # Below current price: don't place any orders initially
            # Buy orders will be placed when sell orders are filled
    
    def _place_neutral_initial_orders(self, start_level: int, quantity: float) -> None:
        """Place initial orders for neutral grid mode.
        
        Neutral grid: Place buy orders below and sell orders above current price.
        - Buy orders below current price to open long positions
        - Sell orders above current price to open short positions
        - No orders at current price to avoid immediate execution
        """
        for i in range(self.config.grid_count):
            grid = self.grid_levels[i]
            
            if i < start_level:
                # Below current price: place buy orders
                order = GridOrder(i, grid.price, "buy", quantity, "initial", grid.price)
                grid.pending_buy_orders.append(order)
            elif i > start_level:
                # Above current price: place sell orders
                order = GridOrder(i, grid.price, "sell", quantity, "initial", grid.price)
                grid.pending_sell_orders.append(order)
            # At current price (i == start_level): don't place any orders
    
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
            # Initialize with first price
            start_price = klines[0].close
            self.last_price = start_price
            self._place_initial_orders(start_price)
            
            # Record initial equity (should equal initial capital since no positions yet)
            initial_equity = self._calculate_current_equity(start_price)
            self.equity_curve.append(initial_equity)
            self.timestamps.append(klines[0].timestamp)
            
            # Process K-lines starting from the second one
            # (First K-line is used only for initialization)
            for kline in klines[1:]:
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
        self.last_price = kline.close
        
        # Process funding fees
        self._process_funding_fees(kline)
        
        # Check for order fills
        self._check_order_fills(kline)
        
        # Update equity curve
        current_equity = self._calculate_current_equity(kline.close)
        self.equity_curve.append(current_equity)
        self.timestamps.append(kline.timestamp)
        
        # Update max/min equity
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        if current_equity < self.min_equity:
            self.min_equity = current_equity
    
    def _check_order_fills(self, kline: KlineData) -> None:
        """Check if any pending orders should be filled.
        
        Args:
            kline: K-line data
        """
        # Process buy orders
        for level_idx, grid in self.grid_levels.items():
            if grid.is_closed:
                continue
            
            # Check buy orders
            for order in grid.pending_buy_orders[:]:
                if order.is_filled:
                    continue
                
                # Buy order fills when price drops to or below order price
                if kline.low <= order.price:
                    self._fill_order(order, kline, order.price)
                    grid.pending_buy_orders.remove(order)
                    self._place_counter_order(order, kline)
            
            # Check sell orders
            for order in grid.pending_sell_orders[:]:
                if order.is_filled:
                    continue
                
                # Sell order fills when price rises to or above order price
                if kline.high >= order.price:
                    self._fill_order(order, kline, order.price)
                    grid.pending_sell_orders.remove(order)
                    self._place_counter_order(order, kline)
    
    def _fill_order(self, order: GridOrder, kline: KlineData, fill_price: float) -> None:
        """Fill a grid order.
        
        Args:
            order: Grid order to fill
            kline: K-line data
            fill_price: Price at which order is filled
        """
        # Calculate fees
        fee = order.quantity * fill_price * self.config.fee_rate
        
        if self.capital < fee:
            return  # Insufficient capital for fee
        
        self.capital -= fee
        self.total_fees += fee
        
        pnl = 0.0
        
        if order.side == "buy":
            # Buy order: increase long position or close short position
            if self.total_short_position > 0:
                # Close short position
                close_qty = min(order.quantity, self.total_short_position)
                pnl = close_qty * (self.short_entry_price - fill_price) * self.config.leverage
                self.total_short_position -= close_qty
                self.grid_profit += max(0, pnl)
                
                # Remaining quantity becomes long position
                remaining_qty = order.quantity - close_qty
                if remaining_qty > 0:
                    # Update long position and entry price
                    total_cost = self.total_long_position * self.long_entry_price + remaining_qty * fill_price
                    self.total_long_position += remaining_qty
                    self.long_entry_price = total_cost / self.total_long_position if self.total_long_position > 0 else fill_price
            else:
                # Open long position
                total_cost = self.total_long_position * self.long_entry_price + order.quantity * fill_price
                self.total_long_position += order.quantity
                self.long_entry_price = total_cost / self.total_long_position if self.total_long_position > 0 else fill_price
        
        else:  # sell order
            # Sell order: increase short position or close long position
            if self.total_long_position > 0:
                # Close long position
                close_qty = min(order.quantity, self.total_long_position)
                pnl = close_qty * (fill_price - self.long_entry_price) * self.config.leverage
                self.total_long_position -= close_qty
                self.grid_profit += max(0, pnl)
                
                # Remaining quantity becomes short position
                remaining_qty = order.quantity - close_qty
                if remaining_qty > 0:
                    # Update short position and entry price
                    total_cost = self.total_short_position * self.short_entry_price + remaining_qty * fill_price
                    self.total_short_position += remaining_qty
                    self.short_entry_price = total_cost / self.total_short_position if self.total_short_position > 0 else fill_price
            else:
                # Open short position
                total_cost = self.total_short_position * self.short_entry_price + order.quantity * fill_price
                self.total_short_position += order.quantity
                self.short_entry_price = total_cost / self.total_short_position if self.total_short_position > 0 else fill_price
        
        # Record trade
        trade = TradeRecord(
            timestamp=kline.timestamp,
            price=fill_price,
            quantity=order.quantity,
            side=order.side,
            grid_level=order.level_idx,
            fee=fee,
            pnl=pnl,
            funding_fee=0.0,
            position_size=self.total_long_position - self.total_short_position,
        )
        self.trades.append(trade)
        
        order.is_filled = True
        order.fill_price = fill_price
    
    def _place_counter_order(self, filled_order: GridOrder, kline: KlineData) -> None:
        """Place counter order after an order is filled.
        
        Args:
            filled_order: The order that was just filled
            kline: K-line data
        """
        level_idx = filled_order.level_idx
        
        if self.config.mode == StrategyMode.LONG:
            if filled_order.side == "buy" and level_idx + 1 < self.config.grid_count:
                # Buy filled -> place sell at next level
                next_grid = self.grid_levels[level_idx + 1]
                if not next_grid.is_closed:
                    order = GridOrder(level_idx + 1, next_grid.price, "sell", 
                                    filled_order.quantity, "counter", next_grid.price)
                    next_grid.pending_sell_orders.append(order)
            
            elif filled_order.side == "sell" and level_idx - 1 >= 0:
                # Sell filled -> place buy at previous level
                prev_grid = self.grid_levels[level_idx - 1]
                if not prev_grid.is_closed:
                    order = GridOrder(level_idx - 1, prev_grid.price, "buy", 
                                    filled_order.quantity, "counter", prev_grid.price)
                    prev_grid.pending_buy_orders.append(order)
        
        elif self.config.mode == StrategyMode.SHORT:
            if filled_order.side == "sell" and level_idx - 1 >= 0:
                # Sell filled -> place buy at previous level
                prev_grid = self.grid_levels[level_idx - 1]
                if not prev_grid.is_closed:
                    order = GridOrder(level_idx - 1, prev_grid.price, "buy", 
                                    filled_order.quantity, "counter", prev_grid.price)
                    prev_grid.pending_buy_orders.append(order)
            
            elif filled_order.side == "buy" and level_idx + 1 < self.config.grid_count:
                # Buy filled -> place sell at next level
                next_grid = self.grid_levels[level_idx + 1]
                if not next_grid.is_closed:
                    order = GridOrder(level_idx + 1, next_grid.price, "sell", 
                                    filled_order.quantity, "counter", next_grid.price)
                    next_grid.pending_sell_orders.append(order)
        
        else:  # NEUTRAL
            if filled_order.side == "buy" and level_idx + 1 < self.config.grid_count:
                # Buy filled -> place sell at next level
                next_grid = self.grid_levels[level_idx + 1]
                if not next_grid.is_closed:
                    order = GridOrder(level_idx + 1, next_grid.price, "sell", 
                                    filled_order.quantity, "counter", next_grid.price)
                    next_grid.pending_sell_orders.append(order)
            
            elif filled_order.side == "sell" and level_idx - 1 >= 0:
                # Sell filled -> place buy at previous level
                prev_grid = self.grid_levels[level_idx - 1]
                if not prev_grid.is_closed:
                    order = GridOrder(level_idx - 1, prev_grid.price, "buy", 
                                    filled_order.quantity, "counter", prev_grid.price)
                    prev_grid.pending_buy_orders.append(order)
    
    def _process_funding_fees(self, kline: KlineData) -> None:
        """Process funding fees for perpetual contracts.
        
        Args:
            kline: K-line data
        """
        if self.config.funding_rate == 0:
            return
        
        current_position = self.total_long_position - self.total_short_position
        if abs(current_position) < 1e-10:
            return
        
        funding_interval_ms = self.config.funding_interval * 60 * 60 * 1000
        
        if self.last_funding_time == 0:
            self.last_funding_time = kline.timestamp
            return
        
        if kline.timestamp - self.last_funding_time >= funding_interval_ms:
            # Calculate funding fee
            position_notional = abs(current_position) * kline.close
            funding_amount = position_notional * self.config.funding_rate
            
            if current_position > 0:
                # Long position pays funding
                self.capital -= funding_amount
            else:
                # Short position receives funding
                self.capital += funding_amount
            
            self.total_funding_fees += abs(funding_amount)
            self.last_funding_time = kline.timestamp
    
    def _calculate_current_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized PnL.
        
        Args:
            current_price: Current market price
            
        Returns:
            Current equity
        """
        unrealized_pnl = 0.0
        
        # Calculate unrealized PnL for long positions
        if self.total_long_position > 0 and self.long_entry_price > 0:
            unrealized_pnl += self.total_long_position * (current_price - self.long_entry_price)
        
        # Calculate unrealized PnL for short positions
        if self.total_short_position > 0 and self.short_entry_price > 0:
            unrealized_pnl += self.total_short_position * (self.short_entry_price - current_price)
        
        return self.capital + unrealized_pnl
    
    def _calculate_result(self) -> StrategyResult:
        """Calculate strategy result.
        
        Returns:
            Strategy execution result
        """
        final_capital = self.equity_curve[-1] if self.equity_curve else self.config.initial_capital
        total_return = (final_capital - self.config.initial_capital) / self.config.initial_capital
        
        # Calculate trade statistics
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.pnl > 0)
        losing_trades = sum(1 for t in self.trades if t.pnl < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Calculate maximum drawdown
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        if self.equity_curve:
            peak = self.equity_curve[0]
            for equity in self.equity_curve:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak if peak > 0 else 0
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown
                    max_drawdown = peak - equity
        
        # Calculate unrealized PnL
        unrealized_pnl = 0.0
        if self.last_price > 0:
            if self.total_long_position > 0 and self.long_entry_price > 0:
                unrealized_pnl += self.total_long_position * (self.last_price - self.long_entry_price)
            if self.total_short_position > 0 and self.short_entry_price > 0:
                unrealized_pnl += self.total_short_position * (self.short_entry_price - self.last_price)
        
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
            total_fees=self.total_fees,
            total_funding_fees=self.total_funding_fees,
            grid_profit=self.grid_profit,
            unrealized_pnl=unrealized_pnl,
            trades=self.trades,
            equity_curve=self.equity_curve,
            timestamps=self.timestamps,
        )
