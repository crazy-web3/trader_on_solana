"""Property-based tests for MarginCalculator component.

This module contains property-based tests using Hypothesis to verify
the correctness properties of the MarginCalculator component across a wide
range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from strategy_engine.components.margin_calculator import MarginCalculator


# ============================================================================
# Test Data Generators (Strategies)
# ============================================================================

@st.composite
def margin_data_strategy(draw):
    """Generate valid margin calculation data.
    
    Returns:
        Tuple of (quantity, price, leverage)
    """
    quantity = draw(st.floats(min_value=0.01, max_value=10.0))
    price = draw(st.floats(min_value=1000.0, max_value=100000.0))
    leverage = draw(st.floats(min_value=1.0, max_value=10.0))
    
    return quantity, price, leverage


@st.composite
def capital_strategy(draw):
    """Generate valid capital amounts.
    
    Returns:
        Total capital amount
    """
    return draw(st.floats(min_value=1000.0, max_value=100000.0))


# ============================================================================
# Property 4: 保证金计算正确性
# **Validates: Requirements 2.1, 2.4**
# ============================================================================

@settings(max_examples=100)
@given(
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_margin_calculation_correctness(quantity, price, leverage, total_capital):
    """
    Property 4: 保证金计算正确性
    
    **Validates: Requirements 2.1, 2.4**
    
    For any opening operation, the required margin should equal
    (contract_value / leverage), and available capital should equal
    (total_capital - used_margin).
    
    This property verifies that:
    1. Required margin = quantity × price / leverage
    2. Available capital = total_capital - used_margin
    3. After allocation, used_margin increases by the allocated amount
    4. Calculations are accurate within floating-point precision
    """
    calculator = MarginCalculator(leverage)
    
    # Calculate required margin
    required_margin = calculator.calculate_required_margin(quantity, price)
    
    # Verify margin calculation formula: quantity × price / leverage
    expected_margin = quantity * price / leverage
    assert abs(required_margin - expected_margin) < 1e-6, \
        f"Required margin {required_margin} should equal {expected_margin}"
    
    # Verify initial available capital
    initial_available = calculator.get_available_capital(total_capital)
    assert abs(initial_available - total_capital) < 1e-9, \
        f"Initial available capital should equal total capital"
    
    # Allocate margin if sufficient capital
    if required_margin <= total_capital:
        success = calculator.allocate_margin(required_margin, total_capital)
        assert success, "Allocation should succeed when capital is sufficient"
        
        # Verify used margin increased
        assert abs(calculator.get_used_margin() - required_margin) < 1e-9, \
            f"Used margin should equal allocated amount {required_margin}"
        
        # Verify available capital decreased
        available_after = calculator.get_available_capital(total_capital)
        expected_available = total_capital - required_margin
        assert abs(available_after - expected_available) < 1e-6, \
            f"Available capital {available_after} should equal {expected_available}"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_available_capital_formula(leverage, total_capital):
    """
    Property 4 (Available Capital): 可用资金计算公式
    
    **Validates: Requirements 2.4**
    
    Available capital should always equal total_capital - used_margin,
    regardless of how many allocations have been made.
    """
    calculator = MarginCalculator(leverage)
    
    # Make multiple allocations
    allocations = [1000.0, 2000.0, 1500.0]
    total_allocated = 0.0
    
    for amount in allocations:
        if total_allocated + amount <= total_capital:
            success = calculator.allocate_margin(amount, total_capital)
            if success:
                total_allocated += amount
                
                # Verify available capital formula
                available = calculator.get_available_capital(total_capital)
                expected = total_capital - total_allocated
                assert abs(available - expected) < 1e-6, \
                    f"Available capital {available} should equal {expected}"


@settings(max_examples=100)
@given(
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    leverage=st.floats(min_value=1.0, max_value=10.0)
)
def test_property_margin_calculation_positive(quantity, price, leverage):
    """
    Property 4 (Positive): 保证金计算为正数
    
    **Validates: Requirements 2.1**
    
    Required margin should always be positive for positive quantity and price.
    """
    calculator = MarginCalculator(leverage)
    
    required_margin = calculator.calculate_required_margin(quantity, price)
    
    assert required_margin > 0, \
        f"Required margin should be positive, got {required_margin}"
    
    # Verify it's proportional to quantity and price
    assert required_margin <= quantity * price, \
        "Required margin should not exceed contract value"


# ============================================================================
# Property 5: 保证金不变式
# **Validates: Requirements 2.5**
# ============================================================================

@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    operations=st.lists(
        st.tuples(
            st.sampled_from(['allocate', 'release']),
            st.floats(min_value=100.0, max_value=5000.0)
        ),
        min_size=1,
        max_size=20
    )
)
def test_property_margin_invariant(leverage, total_capital, operations):
    """
    Property 5: 保证金不变式
    
    **Validates: Requirements 2.5**
    
    For any system state, used_margin should always be less than or equal
    to total_capital, i.e., used_margin <= total_capital.
    
    This property verifies that:
    1. The invariant holds after initialization
    2. The invariant holds after any allocation
    3. The invariant holds after any release
    4. The invariant holds after any sequence of operations
    """
    calculator = MarginCalculator(leverage)
    
    # Verify initial invariant
    assert calculator.get_used_margin() <= total_capital, \
        "Initial used margin should be <= total capital"
    
    # Perform a sequence of operations
    for operation, amount in operations:
        if operation == 'allocate':
            # Try to allocate margin
            calculator.allocate_margin(amount, total_capital)
        else:  # release
            # Release margin (only if we have used margin)
            if calculator.get_used_margin() > 0:
                release_amount = min(amount, calculator.get_used_margin())
                calculator.release_margin(release_amount)
        
        # Verify invariant after each operation
        used_margin = calculator.get_used_margin()
        assert used_margin <= total_capital, \
            f"Invariant violated: used_margin {used_margin} > total_capital {total_capital}"
        
        # Also verify used margin is non-negative
        assert used_margin >= 0, \
            f"Used margin should be non-negative, got {used_margin}"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_margin_invariant_simple(leverage, total_capital):
    """
    Property 5 (Simple): 保证金不变式简单测试
    
    **Validates: Requirements 2.5**
    
    Simplified test that verifies the invariant holds for basic operations.
    """
    calculator = MarginCalculator(leverage)
    
    # Allocate some margin
    amount1 = total_capital * 0.3
    success1 = calculator.allocate_margin(amount1, total_capital)
    
    if success1:
        assert calculator.get_used_margin() <= total_capital, \
            "Invariant should hold after first allocation"
        
        # Allocate more margin
        amount2 = total_capital * 0.4
        success2 = calculator.allocate_margin(amount2, total_capital)
        
        assert calculator.get_used_margin() <= total_capital, \
            "Invariant should hold after second allocation"
        
        # Release some margin
        calculator.release_margin(amount1)
        
        assert calculator.get_used_margin() <= total_capital, \
            "Invariant should hold after release"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_total_capital_equation(leverage, total_capital):
    """
    Property 5 (Equation): 总资金等式
    
    **Validates: Requirements 2.5**
    
    Verifies that total_capital = used_margin + available_capital at all times.
    """
    calculator = MarginCalculator(leverage)
    
    # Verify initial equation
    used = calculator.get_used_margin()
    available = calculator.get_available_capital(total_capital)
    assert abs((used + available) - total_capital) < 1e-6, \
        f"Initial: used ({used}) + available ({available}) should equal total ({total_capital})"
    
    # Allocate some margin
    amount = total_capital * 0.5
    calculator.allocate_margin(amount, total_capital)
    
    # Verify equation after allocation
    used = calculator.get_used_margin()
    available = calculator.get_available_capital(total_capital)
    assert abs((used + available) - total_capital) < 1e-6, \
        f"After allocation: used ({used}) + available ({available}) should equal total ({total_capital})"
    
    # Release some margin
    calculator.release_margin(amount * 0.5)
    
    # Verify equation after release
    used = calculator.get_used_margin()
    available = calculator.get_available_capital(total_capital)
    assert abs((used + available) - total_capital) < 1e-6, \
        f"After release: used ({used}) + available ({available}) should equal total ({total_capital})"


# ============================================================================
# Property 6: 保证金不足拒绝
# **Validates: Requirements 2.2**
# ============================================================================

@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=1000.0, max_value=10000.0),
    excess_factor=st.floats(min_value=1.1, max_value=2.0)
)
def test_property_insufficient_margin_rejection(leverage, total_capital, excess_factor):
    """
    Property 6: 保证金不足拒绝
    
    **Validates: Requirements 2.2**
    
    When available capital is insufficient, the system should reject
    the margin allocation and maintain the current state unchanged.
    
    This property verifies that:
    1. Allocation fails when required margin > available capital
    2. Used margin remains unchanged after failed allocation
    3. Available capital remains unchanged after failed allocation
    4. System state is consistent after rejection
    """
    calculator = MarginCalculator(leverage)
    
    # Save initial state
    initial_used = calculator.get_used_margin()
    initial_available = calculator.get_available_capital(total_capital)
    
    # Try to allocate more than available capital
    excessive_amount = total_capital * excess_factor
    
    success = calculator.allocate_margin(excessive_amount, total_capital)
    
    # Allocation should fail
    assert not success, \
        f"Allocation should fail when amount ({excessive_amount}) > total capital ({total_capital})"
    
    # Verify state is unchanged
    assert abs(calculator.get_used_margin() - initial_used) < 1e-9, \
        "Used margin should remain unchanged after failed allocation"
    
    assert abs(calculator.get_available_capital(total_capital) - initial_available) < 1e-9, \
        "Available capital should remain unchanged after failed allocation"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    first_allocation_ratio=st.floats(min_value=0.6, max_value=0.9)
)
def test_property_insufficient_margin_after_allocation(leverage, total_capital, 
                                                       first_allocation_ratio):
    """
    Property 6 (Sequential): 多次分配后保证金不足拒绝
    
    **Validates: Requirements 2.2**
    
    After allocating some margin, subsequent allocations that exceed
    remaining available capital should be rejected.
    """
    calculator = MarginCalculator(leverage)
    
    # First allocation (use most of the capital)
    first_amount = total_capital * first_allocation_ratio
    success1 = calculator.allocate_margin(first_amount, total_capital)
    assert success1, "First allocation should succeed"
    
    # Save state after first allocation
    used_after_first = calculator.get_used_margin()
    available_after_first = calculator.get_available_capital(total_capital)
    
    # Try to allocate more than remaining available capital
    excessive_amount = available_after_first * 1.5
    
    success2 = calculator.allocate_margin(excessive_amount, total_capital)
    
    # Second allocation should fail
    assert not success2, \
        f"Second allocation should fail when amount ({excessive_amount}) > " \
        f"available capital ({available_after_first})"
    
    # Verify state is unchanged after failed allocation
    assert abs(calculator.get_used_margin() - used_after_first) < 1e-9, \
        "Used margin should remain unchanged after failed second allocation"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_exact_capital_allocation(leverage, total_capital):
    """
    Property 6 (Boundary): 精确资金分配边界测试
    
    **Validates: Requirements 2.2**
    
    Allocation should succeed when amount exactly equals available capital,
    and fail when amount exceeds it by even a small amount.
    """
    calculator = MarginCalculator(leverage)
    
    # Allocate exactly the total capital
    success = calculator.allocate_margin(total_capital, total_capital)
    assert success, "Allocation should succeed when amount equals total capital"
    
    # Verify all capital is used
    assert abs(calculator.get_used_margin() - total_capital) < 1e-9, \
        "All capital should be used"
    assert abs(calculator.get_available_capital(total_capital)) < 1e-9, \
        "Available capital should be zero"
    
    # Try to allocate even a tiny amount more
    calculator2 = MarginCalculator(leverage)
    success2 = calculator2.allocate_margin(total_capital + 0.01, total_capital)
    assert not success2, \
        "Allocation should fail when amount exceeds total capital by any amount"


# ============================================================================
# Property 7: 保证金释放正确性
# **Validates: Requirements 2.3**
# ============================================================================

@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    allocation_amount=st.floats(min_value=1000.0, max_value=5000.0)
)
def test_property_margin_release_correctness(leverage, total_capital, allocation_amount):
    """
    Property 7: 保证金释放正确性
    
    **Validates: Requirements 2.3**
    
    When closing a position, the system should release the corresponding
    margin, and the used margin should decrease by the released amount.
    
    This property verifies that:
    1. Released margin reduces used_margin by the correct amount
    2. Available capital increases by the released amount
    3. Release operation maintains system consistency
    4. Multiple releases work correctly
    """
    # Ensure allocation amount doesn't exceed total capital
    assume(allocation_amount <= total_capital)
    
    calculator = MarginCalculator(leverage)
    
    # Allocate some margin
    success = calculator.allocate_margin(allocation_amount, total_capital)
    assume(success)  # Only test if allocation succeeded
    
    # Save state after allocation
    used_after_allocation = calculator.get_used_margin()
    available_after_allocation = calculator.get_available_capital(total_capital)
    
    # Release the margin
    calculator.release_margin(allocation_amount)
    
    # Verify used margin decreased
    used_after_release = calculator.get_used_margin()
    expected_used = used_after_allocation - allocation_amount
    assert abs(used_after_release - expected_used) < 1e-6, \
        f"Used margin should decrease by {allocation_amount}, " \
        f"expected {expected_used}, got {used_after_release}"
    
    # Verify available capital increased
    available_after_release = calculator.get_available_capital(total_capital)
    expected_available = available_after_allocation + allocation_amount
    assert abs(available_after_release - expected_available) < 1e-6, \
        f"Available capital should increase by {allocation_amount}, " \
        f"expected {expected_available}, got {available_after_release}"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_margin_release_round_trip(leverage, total_capital):
    """
    Property 7 (Round Trip): 保证金分配释放往返测试
    
    **Validates: Requirements 2.3**
    
    Allocating and then releasing the same amount of margin should
    return the system to its initial state.
    """
    calculator = MarginCalculator(leverage)
    
    # Save initial state
    initial_used = calculator.get_used_margin()
    initial_available = calculator.get_available_capital(total_capital)
    
    # Allocate some margin
    amount = total_capital * 0.5
    success = calculator.allocate_margin(amount, total_capital)
    assume(success)
    
    # Release the same amount
    calculator.release_margin(amount)
    
    # Verify we're back to initial state
    final_used = calculator.get_used_margin()
    final_available = calculator.get_available_capital(total_capital)
    
    assert abs(final_used - initial_used) < 1e-6, \
        f"After round trip, used margin should return to initial value"
    
    assert abs(final_available - initial_available) < 1e-6, \
        f"After round trip, available capital should return to initial value"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    allocations=st.lists(
        st.floats(min_value=500.0, max_value=2000.0),
        min_size=2,
        max_size=5
    )
)
def test_property_multiple_margin_releases(leverage, total_capital, allocations):
    """
    Property 7 (Multiple): 多次保证金释放正确性
    
    **Validates: Requirements 2.3**
    
    Multiple margin releases should correctly reduce used margin each time.
    """
    calculator = MarginCalculator(leverage)
    
    # Allocate multiple times
    total_allocated = 0.0
    successful_allocations = []
    
    for amount in allocations:
        if total_allocated + amount <= total_capital:
            success = calculator.allocate_margin(amount, total_capital)
            if success:
                total_allocated += amount
                successful_allocations.append(amount)
    
    assume(len(successful_allocations) >= 2)  # Need at least 2 successful allocations
    
    # Release margins one by one
    for amount in successful_allocations:
        used_before = calculator.get_used_margin()
        
        calculator.release_margin(amount)
        
        used_after = calculator.get_used_margin()
        expected_used = used_before - amount
        
        assert abs(used_after - expected_used) < 1e-6, \
            f"Used margin should decrease by {amount} after each release"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    allocation_amount=st.floats(min_value=1000.0, max_value=5000.0),
    release_amount=st.floats(min_value=500.0, max_value=2000.0)
)
def test_property_partial_margin_release(leverage, total_capital, 
                                         allocation_amount, release_amount):
    """
    Property 7 (Partial): 部分保证金释放正确性
    
    **Validates: Requirements 2.3**
    
    Releasing less margin than allocated should correctly reduce used margin
    by the released amount, leaving the remainder still allocated.
    """
    assume(allocation_amount <= total_capital)
    assume(release_amount < allocation_amount)
    
    calculator = MarginCalculator(leverage)
    
    # Allocate margin
    success = calculator.allocate_margin(allocation_amount, total_capital)
    assume(success)
    
    used_after_allocation = calculator.get_used_margin()
    
    # Release partial margin
    calculator.release_margin(release_amount)
    
    # Verify partial release
    used_after_release = calculator.get_used_margin()
    expected_remaining = allocation_amount - release_amount
    
    assert abs(used_after_release - expected_remaining) < 1e-6, \
        f"After partial release, used margin should be {expected_remaining}, got {used_after_release}"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0),
    allocation_amount=st.floats(min_value=1000.0, max_value=5000.0),
    excess_release=st.floats(min_value=1.1, max_value=2.0)
)
def test_property_excessive_margin_release(leverage, total_capital, 
                                           allocation_amount, excess_release):
    """
    Property 7 (Excessive): 过量保证金释放保护
    
    **Validates: Requirements 2.3**
    
    Releasing more margin than allocated should not cause used margin
    to become negative. The system should handle this gracefully.
    """
    assume(allocation_amount <= total_capital)
    
    calculator = MarginCalculator(leverage)
    
    # Allocate some margin
    success = calculator.allocate_margin(allocation_amount, total_capital)
    assume(success)
    
    # Try to release more than allocated
    excessive_amount = allocation_amount * excess_release
    calculator.release_margin(excessive_amount)
    
    # Verify used margin is not negative
    used_after_release = calculator.get_used_margin()
    assert used_after_release >= 0, \
        f"Used margin should not be negative after excessive release, got {used_after_release}"
    
    # Should be zero or close to zero
    assert abs(used_after_release) < 1e-6, \
        f"Used margin should be zero after releasing more than allocated, got {used_after_release}"


# ============================================================================
# Additional Property Tests
# ============================================================================

@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0)
)
def test_property_reset_functionality(leverage):
    """
    Property: 重置功能正确性
    
    Reset should clear all used margin and return calculator to initial state.
    """
    calculator = MarginCalculator(leverage)
    total_capital = 50000.0
    
    # Allocate some margin
    calculator.allocate_margin(10000.0, total_capital)
    calculator.allocate_margin(5000.0, total_capital)
    
    # Verify margin is used
    assert calculator.get_used_margin() > 0
    
    # Reset
    calculator.reset()
    
    # Verify reset state
    assert abs(calculator.get_used_margin()) < 1e-9, \
        "Used margin should be zero after reset"
    assert abs(calculator.get_available_capital(total_capital) - total_capital) < 1e-9, \
        "Available capital should equal total capital after reset"


@settings(max_examples=100)
@given(
    quantity=st.floats(min_value=0.01, max_value=10.0),
    price=st.floats(min_value=1000.0, max_value=100000.0),
    leverage1=st.floats(min_value=1.0, max_value=5.0),
    leverage2=st.floats(min_value=5.0, max_value=10.0)
)
def test_property_leverage_effect(quantity, price, leverage1, leverage2):
    """
    Property: 杠杆效应正确性
    
    Higher leverage should result in lower required margin for the same position.
    """
    # Skip if leverages are too close (within 0.1)
    assume(abs(leverage2 - leverage1) > 0.1)
    
    calc1 = MarginCalculator(leverage1)
    calc2 = MarginCalculator(leverage2)
    
    margin1 = calc1.calculate_required_margin(quantity, price)
    margin2 = calc2.calculate_required_margin(quantity, price)
    
    # Higher leverage should require less margin
    assert margin2 < margin1, \
        f"Higher leverage ({leverage2}) should require less margin than lower leverage ({leverage1})"
    
    # Verify the ratio: margin1/margin2 should equal leverage2/leverage1
    # Because margin = quantity * price / leverage
    # So margin1/margin2 = (quantity * price / leverage1) / (quantity * price / leverage2)
    #                    = leverage2 / leverage1
    expected_ratio = leverage2 / leverage1
    actual_ratio = margin1 / margin2
    assert abs(actual_ratio - expected_ratio) < 1e-6, \
        f"Margin ratio should equal leverage ratio: expected {expected_ratio}, got {actual_ratio}"


@settings(max_examples=100)
@given(
    leverage=st.floats(min_value=1.0, max_value=10.0),
    total_capital=st.floats(min_value=10000.0, max_value=100000.0)
)
def test_property_idempotent_queries(leverage, total_capital):
    """
    Property: 查询操作幂等性
    
    Querying used margin and available capital should not change state
    and should return consistent results.
    """
    calculator = MarginCalculator(leverage)
    
    # Allocate some margin
    calculator.allocate_margin(5000.0, total_capital)
    
    # Query multiple times
    used1 = calculator.get_used_margin()
    used2 = calculator.get_used_margin()
    used3 = calculator.get_used_margin()
    
    available1 = calculator.get_available_capital(total_capital)
    available2 = calculator.get_available_capital(total_capital)
    available3 = calculator.get_available_capital(total_capital)
    
    # All queries should return the same value
    assert used1 == used2 == used3, \
        "Querying used margin should return consistent results"
    
    assert available1 == available2 == available3, \
        "Querying available capital should return consistent results"
