"""
Global API Key Manager
Ensures API keys persist across all agent instances with encrypted storage
"""

import os
import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)

class APIKeyManager:
    """Singleton to manage API keys globally with persistent encrypted storage"""
    _instance = None
    _keys: Dict[str, str] = {}
    _secrets_manager = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APIKeyManager, cls).__new__(cls)
            # Initialize secrets manager and load keys on startup
            try:
                from .secrets_manager import get_secrets_manager
                cls._instance._secrets_manager = get_secrets_manager()
                # Load keys from disk
                saved_keys = cls._instance._secrets_manager.load_keys()
                cls._instance._keys.update(saved_keys)
                # Also set in environment for compatibility
                for provider, key in saved_keys.items():
                    if key:
                        if provider == 'groq':
                            os.environ['GROQ_API_KEY'] = key
                        elif provider == 'openai':
                            os.environ['OPENAI_API_KEY'] = key
                        elif provider == 'gemini':
                            os.environ['GEMINI_API_KEY'] = key
                logger.info(f"Loaded {len(saved_keys)} API keys from secrets store")
            except Exception as e:
                logger.warning(f"Failed to initialize secrets manager: {e}. Keys will only persist in session.")
                cls._instance._secrets_manager = None
        return cls._instance
    
    def set_key(self, provider: str, key: str):
        """Set API key for a provider and save to encrypted storage"""
        self._keys[provider] = key
        
        # Also set in environment for compatibility
        if provider == 'groq':
            os.environ['GROQ_API_KEY'] = key
        elif provider == 'openai':
            os.environ['OPENAI_API_KEY'] = key
        elif provider == 'gemini':
            os.environ['GEMINI_API_KEY'] = key
        
        # Save to encrypted storage
        if self._secrets_manager:
            try:
                self._secrets_manager.set_key(provider, key)
                logger.info(f"Saved API key for {provider} to secrets store")
            except Exception as e:
                logger.warning(f"Failed to save API key to secrets store: {e}")
    
    def get_key(self, provider: str) -> Optional[str]:
        """Get API key for a provider"""
        # Check internal storage first
        if provider in self._keys and self._keys[provider]:
            return self._keys[provider]
        
        # Try loading from secrets store if not in memory
        if self._secrets_manager:
            try:
                saved_key = self._secrets_manager.get_key(provider)
                if saved_key:
                    self._keys[provider] = saved_key
                    # Also set in environment
                    if provider == 'groq':
                        os.environ['GROQ_API_KEY'] = saved_key
                    elif provider == 'openai':
                        os.environ['OPENAI_API_KEY'] = saved_key
                    elif provider == 'gemini':
                        os.environ['GEMINI_API_KEY'] = saved_key
                    return saved_key
            except Exception as e:
                logger.warning(f"Failed to load key from secrets store: {e}")
        
        # Fall back to environment variables
        if provider == 'groq':
            return os.getenv('GROQ_API_KEY')
        elif provider == 'openai':
            return os.getenv('OPENAI_API_KEY')
        elif provider == 'gemini':
            return os.getenv('GEMINI_API_KEY')

        logger.warning("API key not found for provider '%s'", provider)
        return None
    
    def get_all_keys(self) -> Dict[str, str]:
        """Get all stored keys"""
        return {
            'groq': self.get_key('groq'),
            'openai': self.get_key('openai'),
            'gemini': self.get_key('gemini')
        }
    
    def clear_keys(self):
        """Clear all keys from memory and disk"""
        self._keys.clear()
        if self._secrets_manager:
            try:
                self._secrets_manager.clear_keys()
            except Exception as e:
                logger.warning(f"Failed to clear keys from secrets store: {e}")


# Global instance
api_key_manager = APIKeyManager()

