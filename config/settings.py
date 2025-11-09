"""
Central Configuration for Architect.AI
Manages environment variables and global settings
"""

import os
from pathlib import Path
from typing import Optional


# ============================================================================
# ChromaDB Configuration (Centralized)
# ============================================================================
def configure_chromadb_telemetry():
    """
    Configure ChromaDB telemetry settings.
    Call this ONCE at application startup before any ChromaDB imports.
    """
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"


# Auto-configure on module import
configure_chromadb_telemetry()


# ============================================================================
# Application Paths
# ============================================================================
ROOT_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
RAG_INDEX_DIR = ROOT_DIR / "rag" / "index"
MODELS_DIR = ROOT_DIR / "finetuned_models"
TRAINING_JOBS_DIR = ROOT_DIR / "training_jobs"

# Ensure directories exist
OUTPUTS_DIR.mkdir(exist_ok=True)
RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)
TRAINING_JOBS_DIR.mkdir(exist_ok=True)


# ============================================================================
# API Keys & Providers
# ============================================================================
def get_api_key(provider: str) -> Optional[str]:
    """Get API key for a specific provider"""
    key_map = {
        'groq': 'GROQ_API_KEY',
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'huggingface': 'HF_TOKEN',
    }
    env_var = key_map.get(provider.lower())
    if env_var:
        return os.getenv(env_var)
    return None


def has_api_key() -> bool:
    """Check if at least one AI provider API key is configured"""
    return any([
        get_api_key('groq'),
        get_api_key('openai'),
        get_api_key('gemini')
    ])


# ============================================================================
# Application Settings
# ============================================================================
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))

# Monitoring
ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'False').lower() == 'true'
METRICS_PORT = int(os.getenv('METRICS_PORT', '9090'))


# ============================================================================
# Validation
# ============================================================================
def validate_configuration():
    """
    Validate that required configuration is present.
    Raises ValueError if critical settings are missing.
    """
    # Check for at least one AI provider (unless using Ollama)
    if not has_api_key():
        # Try to check if Ollama is available
        try:
            import httpx
            response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
            if response.status_code != 200:
                raise ValueError(
                    "No AI provider configured. "
                    "Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY in .env file, "
                    "or ensure Ollama is running."
                )
        except Exception:
            print(
                "[WARN] No AI provider API keys found and Ollama not available. "
                "Set at least one API key in .env file."
            )
    
    return True


# ============================================================================
# Environment Loading
# ============================================================================
def load_environment():
    """Load environment variables from .env file if it exists"""
    env_file = ROOT_DIR / '.env'
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"[OK] Loaded environment from {env_file}")
        except ImportError:
            print("[WARN] python-dotenv not installed. Install with: pip install python-dotenv")
    else:
        print(f"[INFO] No .env file found at {env_file}. Using environment variables.")


# Auto-load on module import
load_environment()
