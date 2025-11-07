"""
File Watcher Service for Automatic RAG Ingestion

Monitors repository files for changes and triggers incremental RAG updates.
Uses watchdog library for cross-platform file system monitoring.
"""

import os
import time
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set, TYPE_CHECKING
from dataclasses import dataclass
from datetime import datetime
import hashlib

if TYPE_CHECKING:
    from watchdog.observers import Observer as ObserverType
else:
    ObserverType = object

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent, FileMovedEvent

from .filters import load_cfg, allow_file
from .refresh_manager import get_refresh_manager


@dataclass
class FileChangeEvent:
    """Represents a file system change event"""
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: str
    old_path: Optional[str] = None  # For moved events
    timestamp: datetime = None
    file_hash: Optional[str] = None
    file_size: Optional[int] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class RAGFileEventHandler(FileSystemEventHandler):
    """Handles file system events for RAG ingestion"""
    
    def __init__(self, callback: Callable[[FileChangeEvent], None], cfg: Dict):
        super().__init__()
        self.callback = callback
        self.cfg = cfg
        self.logger = logging.getLogger(__name__)
        self.refresh_manager = get_refresh_manager()
        
        # Track file hashes to detect actual content changes
        self.file_hashes: Dict[str, str] = {}
        
        # Debouncing: collect events and process in batches
        self.pending_events: Dict[str, FileChangeEvent] = {}
        self.debounce_timer: Optional[threading.Timer] = None
        self.debounce_seconds = cfg.get('auto_ingestion', {}).get('debounce_seconds', 5)
        
    def _compute_file_hash(self, file_path: str) -> Optional[str]:
        """Compute SHA-256 hash of file content"""
        try:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                return None
            
            # Skip large files
            max_size = self.cfg.get('auto_ingestion', {}).get('max_file_size_mb', 1.5) * 1024 * 1024
            if path.stat().st_size > max_size:
                self.logger.warning(f"Skipping large file: {file_path} ({path.stat().st_size} bytes)")
                return None
            
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        except Exception as e:
            self.logger.error(f"Error computing hash for {file_path}: {e}")
            return None
    
    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on configuration"""
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            # Use existing filter logic
            return allow_file(path, self.cfg)
        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {e}")
            return False
    
    def _process_pending_events(self):
        """Process all pending events after debounce period"""
        if not self.pending_events:
            return
        
        events_to_process = list(self.pending_events.values())
        self.pending_events.clear()
        
        self.logger.info(f"Processing {len(events_to_process)} file change events")
        
        for event in events_to_process:
            try:
                # Check if file actually changed (for modified events)
                if event.event_type == 'modified':
                    current_hash = self._compute_file_hash(event.file_path)
                    if current_hash and current_hash == self.file_hashes.get(event.file_path):
                        self.logger.debug(f"File {event.file_path} content unchanged, skipping")
                        continue
                    
                    # Update hash
                    if current_hash:
                        event.file_hash = current_hash
                        self.file_hashes[event.file_path] = current_hash
                
                # Process the event
                self.callback(event)
                
            except Exception as e:
                self.logger.error(f"Error processing event for {event.file_path}: {e}")
    
    def _schedule_debounce(self):
        """Schedule processing of pending events after debounce period"""
        if self.debounce_timer:
            self.debounce_timer.cancel()
        
        self.debounce_timer = threading.Timer(
            self.debounce_seconds, 
            self._process_pending_events
        )
        self.debounce_timer.start()
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_process_file(file_path):
            return
        
        self.logger.debug(f"File modified: {file_path}")
        
        # Add to pending events (will replace any existing event for this file)
        self.pending_events[file_path] = FileChangeEvent(
            event_type='modified',
            file_path=file_path
        )
        
        self._schedule_debounce()
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if not self._should_process_file(file_path):
            return
        
        self.logger.debug(f"File created: {file_path}")
        
        # Add to pending events
        self.pending_events[file_path] = FileChangeEvent(
            event_type='created',
            file_path=file_path
        )
        
        self._schedule_debounce()
    
    def on_deleted(self, event: FileDeletedEvent):
        """Handle file deletion events"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        self.logger.debug(f"File deleted: {file_path}")
        
        # Remove from hash tracking
        self.file_hashes.pop(file_path, None)
        
        # Process immediately (no debounce for deletions)
        event_obj = FileChangeEvent(
            event_type='deleted',
            file_path=file_path
        )
        
        try:
            self.callback(event_obj)
        except Exception as e:
            self.logger.error(f"Error processing deletion event for {file_path}: {e}")
    
    def on_moved(self, event: FileMovedEvent):
        """Handle file move/rename events"""
        if event.is_directory:
            return
        
        old_path = event.src_path
        new_path = event.dest_path
        
        # Check if new file should be processed
        if not self._should_process_file(new_path):
            return
        
        self.logger.debug(f"File moved: {old_path} -> {new_path}")
        
        # Remove old hash, add new file to pending events
        self.file_hashes.pop(old_path, None)
        
        self.pending_events[new_path] = FileChangeEvent(
            event_type='moved',
            file_path=new_path,
            old_path=old_path
        )
        
        self._schedule_debounce()


class RAGFileWatcher:
    """Main file watcher service for automatic RAG ingestion"""
    
    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or load_cfg()
        self.logger = logging.getLogger(__name__)
        self.observer = None  # type: ignore[var-annotated]
        self.is_running = False
        self.event_handler: Optional[RAGFileEventHandler] = None
        
        # Auto-ingestion configuration
        self.auto_cfg = self.cfg.get('auto_ingestion', {})
        self.enabled = self.auto_cfg.get('enabled', False)
        self.watch_directories = self.auto_cfg.get('watch_directories', ['.'])
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'files_indexed': 0,
            'errors': 0,
            'start_time': None
        }
    
    def start(self, callback: Callable[[FileChangeEvent], None]):
        """Start the file watcher service"""
        if not self.enabled:
            self.logger.info("Auto-ingestion is disabled in configuration")
            return False
        
        if self.is_running:
            self.logger.warning("File watcher is already running")
            return False
        
        try:
            # Create event handler
            self.event_handler = RAGFileEventHandler(callback, self.cfg)
            
            # Create observer
            self.observer = Observer()
            
            # Add watches for each directory
            for watch_dir in self.watch_directories:
                watch_path = Path(watch_dir).resolve()
                if not watch_path.exists():
                    self.logger.warning(f"Watch directory does not exist: {watch_path}")
                    continue
                
                self.observer.schedule(
                    self.event_handler,
                    str(watch_path),
                    recursive=True
                )
                self.logger.info(f"Watching directory: {watch_path}")
            
            # Start observer
            self.observer.start()
            self.is_running = True
            self.stats['start_time'] = datetime.now()
            
            self.logger.info(f"File watcher started, monitoring {len(self.watch_directories)} directories")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}")
            return False
    
    def stop(self):
        """Stop the file watcher service"""
        if not self.is_running:
            return
        
        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)
            
            # Cancel any pending debounce timer
            if self.event_handler and self.event_handler.debounce_timer:
                self.event_handler.debounce_timer.cancel()
            
            self.is_running = False
            self.logger.info("File watcher stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping file watcher: {e}")
    
    def get_status(self) -> Dict:
        """Get current status and statistics"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'enabled': self.enabled,
            'watch_directories': self.watch_directories,
            'stats': self.stats.copy(),
            'uptime_seconds': uptime
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# Global file watcher instance
_file_watcher: Optional[RAGFileWatcher] = None


def get_file_watcher() -> RAGFileWatcher:
    """Get or create global file watcher instance"""
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = RAGFileWatcher()
    return _file_watcher


def start_file_watcher(callback: Callable[[FileChangeEvent], None]) -> bool:
    """Start the global file watcher"""
    watcher = get_file_watcher()
    return watcher.start(callback)


def stop_file_watcher():
    """Stop the global file watcher"""
    global _file_watcher
    if _file_watcher:
        _file_watcher.stop()


def get_watcher_status() -> Dict:
    """Get file watcher status"""
    watcher = get_file_watcher()
    return watcher.get_status()
