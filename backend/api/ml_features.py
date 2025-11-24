"""
ML Feature Engineering API endpoints.
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import List, Dict, Any, Optional
from backend.models.dto import MLFeatureRequest, MLFeatureResponse
from backend.services.ml_features import get_engineer
from backend.core.middleware import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis/ml-features", tags=["ml-features"])


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



