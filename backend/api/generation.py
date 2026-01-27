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
    logger.info(f"🚀 [GENERATION] ========== GENERATE ARTIFACT REQUEST RECEIVED ==========")
    logger.info(f"🚀 [GENERATION] Step 1: Request received")
    logger.info(f"🚀 [GENERATION] Step 1.1: URL={request.url}, Method={request.method}")
    logger.info(f"🚀 [GENERATION] Step 1.2: Client={request.client.host if request.client else 'unknown'}")
    logger.info(f"🚀 [GENERATION] Step 1.3: User={current_user.username if current_user else 'anonymous'}")
    logger.info(f"🚀 [GENERATION] Step 2: Parsing request body")
    logger.info(f"🚀 [GENERATION] Step 2.1: artifact_type={gen_request.artifact_type}")
    logger.info(f"🚀 [GENERATION] Step 2.2: has_meeting_notes={bool(gen_request.meeting_notes)}, meeting_notes_length={len(gen_request.meeting_notes) if gen_request.meeting_notes else 0}")
    logger.info(f"🚀 [GENERATION] Step 2.3: folder_id={gen_request.folder_id}")
    logger.info(f"🚀 [GENERATION] Step 2.4: context_id={gen_request.context_id}")
    logger.info(f"🚀 [GENERATION] Step 2.5: options={gen_request.options.dict() if gen_request.options else None}")
    
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
    
    # Use a mutable container to share job_id between async task and main coroutine
    job_state = {"job_id": None}
    
    async def generate_task_async():
        """
        Async background task for artifact generation.
        
        FIX: Previously this was a sync function that created its own event loop,
        which blocked FastAPI's main event loop. Now properly async to allow
        concurrent request handling.
        """
        result = None
        try:
            logger.info(f"🔄 [GENERATION] Background task started for {gen_request.artifact_type}")
            
            final_result = None
            temp_job_id = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Start generation to get job_id and emit progress
            async for update in service.generate_artifact(
                artifact_type=gen_request.artifact_type,
                meeting_notes=meeting_notes,
                context_id=gen_request.context_id,
                options=gen_request.options.dict() if gen_request.options else None,
                stream=True,  # Enable streaming to capture progress events for WebSocket
                folder_id=gen_request.folder_id  # Pass folder_id for artifact association
            ):
                # Capture job_id from first update
                if not job_state["job_id"] and update.get("job_id"):
                    job_state["job_id"] = update.get("job_id")
                    logger.info(f"📋 [GENERATION] Job ID assigned: {job_state['job_id']}")
                    temp_job_id = job_state["job_id"]
                
                # Use temp_job_id if real job_id not yet available
                current_job_id = job_state["job_id"] or temp_job_id
                
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
            
            result = final_result
            if result:
                job_state["job_id"] = result.get("job_id") or job_state["job_id"]
            
            logger.info(f"✅ [GENERATION] Background task completed: job_id={job_state['job_id']}, "
                       f"has_artifact={bool(result.get('artifact') if result else False)}, "
                       f"status={result.get('status') if result else 'unknown'}")
            
            # Emit WebSocket event
            if job_state["job_id"] and result and result.get("artifact"):
                logger.info(f"📡 [WEBSOCKET] Emitting generation_complete event: job_id={job_state['job_id']}, "
                           f"artifact_id={result.get('artifact', {}).get('id')}, "
                           f"validation_score={result.get('artifact', {}).get('validation', {}).get('score', 0)}")
                artifact = result.get("artifact", {}).copy()
                artifact_id = artifact.get("id") or artifact.get("artifact_id") or job_state["job_id"]
                validation = artifact.get("validation", {})
                validation_score = validation.get("score", 0.0) if isinstance(validation, dict) else getattr(validation, "score", 0.0)
                is_valid = validation.get("is_valid", False) if isinstance(validation, dict) else getattr(validation, "is_valid", False)
                
                # Ensure artifact has cleaned content
                if artifact.get("artifact_type", "").startswith("mermaid_") and artifact.get("content"):
                    try:
                        from backend.services.artifact_cleaner import get_cleaner
                        cleaner = get_cleaner()
                        cleaned_content = cleaner.clean_artifact(artifact["content"], artifact["artifact_type"])
                        if cleaned_content != artifact["content"]:
                            logger.info(f"🧹 [GENERATION] Cleaning artifact content for WebSocket: removed {len(artifact['content']) - len(cleaned_content)} chars")
                            artifact["content"] = cleaned_content
                    except Exception as e:
                        logger.warning(f"Failed to clean artifact content for WebSocket: {e}")
                
                # Now we can directly await since we're already async
                await websocket_manager.emit_generation_complete(
                    job_id=job_state["job_id"],
                    artifact_id=str(artifact_id),
                    validation_score=float(validation_score),
                    is_valid=bool(is_valid),
                    artifact=artifact
                )
                logger.info(f"✅ [WEBSOCKET] Successfully emitted generation_complete for job {job_state['job_id']}")
            elif result and not result.get("artifact"):
                logger.warning(f"⚠️ [GENERATION] Result has no artifact: job_id={job_state['job_id']}, result_keys={list(result.keys()) if result else []}")
            elif not job_state["job_id"]:
                logger.warning(f"⚠️ [GENERATION] No job_id available to emit WebSocket event")
        except Exception as e:
            logger.error(f"❌ [GENERATION] Background generation task failed: {e}", exc_info=True)
    
    # Start the async task properly using asyncio.create_task()
    # This runs concurrently without blocking the event loop
    asyncio.create_task(generate_task_async())
    
    # Wait up to 60 seconds for the job to complete (most generations finish within this time)
    # Longer wait avoids premature "pending" responses that feel like timeouts in the UI.
    max_wait = 60
    for i in range(max_wait * 2):  # Check every 0.5 seconds
        await asyncio.sleep(0.5)
        
        # Check if job completed (use job_state dict for shared state with async task)
        current_job_id = job_state["job_id"]
        service = get_service()
        if current_job_id and current_job_id in service.active_jobs:
            job_status = service.active_jobs[current_job_id]
            if job_status.get("status") == GenerationStatus.COMPLETED.value:
                # Artifact is ready! Return it directly
                artifact = job_status.get("artifact")
                if artifact:
                    logger.info(f"✅ [GENERATION] Artifact ready within {(i+1)/2}s, returning directly: job_id={current_job_id}")
                    return GenerationResponse(
                        job_id=current_job_id,
                        status=GenerationStatus.COMPLETED,
                        artifact_id=artifact.get("id") or artifact.get("artifact_id"),
                        artifact=artifact
                    )
            elif job_status.get("status") == GenerationStatus.FAILED.value:
                # Generation failed - try to get more details
                error = job_status.get("error", "Generation failed")
                error_type = job_status.get("error_type", "unknown")
                suggestion = job_status.get("suggestion", "")
                
                logger.error(f"❌ [GENERATION] Generation failed: job_id={current_job_id}, error={error}, type={error_type}")
                
                # Return more helpful error message
                error_detail = error
                if suggestion:
                    error_detail = f"{error}\n\nSuggestion: {suggestion}"
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
    
    # If we reach here, generation is still in progress after max_wait seconds
    # Return the job_id so frontend can wait for WebSocket events
    final_job_id = job_state["job_id"]
    logger.info(f"⏳ [GENERATION] Generation still in progress after {max_wait}s, returning job_id: {final_job_id}")
    response = GenerationResponse(
        job_id=final_job_id or "pending",
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
        logger.info(f"🔄 [STREAM] Starting streaming generation for {artifact_type.value}, folder_id={folder_id}")
        async for update in service.generate_artifact(
            artifact_type=artifact_type,
            meeting_notes=meeting_notes,
            context_id=context_id,
            options=options,
            stream=True,
            folder_id=folder_id  # Pass folder_id for artifact association
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
    logger.info(f"✏️ [INTERACTIVE_EDITOR] ========== UPDATE ARTIFACT REQUEST ==========")
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 1: Received update request")
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 1.1: artifact_id={artifact_id}, content_length={len(body.get('content', ''))}, has_metadata={bool(body.get('metadata'))}")
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 1.2: user={current_user.username}, metadata_source={body.get('metadata', {}).get('source', 'unknown')}")
    
    if "content" not in body:
        logger.error(f"✏️ [INTERACTIVE_EDITOR] Step 1.ERROR: Missing content field")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content field is required"
        )
    
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 2: Calling generation service to update artifact")
    service = get_service()
    updated = service.update_artifact(artifact_id, body.get("content"), body.get("metadata"))
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 2.1: Service update complete: found={bool(updated)}")
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    # Create new version
    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3: Creating new version for updated artifact")
    try:
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        
        # Intelligent artifact_type fallback logic
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1: Determining artifact_type")
        artifact_type = updated.get("artifact_type")
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.1: artifact_type from updated={artifact_type}")
        
        # If not in updated artifact, check existing versions
        if not artifact_type or artifact_type == "unknown":
            logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.2: Checking existing versions for artifact_type")
            if artifact_id in version_service.versions:
                versions = version_service.versions[artifact_id]
                if versions:
                    # Get artifact_type from latest version
                    artifact_type = versions[-1].get("artifact_type")
                    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.3: Found artifact_type from version: {artifact_type}")
        
        # If still unknown, try to infer from artifact_id pattern
        if not artifact_type or artifact_type == "unknown":
            logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.4: Inferring artifact_type from artifact_id pattern")
            # Check if artifact_id matches an ArtifactType enum value
            try:
                from backend.models.dto import ArtifactType
                try:
                    artifact_type_enum = ArtifactType(artifact_id)
                    artifact_type = artifact_type_enum.value
                    logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.5: Matched ArtifactType enum: {artifact_type}")
                except ValueError:
                    # Try to extract type from ID pattern like "mermaid_erd_20231209_123456"
                    for art_type in ArtifactType:
                        if artifact_id.startswith(art_type.value):
                            artifact_type = art_type.value
                            logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.5: Matched pattern: {artifact_type}")
                            break
            except ImportError:
                logger.warning(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.5: Could not import ArtifactType")
                pass
        
        # Final fallback
        if not artifact_type or artifact_type == "unknown":
            artifact_type = "unknown"
            logger.warning(f"✏️ [INTERACTIVE_EDITOR] Step 3.1.6: Using fallback artifact_type='unknown'")
        
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.2: Final artifact_type={artifact_type}")
        
        # BUGFIX: Preserve folder_id from previous version
        # This ensures artifacts remain associated with their folder after manual edits
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.3: Preserving folder_id from previous version")
        previous_folder_id = None
        if artifact_id in version_service.versions:
            versions = version_service.versions[artifact_id]
            if versions:
                previous_metadata = versions[-1].get("metadata", {})
                previous_folder_id = previous_metadata.get("folder_id")
                logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.3.1: Found previous_folder_id={previous_folder_id}")
        
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.4: Creating version with artifact_type={artifact_type}, folder_id={previous_folder_id}")
        version_service.create_version(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            content=body.get("content"),
            metadata={
                "updated_by": current_user.username,
                "update_type": "manual_edit",
                "folder_id": previous_folder_id,  # Preserve folder association
                "artifact_type": artifact_type,  # Also preserve artifact_type
                **(body.get("metadata") or {})
            }
        )
        logger.info(f"✏️ [INTERACTIVE_EDITOR] Step 3.5: Version created successfully")
    except Exception as e:
        logger.warning(f"✏️ [INTERACTIVE_EDITOR] Step 3.ERROR: Failed to create version: {e}", exc_info=True)
    
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
    folder_id: Optional[str] = Query(None, description="Filter artifacts by meeting notes folder ID"),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List all generated artifacts.
    
    Args:
        all_versions: If True, return all versions of all artifacts. If False (default), return only latest version per type.
        folder_id: Optional filter to only return artifacts associated with a specific meeting notes folder.
    
    Returns:
        List of artifact objects with id, type, content, validation, folder_id, etc.
    """
    logger.info(f"📋 [LIST_ARTIFACTS] ========== LIST ARTIFACTS REQUEST ==========")
    logger.info(f"📋 [LIST_ARTIFACTS] Step 1: Initializing list request")
    logger.info(f"📋 [LIST_ARTIFACTS] Step 1.1: all_versions={all_versions}, folder_id={folder_id}")
    
    service = get_service()
    artifacts = []
    artifact_ids_seen = set()  # Track to avoid duplicates
    
    # CONSTANT: Default folder for orphan artifacts (with null folder_id)
    DEFAULT_ORPHAN_FOLDER = "Orphaned Artifacts"
    
    # Use centralized ArtifactCleaner service (avoids code duplication)
    from backend.services.artifact_cleaner import get_cleaner
    cleaner = get_cleaner()
    
    def clean_artifact_content(content: str, artifact_type: str) -> str:
        """Clean artifact content using the centralized ArtifactCleaner service."""
        try:
            return cleaner.clean_artifact(content, artifact_type)
        except Exception as e:
            logger.warning(f"⚠️ [LIST_ARTIFACTS] Failed to clean artifact content: {e}")
            return content
    
    # 1. Get all completed artifacts from active_jobs (in-memory, current session)
    logger.info(f"📋 [LIST_ARTIFACTS] Step 2: Loading artifacts from active_jobs (in-memory)")
    logger.info(f"📋 [LIST_ARTIFACTS] Step 2.1: Checking {len(service.active_jobs)} active jobs")
    active_jobs_count = 0
    for job_id, job in service.active_jobs.items():
        if job.get("status") == GenerationStatus.COMPLETED.value:
            artifact = job.get("artifact")
            if artifact:
                active_jobs_count += 1
                # Get artifact's folder_id (from artifact or job)
                # If null, assign to default orphan folder
                artifact_folder_id = artifact.get("folder_id") or job.get("folder_id")
                if not artifact_folder_id:
                    artifact_folder_id = DEFAULT_ORPHAN_FOLDER
                
                # Filter by folder_id if specified
                if folder_id and artifact_folder_id != folder_id:
                    logger.debug(f"📋 [LIST_ARTIFACTS] Step 2.{active_jobs_count}: Skipping artifact (folder mismatch): {artifact_folder_id} != {folder_id}")
                    continue
                
                artifact_id = artifact.get("id") or artifact.get("artifact_id") or job_id
                if artifact_id not in artifact_ids_seen:
                    artifact_ids_seen.add(artifact_id)
                    artifact_type = artifact.get("artifact_type") or artifact.get("type") or job.get("artifact_type", "unknown")
                    raw_content = artifact.get("content") or job.get("artifact_content", "")
                    # Clean artifact content using centralized cleaner
                    cleaned_content = clean_artifact_content(raw_content, artifact_type)
                    
                    logger.info(f"📋 [LIST_ARTIFACTS] Step 2.{active_jobs_count}: Adding artifact from active_jobs: id={artifact_id}, type={artifact_type}, folder_id={artifact_folder_id}")
                    
                    # Convert to frontend format
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": artifact.get("generated_at") or job.get("created_at") or job.get("completed_at", datetime.now().isoformat()),
                        "updated_at": job.get("updated_at") or artifact.get("generated_at") or job.get("created_at", datetime.now().isoformat()),
                        "folder_id": artifact_folder_id,  # Include folder association
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
    logger.info(f"📋 [LIST_ARTIFACTS] Step 2.2: Found {active_jobs_count} completed artifacts in active_jobs, added {len([a for a in artifacts if a.get('id') in artifact_ids_seen])} to list")
    
    # 2. Load artifacts from VersionService (persistent storage)
    logger.info(f"📋 [LIST_ARTIFACTS] Step 3: Loading artifacts from VersionService (persistent storage)")
    try:
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        logger.info(f"📋 [LIST_ARTIFACTS] Step 3.1: VersionService has {len(version_service.versions)} artifacts with versions")
        
        if all_versions:
            logger.info(f"📋 [LIST_ARTIFACTS] Step 3.2: Returning ALL versions")
            # Return ALL versions of ALL artifacts
            for artifact_id, versions in version_service.versions.items():
                if not versions:
                    continue
                
                # Add all versions for this artifact
                for version in versions:
                    metadata = version.get("metadata", {})
                    version_folder_id = metadata.get("folder_id")
                    # Assign default folder if null
                    if not version_folder_id:
                        version_folder_id = DEFAULT_ORPHAN_FOLDER
                    
                    # Filter by folder_id if specified
                    if folder_id and version_folder_id != folder_id:
                        continue
                    
                    artifact_type = version.get("artifact_type", "unknown")
                    raw_content = version.get("content", "")
                    # Clean artifact content using centralized cleaner
                    cleaned_content = clean_artifact_content(raw_content, artifact_type)
                    
                    # Convert version to frontend format
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": version.get("created_at", datetime.now().isoformat()),
                        "updated_at": version.get("created_at", datetime.now().isoformat()),
                        "version": version.get("version", 1),
                        "is_current": version.get("is_current", False),
                        "folder_id": version_folder_id,  # Include folder association (defaulted)
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
            logger.info(f"📋 [LIST_ARTIFACTS] Step 3.2: Returning only latest version per artifact")
            version_service_count = 0
            for artifact_id, versions in version_service.versions.items():
                if not versions:
                    continue
                
                version_service_count += 1
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
                    metadata = current_version.get("metadata", {})
                    version_folder_id = metadata.get("folder_id")
                    # Assign default folder if null
                    if not version_folder_id:
                        version_folder_id = DEFAULT_ORPHAN_FOLDER
                    
                    # Filter by folder_id if specified
                    if folder_id and version_folder_id != folder_id:
                        logger.debug(f"📋 [LIST_ARTIFACTS] Step 3.2.{version_service_count}: Skipping artifact (folder mismatch): {version_folder_id} != {folder_id}")
                        continue
                    
                    artifact_ids_seen.add(artifact_id)
                    artifact_type = current_version.get("artifact_type", "unknown")
                    raw_content = current_version.get("content", "")
                    # Clean artifact content using centralized cleaner
                    cleaned_content = clean_artifact_content(raw_content, artifact_type)
                    
                    logger.info(f"📋 [LIST_ARTIFACTS] Step 3.2.{version_service_count}: Adding artifact from VersionService: id={artifact_id}, type={artifact_type}, folder_id={version_folder_id}, content_length={len(cleaned_content)}")
                    
                    # Convert version to frontend format
                    artifact_dict = {
                        "id": artifact_id,
                        "type": artifact_type,
                        "content": cleaned_content,
                        "created_at": current_version.get("created_at", datetime.now().isoformat()),
                        "updated_at": current_version.get("created_at", datetime.now().isoformat()),
                        "folder_id": version_folder_id,  # Include folder association (defaulted)
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
            logger.info(f"📋 [LIST_ARTIFACTS] Step 3.3: Processed {version_service_count} artifacts from VersionService, added {len([a for a in artifacts if a.get('id') not in [x.get('id') for x in artifacts[:active_jobs_count]]])} new artifacts")
    except Exception as e:
        logger.error(f"📋 [LIST_ARTIFACTS] Step 3.ERROR: Failed to load artifacts from version service: {e}", exc_info=True)
    
    logger.info(f"📋 [LIST_ARTIFACTS] Step 4: Processing results")
    logger.info(f"📋 [LIST_ARTIFACTS] Step 4.1: Total artifacts collected: {len(artifacts)}")
    
    if all_versions:
        # Return all versions, sorted by created_at descending (newest first)
        artifacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        logger.info(f"📋 [LIST_ARTIFACTS] Step 4.2: Returning {len(artifacts)} artifacts (all versions)")
        logger.info(f"📋 [LIST_ARTIFACTS] ========== LIST ARTIFACTS COMPLETE ==========")
        return artifacts
    
    # Group by (folder_id + artifact_type) and keep only the latest version per type per folder
    # FIX: Previously only grouped by artifact_type, which meant all folders shared the same artifact
    # Now each folder gets its own artifact per type
    logger.info(f"📋 [LIST_ARTIFACTS] Step 4.2: Grouping by folder_id + artifact_type")
    artifacts_by_key: Dict[str, Dict] = {}
    for artifact in artifacts:
        artifact_type = artifact.get("type", "unknown")
        artifact_folder_id = artifact.get("folder_id") or ""  # Use empty string for null folder
        created_at = artifact.get("created_at", "")
        
        # Create a composite key: folder_id + artifact_type
        # This ensures each folder can have its own version of each artifact type
        group_key = f"{artifact_folder_id}::{artifact_type}"
        
        # If we haven't seen this key, or this one is newer, keep it
        if group_key not in artifacts_by_key:
            artifacts_by_key[group_key] = artifact
            logger.debug(f"📋 [LIST_ARTIFACTS] Step 4.2.1: Added artifact to group: {group_key}")
        else:
            existing = artifacts_by_key[group_key]
            existing_date = existing.get("created_at", "")
            if created_at > existing_date:
                artifacts_by_key[group_key] = artifact
                logger.debug(f"📋 [LIST_ARTIFACTS] Step 4.2.1: Replaced artifact in group (newer): {group_key}")
    
    # Convert back to list and sort by created_at descending (newest first)
    latest_artifacts = list(artifacts_by_key.values())
    latest_artifacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    logger.info(f"📋 [LIST_ARTIFACTS] Step 4.3: Grouped to {len(latest_artifacts)} unique artifacts (from {len(artifacts)} total)")
    logger.info(f"📋 [LIST_ARTIFACTS] Step 4.4: Artifact IDs: {[a.get('id') for a in latest_artifacts[:10]]}...")  # Show first 10
    logger.info(f"📋 [LIST_ARTIFACTS] ========== LIST ARTIFACTS COMPLETE ==========")
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
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug(f"Could not parse request body as JSON: {e}")
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
    
    # Use a mutable container to share job_id between async task and main coroutine
    regen_job_state = {"job_id": None}
    
    async def regenerate_task_async():
        """
        Async background task for artifact regeneration.
        
        FIX: Previously this was a sync function that created its own event loop,
        which blocked FastAPI's main event loop. Now properly async.
        """
        result = None
        try:
            logger.info(f"🔄 [REGENERATE] Background task started for {gen_request.artifact_type.value}")
            
            final_result = None
            
            async for update in service.generate_artifact(
                artifact_type=gen_request.artifact_type,
                meeting_notes=meeting_notes,
                context_id=None,
                options=gen_request.options.dict() if gen_request.options else None,
                stream=False
            ):
                if not regen_job_state["job_id"] and update.get("job_id"):
                    regen_job_state["job_id"] = update.get("job_id")
                    logger.info(f"📋 [REGENERATE] Job ID assigned: {regen_job_state['job_id']}")
                
                if update.get("type") == "progress":
                    try:
                        await websocket_manager.emit_generation_progress(
                            job_id=regen_job_state["job_id"] or f"regen_{artifact_id}",
                            progress=update.get("progress", 0.0),
                            message=f"Regenerating: {update.get('message', '')}",
                            quality_prediction=update.get("quality_prediction")
                        )
                    except Exception as e:
                        logger.warning(f"Failed to emit progress: {e}")
                
                final_result = update
            
            result = final_result
            if result:
                regen_job_state["job_id"] = result.get("job_id") or regen_job_state["job_id"]
            logger.info(f"✅ [REGENERATE] Background task completed: job_id={regen_job_state['job_id']}")
            
            # Emit WebSocket event
            if regen_job_state["job_id"] and result and result.get("artifact"):
                artifact = result.get("artifact", {})
                await websocket_manager.emit_generation_complete(
                    job_id=regen_job_state["job_id"],
                    artifact_id=str(artifact.get("id", regen_job_state["job_id"])),
                    validation_score=float(artifact.get("validation", {}).get("score", 0)),
                    is_valid=bool(artifact.get("validation", {}).get("is_valid", False)),
                    artifact=artifact
                )
                logger.info(f"✅ [REGENERATE] WebSocket event emitted for job {regen_job_state['job_id']}")
        except Exception as e:
            logger.error(f"❌ [REGENERATE] Background regeneration task failed: {e}", exc_info=True)
    
    # Start the async task properly using asyncio.create_task()
    asyncio.create_task(regenerate_task_async())
    
    # Return immediately with placeholder job_id (actual ID will be assigned in background)
    response = GenerationResponse(
        job_id=f"regen_{artifact_id}",
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
    
    # Use centralized ArtifactCleaner service (avoids code duplication)
    from backend.services.artifact_cleaner import get_cleaner
    cleaner = get_cleaner()
    
    def clean_artifact_content(content: str, artifact_type: str) -> str:
        """Clean artifact content using the centralized ArtifactCleaner service."""
        try:
            return cleaner.clean_artifact(content, artifact_type)
        except Exception as e:
            logger.warning(f"⚠️ [GET_ARTIFACT] Failed to clean artifact content: {e}")
            return content
    
    # Find artifact in active_jobs
    if artifact_id in service.active_jobs:
        job = service.active_jobs[artifact_id]
        artifact = job.get("artifact")
        if artifact:
            artifact_type = artifact.get("artifact_type") or artifact.get("type") or job.get("artifact_type", "unknown")
            raw_content = artifact.get("content") or job.get("artifact_content", "")
            # Clean artifact content using centralized cleaner
            cleaned_content = clean_artifact_content(raw_content, artifact_type)
            
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
                    # Clean artifact content using centralized cleaner
                    cleaned_content = clean_artifact_content(raw_content, artifact_type)
                    
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


@router.delete("/artifacts/{artifact_id}", response_model=dict, summary="Delete artifact")
@limiter.limit("20/minute")
async def delete_artifact(
    request: Request,
    artifact_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Delete an artifact and all its versions.
    
    Args:
        artifact_id: Artifact identifier to delete
    
    Returns:
        Deletion confirmation
    """
    logger.info(f"🗑️ [DELETE_ARTIFACT] Request to delete artifact: {artifact_id}")
    
    deleted_from_jobs = False
    deleted_from_versions = False
    
    # Check active jobs (in-memory)
    service = get_service()
    if artifact_id in service.active_jobs:
        del service.active_jobs[artifact_id]
        deleted_from_jobs = True
        logger.info(f"✅ [DELETE_ARTIFACT] Deleted from active jobs: {artifact_id}")
    
    # Check VersionService (persistent storage)
    try:
        from backend.services.version_service import get_version_service
        version_service = get_version_service()
        
        if artifact_id in version_service.versions:
            result = version_service.delete_all_versions(artifact_id)
            if result.get("success"):
                deleted_from_versions = True
                logger.info(f"✅ [DELETE_ARTIFACT] Deleted {result.get('versions_deleted', 0)} versions from VersionService: {artifact_id}")
    except Exception as e:
        logger.warning(f"⚠️ [DELETE_ARTIFACT] Failed to delete from VersionService: {e}")
    
    if not deleted_from_jobs and not deleted_from_versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found"
        )
    
    return {
        "success": True,
        "message": f"Artifact {artifact_id} deleted successfully",
        "artifact_id": artifact_id,
        "deleted_from_jobs": deleted_from_jobs,
        "deleted_from_versions": deleted_from_versions
    }


# ============================================================================
# Custom Artifact Types Endpoints
# ============================================================================

@router.get("/artifact-types", summary="List all artifact types (built-in + custom)")
async def list_artifact_types(
    include_disabled: bool = Query(False, description="Include disabled custom types"),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    List all available artifact types including built-in and custom types.
    
    Returns list with: id, name, category, is_custom, is_enabled, description
    """
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    all_types = custom_service.get_all_artifact_types()
    
    if not include_disabled:
        all_types = [t for t in all_types if t.get("is_enabled", True)]
    
    return {
        "success": True,
        "artifact_types": all_types,
        "categories": custom_service.get_categories()
    }


@router.get("/artifact-types/custom", summary="List custom artifact types only")
async def list_custom_artifact_types(
    include_disabled: bool = Query(False, description="Include disabled custom types"),
    current_user: UserPublic = Depends(get_current_user)
):
    """List only custom-defined artifact types."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    custom_types = custom_service.list_types(include_disabled=include_disabled)
    
    return {
        "success": True,
        "custom_types": [t.to_dict() for t in custom_types],
        "count": len(custom_types)
    }


@router.post("/artifact-types/custom", summary="Create a custom artifact type")
@limiter.limit("10/minute")
async def create_custom_artifact_type(
    request: Request,
    type_id: str = Query(..., description="Unique ID (snake_case, 3-50 chars)"),
    name: str = Query(..., description="Display name"),
    category: str = Query(..., description="Category for grouping"),
    prompt_template: str = Query(..., description="Prompt template for generation"),
    description: str = Query("", description="Brief description"),
    default_model: Optional[str] = Query(None, description="Preferred model"),
    output_format: str = Query("document", description="Output format: document, html, mermaid"),
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Create a new custom artifact type.
    
    The prompt_template should include {meeting_notes} and {context} placeholders.
    """
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    try:
        custom_type = custom_service.create_type(
            id=type_id,
            name=name,
            category=category,
            prompt_template=prompt_template,
            description=description,
            default_model=default_model,
            output_format=output_format
        )
        
        return {
            "success": True,
            "custom_type": custom_type.to_dict(),
            "message": f"Custom artifact type '{name}' created successfully"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/artifact-types/custom/{type_id}", summary="Get a custom artifact type")
async def get_custom_artifact_type(
    type_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get details of a specific custom artifact type."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    custom_type = custom_service.get_type(type_id)
    if not custom_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom artifact type '{type_id}' not found"
        )
    
    return {
        "success": True,
        "custom_type": custom_type.to_dict()
    }


@router.put("/artifact-types/custom/{type_id}", summary="Update a custom artifact type")
async def update_custom_artifact_type(
    type_id: str,
    name: Optional[str] = Query(None, description="Display name"),
    category: Optional[str] = Query(None, description="Category for grouping"),
    prompt_template: Optional[str] = Query(None, description="Prompt template"),
    description: Optional[str] = Query(None, description="Brief description"),
    default_model: Optional[str] = Query(None, description="Preferred model"),
    is_enabled: Optional[bool] = Query(None, description="Enable/disable type"),
    current_user: UserPublic = Depends(get_current_user)
):
    """Update an existing custom artifact type."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    # Build updates dict with only provided fields
    updates = {}
    if name is not None:
        updates["name"] = name
    if category is not None:
        updates["category"] = category
    if prompt_template is not None:
        updates["prompt_template"] = prompt_template
    if description is not None:
        updates["description"] = description
    if default_model is not None:
        updates["default_model"] = default_model
    if is_enabled is not None:
        updates["is_enabled"] = is_enabled
    
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )
    
    custom_type = custom_service.update_type(type_id, **updates)
    if not custom_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom artifact type '{type_id}' not found"
        )
    
    return {
        "success": True,
        "custom_type": custom_type.to_dict(),
        "message": f"Custom artifact type '{type_id}' updated successfully"
    }


@router.delete("/artifact-types/custom/{type_id}", summary="Delete a custom artifact type")
async def delete_custom_artifact_type(
    type_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Delete a custom artifact type."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    success = custom_service.delete_type(type_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Custom artifact type '{type_id}' not found"
        )
    
    return {
        "success": True,
        "message": f"Custom artifact type '{type_id}' deleted successfully"
    }


@router.get("/artifact-types/categories", summary="List all artifact categories")
async def list_artifact_categories(
    current_user: UserPublic = Depends(get_current_user)
):
    """List all available categories (default + custom)."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    return {
        "success": True,
        "categories": custom_service.get_categories()
    }


@router.post("/artifact-types/categories", summary="Add a custom category")
async def add_artifact_category(
    category: str = Query(..., description="Category name to add"),
    current_user: UserPublic = Depends(get_current_user)
):
    """Add a new custom category."""
    from backend.services.custom_artifact_service import get_service as get_custom_service
    custom_service = get_custom_service()
    
    success = custom_service.add_category(category)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{category}' already exists"
        )
    
    return {
        "success": True,
        "message": f"Category '{category}' added successfully",
        "categories": custom_service.get_categories()
    }

