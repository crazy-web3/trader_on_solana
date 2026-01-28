"""Tests for custom exceptions."""

import pytest
from market_data_layer.exceptions import (
    MarketDataLayerException,
    DataSourceError,
    ValidationError,
    ParameterError,
    TimeoutError,
    CacheError,
)


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""
    
    def test_data_source_error_is_market_data_layer_exception(self):
        """Test that DataSourceError is a subclass of MarketDataLayerException."""
        assert issubclass(DataSourceError, MarketDataLayerException)
    
    def test_validation_error_is_market_data_layer_exception(self):
        """Test that ValidationError is a subclass of MarketDataLayerException."""
        assert issubclass(ValidationError, MarketDataLayerException)
    
    def test_parameter_error_is_market_data_layer_exception(self):
        """Test that ParameterError is a subclass of MarketDataLayerException."""
        assert issubclass(ParameterError, MarketDataLayerException)
    
    def test_timeout_error_is_market_data_layer_exception(self):
        """Test that TimeoutError is a subclass of MarketDataLayerException."""
        assert issubclass(TimeoutError, MarketDataLayerException)
    
    def test_cache_error_is_market_data_layer_exception(self):
        """Test that CacheError is a subclass of MarketDataLayerException."""
        assert issubclass(CacheError, MarketDataLayerException)


class TestExceptionRaising:
    """Tests for raising exceptions."""
    
    def test_raise_data_source_error(self):
        """Test raising DataSourceError."""
        with pytest.raises(DataSourceError):
            raise DataSourceError("Connection failed")
    
    def test_raise_validation_error(self):
        """Test raising ValidationError."""
        with pytest.raises(ValidationError):
            raise ValidationError("Data validation failed")
    
    def test_raise_parameter_error(self):
        """Test raising ParameterError."""
        with pytest.raises(ParameterError):
            raise ParameterError("Invalid parameter")
    
    def test_raise_timeout_error(self):
        """Test raising TimeoutError."""
        with pytest.raises(TimeoutError):
            raise TimeoutError("Request timeout")
    
    def test_raise_cache_error(self):
        """Test raising CacheError."""
        with pytest.raises(CacheError):
            raise CacheError("Cache operation failed")
    
    def test_raise_market_data_layer_exception(self):
        """Test raising base MarketDataLayerException."""
        with pytest.raises(MarketDataLayerException):
            raise MarketDataLayerException("Generic error")


class TestExceptionMessages:
    """Tests for exception messages."""
    
    def test_exception_message_preservation(self):
        """Test that exception messages are preserved."""
        message = "Test error message"
        
        try:
            raise DataSourceError(message)
        except DataSourceError as e:
            assert str(e) == message
    
    def test_exception_with_multiple_arguments(self):
        """Test exception with multiple arguments."""
        try:
            raise ValidationError("Validation failed", "high < low")
        except ValidationError as e:
            assert "Validation failed" in str(e)


class TestExceptionCatching:
    """Tests for catching exceptions."""
    
    def test_catch_specific_exception(self):
        """Test catching a specific exception type."""
        caught = False
        try:
            raise DataSourceError("Connection failed")
        except DataSourceError:
            caught = True
        
        assert caught is True
    
    def test_catch_base_exception(self):
        """Test catching base MarketDataLayerException."""
        caught = False
        try:
            raise ValidationError("Validation failed")
        except MarketDataLayerException:
            caught = True
        
        assert caught is True
    
    def test_catch_multiple_exception_types(self):
        """Test catching multiple exception types."""
        caught_data_source = False
        caught_validation = False
        
        try:
            raise DataSourceError("Connection failed")
        except (DataSourceError, ValidationError):
            caught_data_source = True
        
        try:
            raise ValidationError("Validation failed")
        except (DataSourceError, ValidationError):
            caught_validation = True
        
        assert caught_data_source is True
        assert caught_validation is True
