"""
Ollama Model Downloader

Automatically downloads required Ollama models when needed.
Supports progress tracking and error handling.
"""

import subprocess
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Callable
import asyncio
import httpx


class OllamaModelDownloader:
    """
    Downloads Ollama models automatically.
    
    Features:
    - Check if model is already downloaded
    - Download with progress tracking
    - Error handling and retry logic
    - Integration with artifact model mapper
    """
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize downloader.
        
        Args:
            base_url: Ollama server URL
        """
        self.base_url = base_url.rstrip("/")
        self._http_client = None
    
    def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0))
        return self._http_client
    
    async def check_ollama_running(self) -> bool:
        """
        Check if Ollama server is running.
        
        Returns:
            True if running, False otherwise
        """
        try:
            client = self._get_http_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    async def is_model_downloaded(self, model_name: str) -> bool:
        """
        Check if model is already downloaded.
        
        Args:
            model_name: Name of the model (e.g., "codellama:7b-instruct-q4_K_M")
            
        Returns:
            True if downloaded, False otherwise
        """
        try:
            client = self._get_http_client()
            response = await client.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("models", [])
                # Check exact match or prefix match
                for model in models:
                    model_full_name = model.get("name", "")
                    if model_name == model_full_name or model_full_name.startswith(model_name):
                        return True
            return False
        except Exception as e:
            print(f"[ERROR] Failed to check model availability: {e}")
            return False
    
    async def download_model(
        self, 
        model_name: str, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> bool:
        """
        Download an Ollama model.
        
        Args:
            model_name: Name of the model to download
            progress_callback: Optional callback for progress updates (message, progress)
            
        Returns:
            True if successful, False otherwise
        """
        # Check if already downloaded
        if await self.is_model_downloaded(model_name):
            if progress_callback:
                progress_callback(f"Model {model_name} already downloaded", 100.0)
            return True
        
        # Check if Ollama is running
        if not await self.check_ollama_running():
            print("[ERROR] Ollama server is not running. Please start it first.")
            if progress_callback:
                progress_callback("Ollama server not running", 0.0)
            return False
        
        if progress_callback:
            progress_callback(f"Downloading {model_name}...", 0.0)
        
        try:
            # Use ollama pull command
            process = subprocess.Popen(
                ["ollama", "pull", model_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Read output line by line for progress
            last_progress = 0.0
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Try to extract progress from output
                    # Ollama output format: "pulling manifest...", "pulling 8fdf... 50%"
                    if "%" in line:
                        try:
                            # Extract percentage
                            percent_str = line.split("%")[0].split()[-1]
                            progress = float(percent_str)
                            if progress_callback:
                                progress_callback(f"Downloading {model_name}: {progress:.1f}%", progress)
                            last_progress = progress
                        except Exception:
                            pass
                    elif progress_callback:
                        progress_callback(f"Downloading {model_name}...", last_progress)
            
            process.wait()
            
            if process.returncode == 0:
                if progress_callback:
                    progress_callback(f"Successfully downloaded {model_name}", 100.0)
                return True
            else:
                error = process.stderr.read()
                print(f"[ERROR] Failed to download {model_name}: {error}")
                if progress_callback:
                    progress_callback(f"Failed to download {model_name}", 0.0)
                return False
                
        except FileNotFoundError:
            print("[ERROR] Ollama command not found. Is Ollama installed?")
            if progress_callback:
                progress_callback("Ollama not installed", 0.0)
            return False
        except Exception as e:
            print(f"[ERROR] Exception during download: {e}")
            if progress_callback:
                progress_callback(f"Error: {str(e)}", 0.0)
            return False
    
    async def download_required_models(
        self,
        artifact_types: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, bool]:
        """
        Download all required models for given artifact types.
        
        Args:
            artifact_types: List of artifact types (if None, downloads all)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict mapping model names to download success status
        """
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        
        if artifact_types:
            # Get models for specific artifact types
            models_to_download = set()
            for artifact_type in artifact_types:
                mapping = mapper.get_model_for_artifact(artifact_type)
                models_to_download.add(mapping.base_model)
        else:
            # Download all required models
            models_to_download = set(mapper.list_required_models())
        
        results = {}
        
        total = len(models_to_download)
        current = 0
        
        for model_name in models_to_download:
            current += 1
            if progress_callback:
                progress_callback(
                    f"Downloading model {current}/{total}: {model_name}",
                    (current - 1) / total * 100.0
                )
            
            success = await self.download_model(model_name, progress_callback)
            results[model_name] = success
        
        return results


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download Ollama models")
    parser.add_argument(
        "--model",
        type=str,
        help="Specific model to download (e.g., codellama:7b-instruct-q4_K_M)"
    )
    parser.add_argument(
        "--artifact-types",
        nargs="+",
        help="Artifact types to download models for"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all required models"
    )
    
    args = parser.parse_args()
    
    downloader = OllamaModelDownloader()
    
    def progress_callback(message: str, progress: float):
        print(f"[{progress:.1f}%] {message}")
    
    if args.model:
        # Download specific model
        success = await downloader.download_model(args.model, progress_callback)
        sys.exit(0 if success else 1)
    elif args.artifact_types:
        # Download models for artifact types
        results = await downloader.download_required_models(
            args.artifact_types,
            progress_callback
        )
        all_success = all(results.values())
        sys.exit(0 if all_success else 1)
    elif args.all:
        # Download all required models
        results = await downloader.download_required_models(
            None,
            progress_callback
        )
        all_success = all(results.values())
        sys.exit(0 if all_success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

