"""Tests for slippage simulator."""

import pytest
from hypothesis import given, strategies as st
from backtest_engine.slippage_simulator import SlippageConfig, SlippageSimulator


class TestSlippageConfig:
    """Tests for SlippageConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SlippageConfig()
        assert config.enabled is True
        assert config.base_slippage == 0.0001
        assert config.size_impact_factor == 0.001
        assert config.volatility_impact_factor == 0.0005
        assert config.max_slippage == 0.005
        assert config.model == 'linear'
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = SlippageConfig(
            enabled=False,
            base_slippage=0.0002,
            size_impact_factor=0.002,
            volatility_impact_factor=0.001,
            max_slippage=0.01,
            model='sqrt'
        )
        assert config.enabled is False
        assert config.base_slippage == 0.0002
        assert config.size_impact_factor == 0.002
        assert config.volatility_impact_factor == 0.001
        assert config.max_slippage == 0.01
        assert config.model == 'sqrt'
    
    def test_invalid_base_slippage(self):
        """Test that negative base slippage raises error."""
        with pytest.raises(ValueError, match="base_slippage must be non-negative"):
            SlippageConfig(base_slippage=-0.001)
    
    def test_invalid_max_slippage(self):
        """Test that max_slippage < base_slippage raises error."""
        with pytest.raises(ValueError, match="max_slippage must be >= base_slippage"):
            SlippageConfig(base_slippage=0.01, max_slippage=0.005)
    
    def test_invalid_size_impact_factor(self):
        """Test that negative size_impact_factor raises error."""
        with pytest.raises(ValueError, match="size_impact_factor must be non-negative"):
            SlippageConfig(size_impact_factor=-0.001)
    
    def test_invalid_volatility_impact_factor(self):
        """Test that negative volatility_impact_factor raises error."""
        with pytest.raises(ValueError, match="volatility_impact_factor must be non-negative"):
            SlippageConfig(volatility_impact_factor=-0.001)
    
    def test_invalid_model(self):
        """Test that invalid model raises error."""
        with pytest.raises(ValueError, match="model must be"):
            SlippageConfig(model='invalid')


class TestSlippageCalculation:
    """Tests for slippage calculation."""
    
    def test_disabled_slippage_returns_zero(self):
        """Test that disabled slippage returns 0."""
        config = SlippageConfig(enabled=False)
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size=1.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.01
        )
        
        assert slippage == 0.0
    
    def test_small_order_low_slippage(self):
        """Test that small orders have low slippage."""
        config = SlippageConfig(
            base_slippage=0.0001,
            size_impact_factor=0.001,
            model='linear'
        )
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size=1.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.01
        )
        
        # Should be close to base slippage
        assert 0.0001 <= slippage <= 0.001
    
    def test_large_order_high_slippage(self):
        """Test that large orders have higher slippage."""
        config = SlippageConfig(
            base_slippage=0.0001,
            size_impact_factor=0.001,
            model='linear'
        )
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size=100.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.01
        )
        
        # Should be higher than base slippage
        assert slippage > config.base_slippage
    
    def test_high_volatility_increases_slippage(self):
        """Test that high volatility increases slippage."""
        config = SlippageConfig(
            base_slippage=0.0001,
            volatility_impact_factor=0.001
        )
        simulator = SlippageSimulator(config)
        
        low_vol_slippage = simulator.calculate_slippage(
            order_size=1.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.01
        )
        
        high_vol_slippage = simulator.calculate_slippage(
            order_size=1.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.05
        )
        
        assert high_vol_slippage > low_vol_slippage
    
    def test_max_slippage_cap(self):
        """Test that slippage is capped at max_slippage."""
        config = SlippageConfig(
            base_slippage=0.0001,
            size_impact_factor=0.01,
            max_slippage=0.005
        )
        simulator = SlippageSimulator(config)
        
        # Very large order should hit the cap
        slippage = simulator.calculate_slippage(
            order_size=10000.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.1
        )
        
        assert slippage <= config.max_slippage
    
    def test_linear_model(self):
        """Test linear slippage model."""
        config = SlippageConfig(model='linear', size_impact_factor=0.001)
        simulator = SlippageSimulator(config)
        
        slippage1 = simulator.calculate_slippage(
            order_size=10.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.0
        )
        
        slippage2 = simulator.calculate_slippage(
            order_size=20.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.0
        )
        
        # Linear model: double size should roughly double the size impact
        # (not exact due to base slippage)
        assert slippage2 > slippage1
    
    def test_sqrt_model(self):
        """Test sqrt slippage model."""
        config = SlippageConfig(model='sqrt', size_impact_factor=0.001)
        simulator = SlippageSimulator(config)
        
        slippage1 = simulator.calculate_slippage(
            order_size=10.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.0
        )
        
        slippage2 = simulator.calculate_slippage(
            order_size=40.0,
            order_price=50000.0,
            market_volume=1000.0,
            volatility=0.0
        )
        
        # Sqrt model: 4x size should roughly 2x the size impact
        assert slippage2 > slippage1
        # But less than linear would give
        assert slippage2 < slippage1 * 4
    
    def test_zero_volume_uses_default(self):
        """Test that zero volume uses default size ratio."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size=1.0,
            order_price=50000.0,
            market_volume=0.0,  # Zero volume
            volatility=0.01
        )
        
        # Should still calculate slippage using default ratio
        assert slippage > 0


class TestSlippageApplication:
    """Tests for applying slippage to orders."""
    
    def test_buy_order_slips_upward(self):
        """Test that buy orders slip upward (worse price)."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        original_price = 50000.0
        slippage = 0.0001  # 0.01%
        
        actual_price = simulator.apply_slippage(original_price, slippage, "buy")
        
        assert actual_price > original_price
        assert actual_price == original_price * (1 + slippage)
    
    def test_sell_order_slips_downward(self):
        """Test that sell orders slip downward (worse price)."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        original_price = 50000.0
        slippage = 0.0001  # 0.01%
        
        actual_price = simulator.apply_slippage(original_price, slippage, "sell")
        
        assert actual_price < original_price
        assert actual_price == original_price * (1 - slippage)
    
    def test_slippage_cost_tracking(self):
        """Test that slippage cost is tracked."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        assert simulator.get_total_slippage_cost() == 0.0
        
        # Apply slippage to a buy order
        simulator.apply_slippage(50000.0, 0.0001, "buy")
        
        # Cost should be tracked
        assert simulator.get_total_slippage_cost() > 0
    
    def test_multiple_orders_accumulate_cost(self):
        """Test that multiple orders accumulate slippage cost."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        simulator.apply_slippage(50000.0, 0.0001, "buy")
        cost1 = simulator.get_total_slippage_cost()
        
        simulator.apply_slippage(50000.0, 0.0001, "sell")
        cost2 = simulator.get_total_slippage_cost()
        
        assert cost2 > cost1
    
    def test_reset_clears_cost(self):
        """Test that reset clears slippage cost."""
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        simulator.apply_slippage(50000.0, 0.0001, "buy")
        assert simulator.get_total_slippage_cost() > 0
        
        simulator.reset()
        assert simulator.get_total_slippage_cost() == 0.0


class TestSlippageProperties:
    """Property-based tests for slippage simulator.
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    
    @given(
        order_size=st.floats(min_value=0.1, max_value=100.0),
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        market_volume=st.floats(min_value=100.0, max_value=10000.0),
        volatility=st.floats(min_value=0.001, max_value=0.1)
    )
    def test_property_slippage_non_negative(
        self, order_size, order_price, market_volume, volatility
    ):
        """Property: Slippage should always be non-negative.
        
        **Validates: Requirements 2.1**
        """
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size, order_price, market_volume, volatility
        )
        
        assert slippage >= 0
    
    @given(
        order_size=st.floats(min_value=0.1, max_value=100.0),
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        market_volume=st.floats(min_value=100.0, max_value=10000.0),
        volatility=st.floats(min_value=0.001, max_value=0.1)
    )
    def test_property_slippage_bounded_by_max(
        self, order_size, order_price, market_volume, volatility
    ):
        """Property: Slippage should never exceed max_slippage.
        
        **Validates: Requirements 2.1**
        """
        config = SlippageConfig(max_slippage=0.005)
        simulator = SlippageSimulator(config)
        
        slippage = simulator.calculate_slippage(
            order_size, order_price, market_volume, volatility
        )
        
        assert slippage <= config.max_slippage
    
    @given(
        order_size=st.floats(min_value=0.1, max_value=50.0),
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        market_volume=st.floats(min_value=100.0, max_value=10000.0),
        volatility=st.floats(min_value=0.001, max_value=0.05)
    )
    def test_property_larger_orders_more_slippage(
        self, order_size, order_price, market_volume, volatility
    ):
        """Property: Larger orders should have equal or more slippage.
        
        **Validates: Requirements 2.1**
        """
        config = SlippageConfig(model='linear')
        simulator = SlippageSimulator(config)
        
        slippage1 = simulator.calculate_slippage(
            order_size, order_price, market_volume, volatility
        )
        
        slippage2 = simulator.calculate_slippage(
            order_size * 2, order_price, market_volume, volatility
        )
        
        # Larger order should have equal or more slippage
        # (might be equal if hitting max_slippage cap)
        assert slippage2 >= slippage1
    
    @given(
        order_size=st.floats(min_value=0.1, max_value=100.0),
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        market_volume=st.floats(min_value=100.0, max_value=10000.0),
        volatility=st.floats(min_value=0.001, max_value=0.05)
    )
    def test_property_higher_volatility_more_slippage(
        self, order_size, order_price, market_volume, volatility
    ):
        """Property: Higher volatility should increase slippage.
        
        **Validates: Requirements 2.3**
        """
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        slippage1 = simulator.calculate_slippage(
            order_size, order_price, market_volume, volatility
        )
        
        slippage2 = simulator.calculate_slippage(
            order_size, order_price, market_volume, volatility * 2
        )
        
        # Higher volatility should increase slippage
        # (might be equal if hitting max_slippage cap)
        assert slippage2 >= slippage1
    
    @given(
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        slippage=st.floats(min_value=0.0, max_value=0.01)
    )
    def test_property_buy_slips_up_sell_slips_down(self, order_price, slippage):
        """Property: Buy orders slip up, sell orders slip down.
        
        **Validates: Requirements 2.1**
        """
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        buy_price = simulator.apply_slippage(order_price, slippage, "buy")
        sell_price = simulator.apply_slippage(order_price, slippage, "sell")
        
        assert buy_price >= order_price
        assert sell_price <= order_price
    
    @given(
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        slippage=st.floats(min_value=0.0001, max_value=0.01)
    )
    def test_property_slippage_cost_accumulates(self, order_price, slippage):
        """Property: Slippage cost should accumulate with each order.
        
        **Validates: Requirements 2.5**
        """
        config = SlippageConfig()
        simulator = SlippageSimulator(config)
        
        cost_before = simulator.get_total_slippage_cost()
        simulator.apply_slippage(order_price, slippage, "buy")
        cost_after = simulator.get_total_slippage_cost()
        
        assert cost_after > cost_before


class TestSlippageIntegration:
    """Integration tests for slippage simulator."""
    
    def test_realistic_scenario(self):
        """Test a realistic trading scenario with slippage."""
        config = SlippageConfig(
            enabled=True,
            base_slippage=0.0001,
            size_impact_factor=0.001,
            volatility_impact_factor=0.0005,
            max_slippage=0.005,
            model='linear'
        )
        simulator = SlippageSimulator(config)
        
        # Simulate a series of trades
        trades = [
            {"size": 1.0, "price": 50000.0, "volume": 1000.0, "vol": 0.01, "side": "buy"},
            {"size": 2.0, "price": 50100.0, "volume": 1200.0, "vol": 0.015, "side": "sell"},
            {"size": 0.5, "price": 49900.0, "volume": 800.0, "vol": 0.02, "side": "buy"},
        ]
        
        total_slippage_pct = 0.0
        
        for trade in trades:
            slippage = simulator.calculate_slippage(
                trade["size"],
                trade["price"],
                trade["volume"],
                trade["vol"]
            )
            
            actual_price = simulator.apply_slippage(
                trade["price"],
                slippage,
                trade["side"]
            )
            
            total_slippage_pct += slippage
            
            # Verify slippage is reasonable
            assert 0 <= slippage <= config.max_slippage
            
            # Verify price moved in correct direction
            if trade["side"] == "buy":
                assert actual_price >= trade["price"]
            else:
                assert actual_price <= trade["price"]
        
        # Verify total cost was tracked
        assert simulator.get_total_slippage_cost() > 0
        
        # Average slippage should be reasonable
        avg_slippage = total_slippage_pct / len(trades)
        assert 0.0001 <= avg_slippage <= 0.005
