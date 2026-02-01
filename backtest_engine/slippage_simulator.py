"""Slippage simulator for realistic order execution simulation."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class SlippageConfig:
    """Configuration for slippage simulation.
    
    Attributes:
        enabled: Whether slippage simulation is enabled
        base_slippage: Base slippage percentage (e.g., 0.0001 = 0.01%)
        size_impact_factor: Factor for order size impact on slippage
        volatility_impact_factor: Factor for volatility impact on slippage
        max_slippage: Maximum allowed slippage percentage
        model: Slippage calculation model ('linear', 'sqrt', 'volatility')
    """
    enabled: bool = True
    base_slippage: float = 0.0001  # 0.01%
    size_impact_factor: float = 0.001
    volatility_impact_factor: float = 0.0005
    max_slippage: float = 0.005  # 0.5%
    model: Literal['linear', 'sqrt', 'volatility'] = 'linear'
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.base_slippage < 0:
            raise ValueError("base_slippage must be non-negative")
        if self.max_slippage < self.base_slippage:
            raise ValueError("max_slippage must be >= base_slippage")
        if self.size_impact_factor < 0:
            raise ValueError("size_impact_factor must be non-negative")
        if self.volatility_impact_factor < 0:
            raise ValueError("volatility_impact_factor must be non-negative")
        if self.model not in ['linear', 'sqrt', 'volatility']:
            raise ValueError("model must be 'linear', 'sqrt', or 'volatility'")


class SlippageSimulator:
    """Simulator for realistic slippage calculation.
    
    Calculates slippage based on:
    - Order size relative to market volume
    - Market volatility
    - Configurable slippage model
    """
    
    def __init__(self, config: SlippageConfig):
        """Initialize slippage simulator.
        
        Args:
            config: Slippage configuration
        """
        self.config = config
        self.total_slippage_cost = 0.0
    
    def calculate_slippage(
        self,
        order_size: float,
        order_price: float,
        market_volume: float,
        volatility: float
    ) -> float:
        """Calculate slippage for an order.
        
        Args:
            order_size: Order quantity
            order_price: Order price
            market_volume: Market volume for the period
            volatility: Market volatility (standard deviation of returns)
            
        Returns:
            Slippage as a percentage (e.g., 0.0001 = 0.01%)
        """
        if not self.config.enabled:
            return 0.0
        
        # Start with base slippage
        slippage = self.config.base_slippage
        
        # Calculate order size impact
        order_value = order_size * order_price
        # Avoid division by zero
        if market_volume > 0:
            size_ratio = order_value / (market_volume * order_price)
        else:
            size_ratio = 0.1  # Default to 10% if volume is unknown
        
        # Apply size impact based on model
        if self.config.model == 'linear':
            slippage += size_ratio * self.config.size_impact_factor
        elif self.config.model == 'sqrt':
            slippage += (size_ratio ** 0.5) * self.config.size_impact_factor
        
        # Add volatility impact
        slippage += volatility * self.config.volatility_impact_factor
        
        # Cap at maximum slippage
        slippage = min(slippage, self.config.max_slippage)
        
        return slippage
    
    def apply_slippage(
        self,
        order_price: float,
        slippage: float,
        side: str
    ) -> float:
        """Apply slippage to order price.
        
        Args:
            order_price: Original order price
            slippage: Slippage percentage
            side: Order side ('buy' or 'sell')
            
        Returns:
            Actual execution price after slippage
        """
        if side == "buy":
            # Buy orders slip upward (worse price)
            actual_price = order_price * (1 + slippage)
        else:  # sell
            # Sell orders slip downward (worse price)
            actual_price = order_price * (1 - slippage)
        
        # Track slippage cost (assuming 1 unit quantity for tracking)
        slippage_cost = abs(actual_price - order_price)
        self.total_slippage_cost += slippage_cost
        
        return actual_price
    
    def get_total_slippage_cost(self) -> float:
        """Get total accumulated slippage cost.
        
        Returns:
            Total slippage cost
        """
        return self.total_slippage_cost
    
    def reset(self) -> None:
        """Reset slippage cost tracking."""
        self.total_slippage_cost = 0.0
