"""Custom exceptions for backtest engine."""


class BacktestException(Exception):
    """Base exception for backtest engine."""
    pass


class InvalidConfigError(BacktestException):
    """Raised when backtest configuration is invalid."""
    pass


class DataError(BacktestException):
    """Raised when there are data-related errors."""
    pass
