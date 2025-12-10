"""
Knowledge Graph API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pathlib import Path
from typing import Optional
from backend.models.dto import GraphDTO, GraphNodeDTO, GraphEdgeDTO
from backend.services.knowledge_graph import get_builder
from backend.core.middleware import limiter
from backend.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])


def _get_target_directory(provided_path: Optional[str] = None) -> Path:
    """
    Get the target directory for analysis.
    Priority: provided_path > settings.target_repo_path > user project directories
    
    IMPORTANT: This should NEVER return the Architect.AI tool directory.
    """
    from backend.utils.tool_detector import get_user_project_directories, detect_tool_directory
    
    # If path is provided and exists, use it
    if provided_path:
        provided = Path(provided_path)
        if provided.exists():
            logger.info(f"Using provided directory: {provided}")
            return provided
    
    # Use configured target repo path if set
    if settings.target_repo_path:
        target = Path(settings.target_repo_path)
        if target.exists():
            logger.info(f"Using configured target_repo_path: {target}")
            return target
    
    # Get user project directories (siblings of tool)
    user_dirs = get_user_project_directories()
    tool_dir = detect_tool_directory()
    
    logger.info(f"🔍 [TARGET_DIR] Tool directory: {tool_dir}")
    logger.info(f"🔍 [TARGET_DIR] Found {len(user_dirs)} sibling directories")
    
    if user_dirs:
        # Score directories to find the most likely "main" project
        scored_dirs = []
        for d in user_dirs:
            if d == tool_dir or not d.exists():
                continue
            
            score = 0
            name_lower = d.name.lower()
            
            # Deprioritize utility/shared directories
            if name_lower in ['agents', 'components', 'utils', 'shared', 'common', 'lib', 'libs']:
                score -= 100
            
            # Prioritize directories with project markers
            if (d / 'package.json').exists():
                score += 50  # Node.js/Angular/React project
            if (d / 'angular.json').exists():
                score += 60  # Angular project (higher priority)
            if (d / 'pom.xml').exists() or (d / 'build.gradle').exists():
                score += 50  # Java project
            if (d / 'Cargo.toml').exists():
                score += 50  # Rust project
            if (d / 'go.mod').exists():
                score += 50  # Go project
            if (d / 'requirements.txt').exists() or (d / 'setup.py').exists():
                score += 40  # Python project
            if (d / '.csproj').exists() or any(d.glob('*.csproj')):
                score += 50  # .NET project
            if any(d.glob('*.sln')):
                score += 55  # .NET solution
            if (d / 'src').is_dir():
                score += 30  # Has src directory
            if (d / 'frontend').is_dir():
                score += 20  # Has frontend
            if (d / 'backend').is_dir():
                score += 20  # Has backend
            
            # Prioritize directories with "project" or "final" in name
            if 'project' in name_lower or 'final' in name_lower:
                score += 25
            
            scored_dirs.append((d, score))
            logger.debug(f"🔍 [TARGET_DIR] Scored {d.name}: {score}")
        
        if scored_dirs:
            # Sort by score descending and pick the best
            scored_dirs.sort(key=lambda x: x[1], reverse=True)
            best_dir, best_score = scored_dirs[0]
            logger.info(f"✅ [TARGET_DIR] Selected user project: {best_dir} (score: {best_score})")
            return best_dir
    
    # Fallback to parent of tool (the "mother project")
    if tool_dir:
        parent = tool_dir.parent
        logger.warning(f"⚠️ [TARGET_DIR] Falling back to tool parent directory: {parent}")
        return parent
    
    # Last resort - this should NOT happen
    logger.error("❌ [TARGET_DIR] Could not determine target directory - falling back to cwd (THIS MAY BE WRONG)")
    return Path.cwd()


@router.post("/build", response_model=dict)
@limiter.limit("5/minute")
async def build_graph(
    request: Request,
    body: dict,
    background_tasks: BackgroundTasks
):
    """
    Build knowledge graph from directory.
    
    Request body:
    {
        "directory": "/path/to/directory",  (optional - defaults to user project)
        "recursive": true,
        "use_cache": true
    }
    """
    directory = _get_target_directory(body.get("directory"))
    recursive = body.get("recursive", True)
    use_cache = body.get("use_cache", True)
    
    logger.info(f"🔍 [KG] Building knowledge graph from: {directory}")
    
    if not directory.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {directory}"
        )
    
    builder = get_builder()
    
    # Check cache
    if use_cache:
        if builder.load_cached_graph():
            return {
                "message": "Graph loaded from cache",
                "stats": builder.get_stats()
            }
    
    # Build in background
    def build_task():
        builder.build_graph(directory, recursive)
        if use_cache:
            builder.cache_graph()
    
    background_tasks.add_task(build_task)
    
    return {
        "message": "Graph building started",
        "directory": str(directory),
        "recursive": recursive
    }


@router.get("/stats", response_model=dict)
async def get_graph_stats():
    """Get knowledge graph statistics."""
    builder = get_builder()
    return builder.get_stats()


@router.get("/graph", response_model=GraphDTO)
async def get_graph():
    """Get full knowledge graph."""
    builder = get_builder()
    
    if not builder.graph.nodes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph not built. Call /build first."
        )
    
    # Convert to DTO format
    nodes = []
    for node_id, data in builder.graph.nodes(data=True):
        nodes.append(GraphNodeDTO(
            id=node_id,
            label=data.get("name", node_id),
            type=data.get("type", "unknown"),
            properties={k: v for k, v in data.items() if k not in ["name", "type"]}
        ))
    
    edges = []
    for source, target, data in builder.graph.edges(data=True):
        edges.append(GraphEdgeDTO(
            source=source,
            target=target,
            relationship=data.get("relationship", "related"),
            weight=data.get("weight")
        ))
    
    return GraphDTO(
        nodes=nodes,
        edges=edges,
        metadata=builder.get_stats()
    )


@router.get("/current")
async def get_current_graph():
    """
    Get current knowledge graph in simplified format for frontend.
    Returns components, relationships, and summary statistics.
    """
    try:
        builder = get_builder()
        
        # Try to load from cache or return empty state
        if not builder.graph or not builder.graph.nodes:
            try:
                builder.load_cached_graph()
            except Exception as e:
                logger.warning(f"Could not load cached graph: {e}")
        
        if not builder.graph or not builder.graph.nodes:
            return {
                "components": [],
                "relationships": [],
                "summary": {
                    "total_classes": 0,
                    "total_functions": 0,
                    "total_files": 0
                }
            }
        
        # Extract components (nodes)
        components = []
        for node_id, node_data in builder.graph.nodes(data=True):
            components.append({
                "id": node_id,
                "name": node_data.get("name", node_id),
                "type": node_data.get("type", "unknown"),
                "file": node_data.get("file", ""),
                "line_start": node_data.get("line_start"),
                "line_end": node_data.get("line_end")
            })
        
        # Extract relationships (edges)
        relationships = []
        for source, target, edge_data in builder.graph.edges(data=True):
            relationships.append({
                "source": source,
                "target": target,
                "type": edge_data.get("relationship", "related")
            })
        
        # Get summary stats
        stats = builder.get_stats()
    except Exception as e:
        logger.error(f"Error getting current graph: {e}", exc_info=True)
        return {
            "components": [],
            "relationships": [],
            "summary": {
                "total_classes": 0,
                "total_functions": 0,
                "total_files": 0
            },
            "error": str(e)
        }
    
    return {
        "components": components[:100],  # Limit to first 100
        "relationships": relationships[:200],  # Limit to first 200
        "summary": {
            "total_classes": stats.get("total_classes", 0),
            "total_functions": stats.get("total_functions", 0),
            "total_files": stats.get("total_files", 0),
            "total_components": len(components),
            "total_relationships": len(relationships)
        }
    }


@router.get("/path")
async def get_shortest_path(source: str, target: str):
    """
    Get shortest path between two nodes.
    
    Query parameters:
    - source: Source node name or ID
    - target: Target node name or ID
    """
    builder = get_builder()
    path = builder.get_shortest_path(source, target)
    
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No path found between {source} and {target}"
        )
    
    return {
        "source": source,
        "target": target,
        "path": path,
        "length": len(path) - 1
    }


@router.get("/centrality")
async def get_centrality(metric: str = "degree"):
    """
    Get centrality metrics for nodes.
    
    Query parameters:
    - metric: Centrality metric (degree, betweenness, closeness, eigenvector)
    """
    builder = get_builder()
    
    try:
        centrality = builder.get_centrality(metric)
        # Return top 20 nodes
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:20]
        return {
            "metric": metric,
            "top_nodes": [{"node_id": node_id, "score": score} for node_id, score in sorted_nodes]
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/most-connected")
async def get_most_connected(top_k: int = 10):
    """
    Get nodes with most connections.
    
    Query parameters:
    - top_k: Number of top nodes to return
    """
    builder = get_builder()
    nodes = builder.get_most_connected_nodes(top_k)
    
    return {
        "top_k": top_k,
        "nodes": [{"node_id": node_id, "degree": degree} for node_id, degree in nodes]
    }


@router.post("/export")
async def export_graph(request: dict):
    """
    Export graph to JSON file.
    
    Request body:
    {
        "output_path": "/path/to/output.json"
    }
    """
    output_path = Path(request.get("output_path", "outputs/knowledge_graph.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    builder = get_builder()
    builder.export_to_json(output_path)
    
    return {
        "message": "Graph exported",
        "output_path": str(output_path)
    }


@router.post("/cache")
async def cache_graph():
    """Cache current graph to disk."""
    builder = get_builder()
    builder.cache_graph()
    
    return {
        "message": "Graph cached",
        "stats": builder.get_stats()
    }



