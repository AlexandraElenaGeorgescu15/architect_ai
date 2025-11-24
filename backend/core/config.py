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
    app_version: str = "1.0.0"
    debug: bool = False
    base_path: Path = Path(__file__).parent.parent.parent  # Base path for the application (project root)
    
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
    
    # RAG
    rag_index_path: str = str(Path(__file__).parent.parent.parent / "rag" / "index")
    rag_max_chunks: int = 18
    
    # Training
    training_threshold: int = 50  # Examples needed to trigger training
    training_batch_size: int = 4
    training_epochs: int = 3
    
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
    
    class Config:
        env_file = [".env", "../.env", "../../.env"]  # Try multiple locations
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Also load from environment variables directly
        extra = "ignore"


# Global settings instance
settings = Settings()
