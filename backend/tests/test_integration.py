"""
Integration tests for backend services.
Tests service interactions and end-to-end workflows.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.context_builder import get_builder as get_context_builder
from backend.services.generation_service import get_service as get_generation_service
from backend.services.validation_service import get_service as get_validation_service
from backend.services.feedback_service import get_service as get_feedback_service
from backend.models.dto import ArtifactType


@pytest.mark.asyncio
async def test_context_builder_integration():
    """Test Context Builder service integration."""
    builder = get_context_builder()
    
    meeting_notes = "Create a user authentication system with login and registration"
    
    context = await builder.build_context(
        meeting_notes=meeting_notes,
        include_rag=True,
        include_kg=False,  # Skip KG for speed
        include_patterns=False,  # Skip patterns for speed
        include_ml_features=False,
        max_rag_chunks=5
    )
    
    assert context is not None
    assert "meeting_notes" in context
    assert "sources" in context
    assert context["meeting_notes"] == meeting_notes


@pytest.mark.asyncio
async def test_generation_validation_integration():
    """Test Generation -> Validation workflow."""
    gen_service = get_generation_service()
    val_service = get_validation_service()
    
    meeting_notes = "Create an ERD for a blog system with Users, Posts, and Comments"
    
    # Generate artifact (would normally use context_id)
    result = None
    async for update in gen_service.generate_artifact(
        artifact_type=ArtifactType.MERMAID_ERD,
        meeting_notes=meeting_notes,
        stream=False
    ):
        result = update
    
    if result and "artifact" in result:
        artifact_content = result["artifact"]["content"]
        
        # Validate the generated artifact
        validation = await val_service.validate_artifact(
            artifact_type=ArtifactType.MERMAID_ERD,
            content=artifact_content,
            meeting_notes=meeting_notes
        )
        
        assert validation is not None
        assert hasattr(validation, 'score') or 'score' in validation
        assert hasattr(validation, 'is_valid') or 'is_valid' in validation


@pytest.mark.asyncio
async def test_feedback_integration():
    """Test Feedback service integration."""
    feedback_service = get_feedback_service()
    
    result = await feedback_service.record_feedback(
        artifact_id="test-artifact-123",
        artifact_type="mermaid_erd",
        ai_output="erDiagram\nUser ||--o{ Post",
        validation_score=85.0,
        feedback_type="positive",
        notes="Good ERD structure"
    )
    
    assert result is not None
    assert "success" in result
    
    # Get feedback history
    history = feedback_service.get_feedback_history(limit=10)
    assert isinstance(history, list)


def test_rag_cache_integration():
    """Test RAG cache integration with context builder."""
    from backend.services.rag_cache import get_rag_cache
    
    cache = get_rag_cache()
    
    # Test cache operations
    meeting_notes = "Test meeting notes for cache"
    context = "Test RAG context"
    
    # Set cache
    cache.set(meeting_notes, context)
    
    # Get cache
    cached = cache.get(meeting_notes)
    assert cached == context
    
    # Invalidate
    count = cache.invalidate(meeting_notes)
    assert count >= 1


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """Test complete end-to-end workflow: Context -> Generation -> Validation -> Feedback."""
    # Step 1: Build context
    context_builder = get_context_builder()
    meeting_notes = "Create a simple user management system"
    
    context = await context_builder.build_context(
        meeting_notes=meeting_notes,
        include_rag=True,
        include_kg=False,
        include_patterns=False,
        include_ml_features=False,
        max_rag_chunks=3
    )
    
    assert context is not None
    
    # Step 2: Generate artifact
    gen_service = get_generation_service()
    result = None
    async for update in gen_service.generate_artifact(
        artifact_type=ArtifactType.MERMAID_ERD,
        meeting_notes=meeting_notes,
        stream=False
    ):
        result = update
    
    if result and "artifact" in result:
        artifact = result["artifact"]
        artifact_content = artifact.get("content", "")
        
        # Step 3: Validate
        val_service = get_validation_service()
        validation = await val_service.validate_artifact(
            artifact_type=ArtifactType.MERMAID_ERD,
            content=artifact_content,
            meeting_notes=meeting_notes
        )
        
        assert validation is not None
        
        # Step 4: Record feedback
        feedback_service = get_feedback_service()
        feedback_result = await feedback_service.record_feedback(
            artifact_id=artifact.get("id", "test-id"),
            artifact_type=ArtifactType.MERMAID_ERD.value,
            ai_output=artifact_content,
            validation_score=validation.score if hasattr(validation, 'score') else validation.get('score', 0.0),
            feedback_type="positive"
        )
        
        assert feedback_result is not None
        assert "success" in feedback_result


def test_service_initialization():
    """Test that all services can be initialized."""
    from backend.services.rag_retriever import RAGRetriever
    from backend.services.knowledge_graph import get_builder as get_kg_builder
    from backend.services.pattern_mining import get_miner
    from backend.services.ml_features import get_engineer
    
    # Test service initialization
    rag = RAGRetriever()
    assert rag is not None
    
    kg = get_kg_builder()
    assert kg is not None
    
    pm = get_miner()
    assert pm is not None
    
    ml = get_engineer()
    assert ml is not None
    
    context = get_context_builder()
    assert context is not None
    
    gen = get_generation_service()
    assert gen is not None
    
    val = get_validation_service()
    assert val is not None
    
    feedback = get_feedback_service()
    assert feedback is not None



