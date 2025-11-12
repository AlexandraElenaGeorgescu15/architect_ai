"""
Local Fine-Tuning System with LoRA/QLoRA
Provides local model fine-tuning with model selection and training management
"""

import sys
# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        import io
        # Check if already wrapped
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        # Already wrapped, closed, or not available
        pass

import streamlit as st
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path
import json
import time
import math
import psutil
from datetime import datetime
import threading
import queue
import importlib
import platform

from .finetuning_dataset_builder import FineTuningDatasetBuilder, DatasetReport
from .finetuning_feedback import feedback_store, FeedbackEntry
import shutil


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
            ),
            "mermaid-mistral-7b": ModelInfo(
                name="MermaidMistral 7B",
                size="13GB",
                capability="Specialized for Mermaid diagram generation (ERD, Flowcharts, Sequence)",
                ram_required=16,
                download_url="TroyDoesAI/MermaidMistral",  # Fixed: removed _v2 suffix
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
        self._progress_logs: deque[Dict[str, Any]] = deque(maxlen=200)
        
        # Thread safety for shared state
        self._state_lock = threading.Lock()
        self._stop_training = threading.Event()  # Signal to stop training gracefully
        self.env_warning: Optional[str] = None
        
        # Check downloaded models
        self._scan_downloaded_models()
        self.check_environment()
    
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
    
    def check_environment(self) -> Dict[str, Any]:
        """Assess local environment readiness for GPU fine-tuning."""
        status: Dict[str, Any] = {
            "os": platform.system(),
            "has_cuda": False,
            "has_bitsandbytes": False,
            "ready": False,
            "message": ""
        }

        try:
            import torch
            status["has_cuda"] = torch.cuda.is_available()
            
            # Check VRAM if GPU available
            if status["has_cuda"]:
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                status["vram_gb"] = vram_gb
                
                if vram_gb < 11.5:  # More lenient threshold (11.99GB won't trigger warning)
                    status["message"] = (
                        f"⚠️ Only {vram_gb:.1f}GB VRAM detected. Recommend 12GB+ for 7B models with LoRA. "
                        f"Training may be slower or fail with OOM errors. "
                        f"Consider: (1) Reduce batch size to 1, (2) Use 4-bit quantization, or (3) Switch to cloud provider."
                    )
                    status["ready"] = False
                    return status
        except Exception:
            status["has_cuda"] = False

        try:
            importlib.import_module("bitsandbytes")
            status["has_bitsandbytes"] = True
        except Exception:
            status["has_bitsandbytes"] = False

        if not status["has_cuda"]:
            status["message"] = (
                "CUDA-capable GPU not detected. Local fine-tuning requires a GPU. "
                "Install CUDA-enabled PyTorch or switch to a cloud provider (Groq/Gemini/OpenAI)."
            )
        elif not status["has_bitsandbytes"]:
            install_hint = "pip install bitsandbytes" if status["os"] != "Windows" else (
                "bitsandbytes wheels for Windows are experimental; consider WSL2 or a Linux machine."
            )
            status["message"] = (
                "bitsandbytes library not available. Install bitsandbytes for 4-bit loading or use a cloud provider. "
                f"Hint: {install_hint}"
            )
        else:
            status["ready"] = True
            status["message"] = "Environment ready for local fine-tuning."

        self.env_warning = None if status["ready"] else status["message"]
        return status
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for model compatibility"""
        env_status = self.check_environment()
        return {
            "ram_gb": psutil.virtual_memory().total / (1024**3),
            "cpu_count": psutil.cpu_count(),
            "disk_free_gb": psutil.disk_usage('/').free / (1024**3),
            "python_version": "3.8+",
            "cuda_available": env_status["has_cuda"],
            "bitsandbytes_available": env_status["has_bitsandbytes"],
            "environment_ready": env_status["ready"]
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

            # 🚀 REGISTER MODEL: Add to registry so it appears in AI provider dropdown
            try:
                from components.model_registry import model_registry
                model_path_str = str(models_dir / model_key)
                model_registry.register_downloaded_model(
                    base_model=model_key,
                    model_path=model_path_str
                )
                print(f"[REGISTRY] ✅ Model registered in dropdown: {model_key}")
            except Exception as e:
                print(f"[REGISTRY] ⚠️ Failed to register model: {e}")

            env_status = self.check_environment()
            if not env_status["ready"]:
                warning = (
                    "Model downloaded successfully, but the local environment is not ready: "
                    f"{env_status['message']}"
                )
                print(f"[WARN] {warning}")
                self.env_warning = warning
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to download model: {str(e)}")
    
    def load_model(self, model_key: str, incremental: bool = True) -> bool:
        """Load a model for inference/fine-tuning
        
        Args:
            model_key: The base model key (e.g., 'codellama-7b')
            incremental: If True, load the latest fine-tuned version if it exists
        """
        # 🚀 AUTO-UNLOAD: Unload any existing model first to free VRAM
        if self.current_model:
            print(f"[AUTO-UNLOAD] Unloading existing model to free VRAM...")
            self.unload_model()
            
            # Also unload Ollama models if available
            try:
                from ai.ollama_client import OllamaClient
                ollama = OllamaClient()
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # Unload all Ollama models
                loop.run_until_complete(ollama.unload_all_models())
                print(f"[AUTO-UNLOAD] ✅ All Ollama models unloaded")
            except Exception as e:
                print(f"[AUTO-UNLOAD] ⚠️ Could not unload Ollama models: {e}")
        
        try:
            model_info = self.available_models[model_key]
            
            if not model_info.is_downloaded:
                raise Exception("Model not downloaded")

            env_status = self.check_environment()
            if not env_status["ready"]:
                raise Exception(env_status["message"])
            
            # Check if we should load a fine-tuned version for incremental training
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            base_model_path = Path("models") / model_key
            finetuned_path = None
            finetuned_version = None
            
            if incremental:
                # Check for existing fine-tuned versions
                finetuned_versions = self.list_finetuned_models(model_key)
                if finetuned_versions:
                    # Load the latest fine-tuned version
                    finetuned_version = sorted(finetuned_versions)[-1]
                    finetuned_path = Path("finetuned_models") / model_key / finetuned_version
                    
                    if finetuned_path.exists():
                        print(f"[INCREMENTAL] Loading previous fine-tuned model: {finetuned_version}")
                        print(f"[INCREMENTAL] This training will build on previous improvements!")
                    else:
                        print(f"[INFO] Fine-tuned path not found, loading base model")
                        finetuned_path = None
                        finetuned_version = None
            
            if not finetuned_path:
                print(f"[INFO] Loading base model (no previous fine-tuning found)")
            
            model_path = base_model_path
            
            # GPU should be available if environment ready, but double-check
            cuda_available = torch.cuda.is_available()
            if not cuda_available:
                raise Exception(
                    "CUDA not available for local base model load. "
                    "Please enable GPU/bitsandbytes support or use a cloud provider."
                )
            
            print(f"[DEBUG] Loading base model from {model_path}")
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Load model with appropriate settings based on hardware
            model = None

            if cuda_available:
                try:
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
                except Exception as exc:
                    print(f"[WARN] GPU 4-bit load failed ({exc}). Falling back to CPU load.")
                    cuda_available = False

            if model is None:
                raise Exception(
                    "bitsandbytes loading failed. Ensure bitsandbytes is installed and compatible with your GPU."
                )
            
            # If we have a fine-tuned version, load and MERGE the LoRA adapter into base model
            if finetuned_path:
                try:
                    # Check if adapter_config.json exists at root, otherwise try latest checkpoint
                    adapter_config_path = finetuned_path / "adapter_config.json"
                    actual_adapter_path = finetuned_path
                    
                    if not adapter_config_path.exists():
                        print(f"[WARN] No adapter at root, checking for checkpoints...")
                        # Look for checkpoints
                        checkpoints = sorted([d for d in finetuned_path.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")])
                        if checkpoints:
                            # Use the latest checkpoint
                            actual_adapter_path = checkpoints[-1]
                            print(f"[OK] Found checkpoint: {actual_adapter_path.name}")
                        else:
                            raise Exception(f"No adapter_config.json found at {finetuned_path} or in checkpoints")
                    
                    print(f"[INCREMENTAL] Loading LoRA adapter from {actual_adapter_path}")
                    model = PeftModel.from_pretrained(model, str(actual_adapter_path))
                    print(f"[INCREMENTAL] ✅ Successfully loaded fine-tuned model!")
                    
                    # CRITICAL: Merge the adapter into the base model for incremental training
                    print(f"[INCREMENTAL] Merging adapter into base model for incremental training...")
                    model = model.merge_and_unload()
                    print(f"[INCREMENTAL] ✅ Adapter merged! Ready for next training iteration.")
                    print(f"[INCREMENTAL] Next training will build on: {finetuned_version}")
                except Exception as e:
                    print(f"[WARN] Failed to load/merge fine-tuned adapter: {e}")
                    print(f"[WARN] Falling back to base model")
                    finetuned_path = None
                    finetuned_version = None
            
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
                'cuda_available': cuda_available,
                'is_finetuned': finetuned_path is not None,
                'finetuned_version': finetuned_version,
                'base_path': str(base_model_path)
            }
            
            # Update model info
            model_info.is_loaded = True
            
            if finetuned_version:
                print(f"[DEBUG] Model loaded successfully (incremental from {finetuned_version})!")
            else:
                print(f"[DEBUG] Model loaded successfully (base model)!")
            
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
    
    def _get_next_version_name(self, model_key: str) -> str:
        """Generate the next version name for incremental training"""
        from datetime import datetime
        
        # Get existing versions
        existing_versions = self.list_finetuned_models(model_key)
        
        # If this is incremental training from a previous version
        if self.current_model and self.current_model.get('is_finetuned'):
            current_version = self.current_model.get('finetuned_version', '')
            # Try to extract version number
            import re
            match = re.search(r'v(\d+)', current_version)
            if match:
                current_num = int(match.group(1))
                next_num = current_num + 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                return f"v{next_num}_{timestamp}"
        
        # Count existing versions to determine next number
        version_numbers = []
        for version in existing_versions:
            import re
            match = re.search(r'v(\d+)', version)
            if match:
                version_numbers.append(int(match.group(1)))
        
        next_num = max(version_numbers) + 1 if version_numbers else 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"v{next_num}_{timestamp}"
    
    def _record_progress_log(self, logs: Dict[str, Any]) -> None:
        """Persist training logs emitted from background threads."""
        sanitized: Dict[str, Any] = {
            key: float(value) if isinstance(value, (int, float)) else value
            for key, value in logs.items()
        }
        sanitized["timestamp"] = time.time()
        with self._state_lock:
            self._progress_logs.append(sanitized)

    def consume_progress_logs(self) -> List[Dict[str, Any]]:
        """Return and clear accumulated training logs."""
        with self._state_lock:
            logs = list(self._progress_logs)
            self._progress_logs.clear()
        return logs

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

        max_chunks = 1200 if unlimited else 300
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
        
        # Validate learning rate to prevent model divergence
        if not (2e-5 <= config.learning_rate <= 1e-3):
            raise ValueError(
                f"Learning rate {config.learning_rate:.2e} is outside safe range [2e-5, 1e-3]. "
                f"Extreme learning rates can cause model divergence. "
                f"Recommended range: 2e-5 (conservative) to 5e-4 (aggressive)."
            )
        
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
        
        total_effective_steps = 0
        
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
            
            # Get the model and prepare it for training
            model = self.current_model['model']
            tokenizer = self.current_model['tokenizer']
            
            # CRITICAL: Enable gradient checkpointing and prepare model for 4-bit training
            print("[DEBUG] Preparing model for 4-bit LoRA training...")
            model.gradient_checkpointing_enable()
            
            # Ensure the model is in training mode
            model.train()
            
            # Enable input gradients for 4-bit models
            from peft import prepare_model_for_kbit_training
            model = prepare_model_for_kbit_training(model)
            print("[DEBUG] Model prepared for 4-bit training")
            
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
            model = get_peft_model(model, lora_config)
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
            
            # Validate training data is not empty
            if not training_data or len(training_data) == 0:
                raise ValueError("Training data is empty - cannot start training")
            
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
            gradient_accumulation_steps = max(1, 8 // max(1, config.batch_size))
            per_epoch_steps = math.ceil(len(tokenized_dataset) / max(1, config.batch_size * gradient_accumulation_steps))
            total_effective_steps = max(1, per_epoch_steps * config.epochs)

            if cuda_available:
                torch.backends.cuda.matmul.allow_tf32 = True  # type: ignore[attr-defined]
            
            # Check if bf16 is supported, but prefer it over fp16 (more stable)
            bf16_check = getattr(torch.cuda, "is_bf16_supported", lambda: False)
            bf16_enabled = cuda_available and bf16_check()
            
            # CRITICAL: Only one of fp16 or bf16 can be True
            # Prefer bf16 if available (better numerical stability)
            use_fp16 = cuda_available and not bf16_enabled
            use_bf16 = bf16_enabled

            # Generate version name for this training run
            version_name = self._get_next_version_name(config.model_name)
            output_dir = f"./finetuned_models/{config.model_name}/{version_name}"
            
            # Log incremental training info
            if self.current_model and self.current_model.get('is_finetuned'):
                prev_version = self.current_model.get('finetuned_version', 'unknown')
                print(f"[INCREMENTAL] Training {version_name} (builds on {prev_version})")
            else:
                print(f"[INCREMENTAL] Training {version_name} (builds on base model)")
            
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=config.epochs,
                per_device_train_batch_size=config.batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
                learning_rate=config.learning_rate,
                fp16=use_fp16,
                bf16=use_bf16,
                gradient_checkpointing=False,  # Already enabled manually above
                max_grad_norm=0.3,
                logging_steps=10,
                save_steps=100,
                eval_strategy="no",
                eval_steps=100,
                save_total_limit=2,
                load_best_model_at_end=False,
                report_to=None,
                use_cpu=not cuda_available,  # Explicitly use CPU if CUDA not available
                lr_scheduler_type="cosine_with_restarts",
                warmup_ratio=0.05,
            )
            print(f"[DEBUG] Training args created (fp16={cuda_available}, use_cpu={not cuda_available})")
            
            # Custom trainer with progress callback
            class ProgressTrainer(Trainer):
                def __init__(self, *args, **kwargs):
                    progress_cb = kwargs.pop("progress_callback", None)
                    super().__init__(*args, **kwargs)
                    self.progress_callback = progress_cb
                
                def log(self, logs, start_time=None):
                    super().log(logs, start_time)
                    if self.progress_callback:
                        self.progress_callback(logs)

            def handle_progress(logs: Dict[str, Any]) -> None:
                self._record_progress_log(logs)

                epoch_val = float(logs.get("epoch", 0.0) or 0.0)
                loss_val = float(
                    logs.get("loss")
                    or logs.get("train_loss")
                    or logs.get("training_loss")
                    or 0.0
                )
                lr_val = float(logs.get("learning_rate", 0.0) or 0.0)
                step_val = int(logs.get("step") or logs.get("global_step") or 0)

                with self._state_lock:
                    self.training_progress = TrainingProgress(
                        epoch=int(epoch_val),
                        total_epochs=config.epochs,
                        step=step_val,
                        total_steps=total_effective_steps,
                        loss=loss_val,
                        learning_rate=lr_val,
                        eta=0.0,
                        status="training",
                    )

                if progress_callback:
                    try:
                        progress_callback(logs)
                    except Exception as cb_exc:  # noqa: BLE001
                        print(f"[WARN] Progress callback failed: {cb_exc}")
            
            print("[DEBUG] Creating trainer...")
            trainer = ProgressTrainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset,
                tokenizer=tokenizer,
                progress_callback=handle_progress,
            )
            
            # Train
            print("[DEBUG] Starting training...")
            train_start = time.time()
            training_result = trainer.train()
            print("[DEBUG] Training completed!")
            
            # Check if training was stopped early
            if self._stop_training.is_set():
                print("[DEBUG] Training stopped by user, saving checkpoint...")
            
            # Health-check logits to ensure model is numerically stable before saving
            print("[DEBUG] Running post-training health check...")
            health_prompt = "<s>[INST] Briefly reply with 'ACK' for health check. [/INST]"
            health_inputs = tokenizer(health_prompt, return_tensors="pt", truncation=True, max_length=256)
            if cuda_available:
                health_inputs = {k: v.cuda() for k, v in health_inputs.items()}
            with torch.no_grad():
                health_outputs = model(**health_inputs)
            if not torch.isfinite(health_outputs.logits).all():
                raise ValueError(
                    "Fine-tuned model produced non-finite logits during health check. "
                    "Try lowering the learning rate or epochs."
                )
            
            # Save fine-tuned model using structured directory layout
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = Path("finetuned_models") / config.model_name
            version_name = f"{config.model_name}_finetuned-{timestamp}"
            save_dir = base_dir / version_name

            print(f"[DEBUG] Saving fine-tuned model to {save_dir}...")
            save_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(save_dir))
            tokenizer.save_pretrained(str(save_dir))
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
                    model_path=str(save_dir),
                    final_loss=training_result.training_loss,
                    training_time=time.time() - train_start,
                    epochs_completed=config.epochs,
                    error_message=""
                )

                self.training_progress = TrainingProgress(
                    epoch=config.epochs,
                    total_epochs=config.epochs,
                    step=total_effective_steps,
                    total_steps=total_effective_steps,
                    loss=training_result.training_loss,
                    learning_rate=config.learning_rate,
                    eta=0.0,
                    status="completed",
                )

                model_info = self.available_models.get(config.model_name)
                if model_info and version_name not in model_info.fine_tuned_versions:
                    model_info.fine_tuned_versions.append(version_name)

            self._persist_trained_model_metadata(
                base_model=config.model_name,
                version_name=version_name,
                save_dir=save_dir,
                config=config,
                training_loss=training_result.training_loss,
                epochs_completed=config.epochs
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
                self.training_progress = TrainingProgress(
                    epoch=0,
                    total_epochs=config.epochs,
                    step=0,
                    total_steps=0,
                    loss=0.0,
                    learning_rate=config.learning_rate,
                    eta=0.0,
                    status="failed",
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
    
    def has_resumable_checkpoint(self) -> bool:
        """Check if there's a checkpoint available for resume"""
        if not self.current_model:
            return False
        
        model_key = self.current_model['key']
        checkpoint_dir = Path(f"./finetuned_models/{model_key}")
        
        if not checkpoint_dir.exists():
            return False
        
        checkpoints = list(checkpoint_dir.glob("checkpoint-*"))
        return len(checkpoints) > 0
    
    def resume_training_from_checkpoint_async(self, config: TrainingConfig, training_data: List[Dict[str, str]], job_id: str):
        """Resume training from checkpoint in background thread (async, non-blocking)"""
        # Clear previous state
        with self._state_lock:
            self.training_progress = None
            self.training_result = None
        
        # Clear stop signal
        self._stop_training.clear()
        
        # Start resume in background thread
        self.training_thread = threading.Thread(
            target=self._resume_training_worker,
            args=(config, training_data, job_id),
            daemon=False
        )
        self.training_thread.start()
        print(f"[DEBUG] Resume training started in background thread for job: {job_id}")
    
    def _resume_training_worker(self, config: TrainingConfig, training_data: List[Dict[str, str]], job_id: str):
        """Worker method that runs resume training in background thread"""
        try:
            self._resume_training_from_checkpoint(config, training_data, job_id)
        except Exception as e:
            print(f"[ERROR] Resume training worker failed: {e}")
            import traceback
            traceback.print_exc()
            with self._state_lock:
                self.training_result = TrainingResult(
                    success=False,
                    model_path="",
                    final_loss=0.0,
                    training_time=0.0,
                    epochs_completed=0,
                    error_message=str(e)
                )
    
    def _resume_training_from_checkpoint(self, config: TrainingConfig, training_data: List[Dict[str, str]], job_id: str) -> bool:
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
            
            # Get the latest checkpoint (highest step number) with safe parsing
            def safe_checkpoint_number(checkpoint_path):
                try:
                    return int(checkpoint_path.name.split('-')[1])
                except (IndexError, ValueError):
                    return 0
            
            latest_checkpoint = max(checkpoints, key=safe_checkpoint_number)
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
            # Validate training data is not empty
            if not training_data or len(training_data) == 0:
                raise ValueError("Training data is empty - cannot resume training")
            
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
            
            # Save fine-tuned model (resume)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = Path("finetuned_models") / config.model_name
            version_name = f"{config.model_name}_resumed-{timestamp}"
            save_dir = base_dir / version_name

            print(f"[DEBUG] Saving resumed fine-tuned model to {save_dir}...")
            save_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(save_dir))
            tokenizer.save_pretrained(str(save_dir))
            
            with self._state_lock:
                self.training_result = TrainingResult(
                    success=True,
                    model_path=str(save_dir),
                    final_loss=training_result.training_loss,
                    training_time=training_result.metrics.get('train_runtime', 0),
                    epochs_completed=config.epochs,
                    error_message=""
                )

                model_info = self.available_models.get(config.model_name)
                if model_info and version_name not in model_info.fine_tuned_versions:
                    model_info.fine_tuned_versions.append(version_name)

            self._persist_trained_model_metadata(
                base_model=config.model_name,
                version_name=version_name,
                save_dir=save_dir,
                config=config,
                training_loss=training_result.training_loss,
                epochs_completed=config.epochs
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
                legacy_candidates = [
                    Path("finetuned_models") / finetuned_version,
                    Path("finetuned_models") / f"{model_key}_finetuned",
                    Path(finetuned_version)
                ]

                resolved = None
                for candidate in legacy_candidates:
                    if candidate.exists():
                        resolved = candidate
                        break

                if resolved is None:
                    raise Exception("Fine-tuned model not found")

                finetuned_path = resolved
                finetuned_version = finetuned_path.name

            canonical_dir = Path("finetuned_models") / model_key
            target_dir = canonical_dir / finetuned_version

            if finetuned_path.exists() and finetuned_path.resolve() != target_dir.resolve():
                try:
                    target_dir.parent.mkdir(parents=True, exist_ok=True)
                    if target_dir.exists():
                        shutil.rmtree(target_dir)
                    shutil.move(str(finetuned_path), str(target_dir))
                    finetuned_path = target_dir
                    print(f"[INFO] Migrated fine-tuned model to canonical path: {finetuned_path}")
                except Exception as move_exc:
                    print(f"[WARN] Failed to migrate fine-tuned model directory: {move_exc}")
                    # Continue using resolved path even if migration fails
            
            # Load fine-tuned model
            from peft import PeftModel
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch
            
            base_model_path = Path("models") / model_key
            
            env_status = self.check_environment()
            if not env_status["ready"]:
                raise Exception(env_status["message"])
            
            # Check if CUDA is available
            cuda_available = torch.cuda.is_available()
            if not cuda_available:
                raise Exception(
                    "CUDA not available for fine-tuned model load. "
                    "Please enable GPU/bitsandbytes support or select a remote provider."
                )
            
            print(f"[DEBUG] Loading fine-tuned model from {finetuned_path}")
            print(f"[DEBUG] CUDA available: {cuda_available}")
            
            # Load base model with appropriate settings
            base_model = None

            if cuda_available:
                try:
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
                except Exception as exc:
                    raise Exception(
                        f"bitsandbytes GPU load failed: {exc}. Ensure bitsandbytes is installed and compatible with your GPU."
                    )

            if base_model is None:
                raise Exception(
                    "bitsandbytes loading failed. Ensure bitsandbytes is installed and compatible with your GPU."
                )
            
            # Check if adapter_config.json exists at root, otherwise try latest checkpoint
            adapter_config_path = finetuned_path / "adapter_config.json"
            actual_adapter_path = finetuned_path
            
            if not adapter_config_path.exists():
                print(f"[WARN] No adapter at root, checking for checkpoints...")
                # Look for checkpoints
                checkpoints = sorted([d for d in finetuned_path.iterdir() if d.is_dir() and d.name.startswith("checkpoint-")])
                if checkpoints:
                    # Use the latest checkpoint
                    actual_adapter_path = checkpoints[-1]
                    print(f"[OK] Found checkpoint: {actual_adapter_path.name}")
                else:
                    raise Exception(f"No adapter_config.json found at {finetuned_path} or in checkpoints")
            
            # CRITICAL: Use forward slashes for cross-platform compatibility
            # PeftModel.from_pretrained interprets backslashes as HuggingFace repo IDs on Windows
            adapter_path_str = str(actual_adapter_path).replace('\\', '/')
            print(f"[DEBUG] Loading adapter from: {adapter_path_str}")
            
            model = PeftModel.from_pretrained(base_model, adapter_path_str)
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
                'cuda_available': cuda_available,
                'path': str(finetuned_path)
            }

            model_info = self.available_models.get(model_key)
            if model_info:
                if finetuned_version not in model_info.fine_tuned_versions:
                    model_info.fine_tuned_versions.append(finetuned_version)
                model_info.is_loaded = True
            
            print("[DEBUG] Fine-tuned model loaded successfully!")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to load fine-tuned model: {str(e)}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to load fine-tuned model: {str(e)}")

    def _persist_trained_model_metadata(
        self,
        base_model: str,
        version_name: str,
        save_dir: Path,
        config: Any,
        training_loss: float,
        epochs_completed: int,
        model_identifier: Optional[str] = None,
    ) -> None:
        """Persist trained model metadata in registries and dynamic config systems."""

        identifier = model_identifier or version_name

        # Normalize config payload for registry storage
        if hasattr(config, "__dataclass_fields__"):
            config_payload = asdict(config)
        elif isinstance(config, dict):
            config_payload = dict(config)
        else:
            config_payload = {
                "model_name": base_model,
                "epochs": epochs_completed,
            }

        resolved_path = save_dir.resolve()

        # Register in persistent model registry (avoids duplicates by path)
        try:
            from components.model_registry import model_registry

            already_registered = any(
                Path(model.model_path).resolve() == resolved_path
                for model in model_registry.get_trained_models()
            )

            if not already_registered:
                model_registry.register_trained_model(
                    base_model=base_model,
                    model_path=str(save_dir),
                    training_config=config_payload,
                    metrics={
                        "final_loss": training_loss,
                        "epochs_completed": epochs_completed,
                    },
                )
        except Exception as exc:
            print(f"[WARN] Failed to register fine-tuned model in registry: {exc}")

        # Derive heuristic context settings similar to persistent manager
        base_key = base_model.lower()
        is_deepseek = "deepseek" in base_key
        is_llama_or_mistral = any(token in base_key for token in ["llama", "mistral"])

        context_window = 16384 if is_deepseek else 32768 if is_llama_or_mistral else 16384
        recommended_context = 12000 if is_deepseek else 24000 if is_llama_or_mistral else 12000
        max_chunks = 70 if is_deepseek else 100 if is_llama_or_mistral else 60
        recommended_chunks = 45 if is_deepseek else 60 if is_llama_or_mistral else 40

        # Register dynamic model configuration
        try:
            from config.model_config import ModelConfig, ModelProvider, dynamic_model_config

            if not dynamic_model_config.get_model_config(identifier):
                dynamic_model_config.register_finetuned_model(
                    identifier,
                    ModelConfig(
                        name=f"{base_model.replace('-', ' ').title()} (Fine-tuned)",
                        provider=ModelProvider.LOCAL_FINETUNED,
                        context_window=context_window,
                        recommended_context=recommended_context,
                        max_chunks=max_chunks,
                        recommended_chunks=recommended_chunks,
                        supports_function_calling=False,
                        cost_per_1k_tokens=0.0,
                    ),
                )
        except Exception as exc:
            print(f"[WARN] Failed to register dynamic config for fine-tuned model: {exc}")

        # Update local finetuned registry file for UI integrations
        try:
            registry_file = Path("finetuned_models") / "registry.json"
            registry = json.loads(registry_file.read_text(encoding="utf-8")) if registry_file.exists() else {}

            if identifier not in registry:
                registry[identifier] = {
                    "name": f"{base_model.replace('-', ' ').title()} (Fine-tuned)",
                    "provider": "local_finetuned",
                    "context_window": context_window,
                    "max_chunks": max_chunks,
                    "created_at": datetime.now().isoformat(),
                    "training_loss": training_loss,
                    "epochs_completed": epochs_completed,
                    "model_path": str(save_dir),
                }

                registry_file.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[WARN] Failed to update local fine-tuned registry: {exc}")


# Global instance
local_finetuning_system = LocalFineTuningSystem()


def render_local_finetuning_ui():
    """Streamlit UI for local fine-tuning system"""
    
    st.subheader("🧠 Local Fine-Tuning System (LoRA/QLoRA)")
    
    # System info
    system_info = local_finetuning_system.get_system_info()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("RAM", f"{system_info['ram_gb']:.1f} GB")
    with col2:
        st.metric("CPU Cores", system_info['cpu_count'])
    with col3:
        st.metric("Free Disk", f"{system_info['disk_free_gb']:.1f} GB")
    with col4:
        st.metric("CUDA", "✅" if system_info['cuda_available'] else "❌")
    with col5:
        st.metric("bitsandbytes", "✅" if system_info['bitsandbytes_available'] else "❌")
    
    if local_finetuning_system.env_warning:
        st.error(f"⚠️ {local_finetuning_system.env_warning}")
    elif not system_info['environment_ready']:
        env_status = local_finetuning_system.check_environment()
        st.error(f"⚠️ {env_status['message']}")
    
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
                
                # Show incremental training status
                if model_info.is_loaded and local_finetuning_system.current_model:
                    is_finetuned = local_finetuning_system.current_model.get('is_finetuned', False)
                    if is_finetuned:
                        finetuned_version = local_finetuning_system.current_model.get('finetuned_version', 'unknown')
                        st.success(f"🔄 **Incremental Mode:** Loaded {finetuned_version}")
                        st.caption("Next training will build on this version")
                    else:
                        st.info("🆕 **Base Mode:** Next training will be v1")
                
                if model_info.fine_tuned_versions:
                    st.write(f"**Fine-tuned versions:** {len(model_info.fine_tuned_versions)} available")
                    st.caption("💡 Select a version to load for incremental training or rollback:")
                    
                    # Use a scrollable container instead of nested expander
                    version_container = st.container()
                    with version_container:
                        for version in sorted(model_info.fine_tuned_versions, reverse=True):
                            col_version, col_btn = st.columns([3, 1])
                            with col_version:
                                # Highlight if this is the currently loaded version
                                is_current = (model_info.is_loaded and 
                                            local_finetuning_system.current_model and 
                                            local_finetuning_system.current_model.get('finetuned_version') == version)
                                if is_current:
                                    st.success(f"✅ {version} (current)")
                                else:
                                    st.text(f"   {version}")
                            with col_btn:
                                if not is_current:
                                    if st.button("Load", key=f"load_version_{model_key}_{version}"):
                                        with st.spinner(f"Loading {version}..."):
                                            try:
                                                local_finetuning_system.load_finetuned_model(model_key, version)
                                                st.success(f"✅ Loaded {version}!")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"❌ Failed: {str(e)}")
            
            with col2:
                if not model_info.is_downloaded:
                    can_download, reason = local_finetuning_system.can_download_model(model_key)
                    if can_download:
                        if st.button(f"📥 Download", key=f"download_{model_key}"):
                            with st.spinner("Downloading model..."):
                                try:
                                    import asyncio as async_module  # Local import to avoid scoping issues
                                    
                                    def progress_callback(t):
                                        st.progress(t)
                                    
                                    # Run async function synchronously
                                    loop = async_module.new_event_loop()
                                    async_module.set_event_loop(loop)
                                    try:
                                        loop.run_until_complete(local_finetuning_system.download_model(model_key, progress_callback))
                                    finally:
                                        loop.close()
                                    
                                    st.success("✅ Model downloaded!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Download failed: {str(e)}")
                    else:
                        st.error(f"❌ {reason}")
                
                elif not model_info.is_loaded:
                    if local_finetuning_system.env_warning:
                        st.error(local_finetuning_system.env_warning)
                    if st.button(f"🔄 Load", key=f"load_{model_key}"):
                        with st.spinner(f"Loading {model_info.name}..."):
                            try:
                                local_finetuning_system.load_model(model_key)
                                local_finetuning_system.training_result = None
                                with local_finetuning_system._state_lock:
                                    local_finetuning_system.training_progress = None
                                    local_finetuning_system._progress_logs.clear()
                                st.success("✅ Model loaded!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Load failed: {str(e)}")
                
                else:
                    if st.button(f"⏹️ Unload", key=f"unload_{model_key}"):
                        local_finetuning_system.unload_model()
                        local_finetuning_system.training_result = None
                        with local_finetuning_system._state_lock:
                            local_finetuning_system.training_progress = None
                            local_finetuning_system._progress_logs.clear()
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
            learning_rate = st.slider(
                "Learning Rate",
                min_value=0.00002,
                max_value=0.001,
                value=0.0002,
                step=0.00002,
                format="%.5f",  # Show 5 decimal places
                help="Clamp between 2e-5 and 1e-3 to avoid divergence. Default: 0.0002 (2e-4)"
            )
            st.caption(f"Current value: {learning_rate:.5f} ({learning_rate:.2e})")
            batch_size = st.slider("Batch Size", 1, 8, 2)
        
        with col2:
            lora_rank = st.slider("LoRA Rank", 8, 64, 16)
            lora_alpha = st.slider("LoRA Alpha", 16, 128, 32)
            lora_dropout = st.slider("LoRA Dropout", 0.0, 0.5, 0.05, step=0.05)
        
        st.write("**📚 Training Data:**")
        if 'finetuning_meeting_notes' not in st.session_state:
            notes_path = Path("inputs") / "meeting_notes.md"
            default_notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
            st.session_state['finetuning_meeting_notes'] = default_notes

        meeting_notes = st.text_area(
            "Meeting Notes (for context):",
            height=100,
            placeholder="Enter meeting notes or requirements for fine-tuning context...",
            key="finetuning_meeting_notes"
        )

        st.markdown("---")
        st.write("**🧠 Teach the AI (Feedback for Training):**")
        st.caption("💡 Add feedback when the AI makes mistakes. This will be included in the training dataset.")
        with st.expander("➕ Add New Feedback Entry", expanded=True):
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
        
        # Incremental training option (feedback only)
        feedback_count = len(feedback_store.list_feedback())
        if feedback_count > 0:
            st.info(f"💡 **Quick Tip:** You have {feedback_count} feedback entries. You can train **incrementally** (feedback only) instead of rebuilding the full dataset.")
            
            col_train_type1, col_train_type2 = st.columns(2)
            with col_train_type1:
                training_mode = st.radio(
                    "Training Mode:",
                    ["Full Dataset (Feedback + RAG)", "Incremental (Feedback Only)"],
                    key="training_mode_selector",
                    help="Incremental training is faster and focuses only on your corrections"
                )
            
            st.session_state['is_incremental_training'] = (training_mode == "Incremental (Feedback Only)")
        else:
            st.session_state['is_incremental_training'] = False
        
        # Unlimited mode checkbox
        unlimited_mode = st.checkbox(
            "🚀 Unlimited Mode (Retrieve up to 1200 RAG examples)",
            value=True,
            key="unlimited_mode_checkbox",
            help="Retrieves more examples from your repository for better training quality"
        )
        st.session_state['unlimited_mode'] = unlimited_mode
        
        st.divider()
        st.write("**🔍 Dataset Preview:**")
        preview_cols = st.columns([1, 1])
        if preview_cols[0].button("Preview Dataset", key="finetune_preview_button"):
            is_incremental = st.session_state.get('is_incremental_training', False)
            unlimited = st.session_state.get('unlimited_mode', True)
            
            if is_incremental:
                # Build incremental dataset (feedback only)
                with st.spinner("Building incremental dataset (feedback only)..."):
                    try:
                        builder = FineTuningDatasetBuilder(meeting_notes="", max_chunks=0)
                        preview_dataset, preview_report = builder.build_incremental_dataset()
                        
                        st.session_state['finetune_preview_dataset'] = preview_dataset
                        st.session_state['finetuning_preview_report'] = asdict(preview_report)
                        # Clear old training data since dataset changed
                        st.session_state.pop('last_training_data', None)
                        st.session_state.pop('last_training_config', None)
                        st.session_state.pop('last_training_job_id', None)
                        st.success(f"✅ Prepared {len(preview_dataset)} feedback-only training examples")
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Failed to build incremental dataset: {str(e)}")
            elif not meeting_notes.strip():
                st.warning("Please enter meeting notes before previewing the dataset.")
            else:
                with st.spinner("Building dataset preview..."):
                    preview_limit = None if unlimited else 180
                    dataset_preview = local_finetuning_system.prepare_training_data(
                        rag_context="",
                        meeting_notes=meeting_notes,
                        unlimited=unlimited,
                        preview_limit=preview_limit,
                    )
                st.session_state['finetune_preview_dataset'] = dataset_preview
                if local_finetuning_system.last_dataset_report:
                    st.session_state['finetuning_preview_report'] = asdict(local_finetuning_system.last_dataset_report)
                # Clear old training data since dataset changed
                st.session_state.pop('last_training_data', None)
                st.session_state.pop('last_training_config', None)
                st.session_state.pop('last_training_job_id', None)
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

            st.info(
                "Want a baseline before you fine-tune? Switch the main provider in the sidebar to Groq, Gemini, or OpenAI, rerun the same artifact once, and compare the output before training the local model."
            )

            top_files = report.get('top_files') or []
            if top_files:
                st.markdown("**Top Files Contributing Examples:**")
                for path, count in top_files:
                    st.markdown(f"- `{path}` ({count})")

            st.markdown("**Sample Training Examples:**")
            
            # Show feedback examples first (if any)
            feedback_count = report.get('feedback_examples', 0)
            if feedback_count > 0:
                st.markdown("🎯 **From User Feedback:**")
                feedback_samples = [ex for ex in preview_dataset if ex.get('source') == 'feedback'][:2]
                for idx, example in enumerate(feedback_samples):
                    st.markdown(f"**Feedback Example {idx+1}**")
                    st.code(json.dumps(example, indent=2), language="json")
            
            # Then show RAG-sourced examples
            st.markdown("📚 **From Repository Context:**")
            rag_samples = [ex for ex in preview_dataset if ex.get('source') != 'feedback'][:2]
            for idx, example in enumerate(rag_samples):
                st.markdown(f"**RAG Example {idx+1}**")
                st.code(json.dumps(example, indent=2), language="json")

            preview_json = json.dumps(preview_dataset, indent=2)
            preview_cols[1].download_button(
                "Download Preview JSON",
                data=preview_json,
                file_name="finetuning_dataset_preview.json",
                mime="application/json",
                key="download_preview_dataset"
            )
            
            # FULL DATASET VIEWER with search
            st.markdown("---")
            with st.expander("🔍 **View & Search Full Training Dataset**", expanded=False):
                st.caption(f"Total: {len(preview_dataset)} examples")
                
                # Search/filter controls
                search_cols = st.columns([2, 1, 1])
                with search_cols[0]:
                    search_term = st.text_input("🔎 Search examples", placeholder="Search in instruction/input/output...", key="dataset_search")
                with search_cols[1]:
                    filter_source = st.selectbox("Filter by source", ["All", "Feedback", "RAG"], key="dataset_filter_source")
                with search_cols[2]:
                    max_available = max(1, len(preview_dataset))
                    show_limit = st.number_input(
                        "Show first N",
                        min_value=1,
                        max_value=max_available,
                        value=min(20, max_available),
                        key="dataset_limit",
                    )
                
                # Apply filters
                filtered_examples = preview_dataset
                if filter_source == "Feedback":
                    filtered_examples = [ex for ex in filtered_examples if ex.get('source') == 'feedback']
                elif filter_source == "RAG":
                    filtered_examples = [ex for ex in filtered_examples if ex.get('source') != 'feedback']
                
                if search_term:
                    search_lower = search_term.lower()
                    filtered_examples = [
                        ex for ex in filtered_examples 
                        if search_lower in ex.get('instruction', '').lower() 
                        or search_lower in ex.get('input', '').lower() 
                        or search_lower in ex.get('output', '').lower()
                    ]
                
                st.caption(f"Showing {min(show_limit, len(filtered_examples))} of {len(filtered_examples)} matching examples")
                
                # Display examples
                for idx, example in enumerate(filtered_examples[:show_limit]):
                    source_badge = "🎯 Feedback" if example.get('source') == 'feedback' else "📚 RAG"
                    st.markdown(f"---\n**{source_badge} | Example {idx+1}:** {example.get('instruction', 'N/A')[:80]}...")
                    st.markdown("**Instruction:**")
                    st.text(example.get('instruction', 'N/A'))
                    st.markdown("**Input:**")
                    st.text_area(
                        f"Input {idx+1}",
                        value=example.get('input', 'N/A')[:800],
                        height=120,
                        key=f"dataset_view_input_{idx}",
                        disabled=True
                    )
                    st.markdown("**Output:**")
                    st.text_area(
                        f"Output {idx+1}",
                        value=example.get('output', 'N/A')[:800],
                        height=120,
                        key=f"dataset_view_output_{idx}",
                        disabled=True
                    )

        # PRE-FLIGHT VALIDATION & START TRAINING
        st.divider()
        st.write("**🚦 Pre-Flight Check:**")
        
        # Build training data for validation
        validation_ok = True
        validation_messages = []
        is_incremental = st.session_state.get('is_incremental_training', False)
        
        if is_incremental:
            # Incremental mode: skip meeting notes check
            validation_messages.append("🎯 **Incremental Training Mode** - Using feedback examples only")
        elif not meeting_notes.strip():
            validation_ok = False
            validation_messages.append("❌ Meeting notes are empty")
        
        # Check if preview was generated
        preview_dataset = st.session_state.get('finetune_preview_dataset')
        preview_report = st.session_state.get('finetuning_preview_report')
        
        if preview_dataset and preview_report:
            total_examples = preview_report.get('total_examples', 0)
            feedback_examples = preview_report.get('feedback_examples', 0)
            top_files = preview_report.get('top_files', [])
            
            # Adjust minimum for incremental training
            # Import MIN_DATASET_SIZE from dataset builder
            from components.finetuning_dataset_builder import MIN_DATASET_SIZE
            min_examples = 10 if is_incremental else MIN_DATASET_SIZE
            
            if total_examples < min_examples:
                validation_ok = False
                validation_messages.append(f"❌ Only {total_examples} examples (need minimum {min_examples})")
            else:
                validation_messages.append(f"✅ {total_examples} training examples prepared")
                if is_incremental:
                    validation_messages.append(f"✅ All {feedback_examples} examples from feedback")
            
            # Skip scaffolding check for incremental (no RAG files involved)
            if not is_incremental:
                # Check for WeatherForecast contamination
                weather_contamination = [f for f, _ in top_files if 'weatherforecast' in f.lower()]
                if weather_contamination and len(weather_contamination) > 0:
                    validation_ok = False
                    validation_messages.append(f"❌ WeatherForecast detected in top files: {weather_contamination}")
                else:
                    validation_messages.append("✅ No scaffolding files in top 10")
                
                # Show top files
                if top_files:
                    validation_messages.append(f"✅ Top file: {top_files[0][0]}")
        else:
            validation_ok = False
            validation_messages.append("❌ No dataset preview generated - click 'Preview Dataset' first")
        
        for msg in validation_messages:
            if msg.startswith("❌"):
                st.error(msg)
            elif msg.startswith("⚠️"):
                st.warning(msg)
            else:
                st.success(msg)
        
        # Confirmation checkbox
        if validation_ok:
            dataset_confirmed = st.checkbox(
                "✅ I confirm the dataset looks correct and contains MY project files",
                key="finetune_dataset_confirmed"
            )
        else:
            dataset_confirmed = False
            st.info("💡 Fix validation issues above before training")
        
        # Start training button (only enabled if validation passes)
        if st.button("🚀 Start Fine-Tuning", type="primary", disabled=not dataset_confirmed):
            # Get training mode from session state
            is_incremental_mode = st.session_state.get('is_incremental_training', False)
            
            # Use preview dataset if available (avoids rebuilding)
            training_data = st.session_state.get('finetune_preview_dataset')
            
            # Validate training data exists and is not empty
            if not training_data or len(training_data) == 0:
                # Fallback: build dataset now (shouldn't happen if pre-flight passed)
                with st.spinner("Preparing final training dataset..."):
                    if is_incremental_mode:
                        builder = FineTuningDatasetBuilder(meeting_notes="", max_chunks=0)
                        training_data, _ = builder.build_incremental_dataset()
                    else:
                        training_data = local_finetuning_system.prepare_training_data(
                            rag_context="",
                            meeting_notes=meeting_notes,
                            unlimited=True,
                        )
            
            # ========== GENERATE DATASETS USING THREE METHODS ==========
            with st.spinner("🔄 Generating comprehensive datasets (Comprehensive Builder + Ollama + variations)..."):
                import asyncio
                import json
                import random
                from pathlib import Path
                from config.artifact_model_mapping import get_artifact_mapper, ArtifactType
                from ai.ollama_client import OllamaClient
                from ai.model_router import get_router
                
                # Get artifact type from model or default to "code"
                artifact_type = st.session_state.get('selected_artifact_type', 'code_prototype')
                if not artifact_type:
                    # Try to infer from model name
                    model_name = local_finetuning_system.current_model.get('key', 'codellama-7b')
                    if 'mermaid' in model_name.lower():
                        artifact_type = 'erd'
                    elif 'jira' in model_name.lower() or 'llama3' in model_name.lower():
                        artifact_type = 'jira'
                    else:
                        artifact_type = 'code_prototype'
                
                datasets_dir = Path("finetune_datasets")
                datasets_dir.mkdir(parents=True, exist_ok=True)
                
                # ========== METHOD 1: COMPREHENSIVE BUILDER (BEST - 1000+ HIGH QUALITY) ==========
                comprehensive_examples = []
                try:
                    st.info("✨ Generating 1000+ high-quality examples using Comprehensive Builder...")
                    from scripts.build_comprehensive_datasets import ComprehensiveFinetuningDatasets
                    
                    builder = ComprehensiveFinetuningDatasets(output_dir=datasets_dir)
                    
                    # Map artifact type to dataset method
                    dataset_methods = {
                        'erd': builder.build_erd_dataset,
                        'architecture': builder.build_architecture_dataset,
                        'system_overview': builder.build_architecture_dataset,
                        'data_flow': builder.build_sequence_dataset,
                        'user_flow': builder.build_sequence_dataset,
                        'components_diagram': builder.build_class_diagram_dataset,
                        'api_sequence': builder.build_sequence_dataset,
                        'code_prototype': builder.build_code_prototype_dataset,
                        'visual_prototype_dev': builder.build_html_prototype_dataset,
                        'api_docs': builder.build_api_docs_dataset,
                        'jira': builder.build_jira_dataset,
                        'workflows': builder.build_workflow_dataset,
                    }
                    
                    if artifact_type in dataset_methods:
                        comprehensive_examples = dataset_methods[artifact_type]()
                        
                        # Save comprehensive dataset
                        comprehensive_path = datasets_dir / f"{artifact_type}_comprehensive_1000plus.jsonl"
                        with open(comprehensive_path, 'w', encoding='utf-8') as f:
                            for ex in comprehensive_examples:
                                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        
                        st.success(f"✅ Generated {len(comprehensive_examples)} high-quality examples using Comprehensive Builder!")
                    else:
                        st.warning(f"⚠️ No comprehensive dataset available for {artifact_type}. Using fallback methods.")
                except Exception as e:
                    st.warning(f"⚠️ Comprehensive dataset generation failed: {str(e)}. Falling back to other methods...")
                    import traceback
                    print(f"[ERROR] Comprehensive dataset generation: {traceback.format_exc()}")
                
                # Method 2: Generate using Ollama (if available)
                ollama_examples = []
                try:
                    ollama_client = OllamaClient()
                    if asyncio.run(ollama_client.check_server_health()):
                        router = get_router({}, ollama_client)
                        router.set_force_local_only(True)
                        
                        mapper = get_artifact_mapper()
                        task_type = mapper.get_task_type(artifact_type)
                        model_name = mapper.get_model_name(artifact_type)
                        
                        st.info(f"🤖 Generating 1000 examples using Ollama ({model_name})...")
                        
                        # Generate examples using Ollama
                        from scripts.generate_datasets_with_ollama import SEED_PROMPTS, vary_prompt, build_system_message
                        
                        seeds = SEED_PROMPTS.get(task_type, [f"Generate {artifact_type} example."])
                        system_message = build_system_message(artifact_type)
                        
                        # Generate in batches
                        batch_size = 50
                        total_needed = 1000
                        generated = 0
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        while generated < total_needed:
                            batch_prompts = [vary_prompt(random.choice(seeds)) for _ in range(batch_size)]
                            
                            for prompt in batch_prompts:
                                try:
                                    response = asyncio.run(router.generate(
                                        task_type=task_type,
                                        prompt=prompt,
                                        system_message=system_message,
                                        temperature=0.2,
                                        force_cloud=False
                                    ))
                                    
                                    if response.success and response.content and len(response.content.strip()) > 0:
                                        ollama_examples.append({
                                            "prompt": prompt,
                                            "completion": response.content.strip(),
                                            "metadata": {
                                                "artifact": artifact_type,
                                                "model": model_name,
                                                "source": "ollama"
                                            }
                                        })
                                        generated += 1
                                        
                                        if generated % 100 == 0:
                                            status_text.text(f"Generated {generated}/{total_needed} examples...")
                                            progress_bar.progress(generated / total_needed)
                                        
                                        if generated >= total_needed:
                                            break
                                except Exception as e:
                                    continue  # Skip failed generations
                            
                            if generated >= total_needed:
                                break
                        
                        progress_bar.progress(1.0)
                        status_text.text(f"✅ Generated {len(ollama_examples)} examples using Ollama")
                        
                        # Save Ollama dataset
                        ollama_path = datasets_dir / f"{artifact_type}_ollama_1000.jsonl"
                        with open(ollama_path, 'w', encoding='utf-8') as f:
                            for ex in ollama_examples:
                                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        
                        st.success(f"✅ Saved {len(ollama_examples)} Ollama examples to {ollama_path}")
                    else:
                        st.warning("⚠️ Ollama server not running. Skipping Ollama dataset generation.")
                except Exception as e:
                    st.warning(f"⚠️ Ollama dataset generation failed: {str(e)}. Continuing with variation-based generation...")
                
                # Method 2: Generate using variations (from seed examples)
                try:
                    st.info("🔄 Generating 1000 examples using variations...")
                    from scripts.generate_finetuning_datasets import generate_variations
                    
                    # Get seed examples for artifact type
                    seed_examples = []
                    if artifact_type in ['erd', 'architecture', 'data_flow', 'user_flow', 'components_diagram', 'api_sequence']:
                        from scripts.generate_finetuning_datasets import MERMAID_EXAMPLES
                        seed_examples = MERMAID_EXAMPLES
                    elif artifact_type in ['code_prototype']:
                        from scripts.generate_finetuning_datasets import CODE_EXAMPLES
                        seed_examples = CODE_EXAMPLES
                    elif artifact_type in ['visual_prototype_dev']:
                        from scripts.generate_finetuning_datasets import HTML_EXAMPLES
                        seed_examples = HTML_EXAMPLES
                    elif artifact_type in ['api_docs', 'documentation']:
                        from scripts.generate_finetuning_datasets import DOCUMENTATION_EXAMPLES
                        seed_examples = DOCUMENTATION_EXAMPLES
                    elif artifact_type == 'jira':
                        from scripts.generate_finetuning_datasets import JIRA_EXAMPLES
                        seed_examples = JIRA_EXAMPLES
                    elif artifact_type == 'workflows':
                        from scripts.generate_finetuning_datasets import WORKFLOW_EXAMPLES
                        seed_examples = WORKFLOW_EXAMPLES
                    
                    if seed_examples:
                        variation_examples = generate_variations(seed_examples, target_count=1000)
                        
                        # Convert to training format
                        variation_training = []
                        for ex in variation_examples:
                            variation_training.append({
                                "instruction": ex.get("prompt", ""),
                                "input": "",
                                "output": ex.get("completion", ""),
                                "source": "variation",
                                "metadata": {
                                    "artifact": artifact_type,
                                    "source": "variation"
                                }
                            })
                        
                        # Save variation dataset
                        variation_path = datasets_dir / f"{artifact_type}_variation_1000.jsonl"
                        with open(variation_path, 'w', encoding='utf-8') as f:
                            for ex in variation_training:
                                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                        
                        st.success(f"✅ Saved {len(variation_training)} variation examples to {variation_path}")
                        
                        # ========== MERGE ALL DATASETS ==========
                        # Priority: Comprehensive > Ollama > Variations
                        
                        # 1. Add comprehensive examples (highest quality)
                        for ex in comprehensive_examples:
                            training_data.append({
                                "instruction": ex.get("instruction", ""),
                                "input": ex.get("input", ""),
                                "output": ex.get("output", ""),
                                "source": "comprehensive",
                                "metadata": {
                                    "artifact": artifact_type,
                                    "source": "comprehensive_builder",
                                    "quality": "high"
                                }
                            })
                        
                        # 2. Add Ollama examples
                        for ex in ollama_examples:
                            training_data.append({
                                "instruction": ex["prompt"],
                                "input": "",
                                "output": ex["completion"],
                                "source": "ollama",
                                "metadata": ex.get("metadata", {})
                            })
                        
                        # 3. Add variation examples (as supplementary)
                        training_data.extend(variation_training)
                        
                        total_comprehensive = len(comprehensive_examples)
                        total_ollama = len(ollama_examples)
                        total_variations = len(variation_training)
                        
                        st.success(f"✅ Merged {total_comprehensive} comprehensive + {total_ollama} Ollama + {total_variations} variation examples = {total_comprehensive + total_ollama + total_variations} total examples!")
                        
                        # Show breakdown
                        with st.expander("📊 Dataset Breakdown", expanded=False):
                            st.markdown(f"""
                            **Dataset Sources:**
                            - 🌟 **Comprehensive Builder**: {total_comprehensive} examples (high quality, domain-specific)
                            - 🤖 **Ollama Generated**: {total_ollama} examples (AI-generated variations)
                            - 🔄 **Seed Variations**: {total_variations} examples (template-based)
                            
                            **Total Training Examples**: {total_comprehensive + total_ollama + total_variations}
                            """)
                    else:
                        st.warning(f"⚠️ No seed examples found for {artifact_type}. Skipping variation generation.")
                except Exception as e:
                    st.warning(f"⚠️ Variation dataset generation failed: {str(e)}. Using existing training data only.")
                    import traceback
                    st.code(traceback.format_exc())

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
                # Store config and data for potential resume
                st.session_state['last_training_config'] = config
                st.session_state['last_training_data'] = training_data
                st.session_state['last_training_job_id'] = f"{config.model_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                local_finetuning_system.start_training(config, training_data, progress_callback=None)
                st.success("✅ Training started!")
                st.info("📂 Check outputs/finetuning/chunk_selection_debug.json to verify selected files")
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
        
        # Training status and controls
        is_training = local_finetuning_system.is_training()
        training_progress = local_finetuning_system.get_training_progress()
        training_result = local_finetuning_system.get_training_result()
        has_checkpoint = local_finetuning_system.has_resumable_checkpoint()
        
        # Check if we can resume training (not currently training, has checkpoint, has saved config)
        can_resume = (
            not is_training and 
            has_checkpoint and 
            'last_training_config' in st.session_state and
            'last_training_data' in st.session_state
        )
        
        if is_training and training_progress:
            st.write("**📊 Training in Progress:**")
            progress_val = min(training_progress.epoch / max(training_progress.total_epochs, 1), 1.0)
            st.progress(progress_val)
            st.write(f"Epoch: {training_progress.epoch}/{training_progress.total_epochs}")
            st.write(f"Loss: {training_progress.loss:.4f}")
            st.write(f"ETA: {training_progress.eta:.1f}s")

            progress_updates = local_finetuning_system.consume_progress_logs()
            if progress_updates:
                last_update = progress_updates[-1]
                step_display = last_update.get('step') or last_update.get('global_step')
                lr_raw = last_update.get('learning_rate')
                lr_display = float(lr_raw) if isinstance(lr_raw, (int, float)) else 0.0
                loss_raw = (
                    last_update.get('loss')
                    or last_update.get('train_loss')
                    or last_update.get('training_loss')
                )
                loss_display = float(loss_raw) if isinstance(loss_raw, (int, float)) else None
                loss_str = f"{loss_display:.4f}" if loss_display is not None else "—"
                st.caption(f"Step {step_display or '—'} • Loss {loss_str} • LR {lr_display:.2e}")
            
            # Training controls
            st.markdown("**⚙️ Training Controls:**")
            if st.button("⏹️ Stop Training", type="secondary", key="stop_training_btn"):
                local_finetuning_system.stop_training()
                st.warning("🛑 Stopping training gracefully...")
                st.info("💾 Progress has been saved - you can resume later")
                time.sleep(2)
                st.rerun()
        
        elif training_result:
            # Training completed or failed
            local_finetuning_system.consume_progress_logs()
            if training_result.success:
                st.success("✅ Training completed successfully!")
                st.write(f"**Final Loss:** {training_result.final_loss:.4f}")
                st.write(f"**Training Time:** {training_result.training_time:.1f}s")
                st.write(f"**Model Path:** {training_result.model_path}")
                
                # Clear result so user can start new training
                if st.button("🔄 Start New Training", key="clear_result_btn"):
                    local_finetuning_system.training_result = None
                    st.rerun()
            else:
                st.error(f"❌ Training failed: {training_result.error_message}")
                
                # Option to retry
                if st.button("🔄 Retry Training", key="retry_training_btn"):
                    local_finetuning_system.training_result = None
                    st.rerun()
        
        # Resume training section (show if checkpoint exists and not currently training)
        if can_resume and not training_result:
            st.markdown("---")
            st.info("💾 **Checkpoint detected** - You can resume training from where you left off")
            
            col_resume1, col_resume2 = st.columns(2)
            with col_resume1:
                if st.button("▶️ Resume Training", type="primary", key="resume_training_btn"):
                    try:
                        config = st.session_state['last_training_config']
                        training_data = st.session_state['last_training_data']
                        job_id = st.session_state.get('last_training_job_id', 'unknown')
                        
                        # Start resume in background (non-blocking)
                        local_finetuning_system.resume_training_from_checkpoint_async(
                            config, training_data, job_id
                        )
                        st.success("✅ Training resume started in background!")
                        st.info("Check training progress below")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Resume failed: {str(e)}")
            
            with col_resume2:
                if st.button("🗑️ Discard Checkpoint", type="secondary", key="discard_checkpoint_btn"):
                    try:
                        import shutil
                        model_key = local_finetuning_system.current_model['key']
                        checkpoint_dir = Path(f"./finetuned_models/{model_key}")
                        if checkpoint_dir.exists():
                            shutil.rmtree(checkpoint_dir)
                            st.success("✅ Checkpoint discarded")
                            # Clear session state
                            for key in ['last_training_config', 'last_training_data', 'last_training_job_id']:
                                st.session_state.pop(key, None)
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to discard checkpoint: {str(e)}")
    
    else:
        st.info("💡 Please download and load a model to start fine-tuning")


def render_local_finetuning_tab():
    """Render the local fine-tuning tab"""
    render_local_finetuning_ui()
