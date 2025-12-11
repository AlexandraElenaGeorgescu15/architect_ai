"""
Generation API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks, Request, Query
from fastapi.responses import StreamingResponse
from starlette.requests import Request
from typing import Optional, List, Dict
import json
import logging
import asyncio
from datetime import datetime

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
        "folder_id": "meeting-notes-folder-id",
        "context_id": "optional-context-id",
        "options": {
            "max_retries": 3,
            "use_validation": true,
            "temperature": 0.7
        }
    }
    """
    logger.info(f"📥 [GENERATION] Received generation request: artifact_type={gen_request.artifact_type}, "
                f"has_meeting_notes={bool(gen_request.meeting_notes)}, "
                f"folder_id={gen_request.folder_id}, context_id={gen_request.context_id}")
    
    # Validate request
    if not gen_request.meeting_notes and not gen_request.context_id and not gen_request.folder_id:
        logger.warning(f"❌ [GENERATION] Request validation failed: missing meeting_notes, folder_id, and context_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either meeting_notes, folder_id, or context_id must be provided"
        )
    
    # If folder_id is provided, load notes from the folder
    meeting_notes = gen_request.meeting_notes or ""
    if gen_request.folder_id and not meeting_notes:
        logger.info(f"📁 [GENERATION] Loading notes from folder: {gen_request.folder_id}")
        from backend.services.meeting_notes_service import get_service as get_notes_service
        notes_service = get_notes_service()
        if not hasattr(notes_service, 'get_notes_by_folder'):
            logger.error(f"❌ [GENERATION] Meeting notes service missing get_notes_by_folder method")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Meeting notes service is not properly initialized"
            )
        folder_notes = notes_service.get_notes_by_folder(gen_request.folder_id)
        logger.info(f"📄 [GENERATION] Found {len(folder_notes)} notes in folder {gen_request.folder_id}")
        if not folder_notes:
            logger.warning(f"⚠️ [GENERATION] No notes found in folder: {gen_request.folder_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No notes found in folder: {gen_request.folder_id}"
            )
        # Combine all notes from the folder
        meeting_notes = "\n\n".join([note.get("content", "") for note in folder_notes])
        logger.info(f"📝 [GENERATION] Combined {len(folder_notes)} notes into {len(meeting_notes)} chars of meeting notes")
        if not meeting_notes.strip():
            logger.warning(f"⚠️ [GENERATION] Folder {gen_request.folder_id} contains no content after combining")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Folder {gen_request.folder_id} contains no content"
            )
    
    service = get_service()
    logger.info(f"🚀 [GENERATION] Starting generation service for {gen_request.artifact_type}")
    
    # Generate in background
    job_id = None
    
    def generate_task():
        nonlocal job_id
        result = None
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"🔄 [GENERATION] Background task started for {gen_request.artifact_type}")
            
            # Generate with progress updates
            async def generate_with_progress():
                nonlocal job_id
                final_result = None
                temp_job_id = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
                
                # Start generation to get job_id and emit progress
                async for update in service.generate_artifact(
                    artifact_type=gen_request.artifact_type,
                    meeting_notes=meeting_notes,
                    context_id=gen_request.context_id,
                    options=gen_request.options.dict() if gen_request.options else None,
                    stream=False
                ):
                    # Capture job_id from first update
                    if not job_id and update.get("job_id"):
                        job_id = update.get("job_id")
                        logger.info(f"📋 [GENERATION] Job ID assigned: {job_id}")
                        # Use the real job_id for all subsequent events
                        temp_job_id = job_id
                    
                    # Use temp_job_id if real job_id not yet available
                    current_job_id = job_id or temp_job_id
                    
                    # Emit progress if this is a progress update
                    if update.get("type") == "progress":
                        try:
                            await websocket_manager.emit_generation_progress(
                                job_id=current_job_id,
                                progress=update.get("progress", 0.0),
                                message=update.get("message", ""),
                                quality_prediction=update.get("quality_prediction")
                            )
                            logger.debug(f"📡 [GENERATION] Emitted progress: {update.get('progress', 0.0)}% for job {current_job_id}")
                        except Exception as e:
                            logger.warning(f"Failed to emit progress: {e}")
                    
                    # Save every update as potential final result (last one wins)
                    final_result = update
                
                return final_result
            
            result = loop.run_until_complete(generate_with_progress())
            job_id = result.get("job_id") if result else job_id
            logger.info(f"✅ [GENERATION] Background task completed: job_id={job_id}, "
                       f"has_artifact={bool(result.get('artifact') if result else False)}, "
                       f"status={result.get('status') if result else 'unknown'}")
            
            # Emit WebSocket event
            if job_id and result and result.get("artifact"):
                logger.info(f"📡 [WEBSOCKET] Emitting generation_complete event: job_id={job_id}, "
                           f"artifact_id={result.get('artifact', {}).get('id')}, "
                           f"validation_score={result.get('artifact', {}).get('validation', {}).get('score', 0)}")
                artifact = result.get("artifact", {}).copy()
                artifact_id = artifact.get("id") or artifact.get("artifact_id") or job_id
                validation = artifact.get("validation", {})
                validation_score = validation.get("score", 0.0) if isinstance(validation, dict) else getattr(validation, "score", 0.0)
                is_valid = validation.get("is_valid", False) if isinstance(validation, dict) else getattr(validation, "is_valid", False)
                
                # Ensure artifact has cleaned Mermaid content if it's a Mermaid diagram
                if artifact.get("artifact_type", "").startswith("mermaid_") and artifact.get("content"):
                    try:
                        from backend.services.validation_service import ValidationService
                        validator = ValidationService()
                        cleaned_content = validator._extract_mermaid_diagram(artifact["content"])
                        if cleaned_content != artifact["content"]:
                            logger.info(f"🧹 [GENERATION] Cleaning Mermaid content for WebSocket: removed {len(artifact['content']) - len(cleaned_content)} chars")
                            artifact["content"] = cleaned_content
                    except Exception as e:
                        logger.warning(f"Failed to clean Mermaid content for WebSocket: {e}")
                
                # Use asyncio to call async method from sync context
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(
                    websocket_manager.emit_generation_complete(
                        job_id=job_id,
                        artifact_id=str(artifact_id),
                        validation_score=float(validation_score),
                        is_valid=bool(is_valid),
                        artifact=artifact  # Include full artifact with cleaned content
                    )
                )
                logger.info(f"✅ [WEBSOCKET] Successfully emitted generation_complete for job {job_id}")
            elif result and not result.get("artifact"):
                logger.warning(f"⚠️ [GENERATION] Result has no artifact: job_id={job_id}, result_keys={list(result.keys()) if result else []}")
            elif not job_id:
                logger.warning(f"⚠️ [GENERATION] No job_id available to emit WebSocket event")
        except Exception as e:
            logger.error(f"❌ [GENERATION] Background generation task failed: {e}", exc_info=True)
        finally:
            loop.close()
            logger.debug(f"🧹 [GENERATION] Background task cleanup completed")
    
    # Wait a short time for the artifact to be ready (improves UX)
    # This gives immediate results for fast generations while still allowing background for slow ones
    background_tasks.add_task(generate_task)
    
    # Wait up to 60 seconds for the job to complete (most generations finish within this time)
    # Longer wait avoids premature "pending" responses that feel like timeouts in the UI.
    max_wait = 60
    for i in range(max_wait * 2):  # Check every 0.5 seconds
        await asyncio.sleep(0.5)
        
        # Check if job completed
        service = get_service()
        if job_id and job_id in service.active_jobs:
            job_status = service.active_jobs[job_id]
            if job_status.get("status") == GenerationStatus.COMPLETED.value:
                # Artifact is ready! Return it directly
                artifact = job_status.get("artifact")
                if artifact:
                    logger.info(f"✅ [GENERATION] Artifact ready within {(i+1)/2}s, returning directly: job_id={job_id}")
                    return GenerationResponse(
                        job_id=job_id,
                        status=GenerationStatus.COMPLETED,
                        artifact_id=artifact.get("id") or artifact.get("artifact_id"),
                        artifact=artifact
                    )
            elif job_status.get("status") == GenerationStatus.FAILED.value:
                # Generation failed - try to get more details
                error = job_status.get("error", "Generation failed")
                error_type = job_status.get("error_type", "unknown")
                suggestion = job_status.get("suggestion", "")
                
                logger.error(f"❌ [GENERATION] Generation failed: job_id={job_id}, error={error}, type={error_type}")
                
                # Return more helpful error message
                error_detail = error
                if suggestion:
                    error_detail = f"{error}\n\nSuggestion: {suggestion}"
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
    
    # If we reach here, generation is still in progress after 30 seconds
    # Return the job_id so frontend can wait for WebSocket events
    logger.info(f"⏳ [GENERATION] Generation still in progress after {max_wait}s, returning job_id: {job_id}")
    response = GenerationResponse(
        job_id=job_id or "pending",
        status=GenerationStatus.IN_PROGRESS,
        message="Generation in progress. The artifact will be delivered via WebSocket when ready."
    )
    logger.info(f"📤 [GENERATION] Returning response: job_id={response.job_id}, status={response.status}")
    return response


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
        "folder_id": "meeting-notes-folder-id",
        "context_id": "optional-context-id",
        "options": {...}
    }
    """
    logger.info(f"📥 [STREAM] Received streaming generation request: "
               f"artifact_type={stream_request.get('artifact_type')}, "
               f"has_meeting_notes={bool(stream_request.get('meeting_notes'))}, "
               f"folder_id={stream_request.get('folder_id')}, context_id={stream_request.get('context_id')}")
    
    artifact_type_str = stream_request.get("artifact_type")
    meeting_notes = stream_request.get("meeting_notes", "")
    folder_id = stream_request.get("folder_id")
    context_id = stream_request.get("context_id")
    options = stream_request.get("options", {})
    
    if not artifact_type_str:
        logger.warning(f"❌ [STREAM] Request validation failed: missing artifact_type")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="artifact_type is required"
        )
    
    # If folder_id is provided, load notes from the folder
    if folder_id and not meeting_notes:
        from backend.services.meeting_notes_service import get_service as get_notes_service
        notes_service = get_notes_service()
        if not hasattr(notes_service, 'get_notes_by_folder'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Meeting notes service is not properly initialized"
            )
        folder_notes = notes_service.get_notes_by_folder(folder_id)
        if not folder_notes:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No notes found in folder: {folder_id}"
            )
        # Combine all notes from the folder
        meeting_notes = "\n\n".join([note.get("content", "") for note in folder_notes])
    
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
        logger.info(f"🔄 [STREAM] Starting streaming generation for {artifact_type.value}")
        async for update in service.generate_artifact(
            artifact_type=artifact_type,
            meeting_notes=meeting_notes,
            context_id=context_id,
            options=options,
            stream=True
        ):
            # Emit WebSocket event if job_id available
            job_id = update.get("job_id")
            update_type = update.get("type")
            logger.debug(f"📡 [STREAM] Received update: job_id={job_id}, type={update_type}, progress={update.get('progress')}")
            
            if job_id:
                if update_type == "progress":
                    logger.debug(f"📤 [STREAM] Emitting progress event: job_id={job_id}, progress={update.get('progress')}")
                    await websocket_manager.emit_generation_progress(
                        job_id=job_id,
                        progress=update.get("progress", 0.0),
                        message=update.get("message", ""),
                        quality_prediction=update.get("quality_prediction"),
                    )
                elif update_type == "complete":
                    artifact = update.get("artifact", {})
                    artifact_id = artifact.get("id") or artifact.get("artifact_id") or job_id
                    validation = artifact.get("validation", {})
                    validation_score = validation.get("score", 0.0) if isinstance(validation, dict) else getattr(validation, "score", 0.0)
                    is_valid = validation.get("is_valid", False) if isinstance(validation, dict) else getattr(validation, "is_valid", False)
                    
                    logger.info(f"✅ [STREAM] Generation complete, emitting event: job_id={job_id}, "
                               f"artifact_id={artifact_id}, validation_score={validation_score:.1f}, is_valid={is_valid}")
                    await websocket_manager.emit_generation_complete(
                        job_id=job_id,
                        artifact_id=str(artifact_id),
                        validation_score=float(validation_score),
                        is_valid=bool(is_valid),
                        artifact=artifact  # Include full artifact for immediate display
                    )
                elif update_type == "error":
                    error_msg = update.get("error", "Unknown error")
                    logger.error(f"❌ [STREAM] Generation error, emitting event: job_id={job_id}, error={error_msg}")
                    await websocket_manager.emit_generation_error(
                        job_id=job_id,
                        error=error_msg
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
        if not item.meeting_notes and not item.context_id and not item.folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each item must include meeting_notes, folder_id, or context_id",
            )

        # Load notes from folder if provided and meeting_notes missing
        meeting_notes = item.meeting_notes or ""
        if item.folder_id and not meeting_notes:
            from backend.services.meeting_notes_service import get_service as get_notes_service
            notes_service = get_notes_service()
            if not hasattr(notes_service, "get_notes_by_folder"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Meeting notes service is not properly initialized",
                )
            folder_notes = notes_service.get_notes_by_folder(item.folder_id)
            if not folder_notes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No notes found in folder: {item.folder_id}",
                )
            meeting_notes = "\n\n".join([note.get("content", "") for note in folder_notes])

        if not meeting_notes and not item.context_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each item must include meeting_notes or context_id after folder resolution",
            )

        result = await service.generate_artifact_sync(
            artifact_type=item.artifact_type,
            meeting_notes=meeting_notes,
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
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        version_service.create_version(
            artifact_id=artifact_id,
            artifact_type=updated.get("artifact_type", "unknown"),
            content=body.get("content"),
            metadata={
                "updated_by": current_user.username,
                "update_type": "manual_edit",
                **(body.get("metadata") or {})
            }
        )
    except Exception as e:
        logger.warning(f"Failed to create version for updated artifact: {e}")
    
    return {
        "success": True,
        "artifact_id": artifact_id,
        "message": "Artifact updated successfully"
    }


@router.get("/artifacts", response_model=List[dict], summary="List all artifacts")
@limiter.limit("30/minute")
async def list_artifacts(
    request: Request,
    all_versions: bool = Query(False, description="If True, return all versions of all artifacts. If False (default), return only latest version per type."),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List all generated artifacts.
    
    Args:
        all_versions: If True, return all versions of all artifacts. If False (default), return only latest version per type.
    
    Returns:
        List of artifact objects with id, type, content, validation, etc.
    """
    service = get_service()
    artifacts = []
    artifact_ids_seen = set()  # Track to avoid duplicates
    
    # Helper function to clean Mermaid content
    def clean_mermaid_content(content: str, artifact_type: str) -> str:
        """Clean Mermaid diagram content if needed."""
        if artifact_type.startswith("mermaid_") and content:
            try:
                from backend.services.validation_service import ValidationService
                validator = ValidationService()
                cleaned = validator._extract_mermaid_diagram(content)
                if cleaned != content:
                    logger.debug(f"🧹 [LIST_ARTIFACTS] Cleaned Mermaid content: removed {len(content) - len(cleaned)} chars")
                return cleaned
            except Exception as e:
                logger.warning(f"⚠️ [LIST_ARTIFACTS] Failed to clean Mermaid content: {e}")
        return content
    
    # 1. Get all completed artifacts from active_jobs (in-memory, current session)
    for job_id, job in service.active_jobs.items():
        if job.get("status") == GenerationStatus.COMPLETED.value:
            artifact = job.get("artifact")
            if artifact:
                artifact_id = artifact.get("id") or artifact.get("artifact_id") or job_id
                if artifact_id not in artifact_ids_seen:
                    artifact_ids_seen.add(artifact_id)
                    artifact_type = artifact.get("artifact_type") or artifact.get("type") or job.get("artifact_type", "unknown")
                    raw_content = artifact.get("content") or job.get("artifact_content", "")
                    # Clean Mermaid content if needed
                    cleaned_content = clean_mermaid_content(raw_content, artifact_type)
                    
                    # Convert to frontend format
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": artifact.get("generated_at") or job.get("created_at") or job.get("completed_at", datetime.now().isoformat()),
                        "updated_at": job.get("updated_at") or artifact.get("generated_at") or job.get("created_at", datetime.now().isoformat()),
                    }
                    # Add optional fields
                    if "validation" in artifact:
                        validation = artifact["validation"]
                        if isinstance(validation, dict):
                            artifact_dict["score"] = validation.get("score", 0.0)
                    if "html_content" in artifact:
                        artifact_dict["html_content"] = artifact["html_content"]
                    if "model_used" in artifact:
                        artifact_dict["model_used"] = artifact["model_used"]
                    if "attempts" in artifact:
                        artifact_dict["attempts"] = artifact["attempts"]
                    artifacts.append(artifact_dict)
    
    # 2. Load artifacts from VersionService (persistent storage)
    try:
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        
        if all_versions:
            # Return ALL versions of ALL artifacts
            for artifact_id, versions in version_service.versions.items():
                if not versions:
                    continue
                
                # Add all versions for this artifact
                for version in versions:
                    artifact_type = version.get("artifact_type", "unknown")
                    raw_content = version.get("content", "")
                    # Clean Mermaid content if needed
                    cleaned_content = clean_mermaid_content(raw_content, artifact_type)
                    
                    # Convert version to frontend format
                    metadata = version.get("metadata", {})
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": version.get("created_at", datetime.now().isoformat()),
                        "updated_at": version.get("created_at", datetime.now().isoformat()),
                        "version": version.get("version", 1),
                        "is_current": version.get("is_current", False),
                    }
                    # Add optional fields from metadata
                    if "validation_score" in metadata:
                        artifact_dict["score"] = metadata["validation_score"]
                    if "html_content" in metadata:
                        artifact_dict["html_content"] = metadata["html_content"]
                    if "model_used" in metadata:
                        artifact_dict["model_used"] = metadata["model_used"]
                    if "attempts" in metadata:
                        artifact_dict["attempts"] = metadata["attempts"]
                    artifacts.append(artifact_dict)
        else:
            # Return only current/latest version per artifact (original behavior)
            for artifact_id, versions in version_service.versions.items():
                if not versions:
                    continue
                
                # Get the current version (is_current=True) or latest version
                current_version = None
                for version in versions:
                    if version.get("is_current", False):
                        current_version = version
                        break
                
                if not current_version and versions:
                    # If no current version, use the latest one
                    current_version = versions[-1]
                
                if current_version and artifact_id not in artifact_ids_seen:
                    artifact_ids_seen.add(artifact_id)
                    artifact_type = current_version.get("artifact_type", "unknown")
                    raw_content = current_version.get("content", "")
                    # Clean Mermaid content if needed
                    cleaned_content = clean_mermaid_content(raw_content, artifact_type)
                    
                    # Convert version to frontend format
                    metadata = current_version.get("metadata", {})
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": current_version.get("created_at", datetime.now().isoformat()),
                        "updated_at": current_version.get("created_at", datetime.now().isoformat()),
                    }
                    # Add optional fields from metadata
                    if "validation_score" in metadata:
                        artifact_dict["score"] = metadata["validation_score"]
                    if "html_content" in metadata:
                        artifact_dict["html_content"] = metadata["html_content"]
                    if "model_used" in metadata:
                        artifact_dict["model_used"] = metadata["model_used"]
                    if "attempts" in metadata:
                        artifact_dict["attempts"] = metadata["attempts"]
                    artifacts.append(artifact_dict)
    except Exception as e:
        logger.warning(f"Failed to load artifacts from version service: {e}")
    
    if all_versions:
        # Return all versions, sorted by created_at descending (newest first)
        artifacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        logger.info(f"📋 [GENERATION] Returning {len(artifacts)} artifacts (all versions)")
        return artifacts
    
    # Group by artifact_type and keep only the latest version per type
    artifacts_by_type: Dict[str, Dict] = {}
    for artifact in artifacts:
        artifact_type = artifact.get("type", "unknown")
        created_at = artifact.get("created_at", "")
        
        # If we haven't seen this type, or this one is newer, keep it
        if artifact_type not in artifacts_by_type:
            artifacts_by_type[artifact_type] = artifact
        else:
            existing = artifacts_by_type[artifact_type]
            existing_date = existing.get("created_at", "")
            if created_at > existing_date:
                artifacts_by_type[artifact_type] = artifact
    
    # Convert back to list and sort by created_at descending (newest first)
    latest_artifacts = list(artifacts_by_type.values())
    latest_artifacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    logger.info(f"📋 [GENERATION] Returning {len(latest_artifacts)} artifacts (latest version per type, from {len(artifacts)} total)")
    return latest_artifacts


@router.post("/artifacts/{artifact_id}/regenerate", response_model=GenerationResponse)
@limiter.limit("5/minute")
async def regenerate_artifact(
    request: Request,
    artifact_id: str,
    body: dict = None,
    background_tasks: BackgroundTasks = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Regenerate an artifact with the same or updated parameters.
    
    Path parameters:
    - artifact_id: Artifact identifier (can be artifact_type like 'mermaid_erd')
    
    Request body (optional):
    {
        "options": {
            "max_retries": 3,
            "temperature": 0.7
        }
    }
    """
    logger.info(f"🔄 [REGENERATE] Regenerating artifact: {artifact_id}")
    
    service = get_service()
    
    # Try to find original artifact in active_jobs or version_service
    original_meeting_notes = None
    original_artifact_type = None
    
    # Check active jobs first
    if artifact_id in service.active_jobs:
        job = service.active_jobs[artifact_id]
        original_meeting_notes = job.get("meeting_notes", "")
        original_artifact_type = job.get("artifact_type")
        logger.info(f"🔍 [REGENERATE] Found artifact in active_jobs")
    
    # Check version service
    if not original_meeting_notes:
        try:
            from backend.services.version_service import get_version_service
            version_service = get_version_service()
            
            # artifact_id might be the artifact_type (stable ID)
            if artifact_id in version_service.versions:
                versions = version_service.versions[artifact_id]
                if versions:
                    current_version = versions[-1]  # Get latest
                    original_artifact_type = current_version.get("artifact_type", artifact_id)
                    original_meeting_notes = current_version.get("metadata", {}).get("meeting_notes", "")
                    logger.info(f"🔍 [REGENERATE] Found artifact in version_service: type={original_artifact_type}")
        except Exception as e:
            logger.warning(f"Could not check version service: {e}")
    
    # If still no meeting notes, try to infer artifact type from ID
    if not original_artifact_type:
        # The artifact_id might BE the artifact_type
        try:
            original_artifact_type = ArtifactType(artifact_id)
            logger.info(f"🔍 [REGENERATE] Using artifact_id as artifact_type: {original_artifact_type}")
        except ValueError:
            # Try to extract type from ID pattern like "mermaid_erd_20231209_123456"
            for art_type in ArtifactType:
                if artifact_id.startswith(art_type.value):
                    original_artifact_type = art_type
                    logger.info(f"🔍 [REGENERATE] Inferred artifact_type from ID: {original_artifact_type}")
                    break
    
    if not original_artifact_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot determine artifact type for {artifact_id}. Provide artifact_type in request body."
        )
    
    # Use meeting notes from request body if provided, otherwise use original
    if body:
        body_json = body if isinstance(body, dict) else {}
    else:
        try:
            body_json = await request.json()
        except:
            body_json = {}
    
    meeting_notes = body_json.get("meeting_notes", original_meeting_notes or "Regenerate previous artifact")
    options = body_json.get("options", {})
    
    # Ensure minimum meeting notes
    if len(meeting_notes.strip()) < 10:
        meeting_notes = f"Regenerate {original_artifact_type.value if hasattr(original_artifact_type, 'value') else original_artifact_type} artifact with improved quality."
    
    # Create generation request
    gen_request = GenerationRequest(
        artifact_type=original_artifact_type if isinstance(original_artifact_type, ArtifactType) else ArtifactType(original_artifact_type),
        meeting_notes=meeting_notes,
        options=GenerationOptions(**options) if options else GenerationOptions()
    )
    
    logger.info(f"🚀 [REGENERATE] Starting regeneration: artifact_type={gen_request.artifact_type.value}, "
                f"meeting_notes_length={len(meeting_notes)}")
    
    # Generate in background (same logic as generate_artifact)
    job_id = None
    
    def regenerate_task():
        nonlocal job_id
        result = None
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"🔄 [REGENERATE] Background task started for {gen_request.artifact_type.value}")
            
            async def generate_with_progress():
                nonlocal job_id
                final_result = None
                
                async for update in service.generate_artifact(
                    artifact_type=gen_request.artifact_type,
                    meeting_notes=meeting_notes,
                    context_id=None,
                    options=gen_request.options.dict() if gen_request.options else None,
                    stream=False
                ):
                    if not job_id and update.get("job_id"):
                        job_id = update.get("job_id")
                        logger.info(f"📋 [REGENERATE] Job ID assigned: {job_id}")
                    
                    if update.get("type") == "progress":
                        try:
                            from backend.core.websocket import websocket_manager
                            await websocket_manager.emit_generation_progress(
                                job_id=job_id or f"regen_{artifact_id}",
                                progress=update.get("progress", 0.0),
                                message=f"Regenerating: {update.get('message', '')}",
                                quality_prediction=update.get("quality_prediction")
                            )
                        except Exception as e:
                            logger.warning(f"Failed to emit progress: {e}")
                    
                    final_result = update
                
                return final_result
            
            result = loop.run_until_complete(generate_with_progress())
            job_id = result.get("job_id") if result else job_id
            logger.info(f"✅ [REGENERATE] Background task completed: job_id={job_id}")
            
            # Emit WebSocket event
            if job_id and result and result.get("artifact"):
                from backend.core.websocket import websocket_manager
                artifact = result.get("artifact", {})
                loop.run_until_complete(
                    websocket_manager.emit_generation_complete(
                        job_id=job_id,
                        artifact_id=str(artifact.get("id", job_id)),
                        validation_score=float(artifact.get("validation", {}).get("score", 0)),
                        is_valid=bool(artifact.get("validation", {}).get("is_valid", False)),
                        artifact=artifact
                    )
                )
                logger.info(f"✅ [REGENERATE] WebSocket event emitted for job {job_id}")
        except Exception as e:
            logger.error(f"❌ [REGENERATE] Background regeneration task failed: {e}", exc_info=True)
        finally:
            loop.close()
    
    background_tasks.add_task(regenerate_task)
    
    # Return immediately with job_id
    response = GenerationResponse(
        job_id=job_id or f"regen_{artifact_id}",
        status=GenerationStatus.IN_PROGRESS
    )
    logger.info(f"📤 [REGENERATE] Returning response: job_id={response.job_id}, status={response.status}")
    return response


@router.get("/artifacts/{artifact_id}", response_model=dict, summary="Get artifact by ID")
@limiter.limit("30/minute")
async def get_artifact(
    request: Request,
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get a specific artifact by ID.
    
    Path parameters:
    - artifact_id: Artifact identifier
    """
    service = get_service()
    
    # Helper function to clean Mermaid content
    def clean_mermaid_content(content: str, artifact_type: str) -> str:
        """Clean Mermaid diagram content if needed."""
        if artifact_type.startswith("mermaid_") and content:
            try:
                from backend.services.validation_service import ValidationService
                validator = ValidationService()
                cleaned = validator._extract_mermaid_diagram(content)
                if cleaned != content:
                    logger.debug(f"🧹 [GET_ARTIFACT] Cleaned Mermaid content: removed {len(content) - len(cleaned)} chars")
                return cleaned
            except Exception as e:
                logger.warning(f"⚠️ [GET_ARTIFACT] Failed to clean Mermaid content: {e}")
        return content
    
    # Find artifact in active_jobs
    if artifact_id in service.active_jobs:
        job = service.active_jobs[artifact_id]
        artifact = job.get("artifact")
        if artifact:
            artifact_type = artifact.get("artifact_type") or artifact.get("type") or job.get("artifact_type", "unknown")
            raw_content = artifact.get("content") or job.get("artifact_content", "")
            # Clean Mermaid content if needed
            cleaned_content = clean_mermaid_content(raw_content, artifact_type)
            
            # Convert to frontend format
            artifact_dict = {
                "id": artifact.get("id") or artifact.get("artifact_id") or artifact_id,
                "type": artifact_type,
                "content": cleaned_content,
                "created_at": artifact.get("generated_at") or job.get("created_at") or job.get("completed_at", datetime.now().isoformat()),
                "updated_at": job.get("updated_at") or artifact.get("generated_at") or job.get("created_at", datetime.now().isoformat()),
            }
            # Add optional fields
            if "validation" in artifact:
                validation = artifact["validation"]
                if isinstance(validation, dict):
                    artifact_dict["score"] = validation.get("score", 0.0)
            if "html_content" in artifact:
                artifact_dict["html_content"] = artifact["html_content"]
            if "model_used" in artifact:
                artifact_dict["model_used"] = artifact["model_used"]
            return artifact_dict
    
    # Check VersionService (persistent storage)
    try:
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        
        if artifact_id in version_service.versions:
            versions = version_service.versions[artifact_id]
            if versions:
                # Get the current version (is_current=True) or latest version
                current_version = None
                for version in versions:
                    if version.get("is_current", False):
                        current_version = version
                        break
                
                if not current_version and versions:
                    current_version = versions[-1]
                
                if current_version:
                    artifact_type = current_version.get("artifact_type", "unknown")
                    raw_content = current_version.get("content", "")
                    # Clean Mermaid content if needed
                    cleaned_content = clean_mermaid_content(raw_content, artifact_type)
                    
                    metadata = current_version.get("metadata", {})
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": current_version.get("created_at", datetime.now().isoformat()),
                        "updated_at": current_version.get("created_at", datetime.now().isoformat()),
                    }
                    # Add optional fields from metadata
                    if "validation_score" in metadata:
                        artifact_dict["score"] = metadata["validation_score"]
                    if "html_content" in metadata:
                        artifact_dict["html_content"] = metadata["html_content"]
                    if "model_used" in metadata:
                        artifact_dict["model_used"] = metadata["model_used"]
                    return artifact_dict
    except Exception as e:
        logger.warning(f"Failed to load artifact from version service: {e}")
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Artifact {artifact_id} not found"
    )



