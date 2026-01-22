"""
Enhanced Generation Service - Implements proper pipeline:
local model → retry with next model → cloud fallback → return best attempt

This service properly uses model routing and implements the user's requirements.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
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
from backend.core.logger import get_logger, log_error_to_file, log_token_usage, log_ai_call
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
    from ai.huggingface_client import get_client as get_hf_client
    HF_CLIENT_AVAILABLE = True
except ImportError:
    HF_CLIENT_AVAILABLE = False
    logger.warning("HuggingFace client not available. Direct HF model usage disabled.")

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
        self.hf_client = get_hf_client() if HF_CLIENT_AVAILABLE else None
        
        logger.info("Enhanced Generation Service initialized")
    
    async def generate_with_pipeline(
        self,
        artifact_type: Union[ArtifactType, str],
        meeting_notes: str,
        context_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate artifact using proper pipeline.
        
        Args:
            artifact_type: Type of artifact to generate (enum or custom type string)
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
        
        # Handle both enum and string artifact types
        custom_prompt_template = None
        if isinstance(artifact_type, ArtifactType):
            artifact_type_str = artifact_type.value
            is_custom_type = False
        else:
            artifact_type_str = str(artifact_type)
            is_custom_type = True
            # Load custom artifact type info for prompt template
            try:
                from backend.services.custom_artifact_service import get_service as get_custom_service
                custom_service = get_custom_service()
                custom_type_info = custom_service.get_type(artifact_type_str)
                if custom_type_info:
                    custom_prompt_template = custom_type_info.prompt_template
                    logger.info(f"📝 [ENHANCED_GEN] Loaded custom prompt template for {artifact_type_str}")
            except Exception as e:
                logger.warning(f"⚠️ [ENHANCED_GEN] Could not load custom type info: {e}")
        
        logger.info(f"🚀 [ENHANCED_GEN] Starting generation pipeline: artifact_type={artifact_type_str}, "
                   f"is_custom={is_custom_type}, has_custom_template={bool(custom_prompt_template)}, "
                   f"meeting_notes_length={len(meeting_notes)}, context_id={context_id}")
        
        # Record metrics
        metrics.increment("generation_requests_total", tags={"artifact_type": artifact_type_str})
        
        # Progress: Building context (10%)
        if progress_callback:
            await progress_callback(10.0, "Building context from repository...")
        
        # Build context if not provided (with artifact-specific RAG targeting)
        logger.info(f"🏗️ [ENHANCED_GEN] Building context (artifact_type={artifact_type_str})")
        with metrics.timer("context_building", tags={"artifact_type": artifact_type_str}):
            try:
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
                            artifact_type=artifact_type_str,  # Pass artifact type for targeted RAG
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
                        artifact_type=artifact_type_str,  # Pass artifact type for targeted RAG
                        force_refresh=True  # Always get fresh context for generation
                    )
                    logger.info(f"✅ [ENHANCED_GEN] Context built successfully")
            except Exception as e:
                logger.error(f"❌ [ENHANCED_GEN] Context building failed: {e}", exc_info=True)
                # FIX: Don't fail generation if context building fails - use minimal context
                logger.warning(f"⚠️ [ENHANCED_GEN] Continuing with minimal context (meeting notes only)")
                context = {
                    "meeting_notes": meeting_notes,
                    "assembled_context": f"## Requirements\n{meeting_notes}",
                    "sources": {},
                    "created_at": datetime.now().isoformat()
                }
                if progress_callback:
                    await progress_callback(30.0, "Using minimal context (context building had issues)")
        
        # Progress: Context ready (30%)
        if progress_callback:
            await progress_callback(30.0, "Context built successfully")
        
        assembled_context = context.get("assembled_context", "")
        
        # FIX: Ensure meeting notes are in context if missing (for retrieved contexts)
        if not context.get("meeting_notes") and meeting_notes:
            context["meeting_notes"] = meeting_notes
            logger.info(f"🔧 [ENHANCED_GEN] Added meeting notes to retrieved context")
        
        # FIX: If assembled_context is empty or missing, rebuild it with current meeting notes
        if not assembled_context or len(assembled_context.strip()) < 100:
            logger.warning(f"⚠️ [ENHANCED_GEN] Assembled context is empty or too short, rebuilding...")
            # Re-assemble context with current meeting notes
            context["meeting_notes"] = meeting_notes
            assembly_result = self.context_builder._assemble_context(context)
            assembled_context = assembly_result.get("content", "")
            context["assembled_context"] = assembled_context
            logger.info(f"✅ [ENHANCED_GEN] Rebuilt assembled context: length={len(assembled_context)}")
        
        logger.info(f"📊 [ENHANCED_GEN] Context assembled: length={len(assembled_context)}, "
                   f"has_rag={bool(context.get('rag') or context.get('sources', {}).get('rag'))}, "
                   f"has_kg={bool(context.get('knowledge_graph') or context.get('sources', {}).get('kg'))}, "
                   f"has_meeting_notes={bool(context.get('meeting_notes'))}")
        
        # ========================================================================
        # STEP 0: Check if user has a CLOUD model preference (highest priority)
        # This respects user's Model Mapping configuration
        # ========================================================================
        preferred = self.model_service.get_preferred_model_for_artifact(artifact_type)
        if preferred:
            pref_provider, pref_model = preferred
            logger.info(f"🎯 [ENHANCED_GEN] User's preferred model: {pref_provider}:{pref_model}")
            
            # If user prefers a CLOUD model, try it FIRST before local models
            if pref_provider not in ["ollama", "huggingface"]:
                logger.info(f"☁️ [ENHANCED_GEN] User prefers cloud model, trying {pref_provider}:{pref_model} FIRST...")
                
                if progress_callback:
                    await progress_callback(35.0, f"Using your preferred cloud model: {pref_provider}:{pref_model}...")
                
                # Try the user's preferred cloud model
                cloud_result = await self._try_single_cloud_model(
                    provider=pref_provider,
                    model_name=pref_model,
                    artifact_type=artifact_type,
                    meeting_notes=meeting_notes,
                    assembled_context=assembled_context,
                    context=context,
                    threshold=opts.get("validation_threshold", 80.0),
                    progress_callback=progress_callback,
                    custom_prompt_template=custom_prompt_template
                )
                
                if cloud_result and cloud_result.get("success"):
                    logger.info(f"✅ [ENHANCED_GEN] User's preferred cloud model succeeded!")
                    return cloud_result
                else:
                    logger.warning(f"⚠️ [ENHANCED_GEN] User's preferred cloud model failed, falling back to local models...")
        
        # Get models for this artifact type
        # This now properly prioritizes fine-tuned models first
        logger.info(f"🔍 [ENHANCED_GEN] Getting models for artifact type: {artifact_type_str}")
        local_models = self.model_service.get_models_for_artifact(artifact_type)
        logger.info(f"📋 [ENHANCED_GEN] Found {len(local_models)} local model(s) for {artifact_type_str}")
        
        # Log which models will be tried (first 3)
        if local_models:
            model_preview = ", ".join(local_models[:3])
            if len(local_models) > 3:
                model_preview += f" (+{len(local_models) - 3} more)"
            logger.info(f"🎯 [ENHANCED_GEN] Model priority order: {model_preview}")
        
        # If no local models AND no cloud preference worked, try cloud fallback
        if not local_models:
            logger.warning(f"⚠️ [ENHANCED_GEN] No local models available, trying cloud fallback...")
            
            if progress_callback:
                await progress_callback(40.0, "No local models, trying cloud models...")
            
            # Try cloud models as fallback
            cloud_result = await self._try_cloud_models(
                artifact_type=artifact_type,
                meeting_notes=meeting_notes,
                assembled_context=assembled_context,
                context=context,
                threshold=opts.get("validation_threshold", 80.0),
                progress_callback=progress_callback
            )
            
            if cloud_result and cloud_result.get("success"):
                return cloud_result
            
            # If even cloud failed, return error
            error_msg = "No models available. Please ensure Ollama is running or configure cloud API keys."
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
        
        # Known cloud providers - anything else with ":" is likely an Ollama model:tag format
        CLOUD_PROVIDERS = {"gemini", "groq", "openai", "anthropic"}
        
        for model_idx, model_id in enumerate(local_models):
            # Check if this is a local model (Ollama/HuggingFace) or cloud model
            provider = "ollama"  # default
            model_name = model_id
            hf_model_id = None
            hf_model_path = None
            
            if ":" in model_id:
                prefix, rest = model_id.split(":", 1)
                
                # Check if the prefix is a known provider
                if prefix == "huggingface":
                    provider = "huggingface"
                    model_name = rest
                    # Extract HuggingFace model ID
                    hf_model_id = model_name.replace("-", "/")  # Convert back from registry format
                    # Try to get model path from registry
                    try:
                        from backend.services.huggingface_service import get_service as get_hf_service
                        hf_service = get_hf_service()
                        if hf_model_id in hf_service.downloaded_models:
                            hf_model_path = hf_service.downloaded_models[hf_model_id].get("path")
                            # Also check for actual_file_path
                            if not hf_model_path:
                                hf_model_path = hf_service.downloaded_models[hf_model_id].get("actual_file_path")
                        # Also check ModelService metadata
                        if not hf_model_path:
                            model_info = self.model_service.models.get(model_id)
                            if model_info and model_info.metadata:
                                hf_model_path = model_info.metadata.get("path") or model_info.metadata.get("actual_file_path")
                    except Exception as e:
                        logger.debug(f"Could not get HF model path: {e}")
                elif prefix == "ollama":
                    # Explicit ollama:model:tag format
                    provider = "ollama"
                    model_name = rest
                elif prefix.lower() in CLOUD_PROVIDERS:
                    # This is a cloud model (gemini:xxx, groq:xxx, etc.)
                    provider = prefix.lower()
                    model_name = rest
                else:
                    # Assume Ollama model:tag format (e.g., codellama:7b-instruct-q4_K_M)
                    # The full model_id IS the Ollama model name
                    provider = "ollama"
                    model_name = model_id  # Keep the full name including tag
            
            # Skip cloud models in local phase
            if provider in CLOUD_PROVIDERS:
                logger.debug(f"⏭️ [ENHANCED_GEN] Skipping cloud model in local phase: {model_id}")
                continue
            
            # Check if we have the appropriate client
            if provider == "ollama" and not self.ollama_client:
                logger.debug(f"⏭️ [ENHANCED_GEN] Ollama client not available, skipping: {model_id}")
                continue
            
            if provider == "huggingface" and not self.hf_client:
                logger.debug(f"⏭️ [ENHANCED_GEN] HuggingFace client not available, skipping: {model_id}")
                continue
            
            logger.info(f"🤖 [ENHANCED_GEN] Attempting local model [{model_idx + 1}/{len(local_models)}]: {model_name} ({provider}) for {artifact_type_str}")
            
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
                    logger.info(f"🔄 [ENHANCED_GEN] Model attempt {retry + 1}/{opts['max_retries'] + 1}: {model_name} ({provider})")
                    logger.info(f"📋 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}: Building prompt with meeting_notes_length={len(meeting_notes)}, assembled_context_length={len(assembled_context)}")
                    
                    # Build prompt with context (use custom template if available)
                    prompt = self._build_prompt(meeting_notes, assembled_context, artifact_type, custom_prompt_template)
                    logger.info(f"📝 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.1: Prompt built: length={len(prompt)}, custom_template={bool(custom_prompt_template)}")
                    logger.info(f"📝 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.2: Prompt preview (first 200 chars): {prompt[:200]}...")
                    
                    # Generate based on provider
                    if provider == "ollama":
                        # Load model (with VRAM management)
                        logger.info(f"📋 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.3: Ensuring Ollama model {model_name} is available...")
                        await self.ollama_client.ensure_model_available(model_name)
                        logger.info(f"✅ [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.4: Model {model_name} is available and loaded")
                        
                        # Generate with context window from centralized config
                        logger.info(f"⚡ [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.5: Generating with {model_name} (temperature={opts['temperature']}, num_ctx={settings.local_model_context_window})...")
                        response = await self.ollama_client.generate(
                            model_name=model_name,
                            prompt=prompt,
                            system_message=self._get_system_message(artifact_type),
                            temperature=opts["temperature"],
                            num_ctx=settings.local_model_context_window  # From centralized config
                        )
                    elif provider == "huggingface":
                        # Use HuggingFace client
                        logger.info(f"📋 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.3: Loading HuggingFace model: {hf_model_id or model_name}...")
                        logger.info(f"⚡ [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.4: Generating with HuggingFace model: {hf_model_id or model_name}...")
                        hf_response = await self.hf_client.generate(
                            model_id=hf_model_id or model_name,
                            prompt=prompt,
                            system_message=self._get_system_message(artifact_type),
                            temperature=opts["temperature"],
                            model_path=hf_model_path
                        )
                        # Convert HF response to Ollama-like response format
                        from ai.ollama_client import GenerationResponse as OllamaResponse
                        response = OllamaResponse(
                            content=hf_response.content,
                            model_used=hf_response.model_used,
                            generation_time=hf_response.generation_time,
                            tokens_generated=hf_response.tokens_generated,
                            success=hf_response.success,
                            error_message=hf_response.error_message
                        )
                    else:
                        logger.warning(f"⚠️ [ENHANCED_GEN] Unknown provider: {provider}")
                        continue
                    
                    # Log AI call and token usage
                    if response.success:
                        logger.info(f"✅ [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.6: Generation completed successfully: content_length={len(response.content) if response.content else 0}, duration={response.generation_time if hasattr(response, 'generation_time') else 0:.2f}s")
                        log_ai_call(
                            model=model_name,
                            prompt_length=len(prompt),
                            response_length=len(response.content) if response.content else 0,
                            operation="artifact_generation",
                            success=True,
                            duration_seconds=response.generation_time if hasattr(response, 'generation_time') else 0,
                            metadata={"artifact_type": artifact_type_str, "provider": provider}
                        )
                        
                        # Log token usage if available
                        if hasattr(response, 'tokens_generated') and response.tokens_generated:
                            logger.info(f"🔢 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.7: Token usage: input≈{len(prompt) // 4}, output={response.tokens_generated}, total≈{len(prompt) // 4 + response.tokens_generated}")
                            log_token_usage(
                                model=f"{provider}:{model_name}",
                                input_tokens=len(prompt) // 4,  # Rough estimate: 4 chars per token
                                output_tokens=response.tokens_generated,
                                operation="artifact_generation",
                                artifact_type=artifact_type_str,
                                duration_seconds=response.generation_time if hasattr(response, 'generation_time') else None,
                                success=True
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
                    logger.info(f"🔍 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.8: Validating output from {model_name}...")
                    logger.info(f"📋 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.8.1: Calling validation service with content_length={len(response.content)}")
                    validation_result = await self.validation_service.validate_artifact(
                        artifact_type=artifact_type,
                        content=response.content,
                        meeting_notes=meeting_notes,
                        context=context
                    )
                    
                    score = validation_result.score
                    logger.info(f"📊 [ENHANCED_GEN] Step 3.{model_idx + 1}.{retry + 1}.8.2: Validation result: score={score:.1f}, is_valid={validation_result.is_valid}, threshold={opts['validation_threshold']}")
                    # Use raw content as default; may be refined later after a successful validation pass
                    cleaned_content = response.content
                    # Additional render-viability checks for diagrams/HTML
                    render_viable = True
                    is_runnable = True
                    if artifact_type_str.startswith("mermaid_"):
                        candidate = cleaned_content
                        mermaid_markers = [
                            "graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram",
                            "erDiagram", "gantt", "journey", "pie", "gitGraph", "mindmap", "timeline"
                        ]
                        if not any(marker in candidate for marker in mermaid_markers):
                            render_viable = False
                        
                        # Check if diagram is actually runnable (can be rendered)
                        try:
                            from backend.services.validation_service import get_service
                            validator = get_service()
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
                    
                    if artifact_type_str.startswith("html_"):
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
                        if artifact_type_str.startswith("mermaid_"):
                            try:
                                from backend.services.validation_service import ValidationService
                                validator = ValidationService()
                                cleaned_content = validator._extract_mermaid_diagram(response.content)
                                chars_removed = len(response.content) - len(cleaned_content)
                                # Only log significant cleanups to reduce log spam
                                if chars_removed > 5:
                                    logger.info(f"🧹 [ENHANCED_GEN] Cleaned Mermaid diagram: removed {chars_removed} chars of extra text")
                                
                                # Fix ERD syntax if it's using class diagram syntax
                                if artifact_type_str == "mermaid_erd" and ("class " in cleaned_content or "CLASS " in cleaned_content):
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
                                    artifact_type=artifact_type_str,
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
                        if artifact_type_str.startswith("mermaid_"):
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
                                logger.info(f"✅ Auto-generated HTML version for {artifact_type_str}")
                            except Exception as e:
                                logger.warning(f"Failed to auto-generate HTML version: {e}")
                        
                        # Create version for this artifact
                        # Use stable artifact_id (the artifact type itself) to ensure versioning works correctly
                        # instead of creating a new artifact for every generation.
                        artifact_id = artifact_type_str
                        
                        # NOTE: GenerationService handles saving to VersionService using this artifact_id.
                        # We avoid double-saving here.
                        # try:
                        #     from backend.services.version_service import get_version_service
                        #     version_service = get_version_service()
                        #     version_service.create_version(
                        #         artifact_id=artifact_id,
                        #         artifact_type=artifact_type_str,
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
                                        logger.info(f"✅ [ENHANCED_GEN] Promoted {model_name} ({model_id}) to primary for {artifact_type_str} (score: {score:.1f}, previous: {current_primary})")
                                    elif model_already_primary:
                                        logger.debug(f"✅ [ENHANCED_GEN] Model {model_name} already primary for {artifact_type_str}, no update needed")
                                    else:
                                        logger.debug(f"⚠️ [ENHANCED_GEN] Model {model_name} scored {score:.1f} but not promoting (already primary or score < 80)")
                                else:
                                    # Create new routing with this successful model
                                    # Note: settings is imported at module level
                                    routing = ModelRoutingDTO(
                                        artifact_type=artifact_type,
                                        primary_model=model_id,
                                        fallback_models=settings.default_fallback_models,
                                        enabled=True
                                    )
                                    model_service.update_routing([routing])
                                    logger.info(f"✅ [ENHANCED_GEN] Created routing for {artifact_type_str} with {model_name} ({model_id}) as primary (score: {score:.1f})")
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
                    
                    # Log error to JSONL
                    log_error_to_file(
                        error=e,
                        context={
                            "model": model_name,
                            "provider": provider,
                            "artifact_type": artifact_type_str,
                            "retry": retry,
                            "operation": "artifact_generation"
                        },
                        module="enhanced_generation",
                        function="generate_with_pipeline"
                    )
                    
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
                                    artifact_type=artifact_type_str,
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
                        if artifact_type_str.startswith("mermaid_"):
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
                                logger.info(f"✅ Auto-generated HTML version for {artifact_type_str} (cloud)")
                            except Exception as e:
                                logger.warning(f"Failed to auto-generate HTML version: {e}")
                        
                        # Use stable artifact_id (artifact type) for proper versioning
                        # NOTE: Version creation is handled by GenerationService to avoid duplicates
                        artifact_id = artifact_type_str
                        
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
            artifact_id = artifact_type_str
            
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
            metrics.increment("generation_failures_total", tags={"artifact_type": artifact_type_str})
            
            if progress_callback:
                await progress_callback(100.0, f"Error: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "error_type": "all_attempts_failed",
                "attempts": attempts,
                "suggestion": "Ensure Ollama is running, models are installed, or cloud API keys are configured"
            }
    
    def _build_prompt(self, meeting_notes: str, rag_context: str, artifact_type: Union[ArtifactType, str], 
                       custom_prompt_template: Optional[str] = None) -> str:
        """
        Build comprehensive prompt with all context.
        
        FIX: The rag_context (assembled_context) already includes meeting notes,
        so we check if meeting notes are already in rag_context to avoid duplication.
        However, we still include them separately for clarity and emphasis.
        """
        # Import prompt sanitization to prevent injection attacks
        from rag.filters import sanitize_prompt_input
        
        parts = []
        
        # Get artifact type as string
        if isinstance(artifact_type, ArtifactType):
            artifact_type_str = artifact_type.value
        else:
            artifact_type_str = str(artifact_type)
        
        # Check if we have a custom prompt template
        if custom_prompt_template:
            # Use custom prompt template, substituting {meeting_notes} and {context}
            prompt = custom_prompt_template
            safe_notes = sanitize_prompt_input(meeting_notes, max_length=8000)
            safe_context = sanitize_prompt_input(rag_context, max_length=12000) if rag_context else ""
            prompt = prompt.replace("{meeting_notes}", safe_notes)
            prompt = prompt.replace("{context}", safe_context)
            return prompt
        
        # Default prompt building for built-in types
        artifact_name = artifact_type_str.replace("_", " ").title()
        parts.append(f"Generate a {artifact_name} based on the following requirements and project context.")
        
        # FIX: Check if meeting notes are already in rag_context to avoid duplication
        # The assembled_context includes meeting notes, but we still want them as a clear section
        # So we include them, but note that they may also appear in the context section
        if meeting_notes and meeting_notes.strip():
            parts.append("\n## Requirements")
            # Sanitize user-provided meeting notes to prevent prompt injection
            safe_notes = sanitize_prompt_input(meeting_notes, max_length=8000)
            parts.append(safe_notes)
        
        if rag_context and rag_context.strip():
            parts.append("\n## Project Context (from codebase)")
            # Sanitize RAG context (already from our own codebase, but still good practice)
            # FIX: Increased from 3000 to 12000 chars to preserve more important context
            # The previous 3000 char limit was losing critical architectural details
            # Most LLMs can handle 8K+ context; Ollama/llama3 supports 8K tokens (~32K chars)
            safe_context = sanitize_prompt_input(rag_context, max_length=12000)
            parts.append(safe_context)
        elif not rag_context or not rag_context.strip():
            logger.warning(f"⚠️ [ENHANCED_GEN] RAG context is empty! This may result in generic outputs.")
        
        parts.append("\n## Instructions")
        parts.append("1. Ensure the output is complete and production-ready")
        parts.append("2. Follow best practices and conventions")
        parts.append("3. Include all necessary details")
        parts.append("4. Validate syntax and correctness")
        
        final_prompt = "\n".join(parts)
        
        # Log prompt composition for debugging
        logger.debug(f"📝 [ENHANCED_GEN] Prompt built: total_length={len(final_prompt)}, "
                    f"meeting_notes_length={len(meeting_notes) if meeting_notes else 0}, "
                    f"rag_context_length={len(rag_context) if rag_context else 0}")
        
        return final_prompt
    
    def _get_system_message(self, artifact_type: Union[ArtifactType, str]) -> str:
        """Get comprehensive system message for artifact type."""
        base_message = "You are an expert architect and developer assistant. Your goal is to generate high-quality, accurate, and relevant architectural artifacts."
        
        # Handle custom artifact types (not in the messages dict)
        if isinstance(artifact_type, str):
            # Try to convert to enum, if fails use generic message
            try:
                artifact_type = ArtifactType(artifact_type)
            except ValueError:
                # This is a custom artifact type - use generic message
                artifact_name = artifact_type.replace("_", " ").title()
                return f"{base_message} Generate a {artifact_name} based on the provided requirements. Ensure the output is accurate, well-structured, and follows best practices."
        
        # CRITICAL: Explicit instruction to avoid explanatory text
        mermaid_output_rules = """

CRITICAL OUTPUT RULES:
- Output ONLY the Mermaid diagram code
- Start directly with the diagram type keyword (erDiagram, flowchart, classDiagram, etc.)
- Do NOT include explanations, notes, or comments
- Do NOT wrap in markdown code blocks (no ```)
- Do NOT say "Here is", "Let me know", or similar phrases
- Do NOT include numbered lists or bullet points
- Your first character MUST be the diagram type (e, f, g, c, s, etc.)
- Your last character MUST be } or end or a diagram element
- Just the raw Mermaid code, nothing else"""

        # ERD-specific syntax guide
        erd_syntax_guide = """

ERD SYNTAX REQUIREMENTS:
Valid format:
erDiagram
    ENTITY_NAME {
        type fieldname KEY
    }
    ENTITY1 ||--o{ ENTITY2 : relationship_label

Example:
erDiagram
    USER {
        int id PK
        string name
        string email
    }
    ORDER {
        int id PK
        int user_id FK
        datetime created_at
    }
    USER ||--o{ ORDER : places

RELATIONSHIP SYMBOLS:
- ||--|| : one to one
- ||--o{ : one to many
- }o--o{ : many to many
- ||--o| : one to zero or one

NEVER USE: class, ->, depend, quotes around entity names"""
        
        messages = {
            # Mermaid Diagrams
            ArtifactType.MERMAID_ERD: f"{base_message} Generate a clean, correct Entity-Relationship Diagram in Mermaid syntax. Include all entities, relationships, and cardinalities.{erd_syntax_guide}{mermaid_output_rules}",
            ArtifactType.MERMAID_ARCHITECTURE: f"""{base_message} Generate a comprehensive System Architecture Diagram in Mermaid syntax. Show components, their relationships, data flow, and system boundaries.

FLOWCHART SYNTAX FOR ARCHITECTURE:
flowchart TD
    subgraph Frontend
        UI[User Interface]
        API_Gateway[API Gateway]
    end
    subgraph Backend
        Service[Service Layer]
        DB[(Database)]
    end
    UI --> API_Gateway --> Service --> DB

Use subgraphs for system boundaries.{mermaid_output_rules}""",
            ArtifactType.MERMAID_SEQUENCE: f"""{base_message} Generate a detailed Sequence Diagram in Mermaid syntax. Show all actors, objects, and message flows.

SEQUENCE SYNTAX:
sequenceDiagram
    participant U as User
    participant S as Server
    participant DB as Database
    U->>S: Request
    S->>DB: Query
    DB-->>S: Results
    S-->>U: Response

Use ->> for solid arrows, -->> for dashed arrows.
Always include : for messages.{mermaid_output_rules}""",
            ArtifactType.MERMAID_CLASS: f"""{base_message} Generate a Class Diagram in Mermaid syntax.

CLASS DIAGRAM SYNTAX:
classDiagram
    class ClassName {{
        +type attribute
        +method() returnType
    }}
    Parent <|-- Child : inherits
    Container *-- Component : contains
    Owner o-- Owned : aggregates
    A --> B : uses

Relationships: <|-- inheritance, *-- composition, o-- aggregation, --> association{mermaid_output_rules}""",
            ArtifactType.MERMAID_STATE: f"""{base_message} Generate a State Diagram in Mermaid syntax.

STATE DIAGRAM SYNTAX:
stateDiagram-v2
    [*] --> State1
    State1 --> State2 : trigger
    State2 --> [*]
    state State1 {{
        [*] --> SubState
    }}

Use [*] for start/end, --> for transitions.{mermaid_output_rules}""",
            ArtifactType.MERMAID_FLOWCHART: f"""{base_message} Generate a Flowchart in Mermaid syntax.

FLOWCHART SYNTAX:
flowchart TD
    A[Start] --> B{{Decision}}
    B -->|Yes| C[Process]
    B -->|No| D[Other]
    C --> E[End]
    D --> E

Shapes: [text] rectangle, (text) rounded, {{text}} diamond, [(text)] stadium.
Arrows: --> solid, -.-> dotted, ==> thick.
Labels: -->|label| (NOT |>).{mermaid_output_rules}""",
            ArtifactType.MERMAID_DATA_FLOW: f"{base_message} Generate a Data Flow Diagram in Mermaid syntax. Show processes, data stores, external entities, and data flows.{mermaid_output_rules}",
            ArtifactType.MERMAID_USER_FLOW: f"{base_message} Generate a User Flow Diagram in Mermaid syntax. Show user actions, decision points, and flow paths.{mermaid_output_rules}",
            ArtifactType.MERMAID_COMPONENT: f"{base_message} Generate a Component Diagram in Mermaid syntax. Show components, interfaces, and dependencies.{mermaid_output_rules}",
            ArtifactType.MERMAID_GANTT: f"""{base_message} Generate a Gantt Chart in Mermaid syntax.

VALID GANTT SYNTAX - FOLLOW EXACTLY:
gantt
    title Project Timeline
    dateFormat YYYY-MM-DD
    section Phase Name
    Task Name :taskid, 2024-01-01, 5d
    Another Task :task2, after taskid, 3d

CRITICAL RULES:
1. Task format: "Task Name :taskId, startDate, duration" OR "Task Name :taskId, after otherId, duration"
2. Duration MUST be number + unit (1d, 2w, 3h)
3. Use "after taskId" for dependencies
4. NEVER use "depend on" or "depends on" - this is INVALID
5. NEVER use "dependencies:" as a line - use "section Dependencies" instead

❌ INVALID (DO NOT GENERATE):
- "Task depend on Other: 1d"
- "dependencies: UX Team"
- "UX Team depend on wireframe approval"

✅ VALID (GENERATE THIS):
- "UX Review :uxreview, after wireframe, 1d"
- "section Dependencies"
- "Wireframe Design :wireframe, 2024-01-01, 5d"

{mermaid_output_rules}""",
            ArtifactType.MERMAID_PIE: f"{base_message} Generate a Pie Chart in Mermaid syntax with proper data visualization.{mermaid_output_rules}",
            ArtifactType.MERMAID_JOURNEY: f"{base_message} Generate a User Journey Map in Mermaid syntax showing user experience stages.{mermaid_output_rules}",
            ArtifactType.MERMAID_MINDMAP: f"{base_message} Generate a Mindmap in Mermaid syntax with hierarchical structure.{mermaid_output_rules}",
            ArtifactType.MERMAID_GIT_GRAPH: f"{base_message} Generate a Git Graph in Mermaid syntax showing branch structure.{mermaid_output_rules}",
            ArtifactType.MERMAID_TIMELINE: f"{base_message} Generate a Timeline in Mermaid syntax with chronological events.{mermaid_output_rules}",
            ArtifactType.MERMAID_SYSTEM_OVERVIEW: f"{base_message} Generate a System Overview Diagram in Mermaid syntax showing high-level system architecture.{mermaid_output_rules}",
            ArtifactType.MERMAID_API_SEQUENCE: f"{base_message} Generate an API Sequence Diagram in Mermaid syntax showing API calls and responses.{mermaid_output_rules}",
            ArtifactType.MERMAID_UML: f"{base_message} Generate a UML Diagram in Mermaid syntax following UML standards.{mermaid_output_rules}",
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
        
        def _add_cloud_provider_if_valid(model_id: str) -> bool:
            """Helper to add a cloud provider if the model_id is a cloud model with valid API key."""
            if ":" not in model_id:
                return False
            provider, model_name = model_id.split(":", 1)
            # Skip local models (Ollama/HuggingFace)
            if provider in ["ollama", "huggingface"]:
                return False
            # Check if API key is available for this provider
            if provider == "gemini" and (settings.google_api_key or settings.gemini_api_key):
                cloud_providers.append((provider, model_name))
                return True
            elif provider == "groq" and settings.groq_api_key:
                cloud_providers.append((provider, model_name))
                return True
            elif provider == "openai" and settings.openai_api_key:
                cloud_providers.append((provider, model_name))
                return True
            elif provider == "anthropic" and settings.anthropic_api_key:
                cloud_providers.append((provider, model_name))
                return True
            return False
        
        # FIRST: Check if routing.primary_model is a cloud model (user's explicit choice)
        if routing and routing.primary_model:
            if _add_cloud_provider_if_valid(routing.primary_model):
                logger.info(f"📋 [CLOUD_FALLBACK] Using user's primary_model as cloud provider: {routing.primary_model}")
        
        # SECOND: Extract cloud models from routing fallback_models
        if routing and routing.fallback_models:
            for model_id in routing.fallback_models:
                # Skip if already added (e.g., primary_model was same as a fallback)
                if ":" in model_id:
                    provider, model_name = model_id.split(":", 1)
                    if (provider, model_name) not in cloud_providers:
                        _add_cloud_provider_if_valid(model_id)
        
        # Add default cloud models ONLY if routing didn't provide any cloud models
        # This respects the user's model mapping configuration
        # Updated Jan 2026 - Use latest stable models (Official Google AI)
        if not cloud_providers:
            logger.info("📋 [CLOUD_FALLBACK] No cloud models in routing, using defaults")
            if settings.google_api_key or settings.gemini_api_key:
                cloud_providers.append(("gemini", "gemini-2.5-flash"))  # Best price-performance
            if settings.groq_api_key:
                cloud_providers.append(("groq", "llama-3.3-70b-versatile"))
            if settings.openai_api_key:
                cloud_providers.append(("openai", "gpt-4o"))  # Latest GPT-4o
            if settings.anthropic_api_key:
                cloud_providers.append(("anthropic", "claude-sonnet-4-20250514"))  # Claude 4
        
        logger.info(f"☁️ [CLOUD_FALLBACK] Cloud providers to try: {cloud_providers}")
        
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
                    artifact_type=artifact_type,
                    custom_prompt_template=custom_prompt_template
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
    
    async def _try_single_cloud_model(
        self,
        provider: str,
        model_name: str,
        artifact_type: Union[ArtifactType, str],
        meeting_notes: str,
        assembled_context: str,
        context: Dict[str, Any],
        threshold: float,
        progress_callback: Optional[callable] = None,
        custom_prompt_template: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Try a single specific cloud model (user's preferred model from routing).
        
        This is called when the user has explicitly configured a cloud model
        as their primary model for an artifact type.
        
        Args:
            provider: Cloud provider (gemini, groq, openai, anthropic)
            model_name: Model name
            artifact_type: Type of artifact to generate
            meeting_notes: User requirements
            assembled_context: RAG context
            context: Full context dict
            threshold: Validation score threshold
            progress_callback: Optional progress callback
            custom_prompt_template: Optional custom prompt template
        
        Returns:
            Generation result dict or None if failed
        """
        # Check if API key is available for this provider
        has_key = False
        if provider == "gemini" and (settings.google_api_key or settings.gemini_api_key):
            has_key = True
        elif provider == "groq" and settings.groq_api_key:
            has_key = True
        elif provider == "openai" and settings.openai_api_key:
            has_key = True
        elif provider == "anthropic" and settings.anthropic_api_key:
            has_key = True
        
        if not has_key:
            logger.warning(f"⚠️ [ENHANCED_GEN] No API key for {provider}, cannot use preferred model {model_name}")
            return None
        
        try:
            logger.info(f"☁️ [ENHANCED_GEN] Trying user's preferred cloud model: {provider}:{model_name}")
            
            if progress_callback:
                await progress_callback(40.0, f"Generating with your preferred model: {provider}:{model_name}...")
            
            # Call cloud API (pass custom_prompt_template if available)
            content = await self._call_cloud_api(
                provider=provider,
                model_name=model_name,
                meeting_notes=meeting_notes,
                rag_context=assembled_context,
                artifact_type=artifact_type,
                custom_prompt_template=custom_prompt_template
            )
            
            if not content:
                logger.warning(f"⚠️ [ENHANCED_GEN] Cloud model {provider}:{model_name} returned no content")
                return None
            
            # Validate
            if progress_callback:
                await progress_callback(70.0, f"Validating output from {provider}:{model_name}...")
            
            validation_result = await self.validation_service.validate_artifact(
                artifact_type=artifact_type,
                content=content,
                meeting_notes=meeting_notes,
                context=context
            )
            
            score = validation_result.score
            is_valid = validation_result.is_valid and score >= threshold
            
            # Generate artifact ID
            artifact_id = f"{artifact_type_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if is_valid:
                if progress_callback:
                    await progress_callback(90.0, f"Generation successful with {provider}:{model_name}! (Score: {score:.1f})")
                
                return {
                    "success": True,
                    "content": content,
                    "model_used": model_name,
                    "provider": provider,
                    "validation_score": score,
                    "is_valid": True,
                    "artifact_id": artifact_id,
                    "attempts": 1
                }
            else:
                logger.warning(f"⚠️ [ENHANCED_GEN] Cloud model {provider}:{model_name} output failed validation (score: {score:.1f})")
                return None
                
        except Exception as e:
            logger.error(f"❌ [ENHANCED_GEN] Error with user's preferred cloud model {provider}:{model_name}: {e}")
            return None
    
    async def _call_cloud_api(
        self,
        provider: str,
        model_name: str,
        meeting_notes: str,
        rag_context: str,
        artifact_type: Union[ArtifactType, str],
        custom_prompt_template: Optional[str] = None
    ) -> Optional[str]:
        """
        Call cloud API directly for artifact generation.
        
        This is called as a cloud fallback AFTER local models have failed.
        We go directly to cloud API calls to avoid infinite loops through
        SmartGenerationOrchestrator (which would try local models again).
        
        Args:
            provider: Cloud provider (gemini, groq, openai, anthropic)
            model_name: Model name
            meeting_notes: User requirements
            rag_context: RAG context
            artifact_type: Type of artifact to generate
            custom_prompt_template: Optional custom prompt template for custom artifact types
        
        Returns:
            Generated content or None on failure
        """
        # Get artifact type string
        artifact_type_str = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
        
        try:
            # Build prompt with full context (use custom template if available)
            prompt = self._build_prompt(meeting_notes, rag_context, artifact_type, custom_prompt_template)
            system_message = self._get_system_message(artifact_type)
            
            logger.info(f"☁️ [CLOUD_API] Calling {provider}:{model_name} directly for {artifact_type_str}")
            logger.debug(f"☁️ [CLOUD_API] Prompt length: {len(prompt)}, System message length: {len(system_message)}")
            
            # Call cloud API directly - this is a fallback path, skip orchestrators
            content = await self._call_cloud_api_direct(provider, model_name, prompt, system_message)
            
            if content:
                logger.info(f"✅ [CLOUD_API] {provider}:{model_name} generated {len(content)} chars")
            else:
                logger.warning(f"⚠️ [CLOUD_API] {provider}:{model_name} returned no content")
            
            return content
            
        except Exception as e:
            logger.error(f"❌ [CLOUD_API] Error calling {provider}:{model_name}: {e}", exc_info=True)
            return None
    
    async def _call_cloud_api_direct(
        self,
        provider: str,
        model_name: str,
        prompt: str,
        system_message: str,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> Optional[str]:
        """
        Direct cloud API calls with retry logic and exponential backoff.
        
        Features:
        - Exponential backoff for rate limit errors (429)
        - Automatic retry on transient failures
        - Proper error classification and logging
        
        Args:
            provider: Cloud provider name
            model_name: Model name to use
            prompt: User prompt
            system_message: System instruction
            max_retries: Maximum retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        
        Returns:
            Generated content or None on failure
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return await self._execute_cloud_api_call(provider, model_name, prompt, system_message)
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check if this is a rate limit error (429)
                is_rate_limit = (
                    "429" in error_str or 
                    "rate limit" in error_str or 
                    "quota exceeded" in error_str or
                    "resource exhausted" in error_str or
                    "too many requests" in error_str
                )
                
                # Check if this is a transient error worth retrying
                is_transient = (
                    is_rate_limit or
                    "timeout" in error_str or
                    "connection" in error_str or
                    "503" in error_str or
                    "502" in error_str
                )
                
                if is_rate_limit:
                    logger.warning(f"⚠️ [CLOUD_API] Rate limit hit for {provider}:{model_name} (attempt {attempt + 1}/{max_retries + 1})")
                    metrics.increment("cloud_api_rate_limits", tags={"provider": provider})
                
                if is_transient and attempt < max_retries:
                    # Calculate exponential backoff delay
                    delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s, 8s...
                    
                    # Add jitter to prevent thundering herd
                    import random
                    jitter = random.uniform(0, delay * 0.1)
                    delay += jitter
                    
                    logger.info(f"🔄 [CLOUD_API] Retrying {provider}:{model_name} in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Non-transient error or max retries exceeded
                    logger.error(f"❌ [CLOUD_API] {provider}:{model_name} failed after {attempt + 1} attempts: {e}")
                    
                    # Log error details for debugging
                    log_error_to_file(
                        error=e,
                        context={
                            "provider": provider,
                            "model_name": model_name,
                            "attempt": attempt + 1,
                            "is_rate_limit": is_rate_limit,
                            "operation": "cloud_api_call"
                        },
                        module="enhanced_generation",
                        function="_call_cloud_api_direct"
                    )
                    break
        
        # All retries exhausted - return None to trigger failover to next provider
        if last_error:
            logger.warning(f"⚠️ [CLOUD_API] All retries exhausted for {provider}:{model_name}, will failover to next provider")
        
        return None
    
    async def _execute_cloud_api_call(
        self,
        provider: str,
        model_name: str,
        prompt: str,
        system_message: str
    ) -> Optional[str]:
        """Execute a single cloud API call without retry logic."""
        if provider == "gemini" and (settings.google_api_key or settings.gemini_api_key):
            import google.generativeai as genai
            api_key = settings.google_api_key or settings.gemini_api_key
            if not api_key:
                logger.warning("Gemini API key not found in settings")
                return None
            
            genai.configure(api_key=api_key)
            # Extract model name if it includes provider prefix (e.g., "gemini-2.0-flash-exp" from "gemini:gemini-2.0-flash-exp")
            actual_model_name = model_name.split(":")[-1] if ":" in model_name else model_name
            # Map model names to actual Gemini model IDs (Updated Jan 2026 - Official Google AI)
            model_mapping = {
                # Gemini 3 (Latest Preview - Nov/Dec 2025)
                "gemini-3-pro-preview": "gemini-3-pro-preview",
                "gemini-3-flash-preview": "gemini-3-flash-preview",
                # Gemini 2.5 (Stable - June/July 2025)
                "gemini-2.5-pro": "gemini-2.5-pro",
                "gemini-2.5-flash": "gemini-2.5-flash",
                "gemini-2.5-flash-lite": "gemini-2.5-flash-lite",
                # Gemini 2.0 (Previous Gen)
                "gemini-2.0-flash": "gemini-2.0-flash",
                "gemini-2.0-flash-lite": "gemini-2.0-flash-lite",
                # Legacy aliases (redirect to current stable)
                "gemini-2.0-flash-exp": "gemini-2.5-flash",  # Redirect to 2.5
                "gemini-1.5-pro": "gemini-2.5-pro",  # Deprecated → 2.5 Pro
                "gemini-1.5-flash": "gemini-2.5-flash",  # Deprecated → 2.5 Flash
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
                max_tokens=settings.cloud_api_max_tokens,
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
            # Map Groq model names (Updated Jan 2026)
            model_mapping = {
                # Llama 3.3 (Latest)
                "llama-3.3-70b-versatile": "llama-3.3-70b-versatile",
                "llama-3.3-70b-specdec": "llama-3.3-70b-specdec",
                # Llama 3.2 (Multimodal)
                "llama-3.2-90b-vision-preview": "llama-3.2-90b-vision-preview",
                "llama-3.2-11b-vision-preview": "llama-3.2-11b-vision-preview",
                # Mixtral
                "mixtral-8x7b-32768": "mixtral-8x7b-32768",
                # Legacy aliases
                "llama-3.1-70b-versatile": "llama-3.3-70b-versatile",  # Redirect to 3.3
                "llama-3.1-8b-instant": "llama-3.3-70b-specdec",  # Redirect to 3.3 fast
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
    for model_name in models_to_try:
        if local_attempts >= max_local_attempts:
            logger.info(f"⏭️ [ENHANCED_GEN] Reached max local attempts ({max_local_attempts}), moving to cloud")
            break
        
        # Determine provider
        provider = "ollama"  # default
        hf_model_id = None
        if ":" in model_name:
            provider, model_name = model_name.split(":", 1)
            if provider == "huggingface":
                hf_model_id = model_name.replace("-", "/")
        
        local_attempts += 1
        try:
            logger.info(f"🤖 [ENHANCED_GEN] Trying local model: {model_name} ({provider}) (attempt {local_attempts}/{max_local_attempts})")
            
            # Generate based on provider
            if provider == "ollama" and self.ollama_client:
                # Ensure model is available
                await self.ollama_client.ensure_model_available(model_name)
                
                # Generate with timeout and context window from config
                try:
                    import asyncio
                    response = await asyncio.wait_for(
                        self.ollama_client.generate(
                            model_name=model_name,
                            prompt=prompt,
                            system_message=system_instruction,
                            temperature=temperature,
                            num_ctx=settings.local_model_context_window  # From centralized config
                        ),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ [ENHANCED_GEN] Timeout after {timeout_seconds}s with {model_name}")
                    continue
            elif provider == "huggingface" and self.hf_client:
                # Use HuggingFace client
                try:
                    import asyncio
                    hf_response = await asyncio.wait_for(
                        self.hf_client.generate(
                            model_id=hf_model_id or model_name,
                            prompt=prompt,
                            system_message=system_instruction,
                            temperature=temperature
                        ),
                        timeout=timeout_seconds
                    )
                    # Convert to Ollama-like response
                    from ai.ollama_client import GenerationResponse as OllamaResponse
                    response = OllamaResponse(
                        content=hf_response.content,
                        model_used=hf_response.model_used,
                        generation_time=hf_response.generation_time,
                        tokens_generated=hf_response.tokens_generated,
                        success=hf_response.success,
                        error_message=hf_response.error_message
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ [ENHANCED_GEN] Timeout after {timeout_seconds}s with HuggingFace {model_name}")
                    continue
            else:
                logger.debug(f"⏭️ [ENHANCED_GEN] Skipping {model_name} ({provider}) - client not available")
                continue
            
            if response.success and response.content:
                logger.info(f"✅ [ENHANCED_GEN] Success with {model_name}: content_length={len(response.content)}")
                return GenerationResult(
                    content=response.content,
                    model_used=f"{provider}:{model_name}" if provider != "ollama" else model_name,
                    success=True
                )
            else:
                logger.warning(f"⚠️ [ENHANCED_GEN] {model_name} returned no content")
                
        except Exception as e:
            logger.warning(f"⚠️ [ENHANCED_GEN] Error with {model_name}: {e}")
            continue
    
    # Try cloud models as fallback
    # Prioritize cloud models from routing, then default providers (Updated Jan 2026 - Official)
    default_cloud_providers = [
        ("gemini", "gemini-2.5-flash"),  # Best price-performance (stable)
        ("groq", "llama-3.3-70b-versatile"),  # Latest Llama
        ("openai", "gpt-4o"),  # Latest GPT-4o
        ("anthropic", "claude-sonnet-4-20250514"),  # Claude 4
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

