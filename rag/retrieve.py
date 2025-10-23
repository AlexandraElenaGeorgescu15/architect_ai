
import argparse
from pathlib import Path
from rich import print
from rag.filters import load_cfg
from rag.utils import chroma_client, BM25Index
from typing import Dict, List, Any, Optional

def load_docs_from_chroma(coll):
    res = coll.get(include=["documents","metadatas","embeddings"], limit=100000)
    docs = [{"id":i, "content":d, "meta":m} for i,(d,m) in enumerate(zip(res["documents"], res["metadatas"]))]
    return docs

def vector_search(coll, query, k, metadata_filter: Optional[Dict[str, Any]] = None):
    """
    Vector search with optional metadata filtering
    
    Args:
        coll: ChromaDB collection
        query: Search query
        k: Number of results
        metadata_filter: Optional metadata filter (e.g., {"language": "python", "has_tests": True})
    """
    query_params = {
        "query_texts": [query],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"]
    }
    
    # Add metadata filter if provided
    if metadata_filter:
        query_params["where"] = metadata_filter
    
    res = coll.query(**query_params)
    out=[]
    for d,m,dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        out.append(({"content":d,"meta":m}, 1.0 - float(dist)))
    return out

def bm25_search(bm25, query, k):
    return bm25.search(query, k=k)

def merge_rerank(vec_hits, bm25_hits, k_final=18):
    pool = []
    v_max = max([s for _,s in vec_hits], default=1.0) or 1.0
    b_max = max([s for _,s in bm25_hits], default=1.0) or 1.0
    for d,s in vec_hits:
        pool.append((d, 0.6*(s/v_max)))
    for d,s in bm25_hits:
        pool.append((d, 0.4*(s/b_max)))
    seen=set(); merged=[]
    for d,score in sorted(pool, key=lambda x:x[1], reverse=True):
        key = f'{d["meta"].get("path")}::{d["meta"].get("chunk")}'
        if key in seen: continue
        seen.add(key); merged.append((d,score))
        if len(merged)>=k_final: break
    return merged

def write_context(hits, out_path="context/_retrieved.md"):
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path,"w",encoding="utf-8") as f:
        f.write("# Retrieved Context\n\n")
        for i,(d,score) in enumerate(hits, start=1):
            f.write(f"---\n## Snippet {i} (score={score:.3f})\n")
            f.write(f"**FILE:** {d['meta'].get('path')}  \n")
            f.write("```\n"+d["content"]+"\n```\n\n")
    print(f"[bold green]Wrote {out_path} with {len(hits)} snippets.[/]")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", type=str, default=None)
    ap.add_argument("--query-file", type=str, default=None)
    args = ap.parse_args()

    if not args.query and not args.query_file:
        raise SystemExit("Provide --query or --query-file")

    query = args.query or Path(args.query_file).read_text(encoding="utf-8")

    cfg = load_cfg()
    client = chroma_client(cfg["store"]["path"])
    coll = client.get_or_create_collection("repo", metadata={"hnsw:space":"cosine"})
    docs = load_docs_from_chroma(coll)
    print(f"[cyan]BM25 over {len(docs)} docs...[/]")
    bm25 = BM25Index(docs)

    vec_hits = vector_search(coll, query, cfg["hybrid"]["k_vector"])
    bm25_hits = bm25_search(bm25, query, cfg["hybrid"]["k_bm25"])
    hits = merge_rerank(vec_hits, bm25_hits, cfg["hybrid"]["k_final"])
    write_context(hits)

if __name__ == "__main__":
    main()
