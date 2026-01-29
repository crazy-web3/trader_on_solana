"""Data models for wallet authentication."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WalletUser:
    """Represents a wallet user."""
    
    public_key: str
    signature: str
    message: str
    timestamp: datetime
    is_whitelisted: bool = False
    nickname: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "public_key": self.public_key,
            "signature": self.signature,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "is_whitelisted": self.is_whitelisted,
            "nickname": self.nickname
        }


@dataclass
class AuthToken:
    """Represents an authentication token."""
    
    token: str
    public_key: str
    expires_at: datetime
    created_at: datetime
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "token": self.token,
            "public_key": self.public_key,
            "expires_at": self.expires_at.isoformat(),
            "created_at": self.created_at.isoformat()
        }