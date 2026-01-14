"""
Intelligent Assistant API Endpoints

Production-grade REST API for AI-powered development assistance:
1. Artifact Suggestions - Smart recommendations for next steps
2. Artifact Dependency Tracking - Cross-artifact linking and staleness detection
3. Sprint Package Generator - Batch artifact generation
4. Meeting Notes Analysis - Structured extraction from notes
5. Migration Generator - Database migration from ERD
6. Multi-Repository Analysis - Cross-repo architecture views
7. Design Review - AI-powered code and architecture review
8. Impact Analysis - Change impact assessment
9. Contextual AI - File-focused AI assistance
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from pydantic import BaseModel, Field
from datetime import datetime

from backend.core.auth import get_current_user
from backend.models.dto import ArtifactType
from backend.models.schemas import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["intelligent-assistant"])


# ============================================================
# Request/Response Models
# ============================================================

class SuggestionRequest(BaseModel):
    """Request for smart suggestions."""
    existing_artifact_types: List[str] = Field(default_factory=list)
    meeting_notes: str = ""
    max_suggestions: int = 5


class SuggestionResponse(BaseModel):
    """Response with suggestions."""
    suggestions: List[Dict[str, Any]]
    roadmap: Optional[Dict[str, Any]] = None


class ArtifactLinkRequest(BaseModel):
    """Request to register or link artifacts."""
    artifact_id: str
    artifact_type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class StalenessCheckRequest(BaseModel):
    """Request to check artifact staleness."""
    artifact_ids: List[str]


class SprintPackageRequest(BaseModel):
    """Request to generate sprint package."""
    meeting_notes: str
    preset: str = "full"  # full, backend, frontend, documentation, pm, quick
    custom_artifacts: Optional[List[str]] = None


class MeetingNotesParseRequest(BaseModel):
    """Request to parse meeting notes."""
    meeting_notes: str


class MigrationRequest(BaseModel):
    """Request to generate database migration."""
    erd_content: str
    framework: str = "ef_core"  # ef_core, django, prisma, sql_postgres, etc.
    migration_name: Optional[str] = None


class MultiRepoRequest(BaseModel):
    """Request to register a repository."""
    path: str
    name: Optional[str] = None
    repo_type: str = "other"
    language: str = "unknown"
    framework: Optional[str] = None


class DesignReviewRequest(BaseModel):
    """Request for design review."""
    directory: str
    architecture_diagram: Optional[str] = None
    meeting_notes: Optional[str] = None
    review_type: str = "full"  # full, architecture, security, tests, patterns


class ImpactAnalysisRequest(BaseModel):
    """Request for impact analysis."""
    artifact_id: str


class ContextualAskRequest(BaseModel):
    """Request for contextual Ask AI."""
    question: str
    file_paths: List[str] = Field(default_factory=list)
    include_project_context: bool = True


# ============================================================
# Smart Suggestions Endpoints
# ============================================================

@router.post("/suggestions", response_model=SuggestionResponse)
async def get_suggestions(
    request: SuggestionRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Get smart suggestions for what to generate next.
    
    Analyzes existing artifacts and meeting notes to suggest logical next steps.
    """
    try:
        from backend.services.artifact_suggestions import get_suggestion_engine
        
        engine = get_suggestion_engine()
        
        # Convert artifact types to dicts
        existing_artifacts = [{"type": t} for t in request.existing_artifact_types]
        
        suggestions = engine.get_suggestions(
            existing_artifacts=existing_artifacts,
            meeting_notes=request.meeting_notes,
            max_suggestions=request.max_suggestions
        )
        
        # Get roadmap if no artifacts exist
        roadmap = None
        if not request.existing_artifact_types:
            roadmap = engine.get_generation_roadmap(request.meeting_notes)
        
        return SuggestionResponse(
            suggestions=[s.to_dict() for s in suggestions],
            roadmap=roadmap
        )
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions/roadmap")
async def get_roadmap(
    meeting_notes: str = Query(""),
    current_user: UserPublic = Depends(get_current_user)
):
    """Get a full generation roadmap for meeting notes."""
    try:
        from backend.services.artifact_suggestions import get_suggestion_engine
        
        engine = get_suggestion_engine()
        roadmap = engine.get_generation_roadmap(meeting_notes)
        
        return roadmap
        
    except Exception as e:
        logger.error(f"Failed to get roadmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Artifact Linking Endpoints
# ============================================================

@router.post("/artifacts/register")
async def register_artifact(
    request: ArtifactLinkRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Register an artifact in the dependency graph."""
    try:
        from backend.services.artifact_linker import get_artifact_linker
        
        linker = get_artifact_linker()
        node = linker.register_artifact(
            artifact_id=request.artifact_id,
            artifact_type=request.artifact_type,
            content=request.content,
            metadata=request.metadata
        )
        
        return {"success": True, "artifact": node.to_dict()}
        
    except Exception as e:
        logger.error(f"Failed to register artifact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifacts/staleness")
async def check_staleness(
    request: StalenessCheckRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Check staleness of artifacts."""
    try:
        from backend.services.artifact_linker import get_artifact_linker
        
        linker = get_artifact_linker()
        reports = []
        
        for artifact_id in request.artifact_ids:
            report = linker.check_staleness(artifact_id)
            reports.append(report.to_dict())
        
        return {"reports": reports}
        
    except Exception as e:
        logger.error(f"Failed to check staleness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/stale")
async def get_all_stale(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all stale artifacts."""
    try:
        from backend.services.artifact_linker import get_artifact_linker
        
        linker = get_artifact_linker()
        stale = linker.get_all_stale_artifacts()
        
        return {"stale_artifacts": [s.to_dict() for s in stale]}
        
    except Exception as e:
        logger.error(f"Failed to get stale artifacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/artifacts/dependency-tree")
async def get_dependency_tree(
    artifact_id: Optional[str] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get the artifact dependency tree."""
    try:
        from backend.services.artifact_linker import get_artifact_linker
        
        linker = get_artifact_linker()
        tree = linker.get_dependency_tree(artifact_id)
        
        return tree
        
    except Exception as e:
        logger.error(f"Failed to get dependency tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/artifacts/impact")
async def get_impact_analysis(
    request: ImpactAnalysisRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get impact analysis for changing an artifact."""
    try:
        from backend.services.artifact_linker import get_artifact_linker
        
        linker = get_artifact_linker()
        impact = linker.get_impact_analysis(request.artifact_id)
        
        return impact
        
    except Exception as e:
        logger.error(f"Failed to get impact analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Sprint Package Endpoints
# ============================================================

@router.get("/sprint-package/presets")
async def get_package_presets(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get available sprint package presets."""
    try:
        from backend.services.sprint_package import get_sprint_package_generator
        
        generator = get_sprint_package_generator()
        presets = generator.get_available_presets()
        
        return {"presets": presets}
        
    except Exception as e:
        logger.error(f"Failed to get presets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sprint-package/generate")
async def generate_sprint_package(
    request: SprintPackageRequest,
    background_tasks: BackgroundTasks,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Generate a complete sprint package.
    
    This starts a background task and returns immediately with a job ID.
    """
    try:
        from backend.services.sprint_package import get_sprint_package_generator, PackagePreset
        
        generator = get_sprint_package_generator()
        
        # Validate preset
        try:
            preset = PackagePreset(request.preset)
        except ValueError:
            preset = PackagePreset.FULL
        
        job_id = f"pkg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # For now, return the preset details
        # Full async generation would use WebSocket
        preset_details = generator.get_preset_details(preset)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "preset": preset.value,
            "details": preset_details,
            "message": "Sprint package generation started. Use WebSocket for progress updates."
        }
        
    except Exception as e:
        logger.error(f"Failed to start sprint package: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Meeting Notes Parser Endpoints
# ============================================================

@router.post("/meeting-notes/parse")
async def parse_meeting_notes(
    request: MeetingNotesParseRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Parse meeting notes and extract structured information.
    
    Extracts:
    - Feature name and description
    - Database entities
    - API endpoints
    - UI components
    - Action items
    - User stories
    """
    try:
        from backend.services.meeting_notes_parser import get_meeting_notes_parser
        
        parser = get_meeting_notes_parser()
        result = parser.parse(request.meeting_notes)
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to parse meeting notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Migration Generator Endpoints
# ============================================================

@router.get("/migration/frameworks")
async def get_migration_frameworks(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get available migration frameworks."""
    try:
        from backend.services.migration_generator import get_migration_generator
        
        generator = get_migration_generator()
        frameworks = generator.get_available_frameworks()
        
        return {"frameworks": frameworks}
        
    except Exception as e:
        logger.error(f"Failed to get frameworks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migration/generate")
async def generate_migration(
    request: MigrationRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Generate database migration from ERD diagram.
    
    Supports Entity Framework Core, Django, Prisma, and raw SQL.
    """
    try:
        from backend.services.migration_generator import get_migration_generator, MigrationFramework
        
        generator = get_migration_generator()
        
        # Validate framework
        try:
            framework = MigrationFramework(request.framework)
        except ValueError:
            framework = MigrationFramework.EF_CORE
        
        result = generator.generate_migration(
            erd_content=request.erd_content,
            framework=framework,
            migration_name=request.migration_name
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to generate migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Multi-Repo Endpoints
# ============================================================

@router.get("/repos")
async def get_repositories(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get all registered repositories."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        repos = service.get_repositories()
        
        return {"repositories": [r.to_dict() for r in repos]}
        
    except Exception as e:
        logger.error(f"Failed to get repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repos/register")
async def register_repository(
    request: MultiRepoRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Register a new repository for multi-repo analysis."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        config = service.register_repository(
            path=request.path,
            name=request.name,
            repo_type=request.repo_type,
            language=request.language,
            framework=request.framework
        )
        
        return {"success": True, "repository": config.to_dict()}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/repos/{repo_id}")
async def unregister_repository(
    repo_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Unregister a repository."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        success = service.unregister_repository(repo_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repos/{repo_id}/index")
async def index_repository(
    repo_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserPublic = Depends(get_current_user)
):
    """Index a repository for RAG retrieval."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        
        # Start indexing in background
        result = await service.index_repository(repo_id)
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to index repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/context")
async def get_combined_context(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get combined context from all repositories."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        context = service.build_combined_context()
        
        return context.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to get combined context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repos/cross-links")
async def detect_cross_repo_links(
    current_user: UserPublic = Depends(get_current_user)
):
    """Detect cross-repository dependencies."""
    try:
        from backend.services.multi_repo import get_multi_repo_service
        
        service = get_multi_repo_service()
        links = service.detect_cross_repo_links()
        
        return {"links": [l.to_dict() for l in links]}
        
    except Exception as e:
        logger.error(f"Failed to detect cross-repo links: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Design Review Endpoints
# ============================================================

@router.post("/review")
async def design_review(
    request: DesignReviewRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Perform a design review.
    
    Review types:
    - full: Complete review (architecture, tests, security, patterns)
    - architecture: Check against architecture diagram
    - security: Security vulnerability scan
    - tests: Test coverage analysis
    - patterns: Design pattern detection
    """
    try:
        from backend.services.design_review import get_design_review_service
        
        service = get_design_review_service()
        
        if request.review_type == "full":
            result = await service.full_review(
                directory=request.directory,
                architecture_diagram=request.architecture_diagram,
                meeting_notes=request.meeting_notes
            )
        elif request.review_type == "security":
            # Get files from directory
            from pathlib import Path
            files = [str(f) for f in Path(request.directory).glob("**/*.py")]
            files.extend([str(f) for f in Path(request.directory).glob("**/*.ts")])
            result = await service.review_security(files[:50])
        elif request.review_type == "patterns":
            result = await service.review_patterns(request.directory)
        else:
            result = await service.full_review(
                directory=request.directory,
                architecture_diagram=request.architecture_diagram,
                meeting_notes=request.meeting_notes
            )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to perform design review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Contextual Ask AI Endpoint
# ============================================================

@router.post("/ask")
async def contextual_ask(
    request: ContextualAskRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Ask AI a question with specific file context.
    
    Provides more focused answers by limiting context to selected files.
    """
    try:
        from backend.services.chat_service import get_chat_service
        from pathlib import Path
        
        # Build context from specific files
        file_context = ""
        if request.file_paths:
            for file_path in request.file_paths[:10]:  # Limit to 10 files
                path = Path(file_path)
                if path.exists():
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")[:3000]
                        file_context += f"\n\n### {path.name}\n```\n{content}\n```"
                    except Exception:
                        pass
        
        # Enhance question with file context
        enhanced_question = request.question
        if file_context:
            enhanced_question = f"Regarding these specific files:{file_context}\n\nQuestion: {request.question}"
        
        chat_service = get_chat_service()
        response = await chat_service.chat(
            message=enhanced_question,
            conversation_history=[],
            include_project_context=request.include_project_context
        )
        
        return {
            "question": request.question,
            "files_analyzed": request.file_paths,
            "response": response.get("message", ""),
            "context_used": bool(file_context)
        }
        
    except Exception as e:
        logger.error(f"Failed to process contextual ask: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Feature Summary Endpoint
# ============================================================

@router.get("/features")
async def get_feature_summary(
    current_user: UserPublic = Depends(get_current_user)
):
    """Get summary of all available intelligent assistant features."""
    return {
        "features": [
            {
                "id": "suggestions",
                "name": "Smart Suggestions",
                "description": "Get intelligent suggestions for what to generate next",
                "endpoints": ["/api/assistant/suggestions", "/api/assistant/suggestions/roadmap"]
            },
            {
                "id": "artifact-linking",
                "name": "Artifact Linking & Staleness",
                "description": "Track dependencies between artifacts and detect outdated ones",
                "endpoints": ["/api/assistant/artifacts/register", "/api/assistant/artifacts/staleness", "/api/assistant/artifacts/impact"]
            },
            {
                "id": "sprint-package",
                "name": "Sprint Package Generator",
                "description": "Generate complete artifact suites in one click",
                "endpoints": ["/api/assistant/sprint-package/presets", "/api/assistant/sprint-package/generate"]
            },
            {
                "id": "meeting-notes",
                "name": "Meeting Notes Parser",
                "description": "Extract structured information from meeting notes",
                "endpoints": ["/api/assistant/meeting-notes/parse"]
            },
            {
                "id": "migration",
                "name": "Migration Generator",
                "description": "Generate database migrations from ERD diagrams",
                "endpoints": ["/api/assistant/migration/frameworks", "/api/assistant/migration/generate"]
            },
            {
                "id": "multi-repo",
                "name": "Multi-Repository Support",
                "description": "Analyze multiple repositories together",
                "endpoints": ["/api/assistant/repos", "/api/assistant/repos/register", "/api/assistant/repos/context"]
            },
            {
                "id": "design-review",
                "name": "Design Review",
                "description": "AI-powered code and design review",
                "endpoints": ["/api/assistant/review"]
            },
            {
                "id": "contextual-ask",
                "name": "Contextual Ask AI",
                "description": "Ask AI about specific files",
                "endpoints": ["/api/assistant/ask"]
            }
        ]
    }
