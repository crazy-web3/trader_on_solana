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
from strategy_engine.components.order_manager import OrderManager, GridOrder
from strategy_engine.components.position_manager import PositionManager
from strategy_engine.components.margin_calculator import MarginCalculator
from strategy_engine.components.pnl_calculator import PnLCalculator
from strategy_engine.components.funding_fee_calculator import FundingFeeCalculator


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
        self.total_fees = 0.0
        self.equity_curve: List[float] = []  # 不包含初始值，在处理第一个K线时添加
        self.timestamps: List[int] = []
        self.max_equity = config.initial_capital
        self.min_equity = config.initial_capital
        
        # Initialize all components using dependency injection
        self.order_manager = OrderManager(config)
        self.position_manager = PositionManager()
        self.margin_calculator = MarginCalculator(leverage=config.leverage)
        self.pnl_calculator = PnLCalculator()
        self.funding_fee_calculator = FundingFeeCalculator(
            funding_rate=config.funding_rate,
            funding_interval=config.funding_interval
        )
        
        # Calculate grid parameters
        self.grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
        
        # Legacy attributes for backward compatibility (will be removed in later tasks)
        self.used_margin = 0.0
        self.position_size = 0.0
        self.total_funding_fees = 0.0
        self.grid_profit = 0.0
        self.pending_orders: Dict[int, GridOrder] = {}
        self.grid_positions: Dict[int, float] = {}
        self.capital_per_grid = config.initial_capital / (config.grid_count * 2)
        self.last_funding_time = 0
    
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
    
    def _place_initial_orders(self, current_price: float):
        """Place initial grid orders based on current price and strategy mode.
        
        Args:
            current_price: Current market price
        """
        # Delegate to OrderManager
        self.order_manager.place_initial_orders(current_price, self.config.mode)
        
        # Sync pending_orders for backward compatibility
        self.pending_orders = self.order_manager.get_pending_orders()
    
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
        # Initialize grid if not done yet
        if not self.pending_orders:
            self._place_initial_orders(kline.close)
        
        # Process funding fees using FundingFeeCalculator
        if self.funding_fee_calculator.should_settle_funding(kline.timestamp):
            net_position = self.position_manager.get_net_position()
            if net_position != 0:
                # Calculate funding fee (positive for long, negative for short)
                funding_fee = self.funding_fee_calculator.calculate_funding_fee(
                    net_position, kline.close
                )
                # Deduct funding fee from capital
                self.capital -= funding_fee
                self.funding_fee_calculator.add_funding_fee(funding_fee)
                self.total_funding_fees = self.funding_fee_calculator.get_total_funding_fees()
            
            # Update funding settlement time
            self.funding_fee_calculator.settle_funding(kline.timestamp)
        
        # Check for order fills using OrderManager
        filled_orders = self.order_manager.check_order_fills(kline)
        
        # Process each filled order
        for order in filled_orders:
            self._fill_order(order, kline)
            # Place counter order after fill
            self._place_counter_order(order, kline)
        
        # Update equity curve using PnLCalculator
        unrealized_pnl = self.pnl_calculator.calculate_unrealized_pnl(
            self.position_manager.get_all_positions(),
            kline.close
        )
        current_equity = self.pnl_calculator.calculate_equity(self.capital, unrealized_pnl)
        self.equity_curve.append(current_equity)
        self.timestamps.append(kline.timestamp)
        
        # Update max/min equity for drawdown calculation
        if current_equity > self.max_equity:
            self.max_equity = current_equity
        if current_equity < self.min_equity:
            self.min_equity = current_equity
    

    def _fill_order(self, order: GridOrder, kline: KlineData) -> None:
        """Fill a grid order using component-based architecture.
        
        Refactored to follow the correct order:
        1. Deduct fees first
        2. Check if margin is sufficient
        3. Find matching position
        4. If matched, calculate realized PnL and close position
        5. If not matched, open new position
        6. Update capital and margin
        
        Args:
            order: Grid order to fill
            kline: K-line data
        """
        # Step 1: Deduct fees first
        fee = order.quantity * order.price * self.config.fee_rate
        if self.capital < fee:
            return  # Insufficient capital for fee
        
        self.capital -= fee
        self.total_fees += fee
        
        # Step 2: Calculate required margin for potential opening
        required_margin = self.margin_calculator.calculate_required_margin(
            order.quantity, order.price
        )
        
        # Step 3: Find matching position using PositionManager
        matching_result = self.position_manager.find_matching_position(
            order.grid_idx, order.side, self.config.mode
        )
        
        pnl = 0.0
        
        if matching_result is not None:
            # Step 4: If matched, calculate realized PnL and close position
            matched_grid_idx, matched_position = matching_result
            
            # Calculate realized PnL using PnLCalculator
            pnl = self.pnl_calculator.calculate_realized_pnl(
                matched_position.entry_price,
                order.price,
                order.quantity,
                matched_position.side
            )
            
            # Add PnL to capital immediately
            self.capital += pnl
            
            # Add to grid profit
            self.pnl_calculator.add_realized_pnl(pnl)
            self.grid_profit = self.pnl_calculator.get_grid_profit()
            
            # Close the matched position
            self.position_manager.close_position(matched_grid_idx, order.quantity)
            
            # Release margin for closed position
            released_margin = self.margin_calculator.calculate_required_margin(
                order.quantity, matched_position.entry_price
            )
            self.margin_calculator.release_margin(released_margin)
            
            # Update legacy attributes for backward compatibility
            self.used_margin = self.margin_calculator.get_used_margin()
            
        else:
            # Step 5: If not matched, open new position
            # Check if margin is sufficient
            if not self.margin_calculator.allocate_margin(required_margin, self.capital):
                # Insufficient margin, refund the fee and abort
                self.capital += fee
                self.total_fees -= fee
                return
            
            # Determine position side based on order side
            position_side = "long" if order.side == "buy" else "short"
            
            # Open new position using PositionManager
            self.position_manager.open_position(
                order.grid_idx,
                order.quantity,
                order.price,
                position_side,
                kline.timestamp
            )
            
            # Update legacy attributes for backward compatibility
            self.used_margin = self.margin_calculator.get_used_margin()
        
        # Update net position for backward compatibility
        self.position_size = self.position_manager.get_net_position()
        
        # Sync grid_positions for backward compatibility
        self.grid_positions = {}
        for grid_idx, position in self.position_manager.get_all_positions().items():
            self.grid_positions[grid_idx] = position.quantity
        
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
        # Delegate to OrderManager
        self.order_manager.place_counter_order(filled_order, self.config.mode)
        
        # Sync pending_orders for backward compatibility
        self.pending_orders = self.order_manager.get_pending_orders()
    


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
        
        # Calculate unrealized PnL from current positions using the LAST K-line price
        unrealized_pnl = 0.0
        if self.equity_curve and self.timestamps:
            # Get the last processed K-line price from equity curve calculation
            # We need to recalculate using the actual last price, not the middle price
            # The equity curve already includes unrealized PnL, so we can derive it
            # unrealized_pnl = final_capital - capital - grid_profit + total_fees + total_funding_fees
            unrealized_pnl = final_capital - self.capital
        
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