"""
Smart Model Routing System
Routes requests to appropriate AI models based on task complexity and cost

NEW (Nov 2025): Ollama integration for local models with cloud fallback
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass
import time

if TYPE_CHECKING:
    from ai.ollama_client import OllamaClient

class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

class ModelTier(Enum):
    """Model tier levels"""
    LOCAL = "local"  # Ollama (FREE, fast, private)
    FREE = "free"  # Gemini Flash
    CHEAP = "cheap"  # GPT-3.5-turbo
    STANDARD = "standard"  # GPT-4
    PREMIUM = "premium"  # GPT-4-turbo, Claude 3

@dataclass
class ModelResponse:
    """Response from model generation"""
    content: str
    model_used: str
    is_fallback: bool
    is_local: bool
    generation_time: float
    tokens_used: int = 0
    error_message: str = ""
    success: bool = True

class ModelRouter:
    """Route AI requests to appropriate models"""
    
    # Task complexity mapping
    TASK_COMPLEXITY = {
        'diagram_generation': TaskComplexity.SIMPLE,
        'jira_tasks': TaskComplexity.SIMPLE,
        'workflow_generation': TaskComplexity.MEDIUM,
        'api_documentation': TaskComplexity.MEDIUM,
        'code_generation': TaskComplexity.COMPLEX,
        'architecture_design': TaskComplexity.COMPLEX,
        'repository_analysis': TaskComplexity.COMPLEX,
    }
    
    # Model selection based on complexity (Updated Jan 2026 - Official Google AI)
    MODEL_SELECTION = {
        TaskComplexity.SIMPLE: {
            'primary': ('gemini', 'gemini-2.5-flash-lite'),  # Ultra fast, cost-efficient
            'fallback': ('openai', 'gpt-4o-mini')  # Fast GPT-4o Mini
        },
        TaskComplexity.MEDIUM: {
            'primary': ('gemini', 'gemini-2.5-flash'),  # Best price-performance
            'fallback': ('openai', 'gpt-4o-mini')
        },
        TaskComplexity.COMPLEX: {
            'primary': ('gemini', 'gemini-2.5-pro'),  # Advanced thinking
            'fallback': ('openai', 'gpt-4o')  # Latest GPT-4o
        }
    }
    
    # Cost per 1K tokens (approximate, Updated Jan 2026 - Official Google AI)
    MODEL_COSTS = {
        # Gemini 3 (Preview)
        'gemini-3-pro-preview': {'input': 0.00125, 'output': 0.005},
        'gemini-3-flash-preview': {'input': 0.000075, 'output': 0.0003},
        # Gemini 2.5 (Stable - Free tier available)
        'gemini-2.5-pro': {'input': 0.00125, 'output': 0.005},
        'gemini-2.5-flash': {'input': 0.0, 'output': 0.0},  # Free tier
        'gemini-2.5-flash-lite': {'input': 0.0, 'output': 0.0},  # Free tier
        # Gemini 2.0 (Legacy)
        'gemini-2.0-flash': {'input': 0.0, 'output': 0.0},  # Free tier
        # OpenAI
        'gpt-4o': {'input': 0.005, 'output': 0.015},
        'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
        'o1': {'input': 0.015, 'output': 0.06},
        'o1-mini': {'input': 0.003, 'output': 0.012},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},  # Legacy
        # Anthropic Claude
        'claude-sonnet-4-20250514': {'input': 0.003, 'output': 0.015},
        'claude-opus-4-20250514': {'input': 0.015, 'output': 0.075},
        'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
        # Groq (Free/Cheap)
        'llama-3.3-70b-versatile': {'input': 0.0, 'output': 0.0},
    }
    
    def __init__(self, config: Dict[str, Any] = None, ollama_client: Optional['OllamaClient'] = None):
        """
        Initialize ModelRouter with optional Ollama integration.
        
        Args:
            config: Configuration dict
            ollama_client: OllamaClient instance for local models (optional)
        """
        self.config = config or {}
        self.total_cost = 0.0
        self.request_count = 0
        self.model_usage = {}
        
        # NEW: Ollama integration
        self.ollama_client = ollama_client
        self.force_local_only = False
        self.ollama_enabled = ollama_client is not None
        
        # Task → Local Model mapping (VRAM-optimized for 12GB)
        self.local_model_map = {
            # Persistent models (instant response)
            'code': 'codellama:7b-instruct-q4_K_M',
            'html': 'llama3:8b-instruct-q4_K_M',  # Changed from codellama for better HTML generation
            'documentation': 'llama3:8b-instruct-q4_K_M',  # Changed from codellama for better natural language
            'jira': 'llama3:8b-instruct-q4_K_M',
            'tasks': 'llama3:8b-instruct-q4_K_M',
            'planning': 'llama3:8b-instruct-q4_K_M',
            
            # Swap model (requires load time)
            'mermaid': 'mistral:7b-instruct-q4_K_M',
            'diagram': 'mistral:7b-instruct-q4_K_M',
            'erd': 'mistral:7b-instruct-q4_K_M',
            'architecture': 'llama3:8b-instruct-q4_K_M',  # Changed from mistral for better complex diagrams
            'flowchart': 'mistral:7b-instruct-q4_K_M',
            'sequence': 'mistral:7b-instruct-q4_K_M'
        }
        
        # Track persistent models (instant)
        self.persistent_models = {
            'codellama:7b-instruct-q4_K_M',
            'llama3:8b-instruct-q4_K_M'
        }
    
    def select_model(self, task_type: str, prefer_cost_effective: bool = True) -> tuple:
        """
        Select appropriate model for task
        
        Args:
            task_type: Type of task
            prefer_cost_effective: Prefer cheaper models when possible
        
        Returns:
            tuple: (provider, model_name)
        """
        complexity = self.TASK_COMPLEXITY.get(task_type, TaskComplexity.MEDIUM)
        
        if prefer_cost_effective:
            # Use primary model (usually cheaper/free)
            provider, model = self.MODEL_SELECTION[complexity]['primary']
        else:
            # Use best model regardless of cost
            if complexity == TaskComplexity.COMPLEX:
                provider, model = ('openai', 'gpt-4')
            else:
                provider, model = self.MODEL_SELECTION[complexity]['primary']
        
        # Track usage
        self.request_count += 1
        self.model_usage[model] = self.model_usage.get(model, 0) + 1
        
        return provider, model
    
    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for a request
        
        Args:
            model_name: Name of the model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        
        Returns:
            float: Estimated cost in USD
        """
        if model_name not in self.MODEL_COSTS:
            return 0.0
        
        costs = self.MODEL_COSTS[model_name]
        input_cost = (input_tokens / 1000) * costs['input']
        output_cost = (output_tokens / 1000) * costs['output']
        
        total = input_cost + output_cost
        self.total_cost += total
        
        return total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            'total_requests': self.request_count,
            'total_cost_usd': round(self.total_cost, 4),
            'model_usage': self.model_usage,
            'avg_cost_per_request': round(self.total_cost / max(self.request_count, 1), 4)
        }
    
    def recommend_model(self, task_type: str, budget_limit: float = None) -> Dict[str, Any]:
        """
        Recommend best model for task within budget
        
        Args:
            task_type: Type of task
            budget_limit: Maximum budget in USD
        
        Returns:
            dict: Recommendation with model and reasoning
        """
        complexity = self.TASK_COMPLEXITY.get(task_type, TaskComplexity.MEDIUM)
        
        # Get all viable models
        primary = self.MODEL_SELECTION[complexity]['primary']
        fallback = self.MODEL_SELECTION[complexity]['fallback']
        
        recommendations = []
        
        for provider, model in [primary, fallback]:
            cost_info = self.MODEL_COSTS.get(model, {'input': 0, 'output': 0})
            avg_cost = (cost_info['input'] + cost_info['output']) / 2
            
            if budget_limit is None or avg_cost <= budget_limit:
                recommendations.append({
                    'provider': provider,
                    'model': model,
                    'complexity': complexity.value,
                    'estimated_cost_per_1k_tokens': avg_cost,
                    'suitable': True
                })
        
        return {
            'task_type': task_type,
            'complexity': complexity.value,
            'recommendations': recommendations,
            'best_choice': recommendations[0] if recommendations else None
        }
    
    # ====================================================================
    # NEW: Ollama Integration Methods (Nov 2025)
    # ====================================================================
    
    def set_force_local_only(self, enabled: bool):
        """
        Enable/disable cloud fallback.
        
        Args:
            enabled: If True, never fall back to cloud (fail instead)
        """
        self.force_local_only = enabled
    
    def get_local_model_for_task(self, task_type: str) -> Optional[str]:
        """
        Get local model name for task type.
        
        Args:
            task_type: Task type (e.g., 'code', 'mermaid', 'jira')
            
        Returns:
            Local model name or None if no mapping
        """
        return self.local_model_map.get(task_type)
    
    def is_persistent_model(self, model_name: str) -> bool:
        """Check if model stays loaded (persistent) or swaps on-demand"""
        return model_name in self.persistent_models
    
    async def generate_with_local(
        self,
        task_type: str,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> ModelResponse:
        """
        Generate using local Ollama model with smart VRAM management.
        
        Args:
            task_type: Task type (e.g., 'code', 'mermaid', 'jira')
            prompt: User prompt
            system_message: System message (optional)
            temperature: Generation temperature
            **kwargs: Additional arguments
            
        Returns:
            ModelResponse with generation result
        """
        if not self.ollama_enabled:
            return ModelResponse(
                content="",
                model_used="",
                is_fallback=False,
                is_local=False,
                generation_time=0.0,
                error_message="Ollama not enabled",
                success=False
            )
        
        # Get local model for task
        local_model = self.get_local_model_for_task(task_type)
        
        if not local_model:
            return ModelResponse(
                content="",
                model_used="",
                is_fallback=False,
                is_local=False,
                generation_time=0.0,
                error_message=f"No local model mapped for task type: {task_type}",
                success=False
            )
        
        # Check if model is persistent (instant) or requires swap
        is_persistent = self.is_persistent_model(local_model)
        
        try:
            start_time = time.time()
            
            # Ensure model is available (handles swapping if needed)
            await self.ollama_client.ensure_model_available(local_model)
            
            # Generate
            ollama_response = await self.ollama_client.generate(
                model_name=local_model,
                prompt=prompt,
                system_message=system_message,
                temperature=temperature
            )
            
            generation_time = time.time() - start_time
            
            if ollama_response.success:
                # Track usage
                self.request_count += 1
                self.model_usage[local_model] = self.model_usage.get(local_model, 0) + 1
                
                return ModelResponse(
                    content=ollama_response.content,
                    model_used=local_model,
                    is_fallback=False,
                    is_local=True,
                    generation_time=generation_time,
                    tokens_used=0,  # Ollama doesn't provide token count
                    success=True
                )
            else:
                return ModelResponse(
                    content="",
                    model_used=local_model,
                    is_fallback=False,
                    is_local=True,
                    generation_time=generation_time,
                    error_message=ollama_response.error_message,
                    success=False
                )
        
        except Exception as e:
            return ModelResponse(
                content="",
                model_used=local_model,
                is_fallback=False,
                is_local=True,
                generation_time=0.0,
                error_message=str(e),
                success=False
            )
    
    async def generate(
        self,
        task_type: str,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.0,
        force_cloud: bool = False,
        **kwargs
    ) -> ModelResponse:
        """
        Generate with automatic local → cloud fallback.
        
        This is the main entry point for generation. It will:
        1. Try local model first (if Ollama enabled)
        2. Fall back to cloud if local fails (unless force_local_only)
        3. Return ModelResponse with metadata
        
        Args:
            task_type: Task type (e.g., 'code', 'mermaid', 'jira')
            prompt: User prompt
            system_message: System message (optional)
            temperature: Generation temperature
            force_cloud: Skip local, go straight to cloud
            **kwargs: Additional arguments for cloud providers
            
        Returns:
            ModelResponse with generation result
        """
        # Try local model first (unless force_cloud)
        if self.ollama_enabled and not force_cloud:
            local_response = await self.generate_with_local(
                task_type=task_type,
                prompt=prompt,
                system_message=system_message,
                temperature=temperature,
                **kwargs
            )
            
            if local_response.success:
                return local_response
            
            # Local failed - check if we can fall back
            if self.force_local_only:
                # User disabled cloud fallback
                local_response.error_message = (
                    f"Local model failed: {local_response.error_message}. "
                    "Cloud fallback disabled (force_local_only=True)."
                )
                return local_response
        
        # Fall back to cloud provider
        # NOTE: This requires the cloud generation logic from the calling code
        # We return a special response indicating cloud fallback is needed
        return ModelResponse(
            content="",
            model_used="cloud_fallback_required",
            is_fallback=True,
            is_local=False,
            generation_time=0.0,
            error_message="Local generation failed or disabled. Cloud fallback required.",
            success=False
        )


# Global router instance
_router_instance = None

def get_router(config: Dict[str, Any] = None, ollama_client: Optional['OllamaClient'] = None) -> ModelRouter:
    """
    Get or create global router instance.
    
    Args:
        config: Configuration dict
        ollama_client: OllamaClient instance for local models (optional)
    """
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter(config, ollama_client)
    return _router_instance

