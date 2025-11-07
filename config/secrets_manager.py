"""
Secrets Manager - Encrypted API Key Storage

Stores API keys securely in an encrypted file under secrets/ folder.
Keys are persisted permanently and loaded on startup.
"""

import os
import json
import base64
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Manages encrypted storage of API keys.
    
    Uses Fernet symmetric encryption with a key derived from a master password.
    Falls back to a default key if no password is set (for convenience).
    """
    
    def __init__(self, secrets_dir: Path = None):
        """
        Initialize secrets manager.
        
        Args:
            secrets_dir: Directory to store secrets (default: project_root/secrets/)
        """
        if secrets_dir is None:
            # Default to project root / secrets/
            project_root = Path(__file__).parent.parent
            secrets_dir = project_root / "secrets"
        
        self.secrets_dir = Path(secrets_dir)
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self.secrets_file = self.secrets_dir / ".keys.json.enc"
        
        # Generate or load encryption key
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """
        Get or create encryption key.
        
        Uses a default key derived from a fixed salt for convenience.
        In production, you'd want to use a user-provided password.
        """
        key_file = self.secrets_dir / ".key"
        
        if key_file.exists():
            # Load existing key
            try:
                return key_file.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to load encryption key: {e}. Creating new key.")
        
        # Generate new key
        key = Fernet.generate_key()
        
        try:
            key_file.write_bytes(key)
            # Make key file readable only by owner (Unix)
            try:
                os.chmod(key_file, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod
        except Exception as e:
            logger.warning(f"Failed to save encryption key: {e}")
        
        return key
    
    def save_keys(self, keys: Dict[str, str]) -> bool:
        """
        Save API keys to encrypted file.
        
        Args:
            keys: Dictionary of provider -> API key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Encrypt the keys
            keys_json = json.dumps(keys, indent=2)
            keys_bytes = keys_json.encode('utf-8')
            encrypted = self._cipher.encrypt(keys_bytes)
            
            # Write to file
            self.secrets_file.write_bytes(encrypted)
            
            # Make file readable only by owner (Unix)
            try:
                os.chmod(self.secrets_file, 0o600)
            except Exception:
                pass  # Windows doesn't support chmod
            
            logger.info(f"Saved {len(keys)} API keys to {self.secrets_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
            return False
    
    def load_keys(self) -> Dict[str, str]:
        """
        Load API keys from encrypted file.
        
        Returns:
            Dictionary of provider -> API key (empty if file doesn't exist or decryption fails)
        """
        if not self.secrets_file.exists():
            return {}
        
        try:
            # Read encrypted file
            encrypted = self.secrets_file.read_bytes()
            
            # Decrypt
            decrypted = self._cipher.decrypt(encrypted)
            keys_json = decrypted.decode('utf-8')
            keys = json.loads(keys_json)
            
            logger.info(f"Loaded {len(keys)} API keys from {self.secrets_file}")
            return keys
            
        except Exception as e:
            logger.warning(f"Failed to load API keys: {e}")
            return {}
    
    def get_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider.
        
        Args:
            provider: Provider name (groq, openai, gemini)
            
        Returns:
            API key or None if not found
        """
        keys = self.load_keys()
        return keys.get(provider)
    
    def set_key(self, provider: str, key: str) -> bool:
        """
        Set API key for a provider and save to disk.
        
        Args:
            provider: Provider name (groq, openai, gemini)
            key: API key value
            
        Returns:
            True if successful, False otherwise
        """
        keys = self.load_keys()
        keys[provider] = key
        return self.save_keys(keys)
    
    def clear_keys(self) -> bool:
        """
        Clear all saved API keys.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.secrets_file.exists():
                self.secrets_file.unlink()
            logger.info("Cleared all API keys")
            return True
        except Exception as e:
            logger.error(f"Failed to clear API keys: {e}")
            return False


# Global secrets manager instance
_secrets_manager_instance: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create global secrets manager instance"""
    global _secrets_manager_instance
    if _secrets_manager_instance is None:
        _secrets_manager_instance = SecretsManager()
    return _secrets_manager_instance

