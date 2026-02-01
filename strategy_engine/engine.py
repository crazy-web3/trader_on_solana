"""Grid strategy engine implementation."""

from typing import List, Tuple, Dict
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


class GridOrder:
    """Represents a grid order."""
    def __init__(self, grid_idx: int, price: float, side: str, quantity: float, order_type: str = "counter"):
        self.grid_idx = grid_idx
        self.price = price
        self.side = side  # "buy" or "sell"
        self.quantity = quantity
        self.is_filled = False
        self.order_type = order_type  # "initial" or "counter"


class GridStrategyEngine:
    """Grid trading strategy engine for perpetual contracts.

    Implements grid trading strategy with correct logic:
    - 做多网格: 低价位建多仓，高价位挂卖单，价格下跌时买入，上涨时卖出平仓
    - 做空网格: 高价位建空仓，低价位挂买单，价格上涨时卖出开空，下跌时买入平空
    - 中性网格: 中间建仓，低买高卖，做多和做空同时进行
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
        self.position_size = 0.0  # Net position size (positive for long, negative for short)
        self.total_fees = 0.0
        self.total_funding_fees = 0.0
        self.grid_profit = 0.0  # 网格收益累计（已配对交易的收益）
        self.equity_curve: List[float] = []
        self.timestamps: List[int] = []
        self.max_equity = config.initial_capital
        self.min_equity = config.initial_capital
        self.last_funding_time = 0

        # Grid order management: grid_idx -> List[GridOrder]
        self.pending_orders: Dict[int, List[GridOrder]] = {}
        self.grid_positions: Dict[int, float] = {}  # grid_idx -> position_size (positive=long, negative=short)

        # Track last K-line close price for accurate unrealized PnL calculation
        self.last_price = 0.0

        # Calculate grid parameters
        self.grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
        # Use a smaller portion of capital per grid to avoid over-allocation
        self.capital_per_grid = config.initial_capital / (config.grid_count * 2)

        # Initialize grid
        self._initialize_grid()

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

        if config.initial_capital <= 0:
            raise InvalidParameterError("Initial capital must be positive")

        if config.fee_rate < 0 or config.fee_rate > 0.01:
            raise InvalidParameterError("Fee rate must be between 0 and 1%")

        if config.leverage <= 0 or config.leverage > 100:
            raise InvalidParameterError("Leverage must be between 1x and 100x")

    def _initialize_grid(self):
        """Initialize grid with proper order placement based on strategy mode."""
        # This will be called when we get the first price data
        pass

    def _update_position_size(self):
        """Recalculate position size from grid positions."""
        self.position_size = sum(self.grid_positions.values())

    def _add_pending_order(self, order: GridOrder):
        """Add a pending order to the grid.

        Args:
            order: Order to add
        """
        if order.grid_idx not in self.pending_orders:
            self.pending_orders[order.grid_idx] = []
        self.pending_orders[order.grid_idx].append(order)

    def _remove_order(self, grid_idx: int, order: GridOrder):
        """Remove a filled order from pending orders.

        Args:
            grid_idx: Grid index
            order: Order to remove
        """
        if grid_idx in self.pending_orders:
            if order in self.pending_orders[grid_idx]:
                self.pending_orders[grid_idx].remove(order)
            if not self.pending_orders[grid_idx]:
                del self.pending_orders[grid_idx]

    def _place_initial_positions_from_start(self, start_price: float):
        """从起始价格开始建立初始仓位和挂单.

        Args:
            start_price: 历史数据的起始价格
        """
        # 确保起始价格在网格区间内
        if start_price < self.config.lower_price:
            start_price = self.config.lower_price
        elif start_price > self.config.upper_price:
            start_price = self.config.upper_price

        # 找到起始价格对应的网格索引
        start_grid_idx = int((start_price - self.config.lower_price) / self.grid_gap)
        start_grid_idx = max(0, min(start_grid_idx, self.config.grid_count - 1))

        for i in range(self.config.grid_count):
            grid_price = self.config.lower_price + i * self.grid_gap
            base_quantity = self.capital_per_grid / grid_price
            quantity = base_quantity * self.config.leverage

            if self.config.mode == StrategyMode.LONG:
                # 做多网格: 低价位建多仓，高价位挂卖单
                if i <= start_grid_idx:
                    # 在起始价格及以下建立多仓
                    initial_position = quantity * 0.8
                    self.grid_positions[i] = self.grid_positions.get(i, 0) + initial_position

                    # 在上一个网格挂卖单
                    if i + 1 < self.config.grid_count:
                        sell_price = self.config.lower_price + (i + 1) * self.grid_gap
                        sell_order = GridOrder(i + 1, sell_price, "sell", initial_position, "initial")
                        self._add_pending_order(sell_order)
                else:
                    # 起始价格以上挂买单
                    buy_order = GridOrder(i, grid_price, "buy", quantity * 0.8, "initial")
                    self._add_pending_order(buy_order)

            elif self.config.mode == StrategyMode.SHORT:
                # 做空网格: 高价位建空仓，低价位挂买单
                if i >= start_grid_idx:
                    # 在起始价格及以上建立空仓
                    initial_position = quantity * 0.8
                    self.grid_positions[i] = self.grid_positions.get(i, 0) - initial_position

                    # 在下一个网格挂买单
                    if i - 1 >= 0:
                        buy_price = self.config.lower_price + (i - 1) * self.grid_gap
                        buy_order = GridOrder(i - 1, buy_price, "buy", initial_position, "initial")
                        self._add_pending_order(buy_order)
                else:
                    # 起始价格以下挂卖单
                    sell_order = GridOrder(i, grid_price, "sell", quantity * 0.8, "initial")
                    self._add_pending_order(sell_order)

            elif self.config.mode == StrategyMode.NEUTRAL:
                # 中性网格: 根据位置平衡多空
                if i < start_grid_idx:
                    # 下方网格偏向多仓
                    long_position = quantity * 0.4
                    self.grid_positions[i] = self.grid_positions.get(i, 0) + long_position

                    # 挂卖单
                    if i + 1 < self.config.grid_count:
                        sell_price = self.config.lower_price + (i + 1) * self.grid_gap
                        sell_order = GridOrder(i + 1, sell_price, "sell", long_position, "initial")
                        self._add_pending_order(sell_order)

                    # 挂补仓买单
                    buy_order = GridOrder(i, grid_price, "buy", quantity * 0.2, "initial")
                    self._add_pending_order(buy_order)

                elif i > start_grid_idx:
                    # 上方网格偏向空仓
                    short_position = quantity * 0.4
                    self.grid_positions[i] = self.grid_positions.get(i, 0) - short_position

                    # 挂买单
                    if i - 1 >= 0:
                        buy_price = self.config.lower_price + (i - 1) * self.grid_gap
                        buy_order = GridOrder(i - 1, buy_price, "buy", short_position, "initial")
                        self._add_pending_order(buy_order)

                    # 挂补仓卖单
                    sell_order = GridOrder(i, grid_price, "sell", quantity * 0.2, "initial")
                    self._add_pending_order(sell_order)
                else:
                    # 中间位置，小量多空平衡
                    long_position = quantity * 0.2
                    short_position = quantity * 0.2
                    self.grid_positions[i] = self.grid_positions.get(i, 0) + long_position - short_position

                    # 同时挂卖单和买单
                    sell_order = GridOrder(i, grid_price, "sell", long_position, "initial")
                    buy_order = GridOrder(i, grid_price, "buy", short_position, "initial")
                    self._add_pending_order(sell_order)
                    self._add_pending_order(buy_order)

        # Recalculate position size
        self._update_position_size()

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
            # 从区间最早的价格（第一个K线）开始建仓
            start_price = klines[0].close
            self.last_price = start_price

            # 初始化网格，从起始价格开始建仓
            self._place_initial_positions_from_start(start_price)

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
        # Update last price for accurate unrealized PnL calculation
        self.last_price = kline.close

        # Process funding fees
        self._process_funding_fees(kline)

        # Check for order fills
        self._check_order_fills(kline)

        # Update equity curve
        current_equity = self._calculate_current_equity(kline.close)
        self.equity_curve.append(current_equity)
        self.timestamps.append(kline.timestamp)

        # Update max/min equity for drawdown calculation
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        if current_equity < self.min_equity:
            self.min_equity = current_equity

    def _check_order_fills(self, kline: KlineData) -> None:
        """Check if any pending orders should be filled.

        Args:
            kline: K-line data
        """
        current_price = kline.close
        filled_orders = []

        for grid_idx, orders in self.pending_orders.items():
            for order in orders:
                if order.is_filled:
                    continue

                # Check if order should be filled
                should_fill = False
                if order.side == "buy" and current_price <= order.price:
                    should_fill = True
                elif order.side == "sell" and current_price >= order.price:
                    should_fill = True

                if should_fill:
                    self._fill_order(order, kline)
                    filled_orders.append((grid_idx, order))

        # Remove filled orders and place new ones
        for grid_idx, order in filled_orders:
            self._remove_order(grid_idx, order)
            self._place_counter_order(order, kline)

    def _fill_order(self, order: GridOrder, kline: KlineData) -> None:
        """Fill a grid order.

        Args:
            order: Grid order to fill
            kline: K-line data
        """
        # Calculate fees
        fee = order.quantity * order.price * self.config.fee_rate
        pnl = 0.0

        if self.capital < fee:
            return  # Insufficient capital for fee

        if order.side == "buy":
            # Buy order filled
            self.capital -= fee
            self.total_fees += fee

            if self.config.mode == StrategyMode.LONG:
                # LONG模式: 买单增加多仓，或检查是否平空仓
                # 先检查是否有空仓需要平掉
                closed_short_pnl = self._try_close_short_position(order, kline)
                if closed_short_pnl > 0:
                    pnl = closed_short_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    # 建立多仓
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) + order.quantity

            elif self.config.mode == StrategyMode.SHORT:
                # SHORT模式: 买单平空仓并产生利润
                closed_short_pnl = self._try_close_short_position(order, kline)
                if closed_short_pnl > 0:
                    pnl = closed_short_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    # 没有空仓可平，建立多仓（这种情况在SHORT模式下较少见）
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) + order.quantity

            elif self.config.mode == StrategyMode.NEUTRAL:
                # NEUTRAL模式: 先平空仓，再建多仓
                closed_short_pnl = self._try_close_short_position(order, kline)
                if closed_short_pnl > 0:
                    pnl = closed_short_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) + order.quantity

        else:  # sell order
            # Sell order filled
            self.capital -= fee
            self.total_fees += fee

            if self.config.mode == StrategyMode.LONG:
                # LONG模式: 卖单平多仓并产生利润
                closed_long_pnl = self._try_close_long_position(order, kline)
                if closed_long_pnl > 0:
                    pnl = closed_long_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    # 没有多仓可平，建立空仓（这种情况在LONG模式下较少见）
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) - order.quantity

            elif self.config.mode == StrategyMode.SHORT:
                # SHORT模式: 卖单增加空仓，或检查是否平多仓
                # 先检查是否有多仓需要平掉
                closed_long_pnl = self._try_close_long_position(order, kline)
                if closed_long_pnl > 0:
                    pnl = closed_long_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    # 建立空仓
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) - order.quantity

            elif self.config.mode == StrategyMode.NEUTRAL:
                # NEUTRAL模式: 先平多仓，再建空仓
                closed_long_pnl = self._try_close_long_position(order, kline)
                if closed_long_pnl > 0:
                    pnl = closed_long_pnl
                    self.capital += pnl
                    self.grid_profit += pnl
                else:
                    self.grid_positions[order.grid_idx] = self.grid_positions.get(order.grid_idx, 0) - order.quantity

        # Clean up zero positions
        self._cleanup_zero_positions()

        # Update position size
        self._update_position_size()

        # Record trade
        trade = TradeRecord(
            timestamp=kline.timestamp,
            price=order.price,
            quantity=order.quantity,
            side=order.side,
            grid_level=order.grid_idx,
            fee=fee,
            pnl=pnl,
            funding_fee=0.0,
            position_size=self.position_size,
        )
        self.trades.append(trade)

        order.is_filled = True

    def _try_close_short_position(self, order: GridOrder, kline: KlineData) -> float:
        """Try to close a short position and calculate profit.

        Args:
            order: The buy order that might close a short position
            kline: K-line data

        Returns:
            Profit from closing the short position, 0 if no short closed
        """
        # Find short positions at higher grid levels
        pnl = 0.0
        remaining_quantity = order.quantity

        # Check from highest to lowest grid level
        for sell_grid_idx in range(self.config.grid_count - 1, order.grid_idx, -1):
            if sell_grid_idx not in self.grid_positions:
                continue

            short_pos = self.grid_positions[sell_grid_idx]
            if short_pos >= 0:
                continue  # Not a short position

            # This is a short position, try to close
            abs_short_pos = abs(short_pos)
            close_quantity = min(remaining_quantity, abs_short_pos)

            sell_price = self.config.lower_price + sell_grid_idx * self.grid_gap
            position_pnl = close_quantity * (sell_price - order.price) * self.config.leverage
            pnl += position_pnl

            # Reduce the short position
            self.grid_positions[sell_grid_idx] += close_quantity
            remaining_quantity -= close_quantity

            if remaining_quantity <= 0:
                break

        return pnl if pnl > 0 else 0.0

    def _try_close_long_position(self, order: GridOrder, kline: KlineData) -> float:
        """Try to close a long position and calculate profit.

        Args:
            order: The sell order that might close a long position
            kline: K-line data

        Returns:
            Profit from closing the long position, 0 if no long closed
        """
        # Find long positions at lower grid levels
        pnl = 0.0
        remaining_quantity = order.quantity

        # Check from lowest to highest grid level
        for buy_grid_idx in range(0, order.grid_idx):
            if buy_grid_idx not in self.grid_positions:
                continue

            long_pos = self.grid_positions[buy_grid_idx]
            if long_pos <= 0:
                continue  # Not a long position

            # This is a long position, try to close
            close_quantity = min(remaining_quantity, long_pos)

            buy_price = self.config.lower_price + buy_grid_idx * self.grid_gap
            position_pnl = close_quantity * (order.price - buy_price) * self.config.leverage
            pnl += position_pnl

            # Reduce the long position
            self.grid_positions[buy_grid_idx] -= close_quantity
            remaining_quantity -= close_quantity

            if remaining_quantity <= 0:
                break

        return pnl if pnl > 0 else 0.0

    def _cleanup_zero_positions(self):
        """Remove zero positions from grid_positions."""
        zero_positions = [idx for idx, pos in self.grid_positions.items() if abs(pos) < 1e-10]
        for idx in zero_positions:
            del self.grid_positions[idx]

    def _place_counter_order(self, filled_order: GridOrder, kline: KlineData) -> None:
        """Place counter order after an order is filled.

        Args:
            filled_order: The order that was just filled
            kline: K-line data
        """
        base_quantity = self.capital_per_grid / filled_order.price
        quantity = base_quantity * self.config.leverage

        if self.config.mode == StrategyMode.LONG:
            if filled_order.side == "buy":
                # 买单成交 → 上一网格挂卖 (sell at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity, "counter")
                    self._add_pending_order(counter_order)

            elif filled_order.side == "sell":
                # 卖单成交 → 下一网格挂买 (buy at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity, "counter")
                    self._add_pending_order(counter_order)

        elif self.config.mode == StrategyMode.SHORT:
            if filled_order.side == "sell":
                # 卖单成交 → 下一网格挂买 (buy to cover at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity, "counter")
                    self._add_pending_order(counter_order)

            elif filled_order.side == "buy":
                # 买单成交 → 上一网格挂卖 (sell short at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity, "counter")
                    self._add_pending_order(counter_order)

        elif self.config.mode == StrategyMode.NEUTRAL:
            if filled_order.side == "buy":
                # 多单成交 → 上一格卖出平多 (sell to close long at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity, "counter")
                    self._add_pending_order(counter_order)

            elif filled_order.side == "sell":
                # 空单成交 → 下一格买入平空 (buy to cover short at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity, "counter")
                    self._add_pending_order(counter_order)

    def _process_funding_fees(self, kline: KlineData) -> None:
        """Process funding fees for perpetual contracts.

        Args:
            kline: K-line data
        """
        # Calculate current position size from grid positions (may be different due to recent trades)
        current_position_size = self._calculate_position_size()

        if self.config.funding_rate == 0 or current_position_size == 0:
            return

        funding_interval_ms = self.config.funding_interval * 60 * 60 * 1000

        if self.last_funding_time == 0:
            self.last_funding_time = kline.timestamp
            return

        if kline.timestamp - self.last_funding_time >= funding_interval_ms:
            # Calculate funding fee based on position notional value
            position_notional = abs(current_position_size) * kline.close
            funding_amount = position_notional * self.config.funding_rate

            if current_position_size > 0:
                # Long position pays funding
                self.capital -= funding_amount
            else:
                # Short position receives funding
                self.capital += funding_amount

            self.total_funding_fees += abs(funding_amount)
            self.last_funding_time = kline.timestamp

    def _calculate_position_size(self) -> float:
        """Calculate current position size from grid positions.

        Returns:
            Current position size (positive for long, negative for short)
        """
        return sum(self.grid_positions.values())

    def _calculate_current_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized PnL.

        Args:
            current_price: Current market price

        Returns:
            Current equity
        """
        unrealized_pnl = 0.0

        # Calculate unrealized PnL for all grid positions
        for grid_idx, position in self.grid_positions.items():
            if abs(position) < 1e-10:
                continue

            entry_price = self.config.lower_price + grid_idx * self.grid_gap

            if position > 0:  # Long position
                unrealized_pnl += position * (current_price - entry_price)
            else:  # Short position (position is negative)
                unrealized_pnl += abs(position) * (entry_price - current_price)

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

        # Calculate unrealized PnL from current positions using last price
        unrealized_pnl = 0.0
        if self.last_price > 0:
            for grid_idx, position in self.grid_positions.items():
                if abs(position) < 1e-10:
                    continue

                entry_price = self.config.lower_price + grid_idx * self.grid_gap

                if position > 0:  # Long position
                    unrealized_pnl += position * (self.last_price - entry_price)
                else:  # Short position (position is negative)
                    unrealized_pnl += abs(position) * (entry_price - self.last_price)

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
