"""
🚀 BACKGROUND FINE-TUNING WORKER
Monitors training jobs and executes fine-tuning automatically.

This worker runs in the background and:
1. Monitors db/training_jobs/ for new batches
2. Triggers fine-tuning when batch reaches threshold (50 examples)
3. Saves fine-tuned models to finetuned_models/
4. Updates model registry for automatic model selection

LAUNCH: python workers/finetuning_worker.py
"""

import sys
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

import os
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [FINETUNING_WORKER] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class FinetuningWorker:
    """Background worker for automatic model fine-tuning"""
    
    def __init__(
        self,
        jobs_dir: str = "db/training_jobs",
        models_dir: str = "finetuned_models",
        registry_path: str = "model_registry.json",
        batch_threshold: int = 50,
        check_interval: int = 60  # seconds
    ):
        self.jobs_dir = Path(jobs_dir)
        self.models_dir = Path(models_dir)
        self.registry_path = Path(registry_path)
        self.batch_threshold = batch_threshold
        self.check_interval = check_interval
        
        # Create directories
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Worker initialized - watching {self.jobs_dir}")
        logger.info(f"Batch threshold: {self.batch_threshold} examples")
        logger.info(f"Check interval: {self.check_interval}s")
    
    def get_pending_jobs(self) -> List[Dict]:
        """Get all pending training jobs"""
        jobs = []
        
        if not self.jobs_dir.exists():
            return jobs
        
        for job_file in self.jobs_dir.glob("*.json"):
            try:
                with open(job_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                
                # Check if job is pending (not processed yet)
                if job_data.get("status") == "pending":
                    job_data["file_path"] = str(job_file)
                    jobs.append(job_data)
            except Exception as e:
                logger.error(f"Error reading job {job_file}: {e}")
        
        return jobs
    
    def check_batch_ready(self, job: Dict) -> bool:
        """Check if training batch has enough examples"""
        examples = job.get("training_examples", [])
        artifact_type = job.get("artifact_type", "unknown")
        
        logger.info(f"Checking batch for {artifact_type}: {len(examples)} examples (threshold: {self.batch_threshold})")
        
        return len(examples) >= self.batch_threshold
    
    def trigger_finetuning(self, job: Dict) -> bool:
        """
        Trigger fine-tuning process.
        
        NOW CREATES SPECIALIZED MODELS PER (artifact_type, model) PAIR:
        - Each pair gets its own fine-tuned model
        - Model name includes both artifact type and base model
        - Registry tracks which fine-tuned model to use for each pair
        
        In production, this would:
        1. Prepare training data in Ollama format
        2. Call Ollama's fine-tuning API
        3. Save fine-tuned model
        4. Update model registry
        
        For now, we simulate the process and update registry.
        """
        artifact_type = job.get("artifact_type", "unknown")
        model_used = job.get("model_used", "codellama:7b-instruct-q4_K_M")
        base_model = job.get("base_model", model_used)  # Fallback to model_used if base_model not set
        examples = job.get("training_examples", [])
        
        logger.info(f"🚀 Starting fine-tuning for ({artifact_type}, {model_used})")
        logger.info(f"Base model: {base_model}")
        logger.info(f"Training examples: {len(examples)}")
        
        try:
            # STEP 1: Prepare training data
            training_data = self._prepare_training_data(examples)
            
            # STEP 2: Create fine-tuned model name (includes artifact type and base model)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize model name for filesystem
            model_slug = model_used.replace(":", "_").replace("/", "_")
            finetuned_model_name = f"{artifact_type}_{model_slug}_ft_{timestamp}"
            
            # STEP 3: Save training data
            training_file = self.models_dir / f"{finetuned_model_name}_training.jsonl"
            with open(training_file, 'w', encoding='utf-8') as f:
                for example in training_data:
                    f.write(json.dumps(example) + '\n')
            
            logger.info(f"✅ Training data saved to {training_file}")
            
            # STEP 4: Trigger Ollama fine-tuning (if available)
            # NOTE: This requires Ollama fine-tuning support
            # For now, we just log that we would trigger it
            logger.info(f"⏳ Fine-tuning would be triggered here...")
            logger.info(f"Command: ollama create {finetuned_model_name} --from {base_model} --training-data {training_file}")
            
            # STEP 5: Update model registry with (artifact_type, base_model) -> fine-tuned model mapping
            self._update_registry_for_pair(artifact_type, model_used, finetuned_model_name, base_model)
            
            # STEP 6: Mark job as completed
            job["status"] = "completed"
            job["finetuned_model"] = finetuned_model_name
            job["completed_at"] = datetime.now().isoformat()
            
            job_file = Path(job["file_path"])
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job, f, indent=2)
            
            logger.info(f"✅ Fine-tuning job completed for ({artifact_type}, {model_used})")
            logger.info(f"Fine-tuned model: {finetuned_model_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Fine-tuning failed: {e}")
            
            # Mark job as failed
            job["status"] = "failed"
            job["error"] = str(e)
            job["failed_at"] = datetime.now().isoformat()
            
            job_file = Path(job["file_path"])
            with open(job_file, 'w') as f:
                json.dump(job, f, indent=2)
            
            return False
    
    def _prepare_training_data(self, examples: List[Dict]) -> List[Dict]:
        """
        Prepare training data in Ollama format.
        
        Format:
        {
            "prompt": "user input",
            "completion": "ai output",
            "system": "system prompt (optional)"
        }
        """
        training_data = []
        
        for example in examples:
            training_example = {
                "prompt": example.get("input", ""),
                "completion": example.get("output", ""),
            }
            
            # Add context if available
            context = example.get("context", {})
            if context:
                training_example["system"] = f"Context: {json.dumps(context)}"
            
            training_data.append(training_example)
        
        return training_data
    
    def _update_registry_for_pair(
        self, 
        artifact_type: str, 
        model_used: str, 
        finetuned_model_name: str, 
        base_model: str
    ):
        """
        Update model registry with fine-tuned model for specific (artifact_type, model) pair.
        
        Registry structure:
        {
            "pairs": {
                "erd:mistral:7b-instruct-q4_K_M": {
                    "finetuned_model": "erd_mistral_7b-instruct-q4_K_M_ft_20250109_123456",
                    "base_model": "mistral:7b-instruct-q4_K_M",
                    "artifact_type": "erd",
                    "created_at": "2025-01-09T12:34:56",
                    "status": "ready"
                }
            }
        }
        """
        # Load existing registry
        if self.registry_path.exists():
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        else:
            registry = {"pairs": {}, "models": {}}  # Keep old "models" for backward compatibility
        
        # Ensure "pairs" key exists
        if "pairs" not in registry:
            registry["pairs"] = {}
        
        # Create pair key
        pair_key = f"{artifact_type}:{model_used}"
        
        # Add fine-tuned model for this pair
        registry["pairs"][pair_key] = {
            "finetuned_model": finetuned_model_name,
            "base_model": base_model,
            "artifact_type": artifact_type,
            "model_used": model_used,
            "created_at": datetime.now().isoformat(),
            "status": "ready"
        }
        
        # Also update old "models" dict for backward compatibility
        if "models" not in registry:
            registry["models"] = {}
        registry["models"][artifact_type] = {
            "finetuned_model": finetuned_model_name,
            "base_model": base_model,
            "created_at": datetime.now().isoformat(),
            "status": "ready"
        }
        
        # Save registry
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)
        
        logger.info(f"✅ Model registry updated: {pair_key} -> {finetuned_model_name}")
    
    def _update_registry(self, artifact_type: str, model_name: str, base_model: str):
        """DEPRECATED: Use _update_registry_for_pair instead"""
        # Fallback for old code paths
        self._update_registry_for_pair(artifact_type, base_model, model_name, base_model)
        
        # Save registry
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2)
        
        logger.info(f"✅ Model registry updated: {artifact_type} -> {model_name}")
    
    def run(self):
        """Main worker loop"""
        logger.info("🚀 Fine-tuning worker started")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                # Check for pending jobs
                jobs = self.get_pending_jobs()
                
                if jobs:
                    logger.info(f"Found {len(jobs)} pending training jobs")
                    
                    for job in jobs:
                        # Check if batch is ready
                        if self.check_batch_ready(job):
                            logger.info(f"Batch ready for {job.get('artifact_type')} - triggering fine-tuning")
                            self.trigger_finetuning(job)
                        else:
                            logger.info(f"Batch not ready yet for {job.get('artifact_type')} - waiting for more examples")
                else:
                    logger.debug("No pending jobs found")
                
                # Sleep before next check
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Worker stopped by user")
        except Exception as e:
            logger.error(f"❌ Worker crashed: {e}")
            raise


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tuning background worker")
    parser.add_argument(
        "--single-job",
        type=str,
        help="Process a single job file and exit (for automatic triggers)"
    )
    args = parser.parse_args()
    
    worker = FinetuningWorker(
        jobs_dir="db/training_jobs",
        models_dir="finetuned_models",
        registry_path="model_registry.json",
        batch_threshold=50,  # Trigger fine-tuning after 50 examples
        check_interval=60    # Check every 60 seconds
    )
    
    if args.single_job:
        # Process single job and exit (automatic trigger mode)
        import json
        from pathlib import Path
        
        job_file = Path(args.single_job)
        if job_file.exists():
            with open(job_file, 'r', encoding='utf-8') as f:
                job = json.load(f)
            
            job["file_path"] = str(job_file)
            
            logger.info(f"🎯 Processing single job: {job.get('job_id')}")
            
            if worker.check_batch_ready(job):
                success = worker.trigger_finetuning(job)
                if success:
                    logger.info(f"✅ Job completed successfully")
                else:
                    logger.error(f"❌ Job failed")
            else:
                logger.info(f"⏳ Batch not ready yet")
        else:
            logger.error(f"❌ Job file not found: {job_file}")
    else:
        # Continuous mode (manual start)
        worker.run()


if __name__ == "__main__":
    main()
