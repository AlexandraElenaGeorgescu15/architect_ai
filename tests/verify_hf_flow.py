
import asyncio
import sys
import logging
from pathlib import Path
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import settings
from backend.core.logger import get_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY_HF")

async def test_hf_flow():
    """
    Test the HuggingFace model download and conversion flow.
    """
    try:
        from backend.services.huggingface_service import get_service as get_hf_service
        from backend.services.model_service import get_service as get_model_service
        
        hf_service = get_hf_service()
        model_service = get_model_service()
        
        # 1. Download a small valid GGUF model
        # using a very small model for speed: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0' 
        # But we need a GGUF version. 'TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF' is good.
        test_model = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
        
        print(f"\n--- Starting Download Test for {test_model} ---")
        result = await hf_service.download_model(test_model, convert_to_ollama=True)
        
        print(f"Download Result: {result}")
        
        if not result["success"]:
            print("❌ Download failed!")
            return
            
        ollama_name = result.get("ollama_name")
        print(f"✅ Download successful. Ollama name: {ollama_name}")
        
        # 2. Verify Registration in ModelService
        print(f"\n--- Verifying Model Registration ---")
        # Force refresh models
        await model_service.list_models(force_refresh=True)
        
        # Check by HF ID
        hf_key = f"huggingface:{test_model.replace('/', '-')}"
        if hf_key in model_service.models:
            print(f"✅ Found HF model in registry: {hf_key}")
        else:
            print(f"❌ Could not find {hf_key} in registry")
            
        # Check by Ollama ID
        if ollama_name:
            ollama_key = f"ollama:{ollama_name}"
            if ollama_key in model_service.models:
                print(f"✅ Found Ollama converted model in registry: {ollama_key}")
            else:
                print(f"❌ Could not find {ollama_key} in registry")
                
        # 3. Test Generation (if Ollama is available)
        if ollama_name:
            print(f"\n--- Testing Generation with {ollama_name} ---")
            
            # Check if ollama is running
            if shutil.which("ollama"):
                import subprocess
                # Simple run check
                cmd = f'ollama run {ollama_name} "Say hello!"'
                print(f"Running: {cmd}")
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    print(f"✅ Generation successful!")
                    print(f"Output: {stdout.decode().strip()}")
                else:
                    print(f"❌ Generation failed: {stderr.decode()}")
            else:
                print("⚠️ Ollama not found, skipping generation test")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hf_flow())
