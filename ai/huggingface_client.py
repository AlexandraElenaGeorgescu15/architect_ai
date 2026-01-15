"""
HuggingFace Transformers Client - Direct model usage without Ollama conversion
Provides on-demand loading and usage of HuggingFace models via transformers library
"""

import asyncio
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import logging
import sys

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available. Install with: pip install transformers torch")


class ModelStatus(Enum):
    """Status of a model"""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    READY = "ready"
    IN_USE = "in_use"
    ERROR = "error"


@dataclass
class ModelInfo:
    """Information about a model"""
    name: str
    status: ModelStatus
    model_path: Optional[str] = None
    size_bytes: int = 0
    last_used: Optional[datetime] = None
    load_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    error_message: str = ""


@dataclass
class GenerationResponse:
    """Response from model generation"""
    content: str
    model_used: str
    generation_time: float
    tokens_generated: int = 0
    success: bool = True
    error_message: str = ""


class HuggingFaceClient:
    """
    Client for using HuggingFace models directly via transformers library.
    
    Features:
    - On-demand model loading
    - Model caching (keep models in memory)
    - Async API for non-blocking operations
    - Automatic device selection (CPU/GPU)
    - Support for both CausalLM and Seq2Seq models
    """
    
    def __init__(self, models_dir: Optional[Path] = None, device: Optional[str] = None):
        """
        Initialize HuggingFace client.
        
        Args:
            models_dir: Directory where models are stored (default: models/huggingface)
            device: Device to use ("cuda", "cpu", or None for auto)
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library not available. Install with: pip install transformers torch")
        
        self.models_dir = models_dir or Path("models/huggingface")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        self.models: Dict[str, ModelInfo] = {}
        self.loaded_models: Dict[str, Any] = {}  # model_id -> (tokenizer, model)
        self._loading_locks: Dict[str, asyncio.Lock] = {}
        
        logger.info(f"HuggingFace Client initialized (device: {self.device})")
    
    def _get_loading_lock(self, model_id: str) -> asyncio.Lock:
        """Get or create a lock for loading a specific model"""
        if model_id not in self._loading_locks:
            self._loading_locks[model_id] = asyncio.Lock()
        return self._loading_locks[model_id]
    
    async def check_model_available(self, model_id: str) -> bool:
        """
        Check if a model is available (downloaded or accessible).
        
        Args:
            model_id: HuggingFace model ID (e.g., "zai-org/GLM-4.6")
        
        Returns:
            True if model is available, False otherwise
        """
        try:
            # Check if model is in our downloads directory
            model_dir = self.models_dir / model_id.replace("/", "_")
            if model_dir.exists():
                # Check for config.json (indicates model is downloaded)
                config_file = model_dir / "config.json"
                if not config_file.exists():
                    # Check in subdirectories (HF cache structure)
                    for subdir in model_dir.rglob("config.json"):
                        return True
                else:
                    return True
            
            # Model might be available from HuggingFace Hub directly
            # We'll try to load it and catch errors if it fails
            return True
        except Exception as e:
            logger.debug(f"Error checking model availability for {model_id}: {e}")
            return False
    
    async def ensure_model_loaded(self, model_id: str, model_path: Optional[str] = None) -> bool:
        """
        Ensure a model is loaded and ready to use.
        
        Args:
            model_id: HuggingFace model ID
            model_path: Optional local path to model files
        
        Returns:
            True if model is loaded, False otherwise
        """
        if model_id in self.loaded_models:
            return True
        
        lock = self._get_loading_lock(model_id)
        async with lock:
            # Double-check after acquiring lock
            if model_id in self.loaded_models:
                return True
            
            # Update status
            if model_id not in self.models:
                self.models[model_id] = ModelInfo(
                    name=model_id,
                    status=ModelStatus.LOADING,
                    model_path=model_path
                )
            else:
                self.models[model_id].status = ModelStatus.LOADING
            
            try:
                logger.info(f"Loading HuggingFace model: {model_id}")
                start_time = datetime.now()
                
                # Determine model path
                if model_path:
                    load_path = model_path
                else:
                    # Check local downloads first
                    model_dir = self.models_dir / model_id.replace("/", "_")
                    if model_dir.exists():
                        # Find the actual model directory (HF cache structure)
                        # HuggingFace cache structure: models--org--model/snapshots/hash/
                        config_files = list(model_dir.rglob("config.json"))
                        if config_files:
                            # Use the directory containing config.json
                            load_path = str(config_files[0].parent)
                            logger.debug(f"Found model at: {load_path}")
                        else:
                            # Try to find any subdirectory that might contain the model
                            # Look for common HF cache structure
                            snapshots_dir = model_dir / "snapshots"
                            if snapshots_dir.exists():
                                # Get the first snapshot directory
                                snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]
                                if snapshot_dirs:
                                    load_path = str(snapshot_dirs[0])
                                    logger.debug(f"Found model in snapshot: {load_path}")
                                else:
                                    load_path = str(model_dir)
                            else:
                                load_path = str(model_dir)
                    else:
                        # Use model_id directly (will download from HF Hub)
                        load_path = model_id
                        logger.info(f"Model not found locally, will download from HuggingFace Hub: {model_id}")
                
                # Load tokenizer and model in thread pool (blocking operations)
                def load_model():
                    tokenizer = AutoTokenizer.from_pretrained(load_path, trust_remote_code=True)
                    
                    # Try CausalLM first (most common)
                    try:
                        model = AutoModelForCausalLM.from_pretrained(
                            load_path,
                            trust_remote_code=True,
                            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                            device_map="auto" if self.device == "cuda" else None,
                            low_cpu_mem_usage=True
                        )
                        if self.device == "cpu":
                            model = model.to(self.device)
                    except Exception:
                        # Try Seq2Seq if CausalLM fails
                        model = AutoModelForSeq2SeqLM.from_pretrained(
                            load_path,
                            trust_remote_code=True,
                            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                            device_map="auto" if self.device == "cuda" else None,
                            low_cpu_mem_usage=True
                        )
                        if self.device == "cpu":
                            model = model.to(self.device)
                    
                    return tokenizer, model
                
                tokenizer, model = await asyncio.to_thread(load_model)
                
                # Store loaded model
                self.loaded_models[model_id] = (tokenizer, model)
                
                # Update status
                load_time = (datetime.now() - start_time).total_seconds()
                self.models[model_id].status = ModelStatus.READY
                self.models[model_id].load_time = load_time
                self.models[model_id].model_path = load_path
                
                logger.info(f"✅ Model {model_id} loaded in {load_time:.2f}s")
                return True
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to load model {model_id}: {error_msg}", exc_info=True)
                if model_id in self.models:
                    self.models[model_id].status = ModelStatus.ERROR
                    self.models[model_id].error_message = error_msg
                return False
    
    async def generate(
        self,
        model_id: str,
        prompt: str,
        system_message: str = "",
        temperature: float = 0.7,
        max_tokens: int = 512,
        model_path: Optional[str] = None
    ) -> GenerationResponse:
        """
        Generate text using a HuggingFace model.
        
        Args:
            model_id: HuggingFace model ID
            prompt: User prompt
            system_message: System message (optional)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            model_path: Optional local path to model
        
        Returns:
            GenerationResponse with generated content
        """
        start_time = datetime.now()
        
        try:
            # Ensure model is loaded
            if not await self.ensure_model_loaded(model_id, model_path):
                return GenerationResponse(
                    content="",
                    model_used=model_id,
                    generation_time=0.0,
                    success=False,
                    error_message=f"Failed to load model {model_id}"
                )
            
            # Get tokenizer and model
            tokenizer, model = self.loaded_models[model_id]
            
            # Update status
            if model_id in self.models:
                self.models[model_id].status = ModelStatus.IN_USE
                self.models[model_id].total_requests += 1
            
            # Prepare input
            if system_message:
                full_prompt = f"{system_message}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            # Generate in thread pool (blocking operation)
            # Use larger context window to retain more context
            def generate_text():
                # Use model's max position embeddings or default to 8192 for larger context
                model_max_length = getattr(model.config, 'max_position_embeddings', 8192)
                # Use at least 8192 tokens for comprehensive context (was hardcoded 2048)
                effective_max_length = min(max(model_max_length, 8192), 16384)
                inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True, max_length=effective_max_length)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=max_tokens,
                        temperature=temperature,
                        do_sample=temperature > 0,
                        pad_token_id=tokenizer.eos_token_id if tokenizer.pad_token_id is None else tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id
                    )
                
                # Decode output
                generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
                
                # Remove input prompt from output
                if generated_text.startswith(full_prompt):
                    generated_text = generated_text[len(full_prompt):].strip()
                
                return generated_text, len(outputs[0]) - len(inputs['input_ids'][0])
            
            content, tokens_generated = await asyncio.to_thread(generate_text)
            
            # Update status
            generation_time = (datetime.now() - start_time).total_seconds()
            if model_id in self.models:
                self.models[model_id].status = ModelStatus.READY
                self.models[model_id].last_used = datetime.now()
                self.models[model_id].successful_requests += 1
            
            return GenerationResponse(
                content=content,
                model_used=model_id,
                generation_time=generation_time,
                tokens_generated=tokens_generated,
                success=True
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Generation error with {model_id}: {error_msg}", exc_info=True)
            generation_time = (datetime.now() - start_time).total_seconds()
            
            if model_id in self.models:
                self.models[model_id].status = ModelStatus.ERROR
                self.models[model_id].error_message = error_msg
            
            return GenerationResponse(
                content="",
                model_used=model_id,
                generation_time=generation_time,
                success=False,
                error_message=error_msg
            )
    
    def unload_model(self, model_id: str):
        """Unload a model from memory to free resources"""
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
            if model_id in self.models:
                self.models[model_id].status = ModelStatus.NOT_LOADED
            logger.info(f"Unloaded model: {model_id}")
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a model"""
        return self.models.get(model_id)
    
    def list_loaded_models(self) -> List[str]:
        """List all currently loaded models"""
        return list(self.loaded_models.keys())


# Singleton instance
_hf_client: Optional[HuggingFaceClient] = None

def get_client() -> Optional[HuggingFaceClient]:
    """Get HuggingFace client instance (returns None if transformers not available)"""
    global _hf_client
    if _hf_client is None and TRANSFORMERS_AVAILABLE:
        try:
            _hf_client = HuggingFaceClient()
        except Exception as e:
            logger.warning(f"Failed to initialize HuggingFace client: {e}")
            return None
    return _hf_client
