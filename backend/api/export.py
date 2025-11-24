"""
Export API endpoints for artifact export.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Response, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import logging
import json

from backend.models.dto import ExportRequest
from backend.services.export_service import get_export_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/artifact")
@limiter.limit("20/minute")
async def export_artifact(
    request: Request,
    body: ExportRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Export an artifact in the specified format.
    
    Request body:
    {
        "artifact_id": "artifact-123",
        "artifact_type": "mermaid_erd",
        "content": "erDiagram\n...",
        "export_format": "svg",
        "options": {
            "language": "python"
        }
    }
    """
    service = get_export_service()
    
    result = await service.export_artifact(
        artifact_id=body.artifact_id,
        artifact_type=body.artifact_type,
        content=body.content,
        export_format=body.export_format,
        options=body.options
    )
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    # Return as downloadable file
    filename = result.get("filename", f"{body.artifact_id}.{body.export_format}")
    mime_type = result.get("mime_type", "application/octet-stream")
    data = result.get("data", "")
    
    if body.export_format in ["png", "pdf"] and result.get("data") is None:
        # For binary formats that need rendering
        return Response(
            content=json.dumps({"message": result.get("note", "Export not yet implemented for this format")}),
            media_type="application/json",
            status_code=status.HTTP_501_NOT_IMPLEMENTED
        )
    
    return Response(
        content=data,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

