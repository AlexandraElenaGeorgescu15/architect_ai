"""
Incremental RAG Indexer

Handles incremental updates to the RAG index based on file changes.
Only processes changed files and updates corresponding chunks in ChromaDB.
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from .file_watcher import FileChangeEvent
from .filters import load_cfg, allow_file, CODE_EXTS, sha1
from .chunkers import chunk_code, chunk_text
from .utils import chroma_client, EmbeddingBackend
from .refresh_manager import get_refresh_manager
from .metadata_enhancer import get_metadata_enhancer


@dataclass
class IndexingResult:
    """Result of an indexing operation"""
    success: bool
    files_processed: int
    chunks_added: int
    chunks_updated: int
    chunks_removed: int
    errors: List[str]
    processing_time: float


class IncrementalIndexer:
    """Handles incremental updates to the RAG index"""
    
    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or load_cfg()
        self.logger = logging.getLogger(__name__)
        self.refresh_manager = get_refresh_manager()
        
        # Initialize components
        self.embedding_backend = None
        self.chroma_client = None
        self.collection = None
        self.metadata_enhancer = None
        
        # Statistics
        self.stats = {
            'total_files_processed': 0,
            'total_chunks_added': 0,
            'total_chunks_updated': 0,
            'total_chunks_removed': 0,
            'total_errors': 0,
            'last_update': None
        }
    
    def _ensure_components(self):
        """Ensure all required components are initialized"""
        if self.embedding_backend is None:
            provider = self.cfg.get("embedding", {}).get("provider", "local")
            model = self.cfg["embedding"]["local_model"] if provider == "local" else self.cfg["embedding"]["openai_model"]
            self.embedding_backend = EmbeddingBackend(provider, model).ensure()
        
        if self.chroma_client is None:
            self.chroma_client = chroma_client(self.cfg["store"]["path"])
            self.collection = self.chroma_client.get_or_create_collection("repo", metadata={"hnsw:space": "cosine"})
        
        if self.metadata_enhancer is None:
            self.metadata_enhancer = get_metadata_enhancer()
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content with error handling"""
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                return None
            
            # Check file size limit
            max_size = self.cfg.get('auto_ingestion', {}).get('max_file_size_mb', 1.5) * 1024 * 1024
            if path.stat().st_size > max_size:
                self.logger.warning(f"File too large, skipping: {file_path}")
                return None
            
            # Read file content
            content = path.read_text(encoding='utf-8', errors='ignore')
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def _generate_chunks(self, file_path: str, content: str) -> List[Dict]:
        """Generate chunks for a file"""
        try:
            path = Path(file_path)
            is_code = path.suffix in CODE_EXTS
            
            if is_code:
                chunks = chunk_code(
                    str(path), content,
                    self.cfg["chunk"]["code_tokens"],
                    self.cfg["chunk"]["overlap_tokens"]
                )
            else:
                chunks = chunk_text(
                    str(path), content,
                    self.cfg["chunk"]["text_tokens"],
                    self.cfg["chunk"]["overlap_tokens"]
                )
            
            return chunks or []
            
        except Exception as e:
            self.logger.error(f"Error generating chunks for {file_path}: {e}")
            return []
    
    def _get_existing_chunk_ids(self, file_path: str) -> Set[str]:
        """Get existing chunk IDs for a file"""
        try:
            # Query ChromaDB for existing chunks from this file
            results = self.collection.get(
                where={"file_path": file_path},
                include=["metadatas"]
            )
            
            return set(results.get('ids', []))
            
        except Exception as e:
            self.logger.error(f"Error getting existing chunks for {file_path}: {e}")
            return set()
    
    def _remove_file_chunks(self, file_path: str) -> int:
        """Remove all chunks for a file"""
        try:
            existing_ids = self._get_existing_chunk_ids(file_path)
            if not existing_ids:
                return 0
            
            # Remove chunks from ChromaDB
            self.collection.delete(ids=list(existing_ids))
            
            self.logger.info(f"Removed {len(existing_ids)} chunks for deleted file: {file_path}")
            return len(existing_ids)
            
        except Exception as e:
            self.logger.error(f"Error removing chunks for {file_path}: {e}")
            return 0
    
    def _update_file_chunks(self, file_path: str, content: str) -> Tuple[int, int, int]:
        """Update chunks for a file (add/update/remove as needed)"""
        try:
            # Generate new chunks
            new_chunks = self._generate_chunks(file_path, content)
            if not new_chunks:
                return 0, 0, 0
            
            # Get existing chunk IDs
            existing_ids = self._get_existing_chunk_ids(file_path)
            
            # Prepare new chunk data
            new_ids = [sha1(chunk["id"]) for chunk in new_chunks]
            new_docs = [chunk["content"] for chunk in new_chunks]
            
            # Generate embeddings
            embeddings = self.embedding_backend.embed(new_docs)
            
            # Prepare metadata
            path = Path(file_path)
            file_metadata = self.metadata_enhancer.enhance(str(path), content)
            
            new_metas = []
            for chunk in new_chunks:
                chunk_meta = chunk["meta"].copy()
                chunk_meta.update({
                    "language": file_metadata["language"],
                    "has_tests": file_metadata["has_tests"],
                    "has_documentation": file_metadata["has_documentation"],
                    "is_config": file_metadata["is_config"],
                    "importance_score": file_metadata["importance_score"],
                    "complexity_score": file_metadata["complexity_score"],
                    "file_type": file_metadata["file_type"]
                })
                new_metas.append(chunk_meta)
            
            # Update ChromaDB (upsert will handle both add and update)
            batch_size = self.cfg["chunk"]["batch_size"]
            for i in range(0, len(new_docs), batch_size):
                self.collection.upsert(
                    ids=new_ids[i:i+batch_size],
                    documents=new_docs[i:i+batch_size],
                    metadatas=new_metas[i:i+batch_size],
                    embeddings=embeddings[i:i+batch_size]
                )
            
            # Calculate statistics
            chunks_added = len(set(new_ids) - existing_ids)
            chunks_updated = len(set(new_ids) & existing_ids)
            chunks_removed = len(existing_ids - set(new_ids))
            
            self.logger.info(f"Updated file {file_path}: +{chunks_added} ~{chunks_updated} -{chunks_removed} chunks")
            
            return chunks_added, chunks_updated, chunks_removed
            
        except Exception as e:
            self.logger.error(f"Error updating chunks for {file_path}: {e}")
            return 0, 0, 0
    
    def _update_file_hash(self, file_path: str, content: str):
        """Update file hash in the manifest"""
        try:
            # Compute current hash
            current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Get current repository path (assume single repo for now)
            repo_path = Path.cwd().resolve()
            
            # Get current hash manifest
            current_hashes = self.refresh_manager.get_file_hash_manifest(str(repo_path))
            
            # Update hash for this file
            current_hashes[file_path] = current_hash
            
            # Save updated manifest
            self.refresh_manager.update_file_hash_manifest(str(repo_path), current_hashes)
            
        except Exception as e:
            self.logger.error(f"Error updating file hash for {file_path}: {e}")
    
    def process_file_change(self, event: FileChangeEvent) -> IndexingResult:
        """Process a single file change event"""
        start_time = datetime.now()
        errors = []
        
        try:
            self._ensure_components()
            
            file_path = event.file_path
            
            if event.event_type == 'deleted':
                # Remove all chunks for deleted file
                chunks_removed = self._remove_file_chunks(file_path)
                
                result = IndexingResult(
                    success=True,
                    files_processed=1,
                    chunks_added=0,
                    chunks_updated=0,
                    chunks_removed=chunks_removed,
                    errors=errors,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
                
            elif event.event_type in ['created', 'modified', 'moved']:
                # Read file content
                content = self._read_file_content(file_path)
                if content is None:
                    errors.append(f"Could not read file: {file_path}")
                    result = IndexingResult(
                        success=False,
                        files_processed=0,
                        chunks_added=0,
                        chunks_updated=0,
                        chunks_removed=0,
                        errors=errors,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
                else:
                    # Update chunks
                    chunks_added, chunks_updated, chunks_removed = self._update_file_chunks(file_path, content)
                    
                    # Update file hash
                    self._update_file_hash(file_path, content)
                    
                    result = IndexingResult(
                        success=True,
                        files_processed=1,
                        chunks_added=chunks_added,
                        chunks_updated=chunks_updated,
                        chunks_removed=chunks_removed,
                        errors=errors,
                        processing_time=(datetime.now() - start_time).total_seconds()
                    )
            else:
                errors.append(f"Unknown event type: {event.event_type}")
                result = IndexingResult(
                    success=False,
                    files_processed=0,
                    chunks_added=0,
                    chunks_updated=0,
                    chunks_removed=0,
                    errors=errors,
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Update statistics
            self._update_stats(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing file change: {e}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            result = IndexingResult(
                success=False,
                files_processed=0,
                chunks_added=0,
                chunks_updated=0,
                chunks_removed=0,
                errors=errors,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            
            self._update_stats(result)
            return result
    
    def process_batch_changes(self, events: List[FileChangeEvent]) -> IndexingResult:
        """Process multiple file change events in batch"""
        start_time = datetime.now()
        total_result = IndexingResult(
            success=True,
            files_processed=0,
            chunks_added=0,
            chunks_updated=0,
            chunks_removed=0,
            errors=[],
            processing_time=0
        )
        
        for event in events:
            result = self.process_file_change(event)
            
            # Aggregate results
            total_result.files_processed += result.files_processed
            total_result.chunks_added += result.chunks_added
            total_result.chunks_updated += result.chunks_updated
            total_result.chunks_removed += result.chunks_removed
            total_result.errors.extend(result.errors)
            
            if not result.success:
                total_result.success = False
        
        total_result.processing_time = (datetime.now() - start_time).total_seconds()
        
        self.logger.info(f"Batch processing completed: {total_result.files_processed} files, "
                        f"+{total_result.chunks_added} ~{total_result.chunks_updated} -{total_result.chunks_removed} chunks")
        
        return total_result
    
    def _update_stats(self, result: IndexingResult):
        """Update internal statistics"""
        self.stats['total_files_processed'] += result.files_processed
        self.stats['total_chunks_added'] += result.chunks_added
        self.stats['total_chunks_updated'] += result.chunks_updated
        self.stats['total_chunks_removed'] += result.chunks_removed
        self.stats['total_errors'] += len(result.errors)
        self.stats['last_update'] = datetime.now()
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_files_processed': 0,
            'total_chunks_added': 0,
            'total_chunks_updated': 0,
            'total_chunks_removed': 0,
            'total_errors': 0,
            'last_update': None
        }


# Global indexer instance
_indexer: Optional[IncrementalIndexer] = None


def get_incremental_indexer() -> IncrementalIndexer:
    """Get or create global incremental indexer instance"""
    global _indexer
    if _indexer is None:
        _indexer = IncrementalIndexer()
    return _indexer


def process_file_change(event: FileChangeEvent) -> IndexingResult:
    """Process a single file change event"""
    indexer = get_incremental_indexer()
    return indexer.process_file_change(event)


def process_batch_changes(events: List[FileChangeEvent]) -> IndexingResult:
    """Process multiple file change events"""
    indexer = get_incremental_indexer()
    return indexer.process_batch_changes(events)
