"""
Local Fine-Tuning System with LoRA/QLoRA
Provides local model fine-tuning with model selection and training management
"""

import streamlit as st
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
import psutil
from datetime import datetime
import threading
import queue

from .finetuning_dataset_builder import FineTuningDatasetBuilder, DatasetReport
from .finetuning_feedback import feedback_store, FeedbackEntry


@dataclass
class ModelInfo:
    """Information about a local model"""
    name: str
    size: str
    capability: str
    ram_required: int
    download_url: str
    is_downloaded: bool
    is_loaded: bool
    fine_tuned_versions: List[str]


@dataclass
class TrainingConfig:
    """Configuration for fine-tuning"""
    model_name: str
    epochs: int
    learning_rate: float
    batch_size: int
    lora_rank: int
    lora_alpha: int
    lora_dropout: float
    use_4bit: bool
    use_8bit: bool
    max_length: int


@dataclass
class TrainingProgress:
    """Training progress information"""
    epoch: int
    total_epochs: int
    step: int
    total_steps: int
    loss: float
    learning_rate: float
    eta: float
    status: str


@dataclass
class TrainingResult:
    """Result of fine-tuning"""
    success: bool
    model_path: str
    final_loss: float
    training_time: float
    epochs_completed: int
    error_message: str


class LocalFineTuningSystem:
    """Local fine-tuning system with LoRA/QLoRA support"""
    
    def __init__(self):
        self.available_models = {
            "codellama-7b": ModelInfo(
                name="CodeLlama 7B",
                size="13GB",
                capability="Excellent for code generation",
                ram_required=16,
                download_url="codellama/CodeLlama-7b-Instruct-hf",
                is_downloaded=False,
                is_loaded=False,
                fine_tuned_versions=[]
            ),
            "llama3-8b": ModelInfo(
                name="Llama 3 8B",
                size="16GB",
                capability="Great for general tasks",
                ram_required=20,
                download_url="meta-llama/Meta-Llama-3-8B-Instruct",
                is_downloaded=False,
                is_loaded=False,
                fine_tuned_versions=[]
            ),
            "mistral-7b": ModelInfo(
                name="Mistral 7B",
                size="14GB",
                capability="Fast and efficient",
                ram_required=16,
                download_url="mistralai/Mistral-7B-Instruct-v0.2",
                is_downloaded=False,
                is_loaded=False,
                fine_tuned_versions=[]
            ),
            "deepseek-coder-6.7b": ModelInfo(
                name="DeepSeek Coder 6.7B",
                size="12GB",
                capability="Specialized for coding",
                ram_required=14,
                download_url="deepseek-ai/deepseek-coder-6.7b-instruct",
                is_downloaded=False,
                is_loaded=False,
                fine_tuned_versions=[]
            )
        }
        
        self.current_model = None
        self.training_queue = queue.Queue()
        self.training_thread = None
        self.training_progress = None
        self.training_result = None
        self.last_dataset_report: Optional[DatasetReport] = None
        self.last_training_examples: List[Dict[str, str]] = []
        
        # Thread safety for shared state
        self._state_lock = threading.Lock()
        self._stop_training = threading.Event()  # Signal to stop training gracefully
        
        # Check downloaded models
        self._scan_downloaded_models()
    
    def _scan_downloaded_models(self):
        """Scan for downloaded models"""
        models_dir = Path("models")
        if models_dir.exists():
            for model_key, model_info in self.available_models.items():
                model_path = models_dir / model_key
                if model_path.exists():
                    model_info.is_downloaded = True
                    
                    # Check for fine-tuned versions
                    finetuned_dir = Path("finetuned_models") / model_key
                    if finetuned_dir.exists():
                        model_info.fine_tuned_versions = [
                            d.name for d in finetuned_dir.iterdir() if d.is_dir()
                        ]
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for model compatibility"""
        return {
            "ram_gb": psutil.virtual_memory().total / (1024**3),
            "cpu_count": psutil.cpu_count(),
            "disk_free_gb": psutil.disk_usage('/').free / (1024**3),
            "python_version": "3.8+",
            "cuda_available": self._check_cuda_availability()
        }
    
    def _check_cuda_availability(self) -> bool:
        """Check if CUDA is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    def can_download_model(self, model_key: str) -> Tuple[bool, str]:
        """Check if a model can be downloaded"""
        model_info = self.available_models[model_key]
        system_info = self.get_system_info()
        
        if model_info.is_downloaded:
            return False, "Model already downloaded"
        
        if system_info["ram_gb"] < model_info.ram_required:
            return False, f"Insufficient RAM. Need {model_info.ram_required}GB, have {system_info['ram_gb']:.1f}GB"
        
        if system_info["disk_free_gb"] < 20:  # Need at least 20GB free
            return False, f"Insufficient disk space. Need 20GB, have {system_info['disk_free_gb']:.1f}GB"
        
        return True, "Model can be downloaded"
    
    async def download_model(self, model_key: str, progress_callback=None) -> bool:
        """Download a model with progress tracking"""
        try:
            model_info = self.available_models[model_key]
            
            # Check if already downloaded
            if model_info.is_downloaded:
                return True
            
            # Check system requirements
            can_download, reason = self.can_download_model(model_key)
            if not can_download:
                raise Exception(reason)
            
            # Download using huggingface_hub
            from huggingface_hub import snapshot_download
            
            models_dir = Path("models")
            models_dir.mkdir(exist_ok=True)
            
            # snapshot_download doesn't support progress_callback in older versions
            # Just download without callback
            snapshot_download(
                repo_id=model_info.download_url,
                local_dir=str(models_dir / model_key),
                allow_patterns=["*.safetensors", "*.bin", "*.json", "*.model"],
                ignore_patterns=["*.msgpack", "*.h5"]
            )
            
            # Update model info
            model_info.is_downloaded = True
            self._scan_downloaded_models()
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to download model: {str(e)}")
    
    def load_model(self, model_key: str) -> bool:
        """Load a model for inference/fine-tuning"""
        try:
            model_info = self.available_models[model_key]
            
            if not model_info.is_downloaded:
                raise Exception("Model not downloaded")
            
            # Load model using transformers
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            model_path = Path("models") / model_key
            
            # Check if CUDA is available
            cuda_available = torch.cuda.is_available()
            
            print(f"[DEBUG] Loading model from {model_path}")
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Load model with appropriate settings based on hardware
            if cuda_available:
                # GPU available - use 4-bit quantization
                print("[DEBUG] Loading with 4-bit quantization (GPU)")
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    quantization_config=quantization_config,
                    device_map="auto"
                )
            else:
                # CPU only - load without quantization
                print("[DEBUG] Loading on CPU (no quantization)")
                model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
            
            tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            
            # Fix padding token for CodeLlama
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Store loaded model
            self.current_model = {
                'model': model,
                'tokenizer': tokenizer,
                'key': model_key,
                'info': model_info,
                'cuda_available': cuda_available
            }
            
            # Update model info
            model_info.is_loaded = True
            
            print(f"[DEBUG] Model loaded successfully!")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load model: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to load model: {str(e)}")
    
    def unload_model(self):
        """Unload the current model"""
        if self.current_model:
            # Clear model from memory
            del self.current_model['model']
            del self.current_model['tokenizer']
            
            # Update model info
            self.current_model['info'].is_loaded = False
            
            self.current_model = None
    
    def prepare_training_data(
        self,
        rag_context: str,
        meeting_notes: str = "",
        unlimited: bool = True,
        preview_limit: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Prepare training data using the enhanced dataset builder."""

        combined_notes = meeting_notes.strip()
        if rag_context:
            combined_notes = f"{combined_notes}\n{rag_context}" if combined_notes else rag_context

        max_chunks = 500 if unlimited else 150
        builder = FineTuningDatasetBuilder(combined_notes, max_chunks=max_chunks)

        try:
            examples, report = builder.build_dataset(limit=preview_limit or max_chunks)
            self.last_dataset_report = report
            self.last_training_examples = examples
            print(
                "[INFO] Dataset prepared"
                f" | total={report.total_examples}"
                f" | feedback={report.feedback_examples}"
                f" | files={report.unique_files}"
            )
            return examples
        except Exception as exc:
            print(f"[WARN] Dataset builder failed, falling back to default examples: {exc}")
            fallback = self._create_default_training_data(meeting_notes)
            self.last_dataset_report = DatasetReport(
                total_examples=len(fallback),
                source_examples=len(fallback),
                feedback_examples=0,
                unique_files=0,
                artifact_breakdown={"code": len(fallback)},
                top_files=[],
                discarded_chunks=0,
            )
            self.last_training_examples = fallback
            return fallback
    
    # Legacy artifact helper methods have been removed; dataset synthesis is handled
    # by `FineTuningDatasetBuilder` to keep the training pipeline single-sourced.
    
    def _create_default_training_data(self, meeting_notes: str = "") -> List[Dict[str, str]]:
        """Create default training data when RAG is empty"""
        
        default_examples = [
            {
                "instruction": "Generate code based on requirements:",
                "input": meeting_notes or "Implement a feature",
                "output": "Follow best practices: clean code, proper error handling, comprehensive tests"
            },
            {
                "instruction": "Create API documentation:",
                "input": "Document API endpoints",
                "output": "Include endpoint descriptions, parameters, responses, and examples"
            },
            {
                "instruction": "Design system architecture:",
                "input": "Plan application structure",
                "output": "Modular design with clear separation of concerns and scalability"
            }
        ]
        
        return default_examples
    
    def start_training(self, config: TrainingConfig, training_data: List[Dict[str, str]], 
                      progress_callback=None) -> bool:
        """Start fine-tuning training"""
        
        if not self.current_model:
            raise Exception("No model loaded")
        
        if self.training_thread and self.training_thread.is_alive():
            raise Exception("Training already in progress")
        
        # Clear previous state before starting new training
        with self._state_lock:
            self.training_progress = None
            self.training_result = None
        
        # Clear stop signal
        self._stop_training.clear()
        
        # Start training in background thread
        self.training_thread = threading.Thread(
            target=self._training_worker,
            args=(config, training_data, progress_callback),
            daemon=False  # Changed from True - allow graceful shutdown
        )
        self.training_thread.start()
        
        return True
    
    def _training_worker(self, config: TrainingConfig, training_data: List[Dict[str, str]], 
                        progress_callback=None):
        """Training worker thread"""
        
        print(f"[DEBUG] Training worker started!")
        print(f"[DEBUG] Config: epochs={config.epochs}, lr={config.learning_rate}, batch_size={config.batch_size}")
        print(f"[DEBUG] Training data: {len(training_data)} examples")
        
        try:
            # Import training dependencies
            print("[DEBUG] Importing training dependencies...")
            from peft import LoraConfig, get_peft_model, TaskType
            from transformers import TrainingArguments, Trainer
            from datasets import Dataset
            import torch
            print("[DEBUG] Dependencies imported successfully!")
            
            # Check if CUDA is available
            cuda_available = self.current_model.get('cuda_available', torch.cuda.is_available())
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Setup LoRA configuration
            print("[DEBUG] Setting up LoRA configuration...")
            lora_config = LoraConfig(
                r=config.lora_rank,
                lora_alpha=config.lora_alpha,
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
                lora_dropout=config.lora_dropout,
                bias="none",
                task_type=TaskType.CAUSAL_LM
            )
            print("[DEBUG] LoRA config created")
            
            # Apply LoRA to model
            print("[DEBUG] Applying LoRA to model...")
            model = get_peft_model(self.current_model['model'], lora_config)
            tokenizer = self.current_model['tokenizer']
            print("[DEBUG] LoRA applied to model")
            
            # Prepare dataset
            def tokenize_function(examples):
                # Tokenize the text
                tokenized = tokenizer(
                    examples['text'],
                    truncation=True,
                    padding=True,
                    max_length=config.max_length
                )
                
                # For causal language modeling, labels are the same as input_ids
                tokenized['labels'] = tokenized['input_ids'].copy()
                
                return tokenized
            
            # Convert to dataset format
            print("[DEBUG] Converting training data to dataset format...")
            texts = []
            for item in training_data:
                text = f"<s>[INST] {item['instruction']} {item['input']} [/INST] {item['output']} </s>"
                texts.append(text)
            
            dataset = Dataset.from_dict({'text': texts})
            print(f"[DEBUG] Created dataset with {len(dataset)} examples")
            
            print("[DEBUG] Tokenizing dataset...")
            tokenized_dataset = dataset.map(tokenize_function, batched=True)
            print("[DEBUG] Dataset tokenized successfully")
            
            # Training arguments - adapt based on hardware
            print("[DEBUG] Setting up training arguments...")
            training_args = TrainingArguments(
                output_dir=f"./finetuned_models/{config.model_name}",
                num_train_epochs=config.epochs,
                per_device_train_batch_size=config.batch_size,
                gradient_accumulation_steps=4,
                warmup_steps=100,
                learning_rate=config.learning_rate,
                fp16=cuda_available,  # Only use fp16 if CUDA is available
                logging_steps=10,
                save_steps=100,
                eval_strategy="no",
                eval_steps=100,
                save_total_limit=2,
                load_best_model_at_end=False,
                report_to=None,
                use_cpu=not cuda_available,  # Explicitly use CPU if CUDA not available
            )
            print(f"[DEBUG] Training args created (fp16={cuda_available}, use_cpu={not cuda_available})")
            
            # Custom trainer with progress callback
            class ProgressTrainer(Trainer):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.progress_callback = progress_callback
                
                def log(self, logs, start_time=None):
                    super().log(logs, start_time)
                    if self.progress_callback:
                        self.progress_callback(logs)
            
            print("[DEBUG] Creating trainer...")
            trainer = ProgressTrainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                tokenizer=tokenizer,
            )
            
            # Train
            print("[DEBUG] Starting training...")
            training_result = trainer.train()
            print("[DEBUG] Training completed!")
            
            # Check if training was stopped early
            if self._stop_training.is_set():
                print("[DEBUG] Training stopped by user, saving checkpoint...")
            
            # Save fine-tuned model
            print("[DEBUG] Saving fine-tuned model...")
            save_path = f"./finetuned_models/{config.model_name}_finetuned"
            model.save_pretrained(save_path)
            print("[DEBUG] Model saved successfully!")
            
            # Free GPU memory after training
            print("[DEBUG] Unloading model to free GPU memory...")
            del model
            del trainer
            if cuda_available:
                import torch
                torch.cuda.empty_cache()
            
            # Update training result (thread-safe)
            with self._state_lock:
                self.training_result = TrainingResult(
                    success=True,
                    model_path=save_path,
                    final_loss=training_result.training_loss,
                    training_time=time.time(),
                    epochs_completed=config.epochs,
                    error_message=""
                )
            
        except Exception as e:
            print(f"[ERROR] Training failed: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Update training result (thread-safe)
            with self._state_lock:
                self.training_result = TrainingResult(
                    success=False,
                    model_path="",
                    final_loss=0.0,
                    training_time=0.0,
                    epochs_completed=0,
                    error_message=str(e)
                )
    
    def get_training_progress(self) -> Optional[TrainingProgress]:
        """Get current training progress (thread-safe)"""
        with self._state_lock:
            return self.training_progress
    
    def is_training_complete(self) -> bool:
        """Check if training is complete"""
        if not self.training_thread:
            return False
        return not self.training_thread.is_alive()
    
    def is_training(self) -> bool:
        """Check if training is currently running"""
        if not self.training_thread:
            return False
        return self.training_thread.is_alive()
    
    def get_training_result(self) -> Optional[TrainingResult]:
        """Get training result if complete (thread-safe)"""
        if self.is_training_complete():
            with self._state_lock:
                return self.training_result
        return None
    
    def stop_training(self):
        """Stop current training gracefully"""
        if self.training_thread and self.training_thread.is_alive():
            print("[DEBUG] Requesting graceful training stop...")
            self._stop_training.set()
            # Wait up to 60 seconds for graceful shutdown
            self.training_thread.join(timeout=60)
            if self.training_thread.is_alive():
                print("[WARNING] Training did not stop gracefully, forcing termination")
            else:
                print("[DEBUG] Training stopped gracefully")
    
    def resume_training_from_checkpoint(self, config: TrainingConfig, training_data: List[Dict[str, str]], job_id: str) -> bool:
        """Resume training from the latest checkpoint"""
        try:
            print(f"[DEBUG] Attempting to resume training from checkpoint for job: {job_id}")
            
            # Check if checkpoint exists
            checkpoint_dir = Path(f"./finetuned_models/{config.model_name}")
            if not checkpoint_dir.exists():
                print(f"[DEBUG] No checkpoint directory found: {checkpoint_dir}")
                return False
            
            # Find the latest checkpoint
            checkpoints = list(checkpoint_dir.glob("checkpoint-*"))
            if not checkpoints:
                print(f"[DEBUG] No checkpoints found in {checkpoint_dir}")
                return False
            
            # Get the latest checkpoint (highest step number)
            latest_checkpoint = max(checkpoints, key=lambda x: int(x.name.split('-')[1]))
            print(f"[DEBUG] Found latest checkpoint: {latest_checkpoint}")
            
            # Import training dependencies
            from peft import LoraConfig, get_peft_model, TaskType
            from transformers import TrainingArguments, Trainer
            from datasets import Dataset
            import torch
            
            # Check if CUDA is available
            cuda_available = self.current_model.get('cuda_available', torch.cuda.is_available())
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Setup LoRA configuration
            lora_config = LoraConfig(
                r=config.lora_rank,
                lora_alpha=config.lora_alpha,
                target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
                lora_dropout=config.lora_dropout,
                bias="none",
                task_type=TaskType.CAUSAL_LM
            )
            
            # Apply LoRA to model
            model = get_peft_model(self.current_model['model'], lora_config)
            tokenizer = self.current_model['tokenizer']
            
            # Prepare dataset
            def tokenize_function(examples):
                tokenized = tokenizer(
                    examples['text'],
                    truncation=True,
                    padding=True,
                    max_length=config.max_length
                )
                tokenized['labels'] = tokenized['input_ids'].copy()
                return tokenized
            
            # Convert to dataset format
            texts = []
            for item in training_data:
                text = f"<s>[INST] {item['instruction']} {item['input']} [/INST] {item['output']} </s>"
                texts.append(text)
            
            dataset = Dataset.from_dict({'text': texts})
            tokenized_dataset = dataset.map(tokenize_function, batched=True)
            
            # Training arguments with resume_from_checkpoint
            training_args = TrainingArguments(
                output_dir=f"./finetuned_models/{config.model_name}",
                num_train_epochs=config.epochs,
                per_device_train_batch_size=config.batch_size,
                gradient_accumulation_steps=4,
                warmup_steps=100,
                learning_rate=config.learning_rate,
                fp16=cuda_available,
                logging_steps=10,
                save_steps=100,
                eval_strategy="no",
                eval_steps=100,
                save_total_limit=2,
                load_best_model_at_end=False,
                report_to=None,
                use_cpu=not cuda_available,
                resume_from_checkpoint=str(latest_checkpoint)  # Resume from checkpoint
            )
            
            # Custom trainer
            class ProgressTrainer(Trainer):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                
                def log(self, logs, start_time=None):
                    super().log(logs, start_time)
            
            trainer = ProgressTrainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                tokenizer=tokenizer,
            )
            
            # Resume training
            print(f"[DEBUG] Resuming training from checkpoint: {latest_checkpoint}")
            training_result = trainer.train(resume_from_checkpoint=str(latest_checkpoint))
            print("[DEBUG] Resumed training completed!")
            
            # Save fine-tuned model
            print("[DEBUG] Saving resumed fine-tuned model...")
            model.save_pretrained(f"./finetuned_models/{config.model_name}_resumed")
            tokenizer.save_pretrained(f"./finetuned_models/{config.model_name}_resumed")
            
            # Store result
            self.training_result = TrainingResult(
                success=True,
                model_path=f"./finetuned_models/{config.model_name}_resumed",
                final_loss=training_result.training_loss,
                training_time=training_result.metrics.get('train_runtime', 0),
                epochs_completed=config.epochs,
                error_message=""
            )
            
            print(f"[DEBUG] Resumed training successful! Model saved to: {self.training_result.model_path}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to resume training: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_finetuned_models(self, model_key: str) -> List[str]:
        """List fine-tuned versions of a model"""
        model_info = self.available_models[model_key]
        return model_info.fine_tuned_versions
    
    def load_finetuned_model(self, model_key: str, finetuned_version: str) -> bool:
        """Load a fine-tuned model"""
        try:
            finetuned_path = Path("finetuned_models") / model_key / finetuned_version
            
            if not finetuned_path.exists():
                raise Exception("Fine-tuned model not found")
            
            # Load fine-tuned model
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            base_model_path = Path("models") / model_key
            
            # Check if CUDA is available
            cuda_available = torch.cuda.is_available()
            
            print(f"[DEBUG] Loading fine-tuned model from {finetuned_path}")
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Load base model with appropriate settings
            if cuda_available:
                print("[DEBUG] Loading base model with 4-bit quantization (GPU)")
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16
                )
                base_model = AutoModelForCausalLM.from_pretrained(
                    str(base_model_path),
                    quantization_config=quantization_config,
                    device_map="auto"
                )
            else:
                print("[DEBUG] Loading base model on CPU")
                base_model = AutoModelForCausalLM.from_pretrained(
                    str(base_model_path),
                    dtype=torch.float32,
                    low_cpu_mem_usage=True
                )
            
            model = PeftModel.from_pretrained(base_model, str(finetuned_path))
            tokenizer = AutoTokenizer.from_pretrained(str(base_model_path))
            
            # Fix padding token for CodeLlama
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            
            # Store loaded model
            self.current_model = {
                'model': model,
                'tokenizer': tokenizer,
                'key': model_key,
                'info': self.available_models[model_key],
                'finetuned_version': finetuned_version,
                'cuda_available': cuda_available
            }
            
            print("[DEBUG] Fine-tuned model loaded successfully!")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load fine-tuned model: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to load fine-tuned model: {str(e)}")


# Global instance
local_finetuning_system = LocalFineTuningSystem()


def render_local_finetuning_ui():
    """Streamlit UI for local fine-tuning system"""
    
    st.subheader("🧠 Local Fine-Tuning System (LoRA/QLoRA)")
    
    # System info
    system_info = local_finetuning_system.get_system_info()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("RAM", f"{system_info['ram_gb']:.1f} GB")
    with col2:
        st.metric("CPU Cores", system_info['cpu_count'])
    with col3:
        st.metric("Free Disk", f"{system_info['disk_free_gb']:.1f} GB")
    with col4:
        st.metric("CUDA", "✅" if system_info['cuda_available'] else "❌")
    
    # Warning for CPU-only mode
    if not system_info['cuda_available']:
        st.warning("""
        ⚠️ **CPU-Only Mode Detected**
        
        CUDA/GPU is not available. Training will run on CPU which is:
        - Much slower (10-100x slower than GPU)
        - Limited to smaller models and batch sizes
        - Not recommended for production fine-tuning
        
        For faster training, consider:
        - Installing CUDA-enabled PyTorch: `pip install torch --index-url https://download.pytorch.org/whl/cu121`
        - Using a GPU-enabled machine
        - Using cloud-based training (Google Colab, AWS, etc.)
        """)
    
    # Model selection
    st.write("**🤖 Available Models:**")
    
    for model_key, model_info in local_finetuning_system.available_models.items():
        with st.expander(f"📦 {model_info.name} ({model_info.size})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Capability:** {model_info.capability}")
                st.write(f"**RAM Required:** {model_info.ram_required}GB")
                st.write(f"**Status:** {'✅ Downloaded' if model_info.is_downloaded else '❌ Not Downloaded'}")
                st.write(f"**Loaded:** {'✅ Yes' if model_info.is_loaded else '❌ No'}")
                
                if model_info.fine_tuned_versions:
                    st.write(f"**Fine-tuned versions:** {', '.join(model_info.fine_tuned_versions)}")
            
            with col2:
                if not model_info.is_downloaded:
                    can_download, reason = local_finetuning_system.can_download_model(model_key)
                    if can_download:
                        if st.button(f"📥 Download", key=f"download_{model_key}"):
                            with st.spinner("Downloading model..."):
                                try:
                                    def progress_callback(t):
                                        st.progress(t)
                                    
                                    asyncio.run(local_finetuning_system.download_model(model_key, progress_callback))
                                    st.success("✅ Model downloaded!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Download failed: {str(e)}")
                    else:
                        st.error(f"❌ {reason}")
                
                elif not model_info.is_loaded:
                    if st.button(f"🔄 Load", key=f"load_{model_key}"):
                        try:
                            local_finetuning_system.load_model(model_key)
                            st.success("✅ Model loaded!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Load failed: {str(e)}")
                
                else:
                    if st.button(f"⏹️ Unload", key=f"unload_{model_key}"):
                        local_finetuning_system.unload_model()
                        st.success("✅ Model unloaded!")
                        st.rerun()
    
    # Current model info
    if local_finetuning_system.current_model:
        st.write("**🎯 Current Model:**")
        current_model = local_finetuning_system.current_model
        st.info(f"**{current_model['info'].name}** - {current_model['info'].capability}")
        
        if 'finetuned_version' in current_model:
            st.info(f"**Fine-tuned version:** {current_model['finetuned_version']}")
    
    # Training section
    if local_finetuning_system.current_model:
        st.divider()
        st.write("**🎓 Fine-Tuning Configuration:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            epochs = st.slider("Epochs", 1, 10, 3)
            learning_rate = st.slider("Learning Rate", 0.0001, 0.01, 0.002, step=0.0001)
            batch_size = st.slider("Batch Size", 1, 8, 2)
        
        with col2:
            lora_rank = st.slider("LoRA Rank", 8, 64, 16)
            lora_alpha = st.slider("LoRA Alpha", 16, 128, 32)
            lora_dropout = st.slider("LoRA Dropout", 0.0, 0.5, 0.05, step=0.05)
        
        st.write("**📚 Training Data:**")
        meeting_notes = st.text_area(
            "Meeting Notes (for context):",
            height=100,
            placeholder="Enter meeting notes or requirements for fine-tuning context...",
            key="finetuning_meeting_notes"
        )

        st.write("**🧠 Feedback Memory (optional):**")
        with st.expander("Add Feedback Entry", expanded=False):
            col_fb1, col_fb2 = st.columns(2)
            with col_fb1:
                artifact_type = st.selectbox(
                    "Artifact Type",
                    [
                        "architecture",
                        "erd",
                        "api",
                        "code",
                        "ui",
                        "tests"
                    ],
                    key="finetune_feedback_artifact"
                )
            with col_fb2:
                meeting_context_feedback = st.text_area(
                    "Relevant Meeting Context",
                    height=80,
                    placeholder="Optional reminder of the scenario",
                    key="finetune_feedback_context"
                )

            issue = st.text_area(
                "What went wrong?",
                height=80,
                placeholder="Describe the problem with the generated artifact",
                key="finetune_feedback_issue"
            )
            expected_style = st.text_area(
                "What should it look like?",
                height=80,
                placeholder="Explain the desired style, pattern, or fix",
                key="finetune_feedback_expected"
            )
            reference_code = st.text_area(
                "Reference Code (optional)",
                height=80,
                placeholder="Paste a representative snippet to guide the model",
                key="finetune_feedback_reference"
            )

            if st.button("💾 Save Feedback Entry", key="finetune_save_feedback"):
                if not issue.strip() or not expected_style.strip():
                    st.warning("Feedback needs both an issue and the expected style/fix.")
                else:
                    entry = FeedbackEntry.create(
                        artifact_type=artifact_type,
                        issue=issue,
                        expected_style=expected_style,
                        reference_code=reference_code,
                        meeting_context=meeting_context_feedback,
                    )
                    feedback_store.add_feedback(entry)
                    st.success("Feedback stored! It will influence the next dataset build.")
                    st.session_state.pop('finetune_preview_dataset', None)
                    st.session_state.pop('finetuning_preview_report', None)
                    st.rerun()

        feedback_entries = feedback_store.list_feedback()
        if feedback_entries:
            st.caption("Stored feedback entries are merged into the training dataset.")
            for entry in feedback_entries:
                with st.container():
                    st.markdown(
                        f"**{entry.artifact_type.upper()}** | {entry.created_at}\n\n"
                        f"*Issue:* {entry.issue}\n\n"
                        f"*Expected:* {entry.expected_style}"
                    )
                    cols = st.columns(2)
                    if entry.reference_code:
                        with cols[0]:
                            st.code(entry.reference_code[:400] + ("..." if len(entry.reference_code) > 400 else ""), language="text")
                    with cols[-1]:
                        if st.button("🗑️ Delete", key=f"delete_feedback_{entry.id}"):
                            feedback_store.delete_feedback(entry.id)
                            st.success("Feedback removed")
                            st.session_state.pop('finetune_preview_dataset', None)
                            st.session_state.pop('finetuning_preview_report', None)
                            st.rerun()

        st.divider()
        st.write("**🔍 Dataset Preview:**")
        preview_cols = st.columns([1, 1])
        if preview_cols[0].button("Preview Dataset", key="finetune_preview_button"):
            if not meeting_notes.strip():
                st.warning("Please enter meeting notes before previewing the dataset.")
            else:
                with st.spinner("Building dataset preview..."):
                    dataset_preview = local_finetuning_system.prepare_training_data(
                        rag_context="",
                        meeting_notes=meeting_notes,
                        unlimited=False,
                        preview_limit=180,
                    )
                st.session_state['finetune_preview_dataset'] = dataset_preview
                if local_finetuning_system.last_dataset_report:
                    st.session_state['finetuning_preview_report'] = asdict(local_finetuning_system.last_dataset_report)
                st.success("Preview generated!")

        preview_dataset = st.session_state.get('finetune_preview_dataset')
        preview_report_dict = st.session_state.get('finetuning_preview_report')
        if preview_dataset and preview_report_dict:
            report = preview_report_dict
            metric_cols = st.columns(4)
            metric_cols[0].metric("Examples", report.get('total_examples', 0))
            metric_cols[1].metric("From Feedback", report.get('feedback_examples', 0))
            metric_cols[2].metric("Unique Files", report.get('unique_files', 0))
            metric_cols[3].metric("Discarded", report.get('discarded_chunks', 0))

            top_files = report.get('top_files') or []
            if top_files:
                st.markdown("**Top Files Contributing Examples:**")
                for path, count in top_files:
                    st.markdown(f"- `{path}` ({count})")

            st.markdown("**Sample Training Examples:**")
            for idx, example in enumerate(preview_dataset[:2]):
                st.code(json.dumps(example, indent=2), language="json")

            preview_json = json.dumps(preview_dataset, indent=2)
            preview_cols[1].download_button(
                "Download Preview JSON",
                data=preview_json,
                file_name="finetuning_dataset_preview.json",
                mime="application/json",
                key="download_preview_dataset"
            )

        # Start training
        if st.button("🚀 Start Fine-Tuning", type="primary"):
            if not meeting_notes.strip():
                st.warning("Please enter meeting notes for context")
                return

            with st.spinner("Preparing training dataset..."):
                training_data = local_finetuning_system.prepare_training_data(
                    rag_context="",
                    meeting_notes=meeting_notes,
                    unlimited=True,
                )

            if local_finetuning_system.last_dataset_report:
                st.session_state['finetuning_last_report'] = asdict(local_finetuning_system.last_dataset_report)
            st.session_state['finetuning_last_dataset'] = training_data

            config = TrainingConfig(
                model_name=local_finetuning_system.current_model['key'],
                epochs=epochs,
                learning_rate=learning_rate,
                batch_size=batch_size,
                lora_rank=lora_rank,
                lora_alpha=lora_alpha,
                lora_dropout=lora_dropout,
                use_4bit=True,
                use_8bit=False,
                max_length=512
            )

            try:
                def progress_callback(logs):
                    if 'epoch' in logs:
                        st.write(f"Epoch {logs['epoch']}/{epochs}")
                    if 'train_loss' in logs:
                        st.write(f"Loss: {logs['train_loss']:.4f}")

                local_finetuning_system.start_training(config, training_data, progress_callback)
                st.success("✅ Training started!")
            except Exception as e:
                st.error(f"❌ Training failed to start: {str(e)}")

        summary_report_dict = (
            st.session_state.get('finetuning_last_report')
            or st.session_state.get('finetuning_preview_report')
        )
        if summary_report_dict:
            st.write("**📊 Current Dataset Summary:**")
            col_summary = st.columns(4)
            col_summary[0].metric("Examples", summary_report_dict.get('total_examples', 0))
            col_summary[1].metric("Feedback", summary_report_dict.get('feedback_examples', 0))
            col_summary[2].metric("Files", summary_report_dict.get('unique_files', 0))
            col_summary[3].metric("Discarded", summary_report_dict.get('discarded_chunks', 0))
            feedback_summary = feedback_store.summary_by_artifact()
            if feedback_summary:
                st.caption("Feedback coverage:")
                st.markdown(
                    "\n".join(
                        f"- **{artifact}**: {count} entries" for artifact, count in feedback_summary.items()
                    )
                )

        last_dataset = st.session_state.get('finetuning_last_dataset')
        if last_dataset:
            dataset_json = json.dumps(last_dataset, indent=2)
            st.download_button(
                "Download Training Dataset",
                data=dataset_json,
                file_name="finetuning_dataset.json",
                mime="application/json",
                key="download_final_dataset"
            )
        
        # Training progress
        training_progress = local_finetuning_system.get_training_progress()
        if training_progress:
            st.write("**📊 Training Progress:**")
            st.progress(training_progress.epoch / training_progress.total_epochs)
            st.write(f"Epoch: {training_progress.epoch}/{training_progress.total_epochs}")
            st.write(f"Loss: {training_progress.loss:.4f}")
            st.write(f"ETA: {training_progress.eta:.1f}s")
        
        # Training result
        training_result = local_finetuning_system.get_training_result()
        if training_result:
            if training_result.success:
                st.success("✅ Training completed successfully!")
                st.write(f"**Final Loss:** {training_result.final_loss:.4f}")
                st.write(f"**Training Time:** {training_result.training_time:.1f}s")
                st.write(f"**Model Path:** {training_result.model_path}")
            else:
                st.error(f"❌ Training failed: {training_result.error_message}")
    
    else:
        st.info("💡 Please download and load a model to start fine-tuning")


def render_local_finetuning_tab():
    """Render the local fine-tuning tab"""
    render_local_finetuning_ui()
