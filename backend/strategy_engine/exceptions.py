"""Custom exceptions for strategy engine."""


class StrategyException(Exception):
    """Base exception for strategy engine."""
    pass


class InvalidParameterError(StrategyException):
    """Raised when strategy parameters are invalid."""
    pass


class InsufficientFundsError(StrategyException):
    """Raised when there are insufficient funds for trading."""
    pass


class ExecutionError(StrategyException):
    """Raised when strategy execution fails."""
    pass
