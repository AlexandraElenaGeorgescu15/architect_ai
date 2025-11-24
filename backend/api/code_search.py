from fastapi import APIRouter, Depends

from backend.core.dependencies import get_current_user
from backend.models.dto import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResult,
)
from backend.services.semantic_search import get_semantic_search_service

router = APIRouter(prefix="/api/code-search", tags=["code-search"])


@router.post("/query", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    current_user=Depends(get_current_user),
) -> SemanticSearchResponse:
    """
    Perform semantic code/document search.
    """

    service = get_semantic_search_service()
    snippets = service.search(
        query=request.query,
        limit=request.limit or 20,
        metadata_filter=request.metadata_filter,
    )

    results = [
        SemanticSearchResult(
            content=snippet.content,
            file_path=snippet.file_path,
            score=snippet.score,
            start_line=snippet.start_line,
            end_line=snippet.end_line,
            metadata=snippet.metadata or {},
        )
        for snippet in snippets
    ]

    return SemanticSearchResponse(
        query=request.query,
        results=results,
        total=len(results),
    )

