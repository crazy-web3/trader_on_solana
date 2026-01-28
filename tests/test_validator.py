"""Tests for the KlineDataValidator."""

import pytest
from market_data_layer.models import KlineData, ValidationResult
from market_data_layer.validator import KlineDataValidator


class TestKlineDataValidatorBasic:
    """Basic tests for KlineDataValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_validate_valid_kline_data(self):
        """Test validation of valid K-line data."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True
        assert result.errors == []
    
    def test_validate_returns_validation_result(self):
        """Test that validate returns a ValidationResult object."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert isinstance(result, ValidationResult)


class TestPriceRelationshipValidation:
    """Tests for price relationship validation (high >= low >= 0)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_high_less_than_low_fails_validation(self):
        """Test that high < low fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=90.0,
            low=95.0,
            close=92.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("high" in error and "low" in error for error in result.errors)
    
    def test_low_negative_fails_validation(self):
        """Test that negative low price fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=-5.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("low" in error for error in result.errors)
    
    def test_high_equals_low_passes_validation(self):
        """Test that high == low passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True
    
    def test_low_equals_zero_passes_validation(self):
        """Test that low == 0 passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=0.0,
            high=5.0,
            low=0.0,
            close=2.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True


class TestPriceRangeValidation:
    """Tests for price range validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_open_price_negative_fails_validation(self):
        """Test that negative open price fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=-100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("open" in error for error in result.errors)
    
    def test_close_price_exceeds_max_fails_validation(self):
        """Test that close price exceeding max fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=2_000_000.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("close" in error for error in result.errors)
    
    def test_high_price_at_max_passes_validation(self):
        """Test that high price at max passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=999_999.0,
            high=1_000_000.0,
            low=999_999.0,
            close=999_999.5,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True
    
    def test_all_prices_zero_passes_validation(self):
        """Test that all prices at zero passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=0.0,
            high=0.0,
            low=0.0,
            close=0.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True


class TestVolumeValidation:
    """Tests for volume validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_negative_volume_fails_validation(self):
        """Test that negative volume fails validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=-1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("volume" in error for error in result.errors)
    
    def test_zero_volume_passes_validation(self):
        """Test that zero volume passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=0.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True
    
    def test_large_volume_passes_validation(self):
        """Test that large volume passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=999_999_999.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True


class TestTimestampValidation:
    """Tests for timestamp validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_negative_timestamp_fails_validation(self):
        """Test that negative timestamp fails validation."""
        kline = KlineData(
            timestamp=-1000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("timestamp" in error for error in result.errors)
    
    def test_zero_timestamp_passes_validation(self):
        """Test that zero timestamp passes validation."""
        kline = KlineData(
            timestamp=0,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True
    
    def test_timestamp_exceeds_max_fails_validation(self):
        """Test that timestamp exceeding max fails validation."""
        kline = KlineData(
            timestamp=10_000_000_000_000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert any("timestamp" in error for error in result.errors)
    
    def test_valid_timestamp_passes_validation(self):
        """Test that valid timestamp passes validation."""
        kline = KlineData(
            timestamp=1609459200000,
            open=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is True


class TestBatchValidation:
    """Tests for batch validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_validate_batch_returns_list(self):
        """Test that validate_batch returns a list."""
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 60000,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
            )
            for i in range(3)
        ]
        
        results = self.validator.validate_batch(klines)
        
        assert isinstance(results, list)
        assert len(results) == 3
    
    def test_validate_batch_all_valid(self):
        """Test batch validation with all valid data."""
        klines = [
            KlineData(
                timestamp=1609459200000 + i * 60000,
                open=100.0 + i,
                high=105.0 + i,
                low=95.0 + i,
                close=102.0 + i,
                volume=1000.0 + i,
            )
            for i in range(5)
        ]
        
        results = self.validator.validate_batch(klines)
        
        assert all(result.isValid for result in results)
    
    def test_validate_batch_mixed_valid_invalid(self):
        """Test batch validation with mixed valid and invalid data."""
        klines = [
            KlineData(
                timestamp=1609459200000,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000.0,
            ),
            KlineData(
                timestamp=1609459200000,
                open=100.0,
                high=90.0,
                low=95.0,
                close=92.0,
                volume=1000.0,
            ),
            KlineData(
                timestamp=1609459200000,
                open=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=-100.0,
            ),
        ]
        
        results = self.validator.validate_batch(klines)
        
        assert results[0].isValid is True
        assert results[1].isValid is False
        assert results[2].isValid is False
    
    def test_validate_batch_empty_list(self):
        """Test batch validation with empty list."""
        results = self.validator.validate_batch([])
        
        assert results == []


class TestMultipleValidationErrors:
    """Tests for multiple validation errors in a single K-line."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = KlineDataValidator()
    
    def test_multiple_errors_reported(self):
        """Test that multiple validation errors are reported."""
        kline = KlineData(
            timestamp=-1000,
            open=-100.0,
            high=90.0,
            low=95.0,
            close=2_000_000.0,
            volume=-1000.0,
        )
        
        result = self.validator.validate(kline)
        
        assert result.isValid is False
        assert len(result.errors) > 1
        assert any("timestamp" in error for error in result.errors)
        assert any("open" in error for error in result.errors)
        assert any("high" in error for error in result.errors)
        assert any("volume" in error for error in result.errors)
