"""
HTML Diagram Generation API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Optional
import logging

from backend.models.dto import ArtifactType
from backend.services.html_diagram_generator import get_generator
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/html-diagrams", tags=["HTML Diagrams"])


@router.post("/generate", summary="Generate HTML from Mermaid diagram")
@limiter.limit("10/minute")
async def generate_html_diagram(
    request: Request,
    mermaid_content: str,
    mermaid_artifact_type: ArtifactType,
    meeting_notes: str = "",
    rag_context: str = "",
    use_ai: bool = True,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Generate HTML visualization from Mermaid diagram.
    
    Args:
        mermaid_content: Mermaid diagram code
        mermaid_artifact_type: Type of Mermaid diagram
        meeting_notes: Meeting notes for context (optional)
        rag_context: RAG context for AI generation (optional)
        use_ai: Whether to use AI for context-aware generation
    
    Returns:
        HTML content
    """
    generator = get_generator()
    
    try:
        html_content = await generator.generate_html_from_mermaid(
            mermaid_content=mermaid_content,
            mermaid_artifact_type=mermaid_artifact_type,
            meeting_notes=meeting_notes,
            rag_context=rag_context,
            use_ai=use_ai
        )
        
        return {
            "success": True,
            "html_content": html_content,
            "artifact_type": mermaid_artifact_type.value
        }
    except Exception as e:
        logger.error(f"Error generating HTML diagram: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate HTML diagram: {str(e)}"
        )


@router.post("/validate", summary="Validate Mermaid syntax")
async def validate_mermaid(
    mermaid_content: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Validate Mermaid diagram syntax and attempt to fix errors."""
    generator = get_generator()
    
    is_valid, corrected, errors = generator.validate_mermaid_syntax(mermaid_content)
    
    return {
        "success": True,
        "is_valid": is_valid,
        "corrected_content": corrected,
        "errors": errors
    }


@router.get("/mapping", summary="Get Mermaid to HTML artifact type mapping")
async def get_mapping(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get mapping of Mermaid artifact types to HTML artifact types."""
    generator = get_generator()
    
    mapping = {
        mermaid_type.value: html_type.value
        for mermaid_type, html_type in generator.MERMAID_TO_HTML_MAP.items()
    }
    
    return {
        "success": True,
        "mapping": mapping
    }

