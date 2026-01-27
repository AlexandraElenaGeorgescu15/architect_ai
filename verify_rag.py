#!/usr/bin/env python3
"""
RAG Index Verification Script

This script helps verify what's been indexed in the RAG system and diagnose
potential indexing issues.

Usage:
    python verify_rag.py                    # Show index stats
    python verify_rag.py KnowledgeGraph     # Search for 'KnowledgeGraph'
    python verify_rag.py --list-files       # List all indexed files
    python verify_rag.py --check-config     # Check ignore_globs config
"""

import sys
import argparse
from pathlib import Path

# Enable UTF-8 output on Windows for emoji/Unicode
if sys.platform == 'win32':
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except (AttributeError, OSError, ValueError):
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import chromadb
import yaml


def load_config():
    """Load RAG configuration."""
    config_path = Path("rag/config.yaml")
    if not config_path.exists():
        print(f"[ERROR] Config not found at {config_path}")
        return None
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_chroma_client(config):
    """Get ChromaDB client."""
    store_path = config.get("store", {}).get("path", "rag/index")
    path = Path(store_path)
    
    if not path.exists():
        print(f"[ERROR] ChromaDB path does not exist: {path.absolute()}")
        print(f"[INFO] Run 'python -m rag.ingest' to create the index first.")
        return None, None
    
    try:
        client = chromadb.PersistentClient(path=str(path))
        collection = client.get_collection("repo")
        return client, collection
    except Exception as e:
        print(f"[ERROR] Failed to connect to ChromaDB: {e}")
        return None, None


def show_stats(collection):
    """Show index statistics."""
    print("\n" + "=" * 60)
    print("RAG INDEX STATISTICS")
    print("=" * 60)
    
    count = collection.count()
    print(f"\n📊 Total chunks indexed: {count}")
    
    if count == 0:
        print("\n⚠️  WARNING: Index is EMPTY!")
        print("   Run 'python -m rag.ingest' to index your codebase.")
        return
    
    # Get sample of metadata to understand structure
    sample = collection.peek(limit=5)
    
    # Collect unique files
    all_results = collection.get(include=["metadatas"])
    files = set()
    languages = {}
    
    for meta in all_results.get("metadatas", []):
        if meta:
            source = meta.get("source", meta.get("file", meta.get("file_path", "unknown")))
            files.add(source)
            lang = meta.get("language", "unknown")
            languages[lang] = languages.get(lang, 0) + 1
    
    print(f"📁 Unique files indexed: {len(files)}")
    print(f"\n📝 Language breakdown:")
    for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:10]:
        print(f"   {lang}: {count} chunks")


def list_indexed_files(collection):
    """List all indexed files."""
    print("\n" + "=" * 60)
    print("INDEXED FILES")
    print("=" * 60 + "\n")
    
    all_results = collection.get(include=["metadatas"])
    files = {}
    
    for meta in all_results.get("metadatas", []):
        if meta:
            source = meta.get("source", meta.get("file", meta.get("file_path", "unknown")))
            files[source] = files.get(source, 0) + 1
    
    if not files:
        print("⚠️  No files indexed!")
        return
    
    # Sort by chunk count
    for filepath, chunk_count in sorted(files.items(), key=lambda x: -x[1]):
        print(f"  [{chunk_count:3d} chunks] {filepath}")
    
    print(f"\n📊 Total: {len(files)} files")


def search_function(collection, query: str, n_results: int = 10):
    """Search for a function or term in the index."""
    print("\n" + "=" * 60)
    print(f"SEARCH RESULTS FOR: '{query}'")
    print("=" * 60 + "\n")
    
    # Search using the collection's query method
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    if not documents:
        print(f"❌ NOT FOUND: '{query}' was not found in the index.")
        print("\n   Possible reasons:")
        print("   1. The file containing it is in ignore_globs (check config.yaml)")
        print("   2. The index hasn't been built yet (run 'python -m rag.ingest')")
        print("   3. The file extension isn't in allow_extensions")
        return False
    
    found = False
    print(f"✅ FOUND: {len(documents)} results for '{query}':\n")
    
    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        source = meta.get("source", meta.get("file", meta.get("file_path", "unknown")))
        similarity = 1 - dist  # Convert distance to similarity
        
        # Check if query term appears in document
        is_exact_match = query.lower() in doc.lower()
        match_indicator = "🎯 EXACT" if is_exact_match else "🔍 SIMILAR"
        
        if is_exact_match:
            found = True
        
        print(f"─── Result {i+1} ({match_indicator}, sim={similarity:.3f}) ───")
        print(f"📁 File: {source}")
        if meta.get("start_line"):
            print(f"📍 Lines: {meta.get('start_line')}-{meta.get('end_line', '?')}")
        
        # Show snippet (first 300 chars)
        snippet = doc[:300].replace('\n', '\n   ')
        print(f"📝 Snippet:\n   {snippet}...")
        print()
    
    return found


def check_config(config):
    """Check and explain the ignore_globs configuration."""
    print("\n" + "=" * 60)
    print("IGNORE_GLOBS CONFIGURATION CHECK")
    print("=" * 60 + "\n")
    
    ignore_globs = config.get("ignore_globs", [])
    allow_extensions = config.get("allow_extensions", [])
    
    print("📋 Allowed extensions:")
    print(f"   {', '.join(allow_extensions)}\n")
    
    print("🚫 Ignored patterns (THESE FOLDERS ARE SKIPPED):")
    
    # Categorize patterns
    dangerous_patterns = []
    for pattern in ignore_globs:
        # These might exclude user code unintentionally
        if pattern in ["components/**", "services/**", "models/**", 
                       "utils/**", "core/**", "db/**", "config/**"]:
            dangerous_patterns.append(pattern)
        print(f"   • {pattern}")
    
    if dangerous_patterns:
        print("\n" + "⚠️ " * 20)
        print("⚠️  WARNING: The following patterns may exclude USER CODE:")
        for p in dangerous_patterns:
            print(f"      ❌ {p}")
        print("\n   These are common folder names in many projects!")
        print("   If your project has these folders, they WON'T be indexed.")
        print("   Consider removing them from rag/config.yaml ignore_globs.")
        print("⚠️ " * 20)
    
    # Check ChromaDB path
    store_path = config.get("store", {}).get("path", "rag/index")
    print(f"\n💾 ChromaDB storage path: {store_path}")
    
    if Path(store_path).exists():
        print(f"   ✅ Path exists")
    else:
        print(f"   ❌ Path does NOT exist - run 'python -m rag.ingest' first")


def main():
    parser = argparse.ArgumentParser(
        description="Verify RAG index contents and diagnose issues"
    )
    parser.add_argument(
        "query", 
        nargs="?", 
        help="Search term (e.g., function name like 'KnowledgeGraph')"
    )
    parser.add_argument(
        "--list-files", "-l",
        action="store_true",
        help="List all indexed files"
    )
    parser.add_argument(
        "--check-config", "-c",
        action="store_true",
        help="Check and explain ignore_globs configuration"
    )
    parser.add_argument(
        "--results", "-n",
        type=int,
        default=10,
        help="Number of search results to return (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Check config option
    if args.check_config:
        check_config(config)
        return
    
    # Get ChromaDB client
    client, collection = get_chroma_client(config)
    if not collection:
        sys.exit(1)
    
    # List files option
    if args.list_files:
        list_indexed_files(collection)
        return
    
    # Show stats if no query
    if not args.query:
        show_stats(collection)
        print("\n" + "-" * 60)
        print("💡 Usage examples:")
        print("   python verify_rag.py KnowledgeGraph    # Search for function")
        print("   python verify_rag.py --list-files      # List all indexed files")
        print("   python verify_rag.py --check-config    # Check ignore patterns")
        return
    
    # Search for query
    found = search_function(collection, args.query, args.results)
    
    if not found:
        print("\n💡 Tip: Run 'python verify_rag.py --check-config' to see what's being ignored.")


if __name__ == "__main__":
    main()

