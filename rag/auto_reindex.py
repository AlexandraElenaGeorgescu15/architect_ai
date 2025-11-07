"""
Auto RAG Re-indexing Module

Watches for file changes and automatically triggers incremental re-indexing.
Uses IncrementalIndexer for actual index updates and FileWatcher for change detection.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .incremental_indexer import IncrementalIndexer
from .file_watcher import RAGFileWatcher, FileChangeEvent
from .filters import load_cfg


logger = logging.getLogger(__name__)


class AutoReindexer:
    """
    Auto-reindexer that monitors files and triggers incremental indexing.
    
    Uses FileWatcher to detect changes and IncrementalIndexer to update the RAG index.
    Runs in a background thread to avoid blocking the main application.
    """
    
    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or load_cfg()
        self.is_running = False
        self.indexer = IncrementalIndexer(self.cfg)
        self.file_watcher: Optional[RAGFileWatcher] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.change_queue: List[FileChangeEvent] = []
        self.queue_lock = threading.Lock()
        
        # Get watched directories from config
        auto_config = self.cfg.get('auto_ingestion', {})
        self.watched_dirs = auto_config.get('watch_directories', ['./'])
        self.watch_interval = auto_config.get('watch_interval', 5)  # seconds
        
        # Statistics
        self._tracked_files_count = 0
        self.last_reindex = "Never"
        self.total_reindexes = 0
    
    def start(self) -> bool:
        """Start the auto-reindexer"""
        if self.is_running:
            logger.warning("Auto-reindexer is already running")
            return False
        
        try:
            # Initialize file watcher
            self.file_watcher = RAGFileWatcher(cfg=self.cfg)
            
            # Start file watcher with callback
            success = self.file_watcher.start(callback=self._on_file_change)
            if not success:
                logger.warning("Failed to start file watcher")
                return False
            
            # Start background worker thread
            self.stop_event.clear()
            self.worker_thread = threading.Thread(
                target=self._worker_loop,
                daemon=True,
                name="AutoReindexWorker"
            )
            self.worker_thread.start()
            
            self.is_running = True
            logger.info(f"Auto-reindexer started, watching {len(self.watched_dirs)} directories")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start auto-reindexer: {e}")
            return False
    
    def stop(self):
        """Stop the auto-reindexer"""
        if not self.is_running:
            return
        
        self.stop_event.set()
        self.is_running = False
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        
        if self.file_watcher:
            self.file_watcher.stop()
        
        logger.info("Auto-reindexer stopped")
    
    def _on_file_change(self, event: FileChangeEvent):
        """Callback for file change events from RAGFileWatcher"""
        with self.queue_lock:
            self.change_queue.append(event)
    
    def _worker_loop(self):
        """Background worker that processes file changes"""
        logger.info("Auto-reindex worker started")
        
        while not self.stop_event.is_set():
            try:
                # Check for queued file changes
                changes = []
                with self.queue_lock:
                    if self.change_queue:
                        changes = self.change_queue[:]
                        self.change_queue.clear()
                
                if changes:
                    logger.info(f"Detected {len(changes)} file changes, triggering reindex...")
                    self._process_changes(changes)
                    self.last_reindex = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self.total_reindexes += 1
                
                # Update tracked files count by scanning watched directories
                self._update_tracked_files_count()
                
            except Exception as e:
                logger.error(f"Error in auto-reindex worker: {e}")
            
            # Sleep before next check
            time.sleep(self.watch_interval)
        
        logger.info("Auto-reindex worker stopped")
    
    def _process_changes(self, changes: List[FileChangeEvent]):
        """Process file changes and update index"""
        try:
            # Group changes by type
            added_files = [c.file_path for c in changes if c.event_type in ('created', 'added')]
            modified_files = [c.file_path for c in changes if c.event_type == 'modified']
            deleted_files = [c.file_path for c in changes if c.event_type == 'deleted']
            
            # Process additions and modifications
            for file_path in added_files + modified_files:
                try:
                    result = self.indexer.process_file(file_path)
                    if result.success:
                        logger.debug(f"Reindexed {file_path}: +{result.chunks_added} chunks")
                except Exception as e:
                    logger.error(f"Failed to reindex {file_path}: {e}")
            
            # Process deletions
            for file_path in deleted_files:
                try:
                    result = self.indexer.remove_file(file_path)
                    if result.success:
                        logger.debug(f"Removed {file_path}: -{result.chunks_removed} chunks")
                except Exception as e:
                    logger.error(f"Failed to remove {file_path}: {e}")
            
            logger.info(f"Reindex complete: +{len(added_files)}, ~{len(modified_files)}, -{len(deleted_files)}")
            
        except Exception as e:
            logger.error(f"Error processing changes: {e}")
    
    def _update_tracked_files_count(self):
        """
        Count files being tracked in watched directories.
        Uses a fast approximation to avoid long scans.
        """
        try:
            from .filters import allow_file
            
            count = 0
            checked = 0
            max_to_scan = 2000  # Limit scan depth
            
            for watch_dir in self.watched_dirs:
                dir_path = Path(watch_dir).resolve()
                if not dir_path.exists():
                    continue
                
                # Count files that match the filter criteria
                for file_path in dir_path.rglob('*'):
                    checked += 1
                    if checked > max_to_scan:
                        # Too many files, stop scanning
                        logger.debug(f"File count limit reached, stopped at {count} files")
                        break
                    
                    if file_path.is_file() and allow_file(file_path, self.cfg):
                        count += 1
                
                if checked > max_to_scan:
                    break
            
            self._tracked_files_count = count
            
        except Exception as e:
            logger.error(f"Error counting tracked files: {e}")
            self._tracked_files_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            'is_running': self.is_running,
            'watched_dirs': self.watched_dirs,
            'tracked_files': self._tracked_files_count,
            'last_reindex': self.last_reindex,
            'total_reindexes': self.total_reindexes,
            'watch_interval': self.watch_interval
        }


# Global instance
_reindexer: Optional[AutoReindexer] = None


def get_auto_reindexer() -> AutoReindexer:
    """Get the global auto-reindexer instance"""
    global _reindexer
    if _reindexer is None:
        _reindexer = AutoReindexer()
    return _reindexer


def start_auto_reindex() -> bool:
    """Start auto-reindexing"""
    return get_auto_reindexer().start()


def stop_auto_reindex():
    """Stop auto-reindexing"""
    get_auto_reindexer().stop()


def get_reindex_status() -> Dict[str, Any]:
    """Get auto-reindexing status"""
    return get_auto_reindexer().get_status()
