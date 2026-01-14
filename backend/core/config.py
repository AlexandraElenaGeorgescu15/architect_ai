"""
Application configuration using Pydantic settings.
"""

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
    cors_origins: list[str] = ["*"]
    
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
    default_mermaid_models: list[str] = ["llama3", "codellama", "gemini-2.0-flash-exp"]
    default_html_models: list[str] = ["llama3", "gemini-2.0-flash-exp", "gpt-4-turbo"]
    default_code_models: list[str] = ["codellama", "llama3", "gemini-2.0-flash-exp"]
    default_pm_models: list[str] = ["llama3", "gemini-2.0-flash-exp", "gpt-4-turbo"]
    default_fallback_models: list[str] = ["ollama:llama3", "gemini:gemini-2.0-flash-exp"]
    default_chat_model: str = "gemini-2.0-flash-exp"  # Default model for chat/conversational AI
    
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
    generation_timeout: int = 120  # Total timeout for artifact generation
    model_attempt_timeout: int = 60  # Timeout per model attempt
    cloud_fallback_timeout: int = 90  # Timeout for cloud API calls
    
    class Config:
        env_file = [".env", "../.env", "../../.env"]  # Try multiple locations
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Also load from environment variables directly
        extra = "ignore"


# Global settings instance
settings = Settings()
