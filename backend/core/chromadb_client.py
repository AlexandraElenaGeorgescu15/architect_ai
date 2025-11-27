"""
Shared ChromaDB Client Factory
Ensures all services use the same ChromaDB client with consistent settings.
"""

import os
from pathlib import Path
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import logging

logger = logging.getLogger(__name__)

# Global client instance
_shared_client: Optional[chromadb.PersistentClient] = None
_client_path: Optional[str] = None


def get_shared_chromadb_client(index_path: str) -> chromadb.PersistentClient:
    """
    Get or create a shared ChromaDB client with consistent settings.
    
    This ensures all services (RAGIngester, RAGRetriever, etc.) use the same
    client instance, preventing "different settings" errors.
    
    Args:
        index_path: Path to ChromaDB index directory
        
    Returns:
        Shared ChromaDB PersistentClient instance
    """
    global _shared_client, _client_path
    
    # Disable telemetry before any ChromaDB operations
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "True")
    
    # Normalize path
    normalized_path = str(Path(index_path).resolve())
    
    # If client exists and path matches, return it
    if _shared_client is not None and _client_path == normalized_path:
        return _shared_client
    
    # If client exists but path is different, log warning
    if _shared_client is not None and _client_path != normalized_path:
        logger.warning(
            f"ChromaDB client already exists for {_client_path}, "
            f"but requested {normalized_path}. Using existing client."
        )
        return _shared_client
    
    # Create new client with consistent settings
    # These settings MUST match across all services
    settings = ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=True
    )
    
    try:
        _shared_client = chromadb.PersistentClient(
            path=normalized_path,
            settings=settings
        )
        _client_path = normalized_path
        logger.debug(f"Created shared ChromaDB client for {normalized_path}")
        return _shared_client
    except ValueError as e:
        # If client already exists with different settings, try to reset
        if "already exists" in str(e) and "different settings" in str(e):
            logger.warning(
                f"ChromaDB client conflict detected: {e}. "
                "This may occur during hot reload. The existing client will be reused."
            )
            # Try to get existing client (may fail, but worth trying)
            try:
                _shared_client = chromadb.PersistentClient(
                    path=normalized_path,
                    settings=settings
                )
                _client_path = normalized_path
                return _shared_client
            except Exception:
                # If that fails, raise the original error
                raise e
        else:
            raise


def reset_shared_client():
    """Reset the shared client (useful for testing or after errors)."""
    global _shared_client, _client_path
    _shared_client = None
    _client_path = None
    logger.debug("Reset shared ChromaDB client")

