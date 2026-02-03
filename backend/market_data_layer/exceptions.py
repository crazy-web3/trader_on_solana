"""Custom exception classes for the market data layer."""


class MarketDataLayerException(Exception):
    """Base exception class for all market data layer exceptions."""
    
    pass


class DataSourceError(MarketDataLayerException):
    """Exception raised when data source connection or request fails.
    
    This exception is raised when:
    - Connection to the data source fails
    - Network request fails
    - Data source returns an error response
    """
    
    pass


class ValidationError(MarketDataLayerException):
    """Exception raised when data validation fails.
    
    This exception is raised when:
    - K-line data fails validation checks
    - Data integrity checks fail
    - Invalid data is received from the data source
    """
    
    pass


class ParameterError(MarketDataLayerException):
    """Exception raised when request parameters are invalid.
    
    This exception is raised when:
    - Unsupported symbol is requested
    - Unsupported time interval is requested
    - Invalid time range is provided
    - Required parameters are missing
    """
    
    pass


class TimeoutError(MarketDataLayerException):
    """Exception raised when a request times out.
    
    This exception is raised when:
    - Data source request exceeds the configured timeout
    - Network operation takes too long
    """
    
    pass


class CacheError(MarketDataLayerException):
    """Exception raised when cache operations fail.
    
    This exception is raised when:
    - Cache storage fails
    - Cache retrieval fails
    - Cache corruption is detected
    """
    
    pass
