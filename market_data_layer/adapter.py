"""Data source adapter module for fetching K-line data."""

from abc import ABC, abstractmethod
from typing import List, Optional, Union
import requests
import time
from datetime import datetime, timedelta
from market_data_layer.models import KlineData, TimeInterval
from market_data_layer.exceptions import (
    DataSourceError,
    ParameterError,
    TimeoutError,
)


class DataSourceAdapter(ABC):
    """Abstract base class for data source adapters.
    
    This class defines the interface for fetching K-line data from various
    data sources (APIs, databases, etc.).
    """
    
    # Supported symbols
    SUPPORTED_SYMBOLS = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
    
    # Supported intervals
    SUPPORTED_INTERVALS = [
        TimeInterval.ONE_MINUTE.value,
        TimeInterval.FIVE_MINUTES.value,
        TimeInterval.FIFTEEN_MINUTES.value,
        TimeInterval.ONE_HOUR.value,
        TimeInterval.FOUR_HOURS.value,
        TimeInterval.ONE_DAY.value,
        TimeInterval.ONE_WEEK.value,
    ]
    
    @abstractmethod
    def fetch_kline_data(
        self,
        symbol: str,
        interval: Union[str, 'Timeframe'],  # Support both str and Timeframe
        start_time: int,
        end_time: int,
    ) -> List[KlineData]:
        """Fetch K-line data from the data source.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            interval: Time interval (e.g., "1h") or Timeframe enum
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of KlineData objects
            
        Raises:
            ParameterError: If parameters are invalid
            DataSourceError: If data source request fails
            TimeoutError: If request times out
        """
        pass
    
    def _normalize_interval(self, interval: Union[str, 'Timeframe']) -> str:
        """Normalize interval to string format.
        
        Args:
            interval: Time interval as string or Timeframe enum
            
        Returns:
            Interval as string (e.g., "1h")
        """
        # Import here to avoid circular dependency
        try:
            from backtest_engine.models import Timeframe
            if isinstance(interval, Timeframe):
                return interval.value
        except ImportError:
            pass
        
        return str(interval)
    
    def validate_parameters(
        self,
        symbol: str,
        interval: Union[str, 'Timeframe'],
        start_time: int,
        end_time: int,
    ) -> None:
        """Validate request parameters.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (string or Timeframe enum)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Raises:
            ParameterError: If any parameter is invalid
        """
        # Normalize interval to string
        interval_str = self._normalize_interval(interval)
        
        # Validate symbol
        if symbol not in self.SUPPORTED_SYMBOLS:
            raise ParameterError(
                f"Unsupported symbol: {symbol}. "
                f"Supported symbols: {', '.join(self.SUPPORTED_SYMBOLS)}"
            )
        
        # Validate interval
        if interval_str not in self.SUPPORTED_INTERVALS:
            raise ParameterError(
                f"Unsupported interval: {interval_str}. "
                f"Supported intervals: {', '.join(self.SUPPORTED_INTERVALS)}"
            )
        
        # Validate time range
        if start_time < 0:
            raise ParameterError("start_time must be >= 0")
        
        if end_time < 0:
            raise ParameterError("end_time must be >= 0")
        
        if start_time > end_time:
            raise ParameterError("start_time must be <= end_time")
    
    @classmethod
    def get_supported_symbols(cls) -> List[str]:
        """Get list of supported symbols.
        
        Returns:
            List of supported trading pair symbols
        """
        return cls.SUPPORTED_SYMBOLS.copy()
    
    @classmethod
    def get_supported_intervals(cls) -> List[str]:
        """Get list of supported intervals.
        
        Returns:
            List of supported time intervals
        """
        return cls.SUPPORTED_INTERVALS.copy()


class MockDataSourceAdapter(DataSourceAdapter):
    """Mock data source adapter for testing.
    
    This adapter generates mock K-line data for testing purposes.
    """
    
    def fetch_kline_data(
        self,
        symbol: str,
        interval: Union[str, 'Timeframe'],
        start_time: int,
        end_time: int,
    ) -> List[KlineData]:
        """Fetch mock K-line data.
        
        Args:
            symbol: Trading pair symbol
            interval: Time interval (string or Timeframe enum)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of mock KlineData objects
            
        Raises:
            ParameterError: If parameters are invalid
        """
        # Validate parameters
        self.validate_parameters(symbol, interval, start_time, end_time)
        
        # Normalize interval to string
        interval_str = self._normalize_interval(interval)
        
        # Generate mock data
        klines = []
        
        # Determine interval in milliseconds
        interval_ms = self._get_interval_ms(interval_str)
        
        # Generate K-line data for each interval
        current_time = start_time
        base_price = 100.0  # Base price for mock data
        
        while current_time < end_time:
            # Generate mock OHLCV data
            open_price = base_price + (current_time % 10)
            high_price = open_price + 5.0
            low_price = open_price - 3.0
            close_price = open_price + 2.0
            volume = 1000.0 + (current_time % 500)
            
            kline = KlineData(
                timestamp=current_time,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
            
            klines.append(kline)
            current_time += interval_ms
        
        return klines
    
    @staticmethod
    def _get_interval_ms(interval: str) -> int:
        """Convert interval string to milliseconds.
        
        Args:
            interval: Interval string (e.g., "1h", "5m")
            
        Returns:
            Interval in milliseconds
        """
        interval_map = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
            "1w": 7 * 24 * 60 * 60 * 1000,
        }
        
        return interval_map.get(interval, 60 * 1000)  # Default to 1 minute


class BinanceDataSourceAdapter(DataSourceAdapter):
    """Binance API data source adapter for fetching real K-line data.
    
    This adapter fetches real K-line data from Binance public API.
    No API key required for public endpoints.
    """
    
    BASE_URL = "https://api.binance.com/api/v3"
    
    # Map our symbols to Binance symbols
    SYMBOL_MAP = {
        "BTC/USDT": "BTCUSDT",
        "ETH/USDT": "ETHUSDT",
        "BNB/USDT": "BNBUSDT",
        "SOL/USDT": "SOLUSDT",
    }
    
    # Map our intervals to Binance intervals
    INTERVAL_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
        "1w": "1w",
    }
    
    def __init__(self, timeout: int = 10):
        """Initialize the Binance adapter.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
    
    def fetch_kline_data(
        self,
        symbol: str,
        interval: Union[str, 'Timeframe'],
        start_time: int,
        end_time: int,
    ) -> List[KlineData]:
        """Fetch K-line data from Binance API.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            interval: Time interval (e.g., "1h") or Timeframe enum
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of KlineData objects
            
        Raises:
            ParameterError: If parameters are invalid
            DataSourceError: If API request fails
            TimeoutError: If request times out
        """
        # Validate parameters
        self.validate_parameters(symbol, interval, start_time, end_time)
        
        # Normalize interval to string
        interval_str = self._normalize_interval(interval)
        
        try:
            # Convert symbol and interval
            binance_symbol = self.SYMBOL_MAP.get(symbol)
            binance_interval = self.INTERVAL_MAP.get(interval_str)
            
            if not binance_symbol or not binance_interval:
                raise ParameterError(f"Unsupported symbol or interval: {symbol} {interval_str}")
            
            # Fetch data from Binance
            klines = []
            current_start = start_time
            
            # Binance API returns max 1000 klines per request
            while current_start < end_time:
                params = {
                    "symbol": binance_symbol,
                    "interval": binance_interval,
                    "startTime": current_start,
                    "endTime": end_time,
                    "limit": 1000,
                }
                
                response = requests.get(
                    f"{self.BASE_URL}/klines",
                    params=params,
                    timeout=self.timeout
                )
                
                if response.status_code != 200:
                    raise DataSourceError(
                        f"Binance API error: {response.status_code} - {response.text}"
                    )
                
                data = response.json()
                
                if not data:
                    break
                
                # Parse kline data
                for kline in data:
                    kline_obj = KlineData(
                        timestamp=int(kline[0]),
                        open=float(kline[1]),
                        high=float(kline[2]),
                        low=float(kline[3]),
                        close=float(kline[4]),
                        volume=float(kline[7]),  # Quote asset volume
                    )
                    klines.append(kline_obj)
                
                # Update start time for next request
                if len(data) < 1000:
                    break
                
                current_start = int(data[-1][0]) + self._get_interval_ms(interval_str)
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
            
            return klines
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Binance API request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise DataSourceError(f"Binance API request failed: {str(e)}")
        except (ValueError, KeyError, IndexError) as e:
            raise DataSourceError(f"Failed to parse Binance API response: {str(e)}")
    
    @staticmethod
    def _get_interval_ms(interval: str) -> int:
        """Convert interval string to milliseconds.
        
        Args:
            interval: Interval string (e.g., "1h", "5m")
            
        Returns:
            Interval in milliseconds
        """
        interval_map = {
            "1m": 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
            "1w": 7 * 24 * 60 * 60 * 1000,
        }
        
        return interval_map.get(interval, 60 * 1000)
