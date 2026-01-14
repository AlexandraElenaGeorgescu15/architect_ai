"""
Persistent Training Manager

Handles fine-tuning processes that survive app refreshes and restarts.
Uses file-based status tracking and process management.
"""

import json
import time
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class PersistentTrainingJob:
    """Represents a training job that can survive app restarts"""
    job_id: str
    model_name: str
    status: str  # "pending", "running", "completed", "failed"
    started_at: str
    config: Dict
    training_data_count: int
    progress: float = 0.0
    error_message: str = ""
    model_path: str = ""
    final_loss: float = 0.0
    epochs_completed: int = 0

class PersistentTrainingManager:
    """Manages training jobs that persist across app restarts"""
    
    def __init__(self):
        self.jobs_dir = Path("training_jobs")
        self.jobs_dir.mkdir(exist_ok=True)
        self.active_jobs: Dict[str, PersistentTrainingJob] = {}
        self._load_existing_jobs()
    
    def _load_existing_jobs(self):
        """Load existing training jobs from disk"""
        try:
            for job_file in self.jobs_dir.glob("*.json"):
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    job = PersistentTrainingJob(**job_data)
                    self.active_jobs[job.job_id] = job
                    logger.info(f"Loaded existing job: {job.job_id} - {job.status}")
        except Exception as e:
            logger.error(f"Error loading existing jobs: {e}")
    
    def start_training_job(self, model_name: str, config: Dict, training_data: List) -> str:
        """Start a new persistent training job"""
        
        # Check if training is already running
        try:
            from .local_finetuning import local_finetuning_system
            if local_finetuning_system.is_training():
                logger.warning("Training is already running. Cannot start new training job.")
                raise Exception("Training is already running. Please wait for current training to complete.")
        except Exception as e:
            logger.error(f"Error checking training status: {e}")
        
        job_id = f"{model_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        job = PersistentTrainingJob(
            job_id=job_id,
            model_name=model_name,
            status="pending",
            started_at=datetime.now().isoformat(),
            config=config,
            training_data_count=len(training_data)
        )
        
        self.active_jobs[job_id] = job
        self._save_job(job)
        
        # Start training in background thread
        thread = threading.Thread(
            target=self._run_training_job,
            args=(job_id, training_data),
            daemon=False  # Non-daemon thread to keep running
        )
        thread.start()
        
        logger.info(f"Started persistent training job: {job_id}")
        return job_id
    
    def _run_training_job(self, job_id: str, training_data: List):
        """Run a training job (this runs in a separate thread)"""
        try:
            job = self.active_jobs[job_id]
            job.status = "running"
            self._save_job(job)
            
            logger.info(f"Training job {job_id} starting...")
            
            # Import training system
            from .local_finetuning import local_finetuning_system, TrainingConfig
            
            # Create training config from job config
            config = TrainingConfig(**job.config)
            
            # USE THE GLOBAL local_finetuning_system (already has model loaded)
            # No need to load again - it's already loaded in the UI thread
            
            logger.info(f"Starting training for {job.model_name} with {len(training_data)} examples...")
            
            # Start training
            local_finetuning_system.start_training(config, training_data)
            
            logger.info(f"Training started successfully for {job_id}")
            
            # Wait for training to complete
            while not local_finetuning_system.is_training_complete():
                time.sleep(30)  # Check every 30 seconds
                # Update progress (simplified)
                job.progress = min(job.progress + 0.1, 0.9)
                self._save_job(job)
                logger.info(f"Training progress for {job_id}: {job.progress:.1%}")
            
            # Get training result
            result = local_finetuning_system.get_training_result()
            if result and result.success:
                job.status = "completed"
                job.model_path = result.model_path
                job.final_loss = result.final_loss
                job.epochs_completed = result.epochs_completed
                job.progress = 1.0
                
                # Register model metadata for future sessions
                self._register_finetuned_model(job)
                
                logger.info(f"Training job {job_id} completed successfully and registered in model registry")
            else:
                job.status = "failed"
                job.error_message = result.error_message if result else "Unknown error"
                logger.error(f"Training job {job_id} failed: {job.error_message}")
            
            self._save_job(job)
            
        except Exception as e:
            logger.error(f"Training job {job_id} failed with exception: {e}")
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job.status = "failed"
                job.error_message = str(e)
                self._save_job(job)
    
    def _register_finetuned_model(self, job: PersistentTrainingJob):
        """Register a completed fine-tuned model"""
        try:
            from .local_finetuning import local_finetuning_system, TrainingConfig

            if not job.model_path:
                logger.error("Training job missing model path; skipping registration")
                return

            save_dir = Path(job.model_path)
            if not save_dir.exists():
                logger.error(f"Model path does not exist: {save_dir}")
                return

            try:
                config = TrainingConfig(**job.config)
            except Exception:
                # Fallback to dataclass-compatible payload if reconstruction fails
                config = job.config

            local_finetuning_system._persist_trained_model_metadata(
                base_model=config.model_name if hasattr(config, "model_name") else job.model_name.lower().replace(" ", "-"),
                version_name=save_dir.name,
                save_dir=save_dir,
                config=config,
                training_loss=job.final_loss,
                epochs_completed=job.epochs_completed,
                model_identifier=job.job_id,
            )

            logger.info(f"Registered fine-tuned model: {job.job_id}")

        except Exception as e:
            logger.error(f"Failed to register model: {e}")
    
    def _save_job(self, job: PersistentTrainingJob):
        """Save job status to disk"""
        try:
            job_file = self.jobs_dir / f"{job.job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(asdict(job), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job {job.job_id}: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[PersistentTrainingJob]:
        """Get status of a training job"""
        return self.active_jobs.get(job_id)
    
    def get_all_jobs(self) -> List[PersistentTrainingJob]:
        """Get all training jobs"""
        return list(self.active_jobs.values())
    
    def get_active_jobs(self) -> List[PersistentTrainingJob]:
        """Get only jobs that are actually interrupted (not currently running)"""
        active_jobs = []
        
        # Check if there's currently a training process running
        try:
            from .local_finetuning import local_finetuning_system
            is_currently_training = local_finetuning_system.is_training()
        except (ImportError, AttributeError):
            is_currently_training = False
        
        for job in self.active_jobs.values():
            if job.status in ["pending", "running"]:
                # Only consider it interrupted if:
                # 1. It's pending (never started)
                # 2. It's marked as running but no training is currently active
                if job.status == "pending":
                    active_jobs.append(job)
                elif job.status == "running" and not is_currently_training:
                    # This job was running but training stopped, so it's interrupted
                    active_jobs.append(job)
        
        return active_jobs
    
    def resume_training_job(self, job_id: str) -> bool:
        """Resume a training job from checkpoint after system restart"""
        try:
            job = self.active_jobs.get(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            if job.status not in ["running", "pending"]:
                logger.error(f"Job {job_id} is not in resumable state: {job.status}")
                return False
            
            logger.info(f"Resuming training job: {job_id}")
            
            # Mark as running
            job.status = "running"
            self._save_job(job)
            
            # Get training data (we need to regenerate this)
            from .local_finetuning import local_finetuning_system
            
            # Prepare training data using the same method as the original training
            training_data = local_finetuning_system.prepare_training_data(
                rag_context="repository patterns conventions code style architecture",
                meeting_notes="Fine-tune on repository codebase",
                unlimited=True  # Use all available chunks
            )
            
            # Start training in background thread
            thread = threading.Thread(
                target=self._resume_training_job,
                args=(job_id, training_data),
                daemon=False
            )
            thread.start()
            
            logger.info(f"Resumed training job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _resume_training_job(self, job_id: str, training_data: List):
        """Resume a training job from checkpoint"""
        try:
            job = self.active_jobs[job_id]
            logger.info(f"Resuming training job {job_id} from checkpoint...")
            
            # Import training system
            from .local_finetuning import local_finetuning_system, TrainingConfig
            
            # Create training config from job config
            config = TrainingConfig(**job.config)
            
            # Load the model first - use the correct model key
            model_name = config.model_name
            # Convert from "models/codellama-7b" to "codellama-7b" if needed
            if model_name.startswith("models/"):
                model_key = model_name.replace("models/", "")
            else:
                model_key = model_name
            local_finetuning_system.load_model(model_key)
            
            # Check if checkpoints exist
            checkpoint_dir = Path(f"./finetuned_models/{config.model_name}")
            checkpoints = list(checkpoint_dir.glob("checkpoint-*")) if checkpoint_dir.exists() else []
            
            if checkpoints:
                # Get the latest checkpoint to show which step we're resuming from
                latest_checkpoint = max(checkpoints, key=lambda x: int(x.name.split('-')[1]))
                checkpoint_step = int(latest_checkpoint.name.split('-')[1])
                logger.info(f"Resuming from checkpoint step {checkpoint_step}")
                
                # Calculate approximate progress from checkpoint
                # Assuming save_steps=100 and typical training is ~180 steps
                estimated_total_steps = (config.epochs * len(training_data)) // config.batch_size
                checkpoint_progress = min(checkpoint_step / estimated_total_steps, 0.95)
                job.progress = checkpoint_progress
                self._save_job(job)
                
                # Resume from checkpoint
                success = local_finetuning_system.resume_training_from_checkpoint(config, training_data, job_id)
            else:
                # No checkpoints available, start fresh training
                logger.info(f"No checkpoints found for {job_id}, starting fresh training")
                job.progress = 0.0
                self._save_job(job)
                success = local_finetuning_system.start_training(config, training_data)
            
            if success:
                logger.info(f"Successfully resumed training for {job_id}")
                
                # Wait for training to complete
                progress_updates = 0
                while not local_finetuning_system.is_training_complete():
                    time.sleep(30)
                    # Update progress more accurately
                    progress_updates += 1
                    # Increment from current progress towards 95%
                    remaining = 0.95 - job.progress
                    job.progress = min(job.progress + (remaining * 0.1), 0.95)
                    self._save_job(job)
                    logger.info(f"Resumed training progress for {job_id}: {job.progress:.1%} (update #{progress_updates})")
                
                # Get training result
                result = local_finetuning_system.get_training_result()
                if result and result.success:
                    job.status = "completed"
                    job.final_loss = result.final_loss
                    job.epochs_completed = result.epochs_completed
                    job.model_path = result.model_path
                    self._save_job(job)
                    self._register_finetuned_model(job)
                    logger.info(f"Training completed successfully for {job_id}")
                else:
                    job.status = "failed"
                    job.error_message = result.error_message if result else "Unknown error"
                    self._save_job(job)
                    logger.error(f"Training failed for {job_id}: {job.error_message}")
            else:
                job.status = "failed"
                job.error_message = "Failed to resume from checkpoint"
                self._save_job(job)
                logger.error(f"Failed to resume training for {job_id}")
                
        except Exception as e:
            job = self.active_jobs[job_id]
            job.status = "failed"
            job.error_message = str(e)
            self._save_job(job)
            logger.error(f"Error resuming training job {job_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def auto_resume_interrupted_jobs(self):
        """Automatically resume jobs that were interrupted by system restart"""
        interrupted_jobs = [job for job in self.active_jobs.values() 
                           if job.status in ["running", "pending"]]
        
        # Only resume ONE job at a time to prevent resource conflicts
        if interrupted_jobs:
            job = interrupted_jobs[0]  # Take only the first job
            logger.info(f"Found interrupted job: {job.job_id}, attempting to resume...")
            logger.info(f"Skipping {len(interrupted_jobs) - 1} other jobs to prevent conflicts")
            self.resume_training_job(job.job_id)
    
    def cleanup_completed_jobs(self, days_old: int = 7):
        """Clean up old completed/failed jobs"""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        
        jobs_to_remove = []
        for job_id, job in self.active_jobs.items():
            if job.status in ["completed", "failed"]:
                job_time = datetime.fromisoformat(job.started_at).timestamp()
                if job_time < cutoff_date:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            # Remove from memory
            del self.active_jobs[job_id]
            # Remove from disk
            job_file = self.jobs_dir / f"{job_id}.json"
            if job_file.exists():
                job_file.unlink()
            logger.info(f"Cleaned up old job: {job_id}")

# Global instance
persistent_training_manager = PersistentTrainingManager()
