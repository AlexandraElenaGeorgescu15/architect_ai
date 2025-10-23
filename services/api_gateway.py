"""
API Gateway - FastAPI-based REST API
Central entry point for all microservices
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from monitoring import get_metrics, counter, histogram, timer
from ai.model_router import get_router

# Create FastAPI app
app = FastAPI(
    title="Architect.AI API",
    description="Microservices API for AI-powered software architecture generation",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class WorkflowRequest(BaseModel):
    meeting_notes_path: str
    feature_name: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    async_mode: bool = False

class WorkflowResponse(BaseModel):
    success: bool
    job_id: Optional[str] = None
    message: str
    result: Optional[Dict[str, Any]] = None

class RAGSearchRequest(BaseModel):
    query: str
    k: int = 18
    force_refresh: bool = False

class RAGSearchResponse(BaseModel):
    success: bool
    context: str
    num_results: int

class DiagramRequest(BaseModel):
    feature_requirements: Dict[str, Any]
    diagram_types: List[str] = ["overview", "dataflow", "userflow", "components", "api"]

class DiagramResponse(BaseModel):
    success: bool
    diagrams: Dict[str, str]

class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    counter('api_health_check_total')
    
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        services={
            "api_gateway": "running",
            "rag_service": "running",
            "llm_service": "running",
            "worker_service": "running"
        }
    )

# Metrics endpoint
@app.get("/metrics")
async def get_system_metrics():
    """Get system metrics"""
    metrics = get_metrics()
    router = get_router()
    
    return {
        "metrics": metrics.get_stats(),
        "model_router": router.get_stats()
    }

# RAG Search endpoint
@app.post("/api/rag/search", response_model=RAGSearchResponse)
async def search_rag_context(request: RAGSearchRequest):
    """Search RAG context"""
    with timer('rag_search_duration_seconds'):
        try:
            from agents.universal_agent import UniversalArchitectAgent
            
            agent = UniversalArchitectAgent()
            context = await agent.retrieve_rag_context(request.query, request.force_refresh)
            
            counter('rag_search_total', status='success')
            
            return RAGSearchResponse(
                success=True,
                context=context,
                num_results=len(context.split('---'))
            )
            
        except Exception as e:
            counter('rag_search_total', status='error')
            raise HTTPException(status_code=500, detail=str(e))

# Workflow generation endpoint
@app.post("/api/workflow/generate", response_model=WorkflowResponse)
async def generate_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """Generate complete workflow"""
    with timer('workflow_api_duration_seconds'):
        try:
            if request.async_mode:
                # Use Celery for async processing
                try:
                    from workers.celery_app import generate_workflow_async
                    
                    task = generate_workflow_async.delay(
                        request.meeting_notes_path,
                        request.feature_name,
                        {
                            'openai_api_key': request.openai_api_key,
                            'gemini_api_key': request.gemini_api_key
                        }
                    )
                    
                    counter('workflow_generation_total', mode='async', status='queued')
                    
                    return WorkflowResponse(
                        success=True,
                        job_id=task.id,
                        message=f"Workflow generation queued. Job ID: {task.id}"
                    )
                    
                except ImportError:
                    raise HTTPException(status_code=503, detail="Async mode not available. Celery not configured.")
            
            else:
                # Synchronous processing
                from agents.universal_agent import run_universal_workflow
                import asyncio
                
                result = await run_universal_workflow(
                    request.meeting_notes_path,
                    request.feature_name,
                    request.openai_api_key,
                    request.gemini_api_key
                )
                
                counter('workflow_generation_total', mode='sync', status='success' if result.success else 'error')
                
                return WorkflowResponse(
                    success=result.success,
                    message="Workflow generated successfully" if result.success else "Workflow generation failed",
                    result={
                        'tech_stacks': result.repository_analysis.tech_stacks if result.repository_analysis else [],
                        'metadata': result.metadata,
                        'errors': result.errors
                    }
                )
                
        except Exception as e:
            counter('workflow_generation_total', status='error')
            raise HTTPException(status_code=500, detail=str(e))

# Job status endpoint
@app.get("/api/workflow/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        from workers.celery_app import app as celery_app
        
        task = celery_app.AsyncResult(job_id)
        
        return {
            'job_id': job_id,
            'status': task.state,
            'result': task.result if task.ready() else None,
            'info': task.info
        }
        
    except ImportError:
        raise HTTPException(status_code=503, detail="Job queue not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Diagram generation endpoint
@app.post("/api/diagrams/generate", response_model=DiagramResponse)
async def generate_diagrams(request: DiagramRequest):
    """Generate diagrams"""
    with timer('diagram_generation_duration_seconds'):
        try:
            from agents.universal_agent import UniversalArchitectAgent
            
            agent = UniversalArchitectAgent()
            agent.feature_requirements = request.feature_requirements
            
            diagrams = await agent.generate_specific_diagrams()
            
            counter('diagram_generation_total', status='success')
            
            return DiagramResponse(
                success=True,
                diagrams=diagrams
            )
            
        except Exception as e:
            counter('diagram_generation_total', status='error')
            raise HTTPException(status_code=500, detail=str(e))

# Model recommendation endpoint
@app.post("/api/ai/recommend-model")
async def recommend_model(task_type: str, budget_limit: Optional[float] = None):
    """Get model recommendation for task"""
    router = get_router()
    recommendation = router.recommend_model(task_type, budget_limit)
    
    return recommendation

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

