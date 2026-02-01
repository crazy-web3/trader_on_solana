"""Validators for backtest engine configuration and data."""

from typing import Optional
from backtest_engine.models import BacktestConfig, Timeframe
from backtest_engine.slippage_simulator import SlippageConfig
from backtest_engine.order_fill_simulator import OrderFillConfig
from market_data_layer.models import KlineData
import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validator for backtest configuration."""
    
    @staticmethod
    def validate_backtest_config(config: BacktestConfig) -> None:
        """Validate backtest configuration.
        
        Args:
            config: Backtest configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate timeframe
        if not isinstance(config.timeframe, Timeframe):
            raise ValueError(f"Invalid timeframe: {config.timeframe}")
        
        # Validate slippage config if provided
        if config.slippage_config is not None:
            ConfigValidator.validate_slippage_config(config.slippage_config)
    
    @staticmethod
    def validate_slippage_config(config: SlippageConfig) -> None:
        """Validate slippage configuration.
        
        Args:
            config: Slippage configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if config.base_slippage < 0:
            raise ValueError("base_slippage must be non-negative")
        
        if config.max_slippage < config.base_slippage:
            raise ValueError("max_slippage must be >= base_slippage")
        
        if config.size_impact_factor < 0:
            raise ValueError("size_impact_factor must be non-negative")
        
        if config.volatility_impact_factor < 0:
            raise ValueError("volatility_impact_factor must be non-negative")
        
        if config.model not in ['linear', 'sqrt', 'volatility']:
            raise ValueError("model must be 'linear', 'sqrt', or 'volatility'")
    
    @staticmethod
    def validate_order_fill_config(config: OrderFillConfig) -> None:
        """Validate order fill configuration.
        
        Args:
            config: Order fill configuration to validate
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not 0 < config.min_fill_ratio <= 1:
            raise ValueError("min_fill_ratio must be in (0, 1]")


class DataValidator:
    """Validator for market data."""
    
    @staticmethod
    def validate_kline(kline: KlineData) -> bool:
        """Validate a single kline data point.
        
        Args:
            kline: Kline data to validate
            
        Returns:
            True if valid, False otherwise (logs warnings)
        """
        # Check price relationships
        if kline.high < kline.low:
            logger.warning(f"Invalid kline: high < low at {kline.timestamp}")
            return False
        
        if kline.high < kline.open or kline.high < kline.close:
            logger.warning(f"Invalid kline: high < open/close at {kline.timestamp}")
            return False
        
        if kline.low > kline.open or kline.low > kline.close:
            logger.warning(f"Invalid kline: low > open/close at {kline.timestamp}")
            return False
        
        # Check for negative values
        if kline.low < 0:
            logger.warning(f"Invalid kline: negative price at {kline.timestamp}")
            return False
        
        if kline.volume < 0:
            logger.warning(f"Invalid kline: negative volume at {kline.timestamp}")
            return False
        
        return True
    
    @staticmethod
    def validate_kline_sequence(klines: list[KlineData]) -> tuple[list[KlineData], int]:
        """Validate a sequence of klines.
        
        Args:
            klines: List of kline data
            
        Returns:
            Tuple of (valid_klines, invalid_count)
        """
        valid_klines = []
        invalid_count = 0
        
        for kline in klines:
            if DataValidator.validate_kline(kline):
                valid_klines.append(kline)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            logger.warning(f"Found {invalid_count} invalid klines out of {len(klines)}")
        
        return valid_klines, invalid_count
