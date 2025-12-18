"""
FastAPI application entry point for Architect.AI backend services.
"""

import sys
from pathlib import Path
import asyncio
import os

# Disable ChromaDB telemetry BEFORE any chromadb imports
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
os.environ.setdefault("CHROMA_TELEMETRY", "False")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "True")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from backend.core.middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    StructuredLoggingMiddleware,
    setup_rate_limiting
)
from backend.core.config import settings
from backend.models.errors import ErrorResponse

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Suppress ChromaDB telemetry errors (posthog API mismatch)
# Set this before any ChromaDB imports to prevent errors during initialization
chromadb_telemetry_logger = logging.getLogger("chromadb.telemetry")
chromadb_telemetry_logger.setLevel(logging.CRITICAL)
chromadb_posthog_logger = logging.getLogger("chromadb.telemetry.product.posthog")
chromadb_posthog_logger.setLevel(logging.CRITICAL)

# Suppress ChromaDB HNSW duplicate embedding warnings (harmless - upsert handles them)
chromadb_hnsw_logger = logging.getLogger("chromadb.segment.impl.vector.local_persistent_hnsw")
chromadb_hnsw_logger.setLevel(logging.ERROR)  # Only show errors, not warnings about duplicates

logger = logging.getLogger(__name__)

# UTF-8 console wrapper for Windows compatibility
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

# Create FastAPI app
app = FastAPI(
    title="Architect.AI API",
    description="FastAPI backend for interactive architecture visualization and artifact generation",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Customize OpenAPI schema
def custom_openapi():
    """Customize OpenAPI schema with additional metadata."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom metadata
    openapi_schema["info"]["contact"] = {
        "name": "Architect.AI Support",
        "email": "support@architect.ai"
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication"
        },
        "APIKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

PHASE_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "database": {"title": "Database", "description": "Initializing database"},
    "model_registry": {"title": "Model Registry", "description": "Loading model catalog"},
    "rag_indexing": {"title": "RAG Index", "description": "Indexing user projects"},
    "knowledge_graph": {"title": "Knowledge Graph", "description": "Building knowledge graph"},
    "pattern_mining": {"title": "Pattern Mining", "description": "Analyzing patterns"},
    "universal_context": {"title": "Universal Context", "description": "Building universal context"},
    "watchers": {"title": "Project Watchers", "description": "Starting directory watchers"},
}


def _init_system_status() -> Dict[str, Any]:
    """Create default system status payload for health checks."""
    now = datetime.now().isoformat()
    return {
        "ready": False,
        "overall_status": "starting",
        "message": "Bootstrapping backend services...",
        "last_updated": now,
        "phases": {
            phase: {
                "name": phase,
                "title": meta["title"],
                "status": "pending",
                "message": meta["description"],
                "progress": 0.0,
                "last_updated": now,
            }
            for phase, meta in PHASE_DEFINITIONS.items()
        },
    }


app.state.system_status = _init_system_status()


def _get_system_status() -> Dict[str, Any]:
    if not hasattr(app.state, "system_status") or not app.state.system_status:
        app.state.system_status = _init_system_status()
    return app.state.system_status


def _evaluate_overall_status() -> None:
    """Evaluate if all required phases are complete and mark system ready."""
    system_status = _get_system_status()
    if system_status.get("overall_status") == "error":
        return
    phases = system_status.get("phases", {})
    if not phases:
        return
    
    # Only check phases that are defined (not all phases in dict)
    required_phases = set(PHASE_DEFINITIONS.keys())
    phase_statuses = {
        name: info.get("status")
        for name, info in phases.items()
        if name in required_phases
    }
    
    # Check if all required phases are complete or skipped
    if phase_statuses and all(status in {"complete", "skipped"} for status in phase_statuses.values()):
        if not system_status.get("ready"):
            logger.info(f"✅ [SYSTEM_STATUS] All phases complete: {phase_statuses}")
            mark_system_ready("System initialization complete")


def update_phase_status(
    phase: str,
    status: str,
    message: Optional[str] = None,
    progress: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Update individual phase status for health reporting."""
    system_status = _get_system_status()
    phase_data = system_status["phases"].setdefault(
        phase,
        {
            "name": phase,
            "title": PHASE_DEFINITIONS.get(phase, {}).get("title", phase.replace("_", " ").title()),
            "status": "pending",
            "message": "",
            "progress": 0.0,
        },
    )
    phase_data["status"] = status
    if message:
        phase_data["message"] = message
    if progress is not None:
        phase_data["progress"] = max(0.0, min(100.0, float(progress)))
    if details:
        current_details = phase_data.setdefault("details", {})
        current_details.update(details)
    timestamp = datetime.now().isoformat()
    phase_data["last_updated"] = timestamp
    system_status["last_updated"] = timestamp
    if status == "error":
        system_status["overall_status"] = "error"
        system_status["ready"] = False
        if message:
            system_status["message"] = message
    _evaluate_overall_status()


def set_overall_status(status: str, message: Optional[str] = None) -> None:
    """Update overall system status message."""
    system_status = _get_system_status()
    system_status["overall_status"] = status
    if message:
        system_status["message"] = message
    system_status["last_updated"] = datetime.now().isoformat()


def mark_system_ready(message: str) -> None:
    """Mark the backend as ready for requests."""
    system_status = _get_system_status()
    system_status["ready"] = True
    set_overall_status("ready", message)
    logger.info(f"✅ [SYSTEM_STATUS] System marked as ready: {message}")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters - last added is first executed)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Setup rate limiting
limiter = setup_rate_limiting(app)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions with structured logging."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    error_response = ErrorResponse(
        error="InternalServerError",
        message=str(exc) if settings.debug else "An internal server error occurred",
        type=type(exc).__name__,
        request_id=request_id,
        timestamp=datetime.now().isoformat()  # Convert to ISO format string
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(exclude_none=True)
    )

# Health check endpoint
@app.get("/health")
@app.get("/api/health")  # Also available under /api for consistency
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    from backend.core.cache import get_cache_manager
    from backend.core.metrics import get_metrics_collector
    
    cache_stats = get_cache_manager().get_stats()
    metrics_stats = get_metrics_collector().get_stats()
    system_status = _get_system_status()
    
    # Ensure ready is always a boolean, never None/undefined
    ready = bool(system_status.get("ready", False))
    overall_status = system_status.get("overall_status", "initializing")
    message = system_status.get("message", "System initializing...")
    phases = system_status.get("phases", {})
    last_updated = system_status.get("last_updated")
    
    # Ensure phases are properly formatted (only include defined phases)
    formatted_phases = {}
    for phase_name in PHASE_DEFINITIONS.keys():
        if phase_name in phases:
            formatted_phases[phase_name] = phases[phase_name]
        else:
            # Include pending phase if not yet started
            formatted_phases[phase_name] = {
                "name": phase_name,
                "title": PHASE_DEFINITIONS[phase_name]["title"],
                "status": "pending",
                "message": PHASE_DEFINITIONS[phase_name]["description"],
                "progress": 0.0,
            }
    
    response = {
        "status": "ready" if ready else overall_status,
        "service": "architect-ai-backend",
        "version": settings.app_version,
        "ready": ready,  # Explicitly ensure boolean
        "overall_status": overall_status,
        "message": message,
        "last_updated": last_updated,
        "phases": formatted_phases,  # Use formatted phases
        "cache": cache_stats,
        "metrics": {
            "counters": len(metrics_stats.get("counters", {})),
            "gauges": len(metrics_stats.get("gauges", {})),
            "timers": len(metrics_stats.get("timers", {}))
        }
    }
    
    # Only log health checks at DEBUG level (not INFO) to reduce noise
    # Only log at INFO level when there's a problem or system not ready
    if not ready:
        phase_summary = {name: info.get("status", "unknown") for name, info in formatted_phases.items()}
        logger.info(f"🏥 [HEALTH] System not ready: overall_status={overall_status}, phases={phase_summary}")
    else:
        logger.debug(f"🏥 [HEALTH] OK: ready={ready}, overall_status={overall_status}")
    
    return response

# Metrics endpoint
@app.get("/metrics")
async def metrics_endpoint() -> str:
    """Prometheus metrics endpoint."""
    from backend.core.metrics import get_metrics_collector
    
    if not settings.metrics_enabled:
        return "# Metrics disabled"
    
    collector = get_metrics_collector()
    return collector.export_prometheus()

# Metrics stats endpoint (JSON)
@app.get("/api/metrics/stats")
async def metrics_stats() -> Dict[str, Any]:
    """Get metrics statistics in JSON format."""
    from backend.core.metrics import get_metrics_collector
    
    if not settings.metrics_enabled:
        return {"error": "Metrics disabled"}
    
    collector = get_metrics_collector()
    return collector.get_stats()

# Root endpoint
@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Architect.AI API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Database initialization
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        from backend.core.database import init_db
        from backend.core.config import settings
        
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        set_overall_status("initializing", "Bootstrapping backend services")
        update_phase_status("database", "running", "Initializing database...")
        init_db()
        update_phase_status("database", "complete", "Database initialized")
        logger.info("Database initialized")
        
        # Refresh cloud models on startup to ensure they're registered
        try:
            from backend.services.model_service import get_service as get_model_service
            model_service = get_model_service()
            
            # Log API key status
            has_gemini = bool(settings.google_api_key or settings.gemini_api_key)
            has_groq = bool(settings.groq_api_key)
            has_openai = bool(settings.openai_api_key)
            has_anthropic = bool(settings.anthropic_api_key)
            
            logger.info(f"API Keys Status - Gemini: {'✅' if has_gemini else '❌'}, Groq: {'✅' if has_groq else '❌'}, OpenAI: {'✅' if has_openai else '❌'}, Anthropic: {'✅' if has_anthropic else '❌'}")
            
            update_phase_status("model_registry", "running", "Refreshing cloud model registry...")
            await model_service._refresh_cloud_models()
            
            # Count available models
            available_count = sum(1 for m in model_service.models.values() if m.status == "available")
            total_count = len(model_service.models)
            logger.info(f"Cloud models refreshed: {available_count}/{total_count} models available")
            update_phase_status(
                "model_registry",
                "complete",
                f"Model registry ready ({available_count}/{total_count} models available)",
                details={"available_models": available_count, "total_models": total_count},
            )
        except Exception as e:
            logger.warning(f"Could not refresh cloud models on startup: {e}", exc_info=True)
            update_phase_status("model_registry", "error", f"Model refresh failed: {e}")
        
        # Start RAG auto-refresh using new RAGIngester service
        try:
            from backend.services.rag_ingester import RAGIngester
            from backend.utils.tool_detector import get_user_project_directories
            
            rag_ingester = RAGIngester()
            user_project_dirs = get_user_project_directories()
            
            if user_project_dirs:
                logger.info(f"Found {len(user_project_dirs)} user project directories")
                update_phase_status(
                    "rag_indexing",
                    "running",
                    f"Indexing {len(user_project_dirs)} project directories...",
                )
                
                # Initial indexing (run in background to not block startup)
                async def initial_index():
                    try:
                        total_dirs = len(user_project_dirs)
                        for index, directory in enumerate(user_project_dirs, start=1):
                            try:
                                logger.info(f"Initial indexing of {directory}...")
                                stats = await rag_ingester.index_directory(directory)
                                logger.info(f"Initial indexing complete for {directory}: {stats}")
                                update_phase_status(
                                    "rag_indexing",
                                    "running",
                                    f"Indexed {index}/{total_dirs} project directories",
                                    progress=(index / total_dirs) * 40.0,
                                )
                            except Exception as e:
                                logger.error(f"Error during initial indexing of {directory}: {e}", exc_info=True)
                                update_phase_status(
                                    "rag_indexing",
                                    "error",
                                    f"Initial indexing failed for {directory}: {e}",
                                )
                                return
                        
                        update_phase_status("rag_indexing", "complete", "Project directories indexed")
                    
                        # Auto-build Knowledge Graph and Pattern Mining after RAG indexing
                        try:
                            logger.info("🧠 Auto-building Knowledge Graph and Pattern Mining...")
                            
                            # Build Knowledge Graph (COMBINED for all directories)
                            try:
                                update_phase_status("knowledge_graph", "running", "Building knowledge graph...")
                                from backend.services.knowledge_graph import get_builder as get_kg_builder
                                kg_builder = get_kg_builder()
                                
                                # Build combined graph for all user directories
                                import networkx as nx
                                combined_graph = nx.DiGraph()
                                
                                for directory in user_project_dirs:
                                    logger.info(f"Building Knowledge Graph for {directory}...")
                                    # Build graph for this directory
                                    dir_graph = await asyncio.to_thread(kg_builder.build_graph, Path(directory))
                                    # Merge into combined graph
                                    combined_graph = nx.compose(combined_graph, dir_graph)
                                
                                # Set the combined graph as the builder's graph
                                kg_builder.graph = combined_graph
                                
                                # Cache the COMBINED results once
                                await asyncio.to_thread(kg_builder.cache_graph)
                                logger.info(f"✅ Knowledge Graph built successfully: {len(combined_graph.nodes)} nodes, {len(combined_graph.edges)} edges")
                                update_phase_status(
                                    "knowledge_graph",
                                    "complete",
                                    "Knowledge graph ready",
                                    details={"nodes": len(combined_graph.nodes), "edges": len(combined_graph.edges)},
                                )
                            except Exception as e:
                                logger.warning(f"Could not build Knowledge Graph: {e}", exc_info=True)
                                update_phase_status("knowledge_graph", "error", f"Knowledge graph failed: {e}")
                            
                            # Build Pattern Mining (COMBINED for all directories)
                            try:
                                update_phase_status("pattern_mining", "running", "Analyzing design patterns...")
                                from backend.services.pattern_mining import get_miner
                                from backend.services.analysis_service import get_service as get_analysis_service
                                
                                pattern_miner = get_miner()
                                analysis_service = get_analysis_service()
                                
                                # Accumulate results from all directories
                                combined_patterns = []
                                combined_code_smells = []
                                combined_security_issues = []
                                combined_metrics = {}
                                combined_recommendations = []
                                
                                for directory in user_project_dirs:
                                    logger.info(f"Analyzing patterns for {directory}...")
                                    # Use analyze_project method
                                    result = await asyncio.to_thread(
                                        pattern_miner.analyze_project,
                                        Path(directory)
                                    )
                                    
                                    # Accumulate results
                                    if hasattr(result, 'patterns'):
                                        combined_patterns.extend(result.patterns)
                                    if hasattr(result, 'code_smells'):
                                        combined_code_smells.extend(result.code_smells)
                                    if hasattr(result, 'security_issues'):
                                        combined_security_issues.extend(result.security_issues)
                                    if hasattr(result, 'metrics'):
                                        combined_metrics.update(result.metrics)
                                    if hasattr(result, 'recommendations'):
                                        combined_recommendations.extend(result.recommendations)
                                
                                # Store COMBINED results in analysis service
                                analysis_service.last_analysis = {
                                    "patterns": combined_patterns,
                                    "code_smells": combined_code_smells,
                                    "security_issues": combined_security_issues,
                                    "metrics": combined_metrics,
                                    "recommendations": combined_recommendations
                                }
                                
                                # Cache the combined results once
                                await asyncio.to_thread(pattern_miner.cache_results)
                                logger.info(f"✅ Pattern Mining completed successfully: {len(combined_patterns)} patterns found")
                                update_phase_status(
                                    "pattern_mining",
                                    "complete",
                                    "Pattern mining ready",
                                    details={"patterns_found": len(combined_patterns)},
                                )
                            except Exception as e:
                                logger.warning(f"Could not build Pattern Mining: {e}", exc_info=True)
                                update_phase_status("pattern_mining", "error", f"Pattern mining failed: {e}")
                            
                            # 🚀 POWERHOUSE: Build Universal Context (combines everything!)
                            try:
                                update_phase_status("universal_context", "running", "Building universal context...")
                                logger.info("🚀 Building Universal Context - The RAG Powerhouse that knows your entire project by heart!")
                                from backend.services.universal_context import get_universal_context_service
                                
                                universal_service = get_universal_context_service()
                                universal_ctx = await universal_service.build_universal_context()
                                
                                logger.info(f"✅ Universal Context built successfully!")
                                logger.info(f"   📂 Project directories: {len(universal_ctx['project_directories'])}")
                                logger.info(f"   📄 Total files indexed: {universal_ctx['total_files']}")
                                logger.info(f"   🏗️ KG nodes: {universal_ctx['knowledge_graph']['total_nodes']}")
                                logger.info(f"   🔍 Patterns found: {universal_ctx['patterns']['total_patterns']}")
                                logger.info(f"   ⭐ Key entities: {len(universal_ctx['key_entities'])}")
                                logger.info(f"   ⏱️ Build time: {universal_ctx['build_duration_seconds']:.2f}s")
                                logger.info("🎉 RAG POWERHOUSE READY - Your project is now known by heart!")
                                update_phase_status(
                                    "universal_context",
                                    "complete",
                                    "Universal context ready",
                                    details={
                                        "project_directories": len(universal_ctx['project_directories']),
                                        "total_files": universal_ctx['total_files'],
                                        "knowledge_graph_nodes": universal_ctx['knowledge_graph']['total_nodes'],
                                        "patterns_found": universal_ctx['patterns']['total_patterns'],
                                    },
                                )
                                # Mark system as ready after universal context is complete
                                mark_system_ready("Universal context built successfully - system ready!")
                            except Exception as e:
                                logger.warning(f"Could not build Universal Context: {e}", exc_info=True)
                                update_phase_status("universal_context", "error", f"Universal context failed: {e}")
                        
                        except Exception as e:
                            logger.warning(f"Auto-build of KG/PM failed: {e}")
                    except Exception as e:
                        logger.error(f"Error in initial_index: {e}", exc_info=True)
                    finally:
                        _evaluate_overall_status()
                
                # Start initial indexing in background
                asyncio.create_task(initial_index())
                
                # Start watching for changes (synchronous, but fast)
                update_phase_status("watchers", "running", "Starting directory watchers...")
                for directory in user_project_dirs:
                    try:
                        rag_ingester.start_watching(directory)
                        logger.info(f"✅ Started watching {directory} for file changes")
                    except Exception as e:
                        logger.error(f"Error starting watcher for {directory}: {e}", exc_info=True)
                        update_phase_status("watchers", "error", f"Failed to watch {directory}: {e}")
                        break
                else:
                    update_phase_status(
                        "watchers",
                        "complete",
                        f"Watching {len(user_project_dirs)} directories for changes",
                        details={"directories": user_project_dirs},
                    )
                
                # Store reference for shutdown
                app.state.rag_ingester = rag_ingester
                
                # Log index stats
                stats = rag_ingester.get_index_stats()
                logger.info(f"RAG auto-refresh started - monitoring {len(user_project_dirs)} directories")
                logger.info(f"RAG index stats: {stats}")
            else:
                logger.warning("No user project directories found. RAG auto-refresh not started.")
                logger.info("Tip: Make sure you're running from a directory that contains your project")
                update_phase_status("rag_indexing", "skipped", "No user project directories detected")
                update_phase_status("knowledge_graph", "skipped", "No project files to analyze")
                update_phase_status("pattern_mining", "skipped", "No project files to analyze")
                update_phase_status("universal_context", "skipped", "Universal context disabled (no project data)")
                update_phase_status("watchers", "skipped", "No directories to watch")
                mark_system_ready("API running without user project context")
        except ImportError as e:
            logger.warning(f"RAG auto-refresh not available: {e}")
        except Exception as e:
            logger.error(f"Error starting RAG auto-refresh: {e}", exc_info=True)
            
    except ImportError as e:
        logger.warning(f"Database modules not available: {e}. Skipping database initialization.")
        logger.info("Architect.AI API starting (database disabled)...")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    # Stop RAG auto-refresh if running
    if hasattr(app.state, 'rag_ingester'):
        try:
            app.state.rag_ingester.stop_watching()
            logger.info("RAG auto-refresh stopped")
        except Exception as e:
            logger.error(f"Error stopping RAG auto-refresh: {e}")
    
    logger.info("Shutting down application")

# Import routers
from backend.api import websocket as ws_router
from backend.api import auth as auth_router
from backend.api import rag as rag_router
from backend.api import knowledge_graph as kg_router
from backend.api import pattern_mining as pm_router
# ML features router temporarily disabled - missing DTOs
# from backend.api import ml_features as ml_router
from backend.api import context as context_router
from backend.api import analysis as analysis_router
from backend.api import chat as chat_router
from backend.api import code_search as code_search_router
from backend.api import universal_context as universal_context_router

app.include_router(ws_router.router, tags=["websocket"])
app.include_router(auth_router.router)
app.include_router(rag_router.router)
app.include_router(kg_router.router)
app.include_router(pm_router.router)
# app.include_router(ml_router.router)
app.include_router(context_router.router)
app.include_router(analysis_router.router)
app.include_router(universal_context_router.router)  # 🚀 Universal Context - The RAG Powerhouse!
app.include_router(chat_router.router)

# Import additional routers
from backend.api import generation as gen_router
from backend.api import validation as val_router
from backend.api import feedback as feedback_router

app.include_router(gen_router.router)
app.include_router(val_router.router)
app.include_router(feedback_router.router)

# Import model management router
from backend.api import models as models_router
from backend.api import training as training_router
from backend.api import datasets as datasets_router
from backend.api import huggingface as hf_router
from backend.api import finetuning_pool as pool_router
from backend.api import html_diagrams as html_diagrams_router
from backend.api import vram as vram_router
from backend.api import meeting_notes as meeting_notes_router
from backend.api import versions as versions_router
from backend.api import git as git_router
from backend.api import export as export_router
from backend.api import templates as templates_router
from backend.api import validators as validators_router
from backend.api import config as config_router
from backend.api import synthetic_data as synthetic_data_router
from backend.api import ai as ai_router  # AI diagram parsing and improvement
from backend.api import project_target as project_target_router  # Project target management

app.include_router(models_router.router)
app.include_router(training_router.router)
app.include_router(datasets_router.router)
app.include_router(hf_router.router)
app.include_router(pool_router.router)
app.include_router(html_diagrams_router.router)
app.include_router(vram_router.router)
app.include_router(meeting_notes_router.router)
app.include_router(versions_router.router)
app.include_router(git_router.router)
app.include_router(export_router.router)
app.include_router(code_search_router.router)
app.include_router(templates_router.router)
app.include_router(validators_router.router)
app.include_router(config_router.router)
app.include_router(synthetic_data_router.router)
app.include_router(ai_router.router)  # AI diagram parsing and improvement
app.include_router(project_target_router.router)  # Project target management

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

