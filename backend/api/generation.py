"""
Generation API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List
import json
import logging

from backend.models.dto import (
    GenerationRequest,
    GenerationResponse,
    GenerationUpdateDTO,
    ArtifactType,
    GenerationStatus,
    GenerationOptions,
    BulkGenerationRequest,
    BulkGenerationResult,
)
from backend.services.generation_service import get_service
from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter
from backend.core.websocket import websocket_manager, EventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generation", tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
@limiter.limit("5/minute")
async def generate_artifact(
    request: Request,
    gen_request: GenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Generate an artifact (non-streaming).
    
    Request body:
    {
        "artifact_type": "mermaid_erd",
        "meeting_notes": "User requirements...",
        "context_id": "optional-context-id",
        "options": {
            "max_retries": 3,
            "use_validation": true,
            "temperature": 0.7
        }
    }
    """
    # Validate request
    if not gen_request.meeting_notes and not gen_request.context_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either meeting_notes or context_id must be provided"
        )
    
    service = get_service()
    
    # Generate in background
    job_id = None
    
    def generate_task():
        nonlocal job_id
        result = None
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.generate_artifact_sync(
                    artifact_type=gen_request.artifact_type,
                    meeting_notes=gen_request.meeting_notes or "",
                    context_id=gen_request.context_id,
                    options=gen_request.options.dict() if gen_request.options else None
                )
            )
            job_id = result.get("job_id")
            
            # Emit WebSocket event
            if job_id and result.get("artifact"):
                websocket_manager.emit_generation_complete(
                    room_id=job_id,
                    artifact=result.get("artifact"),
                    validation=result.get("artifact", {}).get("validation")
                )
        except Exception as e:
            logger.error(f"Background generation task failed: {e}", exc_info=True)
        finally:
            loop.close()
    
    background_tasks.add_task(generate_task)
    
    # Return immediately with job_id
    return GenerationResponse(
        job_id=job_id or "pending",
        status=GenerationStatus.IN_PROGRESS
    )


@router.post("/stream")
async def generate_artifact_stream(
    stream_request: dict,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Generate an artifact with streaming progress updates.
    
    Request body:
    {
        "artifact_type": "mermaid_erd",
        "meeting_notes": "User requirements...",
        "context_id": "optional-context-id",
        "options": {...}
    }
    """
    artifact_type_str = stream_request.get("artifact_type")
    meeting_notes = stream_request.get("meeting_notes", "")
    context_id = stream_request.get("context_id")
    options = stream_request.get("options", {})
    
    if not artifact_type_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_type is required"
        )
    
    if not meeting_notes or len(meeting_notes.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="meeting_notes must be at least 10 characters"
        )
    
    try:
        artifact_type = ArtifactType(artifact_type_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid artifact_type: {artifact_type_str}"
        )
    
    service = get_service()
    
    async def generate_stream():
        """Stream generation progress."""
        async for update in service.generate_artifact(
            artifact_type=artifact_type,
            meeting_notes=meeting_notes,
            context_id=context_id,
            options=options,
            stream=True
        ):
            # Emit WebSocket event if job_id available
            job_id = update.get("job_id")
            if job_id:
                if update.get("type") == "progress":
                    websocket_manager.emit_generation_progress(
                        room_id=job_id,
                        progress=update.get("progress", 0.0),
                        message=update.get("message", ""),
                        quality_prediction=update.get("quality_prediction"),
                    )
                elif update.get("type") == "complete":
                    websocket_manager.emit_generation_complete(
                        room_id=job_id,
                        artifact=update.get("artifact"),
                        validation=update.get("artifact", {}).get("validation")
                    )
                elif update.get("type") == "error":
                    websocket_manager.emit_generation_error(
                        room_id=job_id,
                        error=update.get("error", "Unknown error")
                    )
            
            # Yield as Server-Sent Events
            yield f"data: {json.dumps(update)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/bulk", response_model=list[BulkGenerationResult])
async def bulk_generate(
    request: BulkGenerationRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Generate multiple artifacts sequentially."""
    service = get_service()
    responses: list[BulkGenerationResult] = []

    for item in request.items:
        if not item.meeting_notes and not item.context_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each item must include meeting_notes or context_id",
            )

        result = await service.generate_artifact_sync(
            artifact_type=item.artifact_type,
            meeting_notes=item.meeting_notes or "",
            context_id=item.context_id,
            options=item.options.dict() if item.options else None,
        )

        status_value = result.get("status", GenerationStatus.FAILED.value)
        try:
            status_enum = GenerationStatus(status_value)
        except ValueError:
            status_enum = GenerationStatus.FAILED

        responses.append(
            BulkGenerationResult(
                job_id=result.get("job_id", "unknown"),
                status=status_enum,
                artifact=result.get("artifact"),
                error=result.get("error"),
            )
        )

    return responses


@router.get("/jobs/{job_id}", response_model=dict)
async def get_generation_job(
    job_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get status of a generation job.
    
    Path parameters:
    - job_id: Job identifier
    """
    service = get_service()
    job = service.get_job_status(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    return job


@router.get("/jobs", response_model=List[dict])
async def list_generation_jobs(
    limit: int = 50,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List recent generation jobs.
    
    Query parameters:
    - limit: Maximum number of jobs to return (default: 50)
    """
    service = get_service()
    return service.list_jobs(limit=limit)


@router.post("/jobs/{job_id}/cancel", response_model=dict)
async def cancel_generation_job(
    job_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Cancel a generation job.
    
    Path parameters:
    - job_id: Job identifier
    """
    service = get_service()
    cancelled = service.cancel_job(job_id)
    
    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} cannot be cancelled (not found or not in progress)"
        )
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "cancelled"
    }


@router.put("/artifacts/{artifact_id}", response_model=dict)
@limiter.limit("20/minute")
async def update_artifact(
    request: Request,
    artifact_id: str,
    body: dict,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Update an artifact's content.
    
    Path parameters:
    - artifact_id: Artifact identifier
    
    Request body:
    {
        "content": "Updated artifact content...",
        "metadata": {"optional": "metadata"}
    }
    """
    if "content" not in body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content field is required"
        )
    
    service = get_service()
    updated = service.update_artifact(artifact_id, body.get("content"), body.get("metadata"))
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    # Create new version
    try:
        from backend.services.version_service import get_service as get_version_service
        version_service = get_version_service()
        version_service.create_version(
            artifact_id=artifact_id,
            artifact_type=updated.get("artifact_type", "unknown"),
            content=request.get("content"),
            metadata={
                "updated_by": current_user.username,
                "update_type": "manual_edit",
                **(request.get("metadata") or {})
            }
        )
    except Exception as e:
        logger.warning(f"Failed to create version for updated artifact: {e}")
    
    return {
        "success": True,
        "artifact_id": artifact_id,
        "message": "Artifact updated successfully"
    }



