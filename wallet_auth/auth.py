"""Wallet authentication logic."""

import base64
import hashlib
import secrets
import base58
from datetime import datetime, timedelta
from typing import Optional, Dict
import nacl.signing
import nacl.encoding
from .models import WalletUser, AuthToken
from .whitelist import WhitelistManager
from .exceptions import (
    InvalidSignatureError,
    WhitelistError,
    TokenExpiredError,
    InvalidTokenError
)


class WalletAuth:
    """Handles Solana wallet authentication."""
    
    def __init__(self, whitelist_manager: WhitelistManager):
        """Initialize wallet authentication.
        
        Args:
            whitelist_manager: Whitelist manager instance
        """
        self.whitelist_manager = whitelist_manager
        self._active_tokens: Dict[str, AuthToken] = {}
        self.token_expiry_hours = 24  # Token expires in 24 hours
    
    def generate_challenge_message(self, public_key: str) -> str:
        """Generate challenge message for wallet signing.
        
        Args:
            public_key: Wallet public key
            
        Returns:
            Challenge message to be signed
        """
        timestamp = datetime.now().isoformat()
        nonce = secrets.token_hex(16)
        
        message = f"Sign this message to authenticate with Trader on Solana\n"
        message += f"Wallet: {public_key}\n"
        message += f"Timestamp: {timestamp}\n"
        message += f"Nonce: {nonce}"
        
        return message
    
    def verify_signature(self, public_key: str, message: str, signature: str) -> bool:
        """Verify wallet signature.
        
        Args:
            public_key: Wallet public key
            message: Original message that was signed
            signature: Base64 encoded signature
            
        Returns:
            True if signature is valid
            
        Raises:
            InvalidSignatureError: If signature verification fails
        """
        try:
            # Decode public key and signature
            public_key_bytes = base58.b58decode(public_key)
            signature_bytes = base64.b64decode(signature)
            message_bytes = message.encode('utf-8')
            
            # Create verifying key
            verify_key = nacl.signing.VerifyKey(public_key_bytes)
            
            # Verify signature
            verify_key.verify(message_bytes, signature_bytes)
            return True
            
        except Exception as e:
            raise InvalidSignatureError(f"Signature verification failed: {e}")
    
    def authenticate_wallet(self, public_key: str, message: str, signature: str) -> WalletUser:
        """Authenticate wallet with signature.
        
        Args:
            public_key: Wallet public key
            message: Signed message
            signature: Wallet signature
            
        Returns:
            WalletUser instance
            
        Raises:
            InvalidSignatureError: If signature is invalid
            WhitelistError: If wallet is not whitelisted
        """
        # Verify signature
        if not self.verify_signature(public_key, message, signature):
            raise InvalidSignatureError("Invalid wallet signature")
        
        # Check whitelist
        if not self.whitelist_manager.is_whitelisted(public_key):
            raise WhitelistError(f"Wallet {public_key} is not whitelisted")
        
        # Get wallet info
        wallet_info = self.whitelist_manager.get_wallet_info(public_key)
        nickname = wallet_info.get('nickname') if wallet_info else None
        
        # Create wallet user
        wallet_user = WalletUser(
            public_key=public_key,
            signature=signature,
            message=message,
            timestamp=datetime.now(),
            is_whitelisted=True,
            nickname=nickname
        )
        
        return wallet_user
    
    def generate_auth_token(self, public_key: str) -> AuthToken:
        """Generate authentication token for wallet.
        
        Args:
            public_key: Wallet public key
            
        Returns:
            AuthToken instance
        """
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Set expiry time
        expires_at = datetime.now() + timedelta(hours=self.token_expiry_hours)
        
        # Create auth token
        auth_token = AuthToken(
            token=token,
            public_key=public_key,
            expires_at=expires_at,
            created_at=datetime.now()
        )
        
        # Store active token
        self._active_tokens[token] = auth_token
        
        return auth_token
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify authentication token.
        
        Args:
            token: Authentication token
            
        Returns:
            Public key if token is valid, None otherwise
            
        Raises:
            TokenExpiredError: If token is expired
            InvalidTokenError: If token is invalid
        """
        auth_token = self._active_tokens.get(token)
        
        if not auth_token:
            raise InvalidTokenError("Invalid authentication token")
        
        if auth_token.is_expired():
            # Remove expired token
            del self._active_tokens[token]
            raise TokenExpiredError("Authentication token has expired")
        
        return auth_token.public_key
    
    def revoke_token(self, token: str) -> None:
        """Revoke authentication token.
        
        Args:
            token: Authentication token to revoke
        """
        if token in self._active_tokens:
            del self._active_tokens[token]
    
    def revoke_all_tokens(self, public_key: str) -> None:
        """Revoke all tokens for a wallet.
        
        Args:
            public_key: Wallet public key
        """
        tokens_to_remove = [
            token for token, auth_token in self._active_tokens.items()
            if auth_token.public_key == public_key
        ]
        
        for token in tokens_to_remove:
            del self._active_tokens[token]
    
    def cleanup_expired_tokens(self) -> None:
        """Remove expired tokens from memory."""
        expired_tokens = [
            token for token, auth_token in self._active_tokens.items()
            if auth_token.is_expired()
        ]
        
        for token in expired_tokens:
            del self._active_tokens[token]
    
    def get_active_sessions(self) -> Dict[str, AuthToken]:
        """Get all active authentication sessions.
        
        Returns:
            Dictionary of active tokens and their info
        """
        # Clean up expired tokens first
        self.cleanup_expired_tokens()
        return self._active_tokens.copy()