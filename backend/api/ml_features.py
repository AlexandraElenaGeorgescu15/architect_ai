"""
ML Feature Engineering API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import Dict, Any
from backend.services.ml_features import get_engineer
from backend.core.middleware import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis/ml-features", tags=["ml-features"])

from backend.services.universal_context import get_universal_context_service
from pathlib import Path
import asyncio


@router.post("/extract-code", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def extract_code_features(request: Request, body: Dict[str, Any]):
    """
    Extract ML features from code content.
    
    Request body:
    {
        "code_content": "def hello(): ...",
        "file_path": "/path/to/file.py"
    }
    """
    code_content = body.get("code_content", "")
    file_path = body.get("file_path", "")
    
    if not code_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="code_content is required"
        )
    
    engineer = get_engineer()
    features = engineer.extract_code_features(code_content, file_path)
    
    return {
        "success": True,
        "features": features
    }


@router.post("/extract-diagram", response_model=Dict[str, Any])
@limiter.limit("30/minute")
async def extract_diagram_features(request: Request, body: Dict[str, Any]):
    """
    Extract ML features from diagram content.
    
    Request body:
    {
        "diagram_content": "graph TD\nA-->B",
        "diagram_type": "architecture"
    }
    """
    diagram_content = body.get("diagram_content", "")
    diagram_type = body.get("diagram_type", "unknown")
    
    if not diagram_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="diagram_content is required"
        )
    
    engineer = get_engineer()
    features = engineer.extract_diagram_features(diagram_content, diagram_type)
    
    return {
        "success": True,
        "features": features
    }


@router.post("/cluster", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def cluster_features(request: Request, body: Dict[str, Any]):
    """
    Cluster feature vectors.
    
    Request body:
    {
        "features_list": [
            {"lines_of_code": 100, "complexity": 5, ...},
            ...
        ],
        "n_clusters": 5,
        "method": "kmeans"
    }
    """
    features_list = body.get("features_list", [])
    n_clusters = body.get("n_clusters", 5)
    method = body.get("method", "kmeans")
    
    if not features_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="features_list is required"
        )
    
    engineer = get_engineer()
    result = engineer.cluster_features(features_list, n_clusters, method)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "success": True,
        "result": result
    }


@router.post("/reduce-dimensions", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def reduce_dimensions(request: Request, body: Dict[str, Any]):
    """
    Reduce feature dimensions using PCA.
    
    Request body:
    {
        "features_list": [
            {"lines_of_code": 100, "complexity": 5, ...},
            ...
        ],
        "n_components": 2
    }
    """
    features_list = body.get("features_list", [])
    n_components = body.get("n_components", 2)
    
    if not features_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="features_list is required"
        )
    
    engineer = get_engineer()
    result = engineer.reduce_dimensions(features_list, n_components)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "success": True,
        "result": result
    }


@router.post("/feature-importance", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def analyze_feature_importance(request: Request, body: Dict[str, Any]):
    """
    Analyze feature importance using Random Forest.
    
    Request body:
    {
        "features_list": [
            {"lines_of_code": 100, "complexity": 5, ...},
            ...
        ],
        "target_labels": [0, 1, 0, ...]  # optional
    }
    """
    features_list = body.get("features_list", [])
    target_labels = body.get("target_labels")
    
    if not features_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="features_list is required"
        )
    
    engineer = get_engineer()
    result = engineer.analyze_feature_importance(features_list, target_labels)
    
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return {
        "success": True,
        "result": result
    }


@router.post("/project/cluster", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def cluster_project_code(request: Request, body: Dict[str, Any]):
    """
    Analyze and cluster project code files.
    Uses Universal Context to find key files, extracts features, and clusters them.
    
    Request body:
    {
        "n_clusters": 5,
        "max_files": 50
    }
    """
    n_clusters = body.get("n_clusters", 5)
    max_files = body.get("max_files", 50)
    
    # 1. Get Universal Context to find files
    uc_service = get_universal_context_service()
    context = await uc_service.get_universal_context()
    
    # 2. Get key files (sorted by importance)
    feature_list = []
    
    # Use importance map keys which are absolute paths
    all_files = list(context.get("importance_scores", {}).keys())
    
    # Sort by importance
    all_files.sort(key=lambda f: context["importance_scores"][f], reverse=True)
    
    # Take top N files
    target_files = all_files[:max_files]
    
    engineer = get_engineer()
    
    # 3. Extract features for each file
    for file_path_str in target_files:
        try:
            path = Path(file_path_str)
            if not path.exists() or not path.is_file():
                continue
                
            # Skip non-code files
            if path.suffix.lower() not in ['.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.java']:
                continue
                
            content = path.read_text(encoding='utf-8', errors='ignore')
            if not content.strip():
                continue
                
            features = engineer.extract_code_features(content, str(path))
            feature_list.append(features)
            
        except Exception as e:
            logger.warning(f"Failed to process file {file_path_str} for clustering: {e}")
            continue
    
    if not feature_list:
        return {
            "success": False,
            "message": "No valid code files found to analyze."
        }
    
    # 4. Cluster them
    # Ensure we don't ask for more clusters than samples
    safe_clusters = min(n_clusters, len(feature_list))
    if safe_clusters < 2:
        return {
            "success": True,
            "result": {
                "cluster_labels": [0] * len(feature_list),
                "cluster_stats": {
                    0: {
                        "size": len(feature_list),
                        "samples": [str(Path(f["file_path"]).name) for f in feature_list],
                        "avg_complexity": sum(f.get("cyclomatic_complexity_estimate", 0) for f in feature_list) / len(feature_list)
                    }
                },
                "n_clusters": 1,
                "note": "Not enough samples for clustering"
            },
            "files_analyzed": len(feature_list)
        }
        
    result = engineer.cluster_features(feature_list, n_clusters=safe_clusters)
    
    # Clean up result for frontend (basename only)
    if "cluster_stats" in result:
        for cid, stats in result["cluster_stats"].items():
            if "samples" in stats:
                stats["samples"] = [str(Path(p).name) for p in stats["samples"]]
    
    return {
        "success": True,
        "result": result,
        "files_analyzed": len(feature_list)
    }




