"""Position weight calculator for dynamic grid trading.

This module implements various position weighting strategies:
1. Standard deviation based weighting (TruthHun style)
2. ATR (Average True Range) based weighting
3. Uniform weighting (default)
"""

from typing import List, Tuple
import math
from dataclasses import dataclass


@dataclass
class WeightConfig:
    """Configuration for position weight calculation."""
    method: str = "uniform"  # "uniform", "std_dev", "atr"
    std_dev_multipliers: List[float] = None  # For std_dev method
    weights: List[float] = None  # Corresponding weights
    
    def __post_init__(self):
        """Set default values."""
        if self.std_dev_multipliers is None:
            # Default: [-3σ, -2σ, -1σ, 0, +1σ, +2σ, +3σ]
            self.std_dev_multipliers = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
        
        if self.weights is None:
            # Default: Higher weights at extremes (mean reversion)
            self.weights = [0.5, 0.3, 0.1, 0.1, 0.3, 0.5]


class PositionWeightCalculator:
    """Calculate position weights based on various strategies.
    
    This calculator helps optimize capital allocation across grid levels
    based on market conditions and statistical properties.
    """
    
    def __init__(self, config: WeightConfig = None):
        """Initialize position weight calculator.
        
        Args:
            config: Weight calculation configuration
        """
        self.config = config or WeightConfig()
    
    def calculate_uniform_weights(self, grid_count: int) -> List[float]:
        """Calculate uniform weights for all grid levels.
        
        Args:
            grid_count: Number of grid levels
            
        Returns:
            List of weights (all equal, sum to 1.0)
        """
        weight = 1.0 / grid_count
        return [weight] * grid_count
    
    def calculate_std_dev_weights(
        self,
        historical_prices: List[float],
        grid_count: int,
        lower_price: float,
        upper_price: float
    ) -> Tuple[List[float], List[float]]:
        """Calculate weights based on standard deviation bands.
        
        Based on TruthHun's approach:
        - Calculate mean and std dev of historical prices
        - Define bands at mean ± [1σ, 2σ, 3σ]
        - Assign higher weights to extreme bands (mean reversion)
        
        Args:
            historical_prices: Historical price data
            grid_count: Number of grid levels
            lower_price: Lower bound of grid
            upper_price: Upper bound of grid
            
        Returns:
            Tuple of (grid_prices, weights)
        """
        if not historical_prices or len(historical_prices) < 2:
            # Fallback to uniform if insufficient data
            return self._calculate_uniform_grid_prices(
                grid_count, lower_price, upper_price
            ), self.calculate_uniform_weights(grid_count)
        
        # Calculate mean and standard deviation
        mean_price = sum(historical_prices) / len(historical_prices)
        variance = sum((p - mean_price) ** 2 for p in historical_prices) / len(historical_prices)
        std_dev = math.sqrt(variance)
        
        # Generate grid prices based on std dev bands
        grid_prices = []
        weights = []
        
        # Create bands: mean + multiplier * std_dev
        for i, multiplier in enumerate(self.config.std_dev_multipliers):
            price = mean_price + multiplier * std_dev
            
            # Only include prices within the specified range
            if lower_price <= price <= upper_price:
                grid_prices.append(price)
                # Use corresponding weight, or default to uniform
                if i < len(self.config.weights):
                    weights.append(self.config.weights[i])
                else:
                    weights.append(1.0 / len(self.config.std_dev_multipliers))
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        # If no prices in range, fallback to uniform
        if not grid_prices:
            return self._calculate_uniform_grid_prices(
                grid_count, lower_price, upper_price
            ), self.calculate_uniform_weights(grid_count)
        
        return grid_prices, weights
    
    def calculate_atr_based_spacing(
        self,
        historical_data: List[Tuple[float, float, float]],  # (high, low, close)
        base_spacing: float,
        period: int = 14
    ) -> float:
        """Calculate grid spacing based on ATR (Average True Range).
        
        ATR measures market volatility. Higher ATR = wider spacing.
        
        Args:
            historical_data: List of (high, low, close) tuples
            base_spacing: Base grid spacing
            period: ATR calculation period
            
        Returns:
            Adjusted grid spacing
        """
        if not historical_data or len(historical_data) < period:
            return base_spacing
        
        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(historical_data)):
            high, low, close = historical_data[i]
            prev_close = historical_data[i-1][2]
            
            # True Range = max(high-low, |high-prev_close|, |low-prev_close|)
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        # Calculate ATR (simple moving average of TR)
        if len(true_ranges) < period:
            period = len(true_ranges)
        
        atr = sum(true_ranges[-period:]) / period
        
        # Adjust spacing: spacing = base_spacing * (1 + atr_factor)
        # Higher ATR = wider spacing
        atr_factor = atr / base_spacing if base_spacing > 0 else 0
        adjusted_spacing = base_spacing * (1.0 + atr_factor * 0.5)
        
        return adjusted_spacing
    
    def calculate_position_size(
        self,
        capital: float,
        price: float,
        weight: float,
        leverage: float = 1.0
    ) -> float:
        """Calculate position size for a grid level.
        
        Args:
            capital: Available capital
            price: Grid level price
            weight: Weight for this grid level (0-1)
            leverage: Leverage multiplier
            
        Returns:
            Position size (quantity)
        """
        if price <= 0:
            return 0.0
        
        # Allocated capital for this grid level
        allocated_capital = capital * weight
        
        # Position size with leverage
        position_value = allocated_capital * leverage
        quantity = position_value / price
        
        return quantity
    
    def _calculate_uniform_grid_prices(
        self,
        grid_count: int,
        lower_price: float,
        upper_price: float
    ) -> List[float]:
        """Calculate uniformly spaced grid prices.
        
        Args:
            grid_count: Number of grid levels
            lower_price: Lower bound
            upper_price: Upper bound
            
        Returns:
            List of grid prices
        """
        if grid_count < 2:
            return [lower_price]
        
        gap = (upper_price - lower_price) / (grid_count - 1)
        return [lower_price + i * gap for i in range(grid_count)]
    
    def calculate_dynamic_weights(
        self,
        current_price: float,
        grid_prices: List[float],
        method: str = "distance"
    ) -> List[float]:
        """Calculate dynamic weights based on current price position.
        
        Args:
            current_price: Current market price
            grid_prices: List of grid prices
            method: Weighting method ("distance", "exponential")
            
        Returns:
            List of weights
        """
        if not grid_prices:
            return []
        
        weights = []
        
        if method == "distance":
            # Weight inversely proportional to distance from current price
            for price in grid_prices:
                distance = abs(price - current_price)
                # Avoid division by zero
                weight = 1.0 / (distance + 1.0)
                weights.append(weight)
        
        elif method == "exponential":
            # Exponential decay based on distance
            for price in grid_prices:
                distance = abs(price - current_price)
                # Normalize distance
                max_distance = max(abs(p - current_price) for p in grid_prices)
                if max_distance > 0:
                    normalized_distance = distance / max_distance
                else:
                    normalized_distance = 0
                
                # Exponential weight: e^(-k*distance)
                k = 2.0  # Decay factor
                weight = math.exp(-k * normalized_distance)
                weights.append(weight)
        
        else:
            # Default to uniform
            weights = [1.0] * len(grid_prices)
        
        # Normalize to sum to 1.0
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        
        return weights
    
    def get_weight_for_grid(
        self,
        grid_idx: int,
        grid_prices: List[float],
        weights: List[float]
    ) -> float:
        """Get weight for a specific grid level.
        
        Args:
            grid_idx: Grid index
            grid_prices: List of grid prices
            weights: List of weights
            
        Returns:
            Weight for the grid level
        """
        if not weights or grid_idx >= len(weights):
            # Default to uniform weight
            return 1.0 / len(grid_prices) if grid_prices else 0.0
        
        return weights[grid_idx]


class VolatilityCalculator:
    """Calculate market volatility metrics."""
    
    @staticmethod
    def calculate_historical_volatility(
        prices: List[float],
        period: int = 20
    ) -> float:
        """Calculate historical volatility (standard deviation of returns).
        
        Args:
            prices: Historical prices
            period: Calculation period
            
        Returns:
            Volatility (annualized)
        """
        if not prices or len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Use last 'period' returns
        recent_returns = returns[-period:] if len(returns) > period else returns
        
        # Calculate standard deviation
        mean_return = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean_return) ** 2 for r in recent_returns) / len(recent_returns)
        std_dev = math.sqrt(variance)
        
        # Annualize (assuming daily data, 252 trading days)
        annualized_vol = std_dev * math.sqrt(252)
        
        return annualized_vol
    
    @staticmethod
    def calculate_atr(
        historical_data: List[Tuple[float, float, float]],  # (high, low, close)
        period: int = 14
    ) -> float:
        """Calculate Average True Range.
        
        Args:
            historical_data: List of (high, low, close) tuples
            period: ATR period
            
        Returns:
            ATR value
        """
        if not historical_data or len(historical_data) < 2:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(historical_data)):
            high, low, close = historical_data[i]
            prev_close = historical_data[i-1][2]
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        if not true_ranges:
            return 0.0
        
        # Use last 'period' values
        recent_tr = true_ranges[-period:] if len(true_ranges) > period else true_ranges
        
        return sum(recent_tr) / len(recent_tr)
