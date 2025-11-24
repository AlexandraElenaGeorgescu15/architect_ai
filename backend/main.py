"""
FastAPI application entry point for Architect.AI backend services.
"""

import sys
from pathlib import Path
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import logging
from datetime import datetime
from typing import Dict, Any
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
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    from backend.core.cache import get_cache_manager
    from backend.core.metrics import get_metrics_collector
    
    cache_stats = get_cache_manager().get_stats()
    metrics_stats = get_metrics_collector().get_stats()
    
    return {
        "status": "healthy",
        "service": "architect-ai-backend",
        "version": settings.app_version,
        "cache": cache_stats,
        "metrics": {
            "counters": len(metrics_stats.get("counters", {})),
            "gauges": len(metrics_stats.get("gauges", {})),
            "timers": len(metrics_stats.get("timers", {}))
        }
    }

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
        init_db()
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
            
            await model_service._refresh_cloud_models()
            
            # Count available models
            available_count = sum(1 for m in model_service.models.values() if m.status == "available")
            total_count = len(model_service.models)
            logger.info(f"Cloud models refreshed: {available_count}/{total_count} models available")
        except Exception as e:
            logger.warning(f"Could not refresh cloud models on startup: {e}", exc_info=True)
        
        # Start RAG auto-refresh using new RAGIngester service
        try:
            from backend.services.rag_ingester import RAGIngester
            from backend.utils.tool_detector import get_user_project_directories
            
            rag_ingester = RAGIngester()
            user_project_dirs = get_user_project_directories()
            
            if user_project_dirs:
                logger.info(f"Found {len(user_project_dirs)} user project directories")
                
                # Initial indexing (run in background to not block startup)
                async def initial_index():
                    for directory in user_project_dirs:
                        try:
                            logger.info(f"Initial indexing of {directory}...")
                            stats = await rag_ingester.index_directory(directory)
                            logger.info(f"Initial indexing complete for {directory}: {stats}")
                        except Exception as e:
                            logger.error(f"Error during initial indexing of {directory}: {e}", exc_info=True)
                    
                    # Auto-build Knowledge Graph and Pattern Mining after RAG indexing
                    try:
                        logger.info("🧠 Auto-building Knowledge Graph and Pattern Mining...")
                        
                        # Build Knowledge Graph (COMBINED for all directories)
                        try:
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
                        except Exception as e:
                            logger.warning(f"Could not build Knowledge Graph: {e}", exc_info=True)
                        
                        # Build Pattern Mining (COMBINED for all directories)
                        try:
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
                        except Exception as e:
                            logger.warning(f"Could not build Pattern Mining: {e}", exc_info=True)
                        
                        # 🚀 POWERHOUSE: Build Universal Context (combines everything!)
                        try:
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
                        except Exception as e:
                            logger.warning(f"Could not build Universal Context: {e}", exc_info=True)
                        
                    except Exception as e:
                        logger.warning(f"Auto-build of KG/PM failed: {e}")
                
                # Start initial indexing in background
                asyncio.create_task(initial_index())
                
                # Start watching for changes (synchronous, but fast)
                for directory in user_project_dirs:
                    try:
                        rag_ingester.start_watching(directory)
                        logger.info(f"✅ Started watching {directory} for file changes")
                    except Exception as e:
                        logger.error(f"Error starting watcher for {directory}: {e}", exc_info=True)
                
                # Store reference for shutdown
                app.state.rag_ingester = rag_ingester
                
                # Log index stats
                stats = rag_ingester.get_index_stats()
                logger.info(f"RAG auto-refresh started - monitoring {len(user_project_dirs)} directories")
                logger.info(f"RAG index stats: {stats}")
            else:
                logger.warning("No user project directories found. RAG auto-refresh not started.")
                logger.info("Tip: Make sure you're running from a directory that contains your project")
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
from backend.api import export as export_router
from backend.api import templates as templates_router
from backend.api import validators as validators_router
from backend.api import config as config_router
from backend.api import synthetic_data as synthetic_data_router
from backend.api import ai as ai_router  # AI diagram parsing and improvement

app.include_router(models_router.router)
app.include_router(training_router.router)
app.include_router(datasets_router.router)
app.include_router(hf_router.router)
app.include_router(pool_router.router)
app.include_router(html_diagrams_router.router)
app.include_router(vram_router.router)
app.include_router(meeting_notes_router.router)
app.include_router(versions_router.router)
app.include_router(export_router.router)
app.include_router(code_search_router.router)
app.include_router(templates_router.router)
app.include_router(validators_router.router)
app.include_router(config_router.router)
app.include_router(synthetic_data_router.router)
app.include_router(ai_router.router)  # AI diagram parsing and improvement

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

