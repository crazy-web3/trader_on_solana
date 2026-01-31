"""Property-based tests for OrderManager component.

This module contains property-based tests using Hypothesis to verify
the correctness properties of the OrderManager component across a wide
range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from strategy_engine.components.order_manager import OrderManager, GridOrder
from strategy_engine.models import StrategyConfig, StrategyMode
from market_data_layer.models import KlineData


# ============================================================================
# Test Data Generators (Strategies)
# ============================================================================

@st.composite
def strategy_config_strategy(draw):
    """Generate valid strategy configurations.
    
    Generates configurations with:
    - Reasonable price ranges (1000-100000)
    - Grid counts between 5-20
    - Initial capital between 1000-100000
    - Leverage between 1-10
    - Valid fee rates
    """
    lower_price = draw(st.floats(min_value=1000.0, max_value=50000.0))
    # Upper price must be at least 10% higher than lower price
    upper_price = draw(st.floats(min_value=lower_price * 1.1, max_value=lower_price * 2.0))
    
    return StrategyConfig(
        symbol="BTC/USDT",
        mode=draw(st.sampled_from([StrategyMode.LONG, StrategyMode.SHORT, StrategyMode.NEUTRAL])),
        lower_price=lower_price,
        upper_price=upper_price,
        grid_count=draw(st.integers(min_value=5, max_value=20)),
        initial_capital=draw(st.floats(min_value=1000.0, max_value=100000.0)),
        leverage=draw(st.floats(min_value=1.0, max_value=10.0)),
        fee_rate=0.0005,
        funding_rate=draw(st.floats(min_value=-0.001, max_value=0.001)),
    )


@st.composite
def kline_strategy(draw, price_range=None):
    """Generate valid K-line data.
    
    Args:
        price_range: Optional tuple of (min_price, max_price) to constrain prices
    
    Generates K-lines with:
    - Valid OHLC relationships (high >= max(open, close), low <= min(open, close))
    - Reasonable price ranges
    - Positive volumes
    """
    if price_range:
        min_price, max_price = price_range
    else:
        min_price, max_price = 1000.0, 100000.0
    
    open_price = draw(st.floats(min_value=min_price, max_value=max_price))
    close_price = draw(st.floats(min_value=min_price, max_value=max_price))
    
    # High must be >= max(open, close)
    high_min = max(open_price, close_price)
    high = draw(st.floats(min_value=high_min, max_value=high_min * 1.05))
    
    # Low must be <= min(open, close)
    low_max = min(open_price, close_price)
    low = draw(st.floats(min_value=low_max * 0.95, max_value=low_max))
    
    return KlineData(
        timestamp=draw(st.integers(min_value=1609459200000, max_value=1640995200000)),
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=draw(st.floats(min_value=100.0, max_value=1000000.0)),
    )


@st.composite
def kline_list_strategy(draw, config=None, min_size=10, max_size=100):
    """Generate a list of K-line data.
    
    Args:
        config: Optional StrategyConfig to constrain prices to grid range
        min_size: Minimum number of K-lines
        max_size: Maximum number of K-lines
    
    Generates a sequence of K-lines with increasing timestamps.
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    
    if config:
        # Constrain prices to be within or near the grid range
        price_range = (config.lower_price * 0.8, config.upper_price * 1.2)
    else:
        price_range = None
    
    klines = []
    base_timestamp = 1609459200000
    
    for i in range(size):
        kline = draw(kline_strategy(price_range=price_range))
        # Ensure timestamps are increasing
        kline.timestamp = base_timestamp + i * 86400000  # One day apart
        klines.append(kline)
    
    return klines


# ============================================================================
# Property 1: 订单初始化正确性
# **Validates: Requirements 1.1**
# ============================================================================

@settings(max_examples=100)
@given(config=strategy_config_strategy())
def test_property_order_initialization_correctness(config):
    """
    Property 1: 订单初始化正确性
    
    **Validates: Requirements 1.1**
    
    For any strategy configuration and initial price, the initialized orders
    should follow the strategy mode rules:
    - LONG grid: Buy orders below current price, sell orders above
    - SHORT grid: Sell orders above current price, buy orders below
    - NEUTRAL grid: Balanced buy/sell orders around current price
    
    This property verifies that:
    1. Orders are placed within the grid range
    2. Order sides match the strategy mode and price position
    3. Order prices correspond to grid levels
    4. Order quantities are positive
    """
    # Generate a current price within the grid range
    current_price = (config.lower_price + config.upper_price) / 2.0
    
    # Create OrderManager and place initial orders
    manager = OrderManager(config)
    manager.place_initial_orders(current_price, config.mode)
    
    # Verify orders were placed
    assert len(manager.pending_orders) > 0, "Should place at least one order"
    
    # Calculate grid gap
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Verify each order
    for grid_idx, order in manager.pending_orders.items():
        # Order should be a valid GridOrder
        assert isinstance(order, GridOrder)
        
        # Grid index should be valid
        assert 0 <= grid_idx < config.grid_count, f"Grid index {grid_idx} out of range"
        
        # Order price should match grid level
        expected_price = config.lower_price + grid_idx * grid_gap
        assert abs(order.price - expected_price) < 1e-6, \
            f"Order price {order.price} doesn't match grid level {expected_price}"
        
        # Order quantity should be positive
        assert order.quantity > 0, f"Order quantity {order.quantity} should be positive"
        
        # Order side should be valid
        assert order.side in ["buy", "sell"], f"Invalid order side: {order.side}"
        
        # Verify order side matches strategy mode and price position
        grid_price = order.price
        
        if config.mode == StrategyMode.LONG:
            # LONG: Buy below current price, sell above
            if grid_price < current_price:
                assert order.side == "buy", \
                    f"LONG mode: Order below current price should be buy, got {order.side}"
            elif grid_price > current_price:
                assert order.side == "sell", \
                    f"LONG mode: Order above current price should be sell, got {order.side}"
        
        elif config.mode == StrategyMode.SHORT:
            # SHORT: Sell above current price, buy below
            if grid_price > current_price:
                assert order.side == "sell", \
                    f"SHORT mode: Order above current price should be sell, got {order.side}"
            elif grid_price < current_price:
                assert order.side == "buy", \
                    f"SHORT mode: Order below current price should be buy, got {order.side}"
        
        elif config.mode == StrategyMode.NEUTRAL:
            # NEUTRAL: Buy below current price, sell above
            if grid_price < current_price:
                assert order.side == "buy", \
                    f"NEUTRAL mode: Order below current price should be buy, got {order.side}"
            elif grid_price > current_price:
                assert order.side == "sell", \
                    f"NEUTRAL mode: Order above current price should be sell, got {order.side}"


# ============================================================================
# Property 2: 订单触发准确性
# **Validates: Requirements 1.2**
# ============================================================================

@settings(max_examples=100)
@given(
    config=strategy_config_strategy(),
    klines=st.data()
)
def test_property_order_trigger_accuracy(config, klines):
    """
    Property 2: 订单触发准确性
    
    **Validates: Requirements 1.2**
    
    For any pending order and K-line data, an order should be executed
    if and only if the price touches the order price:
    - Buy order: Executed when K-line low <= order price
    - Sell order: Executed when K-line high >= order price
    
    This property verifies that:
    1. Orders are filled when price conditions are met
    2. Orders are not filled when price conditions are not met
    3. Multiple orders can be filled in a single K-line
    4. Filled orders are marked correctly
    """
    manager = OrderManager(config)
    
    # Place some test orders at different grid levels
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Place a buy order at grid 3
    if config.grid_count > 3:
        buy_price = config.lower_price + 3 * grid_gap
        buy_order = GridOrder(3, buy_price, "buy", 0.1)
        manager.pending_orders[3] = buy_order
    
    # Place a sell order at grid 7
    if config.grid_count > 7:
        sell_price = config.lower_price + 7 * grid_gap
        sell_order = GridOrder(7, sell_price, "sell", 0.1)
        manager.pending_orders[7] = sell_order
    
    # Generate a K-line with prices in the grid range
    kline = klines.draw(kline_strategy(price_range=(config.lower_price, config.upper_price)))
    
    # Check which orders should be filled
    filled_orders = manager.check_order_fills(kline)
    
    # Verify each pending order
    for grid_idx, order in manager.pending_orders.items():
        should_fill = False
        
        if order.side == "buy" and kline.low <= order.price:
            should_fill = True
        elif order.side == "sell" and kline.high >= order.price:
            should_fill = True
        
        # Check if order was correctly filled or not filled
        if should_fill:
            assert order.is_filled, \
                f"{order.side} order at {order.price} should be filled " \
                f"(kline low={kline.low}, high={kline.high})"
            assert order in filled_orders, \
                f"Filled order should be in returned list"
        else:
            assert not order.is_filled, \
                f"{order.side} order at {order.price} should not be filled " \
                f"(kline low={kline.low}, high={kline.high})"
            assert order not in filled_orders, \
                f"Unfilled order should not be in returned list"


@settings(max_examples=100)
@given(config=strategy_config_strategy())
def test_property_order_trigger_boundary_conditions(config):
    """
    Property 2 (Boundary): 订单触发边界条件
    
    **Validates: Requirements 1.2**
    
    Verifies that orders are triggered correctly at exact price boundaries:
    - Buy order triggers when low exactly equals order price
    - Sell order triggers when high exactly equals order price
    """
    manager = OrderManager(config)
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Place a buy order using the new _add_order method
    buy_price = config.lower_price + 3 * grid_gap
    buy_order = GridOrder(3, buy_price, "buy", 0.1)
    manager._add_order(buy_order)  # Use _add_order instead of direct assignment
    
    # Create K-line where low exactly equals buy price
    kline = KlineData(
        timestamp=1609459200000,
        open=buy_price + 100,
        high=buy_price + 200,
        low=buy_price,  # Exactly at buy price
        close=buy_price + 100,
        volume=1000.0,
    )
    
    filled_orders = manager.check_order_fills(kline)
    
    # Buy order should be filled
    assert buy_order.is_filled, "Buy order should be filled when low equals order price"
    assert buy_order in filled_orders, "Filled buy order should be in returned list"
    
    # Test sell order boundary
    manager2 = OrderManager(config)
    sell_price = config.lower_price + 7 * grid_gap
    sell_order = GridOrder(7, sell_price, "sell", 0.1)
    manager2._add_order(sell_order)  # Use _add_order instead of direct assignment
    
    # Create K-line where high exactly equals sell price
    kline2 = KlineData(
        timestamp=1609459200000,
        open=sell_price - 100,
        high=sell_price,  # Exactly at sell price
        low=sell_price - 200,
        close=sell_price - 100,
        volume=1000.0,
    )
    
    filled_orders2 = manager2.check_order_fills(kline2)
    
    # Sell order should be filled
    assert sell_order.is_filled, "Sell order should be filled when high equals order price"
    assert sell_order in filled_orders2, "Filled sell order should be in returned list"


# ============================================================================
# Property 3: 对手订单放置正确性
# **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
# ============================================================================

@settings(max_examples=100)
@given(
    config=strategy_config_strategy(),
    mode=st.sampled_from([StrategyMode.LONG, StrategyMode.SHORT, StrategyMode.NEUTRAL])
)
def test_property_counter_order_placement_correctness(config, mode):
    """
    Property 3: 对手订单放置正确性
    
    **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
    
    For any filled order, the system should place a new order at the correct
    counter grid according to the strategy mode:
    - LONG grid: Buy fills -> sell at next grid up, Sell fills -> buy at next grid down
    - SHORT grid: Sell fills -> buy at next grid down, Buy fills -> sell at next grid up
    - NEUTRAL grid: Order fills -> place closing order at counter grid
    
    This property verifies that:
    1. Counter orders are placed at the correct grid level
    2. Counter orders have the correct side (buy/sell)
    3. Counter orders have appropriate quantities
    4. No counter orders are placed beyond grid boundaries
    """
    config.mode = mode
    manager = OrderManager(config)
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Test different grid positions (avoid boundaries)
    test_grid_idx = config.grid_count // 2
    
    # Ensure we're not at boundaries
    assume(test_grid_idx > 0 and test_grid_idx < config.grid_count - 1)
    
    # Test buy order fill
    buy_price = config.lower_price + test_grid_idx * grid_gap
    buy_order = GridOrder(test_grid_idx, buy_price, "buy", 0.1)
    buy_order.is_filled = True
    
    manager.place_counter_order(buy_order, mode)
    
    if mode == StrategyMode.LONG:
        # LONG: Buy fills -> sell at next grid up (grid_idx + 1)
        expected_counter_idx = test_grid_idx + 1
        if expected_counter_idx < config.grid_count:
            assert expected_counter_idx in manager.pending_orders, \
                f"LONG mode: Buy fill should place sell order at grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "sell", \
                f"LONG mode: Counter order should be sell, got {counter_order.side}"
            expected_price = config.lower_price + expected_counter_idx * grid_gap
            assert abs(counter_order.price - expected_price) < 1e-6, \
                f"Counter order price {counter_order.price} doesn't match expected {expected_price}"
    
    elif mode == StrategyMode.SHORT:
        # SHORT: Buy fills -> sell at next grid up (grid_idx + 1)
        expected_counter_idx = test_grid_idx + 1
        if expected_counter_idx < config.grid_count:
            assert expected_counter_idx in manager.pending_orders, \
                f"SHORT mode: Buy fill should place sell order at grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "sell", \
                f"SHORT mode: Counter order should be sell, got {counter_order.side}"
    
    elif mode == StrategyMode.NEUTRAL:
        # NEUTRAL: Buy fills -> sell at symmetric grid (grid_count - 1 - grid_idx)
        # This is the new symmetric grid strategy for NEUTRAL mode
        expected_counter_idx = config.grid_count - 1 - test_grid_idx
        if expected_counter_idx < config.grid_count and expected_counter_idx >= 0:
            assert expected_counter_idx in manager.pending_orders, \
                f"NEUTRAL mode: Buy fill should place sell order at symmetric grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "sell", \
                f"NEUTRAL mode: Counter order should be sell, got {counter_order.side}"
    
    # Clear orders for next test
    manager.pending_orders.clear()
    manager.grid_orders.clear()
    manager.orders_by_id.clear()
    
    # Test sell order fill
    sell_price = config.lower_price + test_grid_idx * grid_gap
    sell_order = GridOrder(test_grid_idx, sell_price, "sell", 0.1)
    sell_order.is_filled = True
    
    manager.place_counter_order(sell_order, mode)
    
    if mode == StrategyMode.LONG:
        # LONG: Sell fills -> buy at next grid down (grid_idx - 1)
        expected_counter_idx = test_grid_idx - 1
        if expected_counter_idx >= 0:
            assert expected_counter_idx in manager.pending_orders, \
                f"LONG mode: Sell fill should place buy order at grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "buy", \
                f"LONG mode: Counter order should be buy, got {counter_order.side}"
    
    elif mode == StrategyMode.SHORT:
        # SHORT: Sell fills -> buy at next grid down (grid_idx - 1)
        expected_counter_idx = test_grid_idx - 1
        if expected_counter_idx >= 0:
            assert expected_counter_idx in manager.pending_orders, \
                f"SHORT mode: Sell fill should place buy order at grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "buy", \
                f"SHORT mode: Counter order should be buy, got {counter_order.side}"
    
    elif mode == StrategyMode.NEUTRAL:
        # NEUTRAL: Sell fills -> buy at symmetric grid (grid_count - 1 - grid_idx)
        # This is the new symmetric grid strategy for NEUTRAL mode
        expected_counter_idx = config.grid_count - 1 - test_grid_idx
        if expected_counter_idx >= 0 and expected_counter_idx < config.grid_count:
            assert expected_counter_idx in manager.pending_orders, \
                f"NEUTRAL mode: Sell fill should place buy order at symmetric grid {expected_counter_idx}"
            counter_order = manager.pending_orders[expected_counter_idx]
            assert counter_order.side == "buy", \
                f"NEUTRAL mode: Counter order should be buy, got {counter_order.side}"


@settings(max_examples=100)
@given(config=strategy_config_strategy())
def test_property_counter_order_boundary_handling(config):
    """
    Property 3 (Boundary): 对手订单边界处理
    
    **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
    
    Verifies that counter orders are not placed beyond grid boundaries:
    - No counter orders placed at grid_idx < 0
    - No counter orders placed at grid_idx >= grid_count
    """
    manager = OrderManager(config)
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Test at lower boundary (grid 0)
    if config.mode == StrategyMode.LONG:
        # Sell order at grid 0 should not place buy order at grid -1
        sell_order = GridOrder(0, config.lower_price, "sell", 0.1)
        sell_order.is_filled = True
        
        manager.place_counter_order(sell_order, config.mode)
        
        # Should not have any order at negative index
        assert -1 not in manager.pending_orders, \
            "Should not place counter order at negative grid index"
    
    # Test at upper boundary (grid_count - 1)
    if config.mode == StrategyMode.LONG:
        # Buy order at last grid should not place sell order beyond grid_count
        last_idx = config.grid_count - 1
        buy_order = GridOrder(last_idx, config.upper_price, "buy", 0.1)
        buy_order.is_filled = True
        
        manager.place_counter_order(buy_order, config.mode)
        
        # Should not have any order beyond grid_count
        assert config.grid_count not in manager.pending_orders, \
            "Should not place counter order beyond grid_count"


@settings(max_examples=100)
@given(config=strategy_config_strategy())
def test_property_counter_order_quantity_consistency(config):
    """
    Property 3 (Quantity): 对手订单数量一致性
    
    **Validates: Requirements 1.3, 1.4, 1.5, 1.6**
    
    Verifies that counter orders maintain appropriate quantity relationships:
    - For LONG/SHORT modes, counter sell orders should match buy order quantities
    - For NEUTRAL mode, counter orders should match the filled order quantities
    """
    manager = OrderManager(config)
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Test with a middle grid
    test_grid_idx = config.grid_count // 2
    assume(test_grid_idx > 0 and test_grid_idx < config.grid_count - 1)
    
    # Test buy order with specific quantity
    test_quantity = 0.15
    buy_price = config.lower_price + test_grid_idx * grid_gap
    buy_order = GridOrder(test_grid_idx, buy_price, "buy", test_quantity)
    buy_order.is_filled = True
    
    manager.place_counter_order(buy_order, config.mode)
    
    # Check if counter order was placed
    expected_counter_idx = test_grid_idx + 1
    if expected_counter_idx < config.grid_count and expected_counter_idx in manager.pending_orders:
        counter_order = manager.pending_orders[expected_counter_idx]
        
        if config.mode == StrategyMode.NEUTRAL:
            # NEUTRAL mode: counter order quantity should match filled order
            assert abs(counter_order.quantity - test_quantity) < 1e-9, \
                f"NEUTRAL mode: Counter order quantity {counter_order.quantity} " \
                f"should match filled order quantity {test_quantity}"
        elif config.mode == StrategyMode.LONG:
            # LONG mode: sell counter order should match buy order quantity
            assert abs(counter_order.quantity - test_quantity) < 1e-9, \
                f"LONG mode: Counter sell order quantity {counter_order.quantity} " \
                f"should match buy order quantity {test_quantity}"


# ============================================================================
# Additional Property Tests
# ============================================================================

@settings(max_examples=100)
@given(config=strategy_config_strategy())
def test_property_order_idempotency(config):
    """
    Property: 订单初始化幂等性
    
    Verifies that calling place_initial_orders multiple times doesn't
    create duplicate orders or change the initial state.
    """
    current_price = (config.lower_price + config.upper_price) / 2.0
    
    manager = OrderManager(config)
    manager.place_initial_orders(current_price, config.mode)
    
    # Save initial state
    initial_orders = dict(manager.pending_orders)
    initial_count = len(initial_orders)
    
    # Call again
    manager.place_initial_orders(current_price, config.mode)
    
    # Should have same orders
    assert len(manager.pending_orders) == initial_count, \
        "Calling place_initial_orders again should not change order count"
    
    # Orders should be identical
    for grid_idx, order in initial_orders.items():
        assert grid_idx in manager.pending_orders, \
            f"Grid {grid_idx} should still have an order"
        new_order = manager.pending_orders[grid_idx]
        assert order.price == new_order.price, \
            f"Order price should not change"
        assert order.side == new_order.side, \
            f"Order side should not change"


@settings(max_examples=100)
@given(
    config=strategy_config_strategy(),
    klines=st.data()
)
def test_property_no_false_fills(config, klines):
    """
    Property: 无误触发
    
    Verifies that orders are never filled when price doesn't reach them:
    - Buy orders not filled when low > order price
    - Sell orders not filled when high < order price
    """
    manager = OrderManager(config)
    grid_gap = (config.upper_price - config.lower_price) / (config.grid_count - 1)
    
    # Place orders at specific prices
    mid_idx = config.grid_count // 2
    buy_price = config.lower_price + mid_idx * grid_gap
    sell_price = config.lower_price + (mid_idx + 2) * grid_gap
    
    manager.pending_orders[mid_idx] = GridOrder(mid_idx, buy_price, "buy", 0.1)
    manager.pending_orders[mid_idx + 2] = GridOrder(mid_idx + 2, sell_price, "sell", 0.1)
    
    # Generate K-line that doesn't touch either order
    # Price range between buy and sell orders
    kline = KlineData(
        timestamp=1609459200000,
        open=(buy_price + sell_price) / 2,
        high=sell_price - 10,  # Below sell price
        low=buy_price + 10,    # Above buy price
        close=(buy_price + sell_price) / 2,
        volume=1000.0,
    )
    
    filled_orders = manager.check_order_fills(kline)
    
    # No orders should be filled
    assert len(filled_orders) == 0, \
        "No orders should be filled when price doesn't reach them"
    
    for order in manager.pending_orders.values():
        assert not order.is_filled, \
            f"{order.side} order should not be filled when price doesn't reach it"
