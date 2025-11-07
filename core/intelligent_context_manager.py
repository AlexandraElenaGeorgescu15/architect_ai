"""
Intelligent Context Manager

Automatically determines optimal RAG settings based on:
- AI model provider and capabilities
- Task type (generation, fine-tuning, etc.)
- Available data
"""

from typing import Dict, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that require context"""
    ARTIFACT_GENERATION = "artifact_generation"
    FINE_TUNING = "fine_tuning"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"


class IntelligentContextManager:
    """
    Manages context retrieval intelligently based on model and task.
    No manual configuration needed - everything is automatic.
    """
    
    # Model capabilities database
    MODEL_CAPABILITIES = {
        # Google Gemini
        "gemini-1.5-pro": {
            "context_window": 1000000,
            "safe_context": 800000,
            "max_chunks": 200,
            "recommended_chunks": 100,
            "supports_parallel": True,
            "parallel_limit": 5
        },
        "gemini-1.5-flash": {
            "context_window": 1000000,
            "safe_context": 800000,
            "max_chunks": 200,
            "recommended_chunks": 100,
            "supports_parallel": True,
            "parallel_limit": 10
        },
        "gemini-2.0-pro": {
            "context_window": 1000000,
            "safe_context": 800000,
            "max_chunks": 250,
            "recommended_chunks": 150,
            "supports_parallel": True,
            "parallel_limit": 5
        },
        
        # OpenAI
        "gpt-4-turbo": {
            "context_window": 128000,
            "safe_context": 100000,
            "max_chunks": 100,
            "recommended_chunks": 50,
            "supports_parallel": True,
            "parallel_limit": 3
        },
        "gpt-4": {
            "context_window": 8192,
            "safe_context": 6000,
            "max_chunks": 30,
            "recommended_chunks": 18,
            "supports_parallel": False,
            "parallel_limit": 1
        },
        "gpt-3.5-turbo": {
            "context_window": 16384,
            "safe_context": 12000,
            "max_chunks": 50,
            "recommended_chunks": 30,
            "supports_parallel": True,
            "parallel_limit": 5
        },
        
        # Anthropic
        "claude-3-opus": {
            "context_window": 200000,
            "safe_context": 150000,
            "max_chunks": 150,
            "recommended_chunks": 100,
            "supports_parallel": True,
            "parallel_limit": 3
        },
        "claude-3-sonnet": {
            "context_window": 200000,
            "safe_context": 150000,
            "max_chunks": 150,
            "recommended_chunks": 100,
            "supports_parallel": True,
            "parallel_limit": 5
        },
        
        # Groq
        "mixtral-8x7b": {
            "context_window": 32768,
            "safe_context": 24000,
            "max_chunks": 80,
            "recommended_chunks": 50,
            "supports_parallel": True,
            "parallel_limit": 10  # Groq is very fast
        },
        
        # Local Fine-Tuned
        "local-finetuned": {
            "context_window": 32768,
            "safe_context": 24000,
            "max_chunks": 100,
            "recommended_chunks": 60,
            "supports_parallel": False,
            "parallel_limit": 1
        }
    }
    
    @classmethod
    def get_optimal_context(cls, 
                           model_name: str, 
                           task_type: TaskType,
                           available_chunks: int = 1000) -> Dict:
        """
        Get optimal context settings for a model and task.
        
        Returns:
            dict: {
                'max_chunks': int,
                'context_window': int,
                'use_enhanced': bool,
                'reasoning': str
            }
        """
        # Get model capabilities
        model_key = cls._normalize_model_name(model_name)
        capabilities = cls.MODEL_CAPABILITIES.get(
            model_key, 
            cls.MODEL_CAPABILITIES["gpt-4"]  # Default fallback
        )
        
        # Fine-tuning always gets maximum context
        if task_type == TaskType.FINE_TUNING:
            return {
                'max_chunks': min(500, available_chunks),  # Unlimited!
                'context_window': capabilities['safe_context'],
                'use_enhanced': True,
                'reasoning': "Fine-tuning: Maximum context for comprehensive learning"
            }
        
        # For generation tasks, use model's recommended chunks
        if task_type == TaskType.ARTIFACT_GENERATION:
            return {
                'max_chunks': min(capabilities['recommended_chunks'], available_chunks),
                'context_window': capabilities['safe_context'],
                'use_enhanced': capabilities['recommended_chunks'] >= 50,
                'reasoning': f"Artifact generation: {capabilities['recommended_chunks']} chunks optimal for {model_name}"
            }
        
        # For documentation/review, use more context
        if task_type in [TaskType.DOCUMENTATION, TaskType.CODE_REVIEW]:
            return {
                'max_chunks': min(capabilities['max_chunks'], available_chunks),
                'context_window': capabilities['safe_context'],
                'use_enhanced': True,
                'reasoning': f"Documentation/review: Maximum {capabilities['max_chunks']} chunks for thoroughness"
            }
        
        # Default
        return {
            'max_chunks': min(capabilities['recommended_chunks'], available_chunks),
            'context_window': capabilities['safe_context'],
            'use_enhanced': False,
            'reasoning': "Default configuration"
        }
    
    @classmethod
    def can_handle_parallel(cls, model_name: str) -> Tuple[bool, Optional[int], str]:
        """
        Check if a model can handle parallel processing.
        
        Returns:
            tuple: (can_handle: bool, max_parallel: int, warning: str)
        """
        model_key = cls._normalize_model_name(model_name)
        capabilities = cls.MODEL_CAPABILITIES.get(
            model_key,
            cls.MODEL_CAPABILITIES["gpt-4"]
        )
        
        supports = capabilities['supports_parallel']
        limit = capabilities['parallel_limit']
        
        if not supports:
            warning = f"⚠️ {model_name} doesn't support parallel processing efficiently. Sequential processing recommended."
            return False, 1, warning
        
        if limit <= 2:
            warning = f"⚠️ {model_name} supports limited parallelism (max {limit} concurrent). May be slower than sequential."
            return True, limit, warning
        
        if limit >= 5:
            info = f"✅ {model_name} handles parallel processing well (up to {limit} concurrent tasks)."
            return True, limit, info
        
        info = f"✅ {model_name} supports moderate parallelism ({limit} concurrent tasks)."
        return True, limit, info
    
    @classmethod
    def _normalize_model_name(cls, model_name: str) -> str:
        """Normalize model name to match capabilities database"""
        name = model_name.lower().strip()
        
        # Map common variations
        if "gemini" in name and "1.5" in name and "pro" in name:
            return "gemini-1.5-pro"
        if "gemini" in name and "1.5" in name and "flash" in name:
            return "gemini-1.5-flash"
        if "gemini" in name and "2.0" in name:
            return "gemini-2.0-pro"
        
        if "gpt-4" in name and "turbo" in name:
            return "gpt-4-turbo"
        if "gpt-4" in name:
            return "gpt-4"
        if "gpt-3.5" in name or "gpt3.5" in name:
            return "gpt-3.5-turbo"
        
        if "claude" in name and "opus" in name:
            return "claude-3-opus"
        if "claude" in name and "sonnet" in name:
            return "claude-3-sonnet"
        
        if "mixtral" in name:
            return "mixtral-8x7b"
        
        if "local" in name or "fine" in name or "🎓" in name:
            return "local-finetuned"
        
        # Default to GPT-4 for unknown models
        logger.warning(f"Unknown model: {model_name}, using default capabilities")
        return "gpt-4"
    
    @classmethod
    def get_model_info(cls, model_name: str) -> Dict:
        """Get complete information about a model"""
        model_key = cls._normalize_model_name(model_name)
        capabilities = cls.MODEL_CAPABILITIES.get(
            model_key,
            cls.MODEL_CAPABILITIES["gpt-4"]
        )
        
        return {
            "model_key": model_key,
            "model_name": model_name,
            **capabilities
        }


# Global instance
intelligent_context = IntelligentContextManager()

