"""
Generation Service - Refactored from agents/universal_agent.py
Handles artifact generation with streaming support.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
import uuid
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.context_builder import get_builder as get_context_builder
from backend.services.enhanced_generation import get_enhanced_service
from backend.services.quality_predictor import get_quality_predictor
from backend.core.config import settings
from backend.core.logger import get_logger, log_error_to_file, capture_exceptions
from backend.models.dto import ArtifactType, GenerationStatus

logger = get_logger(__name__)

# Enhanced Generation Service is the primary generation path
# It handles: local models → retry → cloud fallback → validation → finetuning pool


class GenerationService:
    """
    Generation service for artifact creation.
    
    Features:
    - Artifact generation with multiple model support
    - Streaming generation support
    - Validation integration
    - Multi-agent feedback (optional)
    - Retry logic with fallback models
    - Progress tracking via WebSocket
    """
    
    def __init__(self):
        """Initialize Generation Service."""
        self.context_builder = get_context_builder()
        self.enhanced_gen = get_enhanced_service()  # Primary generation service (local → cloud pipeline)
        self.quality_predictor = get_quality_predictor()
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        
        # FIX: Memory leak prevention - limit max jobs and add cleanup
        self.max_jobs = 100  # Maximum jobs to keep in memory
        self.job_retention_seconds = 3600  # Keep completed jobs for 1 hour max
        
        logger.info("Generation Service initialized")
    
    def _cleanup_old_jobs(self):
        """
        Clean up old completed/failed jobs to prevent memory leak.
        Called automatically when adding new jobs.
        """
        if len(self.active_jobs) <= self.max_jobs // 2:
            return  # No cleanup needed
        
        now = datetime.now()
        jobs_to_remove = []
        
        for job_id, job in self.active_jobs.items():
            # Only cleanup completed or failed jobs
            status = job.get("status", "")
            if status not in [GenerationStatus.COMPLETED.value, GenerationStatus.FAILED.value]:
                continue
            
            # Check age
            created_at_str = job.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    age_seconds = (now - created_at).total_seconds()
                    if age_seconds > self.job_retention_seconds:
                        jobs_to_remove.append(job_id)
                except Exception:  # Explicit exception handling
                    pass
        
        # Remove old jobs (keep max_jobs // 2 most recent)
        if len(self.active_jobs) - len(jobs_to_remove) > self.max_jobs:
            # Need to remove more - sort by created_at and keep newest
            sorted_jobs = sorted(
                [(jid, j.get("created_at", "")) for jid, j in self.active_jobs.items()
                 if j.get("status") in [GenerationStatus.COMPLETED.value, GenerationStatus.FAILED.value]],
                key=lambda x: x[1]
            )
            # Remove oldest jobs beyond limit
            for jid, _ in sorted_jobs[:len(sorted_jobs) - self.max_jobs // 2]:
                if jid not in jobs_to_remove:
                    jobs_to_remove.append(jid)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
        
        if jobs_to_remove:
            logger.info(f"🧹 [GEN_SERVICE] Cleaned up {len(jobs_to_remove)} old jobs, {len(self.active_jobs)} jobs remain")
    
    
    async def generate_artifact(
        self,
        artifact_type: ArtifactType,
        meeting_notes: str,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate an artifact with optional streaming.
        
        Args:
            artifact_type: Type of artifact to generate
            meeting_notes: User requirements
            context_id: Optional pre-built context ID
            options: Generation options (max_retries, temperature, etc.)
            stream: Whether to stream progress updates
        
        Yields:
            Progress updates and final artifact
        """
        job_id = f"gen_{uuid.uuid4().hex[:8]}"
        logger.info(f"🎯 [GEN_SERVICE] Starting generation: job_id={job_id}, "
                   f"artifact_type={artifact_type.value}, "
                   f"meeting_notes_length={len(meeting_notes)}, "
                   f"context_id={context_id}, stream={stream}")
        
        # Default options
        opts = {
            "max_retries": 3,
            "use_validation": True,
            "use_multi_agent": False,
            "temperature": 0.7,
            "model_preference": None
        }
        if options:
            opts.update(options)
        logger.info(f"⚙️ [GEN_SERVICE] Generation options: {opts}")
        
        # FIX: Cleanup old jobs to prevent memory leak
        self._cleanup_old_jobs()
        
        # Initialize job
        self.active_jobs[job_id] = {
            "job_id": job_id,
            "artifact_type": artifact_type.value,
            "status": GenerationStatus.IN_PROGRESS.value,
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "meeting_notes": meeting_notes
        }
        logger.info(f"📋 [GEN_SERVICE] Job initialized: {job_id}")
        
        try:
            # Step 1: Build context (if not provided)
            logger.info(f"🔨 [GEN_SERVICE] Step 1: Building context (job_id={job_id})")
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "building_context",
                    "progress": 10.0,
                    "message": "Building context from repository..."
                }
            
            if context_id:
                # Use pre-built context (would fetch from cache/DB)
                logger.info(f"♻️ [GEN_SERVICE] Using pre-built context: {context_id}")
                context = {"context_id": context_id}
            else:
                # Build context
                logger.info(f"🏗️ [GEN_SERVICE] Building new context from repository...")
                context = await self.context_builder.build_context(
                    meeting_notes=meeting_notes,
                    include_rag=True,
                    include_kg=True,
                    include_patterns=True,
                    include_ml_features=False,  # Skip ML features for speed
                    force_refresh=True  # Always get fresh context for generation
                )
                logger.info(f"✅ [GEN_SERVICE] Context built successfully: "
                           f"has_rag={bool(context.get('rag'))}, "
                           f"has_kg={bool(context.get('knowledge_graph'))}, "
                           f"has_patterns={bool(context.get('patterns'))}")
            
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "context_ready",
                    "progress": 30.0,
                    "message": "Context built successfully"
                }
            
            logger.info(f"🔮 [GEN_SERVICE] Step 2: Predicting quality (job_id={job_id})")
            quality_prediction = self.quality_predictor.predict(
                artifact_type=artifact_type,
                meeting_notes=meeting_notes,
                context=context if isinstance(context, dict) else None,
            )
            qp_dict = quality_prediction.to_dict()
            self.active_jobs[job_id]["quality_prediction"] = qp_dict
            # Use the 'score' field from QualityPrediction; keep logging robust if structure changes
            score = getattr(quality_prediction, "score", qp_dict.get("score"))
            logger.info(
                "📊 [GEN_SERVICE] Quality prediction: %s (confidence=%.2f, score=%.2f, reasons=%s)",
                quality_prediction.label,
                quality_prediction.confidence,
                float(score) if isinstance(score, (int, float)) else 0.0,
                qp_dict.get("reasons", {}),
            )

            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "quality_forecast",
                    "progress": 35.0,
                    "message": f"Quality forecast: {quality_prediction.label.title()} confidence",
                    "quality_prediction": quality_prediction.to_dict(),
                }
            
            # Step 2: Generate artifact
            logger.info(f"🤖 [GEN_SERVICE] Step 3: Generating artifact (job_id={job_id})")
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "generating",
                    "progress": 40.0,
                    "message": f"Generating {artifact_type.value}..."
                }
            
            # Use Enhanced Generation Service (proper pipeline)
            assembled_context = context.get("assembled_context", "")
            
            # Use Enhanced Generation Service (implements proper pipeline: local → retry → cloud)
            # This is the PRIMARY generation path - it handles everything
            # Pass progress callback for streaming updates
            progress_updates = []
            
            async def progress_callback(p: float, m: str):
                """Capture progress updates for streaming."""
                progress_updates.append((p, m))
                # Note: We can't yield here since this is called from enhanced_gen
                # Instead, we'll yield progress updates after generation completes
            
            result = await self.enhanced_gen.generate_with_pipeline(
                artifact_type=artifact_type,
                meeting_notes=meeting_notes,
                context_id=context_id,
                options=opts,
                progress_callback=progress_callback if stream else None
            )
            
            # Yield progress updates if streaming
            if stream and progress_updates:
                for progress, message in progress_updates:
                    yield {
                        "type": "progress",
                        "job_id": job_id,
                        "status": "generating",
                        "progress": progress,
                        "message": message
                    }
            
            if result.get("success"):
                artifact_content = result["content"]
                
                # Clean ALL artifacts to extract only the relevant content
                if artifact_content:
                    try:
                        from backend.services.artifact_cleaner import get_cleaner
                        cleaner = get_cleaner()
                        original_length = len(artifact_content)
                        artifact_content = cleaner.clean_artifact(artifact_content, artifact_type.value)
                        if len(artifact_content) < original_length:
                            logger.info(f"🧹 [GEN_SERVICE] Cleaned {artifact_type.value}: removed {original_length - len(artifact_content)} chars of noise (job_id={job_id})")
                    except Exception as e:
                        logger.warning(f"⚠️ [GEN_SERVICE] Failed to clean artifact: {e} (job_id={job_id})")
                    
                    # For Mermaid diagrams, ALSO run the universal diagram fixer
                    # to handle syntax issues and aggressive AI text cleanup
                    if artifact_type.value.startswith("mermaid_"):
                        try:
                            from components.universal_diagram_fixer import fix_any_diagram
                            pre_fix_length = len(artifact_content)
                            artifact_content, fixes_applied = fix_any_diagram(artifact_content, max_passes=5)
                            if fixes_applied:
                                logger.info(f"🔧 [GEN_SERVICE] Mermaid fixer applied {len(fixes_applied)} fixes to {artifact_type.value} (job_id={job_id}): {fixes_applied[:3]}")
                            if len(artifact_content) < pre_fix_length:
                                logger.info(f"🔧 [GEN_SERVICE] Mermaid fixer removed {pre_fix_length - len(artifact_content)} chars from {artifact_type.value} (job_id={job_id})")
                        except Exception as e:
                            logger.warning(f"⚠️ [GEN_SERVICE] Mermaid fixer failed: {e} (job_id={job_id})")
                
                validation_score = result.get("validation_score", 0.0)
                model_used = result.get("model_used", "unknown")
                logger.info(f"✅ [GEN_SERVICE] Generation successful: job_id={job_id}, "
                           f"model={model_used}, validation_score={validation_score:.1f}, "
                           f"content_length={len(artifact_content)}")
            else:
                # Enhanced generation failed - log error and return failure
                error_msg = result.get("error", "Generation failed")
                logger.error(f"❌ [GEN_SERVICE] Enhanced generation failed: job_id={job_id}, error={error_msg}")
                artifact_content = f"# {artifact_type.value}\n\nError: {error_msg}"
                validation_score = 0.0
                model_used = "failed"
            
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "validating",
                    "progress": 80.0,
                    "message": "Validating artifact..."
                }
            
            # Step 3: Validate (if enabled) - threshold is now 80.0
            logger.info(f"🔍 [GEN_SERVICE] Step 4: Validation check (job_id={job_id}): "
                       f"score={validation_score:.1f}, threshold=80.0, use_validation={opts['use_validation']}")
            is_valid = validation_score >= 80.0 if opts["use_validation"] else True
            logger.info(f"✅ [GEN_SERVICE] Validation result: is_valid={is_valid} (job_id={job_id})")
            
            # Step 4: Add to finetuning pool if score >= 85.0
            if validation_score >= 85.0:
                logger.info(f"🎓 [GEN_SERVICE] High-quality artifact detected (score={validation_score:.1f} >= 85.0), "
                           f"adding to finetuning pool (job_id={job_id})")
                try:
                    from backend.services.finetuning_pool import get_pool
                    finetuning_pool = get_pool()
                    finetuning_pool.add_example(
                        artifact_type=artifact_type.value,
                        content=artifact_content,
                        meeting_notes=meeting_notes,
                        validation_score=validation_score,
                        model_used=model_used,
                        context={"context_id": context_id} if context_id else None
                    )
                    logger.info(f"✅ [GEN_SERVICE] Successfully added example to finetuning pool "
                               f"(score: {validation_score:.1f}, job_id={job_id})")
                except Exception as e:
                    logger.warning(f"⚠️ [GEN_SERVICE] Failed to add example to finetuning pool: {e} (job_id={job_id})")
            else:
                logger.debug(f"📊 [GEN_SERVICE] Artifact score {validation_score:.1f} < 85.0, "
                            f"skipping finetuning pool (job_id={job_id})")
            
            # Step 5: Generate HTML version if needed
            html_content = None
            if artifact_type.value.startswith("mermaid_"):
                # If Mermaid diagram, also generate HTML version
                logger.info(f"🎨 [GEN_SERVICE] Step 5: Generating HTML version for Mermaid diagram "
                           f"(job_id={job_id}, type={artifact_type.value})")
                try:
                    from backend.services.html_diagram_generator import get_generator
                    html_generator = get_generator()
                    html_content = await html_generator.generate_html_from_mermaid(
                        mermaid_content=artifact_content,
                        mermaid_artifact_type=artifact_type,
                        meeting_notes=meeting_notes,
                        rag_context=assembled_context,
                        # Disable AI-assisted layout by default to reduce latency; relies on cleaned Mermaid instead.
                        use_ai=False
                    )
                    # Store HTML version (would be saved to outputs in production)
                    logger.info(f"✅ [GEN_SERVICE] HTML version generated successfully: "
                               f"job_id={job_id}, html_length={len(html_content) if html_content else 0}")
                except Exception as e:
                    logger.warning(f"⚠️ [GEN_SERVICE] Failed to generate HTML version: {e} (job_id={job_id})")
                    html_content = None
            elif artifact_type.value.startswith("html_"):
                # If HTML diagram type, the content IS the HTML (already generated by enhanced_gen)
                # No additional processing needed - artifact_content is already HTML
                logger.info(f"✅ [GEN_SERVICE] HTML diagram generated directly: "
                           f"job_id={job_id}, type={artifact_type.value}, content_length={len(artifact_content)}")
                html_content = artifact_content  # Content is already HTML
            else:
                html_content = None
                logger.debug(f"📄 [GEN_SERVICE] Skipping HTML generation (not a diagram type, job_id={job_id})")
            
            # Create artifact object
            # FIX: Use artifact_type as the stable ID (not job_id) for consistent navigation
            # This ensures the ID matches what listArtifacts() returns from version_service
            logger.info(f"📦 [GEN_SERVICE] Step 6: Creating artifact object (job_id={job_id})")
            artifact_obj = {
                "id": artifact_type.value,  # STABLE ID: matches version_service and listArtifacts()
                "artifact_id": artifact_type.value,  # Also update artifact_id for consistency
                "job_id": job_id,  # Keep job_id separate for tracking
                "artifact_type": artifact_type.value,
                "content": artifact_content,
                "validation": {
                    "score": validation_score,
                    "is_valid": is_valid
                },
                "quality_prediction": quality_prediction.to_dict(),
                "model_used": model_used,
                "generated_at": datetime.now().isoformat()
            }
            if html_content:
                artifact_obj["html_content"] = html_content
            logger.info(f"✅ [GEN_SERVICE] Artifact object created: job_id={job_id}, "
                       f"type={artifact_type.value}, has_html={bool(html_content)}")
            
            # Update job status with full artifact
            logger.info(f"💾 [GEN_SERVICE] Updating job status: job_id={job_id}, status=COMPLETED")
            self.active_jobs[job_id].update({
                "status": GenerationStatus.COMPLETED.value,
                "progress": 100.0,
                "artifact": artifact_obj,  # Full artifact object
                "artifact_content": artifact_content,  # Keep for backward compatibility
                "validation_score": validation_score,
                "is_valid": is_valid,
                "model_used": model_used,
                "quality_prediction": quality_prediction.to_dict(),
                "completed_at": datetime.now().isoformat()
            })
            logger.info(f"✅ [GEN_SERVICE] Job status updated successfully: job_id={job_id}")
            
            # Save to VersionService for persistent storage
            # Use artifact_type as the STABLE identifier for versioning
            # This ensures all artifacts of the same type share a version history (v1, v2, v3, etc.)
            # Instead of each generation being a separate artifact with v1 only
            artifact_id_for_version = artifact_type.value  # STABLE ID: e.g., "mermaid_erd"
            try:
                from backend.services.version_service import get_version_service
                version_service = get_version_service()
                version_service.create_version(
                    artifact_id=artifact_id_for_version,
                    artifact_type=artifact_type.value,
                    content=artifact_content,  # Already cleaned if Mermaid
                    metadata={
                        "model_used": model_used,
                        "provider": "ollama" if "ollama" in model_used.lower() else "cloud",
                        "validation_score": validation_score,
                        "is_valid": is_valid,
                        "meeting_notes": meeting_notes[:200] if meeting_notes else "",
                        "html_content": html_content,  # Include HTML version if generated
                        "quality_prediction": quality_prediction.to_dict(),
                        "job_id": job_id,  # Keep reference to job_id for tracking
                        "attempts": result.get("attempts", [])  # Include all attempts for tracking
                    }
                )
                logger.info(f"✅ [GEN_SERVICE] Saved artifact to VersionService: artifact_id={artifact_id_for_version}, job_id={job_id}")
            except Exception as e:
                logger.warning(f"⚠️ [GEN_SERVICE] Failed to save artifact to VersionService: {e} (artifact_id={artifact_id_for_version}, job_id={job_id})")
            
            # Final result
            if stream:
                yield {
                    "type": "complete",
                    "job_id": job_id,
                    "status": GenerationStatus.COMPLETED.value,
                    "progress": 100.0,
                    "artifact": {
                        "id": artifact_type.value,  # STABLE ID for consistent navigation
                        "artifact_type": artifact_type.value,
                        "content": artifact_content,
                        "validation": {
                            "score": validation_score,
                            "is_valid": is_valid
                        },
                        "quality_prediction": quality_prediction.to_dict(),
                        "model_used": model_used,
                        "generated_at": datetime.now().isoformat()
                    }
                }
            else:
                # Non-streaming: return final result
                yield {
                    "job_id": job_id,
                    "status": GenerationStatus.COMPLETED.value,
                    "artifact": {
                        "id": artifact_type.value,  # STABLE ID for consistent navigation
                        "artifact_type": artifact_type.value,
                        "content": artifact_content,
                        "validation": {
                            "score": validation_score,
                            "is_valid": is_valid
                        },
                        "quality_prediction": quality_prediction.to_dict(),
                        "model_used": model_used,
                        "generated_at": datetime.now().isoformat()
                    }
                }
            
        except Exception as e:
            logger.error(f"❌ [GEN_SERVICE] Generation failed: job_id={job_id}, error={e}", exc_info=True)
            
            # Log exception to JSONL for persistent tracking
            log_error_to_file(
                error=e,
                context={
                    "job_id": job_id,
                    "artifact_type": artifact_type.value,
                    "meeting_notes_preview": meeting_notes[:200] if meeting_notes else "",
                    "context_id": context_id
                },
                module="generation_service",
                function="generate_artifact"
            )
            
            self.active_jobs[job_id].update({
                "status": GenerationStatus.FAILED.value,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
            logger.info(f"💾 [GEN_SERVICE] Job status updated to FAILED: job_id={job_id}")
            
            if stream:
                logger.info(f"📤 [GEN_SERVICE] Yielding error event: job_id={job_id}")
                yield {
                    "type": "error",
                    "job_id": job_id,
                    "status": GenerationStatus.FAILED.value,
                    "error": str(e)
                }
            else:
                yield {
                    "job_id": job_id,
                    "status": GenerationStatus.FAILED.value,
                    "error": str(e)
                }
    
    async def generate_artifact_sync(
        self,
        artifact_type: ArtifactType,
        meeting_notes: str,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate artifact synchronously (non-streaming).
        
        Args:
            artifact_type: Type of artifact to generate
            meeting_notes: User requirements
            context_id: Optional pre-built context ID
            options: Generation options
        
        Returns:
            Final generation result
        """
        result = None
        async for update in self.generate_artifact(
            artifact_type=artifact_type,
            meeting_notes=meeting_notes,
            context_id=context_id,
            options=options,
            stream=False
        ):
            result = update
        
        return result or {"error": "Generation failed"}
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a generation job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Job status dictionary or None if not found
        """
        return self.active_jobs.get(job_id)
    
    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent generation jobs.
        
        Args:
            limit: Maximum number of jobs to return
        
        Returns:
            List of job dictionaries
        """
        jobs = list(self.active_jobs.values())
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return jobs[:limit]
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a generation job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if job was cancelled, False if not found
        """
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job["status"] == GenerationStatus.IN_PROGRESS.value:
                job["status"] = GenerationStatus.CANCELLED.value
                job["completed_at"] = datetime.now().isoformat()
                return True
        return False
    
    def update_artifact(self, artifact_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Update an artifact's content.
        
        Args:
            artifact_id: Artifact identifier
            content: New content
            metadata: Optional metadata updates
        
        Returns:
            Updated artifact dictionary or None if not found
        """
        # Find artifact in active jobs
        if artifact_id in self.active_jobs:
            job = self.active_jobs[artifact_id]
            job["artifact_content"] = content
            job["updated_at"] = datetime.now().isoformat()
            if metadata:
                if "metadata" not in job:
                    job["metadata"] = {}
                job["metadata"].update(metadata)
            return job
        
        # If not found in active jobs, create a new entry
        logger.warning(f"Artifact {artifact_id} not found in active jobs, creating new entry")
        self.active_jobs[artifact_id] = {
            "job_id": artifact_id,
            "artifact_type": metadata.get("artifact_type", "unknown") if metadata else "unknown",
            "status": GenerationStatus.COMPLETED.value,
            "artifact_content": content,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        return self.active_jobs[artifact_id]


# Global service instance
_service: Optional[GenerationService] = None


def get_service() -> GenerationService:
    """Get or create global Generation Service instance."""
    global _service
    if _service is None:
        _service = GenerationService()
    return _service



