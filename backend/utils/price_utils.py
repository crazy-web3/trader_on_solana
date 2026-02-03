"""Price calculation utilities."""

import math
from typing import List, Tuple
from market_data_layer.models import KlineData


def calculate_price_range(klines: List[KlineData]) -> Tuple[float, float]:
    """Calculate price range based on historical data.
    
    Args:
        klines: List of K-line data
        
    Returns:
        Tuple of (lower_price, upper_price)
        - lower_price: Lowest price rounded down to nearest 100
        - upper_price: Highest price rounded up to nearest 100
    """
    if not klines:
        raise ValueError("No K-line data provided")
    
    # Find the highest and lowest prices
    high_prices = [kline.high for kline in klines]
    low_prices = [kline.low for kline in klines]
    
    max_price = max(high_prices)
    min_price = min(low_prices)
    
    # Round down to nearest 100 for lower bound
    lower_price = math.floor(min_price / 100) * 100
    
    # Round up to nearest 100 for upper bound
    upper_price = math.ceil(max_price / 100) * 100
    
    return lower_price, upper_price


def calculate_grid_count(lower_price: float, upper_price: float, grid_spacing: float = 100.0) -> int:
    """Calculate grid count based on price range and spacing.
    
    Args:
        lower_price: Lower price boundary
        upper_price: Upper price boundary
        grid_spacing: Price spacing between grid levels (default: 100)
        
    Returns:
        Number of grid levels
    """
    if lower_price >= upper_price:
        raise ValueError("Lower price must be less than upper price")
    
    if grid_spacing <= 0:
        raise ValueError("Grid spacing must be positive")
    
    # Calculate the number of intervals
    price_range = upper_price - lower_price
    intervals = int(price_range / grid_spacing)
    
    # Grid count is intervals + 1 (to include both endpoints)
    grid_count = intervals + 1
    
    # Ensure minimum of 2 grids
    return max(grid_count, 2)


def get_optimal_grid_spacing(symbol: str, current_price: float) -> float:
    """Get optimal grid spacing based on symbol and current price.
    
    Args:
        symbol: Trading pair symbol
        current_price: Current price
        
    Returns:
        Optimal grid spacing (fixed at 100 for all symbols)
    """
    # Fixed grid spacing of 100 for all symbols and price ranges
    return 100.0


def calculate_adaptive_price_range(klines: List[KlineData], 
                                 expansion_factor: float = 0.0) -> Tuple[float, float]:
    """Calculate adaptive price range based on historical high/low.
    
    Args:
        klines: List of K-line data
        expansion_factor: Factor to expand the range (default: 0.0, no expansion)
        
    Returns:
        Tuple of (lower_price, upper_price) rounded to nearest 100
        - lower_price: Historical low rounded down to nearest 100
        - upper_price: Historical high rounded up to nearest 100
    """
    if not klines:
        raise ValueError("No K-line data provided")
    
    # Get basic price range (already rounded to nearest 100)
    lower_price, upper_price = calculate_price_range(klines)
    
    # Apply expansion only if expansion_factor > 0
    if expansion_factor > 0:
        price_range = upper_price - lower_price
        expansion = price_range * expansion_factor
        
        # Apply expansion and round to nearest 100
        expanded_lower = math.floor((lower_price - expansion) / 100) * 100
        expanded_upper = math.ceil((upper_price + expansion) / 100) * 100
        
        # Ensure lower price is not negative
        expanded_lower = max(expanded_lower, 100)
        
        return expanded_lower, expanded_upper
    
    # No expansion, return the basic range
    return lower_price, upper_price


def format_price_for_display(price: float) -> str:
    """Format price for display.
    
    Args:
        price: Price value
        
    Returns:
        Formatted price string
    """
    if price >= 1000:
        return f"${price:,.0f}"
    elif price >= 1:
        return f"${price:.2f}"
    else:
        return f"${price:.4f}"