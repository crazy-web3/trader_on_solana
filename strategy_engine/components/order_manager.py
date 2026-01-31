"""Order manager component for grid strategy engine."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from strategy_engine.models import StrategyConfig, StrategyMode
from market_data_layer.models import KlineData
import uuid


@dataclass
class GridOrder:
    """网格订单"""
    grid_idx: int         # 网格索引
    price: float          # 订单价格
    side: str            # "buy" 或 "sell"
    quantity: float      # 订单数量
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 唯一订单ID
    is_filled: bool = False      # 是否已成交


class OrderManager:
    """订单管理器，负责管理网格订单的生命周期
    
    重构说明：
    - 使用订单队列而不是单个订单字典，支持同一网格多个订单
    - 每个订单有唯一ID，便于追踪和管理
    - 订单按FIFO顺序处理
    """
    
    def __init__(self, config: StrategyConfig):
        """初始化订单管理器
        
        Args:
            config: 策略配置
        """
        self.config = config
        # 新结构：每个网格可以有多个订单（队列）
        self.grid_orders: Dict[int, List[GridOrder]] = {}
        # 按订单ID索引，便于快速查找
        self.orders_by_id: Dict[str, GridOrder] = {}
        
        self.grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
        # Use a smaller portion of capital per grid to avoid over-allocation
        self.capital_per_grid = config.initial_capital / (config.grid_count * 2)
        # Store leverage for quantity calculation
        self.leverage = config.leverage
        
        # 向后兼容：保留旧的pending_orders接口
        self.pending_orders: Dict[int, GridOrder] = {}
    
    def _add_order(self, order: GridOrder) -> None:
        """添加订单到队列
        
        Args:
            order: 要添加的订单
        """
        if order.grid_idx not in self.grid_orders:
            self.grid_orders[order.grid_idx] = []
        
        self.grid_orders[order.grid_idx].append(order)
        self.orders_by_id[order.order_id] = order
        
        # 向后兼容：更新pending_orders（只保留第一个未成交的订单）
        self._update_pending_orders_compat()
    
    def _update_pending_orders_compat(self) -> None:
        """更新向后兼容的pending_orders字典"""
        self.pending_orders = {}
        for grid_idx, orders in self.grid_orders.items():
            # 找到第一个未成交的订单
            for order in orders:
                if not order.is_filled:
                    self.pending_orders[grid_idx] = order
                    break
    
    def place_initial_orders(self, current_price: float, strategy_mode: StrategyMode) -> None:
        """根据策略模式放置初始订单
        
        Args:
            current_price: 当前市场价格
            strategy_mode: 策略模式（做多/做空/中性）
        """
        if self.grid_orders:  # Already initialized
            return
        
        # 确保当前价格在区间内
        if current_price < self.config.lower_price:
            current_price = self.config.lower_price
        elif current_price > self.config.upper_price:
            current_price = self.config.upper_price
        
        for i in range(self.config.grid_count):
            grid_price = self.config.lower_price + i * self.grid_gap
            
            # Calculate quantity WITH leverage effect
            # With leverage, we can control more position with same capital
            base_quantity = self.capital_per_grid / grid_price
            quantity = base_quantity * self.leverage
            
            if strategy_mode == StrategyMode.LONG:
                # 做多网格: 当前价以下挂买单，以上挂卖单
                # 目标：低买高卖，建立多头仓位
                if grid_price <= current_price:
                    # 当前价及以下挂买单（建立多头）
                    buy_order = GridOrder(i, grid_price, "buy", quantity)
                    self._add_order(buy_order)
                else:  # grid_price > current_price
                    # 当前价以上挂卖单（平多头）
                    sell_order = GridOrder(i, grid_price, "sell", quantity)
                    self._add_order(sell_order)
                    
            elif strategy_mode == StrategyMode.SHORT:
                # 做空网格: 当前价以上挂卖单，以下不挂单
                # 目标：高卖低买，建立空头仓位
                # 初始状态只在高价位挂卖单等待开空仓
                if grid_price > current_price:
                    # 当前价以上挂卖单（建立空头）
                    sell_order = GridOrder(i, grid_price, "sell", quantity)
                    self._add_order(sell_order)
                # 当前价及以下不挂单（等卖单成交后再挂买单平仓）
                    
            elif strategy_mode == StrategyMode.NEUTRAL:
                # 中性网格: 双向交易，不持有方向性仓位
                # 目标：通过价格波动赚取差价，保持仓位平衡
                # 策略：在每个网格上都挂买单和卖单，通过价格波动双向获利
                # 关键区别：不像做多/做空那样根据当前价格分开挂单，而是在所有网格都挂双向订单
                # 但为了避免同时成交，我们只在当前价以下挂买单，以上挂卖单
                # 真正的区别在于对手订单的处理：中性网格会更积极地平仓
                if grid_price < current_price:
                    # 当前价以下挂买单（价格下跌时开多仓）
                    buy_order = GridOrder(i, grid_price, "buy", quantity)
                    self._add_order(buy_order)
                elif grid_price > current_price:
                    # 当前价以上挂卖单（价格上涨时开空仓）
                    sell_order = GridOrder(i, grid_price, "sell", quantity)
                    self._add_order(sell_order)
                # 当前价格所在网格不挂单
    
    def check_order_fills(self, kline: KlineData) -> List[GridOrder]:
        """检查哪些订单应该成交，返回成交的订单列表
        
        Args:
            kline: K线数据
            
        Returns:
            成交的订单列表
        """
        filled_orders = []
        
        # 遍历所有网格的订单队列
        for grid_idx, orders in self.grid_orders.items():
            for order in orders:
                if order.is_filled:
                    continue
                
                # Check if order should be filled
                should_fill = False
                if order.side == "buy" and kline.low <= order.price:
                    should_fill = True
                elif order.side == "sell" and kline.high >= order.price:
                    should_fill = True
                
                if should_fill:
                    order.is_filled = True
                    filled_orders.append(order)
        
        # 更新向后兼容的pending_orders
        self._update_pending_orders_compat()
        
        return filled_orders
    
    def place_counter_order(self, filled_order: GridOrder, strategy_mode: StrategyMode) -> None:
        """在订单成交后放置对手订单
        
        重构说明：现在可以在同一网格放置多个订单，不会覆盖
        
        Args:
            filled_order: 已成交的订单
            strategy_mode: 策略模式
        """
        if strategy_mode == StrategyMode.LONG:
            if filled_order.side == "buy":
                # 做多网格：买单成交后在上一网格挂卖单
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
                    self._add_order(counter_order)
            elif filled_order.side == "sell":
                # 做多网格：卖单成交后在下一网格挂买单
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    base_quantity = self.capital_per_grid / next_price
                    quantity = base_quantity * self.leverage  # Apply leverage
                    counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
                    self._add_order(counter_order)
                        
        elif strategy_mode == StrategyMode.SHORT:
            if filled_order.side == "sell":
                # 做空网格：卖单成交后在下一网格挂买单
                if filled_order.grid_idx - 1 >= 0:
                    next_grid_idx = filled_order.grid_idx - 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    counter_order = GridOrder(next_grid_idx, next_price, "buy", quantity)
                    self._add_order(counter_order)
            elif filled_order.side == "buy":
                # 做空网格：买单成交后在上一网格挂卖单
                if filled_order.grid_idx + 1 < self.config.grid_count:
                    next_grid_idx = filled_order.grid_idx + 1
                    next_price = self.config.lower_price + next_grid_idx * self.grid_gap
                    base_quantity = self.capital_per_grid / next_price
                    quantity = base_quantity * self.leverage  # Apply leverage
                    counter_order = GridOrder(next_grid_idx, next_price, "sell", quantity)
                    self._add_order(counter_order)
                        
        elif strategy_mode == StrategyMode.NEUTRAL:
            # 中性网格：目标是保持净仓位接近零，通过对称交易获利
            # 关键区别：在对称网格挂反向订单
            # 对称逻辑：如果在网格i成交，则在网格(grid_count-1-i)挂反向订单
            # 这样可以在价格波动中双向获利，同时保持仓位平衡
            if filled_order.side == "buy":
                # 买单成交（开多仓）后，在对称网格挂卖单（平多仓）
                # 对称网格 = grid_count - 1 - current_grid
                symmetric_grid_idx = self.config.grid_count - 1 - filled_order.grid_idx
                if symmetric_grid_idx < self.config.grid_count and symmetric_grid_idx >= 0:
                    next_price = self.config.lower_price + symmetric_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    counter_order = GridOrder(symmetric_grid_idx, next_price, "sell", quantity)
                    self._add_order(counter_order)
            elif filled_order.side == "sell":
                # 卖单成交（开空仓）后，在对称网格挂买单（平空仓）
                symmetric_grid_idx = self.config.grid_count - 1 - filled_order.grid_idx
                if symmetric_grid_idx < self.config.grid_count and symmetric_grid_idx >= 0:
                    next_price = self.config.lower_price + symmetric_grid_idx * self.grid_gap
                    quantity = filled_order.quantity
                    counter_order = GridOrder(symmetric_grid_idx, next_price, "buy", quantity)
                    self._add_order(counter_order)
    
    def remove_order(self, grid_idx: int, order_id: Optional[str] = None) -> Optional[GridOrder]:
        """移除指定网格的订单
        
        Args:
            grid_idx: 网格索引
            order_id: 订单ID（可选）。如果提供，移除指定订单；否则移除第一个未成交订单
            
        Returns:
            被移除的订单，如果不存在则返回None
        """
        if grid_idx not in self.grid_orders:
            return None
        
        orders = self.grid_orders[grid_idx]
        removed_order = None
        
        if order_id:
            # 移除指定ID的订单
            for i, order in enumerate(orders):
                if order.order_id == order_id:
                    removed_order = orders.pop(i)
                    if removed_order.order_id in self.orders_by_id:
                        del self.orders_by_id[removed_order.order_id]
                    break
        else:
            # 移除第一个未成交的订单
            for i, order in enumerate(orders):
                if not order.is_filled:
                    removed_order = orders.pop(i)
                    if removed_order.order_id in self.orders_by_id:
                        del self.orders_by_id[removed_order.order_id]
                    break
        
        # 如果队列为空，删除该网格
        if not orders:
            del self.grid_orders[grid_idx]
        
        # 更新向后兼容的pending_orders
        self._update_pending_orders_compat()
        
        return removed_order
    
    def get_pending_orders(self) -> Dict[int, GridOrder]:
        """获取所有挂单（向后兼容接口）
        
        Returns:
            所有挂单的字典（每个网格只返回第一个未成交订单）
        """
        return self.pending_orders
    
    def get_all_orders(self) -> Dict[int, List[GridOrder]]:
        """获取所有订单队列
        
        Returns:
            所有订单队列的字典
        """
        return self.grid_orders
    
    def get_order_by_id(self, order_id: str) -> Optional[GridOrder]:
        """根据订单ID获取订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            订单对象，如果不存在则返回None
        """
        return self.orders_by_id.get(order_id)
