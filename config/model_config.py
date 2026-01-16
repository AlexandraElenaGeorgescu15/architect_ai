"""
Dynamic Model Configuration System

Manages context windows, chunk limits, and capabilities for different AI models.
Supports cloud providers and local fine-tuned models.
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class ModelProvider(Enum):
    """Supported AI model providers"""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    LOCAL_FINETUNED = "local_finetuned"


@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    provider: ModelProvider
    context_window: int  # Max tokens
    recommended_context: int  # Recommended usage
    max_chunks: int  # Maximum chunks to retrieve
    recommended_chunks: int  # Recommended chunks
    supports_streaming: bool = True
    supports_function_calling: bool = False
    cost_per_1k_tokens: float = 0.0  # For tracking


class DynamicModelConfig:
    """
    Dynamic model configuration system with context-aware chunk limits
    and context window management
    """

    # Cloud Provider Models (Updated Jan 2026 - Official Google AI docs)
    MODEL_CONFIGS: Dict[str, ModelConfig] = {
        # Google Gemini Models (Updated Jan 2026)
        "gemini-3-pro-preview": ModelConfig(
            name="Gemini 3 Pro (Most Intelligent)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,  # 1M tokens
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=150,
            supports_function_calling=True,
            cost_per_1k_tokens=0.00125
        ),
        "gemini-3-flash-preview": ModelConfig(
            name="Gemini 3 Flash (Balanced)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=150,
            supports_function_calling=True,
            cost_per_1k_tokens=0.000075
        ),
        "gemini-2.5-pro": ModelConfig(
            name="Gemini 2.5 Pro (Advanced Thinking)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,  # 1M tokens
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=150,
            supports_function_calling=True,
            cost_per_1k_tokens=0.00125
        ),
        "gemini-2.5-flash": ModelConfig(
            name="Gemini 2.5 Flash (Best Price-Performance)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.0  # Free tier
        ),
        "gemini-2.5-flash-lite": ModelConfig(
            name="Gemini 2.5 Flash-Lite (Ultra Fast)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.0  # Free tier
        ),
        "gemini-2.0-flash": ModelConfig(
            name="Gemini 2.0 Flash (Legacy)",
            provider=ModelProvider.GEMINI,
            context_window=1048576,
            recommended_context=800000,
            max_chunks=200,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.0  # Free tier
        ),
        
        # OpenAI Models (Updated Jan 2026)
        "gpt-4o": ModelConfig(
            name="GPT-4o (Latest)",
            provider=ModelProvider.OPENAI,
            context_window=128000,  # 128K tokens
            recommended_context=100000,
            max_chunks=100,
            recommended_chunks=50,
            supports_function_calling=True,
            cost_per_1k_tokens=0.005
        ),
        "gpt-4o-mini": ModelConfig(
            name="GPT-4o Mini (Fast)",
            provider=ModelProvider.OPENAI,
            context_window=128000,
            recommended_context=100000,
            max_chunks=100,
            recommended_chunks=50,
            supports_function_calling=True,
            cost_per_1k_tokens=0.00015
        ),
        "o1": ModelConfig(
            name="o1 (Reasoning)",
            provider=ModelProvider.OPENAI,
            context_window=200000,
            recommended_context=150000,
            max_chunks=150,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.015
        ),
        "o1-mini": ModelConfig(
            name="o1 Mini (Reasoning Fast)",
            provider=ModelProvider.OPENAI,
            context_window=128000,
            recommended_context=100000,
            max_chunks=100,
            recommended_chunks=50,
            supports_function_calling=True,
            cost_per_1k_tokens=0.003
        ),
        "gpt-4-turbo": ModelConfig(
            name="GPT-4 Turbo (Legacy)",
            provider=ModelProvider.OPENAI,
            context_window=128000,
            recommended_context=100000,
            max_chunks=100,
            recommended_chunks=50,
            supports_function_calling=True,
            cost_per_1k_tokens=0.01
        ),
        
        # Anthropic Models (Updated Jan 2026)
        "claude-sonnet-4-20250514": ModelConfig(
            name="Claude Sonnet 4 (Latest)",
            provider=ModelProvider.ANTHROPIC,
            context_window=200000,  # 200K tokens
            recommended_context=150000,
            max_chunks=150,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.003
        ),
        "claude-opus-4-20250514": ModelConfig(
            name="Claude Opus 4",
            provider=ModelProvider.ANTHROPIC,
            context_window=200000,
            recommended_context=150000,
            max_chunks=150,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.015
        ),
        "claude-3-5-sonnet-20241022": ModelConfig(
            name="Claude 3.5 Sonnet",
            provider=ModelProvider.ANTHROPIC,
            context_window=200000,
            recommended_context=150000,
            max_chunks=150,
            recommended_chunks=100,
            supports_function_calling=True,
            cost_per_1k_tokens=0.003
        ),
        
        # Groq Models (Updated Jan 2026)
        "llama-3.3-70b-versatile": ModelConfig(
            name="Llama 3.3 70B Versatile",
            provider=ModelProvider.GROQ,
            context_window=128000,
            recommended_context=100000,
            max_chunks=100,
            recommended_chunks=60,
            supports_function_calling=True,
            cost_per_1k_tokens=0.0
        ),
        "mixtral-8x7b-32768": ModelConfig(
            name="Mixtral 8x7B",
            provider=ModelProvider.GROQ,
            context_window=32768,
            recommended_context=24000,
            max_chunks=80,
            recommended_chunks=50,
            supports_function_calling=False,
            cost_per_1k_tokens=0.0
        ),
        
        # Local Fine-Tuned Models (examples)
        "codellama-7b-finetuned": ModelConfig(
            name="CodeLlama 7B (Fine-tuned)",
            provider=ModelProvider.LOCAL_FINETUNED,
            context_window=16384,
            recommended_context=12000,
            max_chunks=60,
            recommended_chunks=40,
            supports_function_calling=False,
            cost_per_1k_tokens=0.0
        ),
        "llama3-8b-finetuned": ModelConfig(
            name="Llama 3 8B (Fine-tuned)",
            provider=ModelProvider.LOCAL_FINETUNED,
            context_window=32768,
            recommended_context=24000,
            max_chunks=100,
            recommended_chunks=60,
            supports_function_calling=False,
            cost_per_1k_tokens=0.0
        ),
        "mistral-7b-finetuned": ModelConfig(
            name="Mistral 7B (Fine-tuned)",
            provider=ModelProvider.LOCAL_FINETUNED,
            context_window=32768,
            recommended_context=24000,
            max_chunks=100,
            recommended_chunks=60,
            supports_function_calling=False,
            cost_per_1k_tokens=0.0
        ),
        "deepseek-coder-finetuned": ModelConfig(
            name="DeepSeek Coder (Fine-tuned)",
            provider=ModelProvider.LOCAL_FINETUNED,
            context_window=16384,
            recommended_context=12000,
            max_chunks=70,
            recommended_chunks=45,
            supports_function_calling=False,
            cost_per_1k_tokens=0.0
        ),
    }

    @classmethod
    def get_model_config(cls, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model"""
        return cls.MODEL_CONFIGS.get(model_name)

    @classmethod
    def get_all_models(cls) -> List[str]:
        """Get list of all available models"""
        return list(cls.MODEL_CONFIGS.keys())

    @classmethod
    def get_models_by_provider(cls, provider: ModelProvider) -> List[str]:
        """Get models for a specific provider"""
        return [
            name for name, config in cls.MODEL_CONFIGS.items()
            if config.provider == provider
        ]

    @classmethod
    def get_chunk_limit(cls, model_name: str, use_recommended: bool = False) -> int:
        """Get chunk limit for a model"""
        config = cls.get_model_config(model_name)
        if not config:
            return 100  # Default
        return config.recommended_chunks if use_recommended else config.max_chunks

    @classmethod
    def get_context_window(cls, model_name: str, use_recommended: bool = False) -> int:
        """Get context window for a model"""
        config = cls.get_model_config(model_name)
        if not config:
            return 8192  # Default
        return config.recommended_context if use_recommended else config.context_window

    @classmethod
    def get_local_finetuned_models(cls) -> List[str]:
        """Get list of available fine-tuned local models"""
        return cls.get_models_by_provider(ModelProvider.LOCAL_FINETUNED)

    @classmethod
    def register_finetuned_model(cls, model_name: str, model_config: ModelConfig):
        """Register a new fine-tuned model"""
        cls.MODEL_CONFIGS[model_name] = model_config

    @classmethod
    def calculate_estimated_tokens(cls, model_name: str, chunks: int) -> int:
        """Estimate tokens based on chunks (approx 400 tokens per chunk)"""
        return chunks * 400

    @classmethod
    def is_context_safe(cls, model_name: str, estimated_tokens: int) -> bool:
        """Check if estimated tokens fit within context window"""
        config = cls.get_model_config(model_name)
        if not config:
            return True
        return estimated_tokens <= config.recommended_context

    @classmethod
    def get_optimal_chunks(cls, model_name: str, available_chunks: int = 200) -> int:
        """Get optimal number of chunks for a model given available chunks"""
        config = cls.get_model_config(model_name)
        if not config:
            return min(50, available_chunks)
        
        # Return min of recommended, max allowed, and available
        return min(config.recommended_chunks, config.max_chunks, available_chunks)


# Global instance
dynamic_model_config = DynamicModelConfig()
