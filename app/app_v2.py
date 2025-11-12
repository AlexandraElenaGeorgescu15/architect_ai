"""
Architect.AI - Production-Ready Dual-Mode AI Architecture Assistant

A sophisticated AI-powered system that transforms meeting notes and repository context
into production-ready artifacts. Designed for developers and product managers who want
to move fast without breaking things.

TWO MODES:
1. Developer Mode: Technical artifacts (ERD, architecture, code, API docs, JIRA, workflows)
2. Product/PM Mode: Visual prototypes, feasibility validation, PM power tools

CORE PRINCIPLES:
- RAG-First: Always retrieve repository context before generating
- Feature-Focused: All outputs about the feature in meeting notes, not the app itself
- Stack-Aware: Detects and respects your project's tech stack and conventions
- Context-Driven: Uses your repo's architecture, patterns, and naming conventions

Version: 2.1.0
Author: Alexandra Georgescu (alestef81@gmail.com)
License: Proprietary - Internal use only
"""

import sys
from pathlib import Path

# Add parent directory to path (only if needed)
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Use centralized configuration for ChromaDB and environment
from config.settings import configure_chromadb_telemetry, load_environment
configure_chromadb_telemetry()
load_environment()

import streamlit as st
import asyncio
import json
import base64
import zlib
import time
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

# Import async utilities to fix event loop errors
from utils.async_utils import run_async
# Import artifact router for intelligent model selection
from ai.artifact_router import ArtifactRouter, ArtifactType
# Import output validator for quality assurance
from ai.output_validator import OutputValidator
# Import mermaid editor for interactive diagram editing
from components.mermaid_editor import render_mermaid_editor
# Import visual diagram editor for TRUE Miro-like diagram creation
from components.visual_diagram_editor import render_visual_diagram_editor

# Note: Auto-update architecture documentation feature was removed
# to prevent startup crashes. If needed, run manually via utils/architecture_updater.py

# Import the universal agent
from agents.universal_agent import UniversalArchitectAgent
# UI components - Import what's available, stub what's not
from components.prototype_generator import generate_best_effort
from components.metrics_dashboard import track_generation, render_metrics_dashboard
from components.rag_cache import get_rag_cache
from components.progress_tracker import progress_tracker, render_progress_bar, track_rag_retrieval, track_ai_generation, track_validation, track_file_operations
from components.mermaid_syntax_corrector import mermaid_corrector, render_mermaid_syntax_corrector, validate_mermaid_syntax
from components.mermaid_html_renderer import mermaid_html_renderer, render_mermaid_html_comparison_tab
from components.enhanced_api_docs import enhanced_api_docs_generator, render_enhanced_api_docs_tab
from components.enhanced_rag import enhanced_rag_system, render_enhanced_rag_tab
from components.parallel_processing import parallel_processing_system, render_parallel_processing_tab
# Note: Local fine-tuning system is imported dynamically in sidebar to avoid PEFT dependency at startup
from components.rate_limiter import get_rate_limiter

# Optional components with fallbacks
try:
    from components.code_editor import render_code_editor, render_multi_file_editor
except Exception:
    render_code_editor = None
    render_multi_file_editor = None

try:
    from components.test_generator import render_test_generator
except Exception:
    render_test_generator = None

try:
    from components.export_manager import render_export_manager
except Exception:
    render_export_manager = None

try:
    from components.interactive_prototype_editor import render_interactive_prototype_editor, render_quick_modification_buttons
except Exception:
    render_interactive_prototype_editor = None
    render_quick_modification_buttons = None

# No auth needed for single-user dev tool
AUTH_AVAILABLE = False
current_user = lambda: None
current_role = lambda: "Developer"
has_role = lambda roles: True
# Remove unnecessary features for dev tool
render_git_tools = None
render_collaboration = None
render_user_management = None
render_cleanup_tool = None
render_job_history = None
enqueue_job = None
render_publish_panel = None
render_prototype_editor = None

# Auto-resume interrupted training jobs on startup
# Note: Import happens once at module level, not on every Streamlit rerun
# Use globals() instead of __builtins__ to avoid dict vs module issues
if '_training_manager_imported' not in globals():
    try:
        from components.persistent_training import persistent_training_manager
        # Note: Auto-resume is disabled to prevent resource conflicts
        # Users can manually resume training via sidebar "🔄 Resume Training" section
        # This ensures only one training session runs at a time
        if '_training_init_logged' not in st.session_state:
            print("[INFO] Training manager initialized (auto-resume disabled)")
            st.session_state['_training_init_logged'] = True
        globals()['_training_manager_imported'] = True
    except Exception as e:
        if '_training_init_error_logged' not in st.session_state:
            print(f"[WARNING] Could not initialize training manager: {e}")
            st.session_state['_training_init_error_logged'] = True
        # Graceful degradation - app continues without training features
        globals()['_training_manager_imported'] = False

# Background job worker function for artifact generation
# Note: Runs in-process thread via components.jobs.enqueue_job

def job_generate_artifact(
    artifact_type: str,
    provider_key: str,
    provider_config_key: str,
    provider_label: str,
    meeting_notes: str,
    alternate_models: Optional[List[str]] = None,
    rag_suffix: str = "",
    force_refresh: bool = False,
    job_id: int = 0
) -> str:
    """
    Background job worker for artifact generation with unified context retrieval.
    
    ⚠️ THREAD SAFETY WARNING:
    This function runs in a background thread. Do NOT access st.session_state directly!
    Session state access from threads can cause race conditions and crashes.
    Use logging instead of session state for status updates.
    
    Uses a SINGLE RAG retrieval for all artifact types, avoiding duplication.
    Passes meeting_notes and retrieved context to all generators.
    
    Runs in-process thread via components.jobs.enqueue_job.
    Imports are done locally to avoid circular dependencies.
    
    NOW WITH COMPREHENSIVE FALLBACKS - NEVER FAILS UNEXPECTEDLY!
    """
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(parents=True, exist_ok=True)
    from agents.universal_agent import UniversalArchitectAgent
    from components.prototype_generator import generate_best_effort
    from utils.comprehensive_fallbacks import safe_rag, safe_ai, safe_file, safe_diagram, safe_html
    import asyncio
    import json
    
    # Start progress tracking
    task_name = f"Generate {artifact_type.replace('_', ' ').title()}"
    total_steps = 4  # RAG retrieval, AI generation, validation, file save
    task_id = progress_tracker.start_tracking(task_name, total_steps, f"Initializing {task_name}...")

    # ========== ARTIFACT ROUTING: AUTO-SELECT BEST MODEL ==========
    # If using Ollama, route to specialized model based on artifact type
    if provider_label == "Ollama (Local)":
        try:
            from ai.artifact_router import ArtifactRouter, ArtifactType
            router = ArtifactRouter()
            
            # Map artifact_type string to ArtifactType enum
            artifact_map = {
                'erd': ArtifactType.ERD,
                'architecture': ArtifactType.ARCHITECTURE,
                'system_overview': ArtifactType.ARCHITECTURE,
                'data_flow': ArtifactType.ARCHITECTURE,
                'code_prototype': ArtifactType.CODE,
                'api_client_python': ArtifactType.CODE,
                'api_client_typescript': ArtifactType.CODE,
                'visual_prototype_dev': ArtifactType.HTML,
                'api_docs': ArtifactType.DOCUMENTATION,
                'jira': ArtifactType.DOCUMENTATION,
                'workflows': ArtifactType.DOCUMENTATION,
            }
            
            if artifact_type in artifact_map:
                optimal_model = router.route_artifact(artifact_map[artifact_type])
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Routing {artifact_type} → {optimal_model}")
                # Update provider config to use optimal model
                # Note: This requires the agent to support dynamic model switching
                # For now, we log it for visibility
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️  No specialized routing for {artifact_type}, using default")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Artifact routing failed: {e}")

    agent = UniversalArchitectAgent({provider_config_key: provider_key})
    agent.meeting_notes = meeting_notes

    # ========== STEP 1: UNIFIED RAG RETRIEVAL WITH MODEL AWARENESS ==========
    track_rag_retrieval(task_id, 1, f"Retrieving context for {artifact_type}...")
    rag_query = f"{artifact_type} {meeting_notes} {rag_suffix}".strip()

    # Check if Enhanced RAG is enabled (default: True)
    # NOTE: Accessing session_state in thread is UNSAFE, but .get() with default is read-only and safer
    use_enhanced = st.session_state.get('use_enhanced_rag', True) if hasattr(st, 'session_state') else True

    # Auto-detect task type: GENERATION (always for artifact generation)
    # Fine-tuning is handled separately in local_finetuning.py
    from components.enhanced_rag import TaskType
    task_type = TaskType.GENERATION

    # Get intelligent RAG configuration based on task type and model
    # ========== INTELLIGENT RAG CONFIGURATION ==========
    # Always use GENERATION for artifact creation tasks
    resolved_label = provider_label or provider_config_key
    rag_config = enhanced_rag_system.get_optimal_config(resolved_label, TaskType.GENERATION, alternate_models)

    max_chunks = rag_config["max_chunks"]
    context_window = rag_config["context_window"]
    chunk_source = f"{resolved_label} ({rag_config['reason']})"

    # Log intelligent decision (using print instead of session_state for thread safety)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Intelligent RAG: {max_chunks} chunks, {context_window:,} tokens ({rag_config['reason']})")
    
    # Retrieve context ONCE - to be used for ALL generators
    retrieved_context = None
    context_metadata = {}
        
    try:
        if use_enhanced:
            enhanced_context = run_async(
                enhanced_rag_system.retrieve_enhanced_context(
                    rag_query, 
                    model_name=rag_config.get('resolved_model_name', resolved_label),
                    max_chunks=max_chunks,  # ✅ DYNAMIC
                    strategy="tiered"
                )
            )
            
            # Store enhanced context in agent
            agent.enhanced_rag_context = enhanced_context
            retrieved_context = enhanced_context.context_text if hasattr(enhanced_context, 'context_text') else str(enhanced_context)
            context_metadata = {
                'chunks': enhanced_context.total_chunks,
                'tokens': enhanced_context.total_tokens,
                'quality': enhanced_context.quality_score,
                'source': f'enhanced ({chunk_source})',
                'model': resolved_label,
                'context_window': context_window
            }
            
            # Log to console (thread-safe)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🧠 Enhanced RAG: {enhanced_context.total_chunks} chunks, {enhanced_context.total_tokens} tokens, quality: {enhanced_context.quality_score:.2f}")
        else:
            # Use standard RAG with model-aware limits
            run_async(agent.retrieve_rag_context(rag_query, force_refresh=force_refresh))
            retrieved_context = agent.rag_context
            standard_chunks = min(18, max_chunks) if max_chunks else 18
            context_metadata = {
                'chunks': standard_chunks,
                'source': f'standard ({chunk_source})',
                'model': resolved_label,
                'context_window': context_window
            }
            
            # Log to console (thread-safe)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 📚 Standard RAG: {standard_chunks} chunks from {chunk_source}")

    except Exception as e:
        # Fallback to original RAG
        run_async(agent.retrieve_rag_context(rag_query, force_refresh=force_refresh))
        retrieved_context = agent.rag_context
        context_metadata = {
                'chunks': 18,
                'source': f'fallback',
            'model': resolved_label,
                'context_window': context_window
            }
        
        # Log to console (thread-safe)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Enhanced RAG failed, using fallback: {str(e)[:50]}")

        # ========== STEP 2: AI GENERATION (WITH UNIFIED CONTEXT) ==========
        track_ai_generation(task_id, 2, f"Generating {artifact_type} with AI...")
        
        # Generate and save based on artifact type
        result_path = ""
        
        # Check if using Ollama and should fall back to cloud on validation failure
        use_ollama = provider_label == "Ollama (Local)"
        force_local_only = False  # Can't access session state in background thread
        
        if artifact_type == "erd":
            # Use thread-safe validation
            def generate_erd():
                return run_async(agent.generate_erd_only(artifact_type="erd"))
            
            res = generate_with_validation_silent(
                "erd",
                generate_erd,
                meeting_notes,
                outputs_dir
            )
            
            # 🚀 REMOVED OLD CLOUD FALLBACK - Smart generator handles it internally
            
            if res:
                p = outputs_dir / "visualizations" / "erd_diagram.mmd"
                p.parent.mkdir(exist_ok=True)
                p.write_text(res, encoding='utf-8')
                result_path = str(p)
        elif artifact_type == "all_diagrams":
            diagrams = run_async(agent.generate_specific_diagrams())
            if diagrams:
                viz = outputs_dir / "visualizations"
                viz.mkdir(exist_ok=True)
                for name, content in diagrams.items():
                    p = viz / f"{name}_diagram.mmd"
                    p.write_text(content, encoding='utf-8')
                    result_path = str(p)
        elif artifact_type == "api_docs":
            # Use enhanced API docs generator with context
            try:
                enhanced_docs = run_async(
                    enhanced_api_docs_generator.generate_enhanced_api_docs(
                        rag_query, 
                        meeting_notes,  # ✅ PASS MEETING NOTES
                        "web"
                    )
                )
                
                # Generate markdown content
                markdown_content = f"""# {enhanced_docs.title} API Documentation

**Version:** {enhanced_docs.version}  
**Base URL:** {enhanced_docs.base_url}  
**Generated:** {enhanced_docs.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
**Context:** {context_metadata['chunks']} chunks, {context_metadata.get('tokens', 'unknown')} tokens

## Description
{enhanced_docs.description}

## Authentication
- **Type:** {enhanced_docs.authentication.get('type', 'Bearer Token')}
- **Description:** {enhanced_docs.authentication.get('description', 'API key required')}

## Rate Limits
- **Requests per minute:** {enhanced_docs.rate_limits.get('requests_per_minute', 100)}
- **Requests per hour:** {enhanced_docs.rate_limits.get('requests_per_hour', 1000)}

## Endpoints
"""
                
                for endpoint in enhanced_docs.endpoints:
                    markdown_content += f"""
### {endpoint.method} {endpoint.path}
- **Summary:** {endpoint.summary}
- **Description:** {endpoint.description}
"""
                
                # Save markdown
                p = outputs_dir / "documentation" / "enhanced_api_docs.md"
                p.parent.mkdir(exist_ok=True)
                p.write_text(markdown_content, encoding='utf-8')
                result_path = str(p)
                
                # Also save OpenAPI spec
                openapi_spec = enhanced_api_docs_generator.generate_openapi_spec(enhanced_docs)
                openapi_path = outputs_dir / "documentation" / "api_spec.json"
                openapi_path.write_text(json.dumps(openapi_spec, indent=2), encoding='utf-8')
                
            except Exception as e:
                # Fallback to agent's generate_api_docs_only (has its own RAG retrieval)
                try:
                    res = run_async(agent.generate_api_docs_only())
                    if res:
                        p = outputs_dir / "documentation" / "api.md"
                        p.parent.mkdir(exist_ok=True)
                        p.write_text(res, encoding='utf-8')
                        result_path = str(p)
                    # Log to console (thread-safe)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Enhanced API Docs failed, using standard generator: {str(e)[:50]}")
                except Exception as fallback_exc:
                    # Log to console (thread-safe)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Both enhanced and fallback API doc generation failed: {str(fallback_exc)[:50]}")
                    result_path = str(p)
        elif artifact_type == "jira":
            # JIRA generation with validation
            try:
                def generate_jira():
                    return run_async(agent.generate_jira_only())
                
                res = generate_with_validation_silent(
                    "jira",
                    generate_jira,
                    meeting_notes,
                    outputs_dir
                )
                if res:
                    p = outputs_dir / "documentation" / "jira_tasks.md"
                    p.parent.mkdir(exist_ok=True)
                    # Add context metadata to JIRA output
                    full_content = f"""<!-- Generated with {context_metadata['chunks']} RAG chunks from repository -->
<!-- Meeting Notes: {meeting_notes[:100]}... -->

{res}"""
                    p.write_text(full_content, encoding='utf-8')
                    result_path = str(p)
            except Exception as e:
                # Log to console (thread-safe)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ JIRA generation failed: {str(e)[:50]}")
                result_path = None
        elif artifact_type == "workflows":
            # Workflows generation with validation
            try:
                def generate_workflows():
                    return run_async(agent.generate_workflows_only())
                
                res = generate_with_validation_silent(
                    "workflows",
                    generate_workflows,
                    meeting_notes,
                    outputs_dir
                )
                if res:
                    p = outputs_dir / "workflows" / "workflows.md"
                    p.parent.mkdir(exist_ok=True)
                    # Add context metadata to workflows output
                    full_content = f"""<!-- Generated with {context_metadata['chunks']} RAG chunks from repository -->
<!-- Meeting Notes: {meeting_notes[:100]}... -->

{res}"""
                    p.write_text(full_content, encoding='utf-8')
                    result_path = str(p)
            except Exception as e:
                # Log to console (thread-safe)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Workflows generation failed: {str(e)[:50]}")
                result_path = None
        elif artifact_type == "code_prototype":
            # Code prototype generation with validation
            try:
                def generate_code():
                    res = run_async(agent.generate_prototype_code("feature-from-notes"))
                    if res and isinstance(res, dict) and "code" in res:
                        return res["code"]
                    return None
                
                code_content = generate_with_validation_silent(
                    "code_prototype",
                    generate_code,
                    meeting_notes,
                    outputs_dir
                )
                if code_content:
                    p = outputs_dir / "prototypes" / "prototype_code.txt"
                    p.parent.mkdir(exist_ok=True)
                    p.write_text(code_content, encoding='utf-8')
                    result_path = str(p)
                    
                    # Log completion (thread-safe print instead of session_state)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Code prototype saved! Job #{job_id} complete.")
                else:
                    result_path = None
            except Exception as e:
                # Log to console (thread-safe)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Code prototype generation failed: {str(e)[:50]}")
                result_path = None
        elif artifact_type == "visual_prototype_dev":
            def generate_visual():
                return run_async(agent.generate_visual_prototype("developer-feature"))
            
            res = generate_with_validation_silent(
                "visual_prototype_dev",
                generate_visual,
                meeting_notes,
                outputs_dir
            )
            if res:
                p = outputs_dir / "prototypes" / "developer_visual_prototype.html"
                p.parent.mkdir(exist_ok=True)
                p.write_text(res, encoding='utf-8')
                
                # IMMEDIATE SESSION STATE SYNC - Update prototype tracking flags
                import streamlit as st
                import time
                st.session_state.prototype_last_modified = datetime.now().isoformat()
                st.session_state.dev_prototype_updated = True
                st.session_state.prototype_cache_buster_dev = st.session_state.get('prototype_cache_buster_dev', 0) + 1
                st.session_state.dev_prototype_force_mtime = time.time()
                
                result_path = str(p)
        elif artifact_type == "openapi":
            # Generate OpenAPI YAML via LLM with context
            prompt = f"""
You are an expert API designer. Generate a strict OpenAPI 3.1 YAML for the project's API.

MEETING NOTES / REQUIREMENTS:
{meeting_notes}

RAG CONTEXT (from repository):
{retrieved_context[:2000] if retrieved_context else "No RAG context available"}

Generate a complete OpenAPI 3.1 YAML with:
- info (title, version, description)
- servers (placeholder URL)
- tags
- paths with operations
- requestBodies with examples
- responses with schemas
- components/schemas

Output YAML only, no markdown formatting.
"""
            res = run_async(agent._call_ai(prompt, "Generate valid OpenAPI 3.1 YAML only.", artifact_type="openapi_spec"))
            if res:
                p = outputs_dir / "documentation" / "openapi.yaml"
                p.parent.mkdir(exist_ok=True)
                p.write_text(res, encoding='utf-8')
                result_path = str(p)
        elif artifact_type == "api_client_python":
            # Generate Python API client with context
            prompt = f"""
You are an expert Python engineer. Generate a production-ready Python API client.

MEETING NOTES / REQUIREMENTS:
{meeting_notes}

RAG CONTEXT (from repository):
{retrieved_context[:2000] if retrieved_context else "No RAG context available"}

Generate a complete Python API client that:
- Uses requests library
- Handles authentication with API tokens
- Includes timeout and retry logic
- Has typed dataclasses for requests/responses
- Raises for HTTP errors
- Includes docstrings

Output full .py code only, no markdown.
"""
            res = run_async(agent._call_ai(prompt, "Generate production-ready Python code only.", artifact_type="code_prototype"))
        if res:
            p = outputs_dir / "prototypes" / "api_client.py"
            p.parent.mkdir(exist_ok=True)
            p.write_text(res, encoding='utf-8')
            result_path = str(p)
        elif artifact_type == "api_client_typescript":
            # Generate TypeScript API client with context
            prompt = f"""
You are an expert TypeScript engineer. Generate a production-ready TypeScript API client.

MEETING NOTES / REQUIREMENTS:
{meeting_notes}

RAG CONTEXT (from repository):
{retrieved_context[:2000] if retrieved_context else "No RAG context available"}

Generate a complete TypeScript API client that:
- Uses fetch API with proper types
- Includes generic request/response handling
- Has comprehensive error handling
- Uses typed interfaces for all data
- Includes async/await patterns
- Has JSDoc documentation

Output full .ts code only, no markdown.
"""
            res = run_async(agent._call_ai(prompt, "Generate production-ready TypeScript code only.", artifact_type="code_prototype"))
            if res:
                p = outputs_dir / "prototypes" / "api_client.ts"
                p.parent.mkdir(exist_ok=True)
                p.write_text(res, encoding='utf-8')
                result_path = str(p)
        
        # ========== STEP 3: VALIDATE MERMAID & GENERATE HTML ==========
        if artifact_type in ["erd", "architecture", "all_diagrams"] and result_path:
            try:
                diagram_content = Path(result_path).read_text(encoding='utf-8')
                is_valid, corrected_diagram, errors = validate_mermaid_syntax(diagram_content)
                
                if not is_valid:
                    # Save corrected version
                    Path(result_path).write_text(corrected_diagram, encoding='utf-8')
                    # Log to console (thread-safe)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔧 Mermaid syntax corrected for {artifact_type}")
                
                # Generate HTML version with Gemini (context-aware with RAG)
                try:
                    # Use Gemini to generate context-aware HTML visualization with RAG context
                    html_content = run_async(
                        mermaid_html_renderer.generate_html_visualization_with_gemini(
                            corrected_diagram, 
                            meeting_notes,  # ✅ PASS MEETING NOTES
                            artifact_type,
                            retrieved_context,  # ✅ PASS RAG CONTEXT
                            agent=agent
                        )
                    )
                    html_path = result_path.replace('.mmd', '.html')
                    Path(html_path).write_text(html_content, encoding='utf-8')
                    # Log to console (thread-safe)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Gemini HTML visualization generated for {artifact_type}")
                except Exception as e:
                    # Fallback to basic HTML rendering
                    try:
                        html_content = mermaid_html_renderer.render_mermaid_as_html(corrected_diagram, f"{artifact_type}_diagram")
                        html_path = result_path.replace('.mmd', '.html')
                        Path(html_path).write_text(html_content, encoding='utf-8')
                        # Log to console (thread-safe)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎨 Basic HTML visualization generated for {artifact_type}")
                    except Exception as e2:
                        # Log to console (thread-safe)
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ HTML generation failed: {str(e2)[:50]}")
                    
            except Exception as e:
                # Log to console (thread-safe)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Mermaid validation failed: {str(e)[:50]}")
        
        # ========== STEP 4: FILE OPERATIONS ==========
        track_file_operations(task_id, 4, f"Saving {artifact_type} to disk...")
        
        # Complete progress tracking
        progress_tracker.complete_task(task_id, f"{artifact_type} generated successfully!")
        return result_path
    except Exception as e:
        progress_tracker.fail_task(task_id, f"Failed to generate {artifact_type}: {str(e)}")
        raise
    

# Helpers for RAG controls

def get_rag_suffix() -> str:
    return st.session_state.get('rag_suffix', '').strip()


def is_background_mode() -> bool:
    return bool(st.session_state.get('run_background', False))

# =============================================================================
# BEAUTIFUL UI CONFIGURATION
# =============================================================================

def apply_custom_css():
    """Apply beautiful Trimble brand styling - Original design with Trimble colors"""
    st.markdown("""
    <style>
    /* Trimble Brand Colors */
    :root {
        --trimble-blue: #0063A3;
        --trimble-blue-dark: #004F83;
        --trimble-blue-light: #217CBB;
        --trimble-yellow: #FBAD26;
        --trimble-gray: #252A2E;
        --success-color: #1E8A44;
        --warning-color: #FBAD26;
        --danger-color: #DA212C;
        --dark-bg: #1e1e2e;
        --card-bg: #2a2a3e;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container styling - Beautiful Trimble gradient */
    .main {
        background: linear-gradient(135deg, #0063A3 2%, #004F83 98%);
        padding: 0 !important;
        min-height: 100vh;
    }
    
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 100% !important;
        margin: 0 auto !important;
        background: transparent !important;
    }
    
    /* Responsive layout - adjust when sidebar is open */
    @media (min-width: 768px) {
        /* When sidebar is collapsed */
        [data-testid="collapsedControl"] ~ div .block-container {
            max-width: 100% !important;
        }
        /* When sidebar is open */
        .block-container {
            max-width: calc(100vw - 340px) !important;
        }
    }
    
    /* Ensure columns wrap properly */
    [data-testid="column"] {
        min-width: 0 !important;
    }
    
    /* Fix column alignment issues */
    .stColumns {
        gap: 1rem;
    }
    
    .stColumns > div {
        display: flex;
        flex-direction: column;
    }
    
    /* Main content text colors - All white for visibility */
    .main h1, .main h2, .main h3, .main h4 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    .main p, .main span, .main div, .main label {
        color: white !important;
    }
    
    .main strong {
        color: var(--trimble-yellow) !important;
    }
    
    /* Beautiful Trimble header */
    .app-header {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        text-align: center;
        animation: fadeIn 0.5s ease-in;
        border-bottom: 4px solid var(--trimble-yellow);
    }
    
    .app-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .app-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    
    /* Mode selector cards */
    .mode-card {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        cursor: pointer;
        border: 3px solid transparent;
    }
    
    .mode-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
        border-color: var(--trimble-blue);
    }
    
    .mode-card.selected {
        border-color: var(--trimble-blue);
        background: linear-gradient(135deg, rgba(0, 99, 163, 0.15) 0%, rgba(0, 79, 131, 0.15) 100%);
    }
    
    .mode-card h3 {
        color: #1f2937;
        font-weight: 700;
    }
    
    .mode-card p {
        color: #4b5563;
    }
    
    .mode-card ul {
        color: #6b7280;
    }
    
    .mode-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    
    /* Beautiful Trimble buttons */
    .stButton > button {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0, 99, 163, 0.4);
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 99, 163, 0.6);
    }
    
    /* Granular generation buttons */
    .granular-btn {
        background: white !important;
        color: var(--trimble-blue) !important;
        border: 2px solid var(--trimble-blue) !important;
    }
    
    .granular-btn:hover {
        background: var(--trimble-blue) !important;
        color: white !important;
    }
    
    /* Cards for content */
    .content-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .content-card h3, .content-card h4 {
        color: #1f2937 !important;
        font-weight: 700 !important;
    }
    
    .content-card p, .content-card li {
        color: #4b5563 !important;
    }
    
    /* Tabs styling - Better contrast with scrollbar support */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 10px;
        padding: 0.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        overflow-x: auto;
        overflow-y: hidden;
        max-width: 100%;
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
    }
    
    /* Scrollbar styling for tabs */
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        height: 8px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.05);
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {
        background: rgba(0, 99, 163, 0.5);
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 99, 163, 0.8);
    }
    
    /* Firefox scrollbar */
    .stTabs [data-baseweb="tab-list"] {
        scrollbar-color: rgba(0, 99, 163, 0.5) rgba(0, 0, 0, 0.05);
        scrollbar-width: thin;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #1f2937 !important;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(0, 99, 163, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #0063A3 0%, #217CBB 100%);
        color: white !important;
        box-shadow: 0 2px 8px rgba(0, 99, 163, 0.4);
    }
    
    /* Success/Info/Warning boxes - White text */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.95) !important;
    }
    
    .stSuccess {
        border-left: 5px solid var(--success-color);
    }
    
    .stInfo {
        border-left: 5px solid var(--trimble-blue-light);
    }
    
    .stWarning {
        border-left: 5px solid var(--warning-color);
    }
    
    .stError {
        border-left: 5px solid var(--danger-color);
    }
    
    /* Expander styling - White text for visibility */
    .streamlit-expanderHeader {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        font-weight: 600;
        color: white !important;
        border-left: 4px solid var(--trimble-yellow);
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    .streamlit-expanderHeader p {
        color: white !important;
    }
    
    .streamlit-expanderHeader svg {
        fill: white !important;
    }
    
    /* Metrics - Ensure text is visible */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.15);
        padding: 1rem;
        border-radius: 10px;
    }
    
    [data-testid="stMetricLabel"] {
        color: white !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: white !important;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    
    .animated {
        animation: slideIn 0.5s ease-in;
    }
    
    /* Code blocks */
    .stCodeBlock {
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
    
    /* File uploader - White background with white text */
    [data-testid="stFileUploader"] {
        border: 3px dashed rgba(255, 255, 255, 0.5);
        border-radius: 10px;
        padding: 2rem;
        background: rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: white;
        background: rgba(255, 255, 255, 0.15);
    }
    
    [data-testid="stFileUploader"] * {
        color: white !important;
    }
    
    /* Sidebar - Trimble gradient with fixed width */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0063A3 0%, #004F83 100%);
        min-width: 280px !important;
        max-width: 280px !important;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 {
        color: white !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
    }
    
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: white !important;
    }
    
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] textarea {
        background: white !important;
        color: var(--trimble-gray) !important;
    }
    
    /* Progress bars */
    .stProgress > div > div {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
    }
    
    /* Beautiful scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #0063A3 0%, #004F83 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--trimble-blue-light);
    }
    </style>
    """, unsafe_allow_html=True)

# =============================================================================
# EXTENDED CONTEXT HELPERS
# =============================================================================

def _read_text_safe(path: Path, limit: int = 4000) -> str:
    try:
        if path.exists() and path.is_file():
            return path.read_text(encoding='utf-8')[:limit]
    except Exception:
        return ""
    return ""


def get_extended_project_context(max_chars: int = 8000) -> str:
    """Collect extra project context: meeting notes, context docs, PR comments, READMEs."""
    parts = []
    base = Path(".")
    # Meeting notes
    notes = _read_text_safe(AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE, 6000)
    if notes:
        parts.append(f"# Meeting Notes\n{notes}")
    # Context important files
    ctx_dir = Path("architect_ai_cursor_poc") / "context"
    for name in [
        "_retrieved.md",
        "architecture.md",
        "conventions.md",
        "api_endpoints.md",
        "decisions_adr.md",
        "ready_done.md",
        "repo_tree.txt",
        "commit_log.md",
        "pr_recent.md",
    ]:
        parts.append(f"# {name}\n{_read_text_safe(ctx_dir / name, 4000)}")
    # Root READMEs
    for name in ["README.md", "README_V2.md", "START_HERE.md"]:
        parts.append(f"# {name}\n{_read_text_safe(Path('architect_ai_cursor_poc') / name, 3000)}")
    # Compose and trim
    blob = "\n\n".join([p for p in parts if p.strip()])
    return blob[:max_chars]

# =============================================================================
# CONFIGURATION
# =============================================================================

class AppConfig:
    """
    Application configuration constants.
    
    Centralizes all app-wide settings including UI configuration,
    file paths, and AI provider settings.
    """
    APP_TITLE = "Architect.AI v2.4 - Transform Ideas into Production-Ready Code"
    APP_ICON = "🏗️"
    APP_VERSION = "2.4.0"
    APP_AUTHOR = "Alexandra Georgescu"
    APP_CONTACT = "alestef81@gmail.com"
    LAYOUT = "wide"
    # Use absolute paths based on this file's location
    _APP_ROOT = Path(__file__).parent.parent  # architect_ai_cursor_poc/
    OUTPUTS_DIR = _APP_ROOT / "outputs"
    INPUTS_DIR = _APP_ROOT / "inputs"
    MEETING_NOTES_FILE = "meeting_notes.md"
    
    MIN_MEETING_NOTES_LENGTH = 80  # Minimum characters to consider notes meaningful
    
    # AI Model Providers
    AI_PROVIDERS = {
        "Ollama (Local)": {
            "name": "Ollama Local Models",
            "key_env": None,  # No API key needed
            "config_key": "ollama",
            "icon": "🖥️",
            "is_local": True
        },
        "Groq (FREE & FAST)": {
            "name": "Groq Llama 3.3",
            "key_env": "GROQ_API_KEY",
            "config_key": "groq_api_key",
            "icon": "⚡"
        },
        "Google Gemini (FREE)": {
            "name": "Gemini 2.0 Flash",
            "key_env": "GEMINI_API_KEY",
            "config_key": "gemini_api_key",
            "icon": "🤖"
        },
        "OpenAI GPT-4": {
            "name": "GPT-4",
            "key_env": "OPENAI_API_KEY",
            "config_key": "api_key",
            "icon": "🧠"
        }
    }


def is_local_provider(provider_name: Optional[str]) -> bool:
    """Determine if the selected provider represents a local fine-tuned model or Ollama."""
    if not provider_name:
        return False
    # Check for Ollama provider
    if provider_name == "Ollama (Local)":
        return True
    # Check for fine-tuned models
    return provider_name.startswith("🎓 Local:") or provider_name.endswith(" ✅")


def get_selected_local_model(provider_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Fetch metadata for the currently selected local model, if available."""
    if not provider_name:
        return None
    local_options = st.session_state.get('local_provider_options', {})
    return local_options.get(provider_name)


def resolve_provider_runtime() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Build runtime configuration for the currently selected AI provider."""
    provider = st.session_state.get('provider', 'Ollama (Local)')
    context: Dict[str, Any] = {
        "provider_label": provider
    }
    if is_local_provider(provider):
        # Check if it's Ollama (not fine-tuned)
        if provider == "Ollama (Local)":
            context.update({
                "provider_type": "ollama",
                "config": {
                    "ollama": True
                },
                "config_key": "ollama",
                "credential": "ollama_local",
                "ollama_enabled": True
            })
            return context, None
        
        # Fine-tuned local model
        local_model = get_selected_local_model(provider)
        if not local_model:
            return None, "Local model metadata missing. Re-select the model in the sidebar."
        context.update({
            "provider_type": "local",
            "config": {
                "local_model_path": local_model['model_path'],
                "local_model_name": local_model['model_name']
            },
            "config_key": "local_model_path",
            "credential": local_model['model_path'],
            "local_model": local_model
        })
        return context, None
    provider_info = AppConfig.AI_PROVIDERS.get(provider)
    if not provider_info:
        return None, f"Unsupported provider selected: {provider}"
    api_key = st.session_state.get('api_key') or os.getenv(provider_info['key_env'], "")
    if not api_key:
        return None, f"Missing API key for {provider_info['name']}. Configure it in the sidebar."
    if st.session_state.get('api_key') != api_key:
        st.session_state.api_key = api_key
    context.update({
        "provider_type": "remote",
        "config": {provider_info['config_key']: api_key},
        "config_key": provider_info['config_key'],
        "credential": api_key,
        "provider_info": provider_info
    })
    return context, None


def get_current_agent() -> Tuple[Optional['UniversalArchitectAgent'], Optional[Dict[str, Any]]]:
    """Return an initialized agent and its runtime context for the active provider."""
    runtime_context, error = resolve_provider_runtime()
    if error or not runtime_context:
        st.error(f"❌ {error}")
        return None, None
    agent = get_or_create_agent(runtime_context['config'])
    return agent, runtime_context

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """
    Initialize session state variables.
    
    Ensures ALL required session variables exist to prevent KeyError exceptions.
    Called once at app startup.
    
    State Categories:
    - Core: mode, api_key, provider
    - Logs & History: rag_logs, ai_conversation, last_generation
    - UI Flags: outputs_updated, dev_prototype_updated, pm_prototype_updated
    - Cache Busters: prototype_cache_buster_dev, prototype_cache_buster_pm
    - Timestamps: outputs_updated_time, prototype_last_modified, dev_prototype_force_mtime, pm_prototype_force_mtime
    - Agent: cached_agent, cached_agent_config
    - Features: use_multi_agent, use_validation, max_retries, use_enhanced_rag
    - System: auto_ingestion_initialized
    """
    # === CORE STATE ===
    if 'mode' not in st.session_state:
        st.session_state.mode = None
    if 'api_key' not in st.session_state:
        st.session_state.api_key = None
    if 'provider' not in st.session_state:
        st.session_state.provider = "Ollama (Local)"
    
    # === LOGS & HISTORY ===
    if 'rag_logs' not in st.session_state:
        st.session_state.rag_logs = []
    if 'ai_conversation' not in st.session_state:
        st.session_state.ai_conversation = []
    if 'last_generation' not in st.session_state:
        st.session_state.last_generation = []
    
    # === UI FLAGS (for notifications and updates) ===
    if 'outputs_updated' not in st.session_state:
        st.session_state.outputs_updated = False
    if 'outputs_updated_time' not in st.session_state:
        st.session_state.outputs_updated_time = None
    if 'dev_prototype_updated' not in st.session_state:
        st.session_state.dev_prototype_updated = False
    if 'pm_prototype_updated' not in st.session_state:
        st.session_state.pm_prototype_updated = False
    
    # === CACHE BUSTERS (deterministic, file-based) ===
    if 'prototype_cache_buster_dev' not in st.session_state:
        st.session_state.prototype_cache_buster_dev = 0
    if 'prototype_cache_buster_pm' not in st.session_state:
        st.session_state.prototype_cache_buster_pm = 0
    
    # === TIMESTAMPS ===
    if 'prototype_last_modified' not in st.session_state:
        st.session_state.prototype_last_modified = datetime.now().isoformat()
    if 'dev_prototype_force_mtime' not in st.session_state:
        st.session_state.dev_prototype_force_mtime = 0
    if 'pm_prototype_force_mtime' not in st.session_state:
        st.session_state.pm_prototype_force_mtime = 0
    
    # === MEETING NOTES ===
    if 'meeting_notes' not in st.session_state:
        st.session_state.meeting_notes = ""
    
    # === FEATURE FLAGS ===
    if 'use_multi_agent' not in st.session_state:
        st.session_state.use_multi_agent = False
    if 'use_validation' not in st.session_state:
        st.session_state.use_validation = True
    if 'max_retries' not in st.session_state:
        st.session_state.max_retries = 2
    if 'use_enhanced_rag' not in st.session_state:
        st.session_state.use_enhanced_rag = True
    
    # === AGENT CACHING ===
    if 'cached_agent' not in st.session_state:
        st.session_state.cached_agent = None
    if 'cached_agent_config' not in st.session_state:
        st.session_state.cached_agent_config = None
    
    # === SYSTEM STATE ===
    if 'auto_ingestion_initialized' not in st.session_state:
        st.session_state.auto_ingestion_initialized = False
    
    # === NOTIFICATION SYSTEM (toast-style, auto-clear) ===
    if 'notification_message' not in st.session_state:
        st.session_state.notification_message = None
    if 'notification_type' not in st.session_state:
        st.session_state.notification_type = None  # 'success', 'error', 'info', 'warning'
    if 'notification_timestamp' not in st.session_state:
        st.session_state.notification_timestamp = None


# =============================================================================
# NOTIFICATION SYSTEM (Toast-style, auto-clear)
# =============================================================================

def show_notification(message: str, notification_type: str = "success"):
    """
    Show a toast-style notification that auto-clears after 5 seconds.
    
    Args:
        message: Notification message to display
        notification_type: 'success', 'error', 'info', 'warning'
    
    Usage:
        show_notification("✅ Artifact generated!", "success")
    """
    st.session_state.notification_message = message
    st.session_state.notification_type = notification_type
    st.session_state.notification_timestamp = time.time()


def render_notifications():
    """
    Render active notifications and auto-clear after 5 seconds.
    Call this at the top of main content area.
    """
    if st.session_state.notification_message and st.session_state.notification_timestamp:
        # Check if notification is still fresh (< 5 seconds old)
        elapsed = time.time() - st.session_state.notification_timestamp
        
        if elapsed < 5.0:
            # Show notification
            notification_fn = {
                'success': st.success,
                'error': st.error,
                'info': st.info,
                'warning': st.warning
            }.get(st.session_state.notification_type, st.info)
            
            notification_fn(st.session_state.notification_message)
        else:
            # Clear expired notification
            st.session_state.notification_message = None
            st.session_state.notification_type = None
            st.session_state.notification_timestamp = None


def get_file_cache_buster(file_path: Path) -> str:
    """
    Generate deterministic cache buster based ONLY on file metadata.
    
    No random numbers - this is predictable and correct.
    Changes only when file actually changes.
    
    Args:
        file_path: Path to file
    
    Returns:
        Cache buster string (e.g., "1699123456_12345")
    """
    if not file_path.exists():
        return "0_0"
    
    stat = file_path.stat()
    # Use mtime (modification time) and size - both change when file is updated
    return f"{int(stat.st_mtime)}_{stat.st_size}"


def init_auto_ingestion():
    """
    Initialize the automatic RAG ingestion system.
    
    Starts the file watcher and background processing if enabled in configuration.
    Called once at app startup.
    """
    # Only initialize once per session
    if st.session_state.auto_ingestion_initialized:
        return
    
    try:
        from rag.auto_ingestion import get_auto_ingestion_manager
        
        # Get the manager and check if auto-ingestion is enabled
        manager = get_auto_ingestion_manager()
        
        if manager.enabled:
            # Start the auto-ingestion system
            success = manager.start()
            if success:
                st.session_state.rag_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Auto-ingestion system started"
                )
                # Show a success message in the UI (only on first load)
                if not st.session_state.get('auto_ingestion_started_shown', False):
                    st.success("🔄 Auto-ingestion system started automatically")
                    st.session_state.auto_ingestion_started_shown = True
            else:
                st.session_state.rag_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to start auto-ingestion system"
                )
                if not st.session_state.get('auto_ingestion_error_shown', False):
                    st.warning("⚠️ Failed to start auto-ingestion system")
                    st.session_state.auto_ingestion_error_shown = True
        else:
            st.session_state.rag_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ Auto-ingestion is disabled in configuration"
            )
    
    except Exception as e:
        # Silently fail if auto-ingestion components are not available
        error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
        st.session_state.rag_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Auto-ingestion not available: {error_msg}"
        )
        # Show a warning in the UI (only once)
        if not st.session_state.get('auto_ingestion_error_shown', False):
            st.warning(f"⚠️ Auto-ingestion not available: {error_msg}")
            st.session_state.auto_ingestion_error_shown = True
    
    # Mark as initialized
    st.session_state.auto_ingestion_initialized = True

# =============================================================================
# AGENT CACHING
# =============================================================================

def get_or_create_agent(config: Dict) -> 'UniversalArchitectAgent':
    """
    Get cached agent or create new one if config changed.
    
    This prevents re-initialization of RAG, multi-agent system,
    and other expensive resources on every generation.
    
    Args:
        config: AI provider configuration dict
    
    Returns:
        Cached or new UniversalArchitectAgent instance
    """
    # Generate config hash to detect changes
    import hashlib
    config_hash = hashlib.md5(str(sorted(config.items())).encode()).hexdigest()
    
    # Check if we have a cached agent with same config
    if (st.session_state.cached_agent is not None and 
        st.session_state.cached_agent_config == config_hash):
        return st.session_state.cached_agent
    
    # Create new agent
    agent = UniversalArchitectAgent(config)
    
    # Cache it
    st.session_state.cached_agent = agent
    st.session_state.cached_agent_config = config_hash
    
    # Log agent initialization (safe access)
    config_name = list(config.keys())[0] if config and config.keys() else "unknown"
    st.session_state.rag_logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Agent initialized (config: {config_name})"
    )
    
    return agent

def retrieve_rag_with_cache(agent: 'UniversalArchitectAgent', meeting_notes: str, force_refresh: bool = False) -> str:
    """
    Retrieve RAG context with intelligent caching.
    
    Caches RAG results per meeting notes hash to avoid redundant expensive queries.
    This provides 60-70% reduction in RAG API calls.
    
    Args:
        agent: UniversalArchitectAgent instance
        meeting_notes: Meeting notes content
        force_refresh: Force fresh retrieval, bypass cache
    
    Returns:
        RAG context string
    """
    import asyncio
    
    rag_cache = get_rag_cache()
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_context = rag_cache.get(meeting_notes)
        if cached_context:
            agent.rag_context = cached_context
            st.session_state.rag_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 💾 RAG cache HIT ({len(cached_context)} chars)"
            )
            return cached_context
    
    # Cache miss or force refresh - retrieve from RAG
    st.session_state.rag_logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 RAG cache MISS - retrieving fresh context"
    )
    
    # Perform RAG retrieval
    query = f"repository context, architecture, patterns for: {meeting_notes[:500]}"
    run_async(agent.retrieve_rag_context(query, force_refresh=force_refresh))
    
    # Cache the result
    if agent.rag_context:
        rag_cache.set(meeting_notes, agent.rag_context)
        st.session_state.rag_logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Cached RAG context ({len(agent.rag_context)} chars)"
        )
        snippet_count = agent.rag_context.count('## Context')
        if snippet_count:
            st.session_state.rag_logs.append(
                f"[{datetime.now().strftime('%H:%M:%S')}] 📚 RAG snippets retrieved: {snippet_count}"
            )
    
    return agent.rag_context or ""

# =============================================================================
# BEAUTIFUL HEADER
# =============================================================================

def render_header():
    """
    Render beautiful app header with branding and tagline.
    
    Displays the app title, version, and value proposition in a
    visually appealing gradient header.
    """
    st.markdown(f"""
    <div class="app-header">
        <h1>{AppConfig.APP_ICON} Architect.AI v{AppConfig.APP_VERSION}</h1>
        <p>Transform Meeting Notes into Production-Ready Code | Powered by Advanced RAG & Multi-Agent AI</p>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    """
    Render app footer with version, author, and contact information.
    
    Provides users with version information and a way to contact support.
    Styled to be unobtrusive but informative.
    """
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 1rem 0; color: #6b7280; font-size: 0.875rem;">
        <p style="margin: 0.5rem 0;">
            <strong>Architect.AI v{AppConfig.APP_VERSION}</strong> | 
            Built with ❤️ for developers and product managers
        </p>
        <p style="margin: 0.5rem 0;">
            Made by <strong>{AppConfig.APP_AUTHOR}</strong> | 
            <a href="mailto:{AppConfig.APP_CONTACT}" style="color: #3b82f6; text-decoration: none;">{AppConfig.APP_CONTACT}</a>
        </p>
        <p style="margin: 0.5rem 0; font-size: 0.75rem; color: #9ca3af;">
            Stack-aware prototyping • Context-driven generation • Feature-focused outputs
        </p>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# MODE SELECTION
# =============================================================================

def render_mode_selection():
    """Render beautiful mode selection"""
    st.markdown("## 🎯 Choose Your Mode")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👨‍💻 Developer Mode", key="dev_mode", use_container_width=True):
            st.session_state.mode = "developer"
            st.rerun()
        st.markdown("""
        <div class="content-card">
            <div class="mode-icon">👨‍💻</div>
            <h3 style="color: #1f2937;">Developer Mode</h3>
            <p style="color: #4b5563;">Technical diagrams, ERD, system architecture, code prototypes, API docs, JIRA tasks</p>
            <ul style="text-align: left; color: #6b7280;">
                <li>✅ ERD Diagrams (auto-generated)</li>
                <li>✅ System Architecture</li>
                <li>✅ Component Diagrams</li>
                <li>✅ Code Prototypes</li>
                <li>✅ API Documentation</li>
                <li>✅ JIRA Tasks</li>
                <li>✅ Granular Generation (faster results)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("📊 Product/PM Mode", key="pm_mode", use_container_width=True):
            st.session_state.mode = "product"
            st.rerun()
        st.markdown("""
        <div class="content-card">
            <div class="mode-icon">📊</div>
            <h3 style="color: #1f2937;">Product/PM Mode</h3>
            <p style="color: #4b5563;">Visual prototypes, idea validation, feasibility testing, no code</p>
            <ul style="text-align: left; color: #6b7280;">
                <li>✅ Visual Prototypes</li>
                <li>✅ Ask AI (idea validation)</li>
                <li>✅ Feasibility Testing</li>
                <li>✅ User Flow Diagrams</li>
                <li>✅ No Code (visual only)</li>
                <li>✅ JIRA Generation</li>
                <li>✅ Timeline Estimates</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Render beautiful sidebar"""
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # RAG Index Freshness Check
        try:
            from rag.refresh_manager import get_refresh_manager
            refresh_mgr = get_refresh_manager()
            freshness = refresh_mgr.check_freshness()
            
            if not freshness['is_fresh']:
                st.warning(freshness['recommendation'])
                if freshness['last_updated']:
                    hours_old = freshness['hours_old']
                    if hours_old < 24:
                        time_str = f"{int(hours_old)} hours"
                    else:
                        time_str = f"{int(hours_old/24)} days"
                    st.caption(f"📅 Last indexed: {time_str} ago")
                
                with st.expander("🔄 How to Refresh"):
                    st.code("cd architect_ai_cursor_poc\npython rag/ingest.py", language="bash")
            else:
                with st.expander("✅ RAG Status", expanded=False):
                    st.success(f"Index is fresh ({freshness['indexed_files']} files)")
                    if freshness['last_updated']:
                        st.caption(f"Last updated: {freshness['last_updated'].strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass  # Silently fail if refresh manager not available
        
        # Auto-Reindex Controls
        try:
            from rag.auto_reindex import get_auto_reindexer, start_auto_reindex, stop_auto_reindex, get_reindex_status
            
            with st.expander("🔄 Auto RAG Re-indexing", expanded=False):
                status = get_reindex_status()
                
                if status['is_running']:
                    st.success("✅ Auto-reindex is **running**")
                    st.caption(f"📁 Watching {len(status['watched_dirs'])} directories")
                    st.caption(f"📊 Tracking {status['tracked_files']} files")
                    st.caption(f"⏰ Last reindex: {status['last_reindex']}")
                    
                    if st.button("⏸️ Stop Auto-Reindex", key="stop_auto_reindex"):
                        stop_auto_reindex()
                        st.success("Stopped")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.info("💤 Auto-reindex is **stopped**")
                    st.caption("Files changes will not trigger re-indexing")
                    
                    if st.button("▶️ Start Auto-Reindex", key="start_auto_reindex"):
                        start_auto_reindex()
                        st.success("Started monitoring files")
                        time.sleep(1)
                        st.rerun()
                
                st.caption(f"Check interval: {status['watch_interval']}s")
        except Exception as e:
            pass  # Silently fail if auto-reindex not available
        
        st.divider()
        
        # Manual Reindex / Full Rebuild
        with st.expander("🔧 Manual RAG Rebuild", expanded=False):
            st.info("Rebuild the entire RAG index from scratch")
            st.caption("This will scan all files in the inputs/ directory and recreate the index")
            
            if st.button("🔨 Rebuild RAG Index", key="manual_rebuild_index", type="primary"):
                with st.spinner("Rebuilding RAG index..."):
                    try:
                        import subprocess
                        import sys
                        
                        # Run the ingest.py script
                        result = subprocess.run(
                            [sys.executable, "rag/ingest.py"],
                            capture_output=True,
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        
                        if result.returncode == 0:
                            st.success("✅ RAG index rebuilt successfully!")
                            st.code(result.stdout, language="text")
                            st.rerun()  # Refresh UI to show updated RAG status
                        else:
                            st.error("❌ Failed to rebuild index")
                            st.code(result.stderr, language="text")
                    except subprocess.TimeoutExpired:
                        st.error("❌ Index rebuild timed out (took longer than 5 minutes)")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
        
        st.divider()
        
        # Mode indicator
        if st.session_state.mode:
            mode_emoji = "👨‍💻" if st.session_state.mode == "developer" else "📊"
            mode_name = "Developer" if st.session_state.mode == "developer" else "Product/PM"
            st.success(f"{mode_emoji} **{mode_name} Mode**")
            if st.button("🔄 Switch Mode"):
                st.session_state.mode = None
                st.rerun()
        
        st.divider()

        # AI Provider selection
        st.markdown("### 🤖 AI Provider")
        
        # Build provider list with Ollama first, then cloud + local fine-tuned models
        providers_list = list(AppConfig.AI_PROVIDERS.keys())
        local_provider_options: Dict[str, Dict[str, Any]] = {}
        
        # Ensure Ollama is first (default)
        if "Ollama (Local)" in providers_list:
            providers_list.remove("Ollama (Local)")
            providers_list.insert(0, "Ollama (Local)")
        
        # Add any fine-tuned models from the REGISTRY (check for duplicates)
        added_models = set()  # Track added models to prevent duplicates
        
        try:
            from components.model_registry import model_registry
            
            # Get all usable models from registry (both downloaded and trained)
            trained_models = [
                model for model in model_registry.get_all_models()
                if model.status in ["downloaded", "trained"]
            ]
            for model in trained_models:
                # Add to dropdown with visual indicator
                model_key = model.model_name.lower()
                if model_key not in added_models:
                    display_name = f"🎓 Local: {model.model_name} ✅"
                    providers_list.append(display_name)
                    local_provider_options[display_name] = {
                        "model_id": model.model_id,
                        "model_name": model.model_name,
                        "model_path": model.model_path,
                        "base_model": model.base_model,
                        "trained_at": model.trained_at,
                    }
                    added_models.add(model_key)
        except Exception:
            pass  # Silently continue if registry doesn't exist
        
        provider = st.selectbox(
            "Select Provider",
            providers_list,
            index=0,
            label_visibility="collapsed"
        )
        st.session_state.provider = provider
        st.session_state.local_provider_options = local_provider_options
        selected_local_model = get_selected_local_model(provider)
        
        # Handle provider info
        is_local_model = is_local_provider(provider)
        
        provider_info = AppConfig.AI_PROVIDERS.get(provider)
        if is_local_model:
            # Local fine-tuned model or Ollama
            if provider == "Ollama (Local)":
                # Ollama doesn't use model registry, no warning needed
                st.session_state.selected_local_model = None
            else:
                # Local fine-tuned model - needs registry entry
                st.info(f"🎓 Using local fine-tuned model: {provider}")
                if selected_local_model:
                    st.caption(f"📁 Model path: {selected_local_model['model_path']}")
                    st.session_state.selected_local_model = selected_local_model
                else:
                    st.warning("⚠️ Unable to locate model metadata. Verify model registry entry.")
        else:
            st.session_state.selected_local_model = None
            if not provider_info:
                st.error("❌ Unknown provider selected. Please pick a supported provider.")
            else:
                st.info(f"{provider_info['icon']} {provider_info['name']}")

        actual_provider = st.session_state.get('active_provider_actual')
        if actual_provider and actual_provider != provider:
            st.caption(f"🔌 Active connection: {actual_provider}")

        override_warning = None
        try:
            override_warning = st.session_state.pop('provider_override_warning', None)
        except Exception:
            override_warning = None
        if override_warning:
            st.warning(override_warning)
        
        # API Key input with persistence
        if is_local_model:
            # No API key needed for local models (Ollama or fine-tuned)
            if provider == "Ollama (Local)":
                st.success("✅ Using Ollama local models (no API key needed)")
                st.session_state.api_key = "ollama_local"
            else:
                st.success("✅ No API key needed for local fine-tuned models")
                st.session_state.api_key = "local_finetuned"
        else:
            if provider_info:
                default_key = st.session_state.get('api_key', '') or os.getenv(provider_info['key_env'], "")
                api_key = st.text_input(
                    f"{provider_info['key_env']}",
                    type="password",
                    value=default_key,
                    help=f"Enter your {provider_info['name']} API key (will be remembered in this session)",
                    key=f"api_key_input_{provider}"
                )
                
                if api_key:
                    st.session_state.api_key = api_key
                    
                    # Store in global API key manager for persistence across agent instances
                    from config.secrets_manager import api_key_manager
                    provider_map = {
                        "Ollama (Local)": "ollama",
                        "Groq (FREE & FAST)": "groq",
                        "Google Gemini (FREE)": "gemini",
                        "OpenAI GPT-4": "openai"
                    }
                    if provider in provider_map:
                        api_key_manager.set_key(provider_map[provider], api_key)
                    
                    st.success("✅ API Key configured and saved globally")
                else:
                    st.warning("⚠️ Please enter API key")
        
        st.divider()
        
        # Stats (force recompute on every render for real-time updates)
        st.markdown("### 📊 Session Stats")
        col1, col2 = st.columns(2)
        with col1:
            total_gens = len([log for log in st.session_state.rag_logs if 'Generated' in log or '✅' in log])
            st.metric("Generations", total_gens)
        with col2:
            unique_features = len(set(st.session_state.last_generation)) if st.session_state.last_generation else 0
            st.metric("Features", unique_features)
        
        # RAG Activity Log
        if st.session_state.rag_logs:
            with st.expander("📝 Activity Log"):
                for log in st.session_state.rag_logs[-10:]:
                    st.text(log)
        
        # Cache Controls
        st.divider()
        st.markdown("### 🗄️ Cache")
        
        # Get cache stats
        cache_stats = get_cache_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Hit Rate", cache_stats.get('hit_rate', '0%'))
        with col2:
            total_requests = cache_stats.get('hits', 0) + cache_stats.get('misses', 0)
            st.metric("Requests", total_requests)
        
        # Cache controls
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Clear Cache", help="Force fresh RAG retrieval", use_container_width=True):
                try:
                    from rag.cache import get_cache
                    cache = get_cache()
                    cache.invalidate()
                    st.success("✅ Cache cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        with col2:
            # Info about caching
            with st.popover("ℹ️ Info"):
                st.markdown("""
                **Smart Caching:**
                - ERD, Architecture, JIRA → Cached
                - Prototypes, Code → Fresh each time
                - Auto-invalidates when notes change
                - Reduces API calls by ~40%
                """)
        
        # Quota Usage Monitoring (force fresh calculation)
        st.divider()
        st.markdown("### 📊 API Quota")
        
        rate_limiter = get_rate_limiter()
        # Record calls from session logs for accurate tracking
        rate_limiter.stats.total_calls = len(st.session_state.rag_logs)
        quota_est = rate_limiter.estimate_quota_usage(provider)
        warning_level = rate_limiter.get_warning_level(provider)
        
        # Display quota information
        if quota_est.get('daily_limit'):
            remaining = quota_est.get('estimated_remaining', 0)
            usage_pct = quota_est.get('usage_percentage', 0)
            
            # Color-code based on warning level
            if warning_level == 'exceeded':
                st.error(f"🔴 Quota Exceeded!")
                st.metric("Remaining", "0", delta=f"-{quota_est['total_calls']}")
            elif warning_level == 'critical':
                st.warning(f"⚠️ {remaining} calls left")
                st.progress(usage_pct / 100)
            elif warning_level == 'warning':
                st.info(f"🟡 {remaining} calls left")
                st.progress(usage_pct / 100)
            else:
                st.success(f"✅ {remaining} calls left")
                st.progress(usage_pct / 100)
            
            # Usage stats
            with st.expander("📈 Usage Stats"):
                stats = rate_limiter.get_stats_dict()
                st.metric("Total Calls", stats['total_calls'])
                st.metric("Success Rate", stats['success_rate'])
                st.metric("Calls/Min", stats['calls_per_minute'])
                if stats['last_rate_limit']:
                    st.warning(f"Last rate limit: {stats['last_rate_limit']['provider']}")
        else:
            st.info("📊 Token-based billing (no call limit)")
            stats = rate_limiter.get_stats_dict()
            st.metric("API Calls", stats['total_calls'])
        
        # Workspace Cleanup
        st.divider()
        st.markdown("### 🗑️ Workspace")
        
        # Calculate storage usage
        try:
            outputs_size = sum(
                f.stat().st_size for f in AppConfig.OUTPUTS_DIR.rglob('*') if f.is_file()
            ) / (1024 * 1024)  # Convert to MB
            st.metric("Storage Used", f"{outputs_size:.1f} MB")
        except (OSError, PermissionError) as e:
            st.metric("Storage Used", "0.0 MB")
            print(f"[WARN] Could not calculate storage size: {e}")
        
        if st.button("🧹 Clear All Outputs", help="Delete all generated artifacts", use_container_width=True):
            try:
                import shutil
                deleted_count = 0
                deleted_dirs = 0
                errors = []
                
                for sub in ["visualizations", "documentation", "prototypes", "workflows", "analysis", "validation"]:
                    sub_dir = AppConfig.OUTPUTS_DIR / sub
                    if sub_dir.exists():
                        # Strategy: Delete the entire subdirectory tree, then recreate the parent
                        try:
                            # Count files and dirs before deletion
                            for item in sub_dir.rglob("*"):
                                if item.is_file():
                                    deleted_count += 1
                                elif item.is_dir():
                                    deleted_dirs += 1
                            
                            # Use shutil.rmtree to aggressively delete everything
                            shutil.rmtree(sub_dir)
                            
                            # Recreate the parent directory (empty)
                            sub_dir.mkdir(exist_ok=True)
                            
                        except Exception as e:
                            errors.append(f"{sub}: {str(e)}")
                
                if errors:
                    st.warning(f"⚠️ Deleted {deleted_count} files and {deleted_dirs} dirs, but had errors:\n" + "\n".join(errors))
                else:
                    st.success(f"✅ Deleted {deleted_count} files and {deleted_dirs} directories")
                
                st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Cleared all outputs ({deleted_count} files, {deleted_dirs} dirs)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error during cleanup: {e}")
                import traceback
                st.code(traceback.format_exc())

# =============================================================================
# DEVELOPER MODE
# =============================================================================

def render_dev_mode():
    """
    Render developer mode interface with integrated components.
    
    Comprehensive workflow:
    1. Input - Upload meeting notes
    2. Generate - Create artifacts
    3. Outputs - View generated files
    4. Code Editor - Edit generated code in-app
    5. Tests - Generate unit tests for code
    6. Export - Download artifacts as ZIP or combined docs
    7. Metrics - Track performance
    """
    st.markdown("## 👨‍💻 Developer Mode")
    
    # Render toast-style notifications (auto-clear after 5 seconds)
    render_notifications()
    
    # ========== DEVELOPER SIDEBAR CONTROLS ==========
    st.sidebar.markdown("### ⚙️ Dev Options")
    
    # Parallel Processing Toggle
    use_parallel = st.sidebar.checkbox(
        "⚡ Parallel Processing (60-70% faster)",
        value=True,
        help="Execute artifact generation in parallel for faster results"
    )
    st.session_state.parallel_processing_enabled = use_parallel
    
    # ========== PARALLEL PROCESSING WARNINGS ==========
    # Check model capabilities and show warnings
    if use_parallel:
        from utils.comprehensive_fallbacks import safe_parallel
        
        # Get current provider from session state
        provider_name = st.session_state.get('provider', 'Gemini')
        
        # Strip any prefixes or suffixes (like ✅ or 🎓 Local:)
        if provider_name.startswith("🎓 Local:"):
            provider_name = "Local Model"
        elif " ✅" in provider_name:
            provider_name = provider_name.replace(" ✅", "").strip()
        
        # Check if model supports parallel
        can_parallel, max_concurrent, reason = safe_parallel(
            provider_name,
            ['design', 'jira'],  # Example artifacts
            use_parallel
        )
        
        if can_parallel:
            st.sidebar.success(f"✅ {reason}")
        else:
            st.sidebar.warning(f"⚠️ {reason}")
            st.sidebar.info("System will automatically fall back to sequential processing")
    
    # Enhanced RAG Toggle
    use_enhanced_rag = st.sidebar.checkbox(
        "🧠 Enhanced RAG (100 chunks)",
        value=True,
        help="Use enhanced RAG system with 100 chunks and flexible context windows"
    )
    st.session_state.use_enhanced_rag = use_enhanced_rag
    
    # Visual Diagram Editor Toggle
    enable_visual_editor = st.sidebar.checkbox(
        "🎨 Visual Diagram Editor (Miro-like)",
        value=False,
        help="Enable TRUE Miro-like drag-and-drop diagram editor in Interactive Editor tab"
    )
    st.session_state.enable_visual_diagram_editor = enable_visual_editor
    
    st.sidebar.divider()
    
    # Auto-Ingestion Status
    with st.sidebar.expander("🔄 Auto-Ingestion Status", expanded=False):
        from rag.auto_ingestion import get_auto_ingestion_status
        try:
            status = get_auto_ingestion_status()
            if status.get('enabled', False):
                if status.get('is_running', False):
                    st.success("✅ Auto-ingestion running")
                    st.write(f"**Events processed:** {status.get('events_processed', 0)}")
                    st.write(f"**Files indexed:** {status.get('files_indexed', 0)}")
                    st.write("✅ **Survives app refreshes!**")
                    
                    # Manual controls
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("⏸️ Pause", help="Temporarily pause auto-ingestion"):
                            from rag.auto_ingestion import stop_auto_ingestion
                            stop_auto_ingestion()
                            st.rerun()
                    
                    with col2:
                        if st.button("🔄 Refresh Now", help="Force immediate RAG refresh"):
                            try:
                                import subprocess
                                import sys
                                from pathlib import Path
                                
                                result = subprocess.run([
                                    sys.executable, 
                                    str(Path(__file__).parent.parent / "rag" / "ingest.py")
                                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
                                
                                if result.returncode == 0:
                                    st.success("✅ RAG index refreshed!")
                                else:
                                    st.error(f"❌ RAG refresh failed: {result.stderr}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                else:
                    st.warning("⚠️ Auto-ingestion enabled but not running")
                    if st.button("▶️ Start Auto-Ingestion"):
                        from rag.auto_ingestion import start_auto_ingestion
                        if start_auto_ingestion():
                            st.success("Auto-ingestion started!")
                            st.rerun()
                        else:
                            st.error("Failed to start auto-ingestion")
            else:
                st.info("ℹ️ Auto-ingestion disabled")
                st.caption("Enable in rag/config.yaml to automatically update RAG index")
        except Exception as e:
            st.error(f"❌ Auto-ingestion error: {e}")
    
    local_finetuning_system = None
    persistent_training_manager = None
    st.sidebar.markdown("### 🎓 Local Fine-Tuning")
    try:
        from components.local_finetuning import local_finetuning_system as _local_finetuning_system
        from components.persistent_training import persistent_training_manager as _persistent_training_manager
    except Exception:
        st.sidebar.info("Fine-tuning components unavailable in this environment.")
    else:
        local_finetuning_system = _local_finetuning_system
        persistent_training_manager = _persistent_training_manager
        current_model = local_finetuning_system.current_model
        if current_model:
            model_info = current_model.get('info')
            display_name = model_info.name if model_info else current_model.get('key', 'Local Model')
            st.sidebar.success(f"Loaded locally: {display_name}")
        else:
            st.sidebar.info("Open the **Fine-Tuning** tab to configure local training.")

        active_jobs = persistent_training_manager.get_active_jobs()
        if active_jobs:
            st.sidebar.markdown("**📊 Active Training Jobs**")
            for job in active_jobs:
                status = f"{job.progress:.1%}" if job.status == "running" else job.status
                st.sidebar.info(f"⏳ {job.model_name} — {status}")
        else:
            st.sidebar.caption("No background training jobs running.")
        
        # Manual Resume Section
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔄 Resume Training")
        
    if not local_finetuning_system or not persistent_training_manager:
        st.sidebar.caption("Fine-tuning components not available for resume.")
    else:
        try:
            is_currently_training = local_finetuning_system.is_training()
        except Exception:
            is_currently_training = False
        
        if is_currently_training:
            st.sidebar.success("✅ Training is currently running!")
            st.sidebar.caption("No resume needed - training is active")
        else:
            # Get interrupted jobs
            interrupted_jobs = persistent_training_manager.get_active_jobs()
            
            if interrupted_jobs:
                st.sidebar.info(f"Found {len(interrupted_jobs)} interrupted job(s)")
                for job in interrupted_jobs:
                    with st.sidebar.container():
                        st.markdown(f"**{job.model_name}**")
                        st.caption(f"Job: {job.job_id}")
                        if job.progress > 0:
                            st.caption(f"Progress: {job.progress:.1%} (will resume from checkpoint)")
                        else:
                            st.caption(f"Progress: {job.progress:.1%}")
                        st.caption(f"Status: {job.status}")
                        from pathlib import Path
                        checkpoint_dir = Path(f"./finetuned_models/{job.model_name}")
                        checkpoints = list(checkpoint_dir.glob("checkpoint-*") ) if checkpoint_dir.exists() else []
                        if checkpoints:
                            latest_checkpoint = max(checkpoints, key=lambda x: int(x.name.split('-')[1]))
                            checkpoint_step = int(latest_checkpoint.name.split('-')[1])
                            st.caption(f"✓ Checkpoint available at step {checkpoint_step}")
                        else:
                            st.caption(f"⚠️ No checkpoints - will restart training")
                        if st.button("🔄 Resume Training", key=f"resume_{job.job_id}", use_container_width=True):
                            try:
                                if local_finetuning_system.is_training():
                                    st.sidebar.error("❌ Training is already running!")
                                    return
                                if checkpoints:
                                    with st.spinner(f"Resuming from step {checkpoint_step}..."):
                                        success = persistent_training_manager.resume_training_job(job.job_id)
                                        if success:
                                            st.sidebar.success(f"✅ Training resumed from step {checkpoint_step}!")
                                            st.rerun()
                                        else:
                                            st.sidebar.error("❌ Failed to resume training")
                                else:
                                    with st.spinner("Starting fresh training (no checkpoints)..."):
                                        success = persistent_training_manager.resume_training_job(job.job_id)
                                        if success:
                                            st.sidebar.success("✅ Training started!")
                                            st.rerun()
                                        else:
                                            st.sidebar.error("❌ Failed to start training")
                            except Exception as e:
                                if "already running" in str(e):
                                    st.sidebar.error("❌ Training is already running!")
                                else:
                                    st.sidebar.error(f"❌ Resume error: {str(e)}")
                        st.markdown("---")
            else:
                st.sidebar.info("No interrupted training jobs found")
    
    # ========== MAIN DEV TABS (SIMPLIFIED) ==========
    tabs = st.tabs([
        "📝 Input",
        "🎯 Generate",
        "📊 Outputs",
        "🎨 Interactive Editor",
        "✏️ Code Editor",
        "🎓 Fine-Tuning",
        "🧪 Tests",
        "📤 Export",
        "📚 Versions",
        "📈 Metrics",
        "🔗 Knowledge Graph",
        "🔍 Pattern Mining",
    ])
    
    with tabs[0]:
        render_dev_input_tab()
    
    with tabs[1]:
        render_granular_generation_tab()
    
    with tabs[2]:
        render_dev_outputs_tab()
    
    with tabs[3]:
        render_dev_interactive_editor_tab()
    
    with tabs[4]:
        render_code_editor_tab()
    
    with tabs[5]:
        # Fine-Tuning Tab
        st.markdown("### 🎓 AI Training & Feedback Pipeline")
        st.markdown("Train the AI to learn your project's code patterns and preferences")
        
        # Show the complete feedback-to-training pipeline
        st.info("""
        **📊 Complete Training Pipeline:**
        
        1. **Generate Artifacts** → AI creates code, diagrams, docs
        2. **Provide Feedback** → Click 👍 or 👎 on generated outputs
        3. **Collect Examples** → System stores feedback in training dataset
        4. **Fine-Tune Models** → Train local (Ollama) or cloud (HuggingFace) models
        5. **Deploy & Use** → Improved models generate better outputs
        6. **Repeat** → Continuous improvement loop!
        """)
        
        # Quick stats dashboard
        try:
            from components.finetuning_feedback import feedback_store
            from components.ollama_finetuning import ollama_finetuner
            
            feedback_count = len(feedback_store.list_feedback())
            registered_models = ollama_finetuner.list_models()
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("💬 Feedback Collected", feedback_count, help="Total feedback entries for training")
            with col_stats2:
                st.metric("🤖 Fine-Tuned Models", len(registered_models), help="Custom models created")
            with col_stats3:
                ready_to_train = "✅ Ready" if feedback_count >= 5 else f"⏳ Need {5 - feedback_count} more"
                st.metric("🎯 Training Status", ready_to_train, help="Minimum 5 feedback entries recommended")
            
            if feedback_count > 0 and feedback_count < 5:
                st.warning(f"💡 **Tip:** Collect at least 5 feedback entries for effective training. You have {feedback_count} so far.")
            elif feedback_count >= 5:
                st.success(f"🎉 **Ready to train!** You have {feedback_count} feedback entries. Scroll down to start training.")
                
        except Exception as e:
            st.warning(f"Could not load feedback stats: {e}")
        
        st.markdown("---")
        
        # Main fine-tuning UI
        try:
            from components.local_finetuning import render_local_finetuning_ui
            render_local_finetuning_ui()
        except ImportError as e:
            st.error(f"Fine-tuning component not available: {e}")
        except Exception as e:
            st.error(f"Fine-tuning error: {e}")
            import traceback
            with st.expander("Error Details"):
                st.code(traceback.format_exc())
    
    with tabs[6]:
        render_test_generator_tab()
    
    with tabs[7]:
        render_export_tab()
    
    with tabs[8]:
        from components.version_history import render_version_history
        render_version_history()
    
    with tabs[9]:
        if render_metrics_dashboard:
            render_metrics_dashboard()
        else:
            st.info("📊 Metrics tracking available after generations")
    
    with tabs[10]:
        st.markdown("### 🔗 Knowledge Graph")
        st.markdown("Analyze component relationships and system architecture")
        
        try:
            from components.knowledge_graph import render_knowledge_graph_ui
            render_knowledge_graph_ui()
        except ImportError as e:
            st.error(f"Knowledge Graph component not available: {e}")
        except Exception as e:
            st.error(f"Knowledge Graph error: {e}")
    
    with tabs[11]:
        st.markdown("### 🔍 Pattern Mining")
        st.markdown("Extract code patterns, anti-patterns, and architectural insights")
        
        try:
            from components.pattern_mining import render_pattern_mining_ui
            render_pattern_mining_ui()
        except ImportError as e:
            st.error(f"Pattern Mining component not available: {e}")
        except Exception as e:
            st.error(f"Pattern Mining error: {e}")

def render_dev_input_tab():
    """Render developer input tab"""
    st.markdown("### 📝 Meeting Notes / Requirements")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload meeting notes (Markdown)",
            type=['md', 'txt'],
            help="Upload your meeting notes or requirements document"
        )
    
    with col2:
        st.markdown("#### Quick Actions")
        if st.button("📄 Use Sample", use_container_width=True):
            st.info("Using existing meeting notes")
    
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    
    if uploaded_file:
        content = uploaded_file.read().decode('utf-8')
        stripped_content = content.strip()

        if not stripped_content:
            st.error("❌ Meeting notes are empty. Previous outputs were not cleared.")
            return

        if len(stripped_content) < AppConfig.MIN_MEETING_NOTES_LENGTH:
            st.warning(
                f"⚠️ Meeting notes are very short ({len(stripped_content)} chars). "
                "Add more detail for best results."
            )

        prior = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
        changed = stripped_content != prior.strip()

        if changed:
            invalidate_cache_for_notes()
            clear_feature_outputs()

        notes_path.write_text(content, encoding='utf-8')

        if changed:
            cached_feature_name = cache_feature_name(content)
            st.info(
                "🧹 Cleared previous outputs and cache because meeting notes changed. "
                f"Detected feature: `{cached_feature_name}`"
            )
        else:
            cache_feature_name(content)

        st.success("✅ Meeting notes uploaded!")
    
    if notes_path.exists():
        with st.expander("👀 Preview Meeting Notes", expanded=False):
            st.markdown(notes_path.read_text(encoding='utf-8'))

def render_smart_suggestions(meeting_notes: str):
    """
    Render smart suggestions panel based on meeting notes analysis.
    
    Analyzes meeting notes and suggests relevant artifacts with priority scoring.
    Provides quick-generate buttons for top suggestions.
    """
    from suggestions.smart_suggester import SmartSuggester
    
    suggester = SmartSuggester()
    suggestions = suggester.analyze_and_suggest(meeting_notes)
    
    if not suggestions:
        st.info("📝 No specific suggestions yet. Upload more detailed meeting notes for better recommendations.")
        return
    
    # Show stats
    stats = suggester.get_suggestion_stats(suggestions)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Suggestions", stats['total'])
    with col2:
        st.metric("High Priority", f"🔴 {stats['high_priority']}")
    with col3:
        avg_priority = stats['avg_priority']
        priority_icon = "🟢" if avg_priority >= 80 else "🟡" if avg_priority >= 60 else "⚪"
        st.metric("Avg Priority", f"{priority_icon} {avg_priority:.0f}")
    
    st.markdown("---")
    
    # Show top 3 quick suggestions
    st.markdown("#### 🚀 Quick Generate (Top Suggestions)")
    
    top_suggestions = suggestions[:3]
    cols = st.columns(len(top_suggestions))
    
    for i, suggestion in enumerate(top_suggestions):
        with cols[i]:
            priority_color = "🔴" if suggestion.priority >= 80 else "🟡" if suggestion.priority >= 60 else "⚪"
            display_name = suggester.display_names.get(suggestion.artifact_type, suggestion.artifact_type)
            
            # Wrap in a fixed-height container for alignment
            st.markdown(f"""
            <div style="min-height: 120px; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <p style="font-weight: bold; margin-bottom: 5px;">{priority_color} {display_name}</p>
                    <p style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 5px;">Priority: {suggestion.priority:.0f}/100</p>
                    <p style="font-size: 0.8rem; opacity: 0.7;">{suggestion.reason[:60] + "..." if len(suggestion.reason) > 60 else suggestion.reason}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(
                f"⚡ Generate",
                key=f"quick_gen_{suggestion.artifact_type}",
                use_container_width=True,
                type="primary" if i == 0 else "secondary"
            ):
                generate_single_artifact(suggestion.artifact_type)
    
    st.markdown("---")
    
    # Show all suggestions in expandable list
    st.markdown("#### 📋 All Suggestions")
    
    for suggestion in suggestions:
        priority_color = "🔴" if suggestion.priority >= 80 else "🟡" if suggestion.priority >= 60 else "⚪"
        display_name = suggester.display_names.get(suggestion.artifact_type, suggestion.artifact_type)
        
        with st.expander(f"{priority_color} {display_name} - {suggestion.priority:.0f}/100", expanded=False):
            st.markdown(f"**Why suggested:** {suggestion.reason}")
            
            if suggestion.keywords_matched:
                st.markdown(f"**Keywords found:** {', '.join([f'`{k}`' for k in suggestion.keywords_matched[:5]])}")
            
            if suggestion.dependencies:
                dep_names = [suggester.display_names.get(d, d) for d in suggestion.dependencies]
                st.warning(f"⚠️ **Dependencies:** Generate these first: {', '.join(dep_names)}")
            
            if st.button(f"Generate {display_name}", key=f"gen_{suggestion.artifact_type}", use_container_width=True):
                generate_single_artifact(suggestion.artifact_type)
    
    # Show detected scenarios
    st.markdown("---")
    st.markdown("#### 🎯 Detected Scenarios")
    
    scenarios = suggester.detect_scenarios(meeting_notes)
    active_scenarios = {k: v for k, v in scenarios.items() if v}
    
    if active_scenarios:
        scenario_names = {
            'new_feature': '🆕 New Feature Development',
            'refactoring': '🔧 Code Refactoring',
            'bug_fix': '🐛 Bug Fix',
            'api_integration': '🔌 API Integration',
            'database_migration': '💾 Database Migration',
            'ui_redesign': '🎨 UI/UX Redesign'
        }
        
        for scenario_key in active_scenarios.keys():
            st.success(f"✓ {scenario_names.get(scenario_key, scenario_key)}")
    else:
        st.info("No specific scenarios detected")


def render_granular_generation_tab():
    """Render granular generation tab with beautiful cards"""
    st.markdown("### 🎯 Granular Generation")
    st.info("💡 Generate only what you need for faster results!")
    
    # Smart Suggestions Panel
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        meeting_notes = notes_path.read_text(encoding='utf-8')
        
        if meeting_notes and len(meeting_notes) > 50:
            st.markdown("### 💡 Smart Suggestions - AI Recommendations")
            render_smart_suggestions(meeting_notes)
            st.markdown("---")

    # RAG controls
    with st.expander("🔍 RAG Controls", expanded=False):
        st.text_input("Extra retrieval keywords (improve results)", key="rag_suffix", placeholder="payments, auth, caching, performance")
        st.checkbox("Run in background (jobs)", key="run_background")
        st.caption("Background mode lets you continue working while artifacts generate.")
    
    # Multi-Agent Collaboration toggle
    with st.expander("🤖 Advanced: Multi-Agent Analysis", expanded=False):
        use_multi_agent = st.checkbox(
            "Enable Multi-Agent Collaboration",
            value=False,
            key="use_multi_agent",
            help="Get expert opinions from 3 specialized agents (Design, Backend, Frontend)"
        )
        
        if use_multi_agent:
            st.warning("⚠️ **Cost Warning:** Multi-agent uses 3x API calls per generation (3 expert agents)")
            st.info("""
            **What you get:**
            - 🎨 **Design Agent**: UI/UX, accessibility, visual design analysis
            - 🔧 **Backend Agent**: Scalability, performance, security review
            - 💻 **Frontend Agent**: Components, state management, testing strategy
            - 📊 **Synthesized Recommendations**: Combined best practices from all experts
            """)
            
            st.markdown("**Perfect for:**")
            st.markdown("- Production-critical features")
            st.markdown("- Complex architectures")
            st.markdown("- High-quality requirements")
    
    # Output Validation & Auto-Retry toggle
    with st.expander("✅ Quality: Auto-Validation & Retry", expanded=False):
        use_validation = st.checkbox(
            "Enable Auto-Validation & Retry",
            value=True,
            key="use_validation",
            help="Automatically validate outputs and retry if quality is below threshold"
        )
        
        if use_validation:
            st.info("""
            **What happens:**
            - ✅ **Automatic Validation**: Each artifact is checked for quality
            - 🔄 **Auto-Retry**: If validation fails (score < 60%), automatically retries up to 2 times
            - 📊 **Quality Score**: See real-time quality metrics (0-100%)
            - 📋 **Detailed Feedback**: Get specific errors, warnings, and suggestions
            """)
            
            max_retries = st.slider(
                "Max Retry Attempts",
                min_value=0,
                max_value=3,
                value=2,
                key="max_retries",
                help="Maximum number of retry attempts if validation fails"
            )
            
            st.markdown("**Validates:**")
            st.markdown("- ERD: Entities, relationships, attributes")
            st.markdown("- Architecture: Components, connections, layers")
            st.markdown("- API Docs: Endpoints, methods, examples")
            st.markdown("- JIRA: Tasks, acceptance criteria, structure")
            st.markdown("- Code: Functions, classes, error handling")
            st.markdown("- HTML: Valid structure, styling, content")

    col1, col2 = st.columns(2)

    def _dispatch(artifact: str):
        suffix = get_rag_suffix()
        runtime_context, error = resolve_provider_runtime()
        if error or not runtime_context:
            st.error(f"❌ {error}")
            return
        provider_key_value = runtime_context['credential']
        provider_config_key = runtime_context['config_key']
        if runtime_context['provider_type'] == 'remote' and not provider_key_value:
            st.error("❌ Please configure API key in sidebar first")
            return

        alternate_models: List[str] = []
        if runtime_context.get('provider_type') == 'local':
            local_model_meta = runtime_context.get('local_model') or {}
            alternate_models.extend(
                value for value in [
                    local_model_meta.get('model_id'),
                    local_model_meta.get('model_name'),
                    local_model_meta.get('base_model')
                ]
                if value
            )
        else:
            provider_info = runtime_context.get('provider_info') or {}
            alternate_models.extend(
                value for value in [
                    provider_info.get('name'),
                    provider_info.get('model'),
                    provider_info.get('model_name')
                ]
                if value
            )

        if is_background_mode() and enqueue_job:
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            jid = enqueue_job(
                f"gen_{artifact}",
                job_generate_artifact,
                artifact_type=artifact,
                provider_key=provider_key_value,
                provider_config_key=provider_config_key,
                provider_label=runtime_context.get('provider_label', provider_config_key),
                alternate_models=alternate_models,
                meeting_notes=notes_path.read_text(encoding='utf-8'),
                rag_suffix=suffix,
                force_refresh=True,
            )
            st.success(f"✅ Enqueued job #{jid} for {artifact}")
        else:
            generate_single_artifact(artifact)

    with col1:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">📊 Diagrams & Prototypes</h4>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗄️ Generate ERD Only", use_container_width=True, key="btn_erd"):
            _dispatch("erd")

        if st.button("🏗️ Generate System Architecture", use_container_width=True, key="btn_arch"):
            _dispatch("architecture")

        if st.button("🧩 Generate Code Prototype", use_container_width=True, key="btn_code_proto"):
            _dispatch("code_prototype")

        if st.button("🎨 Generate Developer Visual Prototype", use_container_width=True, key="btn_visual_proto_dev"):
            _dispatch("visual_prototype_dev")

    with col2:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">📊 Individual Diagrams</h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.caption("Generate diagrams one at a time to avoid rate limits")
        
        if st.button("🔵 System Overview", use_container_width=True, key="btn_sys_overview"):
            _dispatch("system_overview")
        
        if st.button("🔄 Data Flow", use_container_width=True, key="btn_data_flow"):
            _dispatch("data_flow")
        
        if st.button("👤 User Flow", use_container_width=True, key="btn_user_flow"):
            _dispatch("user_flow")
        
        if st.button("🧩 Component Diagram", use_container_width=True, key="btn_components"):
            _dispatch("components_diagram")
        
        if st.button("📡 API Sequence", use_container_width=True, key="btn_api_seq"):
            _dispatch("api_sequence")
    
    st.divider()
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">📝 Documentation & API</h4>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📡 Generate API Documentation", use_container_width=True, key="btn_api"):
            _dispatch("api_docs")

        if st.button("📋 Generate JIRA Tasks", use_container_width=True, key="btn_jira"):
            _dispatch("jira")

        if st.button("⚙️ Generate Workflows", use_container_width=True, key="btn_workflows"):
            _dispatch("workflows")

    with col4:
        st.markdown("""
        <div class="content-card">
            <h4 style="color: #1f2937;">⚠️ Batch Operations</h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("⚠️ Batch generation may hit rate limits with Gemini. Use individual buttons above instead.")

        # 📊 Show last individual generation result if exists
        if 'last_generation_result' in st.session_state and st.session_state.last_generation_result:
            result = st.session_state.last_generation_result
            artifact_name = result['artifact'].replace('_', ' ').title()
            if result['success']:
                st.success(f"✅ {artifact_name} generated successfully! ({result['timestamp']})")
            else:
                st.error(f"❌ {artifact_name} generation failed: {result.get('error', 'Unknown error')} ({result['timestamp']})")
        
        # 📊 Show last batch results if they exist
        if 'last_batch_results' in st.session_state and st.session_state.last_batch_results:
            results = st.session_state.last_batch_results
            if results['succeeded']:
                st.success(f"✅ Last batch: {len(results['succeeded'])}/{results['total']} artifacts generated successfully!")
                with st.expander("📋 View details"):
                    st.write("**Succeeded:**", ", ".join(results['succeeded']))
                    if results['failed']:
                        st.write("**Failed:**", ", ".join(results['failed']))
        
        if st.button("🔥 Generate All Docs & Diagrams (10)", use_container_width=True, key="btn_all_docs_diagrams"):
            st.info("Generating: 3 Docs + 7 Diagrams (10 total)...")
            
            # 🔥 FIX: Suppress st.rerun() during batch operations
            st.session_state.batch_mode = True
            
            # 10 artifacts: 3 docs + 7 diagrams
            artifacts = [
                "erd",                    # 1. ERD Diagram
                "architecture",           # 2. Architecture Diagram
                "api_docs",              # 3. API Documentation
                "jira",                  # 4. JIRA Tasks
                "workflows",             # 5. Workflows
                "system_overview",       # 6. System Overview Diagram
                "data_flow",             # 7. Data Flow Diagram
                "user_flow",             # 8. User Flow Diagram
                "components_diagram",    # 9. Components Diagram
                "api_sequence"           # 10. API Sequence Diagram
            ]
            succeeded = []
            failed = []
            
            for i, art in enumerate(artifacts, 1):
                try:
                    st.write(f"⏳ {i}/10: Generating {art}...")
                    _dispatch(art)
                    succeeded.append(art)
                    st.write(f"✅ {i}/10: {art} complete")
                except Exception as e:
                    failed.append(art)
                    st.error(f"❌ {i}/10: {art} failed: {str(e)[:100]}")
                    # Continue to next artifact instead of stopping
                    continue
            
            # Clear batch mode
            st.session_state.batch_mode = False
            
            # 💾 Store results in session state (persists after rerun!)
            st.session_state.last_batch_results = {
                'total': len(artifacts),
                'succeeded': succeeded,
                'failed': failed,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            # Summary before rerun
            if succeeded:
                st.success(f"✅ {len(succeeded)}/10 artifacts complete: {', '.join(succeeded)}")
            if failed:
                st.warning(f"⚠️ {len(failed)}/10 artifacts failed: {', '.join(failed)}")
            
            # Rerun once at the end to refresh UI
            st.rerun()
        
        # 📊 Show last prototype results if they exist
        if 'last_prototype_results' in st.session_state and st.session_state.last_prototype_results:
            results = st.session_state.last_prototype_results
            if results['succeeded']:
                st.success(f"✅ Last batch: {len(results['succeeded'])}/{results['total']} prototypes generated!")
                with st.expander("📋 View details"):
                    st.write("**Succeeded:**", ", ".join(results['succeeded']))
                    if results['failed']:
                        st.write("**Failed:**", ", ".join(results['failed']))
        
        if st.button("🎨 Generate Both Prototypes (2)", use_container_width=True, key="btn_both_prototypes"):
            st.info("Generating: Code + Visual Prototypes (2 total)...")
            
            # 🔥 FIX: Suppress st.rerun() during batch operations
            st.session_state.batch_mode = True
            
            # 2 artifacts: code prototype + visual prototype
            artifacts = [
                "code_prototype",         # 1. Code Prototype
                "visual_prototype_dev"    # 2. Visual Prototype
            ]
            succeeded = []
            failed = []
            
            for i, art in enumerate(artifacts, 1):
                try:
                    st.write(f"⏳ {i}/2: Generating {art}...")
                    _dispatch(art)
                    succeeded.append(art)
                    st.write(f"✅ {i}/2: {art} complete")
                except Exception as e:
                    failed.append(art)
                    st.error(f"❌ {i}/2: {art} failed: {str(e)[:100]}")
                    # Continue to next artifact instead of stopping
                    continue
            
            # Clear batch mode
            st.session_state.batch_mode = False
            
            # 💾 Store results in session state (persists after rerun!)
            st.session_state.last_prototype_results = {
                'total': len(artifacts),
                'succeeded': succeeded,
                'failed': failed,
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            # Summary before rerun
            if succeeded:
                st.success(f"✅ {len(succeeded)}/2 prototypes complete: {', '.join(succeeded)}")
            if failed:
                st.warning(f"⚠️ {len(failed)}/2 prototypes failed: {', '.join(failed)}")
            
            # Rerun once at the end to refresh UI
            st.rerun()


def render_dev_outputs_tab():
    """Render developer outputs tab"""
    st.markdown("### 📊 Generated Outputs")
    
    # Show notification if outputs were just updated
    if st.session_state.get('outputs_updated', False):
        st.session_state.outputs_updated = False
        update_time = st.session_state.get('outputs_updated_time', 'just now')
        st.success(f"✅ New outputs available! (Generated at {update_time})")
    
    # Show last generation info
    if 'last_generation' in st.session_state and st.session_state.last_generation:
        st.info(f"🎉 Last generated: {', '.join(st.session_state.last_generation[-3:])}")
    
    outputs_dir = AppConfig.OUTPUTS_DIR
    
    if not outputs_dir.exists():
        outputs_dir.mkdir(parents=True, exist_ok=True)
        st.warning("💡 No outputs yet. Generate some artifacts using the 'Generate' tab!")
        return
    
    # Check if any outputs exist
    has_outputs = False
    
    # Diagrams
    viz_dir = outputs_dir / "visualizations"
    if viz_dir.exists():
        diagram_files = list(viz_dir.glob("*.mmd"))
        if diagram_files:
            has_outputs = True
            with st.expander("📊 Diagrams", expanded=True):
                # Import diagram viewer
                from components.diagram_viewer import render_diagram_viewer
                
                # Get meeting notes from session state
                meeting_notes = st.session_state.get('meeting_notes', '')
                
                for idx, diagram_file in enumerate(diagram_files):
                    # Use rich diagram viewer with tabs (Mermaid Code | HTML Visualization | Interactive Editor | Export)
                    # This component already has all the tabs we need, no need for outer tabs
                    render_diagram_viewer(diagram_file, meeting_notes)
                    
                    st.divider()
    
    # Documentation (generic) - with black background
    docs_dir = outputs_dir / "documentation"
    if docs_dir.exists():
        doc_files = list(docs_dir.glob("*.md"))
        # Exclude dedicated sections to avoid duplication
        exclude = {"jira_tasks.md", "estimations.md", "personas_journeys.md", "feature_scoring.md", "backlog_pack.md", "pm_jira_tasks.md"}
        doc_files = [p for p in doc_files if p.name not in exclude]
        if doc_files:
            has_outputs = True
            with st.expander("📝 Documentation (All)", expanded=False):
                for doc_file in doc_files:
                    st.markdown(f"#### 📄 {doc_file.stem.replace('_', ' ').title()}")
                    try:
                        content = doc_file.read_text(encoding='utf-8')
                        st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 10px;">{content}</div>', unsafe_allow_html=True)
                        st.divider()
                    except Exception as e:
                        st.error(f"Error loading {doc_file.name}: {str(e)}")
    
    # Dedicated sections for key docs (with black background) - DEV MODE ONLY
    # Note: PM-specific docs (estimations, personas, feature_scoring, backlog_pack) are NOT shown here
    # They belong in PM mode only
    if (docs_dir / "jira_tasks.md").exists():
        has_outputs = True
        with st.expander("📋 JIRA Tasks", expanded=True):
            content = (docs_dir / "jira_tasks.md").read_text(encoding='utf-8')
            # Use proper HTML escaping to prevent stray tags from showing
            st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; font-family: \'Segoe UI\', sans-serif;">{content}</div>', unsafe_allow_html=True)
    
    # OpenAPI
    if (docs_dir / "openapi.yaml").exists():
        has_outputs = True
        with st.expander("📜 OpenAPI.yaml", expanded=False):
            st.code((docs_dir / "openapi.yaml").read_text(encoding='utf-8'), language="yaml")
    
    # Prototypes (code + visual)
    proto_dir = outputs_dir / "prototypes"
    if proto_dir.exists():
        # Get only FILES, skip directories
        proto_files = [f for f in proto_dir.glob("*") if f.is_file()]
        
        if proto_files:
            has_outputs = True
            with st.expander("💻 Prototypes", expanded=False):
                # Show visual prototypes first
                dev_visual = proto_dir / "developer_visual_prototype.html"
                if dev_visual.exists() and dev_visual.is_file():
                    col_title, col_refresh = st.columns([3, 1])
                    with col_title:
                        st.markdown("#### 🎨 Visual Prototype")
                    with col_refresh:
                        if st.button("🔄 Force Refresh", key="refresh_dev_proto", use_container_width=True):
                            # Update timestamp to force reload
                            st.session_state.prototype_last_modified = datetime.now().isoformat()
                            st.rerun()
                    
                    # Check if prototype was updated and show message
                    if st.session_state.get('dev_prototype_updated', False):
                        st.session_state.dev_prototype_updated = False
                        st.success("✅ Prototype updated! Showing latest version.")
                    
                    try:
                        # Deterministic cache busting based on file metadata
                        # Changes ONLY when file actually changes (no random)
                        cache_buster = get_file_cache_buster(dev_visual)
                        
                        # Read file content
                        html_content = dev_visual.read_text(encoding='utf-8')
                        
                        # Vary height significantly to force iframe reload (750-900px range)
                        unique_height = 750 + (abs(hash(cache_buster)) % 150)
                        
                        # Debug info (toggle with checkbox)
                        show_debug = st.checkbox("🔍 Show Debug Info", key="debug_dev_proto", value=False)
                        if show_debug:
                            file_stat = dev_visual.stat()
                            st.code(f"""
File: {dev_visual}
Size: {file_stat.st_size} bytes
Modified: {datetime.fromtimestamp(file_stat.st_mtime)}
Height: {unique_height}px
Cache buster: {cache_buster}
                            """, language="text")
                        
                        # NUCLEAR OPTION: Force complete iframe reload by using unique key
                        iframe_key = f"dev_proto_{abs(hash(cache_buster))}"
                        st.components.v1.html(html_content, height=unique_height, scrolling=True)
                    except Exception as e:
                        st.error(f"Error loading visual prototype: {str(e)}")
                    st.divider()
                
                # Show code prototypes
                code_proto = proto_dir / "prototype_code.txt"
                if code_proto.exists() and code_proto.is_file():
                    st.markdown("#### 💻 Code Prototype")
                    try:
                        st.code(code_proto.read_text(encoding='utf-8'))
                    except Exception as e:
                        st.error(f"Error loading code prototype: {str(e)}")
                    st.divider()
                
                # Code prototypes - NEW enhanced format (from LLM extraction)
                llm_proto_dir = proto_dir / "llm"
                if llm_proto_dir.exists():
                    frontend_dir = llm_proto_dir / "frontend"
                    backend_dir = llm_proto_dir / "backend"
                    
                    has_frontend = frontend_dir.exists() and any(frontend_dir.rglob("*"))
                    has_backend = backend_dir.exists() and any(backend_dir.rglob("*"))
                    
                    if has_frontend or has_backend:
                        st.markdown("#### 💻 Generated Code Prototype")
                        st.info("💡 **Tip:** Go to the **Code Editor** tab to edit these files!")
                        
                        if has_frontend:
                            st.markdown("##### 🎨 Frontend Files")
                            frontend_files = sorted(frontend_dir.rglob("*"), key=lambda p: (p.suffix, p.name))
                            frontend_files = [f for f in frontend_files if f.is_file()]
                            
                            for file_path in frontend_files[:10]:  # Limit to 10 files
                                rel_path = file_path.relative_to(frontend_dir)
                                st.markdown(f"**📄 {rel_path}**")
                                try:
                                    content = file_path.read_text(encoding='utf-8')
                                    # Determine language
                                    ext_map = {'.ts': 'typescript', '.html': 'html', '.scss': 'scss', '.css': 'css', '.js': 'javascript'}
                                    lang = ext_map.get(file_path.suffix, 'text')
                                    st.code(content, language=lang)
                                except Exception as e:
                                    st.error(f"Error loading {file_path.name}: {e}")
                        
                        if has_backend:
                            st.markdown("##### ⚙️ Backend Files")
                            backend_files = sorted(backend_dir.rglob("*"), key=lambda p: (p.suffix, p.name))
                            backend_files = [f for f in backend_files if f.is_file()]
                            
                            for file_path in backend_files[:10]:  # Limit to 10 files
                                rel_path = file_path.relative_to(backend_dir)
                                st.markdown(f"**📄 {rel_path}**")
                                try:
                                    content = file_path.read_text(encoding='utf-8')
                                    st.code(content, language='csharp')
                                except Exception as e:
                                    st.error(f"Error loading {file_path.name}: {e}")
                        
                        st.divider()
    
    # Workflows - with black background
    workflows_dir = outputs_dir / "workflows"
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob("*.md"))
        if workflow_files:
            has_outputs = True
            with st.expander("⚙️ Workflows", expanded=False):
                for workflow_file in workflow_files:
                    st.markdown(f"#### 🔄 {workflow_file.stem.replace('_', ' ').title()}")
                    try:
                        content = workflow_file.read_text(encoding='utf-8')
                        st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 10px;">{content}</div>', unsafe_allow_html=True)
                        st.divider()
                    except Exception as e:
                        st.error(f"Error loading {workflow_file.name}: {str(e)}")
    
    if not has_outputs:
        st.info("💡 No outputs yet. Generate some artifacts using the 'Generate' tab!")
        st.markdown("""
        **Quick Start:**
        1. Go to the **'Generate'** tab
        2. Click any generation button (e.g., 'Generate ERD Only')
        3. Come back here to see your outputs!
        """)

def _require_api_key() -> bool:
    provider = st.session_state.get('provider')
    if is_local_provider(provider):
        return True
    if st.session_state.get('api_key'):
        return True
    st.warning("⚠️ Please configure API key in sidebar first")
    return False

def _build_llm_callable(system_prompt: str = "You are a testing expert. Generate only code."):
    def _call(prompt: str) -> str:
        runtime_context, error = resolve_provider_runtime()
        if error or not runtime_context:
            raise RuntimeError(error or "Unable to resolve provider configuration")
        agent = get_or_create_agent(runtime_context['config'])
        return run_async(agent._call_ai(prompt, system_prompt, artifact_type="code_prototype"))
    return _call




# =============================================================================
# INTELLIGENT CACHING SYSTEM
# =============================================================================

def should_use_cache(artifact_type: str, meeting_notes: str = "") -> bool:
    """
    Determine if cache should be used based on artifact type and context.
    
    Cache-friendly artifacts (stable, repeatable):
    - ERD (same notes → same diagram)
    - Architecture diagrams
    - API documentation
    - All diagrams
    
    Cache-unfriendly artifacts (creative, want variety):
    - Visual prototypes (want fresh designs each time)
    - Code prototypes (explore different implementations)
    
    Args:
        artifact_type: Type of artifact being generated
        meeting_notes: Current meeting notes content
    
    Returns:
        True if cache should be used, False to force fresh generation
    """
    # Check if notes changed recently (within last 5 minutes)
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        import time
        modified_time = notes_path.stat().st_mtime
        age_minutes = (time.time() - modified_time) / 60
        if age_minutes < 5:
            # Notes just uploaded/changed, force fresh generation
            return False
    
    # Cache-friendly artifacts (deterministic, analytical)
    CACHE_FRIENDLY_ARTIFACTS = {
        'erd',              # Database structure is deterministic
        'architecture',     # System architecture is stable
        'all_diagrams',     # All diagrams are analytical
        'api_docs',         # API documentation is factual
        'jira',             # JIRA tasks are requirement-based
        'workflows',        # Workflows are process-based
    }
    
    # Cache-unfriendly artifacts (creative, exploratory)
    CACHE_UNFRIENDLY_ARTIFACTS = {
        'visual_prototype_dev',  # Want fresh UI designs
        'code_prototype',        # Want different implementations
    }
    
    # Determine caching strategy
    if artifact_type in CACHE_FRIENDLY_ARTIFACTS:
        return True  # Use cache for faster results
    elif artifact_type in CACHE_UNFRIENDLY_ARTIFACTS:
        return False  # Force fresh for creativity
    else:
        # Default: use cache for unknown artifacts
        return True


def invalidate_cache_for_notes():
    """
    Invalidate RAG cache when meeting notes change.
    Called when new notes are uploaded.
    """
    try:
        from rag.cache import get_cache
        cache = get_cache()
        cache.invalidate()  # Clear all cached RAG retrievals
        st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Cache invalidated (notes changed)")
    except Exception as e:
        # Cache not critical, continue if fails
        pass


def get_cache_stats() -> dict:
    """
    Get current cache statistics for display.
    
    Returns:
        Dictionary with cache stats (hits, misses, hit_rate)
    """
    try:
        from rag.cache import get_cache
        cache = get_cache()
        return cache.get_stats()
    except Exception:
        return {
            'hits': 0,
            'misses': 0,
            'hit_rate': '0%',
            'backend': {}
        }


# =============================================================================
# INTEGRATED COMPONENTS (Code Editor, Tests, Export)
# =============================================================================

def render_code_editor_tab():
    """
    Render code editor tab for editing generated prototypes.
    Simple but functional code editor with save capability.
    """
    st.markdown("### ✏️ Code Editor")
    st.markdown("Edit generated code files directly and save your changes.")
    
    # List available code files from prototypes (check both singular and plural)
    code_files = []
    proto_dirs = [
        AppConfig.OUTPUTS_DIR / "prototype",  # New location (singular)
        AppConfig.OUTPUTS_DIR / "prototypes"  # Legacy location (plural)
    ]
    
    # 🔥 FIX: Files to exclude (visual prototypes and HTML diagrams belong in Outputs tab only)
    excluded_files = {
        'developer_visual_prototype.html',
        'pm_visual_prototype.html',
        'erd_diagram.html',
        'architecture_diagram.html',
        'api_sequence_diagram.html',
        'user_flow_diagram.html',
        'data_flow_diagram.html',
        'system_overview_diagram.html',
        'components_diagram.html'
    }
    
    for proto_dir in proto_dirs:
        if proto_dir.exists():
            for ext in ['*.ts', '*.py', '*.cs', '*.js', '*.tsx', '*.jsx', '*.html', '*.css']:
                for file_path in proto_dir.rglob(ext):
                    # Exclude test files and visual prototypes/diagrams
                    if (file_path.is_file() and 
                        'test' not in file_path.name.lower() and
                        file_path.name not in excluded_files):
                        code_files.append(file_path)
    
    if not code_files:
        st.info("📝 No code files found. Generate a code prototype first!")
        st.markdown("""
        **To get started:**
        1. Go to the **Generate** tab
        2. Click **Generate Code Prototype**
        3. Return here to edit the generated code
        """)
        return
    
    st.success(f"✅ Found {len(code_files)} code files")
    
    # File selector
    selected_file = st.selectbox(
        "📁 Select File to Edit",
        code_files,
        format_func=lambda x: str(x.relative_to(AppConfig.OUTPUTS_DIR)),
        key="code_editor_file_selector"
    )
    
    if selected_file:
        # Show file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File", selected_file.name)
        with col2:
            size_kb = selected_file.stat().st_size / 1024
            st.metric("Size", f"{size_kb:.1f} KB")
        with col3:
            ext = selected_file.suffix[1:].upper()
            st.metric("Type", ext)
        
        # Read file content
        try:
            original_content = selected_file.read_text(encoding='utf-8')
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
            return
        
        # Determine language for syntax highlighting
        extension_map = {
            '.py': 'python',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.html': 'html',
            '.css': 'css',
            '.cs': 'csharp',
        }
        language = extension_map.get(selected_file.suffix, 'text')
        
        st.markdown("---")
        
        # Editable text area
        edited_content = st.text_area(
            "✏️ Edit Code",
            value=original_content,
            height=500,
            key=f"editor_{selected_file.stem}_{hash(str(selected_file))}",
            help="Edit the code and click Save to write changes to file"
        )
        
        # Show changes indicator
        if edited_content != original_content:
            st.warning("⚠️ You have unsaved changes!")
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                try:
                    selected_file.write_text(edited_content, encoding='utf-8')
                    st.success(f"✅ Saved to {selected_file.name}")
                    st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Edited {selected_file.name}")
                    st.balloons()
                    # Clear any cached editor state
                    editor_key = f"editor_{selected_file.stem}_{hash(str(selected_file))}"
                    if editor_key in st.session_state:
                        del st.session_state[editor_key]
                    # Force reload to show saved content
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        with col2:
            st.download_button(
                "⬇️ Download",
                edited_content,
                file_name=selected_file.name,
                use_container_width=True,
                help="Download current version"
            )
        
        with col3:
            # Copy to clipboard button (download as workaround)
            if st.button("📋 Copy Path", use_container_width=True):
                st.code(str(selected_file))
        
        # Preview section
        with st.expander("👀 Preview (Syntax Highlighted)", expanded=False):
            st.code(edited_content, language=language)


def render_test_generator_tab():
    """
    Render test generator tab for creating unit tests.
    Auto-detects generated code files and generates appropriate tests.
    """
    st.markdown("### 🧪 Test Generator")
    st.markdown("""
    Automatically generate unit tests for your generated code prototypes.
    Supports: **Python (pytest)**, **TypeScript (Jest)**, **C# (xUnit)**, **JavaScript (Jest)**
    """)
    
    # Check if component is available
    if render_test_generator is None:
        st.warning("⚠️ Test generator component not available")
        return
    
    # Auto-detect generated code files (check both singular and plural)
    proto_dirs = [
        AppConfig.OUTPUTS_DIR / "prototype",  # New location (singular)
        AppConfig.OUTPUTS_DIR / "prototypes"  # Legacy location (plural)
    ]
    code_files = []
    
    # 🔥 FIX: Files to exclude (visual prototypes and HTML diagrams belong in Outputs tab only)
    excluded_files = {
        'developer_visual_prototype.html',
        'pm_visual_prototype.html',
        'erd_diagram.html',
        'architecture_diagram.html',
        'api_sequence_diagram.html',
        'user_flow_diagram.html',
        'data_flow_diagram.html',
        'system_overview_diagram.html',
        'components_diagram.html'
    }
    
    for proto_dir in proto_dirs:
        if proto_dir.exists():
            for ext in ['.py', '.ts', '.js', '.cs', '.tsx', '.jsx']:
                for file_path in proto_dir.rglob(f"*{ext}"):
                    # Exclude test files and visual prototypes/diagrams
                    if (file_path.is_file() and 
                        'test' not in file_path.name.lower() and
                        file_path.name not in excluded_files):
                        code_files.append(file_path)
    
    if not code_files:
        st.info("📝 No code files found. Generate a code prototype first!")
        return
    
    st.success(f"✅ Found {len(code_files)} code files")
    
    # File selector
    selected_file = st.selectbox(
        "Select file to generate tests for:",
        options=code_files,
        format_func=lambda x: str(x.relative_to(AppConfig.OUTPUTS_DIR))
    )
    
    if selected_file:
        # Show file preview
        with st.expander("📄 File Preview"):
            try:
                code_content = selected_file.read_text(encoding='utf-8')
                st.code(code_content[:500] + "..." if len(code_content) > 500 else code_content, 
                        language=selected_file.suffix[1:])
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        # Generate tests button
        if st.button("🧪 Generate Tests", type="primary", use_container_width=True):
            with st.spinner("🤖 Generating comprehensive tests..."):
                try:
                    # Read code
                    code = selected_file.read_text(encoding='utf-8')
                    
                    # Get AI configuration
                    runtime_context, error = resolve_provider_runtime()
                    if error or not runtime_context:
                        st.error(f"❌ {error}")
                        return
                    
                    # Get or create cached agent
                    agent = get_or_create_agent(runtime_context['config'])
                    
                    # Determine test framework based on language
                    ext = selected_file.suffix
                    framework_map = {
                        '.py': 'pytest',
                        '.ts': 'Jest',
                        '.tsx': 'Jest',
                        '.js': 'Jest',
                        '.jsx': 'Jest',
                        '.cs': 'xUnit'
                    }
                    framework = framework_map.get(ext, 'appropriate testing framework')
                    
                    # Generate tests
                    prompt = f"""
Generate comprehensive unit tests for this {ext[1:]} code:

FILE: {selected_file.name}
```
{code}
```

Requirements:
- Use {framework} testing framework
- Test happy paths and edge cases
- Include setup/teardown if needed
- Add clear test descriptions
- Mock external dependencies
- Aim for high code coverage

Output ONLY the test code with no explanations or markdown formatting.
"""
                    
                    import asyncio
                    tests = run_async(agent._call_ai(prompt, "You are an expert test engineer", artifact_type="code_prototype"))
                    
                    # Strip markdown artifacts
                    tests = strip_markdown_artifacts(tests)
                    
                    if tests:
                        st.success("✅ Tests generated successfully!")
                        
                        # Display tests
                        st.code(tests, language=selected_file.suffix[1:])
                        
                        # Save tests
                        test_file = selected_file.parent / f"test_{selected_file.name}"
                        test_file.write_text(tests, encoding='utf-8')
                        st.info(f"💾 Saved to: {test_file.relative_to(AppConfig.OUTPUTS_DIR)}")
                        
                        # Download button
                        st.download_button(
                            "⬇️ Download Tests",
                            tests,
                            file_name=f"test_{selected_file.name}",
                            use_container_width=True
                        )
                    else:
                        st.error("❌ Failed to generate tests")
                
                except Exception as e:
                    st.error(f"❌ Error generating tests: {str(e)}")
                    import traceback
                    with st.expander("Error Details"):
                        st.code(traceback.format_exc())


def render_export_tab():
    """
    Render export manager tab for downloading artifacts.
    Supports individual downloads and bulk ZIP export.
    """
    st.markdown("### 📤 Export Manager")
    st.markdown("Download individual files or export all artifacts as a ZIP archive.")
    
    # Scan outputs
    outputs = {
        "Diagrams": list((AppConfig.OUTPUTS_DIR / "visualizations").glob("*.mmd")) if (AppConfig.OUTPUTS_DIR / "visualizations").exists() else [],
        "Documentation": list((AppConfig.OUTPUTS_DIR / "documentation").glob("*.md")) if (AppConfig.OUTPUTS_DIR / "documentation").exists() else [],
        "HTML Prototypes": list((AppConfig.OUTPUTS_DIR / "prototypes").glob("*.html")) if (AppConfig.OUTPUTS_DIR / "prototypes").exists() else [],
        "Code Files": [],
        "Workflows": list((AppConfig.OUTPUTS_DIR / "workflows").glob("*.md")) if (AppConfig.OUTPUTS_DIR / "workflows").exists() else []
    }
    
    # Add code files
    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
    if proto_dir.exists():
        for ext in ['*.ts', '*.py', '*.cs', '*.js', '*.tsx']:
            outputs["Code Files"].extend(proto_dir.rglob(ext))
    
    # Calculate stats
    total_files = sum(len(files) for files in outputs.values())
    total_size = sum(
        f.stat().st_size for files in outputs.values() for f in files if f.is_file()
    ) / (1024 * 1024)  # Convert to MB
    
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Total Files", total_files)
    with col2:
        st.metric("💾 Total Size", f"{total_size:.2f} MB")
    with col3:
        st.metric("📁 Categories", len([v for v in outputs.values() if v]))
    
    if total_files == 0:
        st.info("📝 No artifacts found. Generate some documentation first!")
        return
    
    # Quick export all
    st.markdown("---")
    st.markdown("#### 📦 Bulk Export")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📦 Export All as ZIP", use_container_width=True, type="primary"):
            try:
                import io
                import zipfile
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for category, files in outputs.items():
                        for file in files:
                            if file.is_file():
                                arcname = f"{category}/{file.relative_to(AppConfig.OUTPUTS_DIR)}"
                                zip_file.write(file, arcname)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"architect_ai_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                st.success("✅ ZIP archive ready for download!")
            except Exception as e:
                st.error(f"❌ Error creating ZIP: {e}")
    
    with col2:
        if st.button("📋 Copy All Paths", use_container_width=True):
            all_paths = [str(f.relative_to(AppConfig.OUTPUTS_DIR)) for files in outputs.values() for f in files]
            st.code("\n".join(all_paths))
    
    # Individual category export
    st.markdown("---")
    st.markdown("#### 📂 Export by Category")
    
    for category, files in outputs.items():
        if files:
            with st.expander(f"{category} ({len(files)} files)"):
                for file in files[:20]:  # Limit to first 20 per category
                    col1, col2, col3 = st.columns([4, 1, 1])
                    with col1:
                        st.text(str(file.relative_to(AppConfig.OUTPUTS_DIR)))
                    with col2:
                        size_kb = file.stat().st_size / 1024
                        st.caption(f"{size_kb:.1f} KB")
                    with col3:
                        try:
                            content = file.read_text(encoding='utf-8')
                            st.download_button(
                                "⬇️",
                                content,
                                file_name=file.name,
                                key=f"dl_{file.stem}_{hash(str(file))}"
                            )
                        except (UnicodeDecodeError, ValueError) as e:
                            st.caption(f"(binary or unreadable: {type(e).__name__})")
                
                if len(files) > 20:
                    st.caption(f"... and {len(files) - 20} more files")


# =============================================================================
# PRODUCT/PM MODE
# =============================================================================

def render_pm_mode():
    """Render product/PM mode interface"""
    st.markdown("## 📊 Product/PM Mode")
    
    # Render toast-style notifications (auto-clear after 5 seconds)
    render_notifications()
    
    # ========== PM SIDEBAR CONTROLS ==========
    st.sidebar.markdown("### ⚙️ PM Options")
    
    # Enhanced RAG Toggle
    use_enhanced_rag_pm = st.sidebar.checkbox(
        "🧠 Enhanced RAG (100 chunks)",
        value=True,
        key="pm_enhanced_rag",
        help="Use enhanced RAG system with 100 chunks for better context"
    )
    
    # Auto-Mermaid Toggle
    auto_mermaid_pm = st.sidebar.checkbox(
        "🔧 Auto-Correct Mermaid Diagrams",
        value=True,
        key="pm_auto_mermaid",
        help="Automatically validate and fix Mermaid diagram syntax"
    )
    
    # ========== PM TABS ==========
    tabs = st.tabs(["💡 Idea", "🤖 Ask AI", "📊 Outputs", "🎨 Interactive Editor"])
    
    with tabs[0]:
        render_pm_input_tab()
    
    with tabs[1]:
        render_ask_ai_tab()
    
    with tabs[2]:
        render_pm_outputs_tab()
    
    with tabs[3]:
        render_pm_interactive_editor_tab()

def render_pm_input_tab():
    """Render PM input tab with flexible input sources"""
    st.markdown("### 💡 Your Feature Idea")
    
    # Input method selector
    input_method = st.radio(
        "Choose Input Method:",
        options=["✍️ Describe Idea", "📄 Use Meeting Notes"],
        horizontal=True,
        help="Type directly or use uploaded meeting notes from Developer Mode"
    )
    
    idea = ""
    source = "manual"
    
    if input_method == "✍️ Describe Idea":
        idea = st.text_area(
            "Describe what you want to build:",
            height=200,
            key="pm_idea_manual",
            placeholder="Example:\n• Dashboard for user analytics\n• Mobile checkout flow\n• Admin content moderation panel"
        )
        source = "manual"
    
    else:  # Use Meeting Notes
        notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
        if notes_path.exists():
            idea = notes_path.read_text(encoding='utf-8')
            st.success(f"✅ Loaded meeting notes: {notes_path.name} ({len(idea)} chars)")
            with st.expander("📄 Preview Meeting Notes", expanded=False):
                preview_text = idea[:800] + "\n\n..." if len(idea) > 800 else idea
                st.markdown(preview_text)
            source = "meeting_notes"
        else:
            st.error("⚠️ No meeting notes found")
            st.info("💡 Upload meeting notes in **Developer Mode → Input** tab first")
            idea = ""
            source = "missing"
    
    # Store in session state
    st.session_state.pm_idea = idea
    st.session_state.pm_source = source
    
    # Generation buttons
    if idea:
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎨 Generate Visual Prototype", use_container_width=True, type="primary"):
                generate_visual_prototype(idea, source)
        
        with col2:
            if st.button("📋 Generate JIRA Tasks", use_container_width=True):
                generate_pm_jira(idea, source)
    else:
        if source != "missing":
            st.warning("Please describe your idea first")

def render_ask_ai_tab():
    """Render Ask AI tab with beautiful interface"""
    st.markdown("### 🤖 Ask AI Anything")
    
    if not st.session_state.get('api_key'):
        st.warning("⚠️ Please configure API key in sidebar first")
        return
    
    st.markdown("""
    <div class="content-card">
        <h4 style="color: #1f2937;">💡 Get instant AI feedback on your ideas!</h4>
        <p style="color: #4b5563;">Ask questions about feasibility, risks, timelines, complexity, and more.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # PM power tools
    with st.expander("📦 PM Power Tools", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⏱️ Generate Estimations (timeline/cost)", use_container_width=True):
                _pm_generate_estimations()
            if st.button("👥 Generate Personas & Journeys", use_container_width=True):
                _pm_generate_personas_journeys()
        with col2:
            if st.button("📊 Feature Scoring Matrix", use_container_width=True):
                _pm_generate_scoring()
            if st.button("🧳 Package Backlog", use_container_width=True):
                _pm_package_backlog()

    # Quick question templates
    st.markdown("#### 💡 Quick Questions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Is this feasible?", use_container_width=True):
            st.session_state.ask_ai_question = "Is this idea technically feasible? What are the main challenges?"
    
    with col2:
        if st.button("⚠️ What are the risks?", use_container_width=True):
            st.session_state.ask_ai_question = "What are the main technical and business risks of this idea?"
    
    with col3:
        if st.button("⏱️ How long to build?", use_container_width=True):
            st.session_state.ask_ai_question = "How long would it take to build this? Give me a rough estimate."
    
    with col4:
        if st.button("📊 What's the complexity?", use_container_width=True):
            st.session_state.ask_ai_question = "What's the technical complexity of this idea? Rate it from 1-10."
    
    st.divider()
    
    # Custom question
    st.markdown("#### ✍️ Ask Your Own Question")
    question = st.text_area(
        "Your question:",
        value=st.session_state.get('ask_ai_question', ''),
        height=100,
        placeholder="Ask anything about your idea..."
    )
    
    # Context input
    with st.expander("📝 Add Context (Optional)"):
        context = st.text_area(
            "Describe your idea or feature:",
            height=150,
            placeholder="The more context you provide, the better the AI can help..."
        )
    
    if st.button("🚀 Ask AI", type="primary", use_container_width=True):
        if question:
            ask_ai(question, context)
        else:
            st.warning("Please enter a question")
    
    # Show conversation history
    if 'ai_conversation' in st.session_state and st.session_state.ai_conversation:
        st.divider()
        st.markdown("### 💬 Conversation History")
        for i, (q, a) in enumerate(st.session_state.ai_conversation):
            with st.expander(f"Q{i+1}: {q[:50]}...", expanded=(i == len(st.session_state.ai_conversation) - 1)):
                st.markdown(f"**Question:** {q}")
                st.markdown(f"**Answer:**\n\n{a}")

# PM power tools helpers

def _pm_generate_estimations():
    agent, _ = get_current_agent()
    if not agent:
        return
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
    # RAG first with extended context
    ext_ctx = get_extended_project_context()
    import asyncio
    run_async(agent.retrieve_rag_context(f"estimations {notes} {ext_ctx}"))
    prompt = f"""
Create a realistic delivery plan for the described feature using the project's stack and patterns.
Output:
- Timeline by phases (weeks)
- Roles and estimates (hours)
- Risks and mitigations
- Cost estimate (include assumptions)
- Dependencies
- Milestones
 
PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = run_async(agent._call_ai(prompt, "You are an expert delivery manager. Output in Markdown.", artifact_type="documentation"))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "estimations.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Estimations generated (documentation/estimations.md)")


def _pm_generate_personas_journeys():
    agent, _ = get_current_agent()
    if not agent:
        return
    ext_ctx = get_extended_project_context()
    import asyncio
    run_async(agent.retrieve_rag_context(f"personas journeys {ext_ctx}"))
    prompt = f"""
Generate 3 personas and their user journeys for the proposed feature. Output Markdown with tables and journey steps.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = run_async(agent._call_ai(prompt, "You are an expert UX researcher. Output in Markdown.", artifact_type="documentation"))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "personas_journeys.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Personas & Journeys generated")


def _pm_generate_scoring():
    agent, _ = get_current_agent()
    if not agent:
        return
    ext_ctx = get_extended_project_context()
    import asyncio
    run_async(agent.retrieve_rag_context(f"feature scoring {ext_ctx}"))
    prompt = f"""
Create a feature scoring matrix (Impact, Effort, Risk, Confidence) with formulas and a ranked list. Output Markdown tables.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = run_async(agent._call_ai(prompt, "You are a PM. Output Markdown tables only.", artifact_type="documentation"))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "feature_scoring.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Feature Scoring generated")


def _pm_package_backlog():
    agent, _ = get_current_agent()
    if not agent:
        return
    ext_ctx = get_extended_project_context()
    import asyncio
    run_async(agent.retrieve_rag_context(f"backlog {ext_ctx}"))
    prompt = f"""
Package backlog into Epics, Stories, Subtasks based on the idea and repository patterns. Output Markdown ready to import.

PROJECT CONTEXT (RAG):
{agent.rag_context[:3000]}
"""
    res = run_async(agent._call_ai(prompt, "You are a PM. Output Markdown only.", artifact_type="documentation"))
    if res:
        p = AppConfig.OUTPUTS_DIR / "documentation" / "backlog_pack.md"
        p.parent.mkdir(exist_ok=True)
        p.write_text(res, encoding='utf-8')
        st.success("✅ Backlog package generated")

def render_pm_outputs_tab():
    """Render PM outputs tab"""
    st.markdown("### 📊 Generated Outputs")
    
    outputs_dir = AppConfig.OUTPUTS_DIR
    
    if not outputs_dir.exists():
        st.info("No outputs yet. Generate some prototypes!")
        return
    
    # Visual prototypes (PM-specific)
    proto_dir = outputs_dir / "prototypes"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    if proto_dir.exists() and pm_proto.exists():
        with st.expander("🎨 Visual Prototype", expanded=True):
            # Add manual refresh button
            if st.button("🔄 Force Refresh", key="refresh_pm_proto"):
                # Update timestamp to force reload
                st.session_state.prototype_last_modified = datetime.now().isoformat()
                st.rerun()
            
            # Check if prototype was updated and show message
            if st.session_state.get('pm_prototype_updated', False):
                st.session_state.pm_prototype_updated = False
                st.success("✅ Prototype updated! Showing latest version.")
            
            # Deterministic cache busting based on file metadata
            # Changes ONLY when file actually changes (no random)
            cache_buster = get_file_cache_buster(pm_proto)
            
            # Read file content
            html_content = pm_proto.read_text(encoding='utf-8')
            
            # Vary height significantly to force iframe reload (750-900px range)
            unique_height = 750 + (abs(hash(cache_buster)) % 150)
            
            # Debug info (toggle with checkbox)
            show_debug = st.checkbox("🔍 Show Debug Info", key="debug_pm_proto", value=False)
            if show_debug:
                file_stat = pm_proto.stat()
                st.code(f"""
File: {pm_proto}
Size: {file_stat.st_size} bytes
Modified: {datetime.fromtimestamp(file_stat.st_mtime)}
Height: {unique_height}px
Cache buster: {cache_buster}
                """, language="text")
            
        # NUCLEAR OPTION: Force complete iframe reload by using unique key
        iframe_key = f"pm_proto_{abs(hash(cache_buster))}"
        st.components.v1.html(html_content, height=unique_height, scrolling=True)
    
    # JIRA tasks (PM-specific)
    docs_dir = outputs_dir / "documentation"
    pm_jira = docs_dir / "pm_jira_tasks.md"
    if docs_dir.exists() and pm_jira.exists():
        with st.expander("📋 JIRA Tasks", expanded=True):
            # Black background for markdown
            content = pm_jira.read_text(encoding='utf-8')
            st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">{content}</div>', unsafe_allow_html=True)
    
    # Estimations, Personas, Scoring, Backlog - with black backgrounds
    if docs_dir.exists():
        if (docs_dir / "estimations.md").exists():
            with st.expander("⏱️ Estimations", expanded=False):
                content = (docs_dir / "estimations.md").read_text(encoding='utf-8')
                st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">{content}</div>', unsafe_allow_html=True)
        if (docs_dir / "personas_journeys.md").exists():
            with st.expander("👥 Personas & Journeys", expanded=False):
                content = (docs_dir / "personas_journeys.md").read_text(encoding='utf-8')
                st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">{content}</div>', unsafe_allow_html=True)
        if (docs_dir / "feature_scoring.md").exists():
            with st.expander("📊 Feature Scoring", expanded=False):
                content = (docs_dir / "feature_scoring.md").read_text(encoding='utf-8')
                st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">{content}</div>', unsafe_allow_html=True)
        if (docs_dir / "backlog_pack.md").exists():
            with st.expander("🧳 Backlog Package", expanded=False):
                content = (docs_dir / "backlog_pack.md").read_text(encoding='utf-8')
                st.markdown(f'<div style="background: #1e1e1e; color: #e0e0e0; padding: 20px; border-radius: 8px;">{content}</div>', unsafe_allow_html=True)
        if (docs_dir / "openapi.yaml").exists():
            with st.expander("📜 OpenAPI.yaml", expanded=False):
                st.code((docs_dir / "openapi.yaml").read_text(encoding='utf-8'), language="yaml")

def render_dev_interactive_editor_tab():
    """Render Developer interactive editor tab with AI-powered prototype modification"""
    st.markdown("### 🎨 Interactive Editor")
    
    # Check if visual diagram editor is enabled
    if st.session_state.get('enable_visual_diagram_editor', False):
        st.markdown("#### 🎨 Visual Diagram Editor (Miro-like)")
        st.info("✨ Create Mermaid diagrams with TRUE drag-and-drop! Move nodes, double-click to edit, multi-select with Shift.")
        
        # Load existing diagram if any
        outputs_dir = AppConfig.OUTPUTS_DIR
        viz_dir = outputs_dir / "visualizations"
        initial_mermaid = ""
        
        # Try to load existing diagrams
        diagram_files = []
        if viz_dir.exists():
            diagram_files = list(viz_dir.glob("*.mmd"))
        
        if diagram_files:
            selected_diagram = st.selectbox(
                "Load existing diagram (optional):",
                ["<Create New>"] + [f.stem for f in diagram_files],
                key="visual_editor_diagram_select"
            )
            
            if selected_diagram != "<Create New>":
                diagram_path = viz_dir / f"{selected_diagram}.mmd"
                if diagram_path.exists():
                    initial_mermaid = diagram_path.read_text(encoding='utf-8')
                    st.success(f"✅ Loaded: {selected_diagram}")
        
        # Render the visual diagram editor
        render_visual_diagram_editor(
            diagram_type="flowchart",
            initial_mermaid=initial_mermaid,
            key_suffix="interactive_tab"
        )
        
        st.markdown("---")
        st.markdown("#### 💡 HTML Prototype Editor")
    else:
        st.markdown("Modify your prototype in real-time by chatting with AI. Make it perfect!")
    
    # Check if interactive editor component is available
    if render_interactive_prototype_editor is None:
        st.error("⚠️ Interactive prototype editor component not available")
        return
    
    # Check for existing prototype
    outputs_dir = AppConfig.OUTPUTS_DIR
    proto_dir = outputs_dir / "prototypes"
    dev_proto = proto_dir / "developer_visual_prototype.html"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    
    initial_html = None
    feature_context = ""
    
    # 🔥 FIX: Use file modification time as cache buster to ensure we ALWAYS load the LATEST version
    cache_buster_dev = 0
    if dev_proto.exists():
        cache_buster_dev = int(dev_proto.stat().st_mtime)
    
    last_loaded_dev = st.session_state.get('_editor_last_loaded_dev_cache', -1)
    
    # Load prototype if exists
    if dev_proto.exists():
        # Force reload if file changed (based on modification time)
        if cache_buster_dev != last_loaded_dev:
            st.session_state._editor_last_loaded_dev_cache = cache_buster_dev
            st.session_state.pop('_editor_html_cache', None)  # Clear HTML cache
        
        initial_html = dev_proto.read_text(encoding='utf-8')
        st.success(f"✅ Loaded Developer visual prototype (v{cache_buster_dev})")
    elif pm_proto.exists():
        initial_html = pm_proto.read_text(encoding='utf-8')
        pm_cache_bust = int(pm_proto.stat().st_mtime)
        st.info(f"📋 Loaded PM visual prototype (v{pm_cache_bust})")
    else:
        st.warning("⚠️ No prototype found. Please generate a prototype first in the 'Generate' tab.")
        st.info("💡 Go to **Generate** → Generate Visual Prototype (Dev), then come back here.")
        
        # Option to start from scratch
        if st.button("🎨 Create New Blank Prototype"):
            initial_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Prototype</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 48px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #1f2937;
            margin-bottom: 16px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>New Prototype</h1>
        <p>Start customizing your prototype using the AI chat!</p>
        <button class="btn" onclick="alert('Button clicked!')">Example Button</button>
    </div>
</body>
</html>"""
            st.session_state.current_prototype_html = initial_html
            st.rerun()
    
    # Load meeting notes for context
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        feature_context = notes_path.read_text(encoding='utf-8')
    
    # Get AI agent
    agent, _ = get_current_agent()
    if not agent:
        return
    
    # Render quick modifications
    if initial_html:
        if render_quick_modification_buttons:
            render_quick_modification_buttons(agent, feature_context, mode="dev")
        
        st.markdown("---")
    
    # Render interactive editor
    render_interactive_prototype_editor(agent, initial_html, feature_context, mode="dev")

def render_pm_interactive_editor_tab():
    """Render PM interactive editor tab with AI-powered prototype modification"""
    st.markdown("### 🎨 Interactive Prototype Editor")
    st.markdown("Modify your prototype in real-time by chatting with AI. Make it perfect!")
    
    # Check if interactive editor component is available
    if render_interactive_prototype_editor is None:
        st.error("⚠️ Interactive prototype editor component not available")
        return
    
    # Check for existing prototype
    outputs_dir = AppConfig.OUTPUTS_DIR
    proto_dir = outputs_dir / "prototypes"
    pm_proto = proto_dir / "pm_visual_prototype.html"
    dev_proto = proto_dir / "developer_visual_prototype.html"
    
    initial_html = None
    feature_context = ""
    
    # 🔥 FIX: Use file modification time as cache buster to ensure we ALWAYS load the LATEST version
    cache_buster_pm = 0
    if pm_proto.exists():
        cache_buster_pm = int(pm_proto.stat().st_mtime)
    
    last_loaded_pm = st.session_state.get('_editor_last_loaded_pm_cache', -1)
    
    # Load prototype if exists
    if pm_proto.exists():
        # Force reload if file changed (based on modification time)
        if cache_buster_pm != last_loaded_pm:
            st.session_state._editor_last_loaded_pm_cache = cache_buster_pm
            st.session_state.pop('_editor_html_cache', None)  # Clear HTML cache
        
        initial_html = pm_proto.read_text(encoding='utf-8')
        st.success(f"✅ Loaded PM visual prototype (v{cache_buster_pm})")
    elif dev_proto.exists():
        initial_html = dev_proto.read_text(encoding='utf-8')
        st.info("📋 Loaded Developer visual prototype (will save as PM prototype)")
    else:
        st.warning("⚠️ No prototype found. Please generate a prototype first in the 'Ask AI' tab.")
        st.info("💡 Go to **Ask AI** → Generate Visual Prototype, then come back here.")
        
        # Option to start from scratch
        if st.button("🎨 Create New Blank Prototype"):
            initial_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Prototype</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 48px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #1f2937;
            margin-bottom: 16px;
        }
        .btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 32px;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>New Prototype</h1>
        <p>Start customizing your prototype using the AI chat!</p>
        <button class="btn" onclick="alert('Button clicked!')">Example Button</button>
    </div>
</body>
</html>"""
            st.session_state.current_prototype_html = initial_html
            st.rerun()
    
    # Load meeting notes for context
    notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
    if notes_path.exists():
        feature_context = notes_path.read_text(encoding='utf-8')
    
    # Get AI agent
    agent, _ = get_current_agent()
    if not agent:
        return
    
    # Render quick modifications
    if initial_html:
        if render_quick_modification_buttons:
            render_quick_modification_buttons(agent, feature_context, mode="pm")
        
        st.markdown("---")
    
    # Render interactive editor
    render_interactive_prototype_editor(agent, initial_html, feature_context, mode="pm")
    
# =============================================================================
# GENERATION FUNCTIONS
# =============================================================================

def generate_with_validation_silent(artifact_type: str, generate_fn, meeting_notes: str, outputs_dir: Path, use_ui: bool = False):
    """
    THREAD-SAFE validation wrapper for background jobs with OUTPUT VALIDATOR INTEGRATION.
    
    This is a UI-less version of generate_with_validation that:
    1. Runs the generation function
    2. Validates the output using ai/output_validator.py
    3. Auto-retries if validation fails
    4. Falls back to cloud if local validation fails (for Ollama)
    5. Logs results (no Streamlit UI calls)
    6. Saves validation reports
    
    Args:
        artifact_type: Type of artifact (erd, architecture, etc.)
        generate_fn: Function that generates the artifact (callable, not async)
        meeting_notes: Meeting notes for context
        outputs_dir: Directory to save outputs
        use_ui: If True, show UI (only works in main thread)
    
    Returns:
        Generated content (str) or None
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Use integrated OutputValidator
    try:
        from ai.output_validator import OutputValidator
        validator = OutputValidator()
    except Exception as e:
        logger.warning(f"Failed to load OutputValidator, using fallback: {e}")
        from validation.output_validator import ArtifactValidator
        validator = ArtifactValidator()
    
    use_validation = True  # Always validate in background
    max_retries = 2
    
    result = None
    validation_result = None
    attempt = 0
    
    while attempt <= max_retries:
        # Generate
        try:
            result = generate_fn()  # Execute the callable
        except Exception as e:
            logger.error(f"Generation attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries:
                attempt += 1
                continue
            else:
                return None
        
        # Check if generation returned valid content
        if not result or (isinstance(result, str) and len(result.strip()) == 0):
            logger.warning(f"Generation attempt {attempt + 1} returned empty result")
            if attempt < max_retries:
                attempt += 1
                continue
            else:
                logger.error("All generation attempts failed to produce content")
                return None
        
        # Validate
        if use_validation and result:
            # OutputValidator returns (ValidationResult, issues, score) tuple
            from ai.output_validator import OutputValidator, ValidationResult
            validator_instance = OutputValidator()
            validation_status, validation_issues, validation_score = validator_instance.validate(
                artifact_type, result, {'meeting_notes': meeting_notes}
            )
            
            # Create a validation result object for compatibility
            class ValidationResultWrapper:
                def __init__(self, status, issues, score):
                    self.status = status
                    self.score = score
                    self.is_valid = status != ValidationResult.FAIL
                    self.errors = [issue for issue in issues if "error" in issue.lower() or "missing" in issue.lower()]
                    self.warnings = [issue for issue in issues if issue not in self.errors]
                    self.suggestions = []
            
            validation_result = ValidationResultWrapper(validation_status, validation_issues, validation_score)
            
            logger.info(f"Validation: {artifact_type} - Score: {validation_result.score:.1f}/100, Valid: {validation_result.is_valid}")
            
            # 🚀 RECORD FEEDBACK FOR ADAPTIVE LEARNING (any score ≥80)
            if validation_result.score >= 80:
                try:
                    from components.adaptive_learning import AdaptiveLearningLoop, FeedbackType
                    adaptive_loop = AdaptiveLearningLoop()
                    
                    adaptive_loop.record_feedback(
                        input_data=meeting_notes,
                        ai_output=result,
                        artifact_type=artifact_type,
                        model_used="unknown",  # Model info not available in this path
                        validation_score=validation_result.score,
                        feedback_type=FeedbackType.SUCCESS,
                        corrected_output=None,
                        context={'meeting_notes': meeting_notes, 'is_background_job': True}
                    )
                    logger.info(f"[ADAPTIVE_LEARNING] ✅ Recorded feedback for {artifact_type} (score: {validation_result.score:.1f})")
                except Exception as e:
                    logger.warning(f"[ADAPTIVE_LEARNING] ⚠️ Failed to record feedback: {e}")
            
            # 🚀 REMOVED OLD RETRY LOGIC - Smart generator handles retries internally
            # The smart generation orchestrator already does:
            # 1. Try local models (with quality validation)
            # 2. If local fails validation, automatically fall back to cloud
            # 3. Capture cloud responses for fine-tuning
            # So we don't need app-level retry logic anymore
        
        # Success - exit loop
        break
    
    # Save fine-tuning dataset if cloud model generated quality output
    if use_validation and validation_result and result and validation_result.score >= 80:
        try:
            # Determine if this was a cloud model generation (attempt > 0 means local failed and retried)
            is_cloud_generation = attempt > 0
            
            if is_cloud_generation:
                import json
                
                finetune_dir = Path("finetune_datasets") / "cloud_outputs"
                finetune_dir.mkdir(parents=True, exist_ok=True)
                
                # Create fine-tuning dataset entry
                dataset_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "artifact_type": str(artifact_type),
                    "prompt": f"Generate {artifact_type} for: {meeting_notes[:500]}...",  # First 500 chars
                    "completion": result,
                    "validation_score": validation_result.score,
                    "validation_status": str(validation_result.status.value) if hasattr(validation_result.status, 'value') else str(validation_result.status),
                    "attempts": attempt + 1,
                    "source": "cloud_fallback"
                }
                
                # Save to JSONL file (append mode)
                dataset_file = finetune_dir / f"{artifact_type}_quality_outputs.jsonl"
                with open(dataset_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(dataset_entry) + '\n')
                
                logger.info(f"Saved fine-tuning dataset entry for {artifact_type} (score: {validation_result.score})")
        except Exception as e:
            logger.warning(f"Failed to save fine-tuning dataset: {e}")
    
    # Save validation report if available
    if use_validation and validation_result and result:
        validation_dir = outputs_dir / "validation"
        validation_dir.mkdir(exist_ok=True)
        report = f"""# Validation Report: {artifact_type.upper()}

Score: {validation_result.score:.1f}/100
Status: {'✅ VALID' if validation_result.is_valid else '⚠️ NEEDS IMPROVEMENT'}
Attempts: {attempt + 1}

## Errors
{chr(10).join(f'- {e}' for e in validation_result.errors) if validation_result.errors else 'None'}

## Warnings
{chr(10).join(f'- {w}' for w in validation_result.warnings) if validation_result.warnings else 'None'}

## Suggestions
{chr(10).join(f'- {s}' for s in validation_result.suggestions) if validation_result.suggestions else 'None'}
"""
        (validation_dir / f"{artifact_type}_validation.md").write_text(report, encoding='utf-8')
    
    return result


def generate_with_validation(artifact_type: str, generate_fn, meeting_notes: str, outputs_dir: Path):
    """
    UI-FRIENDLY validation wrapper with INTEGRATED OUTPUT VALIDATOR.
    
    This ensures consistent quality across all artifact types by:
    1. Running the generation function
    2. Validating using ai/output_validator.py (artifact-specific rules)
    3. Auto-retrying if validation fails (up to max_retries)
    4. Displaying quality metrics in UI
    5. Saving validation reports
    
    Args:
        artifact_type: Type of artifact (erd, architecture, etc.)
        generate_fn: Async function that generates the artifact
        meeting_notes: Meeting notes for context
        outputs_dir: Directory to save outputs
    
    Returns:
        Generated content (str) or None
    """
    # Use integrated OutputValidator
    try:
        from ai.output_validator import OutputValidator
        validator_class = OutputValidator
    except Exception as e:
        st.warning(f"⚠️ Using fallback validator: {e}")
        from validation.output_validator import ArtifactValidator
        validator_class = ArtifactValidator
    
    use_validation = st.session_state.get('use_validation', True)
    max_retries = st.session_state.get('max_retries', 2)
    
    result = None
    validation_result = None
    attempt = 0
    
    while attempt <= max_retries:
        # Generate
        import inspect
        is_async = inspect.iscoroutinefunction(generate_fn)
        
        if attempt == 0:
            # Check if function is async or sync
            if is_async:
                result = run_async(generate_fn())
            else:
                result = generate_fn()  # Call directly if not async
        else:
            # Retry with feedback
            st.info(f"🔄 Retry attempt {attempt}/{max_retries}...")
            from validation.output_validator import ArtifactValidator
            validator = ArtifactValidator()
            feedback = validator.get_retry_feedback(validation_result, artifact_type)
            
            # For retry, we regenerate (could enhance generate_fn to accept feedback)
            st.markdown(f"**Feedback for improvement:**\n{feedback}")
            if is_async:
                result = run_async(generate_fn())
            else:
                result = generate_fn()  # Call directly if not async
        
        # Check if generation returned valid content
        if not result or (isinstance(result, str) and len(result.strip()) == 0):
            st.warning(f"⚠️ Generation attempt {attempt + 1} returned empty result")
            if attempt < max_retries:
                attempt += 1
                continue
            else:
                st.error("❌ All generation attempts failed to produce content")
                return None
        
        # Validate if enabled
        if use_validation and result:
            validator = validator_class()
            # OutputValidator returns (ValidationResult, issues, score) tuple
            validation_status, validation_issues, validation_score = validator.validate(
                artifact_type, result, {'meeting_notes': meeting_notes}
            )
            
            # Create a validation result object for compatibility
            class ValidationResultWrapper:
                def __init__(self, status, issues, score):
                    self.status = status
                    self.score = score
                    self.is_valid = status != ValidationResult.FAIL
                    self.errors = [issue for issue in issues if "error" in issue.lower() or "missing" in issue.lower()]
                    self.warnings = [issue for issue in issues if issue not in self.errors]
                    self.suggestions = []
            
            from ai.output_validator import ValidationResult
            validation_result = ValidationResultWrapper(validation_status, validation_issues, validation_score)
            
            # 🚀 RECORD FEEDBACK FOR ADAPTIVE LEARNING (any score ≥80)
            if validation_result.score >= 80:
                try:
                    from components.adaptive_learning import AdaptiveLearningLoop, FeedbackType
                    adaptive_loop = AdaptiveLearningLoop()
                    
                    adaptive_loop.record_feedback(
                        input_data=meeting_notes,
                        ai_output=result,
                        artifact_type=artifact_type,
                        model_used="unknown",  # Model info not available in this path
                        validation_score=validation_result.score,
                        feedback_type=FeedbackType.SUCCESS,
                        corrected_output=None,
                        context={'meeting_notes': meeting_notes, 'is_ui_generation': True}
                    )
                    st.session_state.rag_logs.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Recorded feedback for fine-tuning (score: {validation_result.score:.1f})"
                    )
                except Exception as e:
                    st.session_state.rag_logs.append(
                        f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Failed to record feedback: {str(e)}"
                    )
            
            # Show validation results
            col1, col2 = st.columns([1, 3])
            with col1:
                score_color = "🟢" if validation_result.score >= 80 else "🟡" if validation_result.score >= 60 else "🔴"
                st.metric("Quality Score", f"{score_color} {validation_result.score:.1f}/100")
            with col2:
                status = "✅ PASS" if validation_result.is_valid else "⚠️ NEEDS IMPROVEMENT"
                st.metric("Validation", status)
            
            if validation_result.errors or validation_result.warnings:
                with st.expander("📋 Validation Details", expanded=not validation_result.is_valid):
                    if validation_result.errors:
                        st.markdown("**❌ Errors:**")
                        for error in validation_result.errors:
                            st.markdown(f"- {error}")
                    if validation_result.warnings:
                        st.markdown("**⚠️ Warnings:**")
                        for warning in validation_result.warnings:
                            st.markdown(f"- {warning}")
                    if validation_result.suggestions:
                        st.markdown("**💡 Suggestions:**")
                        for suggestion in validation_result.suggestions:
                            st.markdown(f"- {suggestion}")
            
            # Check if retry needed
            if validation_result.score < 70 and attempt < max_retries:
                st.warning(f"Quality score below threshold. Retrying... ({attempt + 1}/{max_retries})")
                attempt += 1
                continue
        
        # Success - exit loop
        break
    
    # Save validation report if available
    if use_validation and validation_result and result:
        validation_dir = outputs_dir / "validation"
        validation_dir.mkdir(exist_ok=True)
        report = f"""# Validation Report: {artifact_type.upper()}

Score: {validation_result.score:.1f}/100
Status: {'✅ VALID' if validation_result.is_valid else '⚠️ NEEDS IMPROVEMENT'}
Attempts: {attempt + 1}

## Errors
{chr(10).join(f'- {e}' for e in validation_result.errors) if validation_result.errors else 'None'}

## Warnings
{chr(10).join(f'- {w}' for w in validation_result.warnings) if validation_result.warnings else 'None'}

## Suggestions
{chr(10).join(f'- {s}' for s in validation_result.suggestions) if validation_result.suggestions else 'None'}
"""
        (validation_dir / f"{artifact_type}_validation.md").write_text(report, encoding='utf-8')
        
        if validation_result.is_valid:
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {artifact_type} validation: {validation_result.score:.1f}/100")
        else:
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ {artifact_type} validation: {validation_result.score:.1f}/100 (warnings present)")
    
    # Auto-save version (if versioning enabled)
    if result and st.session_state.get('enable_versioning', True):
        try:
            from versioning.version_manager import VersionManager
            vm = VersionManager()
            vm.save_version(
                artifact_type=artifact_type,
                content=result,
                validation_score=validation_result.score if validation_result else 0.0,
                attempt_count=attempt + 1,
                notes=f"Auto-saved during generation"
            )
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Saved version: {artifact_type}")
        except Exception as e:
            # Don't fail generation if versioning fails
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Version save failed: {str(e)}")
    
    return result


# ============================================================================
# DIAGRAM GENERATION HELPER FUNCTIONS
# These functions encapsulate diagram-specific generation logic for clarity
# ============================================================================

def _save_diagram_with_html(
    diagram_content: str,
    diagram_type: str,
    diagram_name: str,
    meeting_notes: str,
    outputs_dir: Path,
    agent
) -> None:
    """
    Save diagram as .mmd file and generate HTML visualization.
    
    Args:
        diagram_content: The Mermaid diagram code
        diagram_type: Type identifier (e.g., 'erd', 'architecture')
        diagram_name: Human-readable name for messages
        meeting_notes: Meeting notes for context
        outputs_dir: Output directory path
        agent: The AI agent with RAG context
    """
    viz_dir = outputs_dir / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    # Save .mmd file
    mmd_file = viz_dir / f"{diagram_type}_diagram.mmd"
    mmd_file.write_text(diagram_content, encoding='utf-8')
    
    # Generate HTML visualization with RAG context
    try:
        from components.mermaid_html_renderer import mermaid_html_renderer
        html_content = run_async(
            mermaid_html_renderer.generate_html_visualization_with_gemini(
                diagram_content, meeting_notes, diagram_type, agent.rag_context, agent=agent
            )
        )
        html_file = mmd_file.with_suffix('.html')
        html_file.write_text(html_content, encoding='utf-8')
        st.success(f"✅ Generated {diagram_name} + HTML visualization")
    except Exception as e:
        st.warning(f"⚠️ {diagram_name} generated, but HTML creation failed: {str(e)}")


def _update_generation_state(artifact_type: str, model_used: str = "unknown", is_cloud: bool = False) -> None:
    """
    Update session state after successful generation.
    
    This ensures consistent state management across ALL artifact types and enables
    feedback collection for both local and cloud model generations.
    
    Args:
        artifact_type: Type of artifact generated
        model_used: Model identifier (e.g., 'llama3:8b', 'groq/llama-3.3-70b')
        is_cloud: Whether a cloud provider was used
    """
    st.session_state.last_generation.append(artifact_type)
    st.session_state.outputs_updated = True
    st.session_state.outputs_updated_time = datetime.now().isoformat()
    st.session_state[f'generated_{artifact_type}'] = True
    st.session_state[f'generation_time_{artifact_type}'] = datetime.now().isoformat()
    
    # Store model metadata for feedback system
    st.session_state[f'model_used_{artifact_type}'] = model_used
    st.session_state[f'is_cloud_{artifact_type}'] = is_cloud
    st.session_state[f'show_feedback_ui_{artifact_type}'] = True


def generate_single_artifact(artifact_type: str):
    """
    Generate a single artifact with full repository context and RAG.
    
    This is the core generation function that ensures all outputs are:
    1. Context-aware: Uses repository architecture, patterns, and conventions
    2. Feature-focused: Based on meeting notes, not the app itself
    3. Stack-aware: Detects and respects the project's tech stack
    
    Args:
        artifact_type: Type of artifact to generate (erd, architecture, code_prototype, etc.)
    
    Process:
        1. Load meeting notes
        2. Initialize AI agent with API key
        3. Retrieve RAG context (force fresh retrieval)
        4. Analyze repository structure and conventions
        5. Process meeting notes to extract feature requirements
        6. Generate artifact using full context
        7. Save to appropriate output directory
        8. Track generation metrics
    
    Returns:
        None (displays results in Streamlit UI)
    """
    try:
        # 🔥 FIX: Clear previous result to avoid showing stale success message
        st.session_state.last_generation_result = None
        
        with st.spinner(f"🎨 Generating {artifact_type}..."):
            # Load meeting notes
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            
            meeting_notes = notes_path.read_text(encoding='utf-8')
            
            # Get AI config
            runtime_context, error = resolve_provider_runtime()
            if error or not runtime_context:
                st.error(f"❌ {error}")
                return
            
            # Get or create cached agent (avoid re-initialization)
            agent = get_or_create_agent(runtime_context['config'])
            agent.meeting_notes = meeting_notes
            
            # Smart caching decision
            use_cache = should_use_cache(artifact_type, meeting_notes)
            force_refresh = not use_cache
            
            # Retrieve RAG context with intelligent caching
            if use_cache:
                st.info("💾 Retrieving context (using cache for speed)...")
            else:
                st.info("🔄 Retrieving fresh context from repository...")
            
            # Use RAG caching helper - avoids redundant expensive queries
            retrieve_rag_with_cache(agent, meeting_notes, force_refresh=force_refresh)
            
            # Generate based on type
            st.info(f"✨ Generating {artifact_type} with full context...")
            outputs_dir = AppConfig.OUTPUTS_DIR
            outputs_dir.mkdir(parents=True, exist_ok=True)
            
            # Store result for potential multi-agent analysis
            generated_result = None
            
            if artifact_type == "erd":
                result = generate_with_validation(
                    "erd",
                    agent.generate_erd_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    _save_diagram_with_html(result, "erd", "ERD diagram", meeting_notes, outputs_dir, agent)
                    _update_generation_state("erd")
                    
                track_generation("erd")
                st.session_state.last_generation_result = {
                    'artifact': 'erd',
                    'success': True,
                    'timestamp': datetime.now().strftime("%H:%M:%S")
                }
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
                    
            elif artifact_type == "architecture":
                result = generate_with_validation(
                    "architecture",
                    agent.generate_architecture_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    _save_diagram_with_html(result, "architecture", "Architecture diagram", meeting_notes, outputs_dir, agent)
                    _update_generation_state("architecture")
                    
                track_generation("architecture")
                # Only rerun if not in batch mode
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
            elif artifact_type == "api_docs":
                result = generate_with_validation(
                    "api_docs",
                    agent.generate_api_docs_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    docs_dir = outputs_dir / "documentation"
                    docs_dir.mkdir(exist_ok=True)
                    (docs_dir / "api.md").write_text(result, encoding='utf-8')
                    
                    # Update session state for outputs tab
                    st.session_state.last_generation.append("api_docs")
                    st.session_state.outputs_updated = True
                    st.session_state.outputs_updated_time = datetime.now().isoformat()
                    st.success("✅ API Documentation generated!")
                    
                track_generation("api_docs")
                # Only rerun if not in batch mode
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
            elif artifact_type == "jira":
                # Ensure meeting notes are processed first for higher fidelity
                try:
                    run_async(agent.process_meeting_notes(str(notes_path)))
                except Exception:
                    pass
                result = generate_with_validation(
                    "jira",
                    agent.generate_jira_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    result = strip_markdown_artifacts(result)
                    docs_dir = outputs_dir / "documentation"
                    docs_dir.mkdir(exist_ok=True)
                    (docs_dir / "jira_tasks.md").write_text(result, encoding='utf-8')
                    
                    # Update session state for outputs tab
                    st.session_state.last_generation.append("jira")
                    st.session_state.outputs_updated = True
                    st.session_state.outputs_updated_time = datetime.now().isoformat()
                    st.success("✅ JIRA Tasks generated!")
                    
                track_generation("jira")
                # Only rerun if not in batch mode
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
            elif artifact_type == "workflows":
                result = generate_with_validation(
                    "workflows",
                    agent.generate_workflows_only,
                    meeting_notes,
                    outputs_dir
                )
                generated_result = result
                if result:
                    wf_dir = outputs_dir / "workflows"
                    wf_dir.mkdir(exist_ok=True)
                    (wf_dir / "workflows.md").write_text(result, encoding='utf-8')
                    
                    # Update session state for outputs tab
                    st.session_state.last_generation.append("workflows")
                    st.session_state.outputs_updated = True
                    st.session_state.outputs_updated_time = datetime.now().isoformat()
                    st.success("✅ Workflows generated!")
                    
                track_generation("workflows")
                # Only rerun if not in batch mode
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
            elif artifact_type in ["system_overview", "data_flow", "user_flow", "components_diagram", "api_sequence"]:
                # Generate individual diagram (BUG FIX #2: Only generate the requested diagram, not all)
                diagram_map = {
                    "system_overview": ("overview", "System Overview", agent.generate_system_overview_diagram),
                    "data_flow": ("dataflow", "Data Flow", agent.generate_data_flow_diagram),
                    "user_flow": ("userflow", "User Flow", agent.generate_user_flow_diagram),
                    "components_diagram": ("components", "Component Diagram", agent.generate_components_diagram),
                    "api_sequence": ("api", "API Sequence", agent.generate_api_sequence_diagram)
                }
                
                diagram_key, diagram_name, diagram_method = diagram_map[artifact_type]
                
                def generate_single_diagram():
                    # BUG FIX #2: Call individual method instead of generating all diagrams
                    content = run_async(diagram_method())
                    if not content:
                        raise Exception(f"{diagram_name} not generated")
                    viz_dir = outputs_dir / "visualizations"
                    viz_dir.mkdir(exist_ok=True)
                    
                    # Validate diagram syntax
                    is_valid, corrected_content, errors = validate_mermaid_syntax(content)
                    if not is_valid and corrected_content:
                        content = corrected_content
                    
                    mmd_file = viz_dir / f"{diagram_key}_diagram.mmd"
                    mmd_file.write_text(content, encoding='utf-8')
                    
                    # Generate HTML visualization
                    try:
                        from components.mermaid_html_renderer import mermaid_html_renderer
                        html_content = run_async(
                            mermaid_html_renderer.generate_html_visualization_with_gemini(
                                content, meeting_notes, diagram_key, agent.rag_context, agent=agent
                            )
                        )
                        html_file = mmd_file.with_suffix('.html')
                        html_file.write_text(html_content, encoding='utf-8')
                    except Exception as e:
                        st.warning(f"⚠️ {diagram_name} generated, but HTML creation failed: {str(e)}")
                    
                    # ✅ FIX: Return simple success message without diagram name (prevents duplication)
                    return "success"
                
                result = generate_with_validation(
                    artifact_type,
                    generate_single_diagram,
                    meeting_notes,
                    outputs_dir
                )
                
                if result:
                    generated_result = result
                    _update_generation_state(artifact_type)
                    st.success(f"✅ {diagram_name} generated!")
                    
                track_generation(artifact_type)
                if not st.session_state.get('batch_mode', False):
                    st.rerun()
            elif artifact_type == "all_diagrams":
                # Wrap all diagrams generation in validation for unified quality control
                def generate_all_diagrams():
                    diagrams = run_async(agent.generate_specific_diagrams())
                    if not diagrams:
                        raise Exception("No diagrams generated")
                    
                    viz_dir = outputs_dir / "visualizations"
                    viz_dir.mkdir(exist_ok=True)
                    html_generated = 0
                    
                    for name, content in diagrams.items():
                        # Validate each diagram's Mermaid syntax
                        is_valid, corrected_content, errors = validate_mermaid_syntax(content)
                        if not is_valid and corrected_content:
                            content = corrected_content
                        
                        mmd_file = viz_dir / f"{name}_diagram.mmd"
                        mmd_file.write_text(content, encoding='utf-8')
                        
                        # Generate HTML visualization with RAG context
                        try:
                            from components.mermaid_html_renderer import mermaid_html_renderer
                            html_content = run_async(
                                mermaid_html_renderer.generate_html_visualization_with_gemini(
                                    content, meeting_notes, name, agent.rag_context, agent=agent
                                )
                            )
                            html_file = mmd_file.with_suffix('.html')
                            html_file.write_text(html_content, encoding='utf-8')
                            html_generated += 1
                        except Exception as e:
                            st.warning(f"⚠️ {name} diagram generated, but HTML creation failed: {str(e)}")
                    
                    return f"Generated {len(diagrams)} diagrams + {html_generated} HTML visualizations"
                
                # Use unified validation wrapper
                result = generate_with_validation(
                    "all_diagrams",
                    generate_all_diagrams,
                    meeting_notes,
                    outputs_dir
                )
                
                if result:
                    generated_result = result
                track_generation("diagrams")
            elif artifact_type == "code_prototype":
                feature_name = "feature-from-notes"
                try:
                    # Prefer extracted name from processed meeting notes
                    if getattr(agent, 'feature_requirements', None):
                        feature_name = agent.feature_requirements.get('name', feature_name) or feature_name
                except Exception:
                    pass
                if feature_name == "feature-from-notes":
                    feature_name = get_cached_feature_name(meeting_notes)
                
                st.info(f"🧩 Generating code prototype for: {feature_name}")
                
                # Generate code with validation
                def generate_code():
                    res = run_async(agent.generate_prototype_code(feature_name))
                    return res.get("code", "") if isinstance(res, dict) else str(res)
                
                result = generate_with_validation(
                    "code_prototype",
                    generate_code,
                    meeting_notes,
                    outputs_dir
                )
                
                if result:
                    out_base = AppConfig.OUTPUTS_DIR
                    project_root = Path(__file__).resolve().parents[2]
                    
                    # Generate best effort uses both LLM output and fallback scaffolds
                    saved = generate_best_effort(feature_name, project_root, out_base, result)
                
                if saved:
                    st.success(f"✅ Generated {len(saved)} code files:")
                    # Organize files by category
                    frontend_files = [f for f in saved if any(x in str(f).lower() for x in ['frontend', 'angular', 'react', 'vue', 'component', 'page', '/src/app/'])]
                    backend_files = [f for f in saved if any(x in str(f).lower() for x in ['backend', 'api', 'controller', 'service', 'dto', 'program.cs', '.cs']) and not any(x in str(f).lower() for x in ['frontend', 'component.ts', '.ts', '.html'])]
                    other_files = [f for f in saved if f not in frontend_files and f not in backend_files]
                    
                    # Validation check for full-stack projects
                    if frontend_files and not backend_files:
                        st.warning("⚠️ **Missing Backend Files!** Only frontend files were generated. This project has .NET backend.")
                        st.info("💡 Try regenerating or check if backend files were saved to a different location.")
                    
                    if frontend_files:
                        with st.expander(f"📱 Frontend Files ({len(frontend_files)})", expanded=True):
                            for f in frontend_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    if backend_files:
                        with st.expander(f"⚙️ Backend Files ({len(backend_files)})", expanded=True):
                            for f in backend_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    if other_files:
                        with st.expander(f"📄 Other Files ({len(other_files)})", expanded=True):
                            for f in other_files:
                                relative_path = f.relative_to(out_base) if f.is_relative_to(out_base) else f
                                st.code(f"✓ {relative_path}", language="text")
                    
                    st.info(f"💾 All files saved to: `outputs/prototypes/`")
                    
                    # CRITICAL: Set generated_result to mark as successful
                    generated_result = f"Generated {len(saved)} files:\n" + "\n".join(str(p.relative_to(out_base)) for p in saved)
                    
                    # Force UI refresh to show new outputs immediately
                    st.session_state.last_generation.append(artifact_type)
                    
                    # Set flag to notify Outputs tab
                    st.session_state.outputs_updated = True
                    st.session_state.outputs_updated_time = datetime.now().isoformat()
                    
                    st.success("✅ Outputs generated! Switch to 'Outputs' tab to view them.")
                    
                    # Force immediate UI refresh to show new outputs
                    # Only rerun if not in batch mode
                    if not st.session_state.get('batch_mode', False):
                        st.rerun()
                else:
                    st.warning("⚠️ No files generated")
                
                track_generation("code_prototype")
            elif artifact_type == "visual_prototype_dev":
                # Use ENHANCED prototype generator with FULL VALIDATION
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else ""
                feature_name = get_cached_feature_name(notes)
                
                # Retrieve RAG context for better prototype (synchronous call)
                retrieve_rag_with_cache(agent, meeting_notes, force_refresh=force_refresh)
                
                # Wrap in validation for quality scoring and auto-retry
                def generate_visual():
                    from components.enhanced_prototype_generator import EnhancedPrototypeGenerator
                    
                    generator = EnhancedPrototypeGenerator(agent)
                    html = run_async(generator.generate_prototype(notes))
                    
                    # Clean and sanitize
                    clean_html = strip_markdown_artifacts(html)
                    clean_html = sanitize_prototype_html(clean_html)
                    
                    # Fallback ONLY if generation truly failed
                    if not clean_html or len(clean_html) < 100 or ('<html' not in clean_html.lower() and '<body' not in clean_html.lower()):
                        template = pick_template_from_notes(notes)
                        clean_html = build_template_html(template, feature_name, notes)
                    
                    return clean_html
                
                # Use validation wrapper for quality & retry
                result = generate_with_validation(
                    "visual_prototype_dev",
                    generate_visual,
                    meeting_notes,
                    outputs_dir
                )
                
                if result:
                    generated_result = result
                    proto_dir = AppConfig.OUTPUTS_DIR / "prototypes"
                    proto_dir.mkdir(exist_ok=True)
                    (proto_dir / "developer_visual_prototype.html").write_text(result, encoding='utf-8')
                    
                    # IMMEDIATE SESSION STATE SYNC - Update prototype tracking flags
                    st.session_state.prototype_last_modified = datetime.now().isoformat()
                    st.session_state.dev_prototype_updated = True
                    st.session_state.prototype_cache_buster_dev = st.session_state.get('prototype_cache_buster_dev', 0) + 1
                    st.session_state.dev_prototype_force_mtime = time.time()
                    
                    # Update session state for outputs tab
                    st.session_state.last_generation.append("visual_prototype_dev")
                    st.session_state.outputs_updated = True
                    st.session_state.outputs_updated_time = datetime.now().isoformat()
                    st.success("✅ Visual Prototype generated!")
                    
                    track_generation("visual_prototype")
                    # Only rerun if not in batch mode
                    if not st.session_state.get('batch_mode', False):
                        st.rerun()
            
            # Log activity
            log_message = f"Generated {artifact_type}"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_message}")
            
            # Multi-Agent Analysis (if enabled)
            use_multi_agent = st.session_state.get('use_multi_agent', False)
            # Ensure it's explicitly True (not just truthy)
            if use_multi_agent is True and generated_result:
                st.markdown("---")
                st.markdown("### 🤖 Multi-Agent Analysis")
                st.info("Running expert analysis from 3 specialized agents...")
                
                try:
                    from agents.specialized_agents import MultiAgentOrchestrator
                    
                    orchestrator = MultiAgentOrchestrator(agent)
                    analysis = run_async(orchestrator.analyze_with_agents(
                        artifact_type,
                        generated_result[:3000] if len(generated_result) > 3000 else generated_result,
                        meeting_notes[:2000] if len(meeting_notes) > 2000 else meeting_notes
                    ))
                    
                    if analysis['agent_count'] > 0:
                        # Show average score
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            score = analysis['average_score']
                            color = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
                            st.metric("Average Score", f"{color} {score:.1f}/100")
                        with col2:
                            st.metric("Agents Analyzed", f"{analysis['agent_count']}/3")
                        
                        # Show each agent's opinion
                        for opinion in analysis['opinions']:
                            with st.expander(f"{opinion.agent_name} - Score: {opinion.score:.0f}/100", expanded=False):
                                st.markdown(f"**Perspective:** {opinion.perspective}")
                                st.markdown(f"**Feedback:** {opinion.feedback}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    if opinion.suggestions:
                                        st.markdown("**✅ Suggestions:**")
                                        for sug in opinion.suggestions[:5]:
                                            st.markdown(f"- {sug}")
                                
                                with col2:
                                    if opinion.concerns:
                                        st.markdown("**⚠️ Concerns:**")
                                        for con in opinion.concerns[:5]:
                                            st.markdown(f"- {con}")
                        
                        # Show synthesis
                        st.markdown("---")
                        st.markdown("### 📊 Synthesis")
                        st.markdown(analysis['synthesis'])
                        
                        # Save analysis to file
                        analysis_dir = outputs_dir / "analysis"
                        analysis_dir.mkdir(exist_ok=True)
                        analysis_file = analysis_dir / f"{artifact_type}_multi_agent_analysis.md"
                        
                        analysis_content = f"""# Multi-Agent Analysis: {artifact_type}

## Overall Score: {analysis['average_score']:.1f}/100

## Agent Opinions

"""
                        for opinion in analysis['opinions']:
                            analysis_content += f"""### {opinion.agent_name} (Score: {opinion.score}/100)

**Perspective:** {opinion.perspective}

**Feedback:** {opinion.feedback}

**Suggestions:**
{chr(10).join(f'- {s}' for s in opinion.suggestions)}

**Concerns:**
{chr(10).join(f'- {c}' for c in opinion.concerns)}

---

"""
                        analysis_content += f"""## Synthesis
                        
                        {analysis['synthesis']}
                        """
                        analysis_file.write_text(analysis_content, encoding='utf-8')
                        st.success(f"💾 Multi-agent analysis saved to: analysis/{artifact_type}_multi_agent_analysis.md")
                        
                    else:
                        st.warning("⚠️ Multi-agent analysis failed. Generated artifact is still available.")
                
                except Exception as e:
                    st.warning(f"⚠️ Multi-agent analysis encountered an error: {str(e)}")
                    st.info("Generated artifact is still available in Outputs tab.")
            
            # 🔥 FIX: Persist generation results in session state to survive reruns
            if generated_result:
                success_message = f"✅ {artifact_type.title()} generated successfully!"
                st.session_state['last_generation_success'] = success_message
                st.session_state['last_generation_timestamp'] = datetime.now().strftime("%H:%M:%S")
                st.session_state['last_generation_artifact'] = artifact_type
                st.success(success_message)
            else:
                error_message = f"❌ {artifact_type.title()} generation failed after all retry attempts."
                st.session_state['last_generation_success'] = None
                st.session_state['last_generation_error'] = error_message
                st.session_state['last_generation_timestamp'] = datetime.now().strftime("%H:%M:%S")
                st.session_state['last_generation_artifact'] = artifact_type
                st.error(error_message)
                st.info("Please check the validation details above and try again with different meeting notes or settings.")
            if use_multi_agent:
                st.success("🤖 Multi-agent analysis complete!")
            st.info("💡 Go to the 'Outputs' tab to view your generated content!")
            st.balloons()
            
            # ✅ FIX: Persist feedback UI - don't clear it on rerun
            # Mark that we should show feedback for this artifact
            st.session_state[f'show_feedback_ui_{artifact_type}'] = True
            
        # 💬 PERSISTENT FEEDBACK SECTION (shows even after rerun)
        # Display feedback UI if this artifact was recently generated
        if st.session_state.get(f'show_feedback_ui_{artifact_type}', False):
            st.markdown("---")
            st.markdown("### 💬 Was this output helpful?")
            st.caption(f"Provide feedback for: **{artifact_type.replace('_', ' ').title()}**")
            feedback_cols = st.columns([1, 1, 2])
            with feedback_cols[0]:
                if st.button("👍 Good", key=f"feedback_good_{artifact_type}", use_container_width=True):
                    try:
                        from components.finetuning_feedback import feedback_store, FeedbackEntry
                        # Get the actual output that was generated
                        generated_output = st.session_state.get(artifact_type, "")
                        # ✅ FIX: Record feedback for BOTH local and cloud models
                        model_used = st.session_state.get(f'model_used_{artifact_type}', 'unknown')
                        is_cloud = st.session_state.get(f'is_cloud_{artifact_type}', False)
                        
                        # Save positive feedback with the actual generated output
                        entry = FeedbackEntry.create(
                            artifact_type=artifact_type,
                            issue=f"Positive feedback - output was correct and helpful (Model: {model_used}, Cloud: {is_cloud})",
                            expected_style=str(generated_output)[:1000] if generated_output else "Continue generating similar quality output",
                            reference_code="",
                            meeting_context=st.session_state.get('meeting_notes', '')[:200],
                        )
                        feedback_store.add_feedback(entry)
                        feedback_count = len(feedback_store.list_feedback())
                        st.success(f"✅ Thanks! Positive feedback saved for training (Total: {feedback_count} entries).")
                        print(f"[FEEDBACK] Saved positive feedback for {artifact_type} using {model_used} (Cloud: {is_cloud}, Total: {feedback_count})")
                    except Exception as e:
                        st.error(f"❌ Failed to save feedback: {e}")
                        import traceback
                        st.code(traceback.format_exc())
            with feedback_cols[1]:
                if st.button("👎 Needs Improvement", key=f"feedback_bad_{artifact_type}", use_container_width=True):
                    st.session_state['show_feedback_form'] = True
                    st.session_state['feedback_artifact_type'] = artifact_type
                    st.rerun()
            with feedback_cols[2]:
                st.caption("Help the AI learn by providing feedback on generated artifacts")
            
            # Show feedback form if user clicked "Needs Improvement"
            if st.session_state.get('show_feedback_form') and st.session_state.get('feedback_artifact_type') == artifact_type:
                with st.expander("📝 Provide Detailed Feedback", expanded=True):
                    from components.finetuning_feedback import feedback_store, FeedbackEntry
                    
                    st.markdown("**Tell the AI what went wrong and how to fix it:**")
                    fb_issue = st.text_area(
                        "What was wrong with this output?",
                        height=80,
                        placeholder="E.g., 'Used wrong naming convention', 'Missing error handling', etc.",
                        key=f"quick_fb_issue_{artifact_type}"
                    )
                    fb_expected = st.text_area(
                        "What should it look like instead?",
                        height=80,
                        placeholder="Describe the correct approach or paste example code",
                        key=f"quick_fb_expected_{artifact_type}"
                    )
                    
                    fb_cols = st.columns(2)
                    with fb_cols[0]:
                        if st.button("💾 Save Feedback", key=f"save_quick_fb_{artifact_type}", type="primary"):
                            if fb_issue.strip() and fb_expected.strip():
                                # ✅ FIX: Include model info in feedback
                                model_used = st.session_state.get(f'model_used_{artifact_type}', 'unknown')
                                is_cloud = st.session_state.get(f'is_cloud_{artifact_type}', False)
                                
                                entry = FeedbackEntry.create(
                                    artifact_type=artifact_type,
                                    issue=f"{fb_issue} (Model: {model_used}, Cloud: {is_cloud})",
                                    expected_style=fb_expected,
                                    reference_code="",
                                    meeting_context=st.session_state.get('meeting_notes', '')[:200],
                                )
                                feedback_store.add_feedback(entry)
                                st.success("✅ Feedback saved! It will be used in the next training.")
                                st.session_state['show_feedback_form'] = False
                                st.balloons()
                            else:
                                st.warning("Please fill in both fields")
                    with fb_cols[1]:
                        if st.button("Cancel", key=f"cancel_quick_fb_{artifact_type}"):
                            st.session_state['show_feedback_form'] = False
                            st.rerun()
            
            # RAG Context Viewer (for debugging/verification)
            if st.session_state.get("last_rag_debug"):
                st.markdown("---")
                with st.expander("🐞 View RAG Context (Debug)", expanded=False):
                    st.caption(f"Query: `{st.session_state.get('last_rag_query', 'N/A')}`")
                    st.caption(f"Retrieved {len(st.session_state['last_rag_debug'])} chunks")
                    
                    for i, chunk in enumerate(st.session_state['last_rag_debug'][:10]):
                        st.markdown(f"**{i+1}. {chunk['path']}** (Score: {chunk['score']})")
                        st.code(chunk['content_preview'], language="text")
            
            # Force refresh outputs
            st.session_state.last_generation.append(artifact_type)
    
    except Exception as e:
        # 💾 Store error in session state (persists after rerun!)
        st.session_state.last_generation_result = {
            'artifact': artifact_type,
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime("%H:%M:%S")
        }
        
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def run_complete_workflow():
    """Run complete workflow"""
    try:
        with st.spinner("🚀 Running complete workflow..."):
            notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
            if not notes_path.exists():
                st.error("❌ Please upload meeting notes first!")
                return
            
            agent, _ = get_current_agent()
            if not agent:
                return
            
            # Run workflow with cached agent
            result = run_async(agent.run_complete_workflow(".", str(notes_path)))
            
            # Log activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Complete workflow executed")
            
            st.success("✅ Complete workflow finished!")
            st.balloons()
            track_generation("complete_workflow", cost=0.5, time_saved=2.0)
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def generate_visual_prototype_with_multi_agent(
    idea: str,
    mode: str = "pm",
    source: str = "manual"
) -> str:
    """
    Generate HIGH-QUALITY visual prototype using 3-stage multi-agent pipeline.
    
    Pipeline:
    1. Analyzer: Deep feature understanding
    2. Generator: Tech-stack-specific code generation
    3. Critic: Quality review and potential regeneration
    
    Args:
        idea: Feature idea or meeting notes content
        mode: "pm" or "dev" - determines save path
        source: Input source ("manual" or "meeting_notes")
        
    Returns:
        Generated HTML content
    """
    from agents.prototype_agents import PrototypeOrchestrator, TechStack
    from components.tech_stack_detector import get_tech_stack_from_context
    
    # Get agent
    agent, _ = get_current_agent()
    if not agent:
        return ""
    
    # Get RAG context
    ext_ctx = get_extended_project_context()
    run_async(agent.retrieve_rag_context(f"visual prototype {idea[:500]} {ext_ctx[:1000]}"))
    rag_context = agent.rag_context  # Access the attribute directly
    
    # Detect tech stack from context
    tech_stack = get_tech_stack_from_context(rag_context)
    
    # Convert to prototype agent format
    from agents.prototype_agents import TechStack as PTechStack
    proto_tech_stack = PTechStack(
        framework=tech_stack.framework,
        language=tech_stack.language,
        styling=tech_stack.styling,
        components=tech_stack.components,
        api_tech=tech_stack.api_tech
    )
    
    # Create orchestrator and run pipeline
    orchestrator = PrototypeOrchestrator(agent)
    result = run_async(orchestrator.generate_prototype(
        meeting_notes=idea,
        tech_stack=proto_tech_stack,
        rag_context=rag_context,
        max_iterations=2
    ))
    
    # Display pipeline results
    with st.expander("🤖 Multi-Agent Prototype Pipeline", expanded=False):
        st.markdown(f"""
        **Tech Stack Detected:** {tech_stack.framework} + {tech_stack.language}
        
        **Pipeline Results:**
        - **Iterations:** {result['iterations']}
        - **Final Quality Score:** {result['final_score']:.1f}/100
        - **Framework:** {result['tech_stack'].framework}
        - **Components:** {', '.join(result['tech_stack'].components) if result['tech_stack'].components else 'None'}
        """)
        
        # Show analysis
        st.markdown("### 📋 Feature Analysis")
        analysis = result['analysis']
        st.write(f"**Feature Name:** {analysis.feature_name}")
        st.write(f"**Core Functionality:** {', '.join(analysis.core_functionality[:3])}")
        st.write(f"**UI Components:** {', '.join(analysis.ui_components_needed[:5])}")
        
        # Show reviews
        st.markdown("### 🔍 Quality Reviews")
        for i, review in enumerate(result['reviews']):
            score_color = "🟢" if review.score >= 80 else "🟡" if review.score >= 60 else "🔴"
            st.markdown(f"**Iteration {i+1}:** {score_color} {review.score:.1f}/100")
            if review.strengths:
                st.markdown(f"✅ {', '.join(review.strengths[:2])}")
            if review.weaknesses:
                st.markdown(f"⚠️ {', '.join(review.weaknesses[:2])}")
    
    # Get final HTML
    prototype = result['prototype']
    html = prototype.framework_specific_code
    
    # Clean and sanitize
    html = strip_markdown_artifacts(html)
    html = sanitize_prototype_html(html)
    
    return html


def generate_visual_prototype(idea: str, source: str = "manual"):
    """
    Generate visual prototype for PM mode using ENHANCED generator.
    
    Args:
        idea: Feature idea or meeting notes content
        source: Input source ("manual" or "meeting_notes")
    """
    try:
        with st.spinner("🎨 Creating enhanced visual prototype..."):
            st.markdown("**Stage 1:** Extracting requirements... **Stage 2:** Generating HTML...")
            
            agent, _ = get_current_agent()
            if not agent:
                return
            
            # Use enhanced generator
            from components.enhanced_prototype_generator import EnhancedPrototypeGenerator
            generator = EnhancedPrototypeGenerator(agent)
            result = run_async(generator.generate_prototype(idea))
            
            # Strip markdown artifacts and sanitize
            html = strip_markdown_artifacts(result or "")
            html = sanitize_prototype_html(html)
            
            # Fallback ONLY if generation truly failed (empty or minimal content)
            # Check for actual HTML structure, not just length
            if not html or len(html) < 100 or ('<html' not in html.lower() and '<body' not in html.lower()):
                st.warning("⚠️ Enhanced generation failed, using template fallback...")
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                notes = notes_path.read_text(encoding='utf-8') if notes_path.exists() else idea
                template = pick_template_from_notes(notes)
                html = build_template_html(template, "PM Visual Prototype", notes)
            
            # Save to PM visual path - SINGLE FILE
            out = AppConfig.OUTPUTS_DIR / "prototypes" / "pm_visual_prototype.html"
            out.parent.mkdir(exist_ok=True)
            out.write_text(html, encoding='utf-8')
            
            # IMMEDIATE SESSION STATE SYNC - Update prototype tracking flags
            st.session_state.prototype_last_modified = datetime.now().isoformat()
            st.session_state.pm_prototype_updated = True
            st.session_state.prototype_cache_buster_pm = st.session_state.get('prototype_cache_buster_pm', 0) + 1
            st.session_state.pm_prototype_force_mtime = time.time()
            
            source_label = "meeting notes" if source == "meeting_notes" else "manual input"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] PM visual prototype generated from {source_label}")
            
            st.success(f"✅ Enhanced visual prototype generated from {source_label}!")
            st.info(f"📁 Saved to: prototypes/pm_visual_prototype.html")
            
            # Force rerun to show in editor immediately
            st.rerun()
            st.balloons()
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def generate_pm_jira(idea: str, source: str = "manual"):
    """
    Generate JIRA tasks for PM mode.
    
    Args:
        idea: Feature idea or meeting notes content
        source: Input source ("manual" or "meeting_notes")
    """
    try:
        with st.spinner("📋 Generating JIRA tasks..."):
            agent, _ = get_current_agent()
            if not agent:
                return
            agent.meeting_notes = idea
            
            result = run_async(agent.generate_jira_only())
            
            # Strip markdown artifacts
            result = strip_markdown_artifacts(result or "")
            
            # Save to PM-specific JIRA file
            if result:
                out = AppConfig.OUTPUTS_DIR / "documentation" / "pm_jira_tasks.md"
                out.parent.mkdir(exist_ok=True)
                out.write_text(result, encoding='utf-8')
            
            source_label = "meeting notes" if source == "meeting_notes" else "manual input"
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] PM JIRA tasks generated from {source_label}")
            
            st.success(f"✅ JIRA tasks generated from {source_label}!")
            st.info(f"📁 Saved to: documentation/pm_jira_tasks.md")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

def ask_ai(question: str, context: str = ""):
    """Ask AI a question with FULL RAG context from repository"""
    try:
        with st.spinner("🔍 Retrieving context from your repository..."):
            agent, _ = get_current_agent()
            if not agent:
                return
            
            # Use PM input based on their selection (meeting notes or manual input)
            pm_source = st.session_state.get('pm_source', 'meeting_notes')
            pm_idea = st.session_state.get('pm_idea', '')
            
            if pm_source == "meeting_notes":
                # Use meeting notes
                notes_path = AppConfig.INPUTS_DIR / AppConfig.MEETING_NOTES_FILE
                if notes_path.exists():
                    meeting_notes = notes_path.read_text(encoding='utf-8')
                    context = f"{context}\n\nMeeting Notes:\n{meeting_notes}" if context else meeting_notes
            elif pm_idea:
                # Use manual input from PM
                context = f"{context}\n\nPM Idea:\n{pm_idea}" if context else f"PM Idea:\n{pm_idea}"
             
            # Retrieve FULL RAG context from repository
            st.info("🧠 AI is analyzing your entire codebase...")
            ext_ctx = get_extended_project_context()
            rag_query = f"{question} {context} {ext_ctx}"
            run_async(agent.retrieve_rag_context(rag_query))
            
            # Log RAG activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Retrieved RAG context for Ask AI")
            
            prompt = f"""
You are an expert product and technical advisor with DEEP knowledge of this specific project.

PROJECT CONTEXT (from RAG):
{agent.rag_context[:3000]}

USER PROVIDED CONTEXT: {context if context else "No additional context provided"}

QUESTION: {question}

IMPORTANT: 
- You have access to the actual codebase through RAG context above
- Reference specific files, patterns, and technologies from the project
- Be specific about how this fits with the existing architecture
- Provide realistic estimates based on the actual tech stack
- Mention any potential conflicts with existing code

Provide a helpful, actionable answer that's tailored to THIS specific project.
"""
            
            response = run_async(agent._call_ai(
                prompt,
                "You are a helpful product and technical advisor with deep knowledge of this specific project. Be clear, concise, and actionable.",
                artifact_type="documentation"
            ))
            
            # Store in conversation history
            st.session_state.ai_conversation.append((question, response))
            
            # Display response with context indicator
            st.success("✅ AI Response (with full project context):")
            st.markdown(response)
            
            # Show what context was used
            with st.expander("🔍 RAG Context Used"):
                st.text(f"Retrieved {len(agent.rag_context)} characters of context from your repository")
                st.text("This includes: code files, architecture, patterns, dependencies, and more")
            
            # Log activity
            st.session_state.rag_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Asked AI with RAG: {question[:30]}...")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# =============================================================================
# PROTOTYPE HTML SANITIZER AND FALLBACKS
# =============================================================================

def strip_markdown_artifacts(text: str) -> str:
    """
    Remove ALL markdown artifacts from generated content.
    Critical for preventing code fence markers in generated HTML/code.
    """
    import re
    if not text:
        return ""
    
    # Remove code fences (```html, ```python, etc.)
    text = re.sub(r'^```[\w\-]*\s*\n?', '', text, flags=re.MULTILINE)  # Opening fences
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)  # Closing fences
    text = re.sub(r'```[\w\-]*\n', '', text)  # Mid-content fences
    text = text.strip('`')  # Stray backticks
    
    return text.strip()


def sanitize_prototype_html(html: str) -> str:
    """Strip dangerous tags, markdown artifacts, and ensure a minimal valid shell."""
    import re
    if not html:
        return ""
    
    # STEP 1: Strip markdown artifacts FIRST (before any other processing)
    html = strip_markdown_artifacts(html)
    
    # STEP 2: Remove only iframes (keep all JavaScript for functionality)
    html = re.sub(r"<iframe[\s\S]*?</iframe>", "", html, flags=re.IGNORECASE)
    
    # STEP 3: Ensure DOCTYPE
    if "<!DOCTYPE" not in html[:200]:
        html = "<!DOCTYPE html>\n" + html
    
    return html

# Notes-driven template chooser and builders

def pick_template_from_notes(notes: str) -> str:
    n = (notes or "").lower()
    # Heuristics by keywords
    if any(k in n for k in ["chart", "kpi", "analytics", "dashboard", "statistics", "metrics"]):
        return "dashboard"
    if any(k in n for k in ["login", "register", "authentication", "auth"]):
        return "auth"
    if any(k in n for k in ["product", "catalog", "e-commerce", "cart", "checkout", "sku"]):
        return "ecommerce"
    if any(k in n for k in ["kanban", "board", "tasks", "swimlane"]):
        return "kanban"
    if any(k in n for k in ["upload", "file", "import csv", "import xlsx"]):
        return "uploader"
    if any(k in n for k in ["q&a", "faq", "question", "answer", "knowledge base"]):
        return "qna"
    if any(k in n for k in ["chat", "assistant", "message", "bot"]):
        return "chat"
    if any(k in n for k in ["crud", "table", "form", "admin", "manage"]):
        return "table_form"
    return "dashboard"


def build_template_html(template: str, title: str, notes: str) -> str:
    import html as htmlmod
    safe_notes = htmlmod.escape((notes or "")[:800])
    common_head = """
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{TITLE}</title>
  <style>
    body {{ background:#f7f7fb; font-family: Segoe UI, Arial; }}
    .container {{ max-width: 1100px; margin: 24px auto; padding: 16px; background:#fff; border-radius:12px; box-shadow:0 10px 30px rgba(0,0,0,.06) }}
    h1 {{ color:#111827; margin:0 0 8px; }}
    p {{ color:#4b5563; }}
    .btn {{ background:#667eea; color:#fff; border:0; padding:8px 16px; border-radius:10px; cursor:pointer; }}
    input,select,textarea {{ padding:8px; border:1px solid #e5e7eb; border-radius:8px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ border-bottom:1px solid #e5e7eb; padding:8px; text-align:left; }}
  </style>
""".replace("{TITLE}", title)
    head = common_head
    body = ""
    if template == "dashboard":
        head += "  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>\n"
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Dashboard</h1>
    <p>Based on meeting notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <canvas id=\"chart1\" height=\"120\"></canvas>
  </div>
  <script>
    const ctx = document.getElementById('chart1');
    new Chart(ctx, { type: 'bar', data: { labels: ['A','B','C','D'], datasets: [{ label:'Values', data:[12,19,5,9], backgroundColor:'#667eea' }] }, options: { responsive:true } });
  </script>
</body>
</html>
"""
    elif template == "table_form":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Admin Table & Form</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <table>
      <thead><tr><th>Name</th><th>Status</th></tr></thead>
      <tbody id=\"rows\"><tr><td>Alpha</td><td>Active</td></tr></tbody>
    </table>
    <h3>Create</h3>
    <input id=\"name\" placeholder=\"Name\"/> <select id=\"status\"><option>Active</option><option>Paused</option></select>
    <button class=\"btn\" onclick=\"addRow()\">Add</button>
  </div>
  <script>
    function addRow(){
      const n = document.getElementById('name').value || 'Item';
      const s = document.getElementById('status').value;
      const tr = document.createElement('tr');
      tr.innerHTML = '<td>' + n + '</td><td>' + s + '</td>';
      document.getElementById('rows').appendChild(tr);
    }
  </script>
</body>
</html>
"""
    elif template == "auth":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Authentication</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <h3>Login</h3>
    <input placeholder=\"Email\"/> <input type=\"password\" placeholder=\"Password\"/> <button class=\"btn\">Login</button>
    <h3>Register</h3>
    <input placeholder=\"Email\"/> <input type=\"password\" placeholder=\"Password\"/> <button class=\"btn\">Create</button>
  </div>
</body>
</html>
"""
    elif template == "ecommerce":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Catalog</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <div style=\"display:grid;grid-template-columns:repeat(3,1fr);gap:12px\">
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product A</h3><button class=\"btn\">Add to cart</button></div>
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product B</h3><button class=\"btn\">Add to cart</button></div>
      <div style=\"border:1px solid #e5e7eb;border-radius:10px;padding:12px\"><h3>Product C</h3><button class=\"btn\">Add to cart</button></div>
    </div>
  </div>
</body>
</html>
"""
    elif template == "qna":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Q&A</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <h3>Ask</h3>
    <input id=\"q\" placeholder=\"Your question\"/> <button class=\"btn\" onclick=\"ask()\">Ask</button>
    <div id=\"answers\" style=\"margin-top:12px\"></div>
  </div>
  <script>
    function ask(){
      var q = document.getElementById('q').value;
      var d = document.createElement('div');
      d.textContent = 'Q: ' + q + ' → A: (placeholder)';
      document.getElementById('answers').appendChild(d);
    }
  </script>
</body>
</html>
"""
    elif template == "kanban":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>Kanban</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <div style=\"display:grid;grid-template-columns:repeat(3,1fr);gap:12px\">
      <div><h3>Todo</h3><ul id=\"todo\"><li>Task 1</li></ul></div>
      <div><h3>Doing</h3><ul id=\"doing\"><li>Task 2</li></ul></div>
      <div><h3>Done</h3><ul id=\"done\"><li>Task 3</li></ul></div>
    </div>
  </div>
</body>
</html>
"""
    elif template == "uploader":
        body = """
</head>
<body>
  <div class=\"container\">
    <h1>File Uploader</h1>
    <p>Notes:</p>
    <pre style=\"white-space:pre-wrap\">[[NOTES]]</pre>
    <input type=\"file\" /> <button class=\"btn\">Upload</button>
  </div>
</body>
</html>
"""
    elif template == "chat":
        body = """
</head>
<body>
  <div class=\"container\" style=\"display:flex;flex-direction:column;height:80vh\">
    <h1>Chat</h1>
    <div id=\"log\" style=\"flex:1;overflow:auto;border:1px solid #e5e7eb;border-radius:10px;padding:8px\"></div>
    <div style=\"display:flex;gap:8px;margin-top:8px\"><input id=\"msg\" style=\"flex:1\" placeholder=\"Type message\"/><button class=\"btn\" onclick=\"send()\">Send</button></div>
  </div>
  <script>
    function send(){
      var m = document.getElementById('msg').value;
      var d = document.createElement('div');
      d.textContent = 'You: ' + m;
      document.getElementById('log').appendChild(d);
      document.getElementById('msg').value = '';
    }
  </script>
</body>
</html>
"""
    else:
        body = "</head><body><div class=\"container\"><h1>Prototype</h1><p>No template selected.</p></div></body></html>"
    return (head + body).replace("[[NOTES]]", safe_notes)

# =============================================================================
# OUTPUT MANAGEMENT HELPERS
# =============================================================================

def clear_feature_outputs():
    """
    Clear artifacts tied to a specific feature so new notes don't mix with old outputs.
    
    This is critical when switching tech stacks (e.g., Angular → React, WPF → Web)
    because we need to completely remove old prototype directories and regenerate
    with the correct stack.
    
    Uses aggressive shutil.rmtree to ensure complete removal.
    """
    import shutil
    base = AppConfig.OUTPUTS_DIR
    for sub in [
        "visualizations",
        "documentation",
        "prototypes",
        "workflows",
        "analysis",
        "context",
    ]:
        try:
            p = base / sub
            if p.exists():
                # Aggressive deletion: Delete entire tree, then recreate empty directory
                try:
                    shutil.rmtree(p)
                    p.mkdir(exist_ok=True)
                except Exception as e:
                    # If shutil.rmtree fails, try manual deletion as fallback
                    for f in p.rglob("*"):
                        try:
                            if f.is_file():
                                f.unlink(missing_ok=True)
                        except Exception:
                            pass
                    
                    # Try to remove subdirectories
                    subdirs = [d for d in p.rglob("*") if d.is_dir()]
                    subdirs.sort(key=lambda x: len(x.parts), reverse=True)
                    for d in subdirs:
                        if d.exists() and d != p:
                            try:
                                d.rmdir()
                            except (OSError, PermissionError):
                                # Directory not empty or permission denied
                                pass
        except Exception:
            pass

# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """
    Main application entry point.
    
    Orchestrates the entire application flow:
    1. Configure page settings
    2. Apply custom styling
    3. Initialize session state
    4. Render sidebar and header
    5. Route to appropriate mode (Developer/PM)
    6. Display footer with version and contact info
    """
    # Page config
    st.set_page_config(
        page_title=AppConfig.APP_TITLE,
        page_icon=AppConfig.APP_ICON,
        layout=AppConfig.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    init_session_state()
    
    # Initialize Artifact Router (for intelligent model routing)
    if 'artifact_router' not in st.session_state:
        from ai.artifact_router import ArtifactRouter
        st.session_state.artifact_router = ArtifactRouter()
        print("[INFO] Artifact Router initialized")
    
    # Initialize Output Validator (for quality assurance)
    if 'output_validator' not in st.session_state:
        from ai.output_validator import OutputValidator
        st.session_state.output_validator = OutputValidator()
        print("[INFO] Output Validator initialized")
    
    # Initialize auto-ingestion system
    # Note: Auto-ingestion is controlled via rag/config.yaml
    # Enable it there and use the sidebar controls to manage it
    # Automatic startup initialization is disabled to prevent potential conflicts
    # Users can manually start via sidebar "🔄 Auto-Ingestion Status" section
    
    # Render sidebar
    render_sidebar()
    
    # Render header
    render_header()
    
    # Mode selection or mode interface
    if st.session_state.mode is None:
        render_mode_selection()
    elif st.session_state.mode == "developer":
        # Gate by role: Developer or Admin
        if has_role(["Developer", "Admin"]):
            render_dev_mode()
        else:
            st.warning("You need Developer or Admin role to access Developer Mode.")
    elif st.session_state.mode == "product":
        # PM or Admin can access PM mode
        if has_role(["PM", "Admin", "Developer", "Viewer"]):
            render_pm_mode()
        else:
            st.warning("You lack permission to access this mode.")
    
    # Render footer
    render_footer()

# =============================================================================
# FEATURE NAME EXTRACTION
# =============================================================================

def cache_feature_name(notes: str) -> str:
    """Cache and return the extracted feature name for provided meeting notes."""
    import hashlib

    stripped = (notes or "").strip()
    feature_name = extract_feature_name_from_notes(stripped)
    cache_key = hashlib.sha256(stripped.encode('utf-8')).hexdigest() if stripped else ""

    try:
        st.session_state.feature_name_cache = {
            'hash': cache_key,
            'name': feature_name,
            'updated_at': datetime.now().isoformat()
        }
    except Exception:
        pass

    return feature_name


def get_cached_feature_name(notes: str) -> str:
    """Retrieve feature name from cache, computing it if necessary."""
    stripped = (notes or "").strip()
    if not stripped:
        return "feature"

    import hashlib

    cache_key = hashlib.sha256(stripped.encode('utf-8')).hexdigest()
    cache = None
    try:
        cache = st.session_state.get('feature_name_cache')
    except Exception:
        cache = None

    if cache and cache.get('hash') == cache_key:
        cached_name = cache.get('name')
        if cached_name:
            return cached_name

    return cache_feature_name(stripped)


def extract_feature_name_from_notes(notes: str) -> str:
    """
    Extract feature name from meeting notes using intelligent pattern matching.
    
    This function implements a cascading strategy to identify the feature name:
    1. Look for explicit "Feature: Name" declarations
    2. Extract from first Markdown H1 heading (# Heading)
    3. Use first non-empty line as fallback
    
    The extracted name is used for:
    - Naming generated prototype files
    - Creating appropriate directory structures
    - Ensuring outputs are feature-specific
    
    Args:
        notes: Raw meeting notes text (Markdown or plain text)
    
    Returns:
        Feature name (max 60 chars) or "feature" if nothing found
    
    Examples:
        "Feature: User Authentication" -> "User Authentication"
        "# Shopping Cart Redesign" -> "Shopping Cart Redesign"
        "Implement payment gateway..." -> "Implement payment gateway"
    """
    import re
    if not notes:
        return "feature"
    
    # Try explicit "Feature: Name" or "Feature - Name"
    m = re.search(r"^\s*#*\s*Feature[:\-]\s*(.+)$", notes, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        return m.group(1).strip()[:60] or "feature"
    
    # Try first H1 Markdown heading
    m = re.search(r"^\s*#\s*(.+)$", notes, flags=re.MULTILINE)
    if m:
        return m.group(1).strip()[:60]
    
    # Fallback to first non-empty line
    for line in notes.splitlines():
        if line.strip():
            return line.strip()[:60]
    
    return "feature"

if __name__ == "__main__":
    main()
