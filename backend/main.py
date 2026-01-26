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
import sys

# ============================================================================
# LOGGING CONFIGURATION (CRITICAL FOR DEBUGGING)
# ============================================================================
# Force encoding to utf-8 for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # Override any existing config
)
logger = logging.getLogger("backend")
logger.info("✅ Logging configured to stdout")

from datetime import datetime
from typing import Dict, Any, Optional
from backend.core.middleware import (
    RequestIDMiddleware,
    TimingMiddleware,
    StructuredLoggingMiddleware,
    setup_rate_limiting,
    setup_security_middleware,
    get_ip_ban_stats
)
from backend.core.config import settings
from backend.models.errors import ErrorResponse


# =============================================================================
# Custom Log Filter - Exclude noisy endpoints from uvicorn access logs
# =============================================================================
class EndpointFilter(logging.Filter):
    """Filter out noisy endpoints from uvicorn access logs."""
    
    # Endpoints to exclude from access logs (checked with 'in' for flexibility)
    EXCLUDED_PATTERNS = [
        "/health",
        "/api/health", 
        "/metrics",
        "/favicon.ico",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to exclude the log record, True to include it."""
        message = record.getMessage()
        
        # Check if the log message contains any excluded endpoint pattern
        for pattern in self.EXCLUDED_PATTERNS:
            if pattern in message:
                return False
        
        return True


# Configure structured logging with colorized output for Windows CMD visibility
class ColoredFormatter(logging.Formatter):
    """Colorized log formatter for Windows CMD visibility."""
    
    # ANSI colors that work in Windows 10+ CMD
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.compact_time = self.formatTime(record, '%H:%M:%S')
        name = record.name
        if len(name) > 25:
            parts = name.split('.')
            if len(parts) > 2:
                name = f"{parts[0]}...{parts[-1]}"
            else:
                name = name[:25]
        return f"{record.compact_time} {color}{record.levelname:7}{reset} [{name:25}] {record.getMessage()}"


# Enable ANSI colors in Windows CMD
if sys.platform == 'win32':
    import ctypes
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Set up colorized logging
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(ColoredFormatter())
_console_handler.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO, handlers=[_console_handler])

# Ensure key loggers are not silenced
for _logger_name in ['backend.services', 'backend.api', 'ai', 'agents']:
    logging.getLogger(_logger_name).setLevel(logging.INFO)


# Apply filter to uvicorn loggers to reduce noise from health checks
_endpoint_filter = EndpointFilter()
logging.getLogger("uvicorn.access").addFilter(_endpoint_filter)
logging.getLogger("uvicorn").addFilter(_endpoint_filter)

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


# =============================================================================
# Lifespan Context Manager - Startup/Shutdown Events
# =============================================================================
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for the FastAPI application."""
    # ==========================================================================
    # STARTUP - Print banner and initialize services
    # ==========================================================================
    print("\n" + "=" * 70)
    print("   🏗️  ARCHITECT.AI BACKEND STARTING")
    print("=" * 70)
    print(f"   Version: {settings.app_version}")
    print(f"   Host: 0.0.0.0:8000")
    print(f"   Docs: http://localhost:8000/api/docs")
    print("=" * 70)

    # Initialize services (replacing @app.on_event("startup"))
    try:
        from backend.core.database import init_db
        
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        set_overall_status("initializing", "Bootstrapping backend services")
        
        # 1. Database
        update_phase_status("database", "running", "Initializing database...")
        init_db()
        update_phase_status("database", "complete", "Database initialized")
        logger.info("Database initialized")
        
        # 2. Model Registry
        try:
            from backend.services.model_service import get_service as get_model_service
            model_service = get_model_service()
            
            update_phase_status("model_registry", "running", "Refreshing cloud model registry...")
            await model_service._refresh_cloud_models()
            
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
            logger.warning(f"Could not refresh cloud models on startup: {e}")
            update_phase_status("model_registry", "error", f"Model refresh failed: {e}")

        # 3. Ollama (local models)
        print("\n🔍 Checking Ollama availability...")
        try:
            from ai.ollama_client import OllamaClient
            update_phase_status("ollama", "running", "Connecting to Ollama...")
            ollama_client = OllamaClient()
            available_models = await ollama_client.list_models()
            
            if available_models:
                model_names = []
                for model in available_models:
                    name = model.get("name", model.get("model", "unknown")) if isinstance(model, dict) else str(model)
                    model_names.append(name)
                
                print(f"   ✅ Ollama is running with {len(model_names)} models")
                if model_names:
                    print(f"   📦 Available: {', '.join(model_names[:5])}")
                logger.info(f"✅ Ollama connected: {len(model_names)} models available")
                update_phase_status("ollama", "complete", f"Ollama ready ({len(model_names)} local models)")
            else:
                print("   ⚠️ Ollama is running but no models are installed")
                update_phase_status("ollama", "complete", "Ollama connected (no models installed)")
        except Exception as e:
            print(f"   ❌ Ollama not available: {e}")
            logger.warning(f"Ollama not available: {e}")
            update_phase_status("ollama", "skipped", f"Ollama not available: {e}")

        # 4. RAG and Analysis
        try:
            from backend.services.rag_ingester import RAGIngester
            from backend.utils.tool_detector import get_user_project_directories
            
            rag_ingester = RAGIngester()
            user_project_dirs = get_user_project_directories()
            
            if user_project_dirs:
                update_phase_status("rag_indexing", "running", f"Indexing {len(user_project_dirs)} projects...")
                
                # Initial indexing and following automated tasks in background
                async def init_rag_system():
                    try:
                        for idx, directory in enumerate(user_project_dirs, 1):
                            await rag_ingester.index_directory(directory)
                            update_phase_status("rag_indexing", "running", f"Indexed {idx}/{len(user_project_dirs)} projects", progress=(idx/len(user_project_dirs))*50)
                        
                        update_phase_status("rag_indexing", "complete", "Projects indexed")
                        
                        # Trigger KG and Patterns
                        await run_background_analysis(user_project_dirs)
                        
                    except Exception as e:
                        logger.error(f"RAG init error: {e}", exc_info=True)
                
                asyncio.create_task(init_rag_system())
                
                # Start watchers
                update_phase_status("watchers", "running", "Starting watchers...")
                for d in user_project_dirs:
                    rag_ingester.start_watching(d)
                update_phase_status("watchers", "complete", "Watchers active")
                app.state.rag_ingester = rag_ingester
            else:
                update_phase_status("rag_indexing", "skipped", "No projects found")
                mark_system_ready("API running without user project context")
        except Exception as e:
            logger.error(f"RAG setup error: {e}")

    except Exception as e:
        logger.error(f"CRITICAL startup failure: {e}", exc_info=True)
    
    # Check API keys for banner
    print("\n🔑 Checking API keys...")
    api_keys = {
        "Groq": bool(settings.groq_api_key),
        "OpenAI": bool(settings.openai_api_key),
        "Google": bool(getattr(settings, 'google_api_key', None)),
    }
    for name, configured in api_keys.items():
        status = "✅" if configured else "❌"
        print(f"   {status} {name}: {'configured' if configured else 'not set'}")
    
    print("\n" + "=" * 70)
    print("   ✅ STARTUP SEQUENCE INITIALIZED")
    print("=" * 70 + "\n")
    logger.info("🚀 Architect.AI initialization triggered")
    
    yield  # Application runs here
    
    # ==========================================================================
    # SHUTDOWN - Replacing @app.on_event("shutdown")
    # ==========================================================================
    print("\n👋 Architect.AI backend shutting down...")
    if hasattr(app.state, 'rag_ingester'):
        try:
            app.state.rag_ingester.stop_watching()
            logger.info("RAG auto-refresh stopped")
        except Exception as e:
            logger.error(f"Error stopping RAG: {e}")
    logger.info("Backend shutdown complete")

async def run_background_analysis(user_project_dirs):
    """Background task to build KG and run Pattern Mining."""
    try:
        update_phase_status("knowledge_graph", "running", "Building knowledge graph...")
        from backend.services.knowledge_graph import get_builder as get_kg_builder
        kg_builder = get_kg_builder()
        # simplified build for all
        for d in user_project_dirs:
            await asyncio.to_thread(kg_builder.build_graph, Path(d))
        update_phase_status("knowledge_graph", "complete", "Knowledge graph ready")
        
        update_phase_status("pattern_mining", "running", "Analyzing patterns...")
        from backend.services.pattern_mining import get_miner
        pattern_miner = get_miner()
        for d in user_project_dirs:
            await asyncio.to_thread(pattern_miner.analyze_project, Path(d))
        update_phase_status("pattern_mining", "complete", "Pattern mining ready")
        
        # Finally Universal Context
        update_phase_status("universal_context", "running", "Building powerhouse context...")
        from backend.services.universal_context import get_universal_context_service
        universal_service = get_universal_context_service()
        await universal_service.build_universal_context()
        update_phase_status("universal_context", "complete", "Universal powerhouse ready")
        
        mark_system_ready("System fully initialized and analyzed")
    except Exception as e:
        logger.error(f"Background analysis failed: {e}", exc_info=True)


# Create FastAPI app with lifespan handler
app = FastAPI(
    title="Architect.AI API",
    description="FastAPI backend for interactive architecture visualization and artifact generation",
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan  # Use lifespan for startup/shutdown
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
    "ollama": {"title": "Ollama", "description": "Connecting to local AI models"},
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


# Custom middleware (order matters - last added is first executed)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

# Setup rate limiting
limiter = setup_rate_limiting(app)

# Setup security middleware (IP banning, trusted hosts)
# This adds protection against vulnerability scanners and ensures
# requests only come from trusted hosts (localhost, frontend, ngrok)
ip_ban_manager = setup_security_middleware(app)

# CORS middleware (OUTERMOST - must be added last in FastAPI/Starlette)
# Supporting local development, Vercel, and dynamic ngrok tunnels
# Improved regex to support .app, .io, and .dev ngrok suffixes
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.ngrok(-free)?\.(app|io|dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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




# Import routers
from backend.api import websocket as ws_router

from backend.api import rag as rag_router
from backend.api import knowledge_graph as kg_router
from backend.api import pattern_mining as pm_router
from backend.api import context as context_router
from backend.api import analysis as analysis_router
from backend.api import chat as chat_router
from backend.api import code_search as code_search_router
from backend.api import universal_context as universal_context_router
from backend.api import ml_features as ml_router  # ML Feature Engineering endpoints

app.include_router(ws_router.router, tags=["websocket"])

app.include_router(rag_router.router)
app.include_router(kg_router.router)
app.include_router(pm_router.router)
app.include_router(ml_router.router)  # ML Feature Engineering (re-enabled)
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
from backend.api import assistant as assistant_router  # Intelligent Assistant - suggestions, linking, review, etc.
from backend.api import multi_repo as multi_repo_router  # Multi-repository analysis

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
app.include_router(assistant_router.router)  # Intelligent Assistant - suggestions, artifact linking, sprint packages, etc.
app.include_router(multi_repo_router.router)  # Multi-repository analysis

if __name__ == "__main__":
    import uvicorn
    
    # Custom uvicorn log config to apply endpoint filter
    log_config = uvicorn.config.LOGGING_CONFIG
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        log_config=log_config
    )

