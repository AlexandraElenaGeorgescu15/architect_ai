"""
Context Builder API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional, Dict, Any
from backend.models.dto import ContextRequest, ContextResponse, ContextBuildRequest, ContextBuildResponse
from backend.services.context_builder import get_builder
from backend.core.auth import get_current_user
from backend.core.middleware import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["context"])


@router.post("/build", response_model=ContextResponse)
@limiter.limit("10/minute")
async def build_context(
    request: Request,
    context_request: ContextRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """
    Build comprehensive context from multiple sources.
    
    Request body:
    {
        "meeting_notes": "User requirements...",  // OR
        "folder_id": "folder-id",                  // Use folder instead
        "repo_id": "optional-repo-id",
        "include_rag": true,
        "include_kg": true,
        "include_patterns": true,
        "include_ml_features": false,
        "max_rag_chunks": 18,
        "kg_depth": 2,
        "artifact_type": "mermaid_erd"
    }
    """
    # Load meeting notes from folder if folder_id is provided
    meeting_notes = context_request.meeting_notes
    if context_request.folder_id:
        from pathlib import Path
        MEETING_NOTES_DIR = Path("data/meeting_notes")
        folder_path = MEETING_NOTES_DIR / context_request.folder_id
        if not folder_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Folder '{context_request.folder_id}' not found"
            )
        
        # Load all notes from folder
        notes_content = []
        for note_file in folder_path.glob("*.md"):
            notes_content.append(note_file.read_text(encoding='utf-8'))
        for note_file in folder_path.glob("*.txt"):
            notes_content.append(note_file.read_text(encoding='utf-8'))
        
        if not notes_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Folder '{context_request.folder_id}' is empty"
            )
        
        # Combine all notes
        meeting_notes = "\n\n---\n\n".join(notes_content)
        logger.info(f"Loaded {len(notes_content)} notes from folder '{context_request.folder_id}'")
    
    if not meeting_notes or len(meeting_notes.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="meeting_notes must be at least 10 characters (or folder must contain notes)"
        )
    
    builder = get_builder()
    
    try:
        context = await builder.build_context(
            meeting_notes=meeting_notes,
            repo_id=context_request.repo_id,
            include_rag=context_request.include_rag if context_request.include_rag is not None else True,
            include_kg=context_request.include_kg if context_request.include_kg is not None else True,
            include_patterns=context_request.include_patterns if context_request.include_patterns is not None else True,
            include_ml_features=context_request.include_ml_features if context_request.include_ml_features is not None else False,
            max_rag_chunks=context_request.max_rag_chunks if context_request.max_rag_chunks else 18,
            kg_depth=context_request.kg_depth if context_request.kg_depth else 2,
            artifact_type=context_request.artifact_type.value if context_request.artifact_type else None
        )
        
        return ContextResponse(
            success=True,
            context_id=context.get("created_at", ""),  # Use timestamp as ID for now
            assembled_context=context.get("assembled_context", ""),
            sources=context.get("sources", {}),
            from_cache=context.get("from_cache", False),
            metadata={
                "meeting_notes_length": len(meeting_notes),
                "folder_id": context_request.folder_id if context_request.folder_id else None,
                "sources_included": list(context.get("sources", {}).keys()),
                "created_at": context.get("created_at")
            }
        )
    except Exception as e:
        logger.error(f"Error building context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build context: {str(e)}"
        )


@router.get("/stats", response_model=dict)
async def get_context_stats(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get context builder statistics."""
    builder = get_builder()
    
    # Get stats from each service
    rag_stats = builder.rag_retriever.get_query_stats()
    kg_stats = builder.kg_builder.get_stats()
    
    return {
        "rag_stats": rag_stats,
        "kg_stats": kg_stats,
        "cache_stats": builder.rag_cache.get_stats()
    }

