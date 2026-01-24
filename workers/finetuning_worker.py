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
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure main logger
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [FINETUNING_WORKER] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configure error file logger for finetuning errors
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ERROR_LOG_FILE = LOGS_DIR / "finetuning_errors.log"

# Create a separate file handler for errors
error_file_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(error_file_handler)


def log_error_to_file(error_msg: str, traceback_str: str = None):
    """Log detailed error to logs/finetuning_errors.log"""
    try:
        with open(ERROR_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FINE-TUNING ERROR\n")
            f.write(f"{'='*80}\n")
            f.write(f"Error: {error_msg}\n")
            if traceback_str:
                f.write(f"\nFull Traceback:\n{traceback_str}\n")
            f.write(f"{'='*80}\n\n")
    except Exception as e:
        logger.warning(f"Could not write to error log file: {e}")


class FinetuningWorker:
    """Background worker for automatic model fine-tuning"""
    
    def __init__(
        self,
        jobs_dir: str = "db/training_jobs",
        models_dir: str = "finetuned_models",
        adapters_dir: str = "data/adapters",  # LoRA adapters directory
        registry_path: str = "model_registry.json",
        batch_threshold: int = 50,
        check_interval: int = 60  # seconds
    ):
        self.jobs_dir = Path(jobs_dir)
        self.models_dir = Path(models_dir)
        self.adapters_dir = Path(adapters_dir)  # For LoRA adapters
        self.registry_path = Path(registry_path)
        self.batch_threshold = batch_threshold
        self.check_interval = check_interval
        
        # Create directories
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.adapters_dir.mkdir(parents=True, exist_ok=True)  # Ensure adapters dir exists
        
        logger.info(f"Worker initialized - watching {self.jobs_dir}")
        logger.info(f"Batch threshold: {self.batch_threshold} examples")
        logger.info(f"Check interval: {self.check_interval}s")
        logger.info(f"LoRA adapters directory: {self.adapters_dir}")
        logger.info(f"Error log file: {ERROR_LOG_FILE}")
    
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
    
    def get_lora_adapter_path(self, adapter_name: str) -> Optional[Path]:
        """Get the path to a downloaded LoRA adapter.
        
        LoRA adapters are stored in data/adapters/<adapter_name>/
        
        Args:
            adapter_name: Name of the adapter (e.g., 'code-llama-lora-sql')
            
        Returns:
            Path to adapter directory if found, None otherwise
        """
        adapter_path = self.adapters_dir / adapter_name
        if adapter_path.exists():
            # Check for adapter_config.json which indicates a valid LoRA adapter
            if (adapter_path / "adapter_config.json").exists():
                logger.info(f"Found LoRA adapter at {adapter_path}")
                return adapter_path
            # Also check for adapter_model files
            adapter_files = list(adapter_path.glob("adapter_model.*"))
            if adapter_files:
                logger.info(f"Found LoRA adapter at {adapter_path}")
                return adapter_path
        return None
    
    def list_available_adapters(self) -> List[Dict]:
        """List all available LoRA adapters in the adapters directory.
        
        Returns:
            List of adapter info dicts with name, path, and metadata
        """
        adapters = []
        
        if not self.adapters_dir.exists():
            return adapters
        
        for adapter_dir in self.adapters_dir.iterdir():
            if adapter_dir.is_dir():
                adapter_info = {
                    "name": adapter_dir.name,
                    "path": str(adapter_dir),
                    "has_config": (adapter_dir / "adapter_config.json").exists()
                }
                
                # Try to read adapter config for more info
                config_path = adapter_dir / "adapter_config.json"
                if config_path.exists():
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        adapter_info["base_model"] = config.get("base_model_name_or_path")
                        adapter_info["r"] = config.get("r")  # LoRA rank
                        adapter_info["lora_alpha"] = config.get("lora_alpha")
                    except Exception as e:
                        logger.warning(f"Could not read adapter config: {e}")
                
                adapters.append(adapter_info)
        
        logger.info(f"Found {len(adapters)} LoRA adapters in {self.adapters_dir}")
        return adapters
    
    def check_batch_ready(self, job: Dict) -> bool:
        """Check if training batch has enough examples"""
        examples = job.get("training_examples", [])
        artifact_type = job.get("artifact_type", "unknown")
        
        logger.info(f"Checking batch for {artifact_type}: {len(examples)} examples (threshold: {self.batch_threshold})")
        
        return len(examples) >= self.batch_threshold
    
    def _validate_dataset_file(self, dataset_path: Path) -> bool:
        """
        Validate that the dataset JSONL file exists and is readable.
        
        Args:
            dataset_path: Path to the dataset JSONL file
            
        Returns:
            True if valid, False otherwise
        """
        if not dataset_path.exists():
            error_msg = f"Dataset file does not exist: {dataset_path}"
            logger.error(error_msg)
            log_error_to_file(error_msg)
            return False
        
        if not dataset_path.is_file():
            error_msg = f"Dataset path is not a file: {dataset_path}"
            logger.error(error_msg)
            log_error_to_file(error_msg)
            return False
        
        if dataset_path.stat().st_size == 0:
            error_msg = f"Dataset file is empty: {dataset_path}"
            logger.error(error_msg)
            log_error_to_file(error_msg)
            return False
        
        # Try to read and validate JSONL format
        try:
            line_count = 0
            with open(dataset_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line:  # Skip empty lines
                        json.loads(line)  # Validate JSON
                        line_count += 1
            
            if line_count == 0:
                error_msg = f"Dataset file has no valid training examples: {dataset_path}"
                logger.error(error_msg)
                log_error_to_file(error_msg)
                return False
            
            logger.info(f"✅ Dataset validated: {dataset_path} ({line_count} examples)")
            return True
            
        except json.JSONDecodeError as e:
            error_msg = f"Dataset file has invalid JSON at line {line_num}: {e}"
            logger.error(error_msg)
            log_error_to_file(error_msg, traceback.format_exc())
            return False
        except Exception as e:
            error_msg = f"Error reading dataset file {dataset_path}: {e}"
            logger.error(error_msg)
            log_error_to_file(error_msg, traceback.format_exc())
            return False
    
    def _check_bitsandbytes_available(self) -> bool:
        """Check if bitsandbytes is available for 4-bit quantization."""
        try:
            import bitsandbytes
            logger.info("✅ bitsandbytes is available for 4-bit quantization")
            return True
        except ImportError:
            logger.warning("⚠️ bitsandbytes not available - 4-bit quantization disabled")
            return False
    
    def _run_huggingface_training(
        self,
        training_file: Path,
        base_model: str,
        output_dir: Path,
        artifact_type: str
    ) -> Dict[str, Any]:
        """
        Run HuggingFace-based LoRA/QLoRA training with bitsandbytes 4-bit quantization.
        
        This method handles OOM issues on consumer GPUs by:
        1. Using bitsandbytes 4-bit quantization
        2. Using gradient checkpointing
        3. Using LoRA for parameter-efficient fine-tuning
        
        Args:
            training_file: Path to JSONL training file
            base_model: HuggingFace model name (e.g., 'codellama/CodeLlama-7b-Instruct-hf')
            output_dir: Directory to save the fine-tuned model
            artifact_type: Type of artifact being trained for
            
        Returns:
            Dict with success status and model info
        """
        result = {"success": False, "error": None, "model_path": None}
        
        try:
            logger.info(f"🚀 Starting HuggingFace training with bitsandbytes 4-bit quantization")
            logger.info(f"Base model: {base_model}")
            logger.info(f"Training file: {training_file}")
            logger.info(f"Output dir: {output_dir}")
            
            # Import required libraries
            import torch
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                TrainingArguments,
                Trainer,
                BitsAndBytesConfig
            )
            from peft import (
                LoraConfig,
                get_peft_model,
                prepare_model_for_kbit_training,
                TaskType
            )
            from datasets import load_dataset
            
            # Check CUDA availability
            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA not available. HuggingFace training requires a GPU. "
                    "Use Ollama-based training for CPU-only environments."
                )
            
            logger.info(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
            logger.info(f"✅ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
            
            # CRITICAL: Configure 4-bit quantization using bitsandbytes to prevent OOM
            logger.info("📦 Configuring 4-bit quantization (bitsandbytes)...")
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True  # Nested quantization for memory savings
            )
            
            # Load tokenizer
            logger.info(f"📦 Loading tokenizer from {base_model}...")
            tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Load model with 4-bit quantization
            logger.info(f"📦 Loading model with 4-bit quantization...")
            model = AutoModelForCausalLM.from_pretrained(
                base_model,
                quantization_config=quantization_config,
                device_map="auto",
                trust_remote_code=True
            )
            
            # Prepare model for k-bit training
            logger.info("📦 Preparing model for 4-bit training...")
            model.gradient_checkpointing_enable()
            model = prepare_model_for_kbit_training(model)
            
            # Configure LoRA
            logger.info("📦 Configuring LoRA adapter...")
            lora_config = LoraConfig(
                r=16,  # LoRA rank
                lora_alpha=32,
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
                lora_dropout=0.05,
                bias="none",
                task_type=TaskType.CAUSAL_LM
            )
            
            # Apply LoRA to model
            model = get_peft_model(model, lora_config)
            model.print_trainable_parameters()
            
            # Load and prepare dataset
            logger.info(f"📦 Loading dataset from {training_file}...")
            dataset = load_dataset("json", data_files=str(training_file), split="train")
            
            # Tokenize dataset
            def tokenize_function(examples):
                # Format as instruction-following
                texts = []
                for prompt, completion in zip(examples.get("prompt", []), examples.get("completion", [])):
                    text = f"<s>[INST] {prompt} [/INST] {completion} </s>"
                    texts.append(text)
                
                tokenized = tokenizer(
                    texts,
                    truncation=True,
                    padding="max_length",
                    max_length=512,
                    return_tensors=None
                )
                tokenized["labels"] = tokenized["input_ids"].copy()
                return tokenized
            
            logger.info("📦 Tokenizing dataset...")
            tokenized_dataset = dataset.map(
                tokenize_function,
                batched=True,
                remove_columns=dataset.column_names
            )
            
            # Training arguments optimized for consumer GPUs
            logger.info("📦 Setting up training arguments...")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            training_args = TrainingArguments(
                output_dir=str(output_dir),
                num_train_epochs=3,
                per_device_train_batch_size=1,  # Small batch size for memory
                gradient_accumulation_steps=8,  # Accumulate to simulate larger batch
                learning_rate=2e-4,
                fp16=True,
                logging_steps=10,
                save_steps=100,
                save_total_limit=2,
                gradient_checkpointing=False,  # Already enabled manually
                max_grad_norm=0.3,
                warmup_ratio=0.03,
                lr_scheduler_type="cosine",
                report_to=None,  # Disable wandb/tensorboard
                optim="paged_adamw_8bit",  # Memory-efficient optimizer
            )
            
            # Create trainer
            logger.info("📦 Creating trainer...")
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                tokenizer=tokenizer,
            )
            
            # CRITICAL: Wrap trainer.train() with robust error handling
            logger.info("🚀 Starting training...")
            train_start = time.time()
            
            try:
                train_result = trainer.train()
                training_time = time.time() - train_start
                logger.info(f"✅ Training completed in {training_time:.1f}s")
                logger.info(f"✅ Final loss: {train_result.training_loss:.4f}")
                
                # Save the model
                logger.info(f"💾 Saving model to {output_dir}...")
                trainer.save_model(str(output_dir))
                tokenizer.save_pretrained(str(output_dir))
                
                result["success"] = True
                result["model_path"] = str(output_dir)
                result["final_loss"] = train_result.training_loss
                result["training_time"] = training_time
                
            except torch.cuda.OutOfMemoryError as oom_error:
                error_msg = (
                    f"CUDA Out of Memory during training. "
                    f"Try reducing batch_size or max_length. "
                    f"Current GPU: {torch.cuda.get_device_name(0)}, "
                    f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
                )
                logger.error(f"❌ {error_msg}")
                log_error_to_file(error_msg, traceback.format_exc())
                result["error"] = error_msg
                raise
                
        except ImportError as e:
            error_msg = f"Missing required library for HuggingFace training: {e}"
            logger.error(f"❌ {error_msg}")
            log_error_to_file(error_msg, traceback.format_exc())
            result["error"] = error_msg
            
        except Exception as e:
            error_msg = f"HuggingFace training failed: {e}"
            logger.error(f"❌ {error_msg}")
            log_error_to_file(error_msg, traceback.format_exc())
            result["error"] = str(e)
        
        finally:
            # Clean up GPU memory
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("🧹 GPU memory cleared")
            except Exception:
                pass
        
        return result
    
    def trigger_finetuning(self, job: Dict) -> bool:
        """
        Trigger fine-tuning process.
        
        NOW CREATES SPECIALIZED MODELS PER (artifact_type, model) PAIR:
        - Each pair gets its own fine-tuned model
        - Model name includes both artifact type and base model
        - Registry tracks which fine-tuned model to use for each pair
        
        Supports two training modes:
        1. Ollama Modelfile approach (no GPU required)
        2. HuggingFace LoRA/QLoRA with bitsandbytes (GPU required)
        """
        artifact_type = job.get("artifact_type", "unknown")
        model_used = job.get("model_used", "codellama:7b-instruct-q4_K_M")
        base_model = job.get("base_model", model_used)  # Fallback to model_used if base_model not set
        examples = job.get("training_examples", [])
        use_huggingface = job.get("use_huggingface", False)  # Flag to use HF training
        
        logger.info(f"🚀 Starting fine-tuning for ({artifact_type}, {model_used})")
        logger.info(f"Base model: {base_model}")
        logger.info(f"Training examples: {len(examples)}")
        logger.info(f"Training mode: {'HuggingFace LoRA' if use_huggingface else 'Ollama Modelfile'}")
        
        try:
            # STEP 1: Prepare training data
            training_data = self._prepare_training_data(examples)
            
            # STEP 2: Create fine-tuned model name (includes artifact type and base model)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize model name for filesystem
            model_slug = model_used.replace(":", "_").replace("/", "_")
            finetuned_model_name = f"{artifact_type}_{model_slug}_ft_{timestamp}"
            
            # STEP 3: Save training data to JSONL file
            training_file = self.models_dir / f"{finetuned_model_name}_training.jsonl"
            with open(training_file, 'w', encoding='utf-8') as f:
                for example in training_data:
                    f.write(json.dumps(example) + '\n')
            
            logger.info(f"✅ Training data saved to {training_file}")
            
            # STEP 4: Validate the dataset file before proceeding
            if not self._validate_dataset_file(training_file):
                raise ValueError(f"Dataset validation failed for {training_file}")
            
            # STEP 5: Choose training method based on job configuration
            if use_huggingface and "/" in base_model:
                # HuggingFace model path detected - use LoRA/QLoRA training
                logger.info("🔧 Using HuggingFace LoRA training with bitsandbytes 4-bit quantization")
                
                # Check if bitsandbytes is available
                if not self._check_bitsandbytes_available():
                    raise RuntimeError(
                        "bitsandbytes not available. Install with: pip install bitsandbytes\n"
                        "On Windows, use: pip install bitsandbytes-windows or use WSL2"
                    )
                
                output_dir = self.models_dir / finetuned_model_name
                hf_result = self._run_huggingface_training(
                    training_file=training_file,
                    base_model=base_model,
                    output_dir=output_dir,
                    artifact_type=artifact_type
                )
                
                if not hf_result["success"]:
                    raise RuntimeError(f"HuggingFace training failed: {hf_result['error']}")
                
                logger.info(f"✅ HuggingFace model trained successfully: {hf_result['model_path']}")
                
            else:
                # Ollama model - use Modelfile approach
                logger.info(f"🚀 Creating Ollama fine-tuned model: {finetuned_model_name}")
                logger.info(f"Base model (must be Ollama format): {base_model}")
                
                try:
                    from components.ollama_finetuning import ollama_finetuner
                    
                    # Verify base_model is an Ollama model (not HuggingFace)
                    if "/" in base_model and ":" not in base_model:
                        logger.warning(f"⚠️ Base model '{base_model}' looks like HuggingFace format.")
                        logger.warning(f"⚠️ Ollama fine-tuning requires Ollama models (e.g., 'llama3:8b').")
                        logger.warning(f"⚠️ Set 'use_huggingface: true' in job config for HF models.")
                    
                    # Convert training data to examples format for Ollama fine-tuning
                    ollama_examples = []
                    for example in training_data:
                        ollama_examples.append({
                            "question": example.get("prompt", ""),
                            "answer": example.get("completion", "")
                        })
                    
                    # Create Modelfile and build model
                    modelfile_path = ollama_finetuner.create_modelfile(
                        base_model=base_model,
                        examples=ollama_examples,
                        custom_name=finetuned_model_name,
                        artifact_type=artifact_type
                    )
                    
                    # Build the actual Ollama model with error handling
                    try:
                        success = ollama_finetuner.build_custom_model(
                            modelfile_path=modelfile_path,
                            custom_name=finetuned_model_name
                        )
                        
                        if not success:
                            raise RuntimeError("Failed to build Ollama model - build_custom_model returned False")
                            
                    except Exception as build_error:
                        error_msg = f"Ollama model build failed: {build_error}"
                        logger.error(f"❌ {error_msg}")
                        log_error_to_file(error_msg, traceback.format_exc())
                        raise
                    
                    logger.info(f"✅ Ollama model created successfully: {finetuned_model_name}")
                    
                except ImportError as e:
                    error_msg = f"Ollama fine-tuning module not available: {e}"
                    logger.error(f"❌ {error_msg}")
                    log_error_to_file(error_msg, traceback.format_exc())
                    raise RuntimeError(error_msg)
            
            # STEP 6: Register model in ModelService so it appears in UI
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from backend.services.model_service import get_service
                
                model_service = get_service()
                model_id = f"ollama:{finetuned_model_name}"
                
                # Register in ModelService
                from backend.models.dto import ModelInfoDTO
                model_service.models[model_id] = ModelInfoDTO(
                    id=model_id,
                    name=f"{finetuned_model_name} (Fine-tuned)",
                    provider="ollama",
                    status="available",
                    is_trained=True,
                    metadata={
                        "artifact_type": artifact_type,
                        "base_model": base_model,
                        "created_at": datetime.now().isoformat()
                    }
                )
                model_service._save_registry()
                logger.info(f"✅ Model registered in ModelService: {model_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to register model in ModelService: {e}")
            
            # STEP 7: Update model registry with (artifact_type, base_model) -> fine-tuned model mapping
            self._update_registry_for_pair(artifact_type, model_used, finetuned_model_name, base_model)
            
            # STEP 8: Update routing to use fine-tuned model for this artifact type
            try:
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from backend.services.model_service import get_service
                from backend.models.dto import ModelRoutingDTO, ArtifactType
                
                model_service = get_service()
                
                # Try to find matching artifact type
                artifact_type_enum = None
                for at in ArtifactType:
                    if at.value.lower() == artifact_type.lower().replace("-", "_"):
                        artifact_type_enum = at
                        break
                
                if artifact_type_enum:
                    # Get or create routing
                    routing = model_service.get_routing_for_artifact(artifact_type_enum)
                    if not routing:
                        routing = ModelRoutingDTO(
                            artifact_type=artifact_type_enum,
                            primary_model=f"ollama:{finetuned_model_name}",
                            fallback_models=[f"ollama:{base_model}"],
                            enabled=True
                        )
                    else:
                        # CRITICAL: Set fine-tuned model as PRIMARY (first in list)
                        routing.primary_model = f"ollama:{finetuned_model_name}"
                        # Add base model as first fallback if not already present
                        if f"ollama:{base_model}" not in routing.fallback_models:
                            routing.fallback_models.insert(0, f"ollama:{base_model}")
                    
                    model_service.update_routing([routing])
                    logger.info(f"✅ Routing updated for {artifact_type} to use {finetuned_model_name} as PRIMARY")
                else:
                    logger.warning(f"⚠️ Could not find ArtifactType enum for {artifact_type}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to update routing: {e}")
                log_error_to_file(f"Failed to update routing: {e}", traceback.format_exc())
            
            # STEP 9: Mark job as completed
            job["status"] = "completed"
            job["finetuned_model"] = finetuned_model_name
            job["completed_at"] = datetime.now().isoformat()
            
            job_file = Path(job["file_path"])
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job, f, indent=2)
            
            logger.info(f"✅ Fine-tuning job completed for ({artifact_type}, {model_used})")
            logger.info(f"Fine-tuned model: {finetuned_model_name}")
            logger.info(f"🎯 Model is now available in UI and mapped to {artifact_type} artifacts")
            
            return True
            
        except Exception as e:
            error_msg = f"Fine-tuning failed for ({artifact_type}, {model_used}): {e}"
            logger.error(f"❌ {error_msg}")
            
            # Log detailed traceback to error file
            full_traceback = traceback.format_exc()
            log_error_to_file(error_msg, full_traceback)
            
            # Also print traceback to console for debugging
            logger.error(f"Full traceback:\n{full_traceback}")
            
            # Mark job as failed
            job["status"] = "failed"
            job["error"] = str(e)
            job["error_traceback"] = full_traceback
            job["failed_at"] = datetime.now().isoformat()
            
            job_file = Path(job["file_path"])
            with open(job_file, 'w', encoding='utf-8') as f:
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
    
    def run(self):
        """Main worker loop"""
        logger.info("🚀 Fine-tuning worker started")
        logger.info("Press Ctrl+C to stop")
        logger.info(f"📋 Error log: {ERROR_LOG_FILE}")
        
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
            error_msg = f"Worker crashed: {e}"
            logger.error(f"❌ {error_msg}")
            log_error_to_file(error_msg, traceback.format_exc())
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
    parser.add_argument(
        "--dataset",
        type=str,
        help="Path to a specific dataset JSONL file to validate before training"
    )
    args = parser.parse_args()
    
    worker = FinetuningWorker(
        jobs_dir="db/training_jobs",
        models_dir="finetuned_models",
        registry_path="model_registry.json",
        batch_threshold=10,  # Trigger fine-tuning after 10 examples (lowered from 50)
        check_interval=60    # Check every 60 seconds
    )
    
    # If dataset path provided, validate it first
    if args.dataset:
        dataset_path = Path(args.dataset)
        if worker._validate_dataset_file(dataset_path):
            logger.info(f"✅ Dataset validation passed: {dataset_path}")
        else:
            logger.error(f"❌ Dataset validation failed: {dataset_path}")
            sys.exit(1)
    
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
                    logger.error(f"❌ Job failed - check {ERROR_LOG_FILE} for details")
                    sys.exit(1)
            else:
                logger.info(f"⏳ Batch not ready yet")
        else:
            error_msg = f"Job file not found: {job_file}"
            logger.error(f"❌ {error_msg}")
            log_error_to_file(error_msg)
            sys.exit(1)
    else:
        # Continuous mode (manual start)
        worker.run()


if __name__ == "__main__":
    main()
