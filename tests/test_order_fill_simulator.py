"""Tests for order fill simulator."""

import pytest
from hypothesis import given, strategies as st
from backtest_engine.order_fill_simulator import OrderFillConfig, OrderFillSimulator
from market_data_layer.models import KlineData


class TestOrderFillConfig:
    """Tests for OrderFillConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = OrderFillConfig()
        assert config.enable_partial_fill is False
        assert config.enable_realistic_timing is True
        assert config.min_fill_ratio == 0.1
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = OrderFillConfig(
            enable_partial_fill=True,
            enable_realistic_timing=False,
            min_fill_ratio=0.5
        )
        assert config.enable_partial_fill is True
        assert config.enable_realistic_timing is False
        assert config.min_fill_ratio == 0.5
    
    def test_invalid_min_fill_ratio_zero(self):
        """Test that min_fill_ratio of 0 raises error."""
        with pytest.raises(ValueError, match="min_fill_ratio must be in"):
            OrderFillConfig(min_fill_ratio=0.0)
    
    def test_invalid_min_fill_ratio_negative(self):
        """Test that negative min_fill_ratio raises error."""
        with pytest.raises(ValueError, match="min_fill_ratio must be in"):
            OrderFillConfig(min_fill_ratio=-0.1)
    
    def test_invalid_min_fill_ratio_greater_than_one(self):
        """Test that min_fill_ratio > 1 raises error."""
        with pytest.raises(ValueError, match="min_fill_ratio must be in"):
            OrderFillConfig(min_fill_ratio=1.1)


class TestLimitOrderFill:
    """Tests for limit order fill checking."""
    
    def test_buy_order_fills_when_low_touches_price(self):
        """Test buy limit order fills when kline low touches order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=49000.0,
            order_side="buy",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_price == 49000.0
        assert fill_time >= kline.timestamp
    
    def test_buy_order_fills_when_low_below_price(self):
        """Test buy limit order fills when kline low is below order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=48000.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=49000.0,
            order_side="buy",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_price == 49000.0
    
    def test_buy_order_not_filled_when_low_above_price(self):
        """Test buy limit order doesn't fill when kline low is above order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49500.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=49000.0,
            order_side="buy",
            kline=kline
        )
        
        assert is_filled is False
    
    def test_sell_order_fills_when_high_touches_price(self):
        """Test sell limit order fills when kline high touches order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=51000.0,
            order_side="sell",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_price == 51000.0
        assert fill_time >= kline.timestamp
    
    def test_sell_order_fills_when_high_above_price(self):
        """Test sell limit order fills when kline high is above order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=52000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=51000.0,
            order_side="sell",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_price == 51000.0
    
    def test_sell_order_not_filled_when_high_below_price(self):
        """Test sell limit order doesn't fill when kline high is below order price."""
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=50500.0,
            low=49000.0,
            close=50200.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=51000.0,
            order_side="sell",
            kline=kline
        )
        
        assert is_filled is False


class TestFillTiming:
    """Tests for fill timing estimation."""
    
    def test_realistic_timing_enabled(self):
        """Test that realistic timing estimates time within kline."""
        config = OrderFillConfig(enable_realistic_timing=True)
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        kline_duration = 86400000  # 1 day
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=49500.0,
            order_side="buy",
            kline=kline,
            kline_duration_ms=kline_duration
        )
        
        assert is_filled is True
        assert kline.timestamp <= fill_time <= kline.timestamp + kline_duration
    
    def test_realistic_timing_disabled(self):
        """Test that disabling realistic timing returns kline timestamp."""
        config = OrderFillConfig(enable_realistic_timing=False)
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=49500.0,
            order_side="buy",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_time == kline.timestamp
    
    def test_zero_price_range_returns_start_time(self):
        """Test that zero price range returns kline start time."""
        config = OrderFillConfig(enable_realistic_timing=True)
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=50000.0,
            high=50000.0,
            low=50000.0,
            close=50000.0,
            volume=1000.0
        )
        
        is_filled, fill_price, fill_time = simulator.check_limit_order_fill(
            order_price=50000.0,
            order_side="buy",
            kline=kline
        )
        
        assert is_filled is True
        assert fill_time == kline.timestamp


class TestPartialFill:
    """Tests for partial fill simulation."""
    
    def test_partial_fill_disabled_returns_full_quantity(self):
        """Test that disabled partial fill returns full quantity."""
        config = OrderFillConfig(enable_partial_fill=False)
        simulator = OrderFillSimulator(config)
        
        filled = simulator.simulate_partial_fill(
            order_quantity=10.0,
            available_liquidity=5.0
        )
        
        assert filled == 10.0
    
    def test_sufficient_liquidity_fills_completely(self):
        """Test that sufficient liquidity fills order completely."""
        config = OrderFillConfig(enable_partial_fill=True)
        simulator = OrderFillSimulator(config)
        
        filled = simulator.simulate_partial_fill(
            order_quantity=10.0,
            available_liquidity=15.0
        )
        
        assert filled == 10.0
    
    def test_insufficient_liquidity_partial_fill(self):
        """Test partial fill when liquidity is insufficient."""
        config = OrderFillConfig(enable_partial_fill=True, min_fill_ratio=0.1)
        simulator = OrderFillSimulator(config)
        
        filled = simulator.simulate_partial_fill(
            order_quantity=10.0,
            available_liquidity=5.0
        )
        
        assert filled == 5.0
        assert simulator.get_partial_fills_count() == 1
    
    def test_very_low_liquidity_uses_min_fill_ratio(self):
        """Test that very low liquidity still fills minimum ratio."""
        config = OrderFillConfig(enable_partial_fill=True, min_fill_ratio=0.2)
        simulator = OrderFillSimulator(config)
        
        filled = simulator.simulate_partial_fill(
            order_quantity=10.0,
            available_liquidity=0.5
        )
        
        # Should fill at least min_fill_ratio
        assert filled >= 10.0 * 0.2
        assert filled <= 10.0
    
    def test_partial_fills_counter(self):
        """Test that partial fills are counted."""
        config = OrderFillConfig(enable_partial_fill=True)
        simulator = OrderFillSimulator(config)
        
        assert simulator.get_partial_fills_count() == 0
        
        # Full fill - no increment
        simulator.simulate_partial_fill(10.0, 15.0)
        assert simulator.get_partial_fills_count() == 0
        
        # Partial fill - increment
        simulator.simulate_partial_fill(10.0, 5.0)
        assert simulator.get_partial_fills_count() == 1
        
        # Another partial fill
        simulator.simulate_partial_fill(10.0, 3.0)
        assert simulator.get_partial_fills_count() == 2
    
    def test_reset_clears_counter(self):
        """Test that reset clears partial fills counter."""
        config = OrderFillConfig(enable_partial_fill=True)
        simulator = OrderFillSimulator(config)
        
        simulator.simulate_partial_fill(10.0, 5.0)
        assert simulator.get_partial_fills_count() > 0
        
        simulator.reset()
        assert simulator.get_partial_fills_count() == 0


class TestOrderFillProperties:
    """Property-based tests for order fill simulator.
    
    **Validates: Requirements 3.1, 3.2, 3.5**
    """
    
    @given(
        order_price=st.floats(min_value=1000.0, max_value=100000.0),
        kline_low=st.floats(min_value=1000.0, max_value=50000.0),
        kline_high=st.floats(min_value=50000.0, max_value=100000.0)
    )
    def test_property_buy_fills_when_low_touches(self, order_price, kline_low, kline_high):
        """Property: Buy order fills when kline low <= order price.
        
        **Validates: Requirements 3.1**
        """
        config = OrderFillConfig()
        simulator = OrderFillSimulator(config)
        
        kline = KlineData(
            timestamp=1000000,
            open=(kline_low + kline_high) / 2,
            high=kline_high,
            low=kline_low,
            close=(kline_low + kline_high) / 2,
            volume=1000.0
        )
        
        is_filled, _, _ = simulator.check_limit_order_fill(
            order_price=order_price,
            order_side="buy",
            kline=kline
        )
        
        # Should fill if and only if low <= order_price
        if kline_low <= order_price:
            assert is_filled is True
        else:
            assert is_filled is False
    
    @given(
        order_quantity=st.floats(min_value=0.1, max_value=100.0),
        available_liquidity=st.floats(min_value=0.0, max_value=100.0)
    )
    def test_property_filled_quantity_bounded(self, order_quantity, available_liquidity):
        """Property: Filled quantity should be between min_fill and order_quantity.
        
        **Validates: Requirements 3.2**
        """
        config = OrderFillConfig(enable_partial_fill=True, min_fill_ratio=0.1)
        simulator = OrderFillSimulator(config)
        
        filled = simulator.simulate_partial_fill(order_quantity, available_liquidity)
        
        # Filled should be at most order_quantity
        assert filled <= order_quantity
        
        # If partial fill enabled and liquidity < quantity, should fill something
        if available_liquidity < order_quantity:
            min_expected = min(order_quantity * config.min_fill_ratio, order_quantity)
            assert filled >= min_expected or filled == available_liquidity
