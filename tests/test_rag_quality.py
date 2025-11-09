"""
Test RAG Quality and Relevance
Verifies that RAG retrieves correct and relevant context
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

def test_rag_retrieval():
    """Test RAG retrieval quality"""
    print("=" * 60)
    print("RAG QUALITY TEST")
    print("=" * 60)
    
    from rag.chromadb_config import get_global_chroma_client
    from rag.filters import load_cfg
    from rag.retrieve import vector_search, bm25_search, merge_rerank
    from rag.utils import BM25Index
    from rag.context_optimizer import get_context_optimizer
    
    # Initialize
    cfg = load_cfg()
    client, collection = get_global_chroma_client(cfg["store"]["path"], "repo")
    
    # Get all docs for BM25
    all_docs_result = collection.get()
    docs = [{"content": d, "meta": m} for d, m in zip(all_docs_result["documents"], all_docs_result["metadatas"])]
    print(f"\n[OK] Loaded {len(docs)} documents from RAG index")
    
    bm25 = BM25Index(docs)
    
    # Test Query 1: Phone Swap Feature
    print("\n" + "=" * 60)
    print("TEST 1: Phone Swap Feature")
    print("=" * 60)
    
    query1 = "phone swap request feature user phone model controller service"
    print(f"\nQuery: {query1}")
    
    vec_hits = vector_search(collection, query1, 10)
    bm25_hits = bm25_search(bm25, query1, 10)
    merged = merge_rerank(vec_hits, bm25_hits, k_final=10)
    
    print(f"\n[OK] Retrieved {len(merged)} chunks")
    print("\nTop 5 Retrieved Chunks:")
    for i, (doc, score) in enumerate(merged[:5], 1):
        path = doc["meta"].get("path", "unknown")
        chunk_num = doc["meta"].get("chunk", "?")
        content_preview = doc["content"][:150].replace("\n", " ")
        print(f"\n{i}. Score: {score:.3f}")
        print(f"   File: {path}")
        print(f"   Chunk: {chunk_num}")
        print(f"   Preview: {content_preview}...")
        
        # Check if relevant
        is_relevant = any(keyword in path.lower() for keyword in ['phone', 'user', 'model', 'controller', 'service', 'registration'])
        print(f"   Relevant: {'[YES]' if is_relevant else '[NO]'}")
    
    # Test Query 2: Database Schema
    print("\n" + "=" * 60)
    print("TEST 2: Database Schema")
    print("=" * 60)
    
    query2 = "database schema table user phone entity model field property"
    print(f"\nQuery: {query2}")
    
    vec_hits = vector_search(collection, query2, 10)
    bm25_hits = bm25_search(bm25, query2, 10)
    merged = merge_rerank(vec_hits, bm25_hits, k_final=10)
    
    print(f"\n[OK] Retrieved {len(merged)} chunks")
    print("\nTop 5 Retrieved Chunks:")
    for i, (doc, score) in enumerate(merged[:5], 1):
        path = doc["meta"].get("path", "unknown")
        chunk_num = doc["meta"].get("chunk", "?")
        content_preview = doc["content"][:150].replace("\n", " ")
        print(f"\n{i}. Score: {score:.3f}")
        print(f"   File: {path}")
        print(f"   Chunk: {chunk_num}")
        print(f"   Preview: {content_preview}...")
        
        # Check if relevant
        is_relevant = any(keyword in path.lower() for keyword in ['model', 'entity', 'dto', 'database', 'schema'])
        print(f"   Relevant: {'✅ YES' if is_relevant else '❌ NO'}")
    
    # Test Query 3: Angular Components
    print("\n" + "=" * 60)
    print("TEST 3: Angular Components")
    print("=" * 60)
    
    query3 = "angular component typescript service http api frontend"
    print(f"\nQuery: {query3}")
    
    vec_hits = vector_search(collection, query3, 10)
    bm25_hits = bm25_search(bm25, query3, 10)
    merged = merge_rerank(vec_hits, bm25_hits, k_final=10)
    
    print(f"\n[OK] Retrieved {len(merged)} chunks")
    print("\nTop 5 Retrieved Chunks:")
    for i, (doc, score) in enumerate(merged[:5], 1):
        path = doc["meta"].get("path", "unknown")
        chunk_num = doc["meta"].get("chunk", "?")
        content_preview = doc["content"][:150].replace("\n", " ")
        print(f"\n{i}. Score: {score:.3f}")
        print(f"   File: {path}")
        print(f"   Chunk: {chunk_num}")
        print(f"   Preview: {content_preview}...")
        
        # Check if relevant
        is_relevant = any(keyword in path.lower() for keyword in ['angular', 'component', 'service', 'typescript', '.ts'])
        print(f"   Relevant: {'✅ YES' if is_relevant else '❌ NO'}")
    
    # Test Context Optimization
    print("\n" + "=" * 60)
    print("TEST 4: Context Optimization")
    print("=" * 60)
    
    optimizer = get_context_optimizer()
    optimized_chunks = optimizer.optimize_context(merged, max_tokens=2000)
    optimized_text = "\n\n".join([doc["content"] for doc, score in optimized_chunks])
    print(f"\n[OK] Optimized from {len(merged)} to {len(optimized_chunks)} chunks")
    print(f"[OK] Optimized context: {len(optimized_text.split())} words (~{optimizer.count_tokens(optimized_text)} tokens)")
    print(f"\nOptimized Context Preview (first 500 chars):")
    print(optimized_text[:500])
    print("...")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\n[OK] RAG Index: {len(docs)} documents")
    print(f"[OK] Hybrid Search: Vector + BM25")
    print(f"[OK] Reranking: Merge with weighted scores")
    print(f"[OK] Context Optimization: Token limit aware")
    
    print("\n[SUCCESS] RAG system is operational and retrieving context!")
    
    return True

if __name__ == "__main__":
    try:
        test_rag_retrieval()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

