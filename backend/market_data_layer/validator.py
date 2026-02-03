"""Data validation module for K-line data."""

from typing import List
from market_data_layer.models import KlineData, ValidationResult
from market_data_layer.exceptions import ValidationError


class KlineDataValidator:
    """Validator for K-line data.
    
    This validator checks the integrity and validity of K-line data according to
    the following rules:
    - high >= low >= 0
    - open, high, low, close are in reasonable price ranges (> 0 and < max_price)
    - volume >= 0
    - timestamp is a valid Unix timestamp
    """
    
    # Maximum reasonable price for any asset (in USDT)
    MAX_PRICE = 1_000_000.0
    
    # Minimum reasonable price (must be positive)
    MIN_PRICE = 0.0
    
    def validate(self, data: KlineData) -> ValidationResult:
        """Validate a single K-line data object.
        
        Args:
            data: The K-line data to validate
            
        Returns:
            ValidationResult containing validation status and any error messages
        """
        errors = []
        
        # Validate timestamp
        if not self._is_valid_timestamp(data.timestamp):
            errors.append("timestamp must be a valid Unix timestamp (milliseconds)")
        
        # Validate price relationship: high >= low >= 0
        if data.low < 0:
            errors.append("low price must be >= 0")
        
        if data.high < data.low:
            errors.append("high price must be >= low price")
        
        # Validate price ranges for open, high, low, close
        for price_name, price_value in [
            ("open", data.open),
            ("high", data.high),
            ("low", data.low),
            ("close", data.close),
        ]:
            if price_value < self.MIN_PRICE:
                errors.append(f"{price_name} price must be >= {self.MIN_PRICE}")
            
            if price_value > self.MAX_PRICE:
                errors.append(f"{price_name} price must be <= {self.MAX_PRICE}")
        
        # Validate volume
        if data.volume < 0:
            errors.append("volume must be >= 0")
        
        return ValidationResult(
            isValid=len(errors) == 0,
            errors=errors,
        )
    
    def validate_batch(self, data: List[KlineData]) -> List[ValidationResult]:
        """Validate a batch of K-line data objects.
        
        Args:
            data: List of K-line data to validate
            
        Returns:
            List of ValidationResult objects, one for each input data
        """
        return [self.validate(kline) for kline in data]
    
    @staticmethod
    def _is_valid_timestamp(timestamp: int) -> bool:
        """Check if a timestamp is valid.
        
        A valid timestamp should be:
        - A positive integer
        - In milliseconds (between 1970 and year 2286)
        
        Args:
            timestamp: The timestamp to validate
            
        Returns:
            True if the timestamp is valid, False otherwise
        """
        # Timestamp should be positive
        if timestamp < 0:
            return False
        
        # Timestamp should be in milliseconds (reasonable range)
        # Min: 1970-01-01 (0)
        # Max: 2286-11-20 (9999999999999)
        if timestamp > 9999999999999:
            return False
        
        return True
