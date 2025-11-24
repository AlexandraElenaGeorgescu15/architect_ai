"""
Generation Service - Refactored from agents/universal_agent.py
Handles artifact generation with streaming support.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator
import logging
from datetime import datetime
import uuid
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.context_builder import get_builder as get_context_builder
from backend.services.enhanced_generation import get_enhanced_service
from backend.services.quality_predictor import get_quality_predictor
from backend.core.config import settings
from backend.models.dto import ArtifactType, GenerationStatus

logger = logging.getLogger(__name__)

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
        
        logger.info("Generation Service initialized")
    
    
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
        
        # Initialize job
        self.active_jobs[job_id] = {
            "job_id": job_id,
            "artifact_type": artifact_type.value,
            "status": GenerationStatus.IN_PROGRESS.value,
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "meeting_notes": meeting_notes
        }
        
        try:
            # Step 1: Build context (if not provided)
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
                context = {"context_id": context_id}
            else:
                # Build context
                context = await self.context_builder.build_context(
                    meeting_notes=meeting_notes,
                    include_rag=True,
                    include_kg=True,
                    include_patterns=True,
                    include_ml_features=False  # Skip ML features for speed
                )
            
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "context_ready",
                    "progress": 30.0,
                    "message": "Context built successfully"
                }
            
            quality_prediction = self.quality_predictor.predict(
                artifact_type=artifact_type,
                meeting_notes=meeting_notes,
                context=context if isinstance(context, dict) else None,
            )
            self.active_jobs[job_id]["quality_prediction"] = quality_prediction.to_dict()

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
                validation_score = result.get("validation_score", 0.0)
                model_used = result.get("model_used", "unknown")
            else:
                # Enhanced generation failed - log error and return failure
                error_msg = result.get("error", "Generation failed")
                logger.error(f"Enhanced generation failed: {error_msg}")
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
            is_valid = validation_score >= 80.0 if opts["use_validation"] else True
            
            # Step 4: Add to finetuning pool if score >= 85.0
            if validation_score >= 85.0:
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
                    logger.info(f"Added example to finetuning pool (score: {validation_score:.1f})")
                except Exception as e:
                    logger.warning(f"Failed to add example to finetuning pool: {e}")
            
            # Step 5: If Mermaid diagram, also generate HTML version
            if artifact_type.value.startswith("mermaid_"):
                try:
                    from backend.services.html_diagram_generator import get_generator
                    html_generator = get_generator()
                    html_content = await html_generator.generate_html_from_mermaid(
                        mermaid_content=artifact_content,
                        mermaid_artifact_type=artifact_type,
                        meeting_notes=meeting_notes,
                        rag_context=assembled_context,
                        use_ai=True
                    )
                    # Store HTML version (would be saved to outputs in production)
                    logger.info(f"Generated HTML version for {artifact_type.value}")
                except Exception as e:
                    logger.warning(f"Failed to generate HTML version: {e}")
            
            # Update job status
            self.active_jobs[job_id].update({
                "status": GenerationStatus.COMPLETED.value,
                "progress": 100.0,
                "artifact_content": artifact_content,
                "validation_score": validation_score,
                "is_valid": is_valid,
                "model_used": model_used,
                "quality_prediction": quality_prediction.to_dict(),
                "completed_at": datetime.now().isoformat()
            })
            
            # Final result
            if stream:
                yield {
                    "type": "complete",
                    "job_id": job_id,
                    "status": GenerationStatus.COMPLETED.value,
                    "progress": 100.0,
                    "artifact": {
                        "id": job_id,
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
                        "id": job_id,
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
            logger.error(f"Error generating artifact: {e}", exc_info=True)
            
            self.active_jobs[job_id].update({
                "status": GenerationStatus.FAILED.value,
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
            
            if stream:
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



