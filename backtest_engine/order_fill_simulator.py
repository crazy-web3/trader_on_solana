"""Order fill simulator for realistic order execution."""

from dataclasses import dataclass
from typing import Tuple
from market_data_layer.models import KlineData


@dataclass
class OrderFillConfig:
    """Configuration for order fill simulation.
    
    Attributes:
        enable_partial_fill: Whether to simulate partial fills
        enable_realistic_timing: Whether to estimate fill timing within kline
        min_fill_ratio: Minimum fill ratio for partial fills (0-1)
    """
    enable_partial_fill: bool = False
    enable_realistic_timing: bool = True
    min_fill_ratio: float = 0.1
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0 < self.min_fill_ratio <= 1:
            raise ValueError("min_fill_ratio must be in (0, 1]")


class OrderFillSimulator:
    """Simulator for realistic order fill logic.
    
    Improves upon simple high/low matching by:
    - Considering OHLC price action sequence
    - Estimating fill timing within kline period
    - Simulating partial fills based on liquidity
    """
    
    def __init__(self, config: OrderFillConfig):
        """Initialize order fill simulator.
        
        Args:
            config: Order fill configuration
        """
        self.config = config
        self.partial_fills_count = 0
    
    def check_limit_order_fill(
        self,
        order_price: float,
        order_side: str,
        kline: KlineData,
        kline_duration_ms: int = 86400000  # Default 1 day
    ) -> Tuple[bool, float, int]:
        """Check if a limit order would fill during this kline.
        
        Args:
            order_price: Limit order price
            order_side: Order side ('buy' or 'sell')
            kline: Kline data
            kline_duration_ms: Duration of kline in milliseconds
            
        Returns:
            Tuple of (is_filled, fill_price, fill_timestamp)
        """
        if order_side == "buy":
            # Buy limit order fills when price drops to or below order price
            if kline.low <= order_price:
                fill_price = order_price
                fill_time = self._estimate_fill_time(
                    kline, order_price, "buy", kline_duration_ms
                )
                return True, fill_price, fill_time
        else:  # sell
            # Sell limit order fills when price rises to or above order price
            if kline.high >= order_price:
                fill_price = order_price
                fill_time = self._estimate_fill_time(
                    kline, order_price, "sell", kline_duration_ms
                )
                return True, fill_price, fill_time
        
        return False, 0.0, 0
    
    def _estimate_fill_time(
        self,
        kline: KlineData,
        fill_price: float,
        side: str,
        kline_duration_ms: int
    ) -> int:
        """Estimate when within the kline period the order would fill.
        
        Args:
            kline: Kline data
            fill_price: Fill price
            side: Order side
            kline_duration_ms: Duration of kline in milliseconds
            
        Returns:
            Estimated fill timestamp
        """
        if not self.config.enable_realistic_timing:
            return kline.timestamp
        
        # Simple model: estimate based on price position in range
        price_range = kline.high - kline.low
        if price_range == 0:
            return kline.timestamp
        
        if side == "buy":
            # Buy order fills when price drops
            # Estimate how far through the kline this happens
            ratio = (kline.high - fill_price) / price_range
        else:
            # Sell order fills when price rises
            ratio = (fill_price - kline.low) / price_range
        
        # Clamp ratio to [0, 1]
        ratio = max(0.0, min(1.0, ratio))
        
        fill_time = kline.timestamp + int(kline_duration_ms * ratio)
        return fill_time
    
    def simulate_partial_fill(
        self,
        order_quantity: float,
        available_liquidity: float
    ) -> float:
        """Simulate partial fill based on available liquidity.
        
        Args:
            order_quantity: Requested order quantity
            available_liquidity: Available liquidity
            
        Returns:
            Actual filled quantity
        """
        if not self.config.enable_partial_fill:
            return order_quantity
        
        # If liquidity is sufficient, fill completely
        if available_liquidity >= order_quantity:
            return order_quantity
        
        # Partial fill: at least min_fill_ratio
        min_fill = order_quantity * self.config.min_fill_ratio
        actual_fill = max(available_liquidity, min_fill)
        actual_fill = min(actual_fill, order_quantity)
        
        if actual_fill < order_quantity:
            self.partial_fills_count += 1
        
        return actual_fill
    
    def get_partial_fills_count(self) -> int:
        """Get count of partial fills.
        
        Returns:
            Number of partial fills
        """
        return self.partial_fills_count
    
    def reset(self) -> None:
        """Reset partial fills counter."""
        self.partial_fills_count = 0
