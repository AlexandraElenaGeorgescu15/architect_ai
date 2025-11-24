"""
Test that all services can be imported and initialized.
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_import_context_builder():
    """Test Context Builder import."""
    from backend.services.context_builder import get_builder
    builder = get_builder()
    assert builder is not None


def test_import_generation_service():
    """Test Generation Service import."""
    from backend.services.generation_service import get_service
    service = get_service()
    assert service is not None


def test_import_validation_service():
    """Test Validation Service import."""
    from backend.services.validation_service import get_service
    service = get_service()
    assert service is not None


def test_import_feedback_service():
    """Test Feedback Service import."""
    from backend.services.feedback_service import get_service
    service = get_service()
    assert service is not None


def test_import_rag_services():
    """Test RAG services import."""
    from backend.services.rag_retriever import RAGRetriever
    from backend.services.rag_ingester import RAGIngester
    from backend.services.rag_cache import get_rag_cache
    
    retriever = RAGRetriever()
    assert retriever is not None
    
    ingester = RAGIngester()
    assert ingester is not None
    
    cache = get_rag_cache()
    assert cache is not None


def test_import_analysis_services():
    """Test analysis services import."""
    from backend.services.knowledge_graph import get_builder
    from backend.services.pattern_mining import get_miner
    from backend.services.ml_features import get_engineer
    
    kg = get_builder()
    assert kg is not None
    
    pm = get_miner()
    assert pm is not None
    
    ml = get_engineer()
    assert ml is not None


def test_import_models():
    """Test model imports."""
    from backend.models.dto import (
        ArtifactType, GenerationStatus, ContextRequest, ContextResponse,
        GenerationRequest, ValidationResultDTO, FeedbackRequest
    )
    
    # Test enum values
    assert ArtifactType.MERMAID_ERD is not None
    assert GenerationStatus.PENDING is not None


def test_import_core():
    """Test core imports."""
    from backend.core.config import settings
    from backend.core.auth import create_access_token
    from backend.core.database import get_db
    
    assert settings is not None
    assert create_access_token is not None
    assert get_db is not None



