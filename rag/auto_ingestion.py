"""
Automatic RAG Ingestion Integration

Main entry point for automatic RAG ingestion system.
Integrates file watching, incremental indexing, and background processing.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .file_watcher import get_file_watcher, FileChangeEvent, start_file_watcher, stop_file_watcher, get_watcher_status
from .background_worker import get_background_worker, process_file_changes_async, get_all_job_statuses
from .filters import load_cfg


class AutoIngestionManager:
    """Manages the automatic RAG ingestion system"""
    
    def __init__(self, cfg: Optional[dict] = None):
        self.cfg = cfg or load_cfg()
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.file_watcher = get_file_watcher()
        self.background_worker = get_background_worker()
        
        # State
        self.is_running = False
        self.pending_events: List[FileChangeEvent] = []
        
        # Configuration
        self.auto_cfg = self.cfg.get('auto_ingestion', {})
        self.enabled = self.auto_cfg.get('enabled', False)
        self.batch_size = self.auto_cfg.get('batch_size', 10)
    
    
    async def _process_file_change(self, event: FileChangeEvent):
        """Process a single file change event"""
        try:
            self.logger.debug(f"Processing file change: {event.event_type} - {event.file_path}")
            
            # Add to pending events
            self.pending_events.append(event)
            
            # Process in batches
            if len(self.pending_events) >= self.batch_size:
                await self._process_batch()
                
        except Exception as e:
            self.logger.error(f"Error processing file change: {e}")
    
    async def _process_batch(self):
        """Process a batch of pending events"""
        if not self.pending_events:
            return
        
        try:
            # Get batch of events
            batch = self.pending_events[:self.batch_size]
            self.pending_events = self.pending_events[self.batch_size:]
            
            self.logger.info(f"Processing batch of {len(batch)} file changes")
            
            # Submit to background worker
            job_id = await process_file_changes_async(batch, job_type='incremental')
            
            self.logger.info(f"Submitted batch job {job_id} with {len(batch)} files")
            
        except Exception as e:
            self.logger.error(f"Error processing batch: {e}")
    
    async def _periodic_batch_processing(self):
        """Periodically process any remaining pending events"""
        while self.is_running:
            try:
                if self.pending_events:
                    await self._process_batch()
                
                # Wait before next check
                await asyncio.sleep(10)  # Process remaining events every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in periodic batch processing: {e}")
                await asyncio.sleep(5)
    
    def start(self) -> bool:
        """Start the automatic ingestion system"""
        if not self.enabled:
            self.logger.info("Auto-ingestion is disabled in configuration")
            return False
        
        if self.is_running:
            self.logger.warning("Auto-ingestion is already running")
            return False
        
        try:
            # Start file watcher
            success = start_file_watcher(self._process_file_change)
            if not success:
                self.logger.error("Failed to start file watcher")
                return False
            
            self.is_running = True
            
            # Start periodic batch processing in a separate thread
            import threading
            def run_periodic():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._periodic_batch_processing())
                except Exception as e:
                    self.logger.error(f"Error in periodic batch processing: {e}")
            
            self.periodic_thread = threading.Thread(target=run_periodic, daemon=True)
            self.periodic_thread.start()
            
            self.logger.info("Automatic RAG ingestion started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start auto-ingestion: {e}")
            return False
    
    def stop(self):
        """Stop the automatic ingestion system"""
        if not self.is_running:
            return
        
        try:
            # Stop file watcher
            stop_file_watcher()
            
            # Stop periodic thread
            if hasattr(self, 'periodic_thread') and self.periodic_thread.is_alive():
                # The thread is daemon, so it will stop when main thread stops
                pass
            
            # Process any remaining pending events
            if self.pending_events:
                self.logger.info(f"Processing {len(self.pending_events)} remaining events before shutdown")
                # Note: This would need to be synchronous for shutdown
                # In a real implementation, you might want to save pending events to disk
            
            self.is_running = False
            self.logger.info("Automatic RAG ingestion stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping auto-ingestion: {e}")
    
    def get_status(self) -> dict:
        """Get current status of the auto-ingestion system"""
        watcher_status = get_watcher_status()
        worker_stats = self.background_worker.get_stats()
        job_statuses = get_all_job_statuses()
        
        return {
            'is_running': self.is_running,
            'enabled': self.enabled,
            'file_watcher': watcher_status,
            'background_worker': worker_stats,
            'active_jobs': len([j for j in job_statuses if j.status in ['pending', 'processing']]),
            'pending_events': len(self.pending_events),
            'recent_jobs': job_statuses[-5:] if job_statuses else []
        }
    
    async def run_forever(self):
        """Run the auto-ingestion system forever"""
        if not self.start():
            return False
        
        try:
            # Keep running until interrupted
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            self.stop()
        
        return True


# Global manager instance
_manager: Optional[AutoIngestionManager] = None


def get_auto_ingestion_manager() -> AutoIngestionManager:
    """Get or create global auto-ingestion manager"""
    global _manager
    if _manager is None:
        _manager = AutoIngestionManager()
    return _manager


def start_auto_ingestion() -> bool:
    """Start the automatic ingestion system"""
    manager = get_auto_ingestion_manager()
    return manager.start()


def stop_auto_ingestion():
    """Stop the automatic ingestion system"""
    manager = get_auto_ingestion_manager()
    manager.stop()


def get_auto_ingestion_status() -> dict:
    """Get status of the auto-ingestion system"""
    manager = get_auto_ingestion_manager()
    return manager.get_status()


async def run_auto_ingestion():
    """Run the auto-ingestion system (for standalone usage)"""
    manager = get_auto_ingestion_manager()
    return await manager.run_forever()


def main():
    """Main entry point for standalone auto-ingestion service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automatic RAG Ingestion Service')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration if specified
    cfg = None
    if args.config:
        cfg = load_cfg(args.config)
    
    # Create manager with custom config
    global _manager
    _manager = AutoIngestionManager(cfg)
    
    # Run the service
    try:
        asyncio.run(run_auto_ingestion())
    except KeyboardInterrupt:
        print("\nShutting down...")
        _manager.stop()
    except Exception as e:
        print(f"Error: {e}")
        _manager.stop()
        sys.exit(1)


if __name__ == '__main__':
    main()
