"""
Enhanced Generation Service - Implements proper pipeline:
local model → retry with next model → cloud fallback → return best attempt

This service properly uses model routing and implements the user's requirements.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import asyncio

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.model_service import get_service as get_model_service
from backend.services.context_builder import get_builder as get_context_builder
from backend.services.validation_service import get_service as get_validation_service
from backend.core.config import settings
from backend.core.metrics import get_metrics_collector, timed
from backend.core.logger import get_logger
from backend.core.cache import cached
from backend.models.dto import ArtifactType

logger = get_logger(__name__)
metrics = get_metrics_collector()

# Optional imports
try:
    from ai.ollama_client import OllamaClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("OllamaClient not available. Local model generation disabled.")

try:
    from agents.universal_agent import UniversalArchitectAgent
    UNIVERSAL_AGENT_AVAILABLE = True
except ImportError:
    UNIVERSAL_AGENT_AVAILABLE = False


class EnhancedGenerationService:
    """
    Enhanced generation service with proper pipeline:
    1. Try local models (from routing) in order
    2. Validate each attempt (threshold: 80)
    3. If validation fails, try next local model
    4. If all local models fail, try cloud models
    5. Return best attempt (even if below threshold)
    """
    
    def __init__(self):
        """Initialize Enhanced Generation Service."""
        self.model_service = get_model_service()
        self.context_builder = get_context_builder()
        self.validation_service = get_validation_service()
        self.ollama_client = OllamaClient() if OLLAMA_AVAILABLE else None
        
        logger.info("Enhanced Generation Service initialized")
    
    async def generate_with_pipeline(
        self,
        artifact_type: ArtifactType,
        meeting_notes: str,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate artifact using proper pipeline.
        
        Args:
            artifact_type: Type of artifact to generate
            meeting_notes: User requirements
            context_id: Optional pre-built context
            options: Generation options
            progress_callback: Optional callback for progress updates (progress: float, message: str)
        
        Returns:
            Dictionary with generation result
        """
        opts = {
            "temperature": 0.2,
            "max_retries": 2,  # Max retries per model
            "use_validation": True,
            "validation_threshold": 80.0
        }
        if options:
            opts.update(options)
        
        logger.info(f"🚀 [ENHANCED_GEN] Starting generation pipeline: artifact_type={artifact_type.value}, "
                   f"meeting_notes_length={len(meeting_notes)}, context_id={context_id}")
        
        # Record metrics
        metrics.increment("generation_requests_total", tags={"artifact_type": artifact_type.value})
        
        # Progress: Building context (10%)
        if progress_callback:
            await progress_callback(10.0, "Building context from repository...")
        
        # Build context if not provided (with artifact-specific RAG targeting)
        logger.info(f"🏗️ [ENHANCED_GEN] Building context (artifact_type={artifact_type.value})")
        with metrics.timer("context_building", tags={"artifact_type": artifact_type.value}):
            if context_id:
                logger.info(f"♻️ [ENHANCED_GEN] Attempting to use pre-built context: {context_id}")
                # Try to get context by ID
                context = await self.context_builder.get_context_by_id(context_id)
                if not context:
                    logger.warning(f"⚠️ [ENHANCED_GEN] Context {context_id} not found, building new context")
                    if progress_callback:
                        await progress_callback(15.0, "Context not found, building new context...")
                    context = await self.context_builder.build_context(
                        meeting_notes=meeting_notes,
                        include_rag=True,
                        include_kg=True,
                        include_patterns=True,
                        artifact_type=artifact_type.value,  # Pass artifact type for targeted RAG
                        force_refresh=True  # Always get fresh context for generation
                    )
                    logger.info(f"✅ [ENHANCED_GEN] New context built successfully")
                else:
                    logger.info(f"✅ [ENHANCED_GEN] Using cached context: {context_id}")
            else:
                logger.info(f"🏗️ [ENHANCED_GEN] Building new context from repository")
                context = await self.context_builder.build_context(
                    meeting_notes=meeting_notes,
                    include_rag=True,
                    include_kg=True,
                    include_patterns=True,
                    artifact_type=artifact_type.value,  # Pass artifact type for targeted RAG
                    force_refresh=True  # Always get fresh context for generation
                )
                logger.info(f"✅ [ENHANCED_GEN] Context built successfully")
        
        # Progress: Context ready (30%)
        if progress_callback:
            await progress_callback(30.0, "Context built successfully")
        
        assembled_context = context.get("assembled_context", "")
        logger.info(f"📊 [ENHANCED_GEN] Context assembled: length={len(assembled_context)}, "
                   f"has_rag={bool(context.get('rag'))}, has_kg={bool(context.get('knowledge_graph'))}")
        
        # Get models for this artifact type
        # This now properly prioritizes fine-tuned models first
        logger.info(f"🔍 [ENHANCED_GEN] Getting models for artifact type: {artifact_type.value}")
        local_models = self.model_service.get_models_for_artifact(artifact_type)
        logger.info(f"📋 [ENHANCED_GEN] Found {len(local_models)} local model(s) for {artifact_type.value}")
        
        # Log which models will be tried (first 3)
        if local_models:
            model_preview = ", ".join(local_models[:3])
            if len(local_models) > 3:
                model_preview += f" (+{len(local_models) - 3} more)"
            logger.info(f"🎯 [ENHANCED_GEN] Model priority order: {model_preview}")
        
        if not local_models:
            error_msg = "No local models available. Please ensure Ollama is running and models are installed."
            logger.error(f"❌ [ENHANCED_GEN] {error_msg}")
            if progress_callback:
                await progress_callback(100.0, f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "no_models_available",
                "suggestion": "Install Ollama models or configure cloud API keys"
            }
        
        attempts = []
        best_attempt = None
        best_score = 0.0
        
        # Progress: Starting generation (40%)
        if progress_callback:
            await progress_callback(40.0, f"Starting generation with {len(local_models)} local model(s)...")
        
        # Step 1: Try local models (with retry logic per model)
        logger.info(f"🔄 [ENHANCED_GEN] Starting local model attempts: {len(local_models)} model(s)")
        for model_idx, model_id in enumerate(local_models):
            if not self.ollama_client:
                logger.warning(f"⚠️ [ENHANCED_GEN] Ollama client not available, skipping local models")
                break
            
            # Check if this is a local model (Ollama) or cloud model
            if ":" in model_id:
                provider, model_name = model_id.split(":", 1)
                if provider != "ollama":
                    logger.debug(f"⏭️ [ENHANCED_GEN] Skipping cloud model in local phase: {model_id}")
                    # Skip cloud models in local phase
                    continue
            else:
                # Assume Ollama model if no provider prefix
                model_name = model_id
            
            logger.info(f"🤖 [ENHANCED_GEN] Attempting local model [{model_idx + 1}/{len(local_models)}]: {model_name} for {artifact_type.value}")
            
            # Progress: Trying model
            if progress_callback:
                progress = 40.0 + (model_idx / len(local_models)) * 30.0
                await progress_callback(progress, f"Trying model: {model_name}...")
            
            # Try this model with retries (max 2 retries = 3 total attempts)
            for retry in range(opts["max_retries"] + 1):
                if progress_callback and retry > 0:
                    await progress_callback(
                        40.0 + (model_idx / len(local_models)) * 30.0,
                        f"Retrying {model_name} (attempt {retry + 1}/{opts['max_retries'] + 1})..."
                    )
                try:
                    logger.info(f"🔄 [ENHANCED_GEN] Model attempt {retry + 1}/{opts['max_retries'] + 1}: {model_name}")
                    # Load model (with VRAM management)
                    await self.ollama_client.ensure_model_available(model_name)
                    logger.debug(f"✅ [ENHANCED_GEN] Model {model_name} is available")
                    
                    # Build prompt with context
                    prompt = self._build_prompt(meeting_notes, assembled_context, artifact_type)
                    logger.debug(f"📝 [ENHANCED_GEN] Prompt built: length={len(prompt)}")
                    
                    # Generate
                    logger.info(f"⚡ [ENHANCED_GEN] Generating with {model_name}...")
                    response = await self.ollama_client.generate(
                        model_name=model_name,
                        prompt=prompt,
                        system_message=self._get_system_message(artifact_type),
                        temperature=opts["temperature"]
                    )
                    
                    if not response.success or not response.content:
                        logger.warning(f"⚠️ [ENHANCED_GEN] Generation failed with {model_name} (attempt {retry + 1}): {response.error_message}")
                        if retry < opts["max_retries"]:
                            logger.info(f"🔄 [ENHANCED_GEN] Retrying {model_name}...")
                            continue  # Retry same model
                        else:
                            logger.warning(f"❌ [ENHANCED_GEN] All retries exhausted for {model_name}, moving to next model")
                            break  # Move to next model
                    
                    logger.info(f"✅ [ENHANCED_GEN] Generation successful with {model_name}: content_length={len(response.content)}")
                    
                    # Progress: Validating (75%)
                    if progress_callback:
                        await progress_callback(75.0, f"Validating output from {model_name}...")
                    
                    # Validate
                    logger.info(f"🔍 [ENHANCED_GEN] Validating output from {model_name}...")
                    validation_result = await self.validation_service.validate_artifact(
                        artifact_type=artifact_type,
                        content=response.content,
                        meeting_notes=meeting_notes,
                        context=context
                    )
                    
                    score = validation_result.score
                    # Use raw content as default; may be refined later after a successful validation pass
                    cleaned_content = response.content
                    # Additional render-viability checks for diagrams/HTML
                    render_viable = True
                    is_runnable = True
                    if artifact_type.value.startswith("mermaid_"):
                        candidate = cleaned_content
                        mermaid_markers = [
                            "graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram",
                            "erDiagram", "gantt", "journey", "pie", "gitGraph", "mindmap", "timeline"
                        ]
                        if not any(marker in candidate for marker in mermaid_markers):
                            render_viable = False
                        
                        # Check if diagram is actually runnable (can be rendered)
                        try:
                            from backend.services.validation_service import ValidationService
                            validator = ValidationService()
                            cleaned = validator._extract_mermaid_diagram(candidate)
                            # Check for basic runnability: has diagram type, balanced brackets
                            mermaid_errors = validator._validate_mermaid(cleaned)
                            if mermaid_errors:
                                is_runnable = False
                                logger.warning(f"⚠️ [ENHANCED_GEN] Diagram not runnable: {mermaid_errors}")
                                # Penalize score if not runnable
                                score = max(0.0, score - 30.0)
                        except Exception as e:
                            logger.warning(f"⚠️ [ENHANCED_GEN] Could not check runnability: {e}")
                    
                    if artifact_type.value.startswith("html_"):
                        candidate = cleaned_content
                        if "<" not in candidate or ">" not in candidate:
                            render_viable = False
                    
                    is_valid = validation_result.is_valid and score >= opts["validation_threshold"] and render_viable and is_runnable
                    logger.info(f"📊 [ENHANCED_GEN] Validation result for {model_name}: score={score:.1f}, "
                               f"is_valid={is_valid}, threshold={opts['validation_threshold']}, "
                               f"is_runnable={is_runnable}, errors={len(validation_result.errors)}")
                    
                    attempt = {
                        "model": model_name,
                        "provider": "ollama",
                        "content": response.content,
                        "score": score,
                        "is_valid": is_valid,
                        "errors": validation_result.errors,
                        "retry": retry
                    }
                    attempts.append(attempt)
                    logger.debug(f"📝 [ENHANCED_GEN] Attempt recorded: model={model_name}, score={score:.1f}, "
                               f"total_attempts={len(attempts)}")
                    
                    # Track best attempt
                    if score > best_score:
                        logger.info(f"🏆 [ENHANCED_GEN] New best attempt: {model_name} (score: {score:.1f}, "
                                   f"previous best: {best_score:.1f})")
                        best_score = score
                        best_attempt = attempt
                    
                    # If valid (score >= 80), return immediately
                    if is_valid:
                        logger.info(f"✅ [ENHANCED_GEN] Success with {model_name} (score: {score:.1f}), "
                                   f"returning result immediately")
                        
                        # Clean content for Mermaid diagrams (extract only diagram code)
                        cleaned_content = response.content
                        if artifact_type.value.startswith("mermaid_"):
                            try:
                                from backend.services.validation_service import ValidationService
                                validator = ValidationService()
                                cleaned_content = validator._extract_mermaid_diagram(response.content)
                                if cleaned_content != response.content:
                                    logger.info(f"🧹 [ENHANCED_GEN] Cleaned Mermaid diagram: removed {len(response.content) - len(cleaned_content)} chars of extra text")
                                
                                # Fix ERD syntax if it's using class diagram syntax
                                if artifact_type.value == "mermaid_erd" and ("class " in cleaned_content or "CLASS " in cleaned_content):
                                    cleaned_content = validator._fix_erd_syntax(cleaned_content)
                                    logger.info("🔧 [ENHANCED_GEN] Fixed ERD syntax (converted class diagram syntax to ERD)")
                            except Exception as e:
                                logger.warning(f"Failed to clean Mermaid diagram: {e}")
                        
                        # Progress: Success (90%)
                        if progress_callback:
                            await progress_callback(90.0, f"Generation successful! (Score: {score:.1f})")
                        
                        # Unload non-persistent models to free VRAM (keep persistent models loaded)
                        try:
                            if model_name not in self.ollama_client.persistent_models:
                                await self.ollama_client.unload_model(model_name, show_progress=False)
                                logger.debug(f"Unloaded {model_name} to free VRAM")
                        except Exception as e:
                            logger.debug(f"Could not unload {model_name}: {e}")
                        
                        # Add to finetuning pool if score >= 85.0
                        if score >= 85.0:
                            try:
                                from backend.services.finetuning_pool import get_pool
                                finetuning_pool = get_pool()
                                finetuning_pool.add_example(
                                    artifact_type=artifact_type.value,
                                    content=cleaned_content,  # Use cleaned content
                                    meeting_notes=meeting_notes,
                                    validation_score=score,
                                    model_used=model_name,
                                    context=context
                                )
                                logger.info(f"Added example to finetuning pool (score: {score:.1f})")
                            except Exception as e:
                                logger.warning(f"Failed to add example to finetuning pool: {e}")
                        
                        # If Mermaid diagram, also generate HTML version automatically
                        html_content = None
                        if artifact_type.value.startswith("mermaid_"):
                            try:
                                from backend.services.html_diagram_generator import get_generator
                                html_generator = get_generator()
                                html_content = await html_generator.generate_html_from_mermaid(
                                    mermaid_content=cleaned_content,  # Use cleaned content
                                    mermaid_artifact_type=artifact_type,
                                    meeting_notes=meeting_notes,
                                    rag_context=assembled_context,
                                    # Avoid AI-assisted layout unless explicitly requested to cut latency
                                    use_ai=False
                                )
                                logger.info(f"✅ Auto-generated HTML version for {artifact_type.value}")
                            except Exception as e:
                                logger.warning(f"Failed to auto-generate HTML version: {e}")
                        
                        # Create version for this artifact
                        # Use stable artifact_id (the artifact type itself) to ensure versioning works correctly
                        # instead of creating a new artifact for every generation.
                        artifact_id = artifact_type.value
                        
                        # NOTE: GenerationService handles saving to VersionService using this artifact_id.
                        # We avoid double-saving here.
                        # try:
                        #     from backend.services.version_service import get_version_service
                        #     version_service = get_version_service()
                        #     version_service.create_version(
                        #         artifact_id=artifact_id,
                        #         artifact_type=artifact_type.value,
                        #         content=cleaned_content,  # Use cleaned content
                        #         metadata={
                        #             "model_used": model_name,
                        #             "provider": "ollama",
                        #             "validation_score": score,
                        #             "is_valid": True,
                        #             "meeting_notes": meeting_notes[:200],  # First 200 chars
                        #             "html_content": html_content,  # Include HTML version if generated
                        #             "attempts": attempts  # Include all attempts for tracking
                        #         }
                        #     )
                        #     logger.info(f"Created version for artifact {artifact_id}")
                        # except Exception as e:
                        #     logger.warning(f"Failed to create version: {e}")
                        
                        # Update model routing if this model performed well (score >= 80)
                        # This promotes successful models to primary position
                        # IMPORTANT: Do this BEFORE returning, so routing is updated for future generations
                        if score >= 80.0:
                            try:
                                from backend.services.model_service import get_service as get_model_service
                                from backend.models.dto import ModelRoutingDTO
                                model_service = get_model_service()
                                
                                # Get current routing
                                routing = model_service.get_routing_for_artifact(artifact_type)
                                
                                # Normalize model name - handle both "llama3" and "ollama:llama3" formats
                                if ":" in model_name:
                                    # Already has provider prefix, use as-is
                                    model_id = model_name
                                else:
                                    # Add ollama prefix
                                    model_id = f"ollama:{model_name}"
                                
                                # Also check for common variations (llama3:latest, llama3:8b, etc.)
                                model_variations = [model_id]
                                if model_name.startswith("llama3"):
                                    model_variations.extend([
                                        f"ollama:llama3",
                                        f"ollama:llama3:latest",
                                        f"ollama:{model_name}:latest"
                                    ])
                                
                                if routing:
                                    # Check if current primary matches any variation of this model
                                    current_primary = routing.primary_model
                                    model_already_primary = any(
                                        current_primary == var or 
                                        current_primary.endswith(f":{model_name}") or
                                        current_primary == model_name
                                        for var in model_variations
                                    )
                                    
                                    # If current primary is different and this model scored well, promote it
                                    # Lower threshold to 80 for promotion (was 85)
                                    if not model_already_primary and score >= 80.0:
                                        # Move current primary to fallback if not already there
                                        if current_primary not in routing.fallback_models:
                                            routing.fallback_models.insert(0, current_primary)
                                        # Set successful model as primary (use the normalized model_id)
                                        routing.primary_model = model_id
                                        model_service.update_routing([routing])
                                        logger.info(f"✅ [ENHANCED_GEN] Promoted {model_name} ({model_id}) to primary for {artifact_type.value} (score: {score:.1f}, previous: {current_primary})")
                                    elif model_already_primary:
                                        logger.debug(f"✅ [ENHANCED_GEN] Model {model_name} already primary for {artifact_type.value}, no update needed")
                                    else:
                                        logger.debug(f"⚠️ [ENHANCED_GEN] Model {model_name} scored {score:.1f} but not promoting (already primary or score < 80)")
                                else:
                                    # Create new routing with this successful model
                                    routing = ModelRoutingDTO(
                                        artifact_type=artifact_type,
                                        primary_model=model_id,
                                        fallback_models=["ollama:llama3", "gemini:gemini-2.0-flash-exp"],
                                        enabled=True
                                    )
                                    model_service.update_routing([routing])
                                    logger.info(f"✅ [ENHANCED_GEN] Created routing for {artifact_type.value} with {model_name} ({model_id}) as primary (score: {score:.1f})")
                            except Exception as e:
                                logger.warning(f"⚠️ [ENHANCED_GEN] Failed to update routing: {e}", exc_info=True)
                        
                        return {
                            "success": True,
                            "content": cleaned_content,  # Use cleaned content
                            "model_used": model_name,
                            "provider": "ollama",
                            "validation_score": score,
                            "is_valid": True,
                            "attempts": attempts,
                            "artifact_id": artifact_id
                        }
                    
                    # If validation failed but we have retries left, retry same model
                    if retry < opts["max_retries"]:
                        logger.info(f"Validation failed (score: {score:.1f} < {opts['validation_threshold']:.1f}), retrying with {model_name}...")
                        continue
                    else:
                        # All retries exhausted for this model, try next model
                        logger.info(f"All retries exhausted for {model_name} (best score: {score:.1f}), trying next model...")
                        break
                        
                except Exception as e:
                    logger.error(f"Error with {model_name} (attempt {retry + 1}): {e}")
                    if retry < opts["max_retries"]:
                        continue  # Retry
                    else:
                        break  # Move to next model
        
        # Step 2: If all local models failed, try cloud models
        if not best_attempt or best_score < opts["validation_threshold"]:
            logger.info("All local models failed, trying cloud fallback...")
            
            # Progress: Cloud fallback (50%)
            if progress_callback:
                await progress_callback(50.0, "Local models didn't meet threshold, trying cloud models...")
            
            cloud_result = await self._try_cloud_models(
                artifact_type=artifact_type,
                meeting_notes=meeting_notes,
                assembled_context=assembled_context,
                context=context,
                threshold=opts["validation_threshold"],
                progress_callback=progress_callback
            )
            
            if cloud_result:
                attempts.append(cloud_result["attempt"])
                if cloud_result["score"] > best_score:
                    best_score = cloud_result["score"]
                    best_attempt = cloud_result["attempt"]
                    
                    if cloud_result["is_valid"]:
                        # Add to finetuning pool if score >= 85.0
                        if cloud_result["score"] >= 85.0:
                            try:
                                from backend.services.finetuning_pool import get_pool
                                finetuning_pool = get_pool()
                                finetuning_pool.add_example(
                                    artifact_type=artifact_type.value,
                                    content=cloud_result["content"],
                                    meeting_notes=meeting_notes,
                                    validation_score=cloud_result["score"],
                                    model_used=cloud_result["model_used"],
                                    context=context
                                )
                                logger.info(f"Added cloud example to finetuning pool (score: {cloud_result['score']:.1f})")
                            except Exception as e:
                                logger.warning(f"Failed to add cloud example to finetuning pool: {e}")
                        
                        # If Mermaid diagram, also generate HTML version automatically
                        html_content = None
                        if artifact_type.value.startswith("mermaid_"):
                            try:
                                from backend.services.html_diagram_generator import get_generator
                                html_generator = get_generator()
                                html_content = await html_generator.generate_html_from_mermaid(
                                    mermaid_content=cloud_result["content"],
                                    mermaid_artifact_type=artifact_type,
                                    meeting_notes=meeting_notes,
                                    rag_context=assembled_context,
                                    # Keep AI layout off by default for stability/latency
                                    use_ai=False
                                )
                                logger.info(f"✅ Auto-generated HTML version for {artifact_type.value} (cloud)")
                            except Exception as e:
                                logger.warning(f"Failed to auto-generate HTML version: {e}")
                        
                        # Use stable artifact_id (artifact type) for proper versioning
                        # NOTE: Version creation is handled by GenerationService to avoid duplicates
                        artifact_id = artifact_type.value
                        
                        return {
                            "success": True,
                            "content": cloud_result["content"],
                            "html_content": html_content,  # Include HTML version if generated
                            "model_used": cloud_result["model_used"],
                            "provider": cloud_result["provider"],
                            "validation_score": cloud_result["score"],
                            "is_valid": True,
                            "attempts": attempts,
                            "artifact_id": artifact_id
                        }
        
        # Step 3: Return best attempt (even if below threshold)
        if best_attempt:
            logger.warning(f"Best attempt score {best_score:.1f} below threshold {opts['validation_threshold']:.1f}, returning anyway")
            if progress_callback:
                await progress_callback(95.0, f"Best attempt found (score: {best_score:.1f}), finalizing...")
            
            # Use stable artifact_id (artifact type) for proper versioning
            # NOTE: Version creation is handled by GenerationService to avoid duplicates
            artifact_id = artifact_type.value
            
            return {
                "success": True,
                "content": best_attempt["content"],
                "model_used": best_attempt["model"],
                "provider": best_attempt["provider"],
                "validation_score": best_score,
                "is_valid": best_score >= opts["validation_threshold"],
                "attempts": attempts,
                "warning": f"Best score {best_score:.1f} below threshold {opts['validation_threshold']:.1f}",
                "error_type": "low_quality" if best_score < opts["validation_threshold"] else None,
                "artifact_id": artifact_id
            }
        else:
            error_msg = "All generation attempts failed. Please check model availability and API keys."
            logger.error(error_msg)
            
            # Record metrics for failure
            metrics.increment("generation_failures_total", tags={"artifact_type": artifact_type.value})
            
            if progress_callback:
                await progress_callback(100.0, f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "all_attempts_failed",
                "attempts": attempts,
                "suggestion": "Ensure Ollama is running, models are installed, or cloud API keys are configured"
            }
    
    def _build_prompt(self, meeting_notes: str, rag_context: str, artifact_type: ArtifactType) -> str:
        """Build comprehensive prompt with all context."""
        parts = []
        
        # Add artifact-specific instructions
        artifact_name = artifact_type.value.replace("_", " ").title()
        parts.append(f"Generate a {artifact_name} based on the following requirements and project context.")
        parts.append("\n## Requirements")
        parts.append(meeting_notes)
        
        if rag_context:
            parts.append("\n## Project Context (from codebase)")
            # Limit RAG context to avoid token limits, but preserve important parts
            rag_limit = 3000
            if len(rag_context) > rag_limit:
                # Try to keep the beginning (usually most relevant) and end
                parts.append(rag_context[:rag_limit] + "\n[... truncated for length ...]")
            else:
                parts.append(rag_context)
        
        parts.append("\n## Instructions")
        parts.append("1. Ensure the output is complete and production-ready")
        parts.append("2. Follow best practices and conventions")
        parts.append("3. Include all necessary details")
        parts.append("4. Validate syntax and correctness")
        
        return "\n".join(parts)
    
    def _get_system_message(self, artifact_type: ArtifactType) -> str:
        """Get comprehensive system message for artifact type."""
        base_message = "You are an expert architect and developer assistant. Your goal is to generate high-quality, accurate, and relevant architectural artifacts."
        
        messages = {
            # Mermaid Diagrams
            ArtifactType.MERMAID_ERD: f"{base_message} Generate a clean, correct Entity-Relationship Diagram in Mermaid syntax. Include all entities, relationships, and cardinalities. Ensure syntax is valid and the diagram clearly represents the data model.",
            ArtifactType.MERMAID_ARCHITECTURE: f"{base_message} Generate a comprehensive System Architecture Diagram in Mermaid syntax. Show components, their relationships, data flow, and system boundaries. Use proper Mermaid syntax for architecture diagrams.",
            ArtifactType.MERMAID_SEQUENCE: f"{base_message} Generate a detailed Sequence Diagram in Mermaid syntax. Show all actors, objects, and message flows with proper lifelines and activation boxes.",
            ArtifactType.MERMAID_CLASS: f"{base_message} Generate a Class Diagram in Mermaid syntax. Include classes, attributes, methods, and relationships (inheritance, composition, association).",
            ArtifactType.MERMAID_STATE: f"{base_message} Generate a State Diagram in Mermaid syntax. Show all states, transitions, and state entry/exit actions.",
            ArtifactType.MERMAID_FLOWCHART: f"{base_message} Generate a Flowchart in Mermaid syntax. Use proper shapes for decisions, processes, and start/end points.",
            ArtifactType.MERMAID_DATA_FLOW: f"{base_message} Generate a Data Flow Diagram in Mermaid syntax. Show processes, data stores, external entities, and data flows.",
            ArtifactType.MERMAID_USER_FLOW: f"{base_message} Generate a User Flow Diagram in Mermaid syntax. Show user actions, decision points, and flow paths.",
            ArtifactType.MERMAID_COMPONENT: f"{base_message} Generate a Component Diagram in Mermaid syntax. Show components, interfaces, and dependencies.",
            ArtifactType.MERMAID_GANTT: f"{base_message} Generate a Gantt Chart in Mermaid syntax. Include tasks, durations, and dependencies.",
            ArtifactType.MERMAID_PIE: f"{base_message} Generate a Pie Chart in Mermaid syntax with proper data visualization.",
            ArtifactType.MERMAID_JOURNEY: f"{base_message} Generate a User Journey Map in Mermaid syntax showing user experience stages.",
            ArtifactType.MERMAID_MINDMAP: f"{base_message} Generate a Mindmap in Mermaid syntax with hierarchical structure.",
            ArtifactType.MERMAID_GIT_GRAPH: f"{base_message} Generate a Git Graph in Mermaid syntax showing branch structure.",
            ArtifactType.MERMAID_TIMELINE: f"{base_message} Generate a Timeline in Mermaid syntax with chronological events.",
            ArtifactType.MERMAID_SYSTEM_OVERVIEW: f"{base_message} Generate a System Overview Diagram in Mermaid syntax showing high-level system architecture.",
            ArtifactType.MERMAID_API_SEQUENCE: f"{base_message} Generate an API Sequence Diagram in Mermaid syntax showing API calls and responses.",
            ArtifactType.MERMAID_UML: f"{base_message} Generate a UML Diagram in Mermaid syntax following UML standards.",
            # C4 Diagrams
            ArtifactType.MERMAID_C4_CONTEXT: f"{base_message} Generate a C4 Context Diagram in Mermaid syntax showing system boundaries and external actors.",
            ArtifactType.MERMAID_C4_CONTAINER: f"{base_message} Generate a C4 Container Diagram in Mermaid syntax showing containers and their relationships.",
            ArtifactType.MERMAID_C4_COMPONENT: f"{base_message} Generate a C4 Component Diagram in Mermaid syntax showing components within a container.",
            ArtifactType.MERMAID_C4_DEPLOYMENT: f"{base_message} Generate a C4 Deployment Diagram in Mermaid syntax showing deployment architecture.",
            # HTML Diagrams
            ArtifactType.HTML_ERD: f"{base_message} Generate a standalone, interactive HTML Entity-Relationship Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_ARCHITECTURE: f"{base_message} Generate a standalone, interactive HTML System Architecture Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_SEQUENCE: f"{base_message} Generate a standalone, interactive HTML Sequence Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_CLASS: f"{base_message} Generate a standalone, interactive HTML Class Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_STATE: f"{base_message} Generate a standalone, interactive HTML State Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_FLOWCHART: f"{base_message} Generate a standalone, interactive HTML Flowchart. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_DATA_FLOW: f"{base_message} Generate a standalone, interactive HTML Data Flow Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_USER_FLOW: f"{base_message} Generate a standalone, interactive HTML User Flow Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_COMPONENT: f"{base_message} Generate a standalone, interactive HTML Component Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_GANTT: f"{base_message} Generate a standalone, interactive HTML Gantt Chart. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_PIE: f"{base_message} Generate a standalone, interactive HTML Pie Chart. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_JOURNEY: f"{base_message} Generate a standalone, interactive HTML User Journey Map. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_MINDMAP: f"{base_message} Generate a standalone, interactive HTML Mindmap. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_GIT_GRAPH: f"{base_message} Generate a standalone, interactive HTML Git Graph. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_TIMELINE: f"{base_message} Generate a standalone, interactive HTML Timeline. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_SYSTEM_OVERVIEW: f"{base_message} Generate a standalone, interactive HTML System Overview Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_API_SEQUENCE: f"{base_message} Generate a standalone, interactive HTML API Sequence Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_UML: f"{base_message} Generate a standalone, interactive HTML UML Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_C4_CONTEXT: f"{base_message} Generate a standalone, interactive HTML C4 Context Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_C4_CONTAINER: f"{base_message} Generate a standalone, interactive HTML C4 Container Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_C4_COMPONENT: f"{base_message} Generate a standalone, interactive HTML C4 Component Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            ArtifactType.HTML_C4_DEPLOYMENT: f"{base_message} Generate a standalone, interactive HTML C4 Deployment Diagram. Use modern HTML/CSS/JS (minimal JS) to make it visually appealing and functional. Output ONLY the HTML.",
            # Code Artifacts
            ArtifactType.CODE_PROTOTYPE: f"""{base_message} Generate a complete, production-ready code prototype with comprehensive tests.

CRITICAL REQUIREMENTS:
1. Generate BOTH implementation code AND comprehensive tests
2. Tests must cover: happy path, edge cases, error handling, validation
3. Use the appropriate testing framework for the language (Jest/Vitest for TS/JS, pytest for Python, NUnit/xUnit for C#)
4. Include setup/teardown, mocks where needed, and clear assertions
5. Aim for 80%+ code coverage
6. Format output as:

=== IMPLEMENTATION ===
[Complete implementation code with proper structure, error handling, and comments]

=== TESTS ===
[Comprehensive test suite with multiple test cases]

=== END ===

Follow the repository's coding style and test patterns. Make tests realistic and meaningful.""",
            ArtifactType.DEV_VISUAL_PROTOTYPE: f"{base_message} Generate a visual prototype code (HTML/CSS/JS) that demonstrates the UI/UX design. Make it interactive and visually appealing.",
            ArtifactType.API_DOCS: f"{base_message} Generate clear, comprehensive API documentation in Markdown format. Include endpoints, methods, request/response schemas, examples, and error codes.",
            # PM Artifacts
            ArtifactType.JIRA: f"{base_message} Generate detailed Jira tickets in Markdown format. Include title, description, acceptance criteria, estimated effort, and labels.",
            ArtifactType.WORKFLOWS: f"{base_message} Generate workflow documentation in Markdown format. Include process steps, decision points, and responsible parties.",
            ArtifactType.BACKLOG: f"{base_message} Generate a prioritized product backlog in Markdown format. Include user stories, priorities, and dependencies.",
            ArtifactType.PERSONAS: f"{base_message} Generate user personas in Markdown format. Include demographics, goals, pain points, and behaviors.",
            ArtifactType.ESTIMATIONS: f"{base_message} Generate project estimations in Markdown format. Include time estimates, resource requirements, and risk assessments.",
            ArtifactType.FEATURE_SCORING: f"{base_message} Generate a feature scoring matrix in Markdown format. Include features, scores, and prioritization rationale.",
        }
        return messages.get(artifact_type, f"{base_message} Generate high-quality artifacts based on the requirements.")
    
    async def _try_cloud_models(
        self,
        artifact_type: ArtifactType,
        meeting_notes: str,
        assembled_context: str,
        context: Dict[str, Any],
        threshold: float,
        progress_callback: Optional[callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Try cloud models as fallback."""
        # Get cloud models from routing first, then fallback to defaults
        routing = self.model_service.get_routing_for_artifact(artifact_type)
        cloud_providers = []
        
        # Extract cloud models from routing fallback_models
        if routing and routing.fallback_models:
            for model_id in routing.fallback_models:
                if ":" in model_id:
                    provider, model_name = model_id.split(":", 1)
                    if provider != "ollama":
                        # Check if API key is available
                        if provider == "gemini" and (settings.google_api_key or settings.gemini_api_key):
                            cloud_providers.append((provider, model_name))
                        elif provider == "groq" and settings.groq_api_key:
                            cloud_providers.append((provider, model_name))
                        elif provider == "openai" and settings.openai_api_key:
                            cloud_providers.append((provider, model_name))
                        elif provider == "anthropic" and settings.anthropic_api_key:
                            cloud_providers.append((provider, model_name))
        
        # Add default cloud models if routing didn't provide any
        if not cloud_providers:
            if settings.google_api_key or settings.gemini_api_key:
                cloud_providers.append(("gemini", "gemini-2.0-flash-exp"))
            if settings.groq_api_key:
                cloud_providers.append(("groq", "llama-3.3-70b-versatile"))
            if settings.openai_api_key:
                cloud_providers.append(("openai", "gpt-4-turbo"))
            if settings.anthropic_api_key:
                cloud_providers.append(("anthropic", "claude-3-5-sonnet-20241022"))
        
        for idx, (provider, model_name) in enumerate(cloud_providers):
            try:
                logger.info(f"Trying cloud provider: {provider} ({model_name})")
                
                # Progress: Trying cloud model
                if progress_callback:
                    progress = 50.0 + (idx / len(cloud_providers)) * 30.0
                    await progress_callback(progress, f"Trying cloud model: {provider}:{model_name}...")
                
                # Call cloud API using SmartGenerationOrchestrator
                content = await self._call_cloud_api(
                    provider=provider,
                    model_name=model_name,
                    meeting_notes=meeting_notes,
                    rag_context=assembled_context,
                    artifact_type=artifact_type
                )
                
                if not content:
                    if progress_callback:
                        await progress_callback(
                            50.0 + (idx / len(cloud_providers)) * 30.0,
                            f"Cloud model {provider}:{model_name} returned no content, trying next..."
                        )
                    continue
                
                # Progress: Validating cloud output (75%)
                if progress_callback:
                    await progress_callback(75.0, f"Validating output from {provider}:{model_name}...")
                
                # Validate
                validation_result = await self.validation_service.validate_artifact(
                    artifact_type=artifact_type,
                    content=content,
                    meeting_notes=meeting_notes,
                    context=context
                )
                
                score = validation_result.score
                is_valid = validation_result.is_valid and score >= threshold
                
                if is_valid:
                    # Progress: Cloud success (90%)
                    if progress_callback:
                        await progress_callback(90.0, f"Cloud generation successful! (Score: {score:.1f})")
                    
                    return {
                        "content": content,
                        "model_used": model_name,
                        "provider": provider,
                        "score": score,
                        "is_valid": True,
                        "attempt": {
                            "model": model_name,
                            "provider": provider,
                            "content": content,
                            "score": score,
                            "is_valid": True,
                            "errors": validation_result.errors
                        }
                    }
            except Exception as e:
                logger.error(f"Error with cloud provider {provider}: {e}")
                continue
        
        return None
    
    async def _call_cloud_api(
        self,
        provider: str,
        model_name: str,
        meeting_notes: str,
        rag_context: str,
        artifact_type: ArtifactType
    ) -> Optional[str]:
        """
        Call cloud API using SmartGenerationOrchestrator or direct API calls.
        
        This properly integrates with cloud providers (Gemini, Grok, OpenAI, Anthropic).
        """
        try:
            # Build prompt
            prompt = self._build_prompt(meeting_notes, rag_context, artifact_type)
            system_message = self._get_system_message(artifact_type)
            
            # Try SmartGenerationOrchestrator first (preferred)
            try:
                from ai.smart_generation import get_smart_generator
                orchestrator = get_smart_generator(
                    ollama_client=self.ollama_client,
                    output_validator=self.validation_service
                )
                
                result = await orchestrator.generate(
                    artifact_type=artifact_type.value,
                    prompt=prompt,
                    system_message=system_message,
                    meeting_notes=meeting_notes,
                    rag_context=rag_context,
                    model_preference=f"{provider}:{model_name}",
                    temperature=0.2
                )
                
                if result and hasattr(result, 'content'):
                    return result.content
                elif isinstance(result, dict) and 'content' in result:
                    return result['content']
            except ImportError:
                logger.debug("SmartGenerationOrchestrator not available, trying UniversalArchitectAgent...")
            except Exception as e:
                logger.warning(f"SmartGenerationOrchestrator failed: {e}, trying fallback...")
            
            # Fallback: Use UniversalArchitectAgent
            if UNIVERSAL_AGENT_AVAILABLE:
                agent = UniversalArchitectAgent()
                
                result = await agent.generate_artifact(
                    artifact_type=artifact_type.value,
                    meeting_notes=meeting_notes,
                    rag_context=rag_context,
                    model_preference=f"{provider}:{model_name}",
                    system_message=system_message
                )
                
                if result and hasattr(result, 'content'):
                    return result.content
                elif isinstance(result, dict) and 'content' in result:
                    return result['content']
            
            # Final fallback: Direct API calls
            return await self._call_cloud_api_direct(provider, model_name, prompt, system_message)
            
        except Exception as e:
            logger.error(f"Error calling cloud API for {provider}:{model_name}: {e}", exc_info=True)
            return None
    
    async def _call_cloud_api_direct(
        self,
        provider: str,
        model_name: str,
        prompt: str,
        system_message: str
    ) -> Optional[str]:
        """Direct cloud API calls as final fallback."""
        try:
            if provider == "gemini" and (settings.google_api_key or settings.gemini_api_key):
                import google.generativeai as genai
                api_key = settings.google_api_key or settings.gemini_api_key
                if not api_key:
                    logger.warning("Gemini API key not found in settings")
                    return None
                
                genai.configure(api_key=api_key)
                # Extract model name if it includes provider prefix (e.g., "gemini-2.0-flash-exp" from "gemini:gemini-2.0-flash-exp")
                actual_model_name = model_name.split(":")[-1] if ":" in model_name else model_name
                # Map model names to actual Gemini model IDs
                model_mapping = {
                    "gemini-2.0-flash-exp": "gemini-2.0-flash-exp",
                    "gemini-1.5-pro": "gemini-1.5-pro",
                    "gemini-1.5-flash": "gemini-1.5-flash",
                }
                actual_model_name = model_mapping.get(actual_model_name, actual_model_name)
                
                logger.info(f"Calling Gemini API with model: {actual_model_name}")
                model = genai.GenerativeModel(actual_model_name)
                
                # Build full prompt with system message
                full_prompt = f"{system_message}\n\n{prompt}"
                
                response = await asyncio.to_thread(
                    model.generate_content,
                    full_prompt
                )
                result = response.text if response and response.text else None
                if result:
                    logger.info(f"Gemini API call successful, response length: {len(result)}")
                else:
                    logger.warning("Gemini API returned empty response")
                return result
                
            elif provider == "openai" and settings.openai_api_key:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                return response.choices[0].message.content if response.choices else None
                
            elif provider == "anthropic" and settings.anthropic_api_key:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                response = await client.messages.create(
                    model=model_name,
                    max_tokens=4096,
                    system=system_message,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text if response.content else None
                
            elif provider == "groq" and settings.groq_api_key:
                from groq import AsyncGroq
                if not settings.groq_api_key:
                    logger.warning("Groq API key not found in settings")
                    return None
                
                client = AsyncGroq(api_key=settings.groq_api_key)
                # Extract model name if it includes provider prefix
                actual_model_name = model_name.split(":")[-1] if ":" in model_name else model_name
                # Map Groq model names
                model_mapping = {
                    "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
                    "llama-3.1-70b-versatile": "llama-3.1-70b-versatile",
                    "llama-3.1-8b-instant": "llama-3.1-8b-instant",
                    "mixtral-8x7b-32768": "mixtral-8x7b-32768",
                }
                actual_model_name = model_mapping.get(actual_model_name, actual_model_name)
                
                logger.info(f"Calling Groq API with model: {actual_model_name}")
                response = await client.chat.completions.create(
                    model=actual_model_name,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2
                )
                result = response.choices[0].message.content if response.choices else None
                if result:
                    logger.info(f"Groq API call successful, response length: {len(result)}")
                else:
                    logger.warning("Groq API returned empty response")
                return result
                
        except ImportError as e:
            logger.warning(f"Required library for {provider} not installed: {e}")
        except Exception as e:
            logger.error(f"Direct API call to {provider} failed: {e}", exc_info=True)
        
        return None


# Simple result class for generate_with_fallback
class GenerationResult:
    """Simple result container for generate_with_fallback."""
    def __init__(self, content: str, model_used: str, success: bool = True, error: Optional[str] = None):
        self.content = content
        self.model_used = model_used
        self.success = success
        self.error = error


# Import normalization utility
from backend.services.model_service import normalize_model_id, get_ollama_model_name

# Add generate_with_fallback method to EnhancedGenerationService
async def _generate_with_fallback(
    self,
    prompt: str,
    system_instruction: str = "",
    model_routing: Optional[Any] = None,
    response_format: str = "text",
    temperature: float = 0.3,
    max_local_attempts: int = 2,  # Reduce from default for faster response
    timeout_seconds: int = 60  # Timeout for single attempt
) -> GenerationResult:
    """
    Generate content with model fallback support.
    Used by Canvas AI improve/auto-fix features.
    
    Args:
        prompt: The prompt to send to the model
        system_instruction: System message for the model
        model_routing: Optional routing configuration
        response_format: Expected response format ("text" or "json")
        temperature: Generation temperature
        max_local_attempts: Maximum local model attempts before cloud fallback (default: 2)
        timeout_seconds: Timeout for a single generation attempt
    
    Returns:
        GenerationResult with content and model_used
    """
    logger.info(f"🔄 [ENHANCED_GEN] generate_with_fallback called: prompt_length={len(prompt)}, "
               f"response_format={response_format}, temperature={temperature}")
    
    # Get models to try (using normalization utility for consistent handling)
    models_to_try = []
    cloud_models_to_try = []  # For cloud fallback
    
    # If routing is provided, use it
    if model_routing:
        if hasattr(model_routing, 'primary_model'):
            primary = model_routing.primary_model
            provider, model_name = normalize_model_id(primary, "ollama")
            if provider == "ollama":
                models_to_try.append(model_name)
            else:
                cloud_models_to_try.append((provider, model_name))
        
        if hasattr(model_routing, 'fallback_models'):
            for fallback in model_routing.fallback_models:
                provider, model_name = normalize_model_id(fallback, "ollama")
                if provider == "ollama":
                    if model_name not in models_to_try:
                        models_to_try.append(model_name)
                else:
                    if (provider, model_name) not in cloud_models_to_try:
                        cloud_models_to_try.append((provider, model_name))
    
    # Default models if none from routing
    if not models_to_try:
        models_to_try = ["llama3", "codellama", "mistral"]
    
    logger.info(f"📋 [ENHANCED_GEN] Models to try: {models_to_try[:5]}")
    
    # Try local models first (with limited attempts for faster response)
    local_attempts = 0
    if self.ollama_client:
        for model_name in models_to_try:
            if local_attempts >= max_local_attempts:
                logger.info(f"⏭️ [ENHANCED_GEN] Reached max local attempts ({max_local_attempts}), moving to cloud")
                break
            
            local_attempts += 1
            try:
                logger.info(f"🤖 [ENHANCED_GEN] Trying local model: {model_name} (attempt {local_attempts}/{max_local_attempts})")
                
                # Ensure model is available
                await self.ollama_client.ensure_model_available(model_name)
                
                # Generate with timeout
                try:
                    import asyncio
                    response = await asyncio.wait_for(
                        self.ollama_client.generate(
                            model_name=model_name,
                            prompt=prompt,
                            system_message=system_instruction,
                            temperature=temperature
                        ),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ [ENHANCED_GEN] Timeout after {timeout_seconds}s with {model_name}")
                    continue
                
                if response.success and response.content:
                    logger.info(f"✅ [ENHANCED_GEN] Success with {model_name}: content_length={len(response.content)}")
                    return GenerationResult(
                        content=response.content,
                        model_used=model_name,
                        success=True
                    )
                else:
                    logger.warning(f"⚠️ [ENHANCED_GEN] {model_name} returned no content")
                    
            except Exception as e:
                logger.warning(f"⚠️ [ENHANCED_GEN] Error with {model_name}: {e}")
                continue
    
    # Try cloud models as fallback
    # Prioritize cloud models from routing, then default providers
    default_cloud_providers = [
        ("gemini", "gemini-2.0-flash-exp"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openai", "gpt-4-turbo"),
        ("anthropic", "claude-3-5-sonnet-20241022"),
    ]
    
    # Combine routing cloud models (first) with defaults (skip duplicates)
    all_cloud_providers = cloud_models_to_try.copy()
    for provider, model_name in default_cloud_providers:
        if (provider, model_name) not in all_cloud_providers:
            all_cloud_providers.append((provider, model_name))
    
    for provider, model_name in all_cloud_providers:
        try:
            logger.info(f"☁️ [ENHANCED_GEN] Trying cloud model: {provider}:{model_name}")
            content = await self._call_cloud_api_direct(
                provider=provider,
                model_name=model_name,
                prompt=prompt,
                system_message=system_instruction
            )
            
            if content:
                logger.info(f"✅ [ENHANCED_GEN] Success with cloud {provider}:{model_name}")
                return GenerationResult(
                    content=content,
                    model_used=f"{provider}:{model_name}",
                    success=True
                )
        except Exception as e:
            logger.warning(f"⚠️ [ENHANCED_GEN] Cloud {provider} failed: {e}")
            continue
    
    # All attempts failed
    error_msg = "All model attempts failed"
    logger.error(f"❌ [ENHANCED_GEN] {error_msg}")
    return GenerationResult(
        content="",
        model_used="none",
        success=False,
        error=error_msg
    )

# Attach the method to the class
EnhancedGenerationService.generate_with_fallback = _generate_with_fallback


# Global service instance
_enhanced_service: Optional[EnhancedGenerationService] = None

def get_enhanced_service() -> EnhancedGenerationService:
    """Get or create global Enhanced Generation Service instance."""
    global _enhanced_service
    if _enhanced_service is None:
        _enhanced_service = EnhancedGenerationService()
    return _enhanced_service

