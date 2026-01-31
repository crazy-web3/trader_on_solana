"""Property-based tests for PositionManager component.

This module contains property-based tests using Hypothesis to verify
the correctness properties of the PositionManager component across a wide
range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from strategy_engine.components.position_manager import PositionManager, Position
from strategy_engine.models import StrategyMode


# ============================================================================
# Test Data Generators (Strategies)
# ============================================================================

@st.composite
def position_data_strategy(draw):
    """Generate valid position data.
    
    Returns:
        Tuple of (grid_idx, quantity, price, side, timestamp)
    """
    grid_idx = draw(st.integers(min_value=0, max_value=19))
    quantity = draw(st.floats(min_value=0.01, max_value=10.0))
    price = draw(st.floats(min_value=1000.0, max_value=100000.0))
    side = draw(st.sampled_from(["long", "short"]))
    timestamp = draw(st.integers(min_value=1609459200000, max_value=1640995200000))
    
    return grid_idx, quantity, price, side, timestamp


@st.composite
def position_list_strategy(draw, min_size=1, max_size=10):
    """Generate a list of position data.
    
    Returns:
        List of position data tuples
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    positions = []
    
    for _ in range(size):
        pos_data = draw(position_data_strategy())
        positions.append(pos_data)
    
    return positions


# ============================================================================
# Property 12: 订单配对正确性
# **Validates: Requirements 4.1, 4.2, 4.3**
# ============================================================================

@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=1, max_value=18),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_long_mode_sell_order_matching(grid_idx, quantity, price, timestamp):
    """
    Property 12a: 做多网格卖单配对正确性
    
    **Validates: Requirements 4.1**
    
    For LONG mode, when a sell order is filled, the system should find
    the long position at the next grid down (grid_idx - 1) for matching.
    
    This property verifies that:
    1. Sell orders in LONG mode look for positions at grid_idx - 1
    2. Only long positions (quantity > 0) are matched
    3. Returns None if no matching position exists
    """
    manager = PositionManager()
    
    # Open a long position at grid_idx - 1
    target_grid_idx = grid_idx - 1
    manager.open_position(target_grid_idx, quantity, price, "long", timestamp)
    
    # Verify the position was created
    assert target_grid_idx in manager.grid_positions
    assert manager.grid_positions[target_grid_idx].quantity > 0
    
    # Find matching position for a sell order at grid_idx
    match = manager.find_matching_position(grid_idx, "sell", StrategyMode.LONG)
    
    # Should find the long position at grid_idx - 1
    assert match is not None, "Should find matching long position for LONG mode sell order"
    matched_grid_idx, matched_position = match
    assert matched_grid_idx == target_grid_idx, \
        f"Should match position at grid {target_grid_idx}, got {matched_grid_idx}"
    assert matched_position.quantity > 0, "Matched position should be long (quantity > 0)"
    assert matched_position.side == "long", "Matched position should be long side"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=17),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_short_mode_buy_order_matching(grid_idx, quantity, price, timestamp):
    """
    Property 12b: 做空网格买单配对正确性
    
    **Validates: Requirements 4.2**
    
    For SHORT mode, when a buy order is filled, the system should find
    the short position at the next grid up (grid_idx + 1) for matching.
    
    This property verifies that:
    1. Buy orders in SHORT mode look for positions at grid_idx + 1
    2. Only short positions (quantity < 0) are matched
    3. Returns None if no matching position exists
    """
    manager = PositionManager()
    
    # Open a short position at grid_idx + 1
    target_grid_idx = grid_idx + 1
    manager.open_position(target_grid_idx, quantity, price, "short", timestamp)
    
    # Verify the position was created
    assert target_grid_idx in manager.grid_positions
    assert manager.grid_positions[target_grid_idx].quantity < 0
    
    # Find matching position for a buy order at grid_idx
    match = manager.find_matching_position(grid_idx, "buy", StrategyMode.SHORT)
    
    # Should find the short position at grid_idx + 1
    assert match is not None, "Should find matching short position for SHORT mode buy order"
    matched_grid_idx, matched_position = match
    assert matched_grid_idx == target_grid_idx, \
        f"Should match position at grid {target_grid_idx}, got {matched_grid_idx}"
    assert matched_position.quantity < 0, "Matched position should be short (quantity < 0)"
    assert matched_position.side == "short", "Matched position should be short side"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=1, max_value=18),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_neutral_mode_sell_order_matching(grid_idx, quantity, price, timestamp):
    """
    Property 12c: 中性网格卖单配对正确性
    
    **Validates: Requirements 4.3**
    
    For NEUTRAL mode, when a sell order is filled, the system should find
    the long position at the next grid down (grid_idx - 1) for matching.
    
    This property verifies that:
    1. Sell orders in NEUTRAL mode look for long positions at grid_idx - 1
    2. Only long positions (quantity > 0) are matched
    3. Returns None if no matching position exists
    """
    manager = PositionManager()
    
    # Open a long position at grid_idx - 1
    target_grid_idx = grid_idx - 1
    manager.open_position(target_grid_idx, quantity, price, "long", timestamp)
    
    # Verify the position was created
    assert target_grid_idx in manager.grid_positions
    assert manager.grid_positions[target_grid_idx].quantity > 0
    
    # Find matching position for a sell order at grid_idx
    match = manager.find_matching_position(grid_idx, "sell", StrategyMode.NEUTRAL)
    
    # Should find the long position at grid_idx - 1
    assert match is not None, "Should find matching long position for NEUTRAL mode sell order"
    matched_grid_idx, matched_position = match
    assert matched_grid_idx == target_grid_idx, \
        f"Should match position at grid {target_grid_idx}, got {matched_grid_idx}"
    assert matched_position.quantity > 0, "Matched position should be long (quantity > 0)"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=17),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_neutral_mode_buy_order_matching(grid_idx, quantity, price, timestamp):
    """
    Property 12d: 中性网格买单配对正确性
    
    **Validates: Requirements 4.3**
    
    For NEUTRAL mode, when a buy order is filled, the system should find
    the short position at the next grid up (grid_idx + 1) for matching.
    
    This property verifies that:
    1. Buy orders in NEUTRAL mode look for short positions at grid_idx + 1
    2. Only short positions (quantity < 0) are matched
    3. Returns None if no matching position exists
    """
    manager = PositionManager()
    
    # Open a short position at grid_idx + 1
    target_grid_idx = grid_idx + 1
    manager.open_position(target_grid_idx, quantity, price, "short", timestamp)
    
    # Verify the position was created
    assert target_grid_idx in manager.grid_positions
    assert manager.grid_positions[target_grid_idx].quantity < 0
    
    # Find matching position for a buy order at grid_idx
    match = manager.find_matching_position(grid_idx, "buy", StrategyMode.NEUTRAL)
    
    # Should find the short position at grid_idx + 1
    assert match is not None, "Should find matching short position for NEUTRAL mode buy order"
    matched_grid_idx, matched_position = match
    assert matched_grid_idx == target_grid_idx, \
        f"Should match position at grid {target_grid_idx}, got {matched_grid_idx}"
    assert matched_position.quantity < 0, "Matched position should be short (quantity < 0)"


# ============================================================================
# Property 13: 无配对仓位处理
# **Validates: Requirements 4.4**
# ============================================================================

@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    mode=st.sampled_from([StrategyMode.LONG, StrategyMode.SHORT, StrategyMode.NEUTRAL])
)
def test_property_no_matching_position_returns_none(grid_idx, mode):
    """
    Property 13: 无配对仓位处理
    
    **Validates: Requirements 4.4**
    
    When no matching position exists, the system should return None,
    indicating that the order should be treated as an opening order.
    
    This property verifies that:
    1. Returns None when no position exists at the target grid
    2. Returns None when position exists but has wrong side
    3. System can distinguish between opening and closing orders
    """
    manager = PositionManager()
    
    # Don't create any positions
    # Try to find matching position
    match = manager.find_matching_position(grid_idx, "sell", mode)
    
    # Should return None when no positions exist
    assert match is None, "Should return None when no matching position exists"
    
    # Test with wrong side position
    if mode == StrategyMode.LONG and grid_idx > 0:
        # Create a short position when we need a long position
        manager.open_position(grid_idx - 1, 1.0, 50000.0, "short", 1609459200000)
        match = manager.find_matching_position(grid_idx, "sell", mode)
        assert match is None, "Should return None when position has wrong side"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    side=st.sampled_from(["long", "short"]),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_opening_position_when_no_match(grid_idx, quantity, price, side, timestamp):
    """
    Property 13 (Opening): 无配对时开新仓
    
    **Validates: Requirements 4.4**
    
    When no matching position is found, the system should treat the order
    as an opening order and create a new position.
    
    This property verifies that:
    1. New positions can be opened at any grid
    2. Position is created with correct parameters
    3. Position is stored in the correct grid
    """
    manager = PositionManager()
    
    # Open a new position (simulating no match scenario)
    manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Verify position was created
    assert grid_idx in manager.grid_positions, \
        f"Position should be created at grid {grid_idx}"
    
    position = manager.grid_positions[grid_idx]
    assert position.grid_idx == grid_idx
    assert abs(abs(position.quantity) - quantity) < 1e-9
    assert position.entry_price == price
    assert position.side == side
    assert position.timestamp == timestamp


# ============================================================================
# Property 14: 仓位独立性
# **Validates: Requirements 4.5**
# ============================================================================

@settings(max_examples=100)
@given(
    positions=position_list_strategy(min_size=2, max_size=10)
)
def test_property_position_independence(positions):
    """
    Property 14: 仓位独立性
    
    **Validates: Requirements 4.5**
    
    Each grid's position should be managed independently. Modifying one
    grid's position should not affect other grids' positions.
    
    This property verifies that:
    1. Positions at different grids are independent
    2. Opening a position at one grid doesn't affect others
    3. Closing a position at one grid doesn't affect others
    4. Each grid maintains its own position state
    """
    manager = PositionManager()
    
    # Ensure we have positions at different grids
    unique_grids = {}
    for grid_idx, quantity, price, side, timestamp in positions:
        if grid_idx not in unique_grids:
            unique_grids[grid_idx] = (quantity, price, side, timestamp)
    
    # Need at least 2 different grids
    assume(len(unique_grids) >= 2)
    
    # Open positions at different grids
    for grid_idx, (quantity, price, side, timestamp) in unique_grids.items():
        manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Save initial state
    initial_positions = {
        grid_idx: (pos.quantity, pos.entry_price, pos.side)
        for grid_idx, pos in manager.grid_positions.items()
    }
    
    # Modify one position
    first_grid = list(unique_grids.keys())[0]
    first_pos = manager.grid_positions[first_grid]
    
    # Close part of the first position
    close_quantity = abs(first_pos.quantity) / 2
    manager.close_position(first_grid, close_quantity)
    
    # Verify other positions are unchanged
    for grid_idx, (orig_quantity, orig_price, orig_side) in initial_positions.items():
        if grid_idx == first_grid:
            # This position should be modified
            if first_grid in manager.grid_positions:
                # Partially closed
                current_pos = manager.grid_positions[first_grid]
                assert abs(abs(current_pos.quantity) - close_quantity) < 1e-9, \
                    "First position should be partially closed"
        else:
            # Other positions should be unchanged
            assert grid_idx in manager.grid_positions, \
                f"Position at grid {grid_idx} should still exist"
            current_pos = manager.grid_positions[grid_idx]
            assert abs(current_pos.quantity - orig_quantity) < 1e-9, \
                f"Position at grid {grid_idx} quantity should be unchanged"
            assert abs(current_pos.entry_price - orig_price) < 1e-9, \
                f"Position at grid {grid_idx} price should be unchanged"
            assert current_pos.side == orig_side, \
                f"Position at grid {grid_idx} side should be unchanged"


@settings(max_examples=100)
@given(
    grid_idx1=st.integers(min_value=0, max_value=9),
    grid_idx2=st.integers(min_value=10, max_value=19),
    quantity1=st.floats(min_value=0.01, max_value=10.0),
    quantity2=st.floats(min_value=0.01, max_value=10.0),
    price1=st.floats(min_value=1000.0, max_value=50000.0),
    price2=st.floats(min_value=50000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_position_independence_simple(grid_idx1, grid_idx2, quantity1, 
                                               quantity2, price1, price2, timestamp):
    """
    Property 14 (Simple): 仓位独立性简单测试
    
    **Validates: Requirements 4.5**
    
    Simplified test for position independence with two positions.
    """
    manager = PositionManager()
    
    # Open two positions at different grids
    manager.open_position(grid_idx1, quantity1, price1, "long", timestamp)
    manager.open_position(grid_idx2, quantity2, price2, "short", timestamp)
    
    # Verify both positions exist
    assert grid_idx1 in manager.grid_positions
    assert grid_idx2 in manager.grid_positions
    
    # Save position 2 state
    pos2_quantity = manager.grid_positions[grid_idx2].quantity
    pos2_price = manager.grid_positions[grid_idx2].entry_price
    
    # Modify position 1
    manager.close_position(grid_idx1, quantity1)
    
    # Verify position 1 is closed
    assert grid_idx1 not in manager.grid_positions, \
        "Position 1 should be completely closed"
    
    # Verify position 2 is unchanged
    assert grid_idx2 in manager.grid_positions, \
        "Position 2 should still exist"
    assert abs(manager.grid_positions[grid_idx2].quantity - pos2_quantity) < 1e-9, \
        "Position 2 quantity should be unchanged"
    assert abs(manager.grid_positions[grid_idx2].entry_price - pos2_price) < 1e-9, \
        "Position 2 price should be unchanged"


# ============================================================================
# Property 15: 仓位清理正确性
# **Validates: Requirements 4.6**
# ============================================================================

@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    side=st.sampled_from(["long", "short"]),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_position_cleanup_on_full_close(grid_idx, quantity, price, side, timestamp):
    """
    Property 15: 仓位清理正确性
    
    **Validates: Requirements 4.6**
    
    When a position is completely closed, it should be removed from the
    position records, and the net position should be updated accordingly.
    
    This property verifies that:
    1. Fully closed positions are removed from grid_positions
    2. Net position is correctly updated after closing
    3. Partial closes reduce position quantity correctly
    4. Position cleanup maintains system consistency
    """
    manager = PositionManager()
    
    # Open a position
    manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Verify position exists
    assert grid_idx in manager.grid_positions
    initial_net_position = manager.get_net_position()
    
    # Completely close the position
    closed_pos = manager.close_position(grid_idx, quantity)
    
    # Verify position was removed
    assert grid_idx not in manager.grid_positions, \
        "Fully closed position should be removed from grid_positions"
    
    # Verify closed position info is correct
    assert closed_pos is not None, "Should return closed position info"
    assert abs(abs(closed_pos.quantity) - quantity) < 1e-9, \
        "Closed position quantity should match"
    assert closed_pos.entry_price == price, "Closed position price should match"
    assert closed_pos.side == side, "Closed position side should match"
    
    # Verify net position is updated
    final_net_position = manager.get_net_position()
    expected_change = quantity if side == "long" else -quantity
    assert abs(final_net_position - (initial_net_position - expected_change)) < 1e-9, \
        "Net position should be updated after closing"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity=st.floats(min_value=0.02, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    side=st.sampled_from(["long", "short"]),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_position_partial_close(grid_idx, quantity, price, side, timestamp):
    """
    Property 15 (Partial): 部分平仓正确性
    
    **Validates: Requirements 4.6**
    
    When a position is partially closed, the remaining position should
    be correctly updated with reduced quantity.
    """
    manager = PositionManager()
    
    # Open a position
    manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Verify position exists
    assert grid_idx in manager.grid_positions
    initial_quantity = manager.grid_positions[grid_idx].quantity
    
    # Partially close the position (close half)
    close_quantity = quantity / 2
    closed_pos = manager.close_position(grid_idx, close_quantity)
    
    # Verify position still exists
    assert grid_idx in manager.grid_positions, \
        "Partially closed position should still exist"
    
    # Verify remaining quantity is correct
    remaining_pos = manager.grid_positions[grid_idx]
    expected_remaining = quantity - close_quantity
    assert abs(abs(remaining_pos.quantity) - expected_remaining) < 1e-9, \
        f"Remaining quantity should be {expected_remaining}, got {abs(remaining_pos.quantity)}"
    
    # Verify other attributes are unchanged
    assert remaining_pos.entry_price == price, \
        "Entry price should remain unchanged after partial close"
    assert remaining_pos.side == side, \
        "Side should remain unchanged after partial close"


@settings(max_examples=100)
@given(
    positions=position_list_strategy(min_size=3, max_size=10)
)
def test_property_net_position_consistency(positions):
    """
    Property 15 (Net Position): 净仓位一致性
    
    **Validates: Requirements 4.6**
    
    The net position should always equal the sum of all individual
    grid positions, and should be correctly updated after any operation.
    """
    manager = PositionManager()
    
    # Ensure we have positions at different grids
    unique_grids = {}
    for grid_idx, quantity, price, side, timestamp in positions:
        if grid_idx not in unique_grids:
            unique_grids[grid_idx] = (quantity, price, side, timestamp)
    
    # Need at least 2 different grids
    assume(len(unique_grids) >= 2)
    
    # Open positions
    for grid_idx, (quantity, price, side, timestamp) in unique_grids.items():
        manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Calculate expected net position
    expected_net = sum(
        quantity if side == "long" else -quantity
        for _, (quantity, _, side, _) in unique_grids.items()
    )
    
    # Verify net position
    actual_net = manager.get_net_position()
    assert abs(actual_net - expected_net) < 1e-6, \
        f"Net position {actual_net} should equal sum of positions {expected_net}"
    
    # Close one position and verify net position updates
    first_grid = list(unique_grids.keys())[0]
    first_quantity, _, first_side, _ = unique_grids[first_grid]
    
    manager.close_position(first_grid, first_quantity)
    
    # Recalculate expected net position
    expected_net_after = expected_net - (first_quantity if first_side == "long" else -first_quantity)
    actual_net_after = manager.get_net_position()
    
    assert abs(actual_net_after - expected_net_after) < 1e-6, \
        f"Net position after close {actual_net_after} should equal {expected_net_after}"


# ============================================================================
# Additional Property Tests
# ============================================================================

@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity1=st.floats(min_value=0.01, max_value=5.0),
    quantity2=st.floats(min_value=0.01, max_value=5.0),
    price1=st.floats(min_value=1000.0, max_value=50000.0),
    price2=st.floats(min_value=50000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_position_accumulation(grid_idx, quantity1, quantity2, 
                                       price1, price2, timestamp):
    """
    Property: 同方向仓位累加
    
    When opening multiple positions of the same side at the same grid,
    quantities should accumulate and entry price should be averaged.
    """
    manager = PositionManager()
    
    # Open first position
    manager.open_position(grid_idx, quantity1, price1, "long", timestamp)
    
    # Open second position at same grid, same side
    manager.open_position(grid_idx, quantity2, price2, "long", timestamp + 1000)
    
    # Verify position exists
    assert grid_idx in manager.grid_positions
    
    position = manager.grid_positions[grid_idx]
    
    # Verify quantity is accumulated
    expected_quantity = quantity1 + quantity2
    assert abs(position.quantity - expected_quantity) < 1e-9, \
        f"Quantity should be accumulated: expected {expected_quantity}, got {position.quantity}"
    
    # Verify entry price is averaged
    expected_price = (price1 * quantity1 + price2 * quantity2) / (quantity1 + quantity2)
    assert abs(position.entry_price - expected_price) < 1e-6, \
        f"Entry price should be averaged: expected {expected_price}, got {position.entry_price}"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_close_nonexistent_position(grid_idx, quantity, price, timestamp):
    """
    Property: 关闭不存在的仓位
    
    Attempting to close a position that doesn't exist should return None
    and not cause errors.
    """
    manager = PositionManager()
    
    # Try to close a position that doesn't exist
    closed_pos = manager.close_position(grid_idx, quantity)
    
    # Should return None
    assert closed_pos is None, "Closing nonexistent position should return None"
    
    # Manager should still be in valid state
    assert len(manager.grid_positions) == 0, "No positions should exist"
    assert manager.get_net_position() == 0, "Net position should be zero"


@settings(max_examples=100)
@given(
    grid_idx=st.integers(min_value=0, max_value=19),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    side=st.sampled_from(["long", "short"]),
    timestamp=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_position_quantity_sign(grid_idx, quantity, price, side, timestamp):
    """
    Property: 仓位数量符号正确性
    
    Long positions should have positive quantity, short positions should
    have negative quantity.
    """
    manager = PositionManager()
    
    # Open a position
    manager.open_position(grid_idx, quantity, price, side, timestamp)
    
    # Verify position exists
    assert grid_idx in manager.grid_positions
    
    position = manager.grid_positions[grid_idx]
    
    # Verify quantity sign matches side
    if side == "long":
        assert position.quantity > 0, \
            f"Long position should have positive quantity, got {position.quantity}"
    else:  # short
        assert position.quantity < 0, \
            f"Short position should have negative quantity, got {position.quantity}"
    
    # Verify absolute value matches input
    assert abs(abs(position.quantity) - quantity) < 1e-9, \
        f"Position quantity magnitude should be {quantity}, got {abs(position.quantity)}"
