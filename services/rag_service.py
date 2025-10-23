"""
RAG Service - Dedicated service for RAG operations
Handles vector search, context retrieval, and caching
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from rag.retrieve import vector_search, bm25_search, merge_rerank
from rag.utils import chroma_client, BM25Index
from rag.filters import load_cfg
from rag.cache import get_cache
from monitoring import counter, timer

app = FastAPI(title="RAG Service", version="1.0.0")

# Initialize RAG system
cfg = load_cfg()
client = chroma_client(cfg["store"]["path"])
collection = client.get_or_create_collection("repo", metadata={"hnsw:space":"cosine"})
cache = get_cache(backend="memory")  # Can be upgraded to Redis

class SearchRequest(BaseModel):
    query: str
    k: int = 18
    use_cache: bool = True

class SearchResponse(BaseModel):
    success: bool
    results: List[Dict[str, Any]]
    num_results: int
    from_cache: bool

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Perform hybrid RAG search"""
    with timer('rag_service_search_duration'):
        try:
            # Check cache
            if request.use_cache:
                cached = cache.get_context(request.query)
                if cached:
                    counter('rag_service_cache_hit')
                    return SearchResponse(
                        success=True,
                        results=[{'content': cached}],
                        num_results=1,
                        from_cache=True
                    )
            
            counter('rag_service_cache_miss')
            
            # Load documents
            res = collection.get(include=["documents","metadatas"], limit=100000)
            docs = res['documents']
            
            # Hybrid search
            vec_hits = vector_search(collection, request.query, cfg["hybrid"]["k_vector"])
            bm25 = BM25Index(docs)
            bm25_hits = bm25_search(bm25, request.query, cfg["hybrid"]["k_bm25"])
            hits = merge_rerank(vec_hits, bm25_hits, request.k)
            
            # Format results
            results = [
                {
                    'content': doc['content'],
                    'metadata': doc['meta'],
                    'score': score
                }
                for doc, score in hits
            ]
            
            # Cache results
            if request.use_cache:
                context = '\n---\n'.join([r['content'] for r in results])
                cache.set_context(request.query, context)
            
            counter('rag_service_search_total', status='success')
            
            return SearchResponse(
                success=True,
                results=results,
                num_results=len(results),
                from_cache=False
            )
            
        except Exception as e:
            counter('rag_service_search_total', status='error')
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rag"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

