
import os, json, sys
from pathlib import Path

# Enable UTF-8 output on Windows for emoji/Unicode
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich import print
from rag.filters import load_cfg, allow_file, sanitize, sha1
from rag.chunkers import chunk_text, chunk_code
from rag.utils import EmbeddingBackend, chroma_client
from rag.metadata_enhancer import get_metadata_enhancer
from rag.filters import CODE_EXTS
from components._tool_detector import should_exclude_path

def read_file(p:Path)->str:
    """
    Read file contents with proper error logging.
    
    Instead of silently failing, logs warnings so users know which files
    couldn't be indexed (permissions, encoding, etc.).
    """
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except PermissionError:
        print(f"[yellow]⚠ Permission denied: {p}[/]")
        return ""
    except UnicodeDecodeError as e:
        print(f"[yellow]⚠ Encoding error in {p}: {e}[/]")
        return ""
    except Exception as e:
        print(f"[yellow]⚠ Failed to read {p}: {type(e).__name__}: {e}[/]")
        return ""

def main():
    cfg = load_cfg()
    
    # SMART ROOT DETECTION: Find the actual project root
    # If this tool is in a subdirectory, go up to find the real project root
    current = Path(".").resolve()
    
    # Check if we're in a tool/utility subdirectory
    root = current
    check_path = current
    for _ in range(3):  # Check up to 3 levels up
        parent = check_path.parent
        if parent != check_path:
            subdirs = [d for d in parent.iterdir() if d.is_dir() and not d.name.startswith('.')]
            if len(subdirs) >= 2 and check_path.name in [d.name for d in subdirs]:
                root = parent
                print(f"[bold yellow]Detected project root at: {root}[/]")
                break
        check_path = parent
    
    if root == current:
        print(f"[bold cyan]Indexing from current directory: {root}[/]")
    
    # Phase 1: Get all files that pass config filters (extensions, size, ignore_globs)
    config_passed = [p for p in root.rglob("*") if allow_file(p, cfg)]
    
    # Phase 2: Exclude tool's own code using intelligent detection
    # This is separate from ignore_globs to keep config clean
    files = []
    tool_excluded = 0
    for p in config_passed:
        if should_exclude_path(p):
            tool_excluded += 1
            continue
        files.append(p)
    
    # Report filtering results
    print(f"\n[bold cyan]📊 File Discovery Summary:[/]")
    print(f"   Total files found: {len(list(root.rglob('*')))}")
    print(f"   After config filters (extensions, size, ignore_globs): {len(config_passed)}")
    print(f"   After tool self-exclusion: {len(files)}")
    if tool_excluded > 0:
        print(f"   [yellow]⚠ Excluded {tool_excluded} files from Architect.AI tool directory[/]")
    
    print(f"\n[bold green]✓ Indexing {len(files)} files...[/]")

    # embeddings
    provider = os.getenv("EMBEDDINGS_PROVIDER", cfg["embedding"]["provider"])
    model = cfg["embedding"]["local_model"] if provider=="local" else cfg["embedding"]["openai_model"]
    emb = EmbeddingBackend(provider, model).ensure()

    # chroma collection
    client = chroma_client(cfg["store"]["path"])
    coll = client.get_or_create_collection("repo", metadata={"hnsw:space":"cosine"})

    # metadata enhancer
    enhancer = get_metadata_enhancer()

    added=0
    for f in files:
        text = sanitize(read_file(f))
        if not text.strip(): continue
        
        # Extract enhanced metadata for the file
        file_metadata = enhancer.enhance(str(f), text)
        
        is_code = f.suffix in CODE_EXTS
        chunks = (chunk_code if is_code else chunk_text)(str(f), text,
                    cfg["chunk"]["code_tokens"] if is_code else cfg["chunk"]["text_tokens"],
                    cfg["chunk"]["overlap_tokens"])
        if not chunks: continue
        ids = [sha1(c["id"]) for c in chunks]
        docs = [c["content"] for c in chunks]
        
        # Merge file metadata with chunk metadata
        metas = []
        for c in chunks:
            chunk_meta = c["meta"].copy()
            # Add selected file metadata to each chunk
            chunk_meta.update({
                "language": file_metadata["language"],
                "has_tests": file_metadata["has_tests"],
                "has_documentation": file_metadata["has_documentation"],
                "is_config": file_metadata["is_config"],
                "importance_score": file_metadata["importance_score"],
                "complexity_score": file_metadata["complexity_score"],
                "file_type": file_metadata["file_type"]
            })
            metas.append(chunk_meta)
        
        vecs = emb.embed(docs)
        B=64
        for i in range(0, len(docs), B):
            coll.upsert(ids=ids[i:i+B], documents=docs[i:i+B], metadatas=metas[i:i+B], embeddings=vecs[i:i+B])
        added += len(docs)

    # Record index completion with refresh manager
    from rag.refresh_manager import get_refresh_manager
    refresh_mgr = get_refresh_manager()
    refresh_mgr.record_index_completion(str(root), added, root.name)
    
    print(f"[bold green]Done. Indexed {added} chunks with enhanced metadata.[/]")
    print(f"[bold cyan]Repository: {root.name}[/]")
    print(f"[bold cyan]Last indexed: {refresh_mgr.check_freshness()['last_updated']}[/]")

if __name__ == "__main__":
    main()
