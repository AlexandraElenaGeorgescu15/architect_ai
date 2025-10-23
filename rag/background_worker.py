"""
Background Worker for RAG Indexing Jobs

Handles asynchronous processing of RAG indexing tasks using Celery.
Provides job queue management, progress tracking, and error handling.
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

# Try to import Celery, fall back to simple queue if not available
try:
    from celery import Celery, Task
    from celery.exceptions import Retry
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Fallback classes
    class Task:
        def __init__(self, *args, **kwargs):
            pass
    
    class Retry(Exception):
        pass

from .file_watcher import FileChangeEvent
from .incremental_indexer import get_incremental_indexer, IndexingResult
from .filters import load_cfg


@dataclass
class IndexingJob:
    """Represents an indexing job"""
    job_id: str
    repository_path: str
    files_to_process: List[str]
    job_type: str  # 'incremental', 'full', 'cleanup'
    priority: int = 1
    created_at: datetime = None
    status: str = 'pending'  # 'pending', 'processing', 'completed', 'failed'
    result: Optional[IndexingResult] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class JobProgress:
    """Job progress information"""
    job_id: str
    status: str
    progress_percent: float
    current_file: Optional[str] = None
    files_processed: int = 0
    total_files: int = 0
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None


class RAGIndexingWorker:
    """Background worker for RAG indexing jobs"""
    
    def __init__(self, cfg: Optional[Dict] = None):
        self.cfg = cfg or load_cfg()
        self.logger = logging.getLogger(__name__)
        
        # Job tracking
        self.active_jobs: Dict[str, IndexingJob] = {}
        self.job_history: List[IndexingJob] = []
        self.max_history = 100
        
        # Statistics
        self.stats = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_files_processed': 0,
            'total_chunks_processed': 0,
            'average_processing_time': 0.0
        }
        
        # Initialize Celery if available
        self.celery_app = None
        if CELERY_AVAILABLE:
            self._setup_celery()
    
    def _setup_celery(self):
        """Setup Celery application for background processing"""
        try:
            # Get Celery configuration
            celery_cfg = self.cfg.get('workers', {})
            broker_url = celery_cfg.get('broker_url', 'pyamqp://guest@localhost//')
            result_backend = celery_cfg.get('result_backend', 'redis://localhost:6379/0')
            
            # Create Celery app
            self.celery_app = Celery(
                'rag_indexing',
                broker=broker_url,
                backend=result_backend
            )
            
            # Configure Celery
            self.celery_app.conf.update(
                task_serializer='json',
                accept_content=['json'],
                result_serializer='json',
                timezone='UTC',
                enable_utc=True,
                task_track_started=True,
                task_time_limit=1800,  # 30 minutes max
                task_soft_time_limit=1500,  # 25 minutes soft limit
                worker_prefetch_multiplier=1,
                worker_max_tasks_per_child=10,
            )
            
            # Register tasks
            self._register_celery_tasks()
            
            self.logger.info("Celery worker setup completed")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Celery: {e}")
            self.celery_app = None
    
    def _register_celery_tasks(self):
        """Register Celery tasks"""
        if not self.celery_app:
            return
        
        @self.celery_app.task(bind=True, name='rag_indexing.process_file_changes')
        def process_file_changes_task(self, job_data: Dict):
            """Celery task for processing file changes"""
            try:
                # Update task state
                self.update_state(
                    state='PROCESSING',
                    meta={
                        'job_id': job_data['job_id'],
                        'status': 'processing',
                        'progress': 0
                    }
                )
                
                # Create job object
                job = IndexingJob(**job_data)
                
                # Process the job
                result = self._process_job_sync(job)
                
                # Update final state
                self.update_state(
                    state='SUCCESS',
                    meta={
                        'job_id': job.job_id,
                        'status': 'completed',
                        'progress': 100,
                        'result': asdict(result)
                    }
                )
                
                return asdict(result)
                
            except Exception as e:
                self.update_state(
                    state='FAILURE',
                    meta={
                        'job_id': job_data.get('job_id', 'unknown'),
                        'status': 'failed',
                        'error': str(e)
                    }
                )
                raise
    
    def _process_job_sync(self, job: IndexingJob) -> IndexingResult:
        """Process a job synchronously (used by Celery task)"""
        try:
            # Update job status
            job.status = 'processing'
            self.active_jobs[job.job_id] = job
            
            # Get indexer
            indexer = get_incremental_indexer()
            
            # Process files based on job type
            if job.job_type == 'incremental':
                # Process individual file changes
                total_result = IndexingResult(
                    success=True,
                    files_processed=0,
                    chunks_added=0,
                    chunks_updated=0,
                    chunks_removed=0,
                    errors=[],
                    processing_time=0
                )
                
                for file_path in job.files_to_process:
                    # Create a mock event for the file
                    event = FileChangeEvent(
                        event_type='modified',
                        file_path=file_path
                    )
                    
                    result = indexer.process_file_change(event)
                    
                    # Aggregate results
                    total_result.files_processed += result.files_processed
                    total_result.chunks_added += result.chunks_added
                    total_result.chunks_updated += result.chunks_updated
                    total_result.chunks_removed += result.chunks_removed
                    total_result.errors.extend(result.errors)
                    
                    if not result.success:
                        total_result.success = False
                
                job.result = total_result
                
            elif job.job_type == 'full':
                # Full re-indexing (delegate to existing ingest.py logic)
                # This would require importing and calling the main ingest function
                job.result = IndexingResult(
                    success=False,
                    files_processed=0,
                    chunks_added=0,
                    chunks_updated=0,
                    chunks_removed=0,
                    errors=["Full re-indexing not implemented in background worker"],
                    processing_time=0
                )
            
            else:
                job.result = IndexingResult(
                    success=False,
                    files_processed=0,
                    chunks_added=0,
                    chunks_updated=0,
                    chunks_removed=0,
                    errors=[f"Unknown job type: {job.job_type}"],
                    processing_time=0
                )
            
            # Update job status
            job.status = 'completed' if job.result.success else 'failed'
            if not job.result.success:
                job.error_message = '; '.join(job.result.errors)
            
            # Move to history
            self._move_job_to_history(job)
            
            # Update statistics
            self._update_stats(job)
            
            return job.result
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.result = IndexingResult(
                success=False,
                files_processed=0,
                chunks_added=0,
                chunks_updated=0,
                chunks_removed=0,
                errors=[str(e)],
                processing_time=0
            )
            
            self._move_job_to_history(job)
            self._update_stats(job)
            
            return job.result
    
    async def process_file_changes(self, events: List[FileChangeEvent], job_type: str = 'incremental') -> str:
        """Process file changes asynchronously"""
        try:
            # Create job
            job_id = str(uuid.uuid4())
            job = IndexingJob(
                job_id=job_id,
                repository_path=str(Path.cwd().resolve()),
                files_to_process=[event.file_path for event in events],
                job_type=job_type
            )
            
            # Add to active jobs
            self.active_jobs[job_id] = job
            
            if self.celery_app and CELERY_AVAILABLE:
                # Use Celery for background processing
                job_data = asdict(job)
                # Convert datetime to string for JSON serialization
                job_data['created_at'] = job.created_at.isoformat()
                
                task = self.celery_app.send_task(
                    'rag_indexing.process_file_changes',
                    args=[job_data]
                )
                
                self.logger.info(f"Queued indexing job {job_id} with Celery task {task.id}")
                return job_id
                
            else:
                # Fallback to synchronous processing
                self.logger.warning("Celery not available, processing synchronously")
                result = self._process_job_sync(job)
                return job_id
                
        except Exception as e:
            self.logger.error(f"Error processing file changes: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[JobProgress]:
        """Get status of a specific job"""
        job = self.active_jobs.get(job_id)
        if not job:
            # Check history
            for hist_job in self.job_history:
                if hist_job.job_id == job_id:
                    job = hist_job
                    break
        
        if not job:
            return None
        
        # Calculate progress
        progress_percent = 0
        if job.status == 'completed':
            progress_percent = 100
        elif job.status == 'processing':
            progress_percent = 50  # Rough estimate
        elif job.status == 'failed':
            progress_percent = 0
        
        return JobProgress(
            job_id=job.job_id,
            status=job.status,
            progress_percent=progress_percent,
            files_processed=job.result.files_processed if job.result else 0,
            total_files=len(job.files_to_process),
            error_message=job.error_message
        )
    
    def get_all_job_statuses(self) -> List[JobProgress]:
        """Get status of all jobs"""
        statuses = []
        
        # Active jobs
        for job in self.active_jobs.values():
            status = self.get_job_status(job.job_id)
            if status:
                statuses.append(status)
        
        # Recent history
        for job in self.job_history[-10:]:  # Last 10 jobs
            status = self.get_job_status(job.job_id)
            if status:
                statuses.append(status)
        
        return statuses
    
    def _move_job_to_history(self, job: IndexingJob):
        """Move completed job to history"""
        if job.job_id in self.active_jobs:
            del self.active_jobs[job.job_id]
        
        self.job_history.append(job)
        
        # Trim history if too long
        if len(self.job_history) > self.max_history:
            self.job_history = self.job_history[-self.max_history:]
    
    def _update_stats(self, job: IndexingJob):
        """Update worker statistics"""
        self.stats['total_jobs'] += 1
        
        if job.status == 'completed':
            self.stats['completed_jobs'] += 1
            if job.result:
                self.stats['total_files_processed'] += job.result.files_processed
                self.stats['total_chunks_processed'] += (
                    job.result.chunks_added + 
                    job.result.chunks_updated + 
                    job.result.chunks_removed
                )
        elif job.status == 'failed':
            self.stats['failed_jobs'] += 1
        
        # Calculate average processing time
        if job.result and job.result.processing_time > 0:
            total_time = self.stats['average_processing_time'] * (self.stats['total_jobs'] - 1)
            self.stats['average_processing_time'] = (total_time + job.result.processing_time) / self.stats['total_jobs']
    
    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics"""
        return {
            'stats': self.stats.copy(),
            'active_jobs': len(self.active_jobs),
            'celery_available': CELERY_AVAILABLE,
            'celery_configured': self.celery_app is not None
        }
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending or processing job"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.status in ['pending', 'processing']:
                job.status = 'cancelled'
                self._move_job_to_history(job)
                return True
        return False


# Global worker instance
_worker: Optional[RAGIndexingWorker] = None


def get_background_worker() -> RAGIndexingWorker:
    """Get or create global background worker instance"""
    global _worker
    if _worker is None:
        _worker = RAGIndexingWorker()
    return _worker


async def process_file_changes_async(events: List[FileChangeEvent], job_type: str = 'incremental') -> str:
    """Process file changes asynchronously"""
    worker = get_background_worker()
    return await worker.process_file_changes(events, job_type)


def get_job_status(job_id: str) -> Optional[JobProgress]:
    """Get status of a specific job"""
    worker = get_background_worker()
    return worker.get_job_status(job_id)


def get_all_job_statuses() -> List[JobProgress]:
    """Get status of all jobs"""
    worker = get_background_worker()
    return worker.get_all_job_statuses()


def get_worker_stats() -> Dict[str, Any]:
    """Get worker statistics"""
    worker = get_background_worker()
    return worker.get_stats()
