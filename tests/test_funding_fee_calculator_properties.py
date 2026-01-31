"""Property-based tests for FundingFeeCalculator component.

This module contains property-based tests using Hypothesis to verify
the correctness properties of the FundingFeeCalculator component across a wide
range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from strategy_engine.components.funding_fee_calculator import FundingFeeCalculator


# ============================================================================
# Test Data Generators (Strategies)
# ============================================================================

@st.composite
def funding_calculator_strategy(draw):
    """Generate a valid FundingFeeCalculator instance.
    
    Returns:
        FundingFeeCalculator object
    """
    funding_rate = draw(st.floats(min_value=-0.001, max_value=0.001))
    funding_interval = draw(st.integers(min_value=1, max_value=24))  # 1-24 hours
    
    return FundingFeeCalculator(funding_rate, funding_interval)


# ============================================================================
# Property 16: 资金费率计算正确性
# **Validates: Requirements 5.1, 5.2, 5.3**
# ============================================================================

@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size=st.floats(min_value=-10.0, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_funding_fee_calculation_correctness(funding_rate, funding_interval, 
                                                      position_size, current_price):
    """
    Property 16: 资金费率计算正确性
    
    **Validates: Requirements 5.1, 5.2, 5.3**
    
    For any position and funding rate, funding fee should equal:
    position_size × current_price × funding_rate
    
    This property verifies that:
    1. Funding fee = position_size × current_price × funding_rate
    2. Long positions (positive size) pay funding fees (positive result)
    3. Short positions (negative size) receive funding fees (negative result)
    4. Calculations are accurate within floating-point precision
    """
    # Skip zero position size
    assume(abs(position_size) > 0.001)
    
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Calculate funding fee
    funding_fee = calculator.calculate_funding_fee(position_size, current_price)
    
    # Verify calculation formula
    expected_fee = position_size * current_price * funding_rate
    
    assert abs(funding_fee - expected_fee) < 1e-6, \
        f"Funding fee {funding_fee} should equal {expected_fee}"
    
    # Verify fee direction for long positions (positive size)
    if position_size > 0 and funding_rate > 0:
        assert funding_fee > 0, "Long position should pay positive funding fee when rate is positive"
    elif position_size > 0 and funding_rate < 0:
        assert funding_fee < 0, "Long position should receive funding fee when rate is negative"
    
    # Verify fee direction for short positions (negative size)
    if position_size < 0 and funding_rate > 0:
        assert funding_fee < 0, "Short position should receive funding fee when rate is positive"
    elif position_size < 0 and funding_rate < 0:
        assert funding_fee > 0, "Short position should pay funding fee when rate is negative"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=0.0001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size=st.floats(min_value=0.01, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_long_position_pays_positive_rate(funding_rate, funding_interval, 
                                                   position_size, current_price):
    """
    Property 16 (Long Pays): 多仓支付正资金费率
    
    **Validates: Requirements 5.2**
    
    When funding rate is positive and holding long position,
    funding fee should be positive (payment).
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Long position has positive size
    funding_fee = calculator.calculate_funding_fee(position_size, current_price)
    
    assert funding_fee > 0, \
        f"Long position should pay positive funding fee, got {funding_fee}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=0.0001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size=st.floats(min_value=-10.0, max_value=-0.01),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_short_position_receives_positive_rate(funding_rate, funding_interval, 
                                                        position_size, current_price):
    """
    Property 16 (Short Receives): 空仓收取正资金费率
    
    **Validates: Requirements 5.3**
    
    When funding rate is positive and holding short position,
    funding fee should be negative (receipt).
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Short position has negative size
    funding_fee = calculator.calculate_funding_fee(position_size, current_price)
    
    assert funding_fee < 0, \
        f"Short position should receive funding fee (negative), got {funding_fee}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size1=st.floats(min_value=0.01, max_value=10.0),
    position_size2=st.floats(min_value=0.01, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_funding_fee_proportional_to_position(funding_rate, funding_interval,
                                                       position_size1, position_size2, 
                                                       current_price):
    """
    Property 16 (Proportional): 资金费用与仓位大小成正比
    
    **Validates: Requirements 5.1**
    
    Funding fee should be proportional to position size.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    fee1 = calculator.calculate_funding_fee(position_size1, current_price)
    fee2 = calculator.calculate_funding_fee(position_size2, current_price)
    
    # Fee ratio should equal position ratio
    if abs(fee2) > 1e-9 and abs(position_size2) > 1e-9:
        fee_ratio = fee1 / fee2
        position_ratio = position_size1 / position_size2
        
        assert abs(fee_ratio - position_ratio) < 1e-6, \
            f"Fee ratio ({fee_ratio}) should equal position ratio ({position_ratio})"


# ============================================================================
# Property 17: 资金费率结算时间正确性
# **Validates: Requirements 5.4**
# ============================================================================

@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    start_time=st.integers(min_value=1609459200000, max_value=1640995200000),
    time_increments=st.lists(
        st.integers(min_value=0, max_value=10 * 60 * 60 * 1000),  # 0-10 hours in ms
        min_size=5,
        max_size=20
    )
)
def test_property_funding_settlement_time_correctness(funding_rate, funding_interval, 
                                                     start_time, time_increments):
    """
    Property 17: 资金费率结算时间正确性
    
    **Validates: Requirements 5.4**
    
    For any time series, funding rate should settle at configured intervals
    (default 8 hours), and settlement time should be updated after each settlement.
    
    This property verifies that:
    1. Funding settles every funding_interval hours
    2. Settlement time is updated after each settlement
    3. No settlement occurs before interval elapses
    4. Settlement occurs when interval is reached or exceeded
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    funding_interval_ms = funding_interval * 60 * 60 * 1000
    current_time = start_time
    last_settlement_time = None
    
    for increment in time_increments:
        current_time += increment
        
        should_settle = calculator.should_settle_funding(current_time)
        
        if last_settlement_time is None:
            # First call initializes last_funding_time
            last_settlement_time = current_time
            assert not should_settle, "First call should not trigger settlement"
        else:
            time_since_last = current_time - last_settlement_time
            
            if time_since_last >= funding_interval_ms:
                assert should_settle, \
                    f"Should settle when {time_since_last}ms >= {funding_interval_ms}ms"
                
                # Settle and update time
                calculator.settle_funding(current_time)
                last_settlement_time = current_time
            else:
                assert not should_settle, \
                    f"Should not settle when {time_since_last}ms < {funding_interval_ms}ms"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    start_time=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_first_call_initializes_time(funding_rate, funding_interval, start_time):
    """
    Property 17 (Initialization): 首次调用初始化时间
    
    **Validates: Requirements 5.4**
    
    First call to should_settle_funding should initialize last_funding_time
    and return False.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # First call should initialize and return False
    should_settle = calculator.should_settle_funding(start_time)
    
    assert not should_settle, "First call should not trigger settlement"
    assert calculator.last_funding_time == start_time, \
        "First call should initialize last_funding_time"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    start_time=st.integers(min_value=1609459200000, max_value=1640995200000)
)
def test_property_settlement_updates_time(funding_rate, funding_interval, start_time):
    """
    Property 17 (Update): 结算更新时间
    
    **Validates: Requirements 5.4**
    
    After settlement, last_funding_time should be updated to current time.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Initialize
    calculator.should_settle_funding(start_time)
    
    # Move forward by interval
    funding_interval_ms = funding_interval * 60 * 60 * 1000
    settlement_time = start_time + funding_interval_ms
    
    # Should trigger settlement
    should_settle = calculator.should_settle_funding(settlement_time)
    assert should_settle, "Should settle after interval"
    
    # Settle
    calculator.settle_funding(settlement_time)
    
    # Verify time updated
    assert calculator.last_funding_time == settlement_time, \
        "Settlement should update last_funding_time"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    start_time=st.integers(min_value=1609459200000, max_value=1640995200000),
    num_intervals=st.integers(min_value=1, max_value=10)
)
def test_property_multiple_settlements(funding_rate, funding_interval, start_time, num_intervals):
    """
    Property 17 (Multiple): 多次结算正确性
    
    **Validates: Requirements 5.4**
    
    Multiple settlements should occur at correct intervals.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Initialize
    calculator.should_settle_funding(start_time)
    
    funding_interval_ms = funding_interval * 60 * 60 * 1000
    current_time = start_time
    
    for i in range(num_intervals):
        # Move forward by interval
        current_time += funding_interval_ms
        
        # Should trigger settlement
        should_settle = calculator.should_settle_funding(current_time)
        assert should_settle, f"Should settle at interval {i+1}"
        
        # Settle
        calculator.settle_funding(current_time)
        
        # Verify time updated
        assert calculator.last_funding_time == current_time, \
            f"Settlement {i+1} should update last_funding_time"


# ============================================================================
# Property 18: 资金费用累加正确性
# **Validates: Requirements 5.5**
# ============================================================================

@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    fees=st.lists(
        st.floats(min_value=-1000.0, max_value=1000.0),
        min_size=1,
        max_size=20
    )
)
def test_property_funding_fee_accumulation_correctness(funding_rate, funding_interval, fees):
    """
    Property 18: 资金费用累加正确性
    
    **Validates: Requirements 5.5**
    
    For any funding rate settlement, fees should be accumulated to total funding fees,
    and total funding fees should always be non-negative.
    
    This property verifies that:
    1. Fees are accumulated to total_funding_fees
    2. Total funding fees is always non-negative (absolute values)
    3. Multiple fee additions accumulate correctly
    4. Both positive and negative fees are handled correctly
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    expected_total = 0.0
    
    for fee in fees:
        calculator.add_funding_fee(fee)
        expected_total += abs(fee)  # Total should be sum of absolute values
        
        # Verify accumulation
        total_fees = calculator.get_total_funding_fees()
        assert abs(total_fees - expected_total) < 1e-6, \
            f"Total funding fees {total_fees} should equal {expected_total}"
        
        # Verify non-negative
        assert total_fees >= 0, \
            f"Total funding fees should be non-negative, got {total_fees}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    positive_fee=st.floats(min_value=0.01, max_value=1000.0)
)
def test_property_positive_fee_accumulation(funding_rate, funding_interval, positive_fee):
    """
    Property 18 (Positive): 正费用累加
    
    **Validates: Requirements 5.5**
    
    Positive fees should be correctly accumulated.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    initial_total = calculator.get_total_funding_fees()
    
    calculator.add_funding_fee(positive_fee)
    
    final_total = calculator.get_total_funding_fees()
    expected_total = initial_total + positive_fee
    
    assert abs(final_total - expected_total) < 1e-6, \
        f"Total should increase by {positive_fee}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    negative_fee=st.floats(min_value=-1000.0, max_value=-0.01)
)
def test_property_negative_fee_accumulation(funding_rate, funding_interval, negative_fee):
    """
    Property 18 (Negative): 负费用累加（取绝对值）
    
    **Validates: Requirements 5.5**
    
    Negative fees should be accumulated as absolute values.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    initial_total = calculator.get_total_funding_fees()
    
    calculator.add_funding_fee(negative_fee)
    
    final_total = calculator.get_total_funding_fees()
    expected_total = initial_total + abs(negative_fee)
    
    assert abs(final_total - expected_total) < 1e-6, \
        f"Total should increase by absolute value {abs(negative_fee)}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24)
)
def test_property_initial_total_fees_zero(funding_rate, funding_interval):
    """
    Property 18 (Initial): 初始总费用为零
    
    **Validates: Requirements 5.5**
    
    Initial total funding fees should be zero.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    total_fees = calculator.get_total_funding_fees()
    
    assert abs(total_fees) < 1e-9, \
        f"Initial total funding fees should be zero, got {total_fees}"


# ============================================================================
# Property 19: 零仓位无费用
# **Validates: Requirements 5.6**
# ============================================================================

@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_zero_position_no_fee(funding_rate, funding_interval, current_price):
    """
    Property 19: 零仓位无费用
    
    **Validates: Requirements 5.6**
    
    When net position is zero, system should not calculate or deduct funding fees.
    
    This property verifies that:
    1. Zero position size results in zero funding fee
    2. No fees are accumulated for zero positions
    3. System correctly handles zero position edge case
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Calculate funding fee for zero position
    funding_fee = calculator.calculate_funding_fee(0.0, current_price)
    
    assert abs(funding_fee) < 1e-9, \
        f"Funding fee should be zero for zero position, got {funding_fee}"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_near_zero_position_minimal_fee(funding_rate, funding_interval, current_price):
    """
    Property 19 (Near Zero): 接近零仓位费用极小
    
    **Validates: Requirements 5.6**
    
    Very small positions should result in very small fees.
    """
    # Skip zero funding rate
    assume(abs(funding_rate) > 1e-9)
    
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    # Very small position
    tiny_position = 0.0001
    
    funding_fee = calculator.calculate_funding_fee(tiny_position, current_price)
    
    # Fee should be proportionally small
    expected_fee = tiny_position * current_price * funding_rate
    
    assert abs(funding_fee - expected_fee) < 1e-6, \
        f"Fee for tiny position should be proportionally small"
    
    # Fee magnitude should be very small
    assert abs(funding_fee) < abs(current_price * funding_rate), \
        "Fee for tiny position should be smaller than price × rate"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size=st.floats(min_value=-10.0, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_zero_rate_no_fee(funding_rate, funding_interval, position_size, current_price):
    """
    Property 19 (Zero Rate): 零费率无费用
    
    **Validates: Requirements 5.6**
    
    When funding rate is zero, no fees should be charged regardless of position.
    """
    # Use zero funding rate
    calculator = FundingFeeCalculator(0.0, funding_interval)
    
    funding_fee = calculator.calculate_funding_fee(position_size, current_price)
    
    assert abs(funding_fee) < 1e-9, \
        f"Funding fee should be zero when rate is zero, got {funding_fee}"


# ============================================================================
# Additional Property Tests
# ============================================================================

def test_property_reset_functionality():
    """
    Property: 重置功能正确性
    
    Reset should clear all accumulated fees and return calculator to initial state.
    """
    calculator = FundingFeeCalculator(0.0005, 8)
    
    # Add some fees
    calculator.add_funding_fee(100.0)
    calculator.add_funding_fee(-50.0)
    calculator.add_funding_fee(30.0)
    
    # Set funding time
    calculator.last_funding_time = 1609459200000
    
    # Verify fees are accumulated
    assert calculator.get_total_funding_fees() > 0
    assert calculator.last_funding_time > 0
    
    # Reset
    calculator.reset()
    
    # Verify reset state
    assert abs(calculator.get_total_funding_fees()) < 1e-9, \
        "Total funding fees should be zero after reset"
    assert calculator.last_funding_time == 0, \
        "Last funding time should be zero after reset"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=-0.001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    position_size=st.floats(min_value=-10.0, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_fee_calculation_idempotent(funding_rate, funding_interval, 
                                            position_size, current_price):
    """
    Property: 费用计算幂等性
    
    Calculating funding fee multiple times should return the same result.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    fee1 = calculator.calculate_funding_fee(position_size, current_price)
    fee2 = calculator.calculate_funding_fee(position_size, current_price)
    fee3 = calculator.calculate_funding_fee(position_size, current_price)
    
    assert fee1 == fee2 == fee3, \
        "Funding fee calculation should be idempotent"


@settings(max_examples=100)
@given(
    funding_rate=st.floats(min_value=0.0001, max_value=0.001),
    funding_interval=st.integers(min_value=1, max_value=24),
    long_position=st.floats(min_value=0.01, max_value=10.0),
    current_price=st.floats(min_value=1000.0, max_value=100000.0)
)
def test_property_long_short_opposite_fees(funding_rate, funding_interval, 
                                          long_position, current_price):
    """
    Property: 多空费用对称性
    
    Long and short positions of same size should have opposite funding fees.
    """
    calculator = FundingFeeCalculator(funding_rate, funding_interval)
    
    long_fee = calculator.calculate_funding_fee(long_position, current_price)
    short_fee = calculator.calculate_funding_fee(-long_position, current_price)
    
    # Fees should be opposite
    assert abs(long_fee + short_fee) < 1e-6, \
        f"Long fee ({long_fee}) and short fee ({short_fee}) should be opposite"
