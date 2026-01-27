"""
Ollama Client - Interface to local Ollama model server
Provides on-demand loading and persistent caching of local AI models
"""

import asyncio
import httpx
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import time


class ModelStatus(Enum):
    """Status of a model in Ollama"""
    NOT_LOADED = "not_loaded"    # Model not in memory
    LOADING = "loading"           # Model being loaded
    READY = "ready"               # Model loaded and ready
    IN_USE = "in_use"             # Model currently generating
    ERROR = "error"               # Model failed to load


@dataclass
class ModelInfo:
    """Information about a model"""
    name: str
    status: ModelStatus
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


class OllamaClient:
    """
    Client for interacting with Ollama local model server.
    
    Features:
    - On-demand model loading (first request loads model)
    - Persistent model caching (subsequent requests are fast)
    - Model status tracking (not loaded / loading / ready / in use / error)
    - Async API for non-blocking operations
    - Automatic retry and error handling
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120, vram_limit_gb: float = 12.0):
        """
        Initialize Ollama client with VRAM management.
        
        Args:
            base_url: Ollama server URL (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 120)
            vram_limit_gb: VRAM limit in GB (default: 12.0 for RTX 3500 Ada)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.vram_limit_gb = vram_limit_gb
        self.models: Dict[str, ModelInfo] = {}
        self._http_client = None
        
        # VRAM management (Dynamic)
        self.persistent_models: set = set()  # Models that should stay loaded
        self.active_models: set = set()      # Currently loaded models
        self.model_sizes: Dict[str, float] = {} # Populated dynamically
        
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._http_client
    
    async def check_server_health(self) -> bool:
        """
        Check if Ollama server is running and accessible.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            client = self._get_http_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            print(f"[ERROR] Ollama server not accessible: {e}")
            return False
    
    async def list_available_models(self) -> List[str]:
        """
        List all models available in Ollama.
        
        Returns:
            List of model names
        """
        return await self.list_models()

    async def list_models(self) -> List[str]:
        """
        Internal implementation for listing models and updating sizes.
        """
        try:
            client = self._get_http_client()
            response = await client.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                
                # Update model sizes map dynamically
                for model in models:
                    name = model.get("name")
                    size_bytes = model.get("size", 0)
                    if name and size_bytes:
                        # Convert to GB (10^9 bytes usually for disk, but VRAM is 2^30? using 10^9 for safety/conservative)
                        # Ollama reports bytes on disk. VRAM usage is roughly similar for GGUF + context.
                        # Let's use binary GB (GiB) as standard VRAM is measured in GiB.
                        self.model_sizes[name] = size_bytes / (1024 ** 3)
                        
                return [model.get("name", "") for model in models]
            else:
                print(f"[ERROR] Failed to list models: {response.status_code}")
                return []
        except Exception as e:
            print(f"[ERROR] Failed to list models: {e}")
            return []
    
    async def is_model_available(self, model_name: str) -> bool:
        """
        Check if a model is available (downloaded) in Ollama.
        
        Args:
            model_name: Name of the model
            
        Returns:
            True if model is available, False otherwise
        """
        return await self.check_model_availability(model_name)

    async def check_model_availability(self, model_name: str) -> bool:
        """
        Internal implementation for checking model availability.
        """
        available_models = await self.list_available_models()
        # Check exact match or prefix match (for versioned models)
        return any(model_name in m or m.startswith(model_name) for m in available_models)
    
    async def load_model(self, model_name: str, show_progress: bool = True) -> bool:
        """
        Load a model into memory (on-demand loading).
        
        First time: Takes 30-60 seconds
        Subsequent times: Model is already loaded (instant)
        
        Args:
            model_name: Name of the model to load
            show_progress: Whether to print progress messages
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        # Check if already loaded
        if model_name in self.models and self.models[model_name].status == ModelStatus.READY:
            if show_progress:
                print(f"[INFO] Model {model_name} already loaded")
            return True
        
        # Initialize model info
        if model_name not in self.models:
            self.models[model_name] = ModelInfo(
                name=model_name,
                status=ModelStatus.NOT_LOADED
            )
        
        # Set status to loading
        self.models[model_name].status = ModelStatus.LOADING
        start_time = time.time()
        
        try:
            if show_progress:
                print(f"[INFO] Loading model {model_name}...")
            
            # Check if model is available
            if not await self.is_model_available(model_name):
                # Auto-pull missing model
                try:
                    import asyncio
                    print(f"[INFO] Model {model_name} not found. Pulling via 'ollama pull {model_name}'...")
                    process = await asyncio.create_subprocess_exec(
                        "ollama", "pull", model_name,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=1800)
                    
                    if process.returncode != 0:
                        err = stderr.decode() or stdout.decode()
                        error_msg = f"Failed to pull model {model_name}: {err.strip()}"
                        print(f"[ERROR] {error_msg}")
                        self.models[model_name].status = ModelStatus.ERROR
                        self.models[model_name].error_message = error_msg
                        return False
                    # Verify availability after pull
                    if not await self.is_model_available(model_name):
                        error_msg = f"Model {model_name} still not available after pull"
                        print(f"[ERROR] {error_msg}")
                        self.models[model_name].status = ModelStatus.ERROR
                        self.models[model_name].error_message = error_msg
                        return False
                    print(f"[SUCCESS] Pulled model {model_name}")
                except FileNotFoundError:
                    error_msg = (
                        f"'ollama' command not found. Install Ollama and ensure it's on PATH, "
                        f"or pull the model manually: ollama pull {model_name}"
                    )
                    print(f"[ERROR] {error_msg}")
                    self.models[model_name].status = ModelStatus.ERROR
                    self.models[model_name].error_message = error_msg
                    return False
                except Exception as e:
                    error_msg = f"Error pulling model {model_name}: {e}"
                    print(f"[ERROR] {error_msg}")
                    self.models[model_name].status = ModelStatus.ERROR
                    self.models[model_name].error_message = error_msg
                    return False
            
            # Send a test generation request to warm up the model
            client = self._get_http_client()
            test_prompt = "Hello"
            
            request_data = {
                "model": model_name,
                "prompt": test_prompt,
                "stream": False
            }
            
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=request_data
            )
            
            if response.status_code == 200:
                load_time = time.time() - start_time
                self.models[model_name].status = ModelStatus.READY
                self.models[model_name].load_time = load_time
                
                if show_progress:
                    print(f"[SUCCESS] Model {model_name} loaded in {load_time:.1f}s")
                return True
            else:
                error_msg = f"Failed to load model: HTTP {response.status_code}"
                print(f"[ERROR] {error_msg}")
                self.models[model_name].status = ModelStatus.ERROR
                self.models[model_name].error_message = error_msg
                return False
                
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to load model {model_name}: {error_msg}")
            self.models[model_name].status = ModelStatus.ERROR
            self.models[model_name].error_message = error_msg
            return False
    
    async def generate(
        self,
        model_name: str,
        prompt: str,
        system: Optional[str] = None,
        system_message: Optional[str] = None,  # Alias for system (compatibility)
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        num_ctx: int = 16384,  # CRITICAL: Context window size (default 16K tokens for ~64K chars)
        **kwargs
    ) -> GenerationResponse:
        """
        Generate text using a model.
        
        Automatically loads model if not already loaded.
        
        Args:
            model_name: Name of the model to use
            prompt: The prompt to generate from
            system: System prompt (optional)
            system_message: Alias for system (for compatibility with enhanced_generation)
            temperature: Sampling temperature (0.0 = deterministic)
            max_tokens: Maximum tokens to generate (optional)
            num_ctx: Context window size in tokens (default 16384 for comprehensive context)
                     - 4096 = ~16K chars (basic)
                     - 8192 = ~32K chars (standard)
                     - 16384 = ~64K chars (comprehensive - RECOMMENDED for chat)
                     - 32768 = ~128K chars (maximum, requires more VRAM)
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResponse with content and metadata
        """
        # Handle system_message alias
        if system_message and not system:
            system = system_message
        
        start_time = time.time()
        
        # Ensure model is loaded
        if model_name not in self.models or self.models[model_name].status != ModelStatus.READY:
            loaded = await self.load_model(model_name, show_progress=True)
            if not loaded:
                return GenerationResponse(
                    content="",
                    model_used=model_name,
                    generation_time=time.time() - start_time,
                    success=False,
                    error_message=self.models[model_name].error_message
                )
        
        # Set status to in use
        self.models[model_name].status = ModelStatus.IN_USE
        self.models[model_name].total_requests += 1
        self.models[model_name].last_used = datetime.now()
        
        try:
            client = self._get_http_client()
            
            # Build request with expanded context window
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_ctx": num_ctx  # CRITICAL: Expand context window for full context retention
                }
            }
            
            if system:
                request_data["system"] = system
            
            if max_tokens:
                request_data["options"]["num_predict"] = max_tokens
            
            # Merge additional options (but don't override num_ctx)
            for k, v in kwargs.items():
                if k != "num_ctx":  # Preserve explicit num_ctx
                    request_data["options"][k] = v
            
            # Send request
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=request_data
            )
            
            generation_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("response", "")
                
                # Update model info
                self.models[model_name].status = ModelStatus.READY
                self.models[model_name].successful_requests += 1
                
                return GenerationResponse(
                    content=content,
                    model_used=model_name,
                    generation_time=generation_time,
                    tokens_generated=len(content.split()),  # Approximate
                    success=True
                )
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.models[model_name].status = ModelStatus.READY
                return GenerationResponse(
                    content="",
                    model_used=model_name,
                    generation_time=generation_time,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e)
            print(f"[ERROR] Generation failed: {error_msg}")
            self.models[model_name].status = ModelStatus.READY
            return GenerationResponse(
                content="",
                model_used=model_name,
                generation_time=generation_time,
                success=False,
                error_message=error_msg
            )
    
    async def generate_stream(
        self,
        model_name: str,
        prompt: str,
        system: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        num_ctx: int = 16384,
        **kwargs
    ):
        """
        Generate text using a model with streaming.
        
        Yields:
            Chunks of generated text
        """
        # Handle system_message alias
        if system_message and not system:
            system = system_message
        
        # Ensure model is loaded
        if model_name not in self.models or self.models[model_name].status != ModelStatus.READY:
            loaded = await self.load_model(model_name, show_progress=True)
            if not loaded:
                yield f"Error: Failed to load model {model_name}"
                return
        
        # Set status to in use
        self.models[model_name].status = ModelStatus.IN_USE
        self.models[model_name].total_requests += 1
        self.models[model_name].last_used = datetime.now()
        
        try:
            client = self._get_http_client()
            
            # Build request
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "stream": True,  # Enable streaming
                "options": {
                    "temperature": temperature,
                    "num_ctx": num_ctx
                }
            }
            
            if system:
                request_data["system"] = system
            
            if max_tokens:
                request_data["options"]["num_predict"] = max_tokens
            
            # Merge additional options
            for k, v in kwargs.items():
                if k != "num_ctx":
                    request_data["options"][k] = v
            
            # Stream response
            async with client.stream("POST", f"{self.base_url}/api/generate", json=request_data) as response:
                if response.status_code != 200:
                    yield f"Error: HTTP {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    try:
                        import json
                        chunk_data = json.loads(line)
                        
                        if "response" in chunk_data:
                            yield chunk_data["response"]
                            
                        if chunk_data.get("done", False):
                            break
                    except Exception:
                        continue
                        
            self.models[model_name].status = ModelStatus.READY
            self.models[model_name].successful_requests += 1

        except Exception as e:
            print(f"[ERROR] Stream generation failed: {e}")
            self.models[model_name].status = ModelStatus.READY
            yield f"Error: {str(e)}"
    
    def get_model_status(self, model_name: str) -> ModelStatus:
        """
        Get current status of a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelStatus enum value
        """
        if model_name in self.models:
            return self.models[model_name].status
        return ModelStatus.NOT_LOADED
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        Get detailed information about a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            ModelInfo or None if model not tracked
        """
        return self.models.get(model_name)
    
    def get_all_model_info(self) -> Dict[str, ModelInfo]:
        """Get information about all tracked models"""
        return self.models.copy()
    
    async def initialize_persistent_models(self) -> bool:
        """
        Load the 2 persistent models at startup (VRAM-optimized for 12GB).
        
        Persistent models:
        - codellama:7b-instruct-q4_K_M (3.8GB)
        - llama3:8b-instruct-q4_K_M (4.7GB)
        Total: 8.5GB (fits in 12GB VRAM)
        
        Returns:
            True if all persistent models loaded successfully
        """
        persistent = ["codellama:7b-instruct-q4_K_M", "llama3:8b-instruct-q4_K_M"]
        
        # Verify total size fits in VRAM
        total_size = sum(self.model_sizes.get(m, 5.0) for m in persistent)
        if total_size > self.vram_limit_gb:
            print(f"[ERROR] Persistent models ({total_size}GB) exceed VRAM limit ({self.vram_limit_gb}GB)")
            return False
        
        print(f"[INFO] Loading persistent models ({total_size}GB / {self.vram_limit_gb}GB VRAM)...")
        
        all_success = True
        for model in persistent:
            success = await self.load_model(model, show_progress=True)
            if success:
                self.persistent_models.add(model)
                self.active_models.add(model)
            else:
                all_success = False
        
        if all_success:
            print(f"[SUCCESS] Persistent models loaded: {len(self.persistent_models)}/2")
        else:
            print(f"[WARN] Some persistent models failed to load")
        
        return all_success
    
    async def ensure_model_available(self, target_model: str, show_progress: bool = True) -> bool:
        """
        Ensure target model is loaded, swapping if necessary (VRAM-aware).
        
        Logic:
        1. If target is already loaded → return immediately ⚡
        2. If target is persistent → should already be loaded
        3. If target requires swap → unload non-persistent, load target ⚠️
        
        Args:
            target_model: Model to ensure is loaded
            show_progress: Show progress messages
            
        Returns:
            True if model is now available
        """
        # Already loaded?
        if target_model in self.active_models:
            if show_progress:
                print(f"[INFO] Model {target_model} already loaded")
            return True
        
        # Calculate VRAM requirements
        target_size = self.model_sizes.get(target_model, 5.0)
        current_usage = sum(self.model_sizes.get(m, 0) for m in self.active_models)
        available = self.vram_limit_gb - current_usage
        
        if show_progress:
            print(f"[INFO] VRAM: {current_usage:.1f}GB used, {available:.1f}GB available, need {target_size:.1f}GB")
        
        # Need to free space?
        if target_size > available:
            if show_progress:
                print(f"[INFO] Insufficient VRAM. Unloading models to make space...")
            
            # Unload non-persistent models first
            to_unload = [m for m in self.active_models if m not in self.persistent_models]
            
            if not to_unload and target_model not in self.persistent_models:
                # Must temporarily unload a persistent model (rare)
                if show_progress:
                    print("[WARN] Must temporarily unload persistent model for diagram generation")
                # Unload the larger persistent model (llama3 is bigger)
                to_unload = ["llama3:8b-instruct-q4_K_M"]
            
            for model in to_unload:
                await self.unload_model(model, show_progress=show_progress)
        
        # Load target model
        if show_progress:
            print(f"[INFO] Loading {target_model}...")
        
        success = await self.load_model(target_model, show_progress=show_progress)
        if success:
            self.active_models.add(target_model)
        
        return success
    
    async def unload_all_models(self):
        """Unload all loaded Ollama models to free VRAM"""
        loaded_models = [
            model_name for model_name, model_info in self.models.items()
            if model_info.status == ModelStatus.LOADED
        ]
        
        for model_name in loaded_models:
            try:
                await self.unload_model(model_name, show_progress=False)
                print(f"[OLLAMA] Unloaded {model_name}")
            except Exception as e:
                print(f"[OLLAMA] Failed to unload {model_name}: {e}")
        
        if loaded_models:
            print(f"[OLLAMA] ✅ Unloaded {len(loaded_models)} models")
    
    async def unload_model(self, model_name: str, show_progress: bool = True):
        """
        Unload a model from VRAM.
        
        Uses Ollama API with keep_alive=0 to immediately free VRAM.
        
        Args:
            model_name: Model to unload
            show_progress: Show progress messages
        """
        if model_name not in self.active_models:
            return
        
        try:
            if show_progress:
                print(f"[INFO] Unloading {model_name}...")
            
            client = self._get_http_client()
            
            # Send empty request with keep_alive=0 to unload immediately
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "keep_alive": 0  # Unload immediately
                }
            )
            
            if response.status_code == 200:
                self.active_models.discard(model_name)
                if model_name in self.models:
                    self.models[model_name].status = ModelStatus.NOT_LOADED
                
                size = self.model_sizes.get(model_name, 0)
                if show_progress:
                    print(f"[SUCCESS] Unloaded {model_name} (freed {size:.1f}GB VRAM)")
            else:
                if show_progress:
                    print(f"[WARN] Unload returned {response.status_code}")
        
        except Exception as e:
            if show_progress:
                print(f"[ERROR] Failed to unload {model_name}: {e}")
    
    def get_vram_usage(self) -> Dict[str, Any]:
        """
        Get current VRAM usage information.
        
        Returns:
            Dict with usage stats
        """
        used_gb = sum(self.model_sizes.get(m, 0) for m in self.active_models)
        available_gb = self.vram_limit_gb - used_gb
        
        return {
            "used_gb": round(used_gb, 1),
            "available_gb": round(available_gb, 1),
            "total_gb": self.vram_limit_gb,
            "active_models": list(self.active_models),
            "persistent_models": list(self.persistent_models),
            "usage_percent": round((used_gb / self.vram_limit_gb) * 100, 1)
        }
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Global instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client(base_url: str = "http://localhost:11434", timeout: int = 120, vram_limit_gb: float = 12.0) -> OllamaClient:
    """Get or create global Ollama client instance"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient(base_url, timeout, vram_limit_gb)
    return _ollama_client


# Alias for compatibility
get_client = get_ollama_client

