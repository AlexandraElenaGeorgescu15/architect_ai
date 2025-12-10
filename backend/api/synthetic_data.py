"""
Synthetic Data API - Generate training examples for fine-tuning.

Endpoints:
- POST /generate - Generate synthetic examples
- GET /backends - List available generation backends
- GET /stats - Get synthetic vs real example stats
- POST /integrate - Add synthetic examples to finetuning pool
"""

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from backend.services.synthetic_dataset_service import get_service
from backend.services.finetuning_pool import get_pool
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/synthetic-data", tags=["synthetic-data"])


class SyntheticGenerationRequest(BaseModel):
    """Request to generate synthetic training examples."""
    artifact_type: str = Field(..., description="Type of artifact to generate examples for")
    target_count: int = Field(50, ge=10, le=500, description="Number of examples to generate")
    model_backend: str = Field("auto", description="Backend to use: 'auto', 'gemini', 'grok', 'phi-local'")
    complexity: str = Field("Mixed", description="Complexity level: 'Simple', 'Mixed', 'Complex'")
    auto_integrate: bool = Field(True, description="Automatically add to finetuning pool")


class SyntheticGenerationResponse(BaseModel):
    """Response from synthetic generation."""
    success: bool
    artifact_type: str
    generated_count: int
    target_count: int
    backend_used: str
    integrated: bool
    examples_preview: List[Dict[str, Any]]
    errors: List[str]


class BackendInfo(BaseModel):
    """Information about a generation backend."""
    id: str
    name: str
    type: str  # 'api' or 'local'
    free: bool
    quota: str
    available: bool


class SyntheticStatsResponse(BaseModel):
    """Statistics for synthetic vs real examples."""
    artifact_type: str
    real_examples: int
    synthetic_examples: int
    total_examples: int
    synthetic_percentage: float
    ready_for_training: bool


@router.post("/generate", response_model=SyntheticGenerationResponse)
@limiter.limit("10/hour")  # Rate limit: 10 generations per hour
async def generate_synthetic_data(
    request: Request,
    body: SyntheticGenerationRequest
):
    """
    Generate synthetic training examples for an artifact type.
    
    Uses free/local AI models to create bootstrapping data for fine-tuning.
    Examples can be automatically added to the finetuning pool or returned for review.
    """
    try:
        service = get_service()
        
        # Generate examples
        logger.info(f"Generating {body.target_count} synthetic examples for {body.artifact_type}")
        result = await service.generate_bootstrap_dataset(
            artifact_type=body.artifact_type,
            target_count=body.target_count,
            model_backend=body.model_backend,
            complexity=body.complexity
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation failed: {result.get('errors', [])}"
            )
        
        # Integrate with finetuning pool if requested
        integrated = False
        if body.auto_integrate:
            pool = get_pool()
            integrated_count = 0
            
            for example in result['examples']:
                added = pool.add_example(
                    artifact_type=body.artifact_type,
                    content=example['output'],
                    meeting_notes=example['instruction'],
                    validation_score=85.0,  # Bootstrap score
                    model_used=f"synthetic-{result['backend']}",
                    context={
                        "source": "synthetic",
                        "category": example.get('category', 'general'),
                        "difficulty": example.get('difficulty', 'Medium'),
                        "input": example.get('input', ''),
                        "generated_at": result.get('generated_at', '')
                    }
                )
                if added:
                    integrated_count += 1
            
            integrated = integrated_count > 0
            logger.info(f"Integrated {integrated_count} synthetic examples into finetuning pool")
        
        # Return preview (first 3 examples)
        examples_preview = result['examples'][:3]
        
        return SyntheticGenerationResponse(
            success=True,
            artifact_type=body.artifact_type,
            generated_count=result['generated_count'],
            target_count=body.target_count,
            backend_used=result['backend'],
            integrated=integrated,
            examples_preview=examples_preview,
            errors=result.get('errors', [])
        )
        
    except Exception as e:
        logger.error(f"Synthetic generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/backends", response_model=List[BackendInfo])
async def list_available_backends():
    """
    List available generation backends.
    
    Returns information about which backends (Gemini, Grok, Phi-local)
    are available and their quota limits.
    """
    try:
        service = get_service()
        backends = service.get_available_backends()
        return backends
    except Exception as e:
        logger.error(f"Failed to list backends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats/{artifact_type}", response_model=SyntheticStatsResponse)
async def get_synthetic_stats(artifact_type: str):
    """
    Get statistics for synthetic vs real examples for an artifact type.
    
    Shows breakdown of training data sources and readiness status.
    """
    try:
        pool = get_pool()
        
        # Get all examples for this artifact type
        examples = pool.get_examples(artifact_type)
        
        # Count by source
        real_count = 0
        synthetic_count = 0
        
        for example in examples:
            source = example.get('context', {}).get('source', 'feedback')
            if source == 'synthetic':
                synthetic_count += 1
            else:
                real_count += 1
        
        total = real_count + synthetic_count
        synthetic_pct = (synthetic_count / total * 100) if total > 0 else 0
        
        # Consider ready if at least 50 examples total
        ready = total >= 50
        
        return SyntheticStatsResponse(
            artifact_type=artifact_type,
            real_examples=real_count,
            synthetic_examples=synthetic_count,
            total_examples=total,
            synthetic_percentage=round(synthetic_pct, 1),
            ready_for_training=ready
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats", response_model=Dict[str, SyntheticStatsResponse])
async def get_all_synthetic_stats():
    """
    Get synthetic vs real stats for all artifact types.
    
    Provides overview of training data across all artifact types.
    """
    try:
        pool = get_pool()
        
        # Check if pool is available
        if not hasattr(pool, 'pools'):
            logger.warning("Finetuning pool not properly initialized")
            return {}
        
        # Get stats for all artifact types
        all_stats = {}
        
        for artifact_type in pool.pools.keys():
            try:
                examples = pool.get_examples(artifact_type)
                
                real_count = 0
                synthetic_count = 0
                
                for example in examples:
                    source = example.get('context', {}).get('source', 'feedback')
                    if source == 'synthetic':
                        synthetic_count += 1
                    else:
                        real_count += 1
                
                total = real_count + synthetic_count
                synthetic_pct = (synthetic_count / total * 100) if total > 0 else 0
                ready = total >= 50
                
                all_stats[artifact_type] = SyntheticStatsResponse(
                    artifact_type=artifact_type,
                    real_examples=real_count,
                    synthetic_examples=synthetic_count,
                    total_examples=total,
                    synthetic_percentage=round(synthetic_pct, 1),
                    ready_for_training=ready
                )
            except Exception as e:
                logger.error(f"Error getting stats for {artifact_type}: {e}")
        
        return all_stats
        
    except Exception as e:
        logger.error(f"Failed to get all stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/clear/{artifact_type}")
@limiter.limit("5/hour")
async def clear_synthetic_examples(request: Request, artifact_type: str):
    """
    Clear all synthetic examples for an artifact type.
    
    Keeps only real feedback-driven examples.
    Useful when enough real data has been collected.
    """
    try:
        pool = get_pool()
        
        # Get all examples
        examples = pool.get_examples(artifact_type)
        
        # Filter to keep only real examples
        real_examples = [
            ex for ex in examples
            if ex.get('context', {}).get('source', 'feedback') != 'synthetic'
        ]
        
        removed_count = len(examples) - len(real_examples)
        
        # Actually update the pool by replacing with filtered examples
        if artifact_type in pool.pools:
            pool.pools[artifact_type] = real_examples
            # Persist changes to disk
            pool._save_pool(artifact_type)
            logger.info(f"Removed {removed_count} synthetic examples for {artifact_type}, {len(real_examples)} real examples remain")
        else:
            logger.warning(f"Artifact type {artifact_type} not found in pool")
        
        return {
            "success": True,
            "artifact_type": artifact_type,
            "removed_count": removed_count,
            "remaining_count": len(real_examples)
        }
        
    except Exception as e:
        logger.error(f"Failed to clear synthetic examples: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

