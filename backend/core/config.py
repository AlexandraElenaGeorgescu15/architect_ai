"""
Application configuration using Pydantic settings.
"""

from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Architect.AI API"
    app_version: str = "3.5.2"
    debug: bool = False
    base_path: Path = Path(__file__).parent.parent.parent  # Base path for the application (project root)
    
    # Target repository path - the USER's project to analyze (NOT Architect.AI itself)
    # Set this to the path of the project you want to analyze
    # If not set, will try to detect user project directories automatically
    target_repo_path: Optional[str] = None
    
    # Database
    database_url: str = f"sqlite:///{Path(__file__).parent.parent.parent / 'data' / 'architect_ai.db'}"
    
    # Redis (optional)
    redis_url: Optional[str] = None
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "https://architect-ai-mvm.vercel.app"]
    
    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None  # Gemini API key
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Alias for google_api_key, for clarity
    xai_api_key: Optional[str] = None  # Grok API key (X.AI)
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    
    # Model Routing Defaults (centralized to avoid magic strings scattered in code)
    # These are used as fallbacks when no fine-tuned or configured model is available
    # Updated Jan 2026 - Using official Gemini stable models
    default_mermaid_models: list[str] = ["llama3", "codellama", "gemini-2.5-flash"]
    default_html_models: list[str] = ["llama3", "gemini-2.5-flash", "gpt-4o"]
    default_code_models: list[str] = ["codellama", "llama3", "gemini-2.5-flash"]
    default_pm_models: list[str] = ["llama3", "gemini-2.5-flash", "gpt-4o"]
    default_fallback_models: list[str] = ["ollama:llama3", "gemini:gemini-2.5-flash"]
    default_chat_model: str = "gemini-2.5-flash"  # Best price-performance model
    
    # RAG
    rag_index_path: str = str(Path(__file__).parent.parent.parent / "rag" / "index")
    rag_max_chunks: int = 18
    
    # Training
    training_threshold: int = 50  # Examples needed to trigger training
    training_batch_size: int = 4
    training_epochs: int = 3
    
    # Data directories (centralized to avoid circular imports)
    meeting_notes_dir: Path = Path(__file__).parent.parent.parent / "data" / "meeting_notes"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    json_logging: bool = False  # Enable JSON structured logging
    
    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090  # Prometheus metrics port
    
    # Performance
    enable_lazy_loading: bool = True
    cache_default_ttl: int = 3600  # Default cache TTL in seconds
    
    # Generation Timeouts (in seconds)
    generation_timeout: int = 300  # Total timeout for artifact generation (increased from 120)
    model_attempt_timeout: int = 120  # Timeout per model attempt (increased from 60)
    cloud_fallback_timeout: int = 120  # Timeout for cloud API calls (increased from 90)
    
    # ==========================================================================
    # LLM-as-a-Judge Validation Settings
    # ==========================================================================
    # Uses a local LLM to evaluate artifact quality alongside rule-based validation
    llm_judge_enabled: bool = True  # Enable/disable LLM-as-a-Judge
    llm_judge_weight: float = 0.4  # Weight of LLM score (0.0-1.0). 0.4 = 40% LLM, 60% rule-based
    llm_judge_timeout: int = 60  # Timeout in seconds for LLM judge call (increased from 30)
    llm_judge_preferred_models: list[str] = [
        "mistral-nemo:12b-instruct-2407-q4_K_M",  # Best reasoning
        "llama3:8b-instruct-q4_K_M",  # Good fallback
        "mistral:7b-instruct-q4_K_M",  # Fast option
        "llama3.2:3b",  # Ultra fast fallback
        "llama3:latest",  # Generic fallback
    ]
    
    # ==========================================================================
    # Ollama (Local Models) Settings
    # ==========================================================================
    ollama_warmup_enabled: bool = True  # Pre-load first model into memory on startup
    ollama_base_url: str = "http://localhost:11434"  # Ollama API endpoint
    
    # ==========================================================================
    # Token/Context Window Limits (CENTRALIZED - use these everywhere!)
    # ==========================================================================
    # These limits prevent context overflow and ensure consistent behavior
    # across all services that interact with LLMs.
    
    # Context assembly budget (for building RAG context)
    context_assembly_max_tokens: int = 12000  # Increased from 8000
    
    # Local model context window (Ollama num_ctx)
    local_model_context_window: int = 32768  # Increased from 16384 for modern models
    
    # Cloud API max output tokens
    cloud_api_max_tokens: int = 8192  # Increased from 4096
    
    # Prompt sanitization max length (characters, not tokens)
    prompt_sanitize_max_length: int = 100000  # Increased from 32000 for large HTML files
    
    # Chat-specific limits
    chat_max_conversation_messages: int = 30  # Increased from 15
    chat_max_snippet_length: int = 5000  # Increased from 2500
    chat_max_rag_snippets: int = 20  # Increased from 12
    
    class Config:
        env_file = [".env", "../.env", "../../.env"]  # Try multiple locations
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Also load from environment variables directly
        extra = "ignore"


    @model_validator(mode='after')
    def sync_google_keys(self) -> 'Settings':
        """Synchronize google_api_key and gemini_api_key if only one is provided."""
        if self.gemini_api_key and not self.google_api_key:
            self.google_api_key = self.gemini_api_key
        elif self.google_api_key and not self.gemini_api_key:
            self.gemini_api_key = self.google_api_key
        return self


# Global settings instance
settings = Settings()
