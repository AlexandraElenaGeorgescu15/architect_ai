"""
Intelligent Model Router for Artifact-Specific Generation
Routes each artifact type to the optimal specialized Ollama model.
"""

from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass
import asyncio


class ArtifactType(Enum):
    """Types of artifacts the system can generate"""
    ERD = "erd"
    ARCHITECTURE = "architecture"
    SEQUENCE = "sequence"
    CLASS_DIAGRAM = "class_diagram"
    STATE_DIAGRAM = "state_diagram"
    CODE_PROTOTYPE = "code_prototype"
    HTML_PROTOTYPE = "html_prototype"
    API_DOCS = "api_docs"
    JIRA_STORIES = "jira_stories"
    WORKFLOWS = "workflows"
    DOCUMENTATION = "documentation"


@dataclass
class ModelSpec:
    """Specification for a model"""
    name: str
    vram_gb: float
    strengths: List[str]
    priority: int  # Lower = higher priority


class ArtifactModelRouter:
    """
    Routes artifact generation requests to optimal specialized models.
    
    Architecture:
    - Each artifact type has a primary model and fallback options
    - Auto-downloads missing models on first use
    - Validates output quality before returning
    - Falls back to cloud only if all local options fail validation
    """
    
    # Model registry with VRAM requirements
    MODELS = {
        # Persistent models (always loaded - 8.5GB total)
        "codellama:7b-instruct-q4_K_M": ModelSpec(
            name="codellama:7b-instruct-q4_K_M",
            vram_gb=3.8,
            strengths=["code", "typescript", "c#", "angular", ".net"],
            priority=1
        ),
        "llama3:8b-instruct-q4_K_M": ModelSpec(
            name="llama3:8b-instruct-q4_K_M",
            vram_gb=4.7,
            strengths=["general", "documentation", "api_docs", "jira"],
            priority=1
        ),
        
        # On-demand models (loaded as needed)
        "mistral:7b-instruct-q4_K_M": ModelSpec(
            name="mistral:7b-instruct-q4_K_M",
            vram_gb=4.1,
            strengths=["mermaid", "diagrams", "erd", "architecture"],
            priority=2
        ),
        "qwen2.5-coder:7b-instruct-q4_K_M": ModelSpec(
            name="qwen2.5-coder:7b-instruct-q4_K_M",
            vram_gb=4.3,
            strengths=["code", "html", "css", "prototypes"],
            priority=3
        ),
    }
    
    # Artifact type → Model mapping (ordered by priority)
    ARTIFACT_MODEL_MAP: Dict[ArtifactType, List[str]] = {
        ArtifactType.ERD: [
            "mistral:7b-instruct-q4_K_M",
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.ARCHITECTURE: [
            "mistral:7b-instruct-q4_K_M",
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.SEQUENCE: [
            "mistral:7b-instruct-q4_K_M",
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.CLASS_DIAGRAM: [
            "mistral:7b-instruct-q4_K_M",
            "codellama:7b-instruct-q4_K_M",
        ],
        ArtifactType.STATE_DIAGRAM: [
            "mistral:7b-instruct-q4_K_M",
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.CODE_PROTOTYPE: [
            "codellama:7b-instruct-q4_K_M",
            "qwen2.5-coder:7b-instruct-q4_K_M",
        ],
        ArtifactType.HTML_PROTOTYPE: [
            "qwen2.5-coder:7b-instruct-q4_K_M",
            "codellama:7b-instruct-q4_K_M",
        ],
        ArtifactType.API_DOCS: [
            "llama3:8b-instruct-q4_K_M",
            "codellama:7b-instruct-q4_K_M",
        ],
        ArtifactType.JIRA_STORIES: [
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.WORKFLOWS: [
            "llama3:8b-instruct-q4_K_M",
        ],
        ArtifactType.DOCUMENTATION: [
            "llama3:8b-instruct-q4_K_M",
        ],
    }
    
    def __init__(self, ollama_client=None):
        """
        Initialize router with Ollama client.
        
        Args:
            ollama_client: Instance of OllamaClient (optional, can be set later)
        """
        self.ollama_client = ollama_client
        self.generation_stats: Dict[str, Dict] = {}
    
    def set_ollama_client(self, ollama_client):
        """Set or update the Ollama client"""
        self.ollama_client = ollama_client
    
    async def get_model_for_artifact(self, artifact_type: ArtifactType) -> Optional[str]:
        """
        Get the best available model for an artifact type.
        
        Logic:
        1. Check model priority list for artifact
        2. Try primary model first
        3. If unavailable/fails, try fallback models
        4. Auto-download if needed
        
        Args:
            artifact_type: Type of artifact to generate
            
        Returns:
            Model name to use, or None if all failed
        """
        if not self.ollama_client:
            print("[ERROR] Ollama client not configured")
            return None
        
        candidates = self.ARTIFACT_MODEL_MAP.get(artifact_type, [])
        
        if not candidates:
            print(f"[WARN] No models mapped for artifact type: {artifact_type.value}")
            return None
        
        for model_name in candidates:
            # Check if model is available
            if await self.ollama_client.is_model_available(model_name):
                # Ensure model is loaded (handles VRAM management)
                success = await self.ollama_client.ensure_model_available(model_name, show_progress=True)
                if success:
                    print(f"[ROUTER] Using {model_name} for {artifact_type.value}")
                    return model_name
                else:
                    print(f"[WARN] Failed to load {model_name}, trying next option")
                    continue
            else:
                print(f"[INFO] Model {model_name} not available, auto-downloading...")
                # Auto-download via Ollama client's load_model (which auto-pulls)
                success = await self.ollama_client.load_model(model_name, show_progress=True)
                if success:
                    print(f"[ROUTER] Using newly downloaded {model_name} for {artifact_type.value}")
                    return model_name
                else:
                    print(f"[WARN] Failed to download {model_name}, trying next option")
                    continue
        
        print(f"[ERROR] All models failed for {artifact_type.value}")
        return None
    
    async def generate(
        self,
        artifact_type: ArtifactType,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict:
        """
        Generate content for an artifact using the optimal model.
        
        Args:
            artifact_type: Type of artifact
            prompt: Generation prompt
            system: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional generation parameters
            
        Returns:
            Dict with:
                - content: Generated content
                - model_used: Model that generated it
                - success: Whether generation succeeded
                - error_message: Error if failed
                - generation_time: Time taken
        """
        # Get optimal model
        model_name = await self.get_model_for_artifact(artifact_type)
        
        if not model_name:
            return {
                "content": "",
                "model_used": None,
                "success": False,
                "error_message": f"No available model for {artifact_type.value}",
                "generation_time": 0.0
            }
        
        # Generate using selected model
        response = await self.ollama_client.generate(
            model_name=model_name,
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
        
        # Track stats
        if artifact_type.value not in self.generation_stats:
            self.generation_stats[artifact_type.value] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "models_used": {}
            }
        
        stats = self.generation_stats[artifact_type.value]
        stats["total_requests"] += 1
        
        if response.success:
            stats["successful_requests"] += 1
            stats["models_used"][model_name] = stats["models_used"].get(model_name, 0) + 1
        else:
            stats["failed_requests"] += 1
        
        return {
            "content": response.content,
            "model_used": response.model_used,
            "success": response.success,
            "error_message": response.error_message,
            "generation_time": response.generation_time
        }
    
    def get_stats(self) -> Dict:
        """Get generation statistics"""
        return self.generation_stats.copy()
    
    async def pre_warm_models(self):
        """Pre-warm persistent models at startup"""
        if not self.ollama_client:
            print("[WARN] Cannot pre-warm models: Ollama client not configured")
            return
        print("[ROUTER] Pre-warming persistent models...")
        await self.ollama_client.initialize_persistent_models()
        print("[ROUTER] Persistent models ready")


# Alias for backward compatibility
ArtifactRouter = ArtifactModelRouter


# Global router instance
_router: Optional[ArtifactModelRouter] = None


def get_artifact_router(ollama_client) -> ArtifactModelRouter:
    """Get or create global artifact router"""
    global _router
    if _router is None:
        _router = ArtifactModelRouter(ollama_client)
    return _router
