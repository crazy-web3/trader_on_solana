"""Whitelist management for wallet authentication."""

import json
import os
from typing import List, Dict, Optional
from .exceptions import WhitelistError


class WhitelistManager:
    """Manages wallet whitelist for authentication."""
    
    def __init__(self, whitelist_file: str = "wallet_whitelist.json"):
        """Initialize whitelist manager.
        
        Args:
            whitelist_file: Path to whitelist JSON file
        """
        self.whitelist_file = whitelist_file
        self._whitelist: Dict[str, Dict] = {}
        self._load_whitelist()
    
    def _load_whitelist(self) -> None:
        """Load whitelist from file."""
        try:
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._whitelist = data.get('wallets', {})
            else:
                # Create default whitelist file
                self._create_default_whitelist()
        except Exception as e:
            raise WhitelistError(f"Failed to load whitelist: {e}")
    
    def _save_whitelist(self) -> None:
        """Save whitelist to file."""
        try:
            data = {
                "wallets": self._whitelist,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise WhitelistError(f"Failed to save whitelist: {e}")
    
    def _create_default_whitelist(self) -> None:
        """Create default whitelist file with example entries."""
        from datetime import datetime
        
        default_whitelist = {
            "wallets": {
                # Example wallet addresses (replace with real ones)
                "11111111111111111111111111111112": {
                    "nickname": "Admin Wallet",
                    "role": "admin",
                    "added_at": "2025-01-29T00:00:00",
                    "active": True
                }
            },
            "created_at": datetime.now().isoformat()
        }
        
        with open(self.whitelist_file, 'w', encoding='utf-8') as f:
            json.dump(default_whitelist, f, indent=2, ensure_ascii=False)
        
        self._whitelist = default_whitelist["wallets"]
    
    def is_whitelisted(self, public_key: str) -> bool:
        """Check if wallet is in whitelist.
        
        Args:
            public_key: Wallet public key
            
        Returns:
            True if wallet is whitelisted and active
        """
        wallet_info = self._whitelist.get(public_key)
        if not wallet_info:
            return False
        
        return wallet_info.get('active', True)
    
    def add_wallet(self, public_key: str, nickname: str = None, role: str = "user") -> None:
        """Add wallet to whitelist.
        
        Args:
            public_key: Wallet public key
            nickname: Optional nickname for the wallet
            role: User role (admin, user, etc.)
        """
        from datetime import datetime
        
        self._whitelist[public_key] = {
            "nickname": nickname or f"User_{public_key[:8]}",
            "role": role,
            "added_at": datetime.now().isoformat(),
            "active": True
        }
        self._save_whitelist()
    
    def remove_wallet(self, public_key: str) -> None:
        """Remove wallet from whitelist.
        
        Args:
            public_key: Wallet public key
        """
        if public_key in self._whitelist:
            del self._whitelist[public_key]
            self._save_whitelist()
    
    def deactivate_wallet(self, public_key: str) -> None:
        """Deactivate wallet (keep in list but disable access).
        
        Args:
            public_key: Wallet public key
        """
        if public_key in self._whitelist:
            self._whitelist[public_key]['active'] = False
            self._save_whitelist()
    
    def activate_wallet(self, public_key: str) -> None:
        """Activate wallet.
        
        Args:
            public_key: Wallet public key
        """
        if public_key in self._whitelist:
            self._whitelist[public_key]['active'] = True
            self._save_whitelist()
    
    def get_wallet_info(self, public_key: str) -> Optional[Dict]:
        """Get wallet information.
        
        Args:
            public_key: Wallet public key
            
        Returns:
            Wallet information dict or None if not found
        """
        return self._whitelist.get(public_key)
    
    def list_wallets(self) -> Dict[str, Dict]:
        """Get all wallets in whitelist.
        
        Returns:
            Dictionary of wallet public keys and their info
        """
        return self._whitelist.copy()
    
    def get_active_wallets(self) -> List[str]:
        """Get list of active wallet public keys.
        
        Returns:
            List of active wallet public keys
        """
        return [
            public_key for public_key, info in self._whitelist.items()
            if info.get('active', True)
        ]