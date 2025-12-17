"""
RAG Ingestion Service - Refactored from rag/ingest.py
Handles file indexing, incremental updates, and file system watching.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import hashlib
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
import chromadb
from chromadb.config import Settings as ChromaSettings
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import tool detector from components (legacy location)
try:
    from components._tool_detector import should_exclude_path, get_user_project_directories
except ImportError:
    # Fallback: try backend.utils if it exists
    try:
        from backend.utils.tool_detector import should_exclude_path, get_user_project_directories
    except ImportError:
        # Last resort: define minimal versions
        def should_exclude_path(path: Path) -> bool:
            """Check if path should be excluded (Architect.AI project files)."""
            path_str = str(path)
            return 'architect_ai_cursor_poc' in path_str or '.git' in path_str
        
        def get_user_project_directories() -> List[Path]:
            """Get user project directories (excludes Architect.AI project)."""
            from pathlib import Path
            current = Path.cwd()
            # Return parent directory if we're in architect_ai_cursor_poc
            if current.name == 'architect_ai_cursor_poc':
                return [current.parent] if current.parent.exists() else []
            return [current] if current.exists() else []
from backend.core.config import settings

logger = logging.getLogger(__name__)


class RAGIngester:
    """
    RAG ingestion service for indexing repository files.
    
    Features:
    - Incremental indexing (only changed files)
    - File system watching with watchdog
    - Automatic exclusion of tool directory
    - ChromaDB integration
    - SHA1 hash-based change detection
    """
    
    def __init__(self, index_path: Optional[str] = None):
        """
        Initialize RAG ingester.
        
        Args:
            index_path: Path to ChromaDB index (defaults to settings.rag_index_path)
        """
        self.index_path = Path(index_path or settings.rag_index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Use shared ChromaDB client to avoid "different settings" conflicts
        from backend.core.chromadb_client import get_shared_chromadb_client
        self.client = get_shared_chromadb_client(str(self.index_path))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="repo",
            metadata={"hnsw:space": "cosine"}
        )
        
        # File hash tracking for incremental indexing
        self.file_hashes: Dict[str, str] = {}  # file_path -> sha1_hash
        self._load_file_hashes()
        
        # Watchdog observer for file system watching
        self.observer: Optional[Observer] = None
        self.watched_directories: Set[Path] = set()
        
        logger.info(f"RAG Ingester initialized with index at {self.index_path}")
    
    def _load_file_hashes(self):
        """Load file hashes from metadata for incremental indexing."""
        try:
            # Get all existing documents to extract file paths and hashes
            results = self.collection.get(include=["metadatas"])
            for metadata in results.get("metadatas", []):
                if metadata and "file_path" in metadata:
                    file_path = metadata["file_path"]
                    file_hash = metadata.get("file_hash", "")
                    if file_hash:
                        self.file_hashes[file_path] = file_hash
        except Exception as e:
            logger.warning(f"Error loading file hashes: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA1 hash of file content.
        
        Args:
            file_path: Path to file
        
        Returns:
            SHA1 hash string
        """
        try:
            with open(file_path, 'rb') as f:  # Binary mode, no encoding
                content = f.read()
            return hashlib.sha1(content).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def _should_index_file(self, file_path: Path) -> bool:
        """
        Check if file should be indexed.
        
        Args:
            file_path: Path to file
        
        Returns:
            True if file should be indexed
        """
        # Exclude tool directory
        if should_exclude_path(file_path):
            return False
        
        # Only index text files
        text_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', 
                          '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.md', '.txt',
                          '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.scss', '.sql'}
        
        if file_path.suffix.lower() not in text_extensions:
            return False
        
        # Skip binary files and common exclusions
        excluded_patterns = [
            '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'env',
            '.pytest_cache', '.mypy_cache', 'dist', 'build', '.next', '.nuxt'
        ]
        
        path_str = str(file_path)
        if any(pattern in path_str for pattern in excluded_patterns):
            return False
        
        return True
    
    def _chunk_file_content(self, content: str, file_path: Path, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Chunk file content into smaller pieces.
        
        Args:
            content: File content
            file_path: Path to file
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks in characters
        
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        lines = content.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            if current_length + line_length > chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    "content": chunk_text,
                    "file_path": str(file_path),
                    "start_line": len(chunks) * (chunk_size - overlap) + 1,
                    "end_line": len(chunks) * (chunk_size - overlap) + len(current_chunk)
                })
                
                # Start new chunk with overlap
                overlap_lines = current_chunk[-overlap//50:] if len(current_chunk) > overlap//50 else current_chunk
                current_chunk = overlap_lines + [line]
                current_length = sum(len(l) + 1 for l in current_chunk)
            else:
                current_chunk.append(line)
                current_length += line_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                "content": chunk_text,
                "file_path": str(file_path),
                "start_line": len(chunks) * (chunk_size - overlap) + 1,
                "end_line": len(chunks) * (chunk_size - overlap) + len(current_chunk)
            })
        
        return chunks
    
    async def index_file(self, file_path: Path) -> bool:
        """
        Index a single file.
        
        Args:
            file_path: Path to file to index
        
        Returns:
            True if file was indexed successfully
        """
        if not self._should_index_file(file_path):
            return False
        
        try:
            # Check if file has changed
            current_hash = self._calculate_file_hash(file_path)
            existing_hash = self.file_hashes.get(str(file_path), "")
            
            if current_hash == existing_hash and existing_hash:
                logger.debug(f"File unchanged, skipping: {file_path}")
                return False
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove old chunks for this file
            self._remove_file_chunks(str(file_path))
            
            # Chunk content
            chunks = self._chunk_file_content(content, file_path)
            
            if not chunks:
                return False
            
            # Prepare documents for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_path}_{i}"
                documents.append(chunk["content"])
                metadatas.append({
                    "file_path": str(file_path),
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "file_hash": current_hash,
                    "indexed_at": datetime.now().isoformat()
                })
                ids.append(chunk_id)
            
            # Add to ChromaDB (use upsert to handle existing IDs gracefully)
            self.collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            # Update hash tracking
            self.file_hashes[str(file_path)] = current_hash
            
            logger.info(f"Indexed {len(chunks)} chunks from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)
            return False
    
    def _remove_file_chunks(self, file_path: str):
        """Remove all chunks for a file from the index."""
        try:
            # Get all document IDs for this file
            results = self.collection.get(
                where={"file_path": file_path},
                include=["metadatas"]
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.debug(f"Removed {len(results['ids'])} chunks for {file_path}")
        except Exception as e:
            logger.warning(f"Error removing chunks for {file_path}: {e}")
    
    async def index_directory(self, directory: Path, recursive: bool = True) -> Dict[str, Any]:
        """
        Index all files in a directory.
        
        Args:
            directory: Directory to index
            recursive: Whether to index recursively
        
        Returns:
            Statistics about indexing operation
        """
        stats = {
            "files_processed": 0,
            "files_indexed": 0,
            "files_skipped": 0,  # Already indexed (unchanged)
            "files_excluded": 0,  # Excluded by filters
            "chunks_created": 0,
            "errors": 0
        }
        
        # Get user project directories (excludes tool)
        user_dirs = get_user_project_directories()
        
        if directory not in user_dirs:
            logger.warning(f"Directory {directory} not in user project directories, skipping")
            return stats
        
        # Find all files
        pattern = "**/*" if recursive else "*"
        files = list(directory.rglob(pattern)) if recursive else list(directory.glob(pattern))
        
        for file_path in files:
            if not file_path.is_file():
                continue
            
            stats["files_processed"] += 1
            
            # Check if file should be indexed
            if not self._should_index_file(file_path):
                stats["files_excluded"] += 1
                continue
            
            try:
                # Check if file is already indexed and unchanged
                current_hash = self._calculate_file_hash(file_path)
                existing_hash = self.file_hashes.get(str(file_path), "")
                
                if current_hash == existing_hash and existing_hash:
                    stats["files_skipped"] += 1
                    continue
                
                # Index the file
                if await self.index_file(file_path):
                    stats["files_indexed"] += 1
                    # Count chunks (approximate)
                    results = self.collection.get(
                        where={"file_path": str(file_path)},
                        include=["metadatas"]
                    )
                    stats["chunks_created"] += len(results.get("ids", []))
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                stats["errors"] += 1
        
        logger.info(f"Indexing complete: {stats}")
        return stats
    
    def start_watching(self, directory: Path):
        """
        Start watching a directory for file changes.
        
        Args:
            directory: Directory to watch
        """
        if directory in self.watched_directories:
            logger.warning(f"Already watching {directory}")
            return
        
        class RAGFileHandler(FileSystemEventHandler):
            """Handler for file system events."""
            
            def __init__(self, ingester: 'RAGIngester'):
                self.ingester = ingester
                self._loop = None
            
            def _get_or_create_loop(self):
                """Get or create event loop for async operations."""
                if self._loop is None or self._loop.is_closed():
                    try:
                        self._loop = asyncio.get_event_loop()
                    except RuntimeError:
                        self._loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._loop)
                return self._loop
            
            def _schedule_index(self, file_path: Path):
                """Schedule file indexing in async context."""
                if should_exclude_path(file_path):
                    logger.debug(f"Skipping excluded file: {file_path}")
                    return
                
                try:
                    # Use thread pool to run async indexing
                    import concurrent.futures
                    import threading
                    
                    def run_index():
                        """Run indexing in a new event loop."""
                        try:
                            # Create new event loop for this thread
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                new_loop.run_until_complete(self.ingester.index_file(file_path))
                                logger.info(f"Auto-indexed file: {file_path}")
                            finally:
                                new_loop.close()
                        except Exception as e:
                            logger.error(f"Error in indexing thread for {file_path}: {e}", exc_info=True)
                    
                    # Run in background thread (non-blocking)
                    thread = threading.Thread(target=run_index, daemon=True, name=f"RAGIndex-{file_path.name}")
                    thread.start()
                    
                except Exception as e:
                    logger.error(f"Error scheduling index for {file_path}: {e}", exc_info=True)
            
            def on_modified(self, event: FileModifiedEvent):
                if not event.is_directory:
                    self._schedule_index(Path(event.src_path))
            
            def on_created(self, event: FileCreatedEvent):
                if not event.is_directory:
                    self._schedule_index(Path(event.src_path))
            
            def on_deleted(self, event):
                if not event.is_directory:
                    file_path = Path(event.src_path)
                    if not should_exclude_path(file_path):
                        self.ingester._remove_file_chunks(str(file_path))
        
        handler = RAGFileHandler(self)
        observer = Observer()
        observer.schedule(handler, str(directory), recursive=True)
        observer.start()
        
        self.observer = observer
        self.watched_directories.add(directory)
        
        logger.info(f"Started watching {directory}")
    
    def stop_watching(self):
        """Stop all file system watchers."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.watched_directories.clear()
            logger.info("Stopped file system watching")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the index.
        
        Returns:
            Dictionary with index statistics
        """
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "index_path": str(self.index_path),
                "watched_directories": [str(d) for d in self.watched_directories],
                "file_hashes_tracked": len(self.file_hashes)
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")
            return {"error": str(e)}


# Global ingester instance
_ingester: Optional[RAGIngester] = None


def get_ingester() -> RAGIngester:
    """Get or create global RAG ingester instance."""
    global _ingester
    if _ingester is None:
        _ingester = RAGIngester()
    return _ingester

