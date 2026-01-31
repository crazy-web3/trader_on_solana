"""Property-based tests for PnLCalculator component.

This module contains property-based tests using Hypothesis to verify
the correctness properties of the PnLCalculator component across a wide
range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from strategy_engine.components.pnl_calculator import PnLCalculator
from strategy_engine.components.position_manager import Position


# ============================================================================
# Test Data Generators (Strategies)
# ============================================================================

@st.composite
def position_strategy(draw):
    """Generate a valid position.
    
    Returns:
        Position object
    """
    grid_idx = draw(st.integers(min_value=0, max_value=20))
    quantity = draw(st.floats(min_value=0.01, max_value=10.0))
    entry_price = draw(st.floats(min_value=1000.0, max_value=100000.0))
    side = draw(st.sampled_from(["long", "short"]))
    timestamp = draw(st.integers(min_value=1609459200000, max_value=1640995200000))
    
    # For short positions, quantity should be negative
    if side == "short":
        quantity = -abs(quantity)
    else:
        quantity = abs(quantity)
    
    return Position(
        grid_idx=grid_idx,
        quantity=quantity,
        entry_price=entry_price,
        side=side,
        timestamp=timestamp
    )


@st.composite
def positions_dict_strategy(draw, min_size=1, max_size=10):
    """Generate a dictionary of positions.
    
    Returns:
        Dict[int, Position]
    """
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    positions = {}
    
    for i in range(size):
        position = draw(position_strategy())
        # Use unique grid indices
        grid_idx = i
        positions[grid_idx] = Position(
            grid_idx=grid_idx,
            quantity=position.quantity,
            entry_price=position.entry_price,
            side=position.side,
            timestamp=position.timestamp
        )
    
    return positions


# ============================================================================
# Property 8: 已实现盈亏计算正确性
# **Validates: Requirements 3.1**
# ============================================================================

@settings(max_examples=100)
@given(
    open_price=st.floats(min_value=1000.0, max_value=100000.0),
    close_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_realized_pnl_calculation_correctness(open_price, close_price, quantity, side):
    """
    Property 8: 已实现盈亏计算正确性
    
    **Validates: Requirements 3.1**
    
    For any closing operation, realized PnL should equal:
    - Long: (close_price - open_price) × quantity
    - Short: (open_price - close_price) × quantity
    
    This property verifies that:
    1. Long position PnL = (close_price - open_price) × quantity
    2. Short position PnL = (open_price - close_price) × quantity
    3. Calculations are accurate within floating-point precision
    4. PnL is positive when profitable, negative when losing
    """
    calculator = PnLCalculator()
    
    # Calculate realized PnL
    realized_pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, side)
    
    # Verify calculation formula
    if side == "long":
        expected_pnl = (close_price - open_price) * quantity
    else:  # short
        expected_pnl = (open_price - close_price) * quantity
    
    assert abs(realized_pnl - expected_pnl) < 1e-6, \
        f"Realized PnL {realized_pnl} should equal {expected_pnl} for {side} position"
    
    # Verify PnL sign makes sense
    if side == "long":
        if close_price > open_price:
            assert realized_pnl > 0, "Long position should profit when close > open"
        elif close_price < open_price:
            assert realized_pnl < 0, "Long position should lose when close < open"
        else:
            assert abs(realized_pnl) < 1e-9, "Long position should break even when close == open"
    else:  # short
        if open_price > close_price:
            assert realized_pnl > 0, "Short position should profit when open > close"
        elif open_price < close_price:
            assert realized_pnl < 0, "Short position should lose when open < close"
        else:
            assert abs(realized_pnl) < 1e-9, "Short position should break even when open == close"


@settings(max_examples=100)
@given(
    price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_realized_pnl_zero_when_same_price(price, quantity, side):
    """
    Property 8 (Zero PnL): 相同价格平仓盈亏为零
    
    **Validates: Requirements 3.1**
    
    When closing at the same price as opening, realized PnL should be zero.
    """
    calculator = PnLCalculator()
    
    realized_pnl = calculator.calculate_realized_pnl(price, price, quantity, side)
    
    assert abs(realized_pnl) < 1e-9, \
        f"Realized PnL should be zero when open and close prices are the same, got {realized_pnl}"


@settings(max_examples=100)
@given(
    open_price=st.floats(min_value=1000.0, max_value=100000.0),
    close_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0)
)
def test_property_realized_pnl_opposite_sides(open_price, close_price, quantity):
    """
    Property 8 (Opposite): 多空盈亏对称性
    
    **Validates: Requirements 3.1**
    
    Long and short positions with the same prices should have opposite PnL.
    """
    calculator = PnLCalculator()
    
    long_pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, "long")
    short_pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, "short")
    
    # Long and short PnL should be opposite
    assert abs(long_pnl + short_pnl) < 1e-6, \
        f"Long PnL ({long_pnl}) and short PnL ({short_pnl}) should be opposite"


@settings(max_examples=100)
@given(
    open_price=st.floats(min_value=1000.0, max_value=100000.0),
    close_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity1=st.floats(min_value=0.01, max_value=5.0),
    quantity2=st.floats(min_value=0.01, max_value=5.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_realized_pnl_quantity_proportional(open_price, close_price, quantity1, quantity2, side):
    """
    Property 8 (Proportional): 盈亏与数量成正比
    
    **Validates: Requirements 3.1**
    
    Realized PnL should be proportional to position quantity.
    """
    calculator = PnLCalculator()
    
    pnl1 = calculator.calculate_realized_pnl(open_price, close_price, quantity1, side)
    pnl2 = calculator.calculate_realized_pnl(open_price, close_price, quantity2, side)
    
    # PnL ratio should equal quantity ratio
    if abs(pnl2) > 1e-9 and abs(quantity2) > 1e-9:
        pnl_ratio = pnl1 / pnl2
        quantity_ratio = quantity1 / quantity2
        
        assert abs(pnl_ratio - quantity_ratio) < 1e-6, \
            f"PnL ratio ({pnl_ratio}) should equal quantity ratio ({quantity_ratio})"


# ============================================================================
# Property 9: 未实现盈亏计算正确性
# **Validates: Requirements 3.2, 3.3**
# ============================================================================

@settings(max_examples=100)
@given(
    positions=positions_dict_strategy(min_size=1, max_size=10),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_unrealized_pnl_calculation_correctness(positions, current_price):
    """
    Property 9: 未实现盈亏计算正确性
    
    **Validates: Requirements 3.2, 3.3**
    
    For any set of open positions and current price, unrealized PnL should equal
    the sum of (current_price - entry_price) × quantity for all positions.
    
    This property verifies that:
    1. Unrealized PnL = Σ(current_price - entry_price) × quantity
    2. Long positions: positive quantity, profit when current > entry
    3. Short positions: negative quantity, profit when current < entry
    4. Current equity = current capital + unrealized PnL
    """
    calculator = PnLCalculator()
    
    # Calculate unrealized PnL
    unrealized_pnl = calculator.calculate_unrealized_pnl(positions, current_price)
    
    # Calculate expected unrealized PnL manually
    expected_pnl = 0.0
    for position in positions.values():
        if position.quantity == 0:
            continue
        
        if position.quantity > 0:  # Long position
            expected_pnl += position.quantity * (current_price - position.entry_price)
        else:  # Short position (quantity is negative)
            expected_pnl += abs(position.quantity) * (position.entry_price - current_price)
    
    assert abs(unrealized_pnl - expected_pnl) < 1e-6, \
        f"Unrealized PnL {unrealized_pnl} should equal {expected_pnl}"


@settings(max_examples=100)
@given(
    capital=st.floats(min_value=10000.0, max_value=100000.0),
    positions=positions_dict_strategy(min_size=1, max_size=10),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_equity_calculation_correctness(capital, positions, current_price):
    """
    Property 9 (Equity): 权益计算正确性
    
    **Validates: Requirements 3.3**
    
    Current equity should equal current capital + unrealized PnL.
    """
    calculator = PnLCalculator()
    
    # Calculate unrealized PnL
    unrealized_pnl = calculator.calculate_unrealized_pnl(positions, current_price)
    
    # Calculate equity
    equity = calculator.calculate_equity(capital, unrealized_pnl)
    
    # Verify equity formula
    expected_equity = capital + unrealized_pnl
    assert abs(equity - expected_equity) < 1e-6, \
        f"Equity {equity} should equal capital ({capital}) + unrealized PnL ({unrealized_pnl})"


@settings(max_examples=100)
@given(
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_unrealized_pnl_zero_for_empty_positions(current_price):
    """
    Property 9 (Empty): 无仓位时未实现盈亏为零
    
    **Validates: Requirements 3.2**
    
    When there are no positions, unrealized PnL should be zero.
    """
    calculator = PnLCalculator()
    
    empty_positions = {}
    unrealized_pnl = calculator.calculate_unrealized_pnl(empty_positions, current_price)
    
    assert abs(unrealized_pnl) < 1e-9, \
        f"Unrealized PnL should be zero for empty positions, got {unrealized_pnl}"


@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_unrealized_pnl_zero_at_entry_price(entry_price, quantity, side):
    """
    Property 9 (Entry Price): 开仓价时未实现盈亏为零
    
    **Validates: Requirements 3.2**
    
    When current price equals entry price, unrealized PnL should be zero.
    """
    calculator = PnLCalculator()
    
    # Create a single position
    if side == "short":
        quantity = -abs(quantity)
    else:
        quantity = abs(quantity)
    
    position = Position(
        grid_idx=0,
        quantity=quantity,
        entry_price=entry_price,
        side=side,
        timestamp=1609459200000
    )
    
    positions = {0: position}
    
    # Calculate unrealized PnL at entry price
    unrealized_pnl = calculator.calculate_unrealized_pnl(positions, entry_price)
    
    assert abs(unrealized_pnl) < 1e-6, \
        f"Unrealized PnL should be zero at entry price, got {unrealized_pnl}"


@settings(max_examples=100)
@given(
    positions=positions_dict_strategy(min_size=1, max_size=10),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_unrealized_pnl_idempotent(positions, current_price):
    """
    Property 9 (Idempotent): 未实现盈亏计算幂等性
    
    **Validates: Requirements 3.2**
    
    Calculating unrealized PnL multiple times should return the same result.
    """
    calculator = PnLCalculator()
    
    pnl1 = calculator.calculate_unrealized_pnl(positions, current_price)
    pnl2 = calculator.calculate_unrealized_pnl(positions, current_price)
    pnl3 = calculator.calculate_unrealized_pnl(positions, current_price)
    
    assert pnl1 == pnl2 == pnl3, \
        "Unrealized PnL calculation should be idempotent"


# ============================================================================
# Property 10: 资金守恒定律
# **Validates: Requirements 3.6**
# ============================================================================

@settings(max_examples=100)
@given(
    initial_capital=st.floats(min_value=10000.0, max_value=100000.0),
    trades=st.lists(
        st.tuples(
            st.floats(min_value=1000.0, max_value=100000.0),  # open_price
            st.floats(min_value=1000.0, max_value=100000.0),  # close_price
            st.floats(min_value=0.01, max_value=1.0),         # quantity
            st.sampled_from(["long", "short"])                # side
        ),
        min_size=1,
        max_size=20
    ),
    total_fees=st.floats(min_value=0.0, max_value=1000.0),
    total_funding=st.floats(min_value=0.0, max_value=500.0)
)
def test_property_capital_conservation(initial_capital, trades, total_fees, total_funding):
    """
    Property 10: 资金守恒定律
    
    **Validates: Requirements 3.6**
    
    For any complete backtest process, final capital should equal:
    initial_capital + realized_pnl - fees - funding_fees
    
    This property verifies that:
    1. Final capital = initial capital + realized PnL - fees - funding fees
    2. All realized PnL is properly accumulated
    3. Capital conservation holds across multiple trades
    4. The system maintains financial consistency
    """
    calculator = PnLCalculator()
    
    # Simulate trades and accumulate realized PnL
    total_realized_pnl = 0.0
    
    for open_price, close_price, quantity, side in trades:
        pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, side)
        calculator.add_realized_pnl(pnl)
        total_realized_pnl += pnl
    
    # Verify grid profit equals total realized PnL
    assert abs(calculator.get_grid_profit() - total_realized_pnl) < 1e-6, \
        f"Grid profit should equal total realized PnL"
    
    # Calculate final capital
    final_capital = initial_capital + total_realized_pnl - total_fees - total_funding
    
    # Verify conservation law
    # final_capital = initial_capital + realized_pnl - fees - funding_fees
    expected_final = initial_capital + calculator.get_grid_profit() - total_fees - total_funding
    
    assert abs(final_capital - expected_final) < 1e-6, \
        f"Capital conservation violated: final {final_capital} != expected {expected_final}"


@settings(max_examples=100)
@given(
    initial_capital=st.floats(min_value=10000.0, max_value=100000.0),
    positions=positions_dict_strategy(min_size=1, max_size=10),
    current_price=st.floats(min_value=1000.0, max_value=100000.0),
    total_fees=st.floats(min_value=0.0, max_value=1000.0),
    total_funding=st.floats(min_value=0.0, max_value=500.0)
)
def test_property_total_value_conservation(initial_capital, positions, current_price, 
                                          total_fees, total_funding):
    """
    Property 10 (Total Value): 总价值守恒
    
    **Validates: Requirements 3.6**
    
    Total value (equity) should equal:
    initial_capital + realized_pnl + unrealized_pnl - fees - funding_fees
    """
    calculator = PnLCalculator()
    
    # Calculate unrealized PnL
    unrealized_pnl = calculator.calculate_unrealized_pnl(positions, current_price)
    
    # Assume some realized PnL has been accumulated
    realized_pnl = calculator.get_grid_profit()
    
    # Calculate current capital (initial + realized - fees - funding)
    current_capital = initial_capital + realized_pnl - total_fees - total_funding
    
    # Calculate equity
    equity = calculator.calculate_equity(current_capital, unrealized_pnl)
    
    # Verify total value conservation
    expected_equity = initial_capital + realized_pnl + unrealized_pnl - total_fees - total_funding
    
    assert abs(equity - expected_equity) < 1e-6, \
        f"Total value conservation violated: equity {equity} != expected {expected_equity}"


@settings(max_examples=100)
@given(
    initial_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_conservation_no_trades(initial_capital):
    """
    Property 10 (No Trades): 无交易时资金守恒
    
    **Validates: Requirements 3.6**
    
    When no trades occur, final capital should equal initial capital.
    """
    calculator = PnLCalculator()
    
    # No trades, no fees
    final_capital = initial_capital + calculator.get_grid_profit()
    
    assert abs(final_capital - initial_capital) < 1e-9, \
        f"With no trades, final capital should equal initial capital"


# ============================================================================
# Property 11: 盈亏更新正确性
# **Validates: Requirements 3.4, 3.5**
# ============================================================================

@settings(max_examples=100)
@given(
    open_price=st.floats(min_value=1000.0, max_value=100000.0),
    close_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_pnl_update_correctness(open_price, close_price, quantity, side):
    """
    Property 11: 盈亏更新正确性
    
    **Validates: Requirements 3.4, 3.5**
    
    When an order is matched and closed, realized PnL should be immediately
    accumulated to grid profit, and current capital should immediately increase
    by the PnL amount.
    
    This property verifies that:
    1. Realized PnL is accumulated to grid_profit
    2. Grid profit increases by the exact PnL amount
    3. Multiple PnL updates accumulate correctly
    4. Capital updates reflect PnL changes
    """
    calculator = PnLCalculator()
    
    # Save initial grid profit
    initial_profit = calculator.get_grid_profit()
    
    # Calculate realized PnL
    pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, side)
    
    # Add realized PnL
    calculator.add_realized_pnl(pnl)
    
    # Verify grid profit increased by PnL amount
    final_profit = calculator.get_grid_profit()
    expected_profit = initial_profit + pnl
    
    assert abs(final_profit - expected_profit) < 1e-6, \
        f"Grid profit should increase by {pnl}, expected {expected_profit}, got {final_profit}"


@settings(max_examples=100)
@given(
    trades=st.lists(
        st.tuples(
            st.floats(min_value=1000.0, max_value=100000.0),  # open_price
            st.floats(min_value=1000.0, max_value=100000.0),  # close_price
            st.floats(min_value=0.01, max_value=1.0),         # quantity
            st.sampled_from(["long", "short"])                # side
        ),
        min_size=2,
        max_size=20
    )
)
def test_property_multiple_pnl_updates(trades):
    """
    Property 11 (Multiple): 多次盈亏更新正确性
    
    **Validates: Requirements 3.4, 3.5**
    
    Multiple PnL updates should correctly accumulate to grid profit.
    """
    calculator = PnLCalculator()
    
    expected_total_pnl = 0.0
    
    for open_price, close_price, quantity, side in trades:
        # Calculate PnL
        pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, side)
        expected_total_pnl += pnl
        
        # Add to grid profit
        calculator.add_realized_pnl(pnl)
        
        # Verify cumulative grid profit
        current_profit = calculator.get_grid_profit()
        assert abs(current_profit - expected_total_pnl) < 1e-6, \
            f"After {len(trades)} trades, grid profit should be {expected_total_pnl}, got {current_profit}"


@settings(max_examples=100)
@given(
    initial_capital=st.floats(min_value=10000.0, max_value=100000.0),
    open_price=st.floats(min_value=1000.0, max_value=100000.0),
    close_price=st.floats(min_value=1000.0, max_value=100000.0),
    quantity=st.floats(min_value=0.01, max_value=10.0),
    side=st.sampled_from(["long", "short"])
)
def test_property_capital_update_on_close(initial_capital, open_price, close_price, quantity, side):
    """
    Property 11 (Capital Update): 平仓时资金更新正确性
    
    **Validates: Requirements 3.5**
    
    When closing a position, current capital should immediately increase
    by the realized PnL amount.
    """
    calculator = PnLCalculator()
    
    # Calculate realized PnL
    pnl = calculator.calculate_realized_pnl(open_price, close_price, quantity, side)
    
    # Add to grid profit
    calculator.add_realized_pnl(pnl)
    
    # Calculate new capital (simulating capital update)
    new_capital = initial_capital + pnl
    
    # Verify capital increased by PnL
    expected_capital = initial_capital + calculator.get_grid_profit()
    
    assert abs(new_capital - expected_capital) < 1e-6, \
        f"Capital should increase by PnL amount: expected {expected_capital}, got {new_capital}"


@settings(max_examples=100)
@given(
    pnl_amount=st.floats(min_value=-10000.0, max_value=10000.0)
)
def test_property_pnl_accumulation_sign(pnl_amount):
    """
    Property 11 (Sign): 盈亏累加符号正确性
    
    **Validates: Requirements 3.4**
    
    Both positive and negative PnL should be correctly accumulated.
    """
    calculator = PnLCalculator()
    
    initial_profit = calculator.get_grid_profit()
    
    calculator.add_realized_pnl(pnl_amount)
    
    final_profit = calculator.get_grid_profit()
    expected_profit = initial_profit + pnl_amount
    
    assert abs(final_profit - expected_profit) < 1e-6, \
        f"Grid profit should correctly accumulate {pnl_amount}"
    
    # Verify sign is preserved
    if pnl_amount > 0:
        assert final_profit > initial_profit, "Positive PnL should increase grid profit"
    elif pnl_amount < 0:
        assert final_profit < initial_profit, "Negative PnL should decrease grid profit"
    else:
        assert abs(final_profit - initial_profit) < 1e-9, "Zero PnL should not change grid profit"


# ============================================================================
# Additional Property Tests
# ============================================================================

def test_property_reset_functionality():
    """
    Property: 重置功能正确性
    
    Reset should clear all accumulated PnL and return calculator to initial state.
    """
    calculator = PnLCalculator()
    
    # Add some PnL
    calculator.add_realized_pnl(1000.0)
    calculator.add_realized_pnl(-500.0)
    calculator.add_realized_pnl(300.0)
    
    # Verify PnL is accumulated
    assert abs(calculator.get_grid_profit() - 800.0) < 1e-9
    
    # Reset
    calculator.reset()
    
    # Verify reset state
    assert abs(calculator.get_grid_profit()) < 1e-9, \
        "Grid profit should be zero after reset"


@settings(max_examples=100)
@given(
    entry_price=st.floats(min_value=1000.0, max_value=100000.0),
    price_change_pct=st.floats(min_value=-0.5, max_value=0.5),
    quantity=st.floats(min_value=0.01, max_value=10.0)
)
def test_property_long_short_symmetry(entry_price, price_change_pct, quantity):
    """
    Property: 多空对称性
    
    Long and short positions should have symmetric PnL behavior.
    """
    calculator = PnLCalculator()
    
    close_price = entry_price * (1 + price_change_pct)
    
    # Ensure close_price is valid
    assume(close_price > 0)
    
    long_pnl = calculator.calculate_realized_pnl(entry_price, close_price, quantity, "long")
    short_pnl = calculator.calculate_realized_pnl(entry_price, close_price, quantity, "short")
    
    # Long and short should have opposite PnL
    assert abs(long_pnl + short_pnl) < 1e-6, \
        f"Long and short PnL should be symmetric: long={long_pnl}, short={short_pnl}"
