"""
HuggingFace Model Service - Search, download, and manage models from HuggingFace.
"""

import sys
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Awaitable
import logging
import asyncio
import subprocess
import json

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Optional imports for HuggingFace
try:
    from huggingface_hub import HfApi, hf_hub_download, list_models
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logger.warning("huggingface_hub not available. Install with: pip install huggingface_hub")


async def _run_subprocess(command: str, *_, **kwargs) -> subprocess.CompletedProcess:
    """
    Cross-platform subprocess execution that works reliably on Windows.

    Design:
        - Uses blocking subprocess.run under the hood.
        - Wraps it with asyncio.to_thread so callers can still 'await' it.
        - Ignores low-level asyncio subprocess APIs to avoid NotImplementedError
          on certain Windows event loop implementations.

    Args:
        command: Shell command to execute (string form).
        timeout (kwarg, optional): Max seconds to wait before killing the process.
    """
    timeout = kwargs.pop("timeout", None)

    def _inner() -> subprocess.CompletedProcess:
        full_command = command if isinstance(command, str) else " ".join(command)
        return subprocess.run(
            full_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,  # we inspect returncode manually
            timeout=timeout,
        )

    return await asyncio.to_thread(_inner)


class HuggingFaceService:
    """
    Service for searching and downloading models from HuggingFace.
    
    Features:
    - Search models by name, tags, task
    - Download models to local storage
    - Convert models to Ollama format
    - Track downloaded models
    """
    
    def __init__(self):
        """Initialize HuggingFace Service."""
        self.api = HfApi() if HUGGINGFACE_AVAILABLE else None
        self.downloaded_models: Dict[str, Dict[str, Any]] = {}
        self.downloads_dir = Path("models/huggingface")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Track active downloads
        self.active_downloads: Dict[str, Dict[str, Any]] = {}  # model_id -> {status, error, progress}
        
        # Load downloaded models registry
        self._load_registry()
        
        if not HUGGINGFACE_AVAILABLE:
            logger.warning("HuggingFace Hub not available. Install with: pip install huggingface_hub")
        
        logger.info("HuggingFace Service initialized")
    
    def _load_registry(self):
        """Load registry of downloaded models."""
        registry_file = self.downloads_dir / "registry.json"
        if registry_file.exists():
            try:
                with open(registry_file, 'r', encoding='utf-8') as f:
                    self.downloaded_models = json.load(f)
            except Exception as e:
                logger.error(f"Error loading HuggingFace registry: {e}")
    
    def _save_registry(self):
        """Save registry of downloaded models."""
        registry_file = self.downloads_dir / "registry.json"
        try:
            with open(registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.downloaded_models, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving HuggingFace registry: {e}")
    
    async def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for models on HuggingFace.
        
        Args:
            query: Search query (model name, description, etc.)
            task: Task type filter (e.g., "text-generation", "code-generation")
            limit: Maximum number of results
        
        Returns:
            List of model information dictionaries
        """
        if not HUGGINGFACE_AVAILABLE:
            return []
        
        try:
            # Search models
            models = list_models(
                search=query,
                task=task,
                limit=limit,
                sort="downloads",
                direction=-1
            )
            
            results = []
            for model in models:
                results.append({
                    "id": model.id,
                    "author": model.author if hasattr(model, 'author') else "unknown",
                    "downloads": model.downloads if hasattr(model, 'downloads') else 0,
                    "likes": model.likes if hasattr(model, 'likes') else 0,
                    "tags": model.tags if hasattr(model, 'tags') else [],
                    "pipeline_tag": model.pipeline_tag if hasattr(model, 'pipeline_tag') else None,
                    "model_type": model.model_type if hasattr(model, 'model_type') else None,
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching HuggingFace models: {e}")
            return []
    
    async def download_model(
        self,
        model_id: str,
        convert_to_ollama: bool = True
    ) -> Dict[str, Any]:
        """
        Download a model from HuggingFace.
        
        Args:
            model_id: HuggingFace model ID (e.g., "codellama/CodeLlama-7b-Instruct-hf")
            convert_to_ollama: Whether to convert to Ollama format after download
        
        Returns:
            Dictionary with download status and model info
        """
        if not HUGGINGFACE_AVAILABLE:
            error_msg = "HuggingFace Hub not available. Install with: pip install huggingface_hub"
            logger.error(error_msg)
            self.active_downloads[model_id] = {
                "status": "failed",
                "error": error_msg,
                "progress": 0.0
            }
            return {
                "success": False,
                "error": error_msg
            }
        
        # Mark download as started
        self.active_downloads[model_id] = {
            "status": "downloading",
            "error": None,
            "progress": 0.0
        }
        
        try:
            # Check if already downloaded
            if model_id in self.downloaded_models:
                return {
                    "success": True,
                    "message": f"Model {model_id} already downloaded",
                    "model_id": model_id,
                    "path": self.downloaded_models[model_id].get("path")
                }
            
            # Download model files
            model_dir = self.downloads_dir / model_id.replace("/", "_")
            model_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"📥 [HF_DOWNLOAD] Starting download for {model_id}...")
            
            # Update progress
            self.active_downloads[model_id]["progress"] = 0.1
            
            # Try to find and download GGUF files first (for Ollama compatibility)
            downloaded_path = None
            try:
                if self.api:
                    logger.info(f"🔍 [HF_DOWNLOAD] Fetching model info for {model_id}...")
                    self.active_downloads[model_id]["progress"] = 0.2
                    model_info = self.api.model_info(model_id)
                    # Get file list from model info
                    model_files = [f.rfilename for f in model_info.siblings] if hasattr(model_info, 'siblings') else []
                    gguf_files = [f for f in model_files if f.endswith(".gguf")]
                    
                    if gguf_files:
                        # Get file sizes to download the largest (best quality)
                        gguf_sizes = {}
                        try:
                            if hasattr(model_info, 'siblings') and model_info.siblings:
                                for file in model_info.siblings:
                                    if file.rfilename.endswith(".gguf"):
                                        file_size = getattr(file, 'size', None)
                                        # Only add if size is not None and is a valid number
                                        if file_size is not None and isinstance(file_size, (int, float)) and file_size > 0:
                                            gguf_sizes[file.rfilename] = file_size
                        except (AttributeError, KeyError, TypeError) as e:
                            logger.debug(f"Could not get GGUF file sizes for {model_id}: {e}")
                        
                        if gguf_sizes:
                            # Filter out None values before max
                            valid_sizes = {k: v for k, v in gguf_sizes.items() if v is not None and v > 0}
                            if valid_sizes:
                                largest_gguf = max(valid_sizes.items(), key=lambda x: x[1])[0]
                                logger.info(f"⬇️ [HF_DOWNLOAD] Downloading GGUF file: {largest_gguf} (size: {gguf_sizes[largest_gguf] / (1024**3):.2f} GB)")
                                self.active_downloads[model_id]["progress"] = 0.3
                                downloaded_path = hf_hub_download(
                                    repo_id=model_id,
                                    filename=largest_gguf,
                                    cache_dir=str(model_dir),
                                    force_download=False  # Allow resume (resume_download is deprecated)
                                )
                                logger.info(f"✅ [HF_DOWNLOAD] Downloaded GGUF file: {largest_gguf}")
                                self.active_downloads[model_id]["progress"] = 0.8
                            else:
                                # Fallback: download first GGUF file if sizes are invalid
                                downloaded_path = hf_hub_download(
                                    repo_id=model_id,
                                    filename=gguf_files[0],
                                    cache_dir=str(model_dir)
                                )
                                logger.info(f"Downloaded GGUF file: {gguf_files[0]} (size info unavailable)")
                        else:
                            # Download first GGUF file if no size info available
                            downloaded_path = hf_hub_download(
                                repo_id=model_id,
                                filename=gguf_files[0],
                                cache_dir=str(model_dir)
                            )
                            logger.info(f"Downloaded GGUF file: {gguf_files[0]}")
                
                if not downloaded_path:
                    # No GGUF file, try to download config.json as fallback
                    try:
                        downloaded_path = hf_hub_download(
                            repo_id=model_id,
                            filename="config.json",
                            cache_dir=str(model_dir)
                        )
                        logger.warning(f"No GGUF file found for {model_id}, downloaded config.json")
                    except Exception as config_error:
                        logger.error(f"Failed to download config.json for {model_id}: {config_error}")
                        raise ValueError(f"Model {model_id} not found or has no downloadable files (GGUF or config.json)")
            except Exception as e:
                logger.warning(f"Error finding GGUF files: {e}")
                if not downloaded_path:
                    # Try config.json as last resort
                    try:
                        downloaded_path = hf_hub_download(
                            repo_id=model_id,
                            filename="config.json",
                            cache_dir=str(model_dir)
                        )
                        logger.info(f"Downloaded config.json as fallback for {model_id}")
                    except Exception as config_error:
                        logger.error(f"Failed to download config.json for {model_id}: {config_error}")
                        raise ValueError(f"Model {model_id} not found or inaccessible: {config_error}")
            
            # Get the actual download directory (hf_hub_download may use cache subdirectories)
            actual_download_path = Path(downloaded_path) if downloaded_path else None
            actual_model_dir = actual_download_path.parent if actual_download_path else model_dir
            
            # Register downloaded model
            logger.info(f"📝 [HF_DOWNLOAD] Registering downloaded model {model_id}...")
            logger.info(f"📁 [HF_DOWNLOAD] Downloaded to: {actual_download_path}")
            self.downloaded_models[model_id] = {
                "id": model_id,
                "path": str(model_dir),
                "actual_file_path": str(actual_download_path) if actual_download_path else None,
                "downloaded_at": str(actual_model_dir),
                "convert_to_ollama": convert_to_ollama
            }
            self._save_registry()
            self.active_downloads[model_id]["progress"] = 0.9
            
            # Register in ModelService for UI visibility
            try:
                from backend.services.model_service import get_service as get_model_service
                from backend.models.dto import ModelInfoDTO
                model_service = get_model_service()
                
                # Create model ID in standard format
                clean_model_id = f"huggingface:{model_id.replace('/', '-')}"
                
                # Register the downloaded model
                if clean_model_id not in model_service.models:
                    model_service.models[clean_model_id] = ModelInfoDTO(
                        id=clean_model_id,
                        name=f"{model_id} (HuggingFace)",
                        provider="huggingface",
                        status="downloaded",
                        is_trained=False,
                        metadata={
                            "huggingface_id": model_id,
                            "path": str(model_dir),
                            "source": "huggingface"
                        }
                    )
                    model_service._save_registry()
                    logger.info(f"✅ [HF_DOWNLOAD] Model registered in ModelService: {clean_model_id}")
            except Exception as e:
                logger.warning(f"⚠️ [HF_DOWNLOAD] Failed to register in ModelService: {e}")
            
            # Convert to Ollama format if requested
            if convert_to_ollama:
                logger.info(f"🔄 [HF_DOWNLOAD] Converting {model_id} to Ollama format...")
                self.active_downloads[model_id]["progress"] = 0.95
                # Pass the actual file path if it's a GGUF, otherwise pass the directory
                gguf_file_path = None
                if actual_download_path and str(actual_download_path).endswith('.gguf'):
                    gguf_file_path = actual_download_path
                conversion_result = await self._convert_to_ollama(model_id, model_dir, gguf_file_path=gguf_file_path)
                if conversion_result.get("success"):
                    return {
                        "success": True,
                        "message": f"Model {model_id} downloaded and converted to Ollama",
                        "model_id": model_id,
                        "ollama_name": conversion_result.get("ollama_name"),
                        "path": str(model_dir),
                        "conversion": conversion_result
                    }
                else:
                    # Download succeeded but conversion failed
                    return {
                        "success": True,  # Download was successful
                        "message": f"Model {model_id} downloaded but conversion to Ollama failed",
                        "model_id": model_id,
                        "path": str(model_dir),
                        "conversion": conversion_result,
                        "warning": conversion_result.get("error", "Conversion failed")
                    }
            
            result = {
                "success": True,
                "message": f"Model {model_id} downloaded successfully",
                "model_id": model_id,
                "path": str(model_dir)
            }
            self.active_downloads[model_id] = {
                "status": "completed",
                "error": None,
                "progress": 1.0
            }
            return result
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error downloading model {model_id}: {error_msg}", exc_info=True)
            self.active_downloads[model_id] = {
                "status": "failed",
                "error": error_msg,
                "progress": 0.0
            }
            return {
                "success": False,
                "error": error_msg,
                "model_id": model_id
            }
    
    async def _convert_to_ollama(
        self,
        model_id: str,
        model_dir: Path,
        progress_callback: Optional[Callable[[float, str], Awaitable[None]]] = None,
        gguf_file_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Convert a HuggingFace model to Ollama format.

        Args:
            model_id: HuggingFace model ID
            model_dir: Directory where model was downloaded
            progress_callback: Optional async callback for progress updates
            gguf_file_path: Optional direct path to GGUF file (if known)

        Returns:
            Dict with success status, ollama_name, and message
        """
        try:
            logger.info(f"Converting {model_id} to Ollama format...")
            logger.debug(f"model_dir: {model_dir}, gguf_file_path: {gguf_file_path}")
            
            if progress_callback:
                try:
                    await progress_callback(0.1, "Checking Ollama availability...")
                except Exception:
                    pass  # Ignore callback errors
            
            # Check if Ollama is available
            try:
                result = await _run_subprocess("ollama --version")
                if result.returncode != 0:
                    raise FileNotFoundError("Ollama not found")
            except FileNotFoundError:
                error_msg = "Ollama CLI not found. Please install Ollama from https://ollama.ai"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "ollama_name": None
                }
            
            # Clean model name for Ollama (no slashes, lowercase, max 64 chars)
            ollama_name = model_id.replace("/", "-").replace("_", "-").lower()
            # Ollama model names have a limit
            if len(ollama_name) > 64:
                ollama_name = ollama_name[:64]
            
            if progress_callback:
                try:
                    await progress_callback(0.2, f"Checking if model '{ollama_name}' already exists in Ollama...")
                except Exception:
                    pass
            
            # Check if model is already in Ollama
            try:
                result = await _run_subprocess("ollama list")
                existing_models = (result.stdout or "").lower()
                if ollama_name.lower() in existing_models:
                    logger.info(f"Model {ollama_name} already exists in Ollama")
                    # Register in ModelService
                    await self._register_in_model_service(ollama_name, model_id)
                    return {
                        "success": True,
                        "message": f"Model {ollama_name} already exists in Ollama",
                        "ollama_name": ollama_name,
                        "already_exists": True
                    }
            except Exception as e:
                logger.warning(f"Could not check Ollama models: {e}")
            
            if progress_callback:
                try:
                    await progress_callback(0.3, "Searching for GGUF files...")
                except Exception:
                    pass
            
            # Use provided GGUF path if available, otherwise search for it
            gguf_path = None
            if gguf_file_path and gguf_file_path.exists():
                gguf_path = gguf_file_path
                logger.info(f"Using provided GGUF file path: {gguf_path}")
            else:
                # Try to find GGUF files in the downloaded model (search recursively)
                gguf_files = list(model_dir.rglob("*.gguf"))
                if gguf_files:
                    gguf_path = gguf_files[0]
                    logger.info(f"Found GGUF file via search: {gguf_path}")
            
            if gguf_path:
                # Found GGUF file - use Modelfile approach (most reliable for GGUF)
                logger.info(f"Using GGUF file: {gguf_path}")
                
                if progress_callback:
                    try:
                        await progress_callback(0.4, f"Creating Ollama model '{ollama_name}' from GGUF...")
                    except Exception:
                        pass
                
                # Create a Modelfile for the GGUF (most reliable method)
                # Use forward slashes for the path in Modelfile (works on all platforms)
                gguf_path_str = str(gguf_path).replace("\\", "/")
                modelfile_path = model_dir / f"{ollama_name}.Modelfile"
                modelfile_content = f"""FROM "{gguf_path_str}"
TEMPLATE \"\"\"{{{{ .Prompt }}}}\"\"\"
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
"""
                modelfile_path.write_text(modelfile_content, encoding='utf-8')
                logger.info(f"Created Modelfile at: {modelfile_path}")
                
                # Use ollama create with Modelfile (works reliably with GGUF)
                # Quote the path for Windows compatibility
                modelfile_path_str = str(modelfile_path).replace("\\", "/")
                result = await _run_subprocess(
                    f'ollama create {ollama_name} -f "{modelfile_path_str}"'
                )
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                
                if result.returncode == 0:
                    logger.info(f"Successfully created {ollama_name} in Ollama from GGUF")
                    # Register in ModelService
                    await self._register_in_model_service(ollama_name, model_id)
                    
                    if progress_callback:
                        try:
                            await progress_callback(1.0, f"Model '{ollama_name}' successfully created in Ollama")
                        except Exception:
                            pass
                    
                    return {
                        "success": True,
                        "message": f"Successfully created {model_id} in Ollama as {ollama_name}",
                        "ollama_name": ollama_name,
                        "method": "modelfile"
                    }
                else:
                    # Log the error details for debugging
                    logger.error(f"Ollama create failed. stdout: {stdout}, stderr: {stderr}")
                    
                    # Try direct import as fallback (older Ollama versions)
                    logger.info("Modelfile approach failed, trying direct import...")
                    if progress_callback:
                        try:
                            await progress_callback(0.5, "Trying direct import...")
                        except Exception:
                            pass
                    
                    result = await _run_subprocess(
                        f'ollama import {ollama_name} "{gguf_path_str}"'
                    )
                    stdout = result.stdout or ""
                    stderr = result.stderr or ""
                    
                    if result.returncode == 0:
                        logger.info(f"Successfully imported {ollama_name} to Ollama")
                        await self._register_in_model_service(ollama_name, model_id)
                        return {
                            "success": True,
                            "message": f"Successfully imported {ollama_name} in Ollama",
                            "ollama_name": ollama_name,
                            "method": "import"
                        }
                    else:
                        error_msg = f"Failed to create Ollama model: {stderr or stdout or 'Unknown error'}"
                        logger.error(error_msg)
                        return {
                            "success": False,
                            "error": error_msg,
                            "ollama_name": ollama_name,
                            "suggestion": "Try running the command manually: ollama create " + ollama_name + " -f <modelfile_path>"
                        }
            else:
                # No GGUF file found - try ollama pull if model exists on Ollama Hub
                logger.info(f"No GGUF file found. Attempting to pull from Ollama Hub...")
                if progress_callback:
                    try:
                        await progress_callback(0.6, "No GGUF found, trying Ollama Hub...")
                    except Exception:
                        pass
                
                # Try common model name variations
                possible_names = [
                    ollama_name,
                    model_id.split("/")[-1].lower(),
                    model_id.replace("/", ":").lower(),
                    model_id.split("/")[-1].replace("_", "-").lower()
                ]
                
                for name in possible_names:
                    try:
                        if progress_callback:
                            try:
                                await progress_callback(0.7, f"Trying to pull '{name}' from Ollama Hub...")
                            except Exception:
                                pass
                        
                        # Use timeout for pull as it can take a long time
                        result = await _run_subprocess(f'ollama pull "{name}"', timeout=600)
                        stdout = result.stdout or ""
                        stderr = result.stderr or ""
                        
                        if result.returncode == 0:
                            logger.info(f"Successfully pulled {name} from Ollama Hub")
                            await self._register_in_model_service(name, model_id)
                            return {
                                "success": True,
                                "message": f"Successfully pulled {name} from Ollama Hub",
                                "ollama_name": name,
                                "method": "pull"
                            }
                        else:
                            logger.debug(f"Could not pull {name}: {stderr or stdout}")
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Timeout pulling {name} from Ollama Hub")
                        continue
                    except Exception as e:
                        logger.debug(f"Could not pull {name}: {e}")
                        continue
                
                error_msg = (
                    f"Could not convert {model_id} to Ollama format. "
                    f"Model needs to be in GGUF format or available on Ollama Hub. "
                    f"Downloaded files are in: {model_dir}"
                )
                logger.warning(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "ollama_name": None,
                    "suggestion": "Try downloading a GGUF quantized version of the model"
                }
                
        except Exception as e:
            error_msg = f"Error converting {model_id} to Ollama: {e}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "ollama_name": None
            }
    
    async def _register_in_model_service(self, ollama_name: str, hf_model_id: str):
        """Register the converted model in ModelService."""
        try:
            from backend.services.model_service import get_service as get_model_service
            model_service = get_model_service()
            
            # Create model ID
            model_id = f"ollama:{ollama_name}"
            
            # Check if already registered
            existing = await model_service.get_model(model_id)
            if existing:
                logger.info(f"Model {model_id} already registered in ModelService")
                return
            
            # Register as Ollama model
            from backend.models.dto import ModelInfoDTO
            model_info = ModelInfoDTO(
                id=model_id,
                name=f"{ollama_name} (from {hf_model_id})",
                provider="ollama",
                status="downloaded",
                is_trained=False,
                metadata={
                    "huggingface_id": hf_model_id,
                    "ollama_name": ollama_name,
                    "source": "huggingface"
                }
            )
            
            model_service.models[model_id] = model_info
            model_service._save_registry()
            logger.info(f"Registered {model_id} in ModelService")
        except Exception as e:
            logger.warning(f"Could not register model in ModelService: {e}")
    
    async def list_downloaded_models(self) -> List[Dict[str, Any]]:
        """List all downloaded models."""
        return list(self.downloaded_models.values())
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific model."""
        if not HUGGINGFACE_AVAILABLE:
            return None
        
        try:
            model_info = self.api.model_info(model_id)
            return {
                "id": model_info.id,
                "author": model_info.author if hasattr(model_info, 'author') else "unknown",
                "downloads": model_info.downloads if hasattr(model_info, 'downloads') else 0,
                "likes": model_info.likes if hasattr(model_info, 'likes') else 0,
                "tags": model_info.tags if hasattr(model_info, 'tags') else [],
                "pipeline_tag": model_info.pipeline_tag if hasattr(model_info, 'pipeline_tag') else None,
            }
        except Exception as e:
            logger.error(f"Error getting model info for {model_id}: {e}")
            return None


# Singleton instance
_hf_service: Optional[HuggingFaceService] = None

def get_service() -> HuggingFaceService:
    """Get HuggingFace service instance."""
    global _hf_service
    if _hf_service is None:
        _hf_service = HuggingFaceService()
    return _hf_service

