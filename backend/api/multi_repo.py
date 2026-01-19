"""
Multi-Repository API endpoints.
Enables configuration and analysis of multiple repositories.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from backend.core.auth import get_current_user
from backend.models.dto import UserPublic
from backend.core.middleware import limiter
from backend.services.multi_repo import MultiRepoService, RepositoryConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/multi-repo", tags=["multi-repo"])

# Global service instance
_multi_repo_service: Optional[MultiRepoService] = None

def get_multi_repo_service() -> MultiRepoService:
    global _multi_repo_service
    if _multi_repo_service is None:
        _multi_repo_service = MultiRepoService()
    return _multi_repo_service


class RepositoryCreateRequest(BaseModel):
    """Request to create/register a new repository."""
    repo_id: str
    name: str
    path: str
    repo_type: str  # "frontend", "backend", "fullstack", "library", "other"
    language: str
    framework: Optional[str] = None


class RepositoryResponse(BaseModel):
    """Response containing repository info."""
    repo_id: str
    name: str
    path: str
    repo_type: str
    language: str
    framework: Optional[str]
    indexed: bool
    last_indexed: Optional[str]
    file_count: int


@router.get("/repositories", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def list_repositories(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """List all configured repositories."""
    service = get_multi_repo_service()
    
    repos = []
    for repo_id, repo in service.repositories.items():
        repos.append({
            "repo_id": repo.repo_id,
            "name": repo.name,
            "path": repo.path,
            "repo_type": repo.repo_type,
            "language": repo.language,
            "framework": repo.framework,
            "indexed": repo.indexed,
            "last_indexed": repo.last_indexed,
            "file_count": repo.file_count
        })
    
    return {
        "repositories": repos,
        "total": len(repos)
    }


@router.post("/repositories", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def add_repository(
    request: Request,
    body: RepositoryCreateRequest,
    current_user: UserPublic = Depends(get_current_user)
):
    """Add a new repository to the multi-repo configuration."""
    service = get_multi_repo_service()
    
    # Check if repo already exists
    if body.repo_id in service.repositories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository with ID '{body.repo_id}' already exists"
        )
    
    # Create repository config
    repo_config = RepositoryConfig(
        repo_id=body.repo_id,
        name=body.name,
        path=body.path,
        repo_type=body.repo_type,
        language=body.language,
        framework=body.framework
    )
    
    # Register the repository
    success = service.register_repository(repo_config)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to register repository"
        )
    
    logger.info(f"Repository registered: {body.repo_id} ({body.name})")
    
    return {
        "message": f"Repository '{body.name}' registered successfully",
        "repo_id": body.repo_id,
        "indexed": False
    }


@router.delete("/repositories/{repo_id}", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def remove_repository(
    request: Request,
    repo_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Remove a repository from the multi-repo configuration."""
    service = get_multi_repo_service()
    
    if repo_id not in service.repositories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_id}' not found"
        )
    
    success = service.unregister_repository(repo_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove repository"
        )
    
    logger.info(f"Repository removed: {repo_id}")
    
    return {
        "message": f"Repository '{repo_id}' removed successfully"
    }


@router.post("/repositories/{repo_id}/index", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def index_repository(
    request: Request,
    repo_id: str,
    current_user: UserPublic = Depends(get_current_user)
):
    """Index a repository for RAG and analysis."""
    service = get_multi_repo_service()
    
    if repo_id not in service.repositories:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repo_id}' not found"
        )
    
    try:
        result = await service.index_repository(repo_id)
        
        return {
            "message": f"Repository '{repo_id}' indexed successfully",
            "files_indexed": result.get("files_indexed", 0),
            "duration": result.get("duration", 0)
        }
    except Exception as e:
        logger.error(f"Failed to index repository {repo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/context", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_multi_repo_context(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get combined context from all indexed repositories."""
    service = get_multi_repo_service()
    
    try:
        context = service.get_combined_context()
        
        return {
            "context": context.to_dict() if context else None,
            "repositories_count": len(service.repositories),
            "indexed_count": sum(1 for r in service.repositories.values() if r.indexed)
        }
    except Exception as e:
        logger.error(f"Failed to get multi-repo context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/cross-links", response_model=Dict[str, Any])
@limiter.limit("20/minute")
async def get_cross_repo_links(
    request: Request,
    current_user: UserPublic = Depends(get_current_user)
):
    """Get cross-repository dependency links."""
    service = get_multi_repo_service()
    
    links = [link.to_dict() for link in service.cross_repo_links]
    
    return {
        "links": links,
        "total": len(links)
    }
