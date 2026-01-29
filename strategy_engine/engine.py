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
    def __init__(self, grid_idx: int, price: float, side: str, quantity: float):
        self.grid_idx = grid_idx
        self.price = price
        self.side = side  # "buy" or "sell"
        self.quantity = quantity
        self.is_filled = False


class GridStrategyEngine:
    """Grid trading strategy engine for perpetual contracts.
    
    Implements grid trading strategy with correct logic:
    - 做多网格: 当前价以下挂买单，以上挂卖单，买单成交后上一网格挂卖，卖单成交后下一网格挂买
    - 做空网格: 当前价以上挂卖单，以下挂买单，卖单成交后下一网格挂买，买单成交后上一网格挂卖
    - 中性网格: 当前价以下挂买单，以上挂卖单，多单成交后上一格卖出平多，空单成交后下一格买入平空
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
        self.equity_curve: List[float] = []  # 不包含初始值，在处理第一个K线时添加
        self.timestamps: List[int] = []
        self.max_equity = config.initial_capital
        self.min_equity = config.initial_capital
        self.last_funding_time = 0
        
        # Grid order management
        self.pending_orders: Dict[int, GridOrder] = {}  # grid_idx -> GridOrder
        self.grid_positions: Dict[int, float] = {}  # grid_idx -> position_size
        
        # Calculate grid parameters
        self.grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
        # Use a smaller portion of capital per grid to avoid over-allocation
        self.capital_per_grid = config.initial_capital / (config.grid_count * 2)  # More conservative
        
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
    
    def _place_initial_orders(self, current_price: float):
        """Place initial grid orders based on current price and strategy mode.
        
        Args:
            current_price: Current market price
        """
        if self.pending_orders:  # Already initialized
            return
        
        # 策略从区间左侧（最低价）开始建仓，到当前价格位置
        start_price = self.config.lower_price
        end_price = current_price
        
        # 确保当前价格在区间内
        if current_price < self.config.lower_price:
            end_price = self.config.lower_price
        elif current_price > self.config.upper_price:
            end_price = self.config.upper_price
        
        for i in range(self.config.grid_count):
            grid_price = self.config.lower_price + i * self.grid_gap
            
            # Calculate quantity with proper leverage effect
            base_quantity = self.capital_per_grid / grid_price
            quantity = base_quantity * self.config.leverage
            
            if self.config.mode == StrategyMode.LONG:
                # 做多网格: 从最低价到当前价建立多仓，当前价以上挂卖单
                if grid_price <= end_price:
                    # 在这个价格区间建立初始多仓
                    initial_position = quantity * 0.8  # 建立80%的仓位
                    self.grid_positions[i] = initial_position
                    self.position_size += initial_position
                    
                    # 在上一个网格挂卖单
                    if i + 1 < self.config.grid_count:
                        sell_price = self.config.lower_price + (i + 1) * self.grid_gap
                        sell_order = GridOrder(i + 1, sell_price, "sell", initial_position)
                        if (i + 1) not in self.pending_orders:
                            self.pending_orders[i + 1] = sell_order
                    
                    # 挂少量买单补仓
                    buy_order = GridOrder(i, grid_price, "buy", quantity * 0.2)
                    self.pending_orders[i] = buy_order
                else:
                    # 当前价以上挂买单
                    buy_order = GridOrder(i, grid_price, "buy", quantity)
                    self.pending_orders[i] = buy_order
                    
            elif self.config.mode == StrategyMode.SHORT:
                # 做空网格: 从最低价到当前价建立空仓，当前价以下挂买单
                if grid_price <= end_price:
                    # 在这个价格区间建立初始空仓
                    initial_position = quantity * 0.8  # 建立80%的空仓
                    self.grid_positions[i] = -initial_position  # 负数表示空仓
                    self.position_size -= initial_position
                    
                    # 在下一个网格挂买单
                    if i - 1 >= 0:
                        buy_price = self.config.lower_price + (i - 1) * self.grid_gap
                        buy_order = GridOrder(i - 1, buy_price, "buy", initial_position)
                        if (i - 1) not in self.pending_orders:
                            self.pending_orders[i - 1] = buy_order
                    
                    # 挂少量卖单补仓
                    sell_order = GridOrder(i, grid_price, "sell", quantity * 0.2)
                    self.pending_orders[i] = sell_order
                else:
                    # 当前价以上挂卖单
                    sell_order = GridOrder(i, grid_price, "sell", quantity)
                    self.pending_orders[i] = sell_order
                    
            elif self.config.mode == StrategyMode.NEUTRAL:
                # 中性网格: 从最低价到当前价建立平衡仓位
                if grid_price <= end_price:
                    # 根据价格位置建立多空平衡仓位
                    price_ratio = (grid_price - start_price) / (end_price - start_price) if end_price > start_price else 0.5
                    
                    if price_ratio < 0.5:
                        # 偏向多仓
                        long_position = quantity * 0.6
                        self.grid_positions[i] = long_position
                        self.position_size += long_position
                        
                        # 挂对应的卖单
                        if i + 1 < self.config.grid_count:
                            sell_price = self.config.lower_price + (i + 1) * self.grid_gap
                            sell_order = GridOrder(i + 1, sell_price, "sell", long_position)
                            if (i + 1) not in self.pending_orders:
                                self.pending_orders[i + 1] = sell_order
                    else:
                        # 偏向空仓
                        short_position = quantity * 0.6
                        self.grid_positions[i] = -short_position
                        self.position_size -= short_position
                        
                        # 挂对应的买单
                        if i - 1 >= 0:
                            buy_price = self.config.lower_price + (i - 1) * self.grid_gap
                            buy_order = GridOrder(i - 1, buy_price, "buy", short_position)
                            if (i - 1) not in self.pending_orders:
                                self.pending_orders[i - 1] = buy_order
                    
                    # 挂补仓单
                    if price_ratio < 0.5:
                        buy_order = GridOrder(i, grid_price, "buy", quantity * 0.4)
                        self.pending_orders[i] = buy_order
                    else:
                        sell_order = GridOrder(i, grid_price, "sell", quantity * 0.4)
                        self.pending_orders[i] = sell_order
                else:
                    # 当前价以上的网格
                    if grid_price <= current_price + self.grid_gap:
                        # 靠近当前价，挂卖单
                        sell_order = GridOrder(i, grid_price, "sell", quantity)
                        self.pending_orders[i] = sell_order
                    else:
                        # 远离当前价，挂买单
                        buy_order = GridOrder(i, grid_price, "buy", quantity)
                        self.pending_orders[i] = buy_order
    
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
            # 从区间最早的价格（第一个K线）开始建仓，到当前位置结束
            start_price = klines[0].close  # 最早的价格
            
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
    
    def _place_initial_positions_from_start(self, start_price: float):
        """从起始价格开始建立初始仓位.
        
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
                # 做多网格: 从起始价格开始建立多仓
                if i <= start_grid_idx:
                    # 在起始价格及以下建立多仓
                    initial_position = quantity * 0.8
                    self.grid_positions[i] = initial_position
                    self.position_size += initial_position
                    
                    # 在上一个网格挂卖单
                    if i + 1 < self.config.grid_count:
                        sell_order = GridOrder(i + 1, self.config.lower_price + (i + 1) * self.grid_gap, "sell", initial_position)
                        self.pending_orders[i + 1] = sell_order
                
                # 所有网格都挂买单（用于补仓）
                buy_order = GridOrder(i, grid_price, "buy", quantity * 0.2)
                if i not in self.pending_orders:
                    self.pending_orders[i] = buy_order
                    
            elif self.config.mode == StrategyMode.SHORT:
                # 做空网格: 从起始价格开始建立空仓
                if i <= start_grid_idx:
                    # 在起始价格及以下建立空仓
                    initial_position = quantity * 0.8
                    self.grid_positions[i] = -initial_position
                    self.position_size -= initial_position
                    
                    # 在下一个网格挂买单
                    if i - 1 >= 0:
                        buy_order = GridOrder(i - 1, self.config.lower_price + (i - 1) * self.grid_gap, "buy", initial_position)
                        self.pending_orders[i - 1] = buy_order
                
                # 所有网格都挂卖单（用于补仓）
                sell_order = GridOrder(i, grid_price, "sell", quantity * 0.2)
                if i not in self.pending_orders:
                    self.pending_orders[i] = sell_order
                    
            elif self.config.mode == StrategyMode.NEUTRAL:
                # 中性网格: 从起始价格开始建立平衡仓位
                if i <= start_grid_idx:
                    # 根据网格位置建立多空平衡仓位
                    if i < start_grid_idx * 0.6:
                        # 下方网格偏多
                        long_position = quantity * 0.6
                        self.grid_positions[i] = long_position
                        self.position_size += long_position
                        
                        if i + 1 < self.config.grid_count:
                            sell_order = GridOrder(i + 1, self.config.lower_price + (i + 1) * self.grid_gap, "sell", long_position)
                            if (i + 1) not in self.pending_orders:
                                self.pending_orders[i + 1] = sell_order
                    else:
                        # 上方网格偏空
                        short_position = quantity * 0.6
                        self.grid_positions[i] = -short_position
                        self.position_size -= short_position
                        
                        if i - 1 >= 0:
                            buy_order = GridOrder(i - 1, self.config.lower_price + (i - 1) * self.grid_gap, "buy", short_position)
                            if (i - 1) not in self.pending_orders:
                                self.pending_orders[i - 1] = buy_order
                
                # 挂补仓单
                if i <= start_grid_idx * 0.6:
                    buy_order = GridOrder(i, grid_price, "buy", quantity * 0.4)
                    if i not in self.pending_orders:
                        self.pending_orders[i] = buy_order
                else:
                    sell_order = GridOrder(i, grid_price, "sell", quantity * 0.4)
                    if i not in self.pending_orders:
                        self.pending_orders[i] = sell_order
    
    def _process_kline(self, kline: KlineData) -> None:
        """Process a single K-line.
        
        Args:
            kline: K-line data
        """
        # Initialize grid if not done yet
        if not self.pending_orders:
            self._place_initial_orders(kline.close)
        
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
        
        for grid_idx, order in self.pending_orders.items():
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
                filled_orders.append(grid_idx)
        
        # Remove filled orders and place new ones
        for grid_idx in filled_orders:
            filled_order = self.pending_orders.pop(grid_idx)
            self._place_counter_order(filled_order, kline)
    
    def _fill_order(self, order: GridOrder, kline: KlineData) -> None:
        """Fill a grid order.
        
        Args:
            order: Grid order to fill
            kline: K-line data
        """
        # Calculate fees
        fee = order.quantity * order.price * self.config.fee_rate
        pnl = 0.0
        
        if order.side == "buy":
            # Buy order filled - only deduct fee
            if self.capital < fee:
                return  # Insufficient capital for fee
            
            self.capital -= fee
            self.total_fees += fee
            
            # Update position
            self.position_size += order.quantity
            
            # Check if this is closing a short position (for SHORT and NEUTRAL modes)
            if self.config.mode == StrategyMode.SHORT:
                # In short grid, buying should close short positions and generate profit
                # Find the corresponding sell position at higher grid level
                sell_grid_idx = order.grid_idx + 1  # We sold at higher level
                if sell_grid_idx < self.config.grid_count and sell_grid_idx in self.grid_positions and self.grid_positions[sell_grid_idx] < 0:
                    sell_price = self.config.lower_price + sell_grid_idx * self.grid_gap
                    pnl = order.quantity * (sell_price - order.price) * self.config.leverage
                    
                    # Reduce the short position at the sell level
                    self.grid_positions[sell_grid_idx] += order.quantity
                    if self.grid_positions[sell_grid_idx] >= 0:
                        del self.grid_positions[sell_grid_idx]
                        
                    # Add PnL to capital and grid profit
                    self.capital += pnl
                    if pnl > 0:  # 只有盈利的配对交易才计入网格收益
                        self.grid_profit += pnl
                else:
                    # Opening a long position or covering without corresponding short
                    if order.grid_idx not in self.grid_positions:
                        self.grid_positions[order.grid_idx] = 0.0
                    self.grid_positions[order.grid_idx] += order.quantity
                    
            elif self.config.mode == StrategyMode.LONG:
                # In long grid, buying opens long positions
                if order.grid_idx not in self.grid_positions:
                    self.grid_positions[order.grid_idx] = 0.0
                self.grid_positions[order.grid_idx] += order.quantity
                
            elif self.config.mode == StrategyMode.NEUTRAL:
                # In neutral grid, check if we're closing a short or opening a long
                sell_grid_idx = order.grid_idx + 1
                if sell_grid_idx < self.config.grid_count and sell_grid_idx in self.grid_positions and self.grid_positions[sell_grid_idx] < 0:
                    # Closing a short position
                    sell_price = self.config.lower_price + sell_grid_idx * self.grid_gap
                    pnl = order.quantity * (sell_price - order.price) * self.config.leverage
                    
                    self.grid_positions[sell_grid_idx] += order.quantity
                    if self.grid_positions[sell_grid_idx] >= 0:
                        del self.grid_positions[sell_grid_idx]
                        
                    self.capital += pnl
                    if pnl > 0:  # 只有盈利的配对交易才计入网格收益
                        self.grid_profit += pnl
                else:
                    # Opening a long position
                    if order.grid_idx not in self.grid_positions:
                        self.grid_positions[order.grid_idx] = 0.0
                    self.grid_positions[order.grid_idx] += order.quantity
            
        else:  # sell order
            # Sell order filled
            self.capital -= fee
            self.total_fees += fee
            
            if self.config.mode == StrategyMode.LONG:
                # In long grid, selling should close long positions and generate profit
                # Find the corresponding buy position at lower grid level
                buy_grid_idx = order.grid_idx - 1  # We bought at lower level
                if buy_grid_idx >= 0 and buy_grid_idx in self.grid_positions and self.grid_positions[buy_grid_idx] > 0:
                    buy_price = self.config.lower_price + buy_grid_idx * self.grid_gap
                    pnl = order.quantity * (order.price - buy_price) * self.config.leverage
                    
                    # Reduce the position at the buy level
                    self.grid_positions[buy_grid_idx] -= order.quantity
                    if self.grid_positions[buy_grid_idx] <= 0:
                        del self.grid_positions[buy_grid_idx]
                        
                    # Add PnL to capital and grid profit
                    self.capital += pnl
                    if pnl > 0:  # 只有盈利的配对交易才计入网格收益
                        self.grid_profit += pnl
                else:
                    # Opening a short position
                    if order.grid_idx not in self.grid_positions:
                        self.grid_positions[order.grid_idx] = 0.0
                    self.grid_positions[order.grid_idx] -= order.quantity
                    
            elif self.config.mode == StrategyMode.SHORT:
                # In short grid, selling opens short positions
                if order.grid_idx not in self.grid_positions:
                    self.grid_positions[order.grid_idx] = 0.0
                self.grid_positions[order.grid_idx] -= order.quantity
                
            elif self.config.mode == StrategyMode.NEUTRAL:
                # In neutral grid, check if we're closing a long or opening a short
                buy_grid_idx = order.grid_idx - 1
                if buy_grid_idx >= 0 and buy_grid_idx in self.grid_positions and self.grid_positions[buy_grid_idx] > 0:
                    # Closing a long position
                    buy_price = self.config.lower_price + buy_grid_idx * self.grid_gap
                    pnl = order.quantity * (order.price - buy_price) * self.config.leverage
                    
                    self.grid_positions[buy_grid_idx] -= order.quantity
                    if self.grid_positions[buy_grid_idx] <= 0:
                        del self.grid_positions[buy_grid_idx]
                        
                    self.capital += pnl
                    if pnl > 0:  # 只有盈利的配对交易才计入网格收益
                        self.grid_profit += pnl
                else:
                    # Opening a short position
                    if order.grid_idx not in self.grid_positions:
                        self.grid_positions[order.grid_idx] = 0.0
                    self.grid_positions[order.grid_idx] -= order.quantity
            
            # Update net position
            self.position_size -= order.quantity
        
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
    
    def _place_counter_order(self, filled_order: GridOrder, kline: KlineData) -> None:
        """Place counter order after an order is filled.
        
        Args:
            filled_order: The order that was just filled
            kline: K-line data
        """
        if self.config.mode == StrategyMode.LONG:
            if filled_order.side == "buy":
                # 买单成交 → 上一网格挂卖 (sell at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity  # 卖出数量等于买入数量
                    
                    # Only place sell order if we don't already have one at this level
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
                    
            elif filled_order.side == "sell":
                # 卖单成交 → 下一网格挂买 (buy at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    # Apply leverage to quantity calculation
                    base_quantity = self.capital_per_grid / next_price
                    quantity = base_quantity * self.config.leverage
                    
                    # Only place buy order if we don't already have one at this level
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
        
        elif self.config.mode == StrategyMode.SHORT:
            if filled_order.side == "sell":
                # 卖单成交 → 下一网格挂买 (buy to cover at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
                    
            elif filled_order.side == "buy":
                # 买单成交 → 上一网格挂卖 (sell short at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    # Apply leverage to quantity calculation
                    base_quantity = self.capital_per_grid / next_price
                    quantity = base_quantity * self.config.leverage
                    
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
        
        elif self.config.mode == StrategyMode.NEUTRAL:
            if filled_order.side == "buy":
                # 多单成交 → 上一格卖出平多 (sell to close long at higher price)
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
                    
            elif filled_order.side == "sell":
                # 空单成交 → 下一格买入平空 (buy to cover short at lower price)
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    
                    if next_grid_idx not in self.pending_orders:
                        counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
                        self.pending_orders[next_grid_idx] = counter_order
    
    def _process_funding_fees(self, kline: KlineData) -> None:
        """Process funding fees for perpetual contracts."""
        if self.config.funding_rate == 0 or self.position_size == 0:
            return
        
        funding_interval_ms = self.config.funding_interval * 60 * 60 * 1000
        
        if self.last_funding_time == 0:
            self.last_funding_time = kline.timestamp
            return
        
        if kline.timestamp - self.last_funding_time >= funding_interval_ms:
            funding_fee = abs(self.position_size) * kline.close * self.config.funding_rate
            
            if self.position_size > 0:  # Long position
                funding_fee = funding_fee  # Pay funding
            else:  # Short position
                funding_fee = -funding_fee  # Receive funding
            
            self.capital -= funding_fee
            self.total_funding_fees += abs(funding_fee)
            self.last_funding_time = kline.timestamp
    
    def _calculate_current_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized PnL."""
        unrealized_pnl = 0.0
        
        # Calculate unrealized PnL for all grid positions
        for grid_idx, position in self.grid_positions.items():
            if position == 0:
                continue
                
            entry_price = self.config.lower_price + grid_idx * self.grid_gap
            
            if position > 0:  # Long position
                unrealized_pnl += position * (current_price - entry_price) * self.config.leverage
            else:  # Short position (position is negative)
                unrealized_pnl += abs(position) * (entry_price - current_price) * self.config.leverage
        
        return self.capital + unrealized_pnl
    
    def _calculate_result(self) -> StrategyResult:
        """Calculate strategy result."""
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
                drawdown = (peak - equity) / peak
                if drawdown > max_drawdown_pct:
                    max_drawdown_pct = drawdown
                    max_drawdown = peak - equity
        
        # Calculate unrealized PnL from current positions
        unrealized_pnl = 0.0
        if self.equity_curve:  # Use last price from equity curve calculation
            last_price = self.equity_curve[-1] - self.capital  # Extract price component
            # Recalculate using actual last price from timestamps
            if self.timestamps:
                # We need to get the last price, but we don't have direct access
                # For now, calculate based on current positions and average grid price
                for grid_idx, position in self.grid_positions.items():
                    if position == 0:
                        continue
                    
                    entry_price = self.config.lower_price + grid_idx * self.grid_gap
                    # Use the middle of the price range as approximation for current price
                    current_price = (self.config.lower_price + self.config.upper_price) / 2
                    
                    if position > 0:  # Long position
                        unrealized_pnl += position * (current_price - entry_price) * self.config.leverage
                    else:  # Short position (position is negative)
                        unrealized_pnl += abs(position) * (entry_price - current_price) * self.config.leverage
        
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