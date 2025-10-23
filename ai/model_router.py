"""
Smart Model Routing System
Routes requests to appropriate AI models based on task complexity and cost
"""

from typing import Dict, Any, Optional
from enum import Enum

class TaskComplexity(Enum):
    """Task complexity levels"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

class ModelTier(Enum):
    """Model tier levels"""
    FREE = "free"  # Gemini Flash
    CHEAP = "cheap"  # GPT-3.5-turbo
    STANDARD = "standard"  # GPT-4
    PREMIUM = "premium"  # GPT-4-turbo, Claude 3

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
    
    # Model selection based on complexity
    MODEL_SELECTION = {
        TaskComplexity.SIMPLE: {
            'primary': ('gemini', 'gemini-2.0-flash-exp'),
            'fallback': ('openai', 'gpt-3.5-turbo')
        },
        TaskComplexity.MEDIUM: {
            'primary': ('openai', 'gpt-3.5-turbo'),
            'fallback': ('gemini', 'gemini-2.0-flash-exp')
        },
        TaskComplexity.COMPLEX: {
            'primary': ('openai', 'gpt-4'),
            'fallback': ('openai', 'gpt-3.5-turbo')
        }
    }
    
    # Cost per 1K tokens (approximate)
    MODEL_COSTS = {
        'gemini-2.0-flash-exp': {'input': 0.0, 'output': 0.0},  # Free
        'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},
        'gpt-4': {'input': 0.03, 'output': 0.06},
        'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.total_cost = 0.0
        self.request_count = 0
        self.model_usage = {}
    
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


# Global router instance
_router_instance = None

def get_router(config: Dict[str, Any] = None) -> ModelRouter:
    """Get or create global router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ModelRouter(config)
    return _router_instance

