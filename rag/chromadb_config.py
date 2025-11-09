"""
Global ChromaDB Client Configuration
Provides a singleton ChromaDB client to avoid telemetry spam and reduce initialization overhead
"""

import chromadb
from typing import Tuple, Optional
import os

# Global client instance to reuse across all agent instances
_global_chroma_client: Optional[chromadb.PersistentClient] = None
_global_collections: dict = {}


def get_global_chroma_client(persist_path: str, collection_name: str) -> Tuple[chromadb.PersistentClient, chromadb.Collection]:
    """
    Get or create a global ChromaDB client and collection.
    
    This singleton pattern prevents:
    - Multiple telemetry initialization messages
    - Redundant client connections
    - Collection recreation overhead
    
    Args:
        persist_path: Path to ChromaDB persistence directory
        collection_name: Name of the collection to get/create
        
    Returns:
        Tuple of (client, collection)
    """
    global _global_chroma_client, _global_collections
    
    # Create client if it doesn't exist
    if _global_chroma_client is None:
        # Disable telemetry to reduce spam
        os.environ["ANONYMIZED_TELEMETRY"] = "False"
        
        _global_chroma_client = chromadb.PersistentClient(
            path=persist_path,
            settings=chromadb.Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        print(f"[CHROMA] Global client initialized at {persist_path}")
    
    # Get or create collection
    collection_key = f"{persist_path}::{collection_name}"
    
    if collection_key not in _global_collections:
        _global_collections[collection_key] = _global_chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"[CHROMA] Collection '{collection_name}' loaded")
    
    return _global_chroma_client, _global_collections[collection_key]


def reset_global_client():
    """
    Reset the global client (useful for testing or after errors).
    """
    global _global_chroma_client, _global_collections
    _global_chroma_client = None
    _global_collections = {}
    print("[CHROMA] Global client reset")
