"""
Generation Service - Refactored from agents/universal_agent.py
Handles artifact generation with streaming support.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
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
    
    def _apply_targeted_mermaid_fixes(self, content: str, errors: List[str]) -> str:
        """
        Apply targeted fixes based on specific validation errors.
        
        This is called when the universal fixer hasn't fully resolved all issues.
        It analyzes the specific errors and applies additional targeted patches.
        
        Args:
            content: The Mermaid diagram content
            errors: List of validation errors from _validate_mermaid()
        
        Returns:
            Fixed content
        """
        import re
        
        for error in errors:
            error_lower = error.lower()
            
            # CRITICAL: Unbalanced curly braces
            if "unbalanced curly braces" in error_lower:
                # Count braces and try to fix
                open_count = content.count('{')
                close_count = content.count('}')
                if open_count > close_count:
                    # Missing closing braces - add them at end of each entity
                    content = re.sub(r'(\n\s*\w+\s+\{[^}]*?)(\n\s*\w+\s+\{)', r'\1}\2', content)
                    # Add final closing brace if still unbalanced
                    if content.count('{') > content.count('}'):
                        content = content.rstrip() + '\n}'
                elif close_count > open_count:
                    # Extra closing braces - remove orphaned ones
                    lines = content.split('\n')
                    fixed_lines = []
                    brace_depth = 0
                    for line in lines:
                        brace_depth += line.count('{') - line.count('}')
                        if brace_depth >= 0:
                            fixed_lines.append(line)
                        else:
                            # This line has orphan closing brace
                            line = line.replace('}', '', -brace_depth)
                            fixed_lines.append(line)
                            brace_depth = 0
                    content = '\n'.join(fixed_lines)
            
            # CRITICAL: Unbalanced square brackets
            if "unbalanced square brackets" in error_lower:
                open_count = content.count('[')
                close_count = content.count(']')
                if open_count > close_count:
                    # Find unclosed brackets and close them
                    content = re.sub(r'\[([^\]]{0,50})(\s*-->|\s*---|\s*$)', r'[\1]\2', content)
                elif close_count > open_count:
                    # Remove orphan closing brackets
                    content = re.sub(r'^\s*\]\s*$', '', content, flags=re.MULTILINE)
            
            # CRITICAL: Unbalanced parentheses
            if "unbalanced parentheses" in error_lower:
                open_count = content.count('(')
                close_count = content.count(')')
                if open_count > close_count:
                    content = re.sub(r'\(([^)]{0,50})(\s*-->|\s*---|\s*$)', r'(\1)\2', content)
                elif close_count > open_count:
                    content = re.sub(r'^\s*\)\s*$', '', content, flags=re.MULTILINE)
            
            # CRITICAL: Unbalanced quotes
            if "unbalanced quotes" in error_lower:
                # Count double quotes
                quote_count = content.count('"')
                if quote_count % 2 != 0:
                    # Find and fix unbalanced quotes in labels
                    # Pattern: [text with "partial quote] should become [text with partial quote]
                    content = re.sub(r'\[([^"\]]*)"([^"\]]*)\]', r'[\1\2]', content)
                    # Or just remove all quotes if still unbalanced
                    if content.count('"') % 2 != 0:
                        content = content.replace('"', '')
            
            # SYNTAX: Arrow pointing to nothing
            if "arrow pointing to nothing" in error_lower:
                # Remove dangling arrows at end of lines
                content = re.sub(r'-->\s*$', '', content, flags=re.MULTILINE)
                content = re.sub(r'---\s*$', '', content, flags=re.MULTILINE)
            
            # SYNTAX: Arrow with no source
            if "arrow with no source" in error_lower:
                # Remove arrows at start of lines
                content = re.sub(r'^\s*-->', '', content, flags=re.MULTILINE)
            
            # ERD: Using classDiagram syntax
            if "using classdiagram syntax" in error_lower:
                # Convert class X to X (for ERD)
                content = re.sub(r'\bclass\s+(\w+)', r'\1', content)
        
        # Final cleanup: remove empty lines at start/end
        content = content.strip()
        
        # Remove consecutive empty lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        return content
    
    async def generate_artifact(
        self,
        artifact_type: Union[ArtifactType, str],
        meeting_notes: str,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        folder_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate an artifact with optional streaming.
        
        Args:
            artifact_type: Type of artifact to generate (enum or custom type string)
            meeting_notes: User requirements
            context_id: Optional pre-built context ID
            options: Generation options (max_retries, temperature, etc.)
            stream: Whether to stream progress updates
            folder_id: Optional folder ID to associate artifact with meeting notes folder
        
        Yields:
            Progress updates and final artifact
        """
        job_id = f"gen_{uuid.uuid4().hex[:8]}"
        
        # Handle both enum and string artifact types
        if isinstance(artifact_type, ArtifactType):
            artifact_type_str = artifact_type.value
            is_custom_type = False
        else:
            artifact_type_str = str(artifact_type)
            is_custom_type = True
        
        logger.info(f"🎯 [GEN_SERVICE] Starting generation: job_id={job_id}, "
                   f"artifact_type={artifact_type_str}, is_custom={is_custom_type}, "
                   f"meeting_notes_length={len(meeting_notes)}, "
                   f"context_id={context_id}, folder_id={folder_id}, stream={stream}")
        
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
            "artifact_type": artifact_type_str,
            "status": GenerationStatus.IN_PROGRESS.value,
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "meeting_notes": meeting_notes,
            "folder_id": folder_id,  # Associate artifact with meeting notes folder
            "is_custom_type": is_custom_type  # Track if this is a custom artifact type
        }
        logger.info(f"📋 [GEN_SERVICE] Job initialized: {job_id}, folder_id={folder_id}, custom_type={is_custom_type}")
        
        try:
            # Yield initial status to ensure job_id is captured by API layer immediately
            yield {
                "type": "started",
                "job_id": job_id,
                "status": GenerationStatus.IN_PROGRESS.value,
                "created_at": self.active_jobs[job_id]["created_at"]
            }

            # Step 1: Build context (if not provided)
            logger.info(f"🔨 [GEN_SERVICE] Step 1: Building context (job_id={job_id})")
            if stream:
                yield {
                    "type": "progress",
                    "job_id": job_id,
                    "status": "analyzing_repo",
                    "progress": 10.0,
                    "message": "Analyzing repository and reading through files..."
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
                    include_ml_features=True,  # Enable ML features for deeper context
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
                    "message": "Repository analysis complete. Knowledge Graph built."
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
                    "message": "Generating code architecture and identifying integration points..." if artifact_type_str == "code_prototype" else f"Generating {artifact_type_str}..."
                }
            
            # Use Enhanced Generation Service (proper pipeline)
            # This is the PRIMARY generation path - it handles everything
            
            # Context setup
            assembled_context = context.get("assembled_context", "")
            
            # Setup async queue for streaming progress updates
            queue = asyncio.Queue()
            
            async def progress_callback(p: float, m: str):
                """Capture progress updates for streaming."""
                # Check for chunk marker
                if m.startswith("||CHUNK||"):
                    chunk_content = m[9:]  # Remove marker
                    await queue.put({
                        "type": "chunk",
                        "job_id": job_id,
                        "chunk": chunk_content
                    })
                else:
                    # Standard progress update
                    await queue.put({
                        "type": "progress",
                        "job_id": job_id,
                        "status": "generating",
                        "progress": p,
                        "message": m
                    })
            
            # Define the generation task wrapper
            async def run_generation_task():
                try:
                    gen_result = await self.enhanced_gen.generate_with_pipeline(
                        artifact_type=artifact_type,
                        meeting_notes=meeting_notes,
                        context_id=context_id,
                        options=opts,
                        progress_callback=progress_callback if stream else None
                    )
                    # Put result in queue
                    await queue.put({"type": "result", "data": gen_result})
                except Exception as e:
                    # Put error in queue
                    await queue.put({"type": "error", "error": e})
                finally:
                    # Put sentinel to signal completion
                    await queue.put(None)

            # Start generation in background
            gen_task = asyncio.create_task(run_generation_task())
            
            # Consumption loop: yield progress from queue as it arrives
            result = None
            
            while True:
                # Wait for next item from queue
                item = await queue.get()
                
                # Sentinel means we are done
                if item is None:
                    break
                
                # Check item type
                if isinstance(item, dict):
                    msg_type = item.get("type")
                    if msg_type == "progress":
                        # Yield progress update immediately
                        if stream:
                            yield item
                    elif msg_type == "chunk":
                        # Yield chunk immediately
                        if stream:
                            # Forward the chunk event directly to the client
                            # The client hook useWebSocket('generation.chunk') expects {job_id, chunk}
                            yield item
                    elif msg_type == "error":
                        # Propagate error from background task
                        raise item.get("error")
                    elif msg_type == "result":
                        # Store result for processing after loop
                        result = item.get("data")
            
            # Ensure the task is definitely done (should be if sentinel was received)
            await gen_task
            
            if result and result.get("success"):
                artifact_content = result["content"]
                validation_score = result.get("validation_score", 0.0)
                model_used = result.get("model_used", "unknown")
            else:
                # Enhanced generation failed - log error and return failure
                error_msg = result.get("error", "Generation failed") if result else "Generation failed (no result)"
                logger.error(f"❌ [GEN_SERVICE] Enhanced generation failed: job_id={job_id}, error={error_msg}")
                artifact_content = f"# {artifact_type_str}\n\nError: {error_msg}"
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
                        artifact_type=artifact_type_str,
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
            
            # INJECT VALIDATION WARNING: If artifact is invalid, add a visible warning to content
            # This ensures the user sees that it's a "best attempt" and not a perfect generation
            if not is_valid and opts["use_validation"]:
                logger.warning(f"⚠️ [GEN_SERVICE] Artifact invalid (score={validation_score:.1f}), injecting warning marker")
                warning_marker = f"<!-- VALIDATION WARNING: Score {validation_score:.1f}/100 - Issues Detected -->\n"
                
                # Prepend to content
                if artifact_content.startswith("<!--"):
                    # If already has comments, append after them but before content
                    lines = artifact_content.split('\n')
                    inserted = False
                    for i, line in enumerate(lines):
                        if not line.strip().startswith("<!--") and line.strip():
                            lines.insert(i, warning_marker)
                            inserted = True
                            break
                    if not inserted:
                        lines.insert(0, warning_marker)
                    artifact_content = '\n'.join(lines)
                else:
                    artifact_content = warning_marker + artifact_content
            
            # Step 5: Generate HTML version if needed
            html_content = None
            if artifact_type_str.startswith("mermaid_"):
                # If Mermaid diagram, also generate HTML version
                logger.info(f"🎨 [GEN_SERVICE] Step 5: Generating HTML version for Mermaid diagram "
                           f"(job_id={job_id}, type={artifact_type_str})")
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
            elif artifact_type_str.startswith("html_"):
                # If HTML diagram type, the content IS the HTML (already generated by enhanced_gen)
                # No additional processing needed - artifact_content is already HTML
                logger.info(f"✅ [GEN_SERVICE] HTML diagram generated directly: "
                           f"job_id={job_id}, type={artifact_type_str}, content_length={len(artifact_content)}")
                html_content = artifact_content  # Content is already HTML
            else:
                html_content = None
                logger.debug(f"📄 [GEN_SERVICE] Skipping HTML generation (not a diagram type, job_id={job_id})")
            
            # Create artifact object
            # FIX: Use artifact_type as the stable ID (not job_id) for consistent navigation
            # This ensures the ID matches what listArtifacts() returns from version_service
            # IMPORTANT: Define folder-specific ID here, BEFORE it's used in artifact_obj
            if folder_id:
                artifact_id_for_version = f"{folder_id}::{artifact_type_str}"  # e.g., "swap phones::mermaid_erd"
            else:
                artifact_id_for_version = artifact_type_str  # Legacy: e.g., "mermaid_erd"
            
            logger.info(f"📦 [GEN_SERVICE] Step 6: Creating artifact object (job_id={job_id}, artifact_id={artifact_id_for_version})")
            artifact_obj = {
                "id": artifact_id_for_version,  # Folder-specific ID: matches version_service and listArtifacts()
                "artifact_id": artifact_id_for_version,  # Also update artifact_id for consistency
                "job_id": job_id,  # Keep job_id separate for tracking
                "artifact_type": artifact_type_str,
                "content": artifact_content,
                "validation": {
                    "score": validation_score,
                    "is_valid": is_valid
                },
                "quality_prediction": quality_prediction.to_dict(),
                "model_used": model_used,
                "generated_at": datetime.now().isoformat(),
                "folder_id": folder_id  # Associate artifact with meeting notes folder
            }
            if html_content:
                artifact_obj["html_content"] = html_content
            logger.info(f"✅ [GEN_SERVICE] Artifact object created: job_id={job_id}, "
                       f"type={artifact_type_str}, has_html={bool(html_content)}")
            
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
            # artifact_id_for_version is already defined above with folder-specific ID
            try:
                from backend.services.version_service import get_version_service
                version_service = get_version_service()
                version_service.create_version(
                    artifact_id=artifact_id_for_version,
                    artifact_type=artifact_type_str,
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
                        "attempts": result.get("attempts", []),  # Include all attempts for tracking
                    },
                    folder_id=folder_id  # FIX: Pass as parameter for version filtering
                )
                logger.info(f"✅ [GEN_SERVICE] Saved artifact to VersionService: artifact_id={artifact_id_for_version}, job_id={job_id}, folder_id={folder_id}")
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
                        "id": artifact_id_for_version,  # Folder-specific ID for consistent navigation
                        "artifact_type": artifact_type_str,
                        "content": artifact_content,
                        "validation": {
                            "score": validation_score,
                            "is_valid": is_valid
                        },
                        "quality_prediction": quality_prediction.to_dict(),
                        "model_used": model_used,
                        "generated_at": datetime.now().isoformat(),
                        "folder_id": folder_id
                    }
                }
            else:
                # Non-streaming: return final result
                yield {
                    "job_id": job_id,
                    "status": GenerationStatus.COMPLETED.value,
                    "artifact": {
                        "id": artifact_id_for_version,  # Folder-specific ID for consistent navigation
                        "artifact_type": artifact_type_str,
                        "content": artifact_content,
                        "validation": {
                            "score": validation_score,
                            "is_valid": is_valid
                        },
                        "quality_prediction": quality_prediction.to_dict(),
                        "model_used": model_used,
                        "generated_at": datetime.now().isoformat(),
                        "folder_id": folder_id
                    }
                }
            
        except Exception as e:
            logger.error(f"❌ [GEN_SERVICE] Generation failed: job_id={job_id}, error={e}", exc_info=True)
            
            # Log exception to JSONL for persistent tracking
            log_error_to_file(
                error=e,
                context={
                    "job_id": job_id,
                    "artifact_type": artifact_type_str,
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
        logger.info(f"✏️ [GEN_SERVICE] ========== UPDATE ARTIFACT STARTED ==========")
        logger.info(f"✏️ [GEN_SERVICE] Step 1: Updating artifact")
        logger.info(f"✏️ [GEN_SERVICE] Step 1.1: artifact_id={artifact_id}, content_length={len(content)}, has_metadata={bool(metadata)}")
        
        updated_artifact = None
        
        # Find artifact in active jobs
        logger.info(f"✏️ [GEN_SERVICE] Step 2: Checking active_jobs")
        if artifact_id in self.active_jobs:
            logger.info(f"✏️ [GEN_SERVICE] Step 2.1: Found artifact in active_jobs")
            job = self.active_jobs[artifact_id]
            artifact = job.get("artifact", {})
            artifact_type = artifact.get("artifact_type") or artifact.get("type") or job.get("artifact_type", "unknown")
            
            # Update in-memory job
            job["artifact_content"] = content
            job["updated_at"] = datetime.now().isoformat()
            if artifact:
                artifact["content"] = content
                artifact["updated_at"] = datetime.now().isoformat()
            if metadata:
                if "metadata" not in job:
                    job["metadata"] = {}
                job["metadata"].update(metadata)
            
            updated_artifact = {
                "id": artifact_id,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "type": artifact_type,
                "content": content,
                "updated_at": job["updated_at"],
                "created_at": artifact.get("generated_at") or job.get("created_at", datetime.now().isoformat()),
                "folder_id": artifact.get("folder_id") or job.get("folder_id")
            }
            logger.info(f"✏️ [GEN_SERVICE] Step 2.2: Updated artifact in active_jobs")
        else:
            logger.warning(f"✏️ [GEN_SERVICE] Step 2.1: Artifact {artifact_id} not found in active_jobs")
        
        # CRITICAL FIX: Also update VersionService (persistent storage)
        logger.info(f"✏️ [GEN_SERVICE] Step 3: Updating VersionService (persistent storage)")
        try:
            from backend.services.version_service import get_version_service
            version_service = get_version_service()
            
            # Get current version to determine artifact_type and folder_id
            versions = version_service.get_versions(artifact_id)
            current_version = version_service.get_current_version(artifact_id)
            
            if current_version:
                artifact_type = current_version.get("artifact_type", "unknown")
                version_metadata = current_version.get("metadata", {})
                folder_id = version_metadata.get("folder_id")
                logger.info(f"✏️ [GEN_SERVICE] Step 3.1: Found in VersionService: artifact_type={artifact_type}, folder_id={folder_id}")
            else:
                # Try to infer from artifact_id
                artifact_type = metadata.get("artifact_type", "unknown") if metadata else "unknown"
                if artifact_type == "unknown":
                    # Try to extract from artifact_id pattern
                    if "::" in artifact_id:
                        artifact_type = artifact_id.split("::")[-1]
                    else:
                        artifact_type = artifact_id
                folder_id = metadata.get("folder_id") if metadata else None
                logger.info(f"✏️ [GEN_SERVICE] Step 3.1: Not found in VersionService, inferred: artifact_type={artifact_type}, folder_id={folder_id}")
            
            # Create new version with updated content
            logger.info(f"✏️ [GEN_SERVICE] Step 3.2: Creating new version with updated content")
            version_service.create_version(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                content=content,
                metadata={
                    "update_type": "manual_edit",
                    "updated_at": datetime.now().isoformat(),
                    **(metadata or {})
                },
                folder_id=folder_id  # FIX: Pass as parameter for version filtering
            )
            logger.info(f"✏️ [GEN_SERVICE] Step 3.3: Version created successfully in VersionService")
            
            # Build updated artifact dict if not already built
            if not updated_artifact:
                updated_artifact = {
                    "id": artifact_id,
                    "artifact_id": artifact_id,
                    "artifact_type": artifact_type,
                    "type": artifact_type,
                    "content": content,
                    "updated_at": datetime.now().isoformat(),
                    "created_at": current_version.get("created_at", datetime.now().isoformat()) if current_version else datetime.now().isoformat(),
                    "folder_id": folder_id
                }
        except Exception as e:
            logger.error(f"✏️ [GEN_SERVICE] Step 3.ERROR: Failed to update VersionService: {e}", exc_info=True)
        
        # If not found anywhere, create a new entry in active_jobs
        if not updated_artifact:
            logger.warning(f"✏️ [GEN_SERVICE] Step 4: Artifact not found anywhere, creating new entry in active_jobs")
            artifact_type = metadata.get("artifact_type", "unknown") if metadata else "unknown"
            self.active_jobs[artifact_id] = {
                "job_id": artifact_id,
                "artifact_type": artifact_type,
                "status": GenerationStatus.COMPLETED.value,
                "artifact_content": content,
                "artifact": {
                    "id": artifact_id,
                    "artifact_type": artifact_type,
                    "type": artifact_type,
                    "content": content
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            updated_artifact = {
                "id": artifact_id,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "type": artifact_type,
                "content": content,
                "updated_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
        
        logger.info(f"✏️ [GEN_SERVICE] ========== UPDATE ARTIFACT COMPLETE ==========")
        return updated_artifact


# Global service instance
_service: Optional[GenerationService] = None


def get_service() -> GenerationService:
    """Get or create global Generation Service instance."""
    global _service
    if _service is None:
        _service = GenerationService()
    return _service



