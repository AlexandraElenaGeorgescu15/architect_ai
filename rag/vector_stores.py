"""
Vector Store Abstraction Layer
Supports multiple vector database backends
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os

class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    def search(self, query_vector: List[float], k: int = 10, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str] = None):
        """Insert or update vectors"""
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]):
        """Delete vectors by IDs"""
        pass
    
    @abstractmethod
    def get(self, ids: List[str] = None, limit: int = None) -> Dict[str, Any]:
        """Get vectors by IDs or all vectors"""
        pass


class ChromaStore(VectorStore):
    """ChromaDB vector store implementation"""
    
    def __init__(self, collection_name: str = "repo", persist_path: str = "rag/index"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_path)
        self.collection = self.client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def search(self, query_vector: List[float], k: int = 10, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            where=filter
        )
        
        # Format results
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted
    
    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str] = None):
        documents = [m.get('content', '') for m in metadata]
        
        self.collection.upsert(
            ids=ids or [str(i) for i in range(len(vectors))],
            embeddings=vectors,
            documents=documents,
            metadatas=metadata
        )
    
    def delete(self, ids: List[str]):
        self.collection.delete(ids=ids)
    
    def get(self, ids: List[str] = None, limit: int = None) -> Dict[str, Any]:
        return self.collection.get(ids=ids, limit=limit)


class PineconeStore(VectorStore):
    """Pinecone vector store implementation"""
    
    def __init__(self, index_name: str, api_key: str = None, environment: str = None):
        try:
            import pinecone
            
            api_key = api_key or os.getenv('PINECONE_API_KEY')
            environment = environment or os.getenv('PINECONE_ENVIRONMENT', 'us-west1-gcp')
            
            pinecone.init(api_key=api_key, environment=environment)
            
            # Create index if it doesn't exist
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    index_name,
                    dimension=384,  # Default for all-MiniLM-L6-v2
                    metric='cosine'
                )
            
            self.index = pinecone.Index(index_name)
            self.available = True
            print(f"[OK] Connected to Pinecone index: {index_name}")
            
        except Exception as e:
            print(f"[WARN] Pinecone not available: {e}")
            self.available = False
    
    def search(self, query_vector: List[float], k: int = 10, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        
        results = self.index.query(
            vector=query_vector,
            top_k=k,
            include_metadata=True,
            filter=filter
        )
        
        return [{
            'id': match.id,
            'content': match.metadata.get('content', ''),
            'metadata': match.metadata,
            'score': match.score
        } for match in results.matches]
    
    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str] = None):
        if not self.available:
            return
        
        ids = ids or [str(i) for i in range(len(vectors))]
        
        # Pinecone expects tuples of (id, vector, metadata)
        vectors_to_upsert = [
            (id, vector, meta)
            for id, vector, meta in zip(ids, vectors, metadata)
        ]
        
        # Batch upsert
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i+batch_size]
            self.index.upsert(vectors=batch)
    
    def delete(self, ids: List[str]):
        if not self.available:
            return
        
        self.index.delete(ids=ids)
    
    def get(self, ids: List[str] = None, limit: int = None) -> Dict[str, Any]:
        if not self.available:
            return {}
        
        # Pinecone doesn't have a direct "get all" method
        # This is a simplified implementation
        if ids:
            results = self.index.fetch(ids=ids)
            return {'ids': list(results.vectors.keys()), 'vectors': list(results.vectors.values())}
        
        return {}


class QdrantStore(VectorStore):
    """Qdrant vector store implementation"""
    
    def __init__(self, collection_name: str = "repo", url: str = None, api_key: str = None):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            url = url or os.getenv('QDRANT_URL', 'http://localhost:6333')
            api_key = api_key or os.getenv('QDRANT_API_KEY')
            
            self.client = QdrantClient(url=url, api_key=api_key)
            self.collection_name = collection_name
            
            # Create collection if it doesn't exist
            try:
                self.client.get_collection(collection_name)
            except Exception:  # Qdrant throws generic Exception when collection doesn't exist
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
            
            self.available = True
            print(f"[OK] Connected to Qdrant collection: {collection_name}")
            
        except Exception as e:
            print(f"[WARN] Qdrant not available: {e}")
            self.available = False
    
    def search(self, query_vector: List[float], k: int = 10, filter: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if not self.available:
            return []
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=k,
            query_filter=filter
        )
        
        return [{
            'id': str(result.id),
            'content': result.payload.get('content', ''),
            'metadata': result.payload,
            'score': result.score
        } for result in results]
    
    def upsert(self, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str] = None):
        if not self.available:
            return
        
        from qdrant_client.models import PointStruct
        
        ids = ids or list(range(len(vectors)))
        
        points = [
            PointStruct(id=id, vector=vector, payload=meta)
            for id, vector, meta in zip(ids, vectors, metadata)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def delete(self, ids: List[str]):
        if not self.available:
            return
        
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=ids
        )
    
    def get(self, ids: List[str] = None, limit: int = None) -> Dict[str, Any]:
        if not self.available:
            return {}
        
        # Simplified implementation
        if ids:
            results = self.client.retrieve(
                collection_name=self.collection_name,
                ids=ids
            )
            return {'points': results}
        
        return {}


def create_vector_store(store_type: str = "chroma", **kwargs) -> VectorStore:
    """
    Factory function to create vector store instances
    
    Args:
        store_type: Type of vector store ("chroma", "pinecone", "qdrant")
        **kwargs: Additional arguments for the specific store
    
    Returns:
        VectorStore instance
    """
    store_type = store_type.lower()
    
    if store_type == "chroma":
        return ChromaStore(**kwargs)
    elif store_type == "pinecone":
        return PineconeStore(**kwargs)
    elif store_type == "qdrant":
        return QdrantStore(**kwargs)
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")

