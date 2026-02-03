"""Data models for the market data layer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class TimeInterval(str, Enum):
    """Supported time intervals for K-line data."""
    
    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"


@dataclass
class KlineData:
    """K-line data model containing OHLCV information.
    
    Attributes:
        timestamp: Unix timestamp in milliseconds representing the start time of the K-line
        open: Opening price
        high: Highest price
        low: Lowest price
        close: Closing price
        volume: Trading volume
    """
    
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class CacheEntry:
    """Cache entry model for storing K-line data with metadata.
    
    Attributes:
        data: List of K-line data
        createdAt: Timestamp when the cache entry was created (milliseconds)
        ttl: Time to live in milliseconds
        accessCount: Number of times this cache entry has been accessed
        lastAccessTime: Timestamp of the last access (milliseconds)
    """
    
    data: List[KlineData]
    createdAt: int
    ttl: int
    accessCount: int = 0
    lastAccessTime: int = field(default_factory=lambda: 0)


@dataclass
class ValidationResult:
    """Result of data validation.
    
    Attributes:
        isValid: Whether the data passed validation
        errors: List of error messages if validation failed
    """
    
    isValid: bool
    errors: List[str] = field(default_factory=list)
