"""Exceptions for wallet authentication module."""


class WalletAuthError(Exception):
    """Base exception for wallet authentication errors."""
    pass


class InvalidSignatureError(WalletAuthError):
    """Raised when wallet signature verification fails."""
    pass


class WhitelistError(WalletAuthError):
    """Raised when wallet is not in whitelist."""
    pass


class TokenExpiredError(WalletAuthError):
    """Raised when authentication token is expired."""
    pass


class InvalidTokenError(WalletAuthError):
    """Raised when authentication token is invalid."""
    pass