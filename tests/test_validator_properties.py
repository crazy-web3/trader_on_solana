"""Property-based tests for the KlineDataValidator.

**Feature: market-data-layer**

These tests verify the correctness properties of the KlineDataValidator
using property-based testing with Hypothesis.
"""

from hypothesis import given, strategies as st, assume
from hypothesis.strategies import composite
from market_data_layer.models import KlineData
from market_data_layer.validator import KlineDataValidator


# Strategy for generating valid K-line data
# We need to ensure high >= low, so we generate two prices and use max/min
@composite
def valid_kline_strategy(draw):
    """Generate valid K-line data with high >= low >= 0."""
    timestamp = draw(st.integers(min_value=0, max_value=9999999999999))
    
    # Generate two prices and ensure high >= low
    price1 = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
    price2 = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
    high = max(price1, price2)
    low = min(price1, price2)
    
    open_price = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
    close_price = draw(st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False))
    volume = draw(st.floats(min_value=0.0, max_value=999_999_999.0, allow_nan=False, allow_infinity=False))
    
    return KlineData(
        timestamp=timestamp,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=volume,
    )


class TestValidatorProperty11:
    """Property 11: 价格关系验证 (high >= low >= 0)
    
    **Validates: Requirements 7.1**
    
    For any K-line data where high >= low >= 0, the validation should pass.
    For any K-line data where high < low or low < 0, the validation should fail.
    """
    
    @given(valid_kline_strategy())
    def test_property_11_valid_price_relationship(self, kline):
        """Test that valid price relationships pass validation.
        
        For any K-line where high >= low >= 0, validation should pass.
        """
        # Ensure high >= low >= 0
        assume(kline.high >= kline.low >= 0)
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        # Should not have price relationship errors
        price_errors = [e for e in result.errors if "high" in e or "low" in e]
        assert len(price_errors) == 0, f"Unexpected price errors: {price_errors}"
    
    @given(
        st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_11_invalid_high_less_than_low(self, high, low):
        """Test that high < low fails validation.
        
        For any K-line where high < low, validation should fail with a price relationship error.
        """
        assume(high < low)
        
        kline = KlineData(
            timestamp=1609459200000,
            open=low,
            high=high,
            low=low,
            close=low,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("high" in e and "low" in e for e in result.errors)
    
    @given(st.floats(min_value=-1_000_000.0, max_value=-0.1, allow_nan=False, allow_infinity=False))
    def test_property_11_invalid_negative_low(self, low):
        """Test that negative low price fails validation.
        
        For any K-line where low < 0, validation should fail.
        """
        kline = KlineData(
            timestamp=1609459200000,
            open=0.0,
            high=100.0,
            low=low,
            close=50.0,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("low" in e for e in result.errors)


class TestValidatorProperty12:
    """Property 12: 价格范围验证
    
    **Validates: Requirements 7.2**
    
    For any K-line data where all prices (open, high, low, close) are in the
    valid range (0 to MAX_PRICE), validation should pass.
    For any K-line data where any price is outside this range, validation should fail.
    """
    
    @given(valid_kline_strategy())
    def test_property_12_valid_price_range(self, kline):
        """Test that prices in valid range pass validation.
        
        For any K-line where all prices are in [0, MAX_PRICE], validation should pass.
        """
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        # Should not have price range errors
        range_errors = [e for e in result.errors if "price" in e and ("open" in e or "high" in e or "low" in e or "close" in e)]
        assert len(range_errors) == 0, f"Unexpected price range errors: {range_errors}"
    
    @given(st.floats(min_value=-1_000_000.0, max_value=-0.1, allow_nan=False, allow_infinity=False))
    def test_property_12_invalid_negative_open(self, open_price):
        """Test that negative open price fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=open_price,
            high=100.0,
            low=50.0,
            close=75.0,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("open" in e for e in result.errors)
    
    @given(st.floats(min_value=1_000_001.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False))
    def test_property_12_invalid_high_exceeds_max(self, high):
        """Test that high price exceeding MAX_PRICE fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=high,
            low=50.0,
            close=75.0,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("high" in e for e in result.errors)
    
    @given(st.floats(min_value=1_000_001.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False))
    def test_property_12_invalid_close_exceeds_max(self, close):
        """Test that close price exceeding MAX_PRICE fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=100.0,
            low=50.0,
            close=close,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("close" in e for e in result.errors)


class TestValidatorProperty13:
    """Property 13: 成交量非负验证
    
    **Validates: Requirements 7.3**
    
    For any K-line data where volume >= 0, validation should pass.
    For any K-line data where volume < 0, validation should fail.
    """
    
    @given(valid_kline_strategy())
    def test_property_13_valid_volume(self, kline):
        """Test that non-negative volume passes validation.
        
        For any K-line where volume >= 0, validation should pass.
        """
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        # Should not have volume errors
        volume_errors = [e for e in result.errors if "volume" in e]
        assert len(volume_errors) == 0, f"Unexpected volume errors: {volume_errors}"
    
    @given(st.floats(min_value=-999_999_999.0, max_value=-0.1, allow_nan=False, allow_infinity=False))
    def test_property_13_invalid_negative_volume(self, volume):
        """Test that negative volume fails validation.
        
        For any K-line where volume < 0, validation should fail.
        """
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=volume,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is False
        assert any("volume" in e for e in result.errors)
    
    @given(st.floats(min_value=0.0, max_value=999_999_999.0, allow_nan=False, allow_infinity=False))
    def test_property_13_zero_and_positive_volume_valid(self, volume):
        """Test that zero and positive volumes pass validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=volume,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        # Should not have volume errors
        volume_errors = [e for e in result.errors if "volume" in e]
        assert len(volume_errors) == 0, f"Unexpected volume errors: {volume_errors}"


class TestValidatorPropertyCombined:
    """Combined property tests for multiple validation rules."""
    
    @given(valid_kline_strategy())
    def test_property_combined_all_valid_passes(self, kline):
        """Test that K-line data with all valid properties passes validation.
        
        For any K-line where all properties are valid, validation should pass.
        """
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        assert result.isValid is True
        assert result.errors == []
    
    @given(
        st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    )
    def test_property_combined_high_low_relationship(self, price1, price2):
        """Test that high >= low relationship is always enforced.
        
        For any two prices, when high >= low, validation should pass the price relationship check.
        """
        high = max(price1, price2)
        low = min(price1, price2)
        
        kline = KlineData(
            timestamp=1609459200000,
            open=low,
            high=high,
            low=low,
            close=low,
            volume=1000.0,
        )
        
        validator = KlineDataValidator()
        result = validator.validate(kline)
        
        # Should not have high < low errors
        assert not any("high" in e and "low" in e for e in result.errors)
