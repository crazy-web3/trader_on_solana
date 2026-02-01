"""Tests for PositionWeightCalculator component."""

import pytest
import math
from strategy_engine.components.position_weight_calculator import (
    PositionWeightCalculator,
    VolatilityCalculator,
    WeightConfig
)


class TestPositionWeightCalculator:
    """Tests for PositionWeightCalculator."""
    
    def test_uniform_weights(self):
        """Test uniform weight calculation."""
        calc = PositionWeightCalculator()
        
        weights = calc.calculate_uniform_weights(10)
        
        assert len(weights) == 10
        assert all(abs(w - 0.1) < 1e-6 for w in weights)
        assert abs(sum(weights) - 1.0) < 1e-6
    
    def test_std_dev_weights_with_data(self):
        """Test standard deviation based weights."""
        calc = PositionWeightCalculator()
        
        # Historical prices around 45000 with std dev ~1000
        historical_prices = [
            44000, 45000, 46000, 44500, 45500,
            43000, 47000, 45000, 44000, 46000
        ]
        
        grid_prices, weights = calc.calculate_std_dev_weights(
            historical_prices,
            grid_count=7,
            lower_price=40000,
            upper_price=50000
        )
        
        assert len(grid_prices) > 0
        assert len(weights) == len(grid_prices)
        assert abs(sum(weights) - 1.0) < 1e-6
    
    def test_std_dev_weights_insufficient_data(self):
        """Test fallback to uniform when insufficient data."""
        calc = PositionWeightCalculator()
        
        grid_prices, weights = calc.calculate_std_dev_weights(
            [],
            grid_count=10,
            lower_price=40000,
            upper_price=50000
        )
        
        assert len(grid_prices) == 10
        assert len(weights) == 10
        assert all(abs(w - 0.1) < 1e-6 for w in weights)
    
    def test_atr_based_spacing(self):
        """Test ATR-based grid spacing."""
        calc = PositionWeightCalculator()
        
        # Historical data: (high, low, close)
        historical_data = [
            (45500, 44500, 45000),
            (46000, 45000, 45500),
            (46500, 45500, 46000),
            (47000, 46000, 46500),
            (46500, 45500, 46000),
        ]
        
        base_spacing = 1000.0
        adjusted_spacing = calc.calculate_atr_based_spacing(
            historical_data,
            base_spacing,
            period=3
        )
        
        # ATR should adjust spacing
        assert adjusted_spacing > 0
        # With volatility, spacing should be wider
        assert adjusted_spacing >= base_spacing
    
    def test_atr_spacing_insufficient_data(self):
        """Test ATR spacing with insufficient data."""
        calc = PositionWeightCalculator()
        
        base_spacing = 1000.0
        adjusted_spacing = calc.calculate_atr_based_spacing(
            [],
            base_spacing,
            period=14
        )
        
        # Should return base spacing
        assert adjusted_spacing == base_spacing
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        calc = PositionWeightCalculator()
        
        capital = 10000.0
        price = 45000.0
        weight = 0.1
        leverage = 2.0
        
        quantity = calc.calculate_position_size(capital, price, weight, leverage)
        
        # Expected: (10000 * 0.1 * 2.0) / 45000 = 0.0444...
        expected = (capital * weight * leverage) / price
        assert abs(quantity - expected) < 1e-6
    
    def test_position_size_zero_price(self):
        """Test position size with zero price."""
        calc = PositionWeightCalculator()
        
        quantity = calc.calculate_position_size(10000.0, 0.0, 0.1, 1.0)
        
        assert quantity == 0.0
    
    def test_dynamic_weights_distance(self):
        """Test dynamic weights based on distance."""
        calc = PositionWeightCalculator()
        
        current_price = 45000.0
        grid_prices = [40000, 42000, 44000, 46000, 48000, 50000]
        
        weights = calc.calculate_dynamic_weights(
            current_price,
            grid_prices,
            method="distance"
        )
        
        assert len(weights) == len(grid_prices)
        assert abs(sum(weights) - 1.0) < 1e-6
        
        # Prices closer to current should have higher weights
        # Find index of closest price
        closest_idx = min(range(len(grid_prices)), 
                         key=lambda i: abs(grid_prices[i] - current_price))
        
        # Closest price should have highest weight
        assert weights[closest_idx] == max(weights)
    
    def test_dynamic_weights_exponential(self):
        """Test dynamic weights with exponential decay."""
        calc = PositionWeightCalculator()
        
        current_price = 45000.0
        grid_prices = [40000, 42000, 44000, 46000, 48000, 50000]
        
        weights = calc.calculate_dynamic_weights(
            current_price,
            grid_prices,
            method="exponential"
        )
        
        assert len(weights) == len(grid_prices)
        assert abs(sum(weights) - 1.0) < 1e-6
    
    def test_get_weight_for_grid(self):
        """Test getting weight for specific grid."""
        calc = PositionWeightCalculator()
        
        grid_prices = [40000, 45000, 50000]
        weights = [0.3, 0.4, 0.3]
        
        weight = calc.get_weight_for_grid(1, grid_prices, weights)
        
        assert weight == 0.4
    
    def test_get_weight_for_grid_out_of_range(self):
        """Test getting weight for out of range grid."""
        calc = PositionWeightCalculator()
        
        grid_prices = [40000, 45000, 50000]
        weights = [0.3, 0.4, 0.3]
        
        weight = calc.get_weight_for_grid(10, grid_prices, weights)
        
        # Should return uniform weight
        assert abs(weight - 1.0/3.0) < 1e-6


class TestVolatilityCalculator:
    """Tests for VolatilityCalculator."""
    
    def test_historical_volatility(self):
        """Test historical volatility calculation."""
        prices = [100, 102, 101, 103, 102, 104, 103, 105]
        
        vol = VolatilityCalculator.calculate_historical_volatility(prices, period=5)
        
        assert vol > 0
        # Volatility should be reasonable (not too extreme)
        assert 0 < vol < 10
    
    def test_historical_volatility_insufficient_data(self):
        """Test volatility with insufficient data."""
        vol = VolatilityCalculator.calculate_historical_volatility([], period=20)
        
        assert vol == 0.0
    
    def test_historical_volatility_single_price(self):
        """Test volatility with single price."""
        vol = VolatilityCalculator.calculate_historical_volatility([100], period=20)
        
        assert vol == 0.0
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        # Historical data: (high, low, close)
        historical_data = [
            (102, 98, 100),
            (104, 100, 102),
            (106, 102, 104),
            (105, 101, 103),
            (107, 103, 105),
        ]
        
        atr = VolatilityCalculator.calculate_atr(historical_data, period=3)
        
        assert atr > 0
        # ATR should be reasonable
        assert 0 < atr < 10
    
    def test_atr_insufficient_data(self):
        """Test ATR with insufficient data."""
        atr = VolatilityCalculator.calculate_atr([], period=14)
        
        assert atr == 0.0
    
    def test_atr_single_data_point(self):
        """Test ATR with single data point."""
        historical_data = [(100, 98, 99)]
        
        atr = VolatilityCalculator.calculate_atr(historical_data, period=14)
        
        assert atr == 0.0


class TestWeightConfig:
    """Tests for WeightConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = WeightConfig()
        
        assert config.method == "uniform"
        assert len(config.std_dev_multipliers) == 7
        assert len(config.weights) == 6
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = WeightConfig(
            method="std_dev",
            std_dev_multipliers=[-2, -1, 0, 1, 2],
            weights=[0.2, 0.3, 0.0, 0.3, 0.2]
        )
        
        assert config.method == "std_dev"
        assert len(config.std_dev_multipliers) == 5
        assert len(config.weights) == 5


class TestIntegration:
    """Integration tests for position weight calculator."""
    
    def test_complete_workflow(self):
        """Test complete workflow from historical data to position sizes."""
        # Setup
        calc = PositionWeightCalculator()
        historical_prices = [
            44000, 45000, 46000, 44500, 45500,
            43000, 47000, 45000, 44000, 46000
        ]
        
        # Calculate grid prices and weights
        grid_prices, weights = calc.calculate_std_dev_weights(
            historical_prices,
            grid_count=7,
            lower_price=40000,
            upper_price=50000
        )
        
        # Calculate position sizes
        capital = 10000.0
        leverage = 2.0
        
        position_sizes = []
        for price, weight in zip(grid_prices, weights):
            size = calc.calculate_position_size(capital, price, weight, leverage)
            position_sizes.append(size)
        
        # Verify
        assert len(position_sizes) == len(grid_prices)
        assert all(size > 0 for size in position_sizes)
        
        # Total position value should not exceed capital * leverage
        total_value = sum(size * price for size, price in zip(position_sizes, grid_prices))
        assert total_value <= capital * leverage * 1.01  # Allow 1% tolerance
    
    def test_volatility_based_adjustment(self):
        """Test volatility-based grid adjustment."""
        calc = PositionWeightCalculator()
        
        # Low volatility data
        low_vol_data = [
            (45100, 44900, 45000),
            (45200, 44800, 45000),
            (45150, 44850, 45000),
        ]
        
        # High volatility data
        high_vol_data = [
            (46000, 44000, 45000),
            (47000, 43000, 45000),
            (48000, 42000, 45000),
        ]
        
        base_spacing = 1000.0
        
        low_vol_spacing = calc.calculate_atr_based_spacing(
            low_vol_data, base_spacing, period=2
        )
        high_vol_spacing = calc.calculate_atr_based_spacing(
            high_vol_data, base_spacing, period=2
        )
        
        # High volatility should result in wider spacing
        assert high_vol_spacing > low_vol_spacing
