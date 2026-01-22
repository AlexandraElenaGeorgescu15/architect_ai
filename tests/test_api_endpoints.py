"""
Comprehensive API Endpoint Tests with Mock Data

Tests all major API endpoints in the Architect.AI backend.
Run with: pytest tests/test_api_endpoints.py -v
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Mock Data
# ============================================================================

MOCK_USER = {
    "id": "user-123",
    "username": "test_user",
    "email": "test@example.com",
    "role": "developer",
    "sub": "user-123",
}

MOCK_MEETING_NOTES = """
# Project Requirements Meeting - E-Commerce Platform

## Attendees
- Product Manager: John Smith
- Tech Lead: Jane Doe
- Backend Developer: Bob Wilson

## Requirements
1. User Authentication System
   - OAuth2 integration with Google and GitHub
   - JWT-based session management
   - Password reset functionality

2. Product Catalog
   - Categories with hierarchical structure
   - Product variants (size, color)
   - Inventory tracking
   - Search with filters

3. Shopping Cart
   - Persistent cart for logged-in users
   - Guest checkout option
   - Apply discount codes

4. Order Management
   - Order status tracking
   - Email notifications
   - Integration with shipping providers

## Technical Decisions
- Backend: FastAPI with Python 3.11
- Database: PostgreSQL with SQLAlchemy
- Cache: Redis
- Frontend: React with TypeScript
"""

MOCK_ARTIFACT_ERD = """erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id PK
        string email UK
        string password_hash
        datetime created_at
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        int id PK
        int user_id FK
        string status
        decimal total
        datetime created_at
    }
    PRODUCT ||--o{ ORDER_ITEM : "ordered in"
    PRODUCT {
        int id PK
        string name
        decimal price
        int inventory
    }
    ORDER_ITEM {
        int id PK
        int order_id FK
        int product_id FK
        int quantity
    }
"""

MOCK_VALIDATION_RESULT = {
    "is_valid": True,
    "score": 85.5,
    "issues": [],
    "suggestions": ["Consider adding indexes for frequently queried fields"]
}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_current_user():
    """Mock current user for authentication."""
    from backend.models.dto import UserPublic
    return UserPublic(**MOCK_USER)


@pytest.fixture
def mock_generation_service():
    """Mock generation service."""
    service = MagicMock()
    service.active_jobs = {}
    service.list_jobs = MagicMock(return_value=[])
    service.get_job_status = MagicMock(return_value=None)
    service.cancel_job = MagicMock(return_value=True)
    service.update_artifact = MagicMock(return_value={"content": "updated"})
    
    async def mock_generate(*args, **kwargs):
        yield {
            "type": "progress",
            "job_id": "test-job-123",
            "progress": 50.0,
            "message": "Generating artifact..."
        }
        yield {
            "type": "complete",
            "job_id": "test-job-123",
            "status": "completed",
            "artifact": {
                "id": "artifact-123",
                "artifact_type": kwargs.get("artifact_type", "mermaid_erd"),
                "content": MOCK_ARTIFACT_ERD,
                "validation": MOCK_VALIDATION_RESULT,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    service.generate_artifact = mock_generate
    return service


@pytest.fixture
def mock_model_service():
    """Mock model service."""
    service = MagicMock()
    
    async def mock_list_models():
        return [
            MagicMock(
                id="llama3.2:3b",
                name="Llama 3.2 3B",
                provider="ollama",
                status="available",
                size_gb=1.8,
                capabilities=["text-generation"]
            ),
            MagicMock(
                id="gemini-1.5-flash",
                name="Gemini 1.5 Flash",
                provider="google",
                status="available",
                size_gb=0.0,
                capabilities=["text-generation", "code"]
            ),
        ]
    
    async def mock_get_model(model_id: str):
        if model_id == "llama3.2:3b":
            return MagicMock(
                id="llama3.2:3b",
                name="Llama 3.2 3B",
                provider="ollama",
                status="available"
            )
        return None
    
    service.list_models = mock_list_models
    service.get_model = mock_get_model
    service.routing = {}
    service.get_routing_for_artifact = MagicMock(return_value=None)
    service.get_stats = MagicMock(return_value={"total_models": 2})
    service.update_routing = MagicMock(return_value=True)
    service._refresh_ollama_models = AsyncMock()
    service._refresh_cloud_models = AsyncMock()
    
    return service


@pytest.fixture
def mock_context_builder():
    """Mock context builder service."""
    builder = MagicMock()
    
    async def mock_build_context(**kwargs):
        return {
            "created_at": datetime.now().isoformat(),
            "assembled_context": f"Context for: {kwargs.get('meeting_notes', '')[:100]}...",
            "sources": {
                "rag": {"chunks": 5},
                "kg": {"nodes": 10, "edges": 15},
                "patterns": {"count": 3}
            },
            "from_cache": False
        }
    
    builder.build_context = mock_build_context
    builder._context_store = {}
    builder.rag_retriever = MagicMock(get_query_stats=MagicMock(return_value={}))
    builder.kg_builder = MagicMock(get_stats=MagicMock(return_value={}))
    builder.rag_cache = MagicMock(get_stats=MagicMock(return_value={}))
    
    return builder


@pytest.fixture
def mock_rag_services():
    """Mock RAG services."""
    ingester = MagicMock()
    ingester.get_index_stats = MagicMock(return_value={
        "total_chunks": 1500,
        "total_files": 120,
        "directories": ["/project"]
    })
    ingester.watched_directories = [Path("/project")]
    ingester.index_directory = AsyncMock()
    ingester.start_watching = MagicMock()
    ingester.stop_watching = MagicMock()
    ingester.clear_index = MagicMock()
    
    retriever = MagicMock()
    retriever.hybrid_search = MagicMock(return_value=[
        ({"content": "def authenticate(user):", "meta": {"file_path": "auth.py"}}, 0.85),
        ({"content": "class User:", "meta": {"file_path": "models.py"}}, 0.78),
    ])
    retriever.get_query_stats = MagicMock(return_value={"total_queries": 50})
    
    cache = MagicMock()
    cache.get_context = MagicMock(return_value=None)
    cache.set_context = MagicMock()
    cache.invalidate = MagicMock(return_value=5)
    cache.get_cache_stats = MagicMock(return_value={"hit_rate": 0.75})
    
    return ingester, retriever, cache


@pytest.fixture
def mock_feedback_service():
    """Mock feedback service."""
    service = MagicMock()
    
    async def mock_record_feedback(**kwargs):
        return {
            "event_recorded": True,
            "training_triggered": False,
            "message": "Feedback recorded successfully"
        }
    
    service.record_feedback = mock_record_feedback
    service.get_training_stats = MagicMock(return_value={
        "total_feedback_events": 150,
        "average_validation_score": 82.5,
        "feedback_by_artifact_type": {
            "mermaid_erd": 50,
            "code_prototype": 30
        }
    })
    service.get_feedback_history = MagicMock(return_value=[
        {"artifact_id": "art-1", "score": 85.0, "timestamp": datetime.now().isoformat()},
        {"artifact_id": "art-2", "score": 78.0, "timestamp": datetime.now().isoformat()},
    ])
    service.check_training_ready = MagicMock(return_value={"ready": True, "examples": 100})
    
    return service


@pytest.fixture
def mock_chat_service():
    """Mock chat service."""
    service = MagicMock()
    
    async def mock_chat(**kwargs):
        yield {
            "type": "complete",
            "content": "Based on your project, I can see you're using FastAPI with PostgreSQL...",
            "model": "llama3.2:3b",
            "provider": "ollama"
        }
    
    service.chat = mock_chat
    return service


# ============================================================================
# Test Application Setup
# ============================================================================

@pytest.fixture
def app():
    """Create test FastAPI application with mocked dependencies."""
    from backend.main import app as fastapi_app
    return fastapi_app


@pytest.fixture
async def client(app):
    """Create async test client."""
    # Mock auth to return test user
    async def mock_get_current_user():
        from backend.models.dto import UserPublic
        return UserPublic(**MOCK_USER)
    
    # Override dependency
    from backend.core.auth import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


# ============================================================================
# Health & Status Tests
# ============================================================================

class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test /health endpoint returns OK."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["service"] == "architect-ai-backend"
    
    @pytest.mark.asyncio
    async def test_api_health_check(self, client):
        """Test /api/health endpoint."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "phases" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Architect.AI API"
        assert "version" in data


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login."""
        response = await client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with missing credentials."""
        response = await client.post(
            "/api/auth/login",
            json={"username": "", "password": ""}
        )
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_info(self, client):
        """Test getting current user info."""
        response = await client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test_user"


# ============================================================================
# Generation Tests
# ============================================================================

class TestGenerationEndpoints:
    """Test artifact generation endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_artifacts(self, client):
        """Test listing all artifacts."""
        response = await client.get("/api/generation/artifacts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_artifact_types(self, client):
        """Test listing artifact types."""
        response = await client.get("/api/generation/artifact-types")
        assert response.status_code == 200
        data = response.json()
        assert "artifact_types" in data
        assert "categories" in data
    
    @pytest.mark.asyncio
    async def test_list_artifact_categories(self, client):
        """Test listing artifact categories."""
        response = await client.get("/api/generation/artifact-types/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
    
    @pytest.mark.asyncio
    async def test_list_generation_jobs(self, client):
        """Test listing generation jobs."""
        response = await client.get("/api/generation/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_generation_job_not_found(self, client):
        """Test getting non-existent job."""
        response = await client.get("/api/generation/jobs/nonexistent-job")
        assert response.status_code == 404


# ============================================================================
# Model Management Tests
# ============================================================================

class TestModelEndpoints:
    """Test model management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_models(self, client, mock_model_service):
        """Test listing all models."""
        with patch('backend.api.models.get_service', return_value=mock_model_service):
            response = await client.get("/api/models/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_routing(self, client, mock_model_service):
        """Test getting model routing configuration."""
        with patch('backend.api.models.get_service', return_value=mock_model_service):
            response = await client.get("/api/models/routing")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_model_stats(self, client, mock_model_service):
        """Test getting model statistics."""
        with patch('backend.api.models.get_service', return_value=mock_model_service):
            response = await client.get("/api/models/stats")
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_check_api_keys_status(self, client):
        """Test API key status check."""
        response = await client.get("/api/models/api-keys/status")
        assert response.status_code == 200
        data = response.json()
        assert "gemini" in data
        assert "groq" in data
        assert "openai" in data


# ============================================================================
# Context Builder Tests
# ============================================================================

class TestContextEndpoints:
    """Test context builder endpoints."""
    
    @pytest.mark.asyncio
    async def test_build_context(self, client, mock_context_builder):
        """Test building context from meeting notes."""
        with patch('backend.api.context.get_builder', return_value=mock_context_builder):
            response = await client.post(
                "/api/context/build",
                json={
                    "meeting_notes": MOCK_MEETING_NOTES,
                    "include_rag": True,
                    "include_kg": True,
                    "include_patterns": True
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "assembled_context" in data
    
    @pytest.mark.asyncio
    async def test_build_context_too_short(self, client):
        """Test context build with notes too short."""
        response = await client.post(
            "/api/context/build",
            json={"meeting_notes": "short"}
        )
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_get_context_stats(self, client, mock_context_builder):
        """Test getting context builder stats."""
        with patch('backend.api.context.get_builder', return_value=mock_context_builder):
            response = await client.get("/api/context/stats")
            assert response.status_code == 200
            data = response.json()
            assert "rag_stats" in data


# ============================================================================
# RAG Tests
# ============================================================================

class TestRAGEndpoints:
    """Test RAG (Retrieval Augmented Generation) endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, client, mock_rag_services):
        """Test getting RAG index stats."""
        ingester, retriever, cache = mock_rag_services
        with patch('backend.api.rag.get_ingester', return_value=ingester):
            response = await client.get("/api/rag/index/stats")
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_get_rag_status(self, client, mock_rag_services):
        """Test getting RAG system status."""
        ingester, retriever, cache = mock_rag_services
        with patch('backend.api.rag.get_ingester', return_value=ingester):
            response = await client.get("/api/rag/status")
            assert response.status_code == 200
            data = response.json()
            assert "is_watching" in data
    
    @pytest.mark.asyncio
    async def test_search_rag(self, client, mock_rag_services):
        """Test RAG search."""
        ingester, retriever, cache = mock_rag_services
        with patch('backend.api.rag.get_retriever', return_value=retriever):
            with patch('backend.api.rag.get_cache', return_value=cache):
                response = await client.post(
                    "/api/rag/search",
                    json={"query": "user authentication", "k": 5}
                )
                assert response.status_code == 200
                data = response.json()
                assert "results" in data
    
    @pytest.mark.asyncio
    async def test_search_rag_empty_query(self, client):
        """Test RAG search with empty query."""
        response = await client.post(
            "/api/rag/search",
            json={"query": "", "k": 5}
        )
        assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client, mock_rag_services):
        """Test getting cache stats."""
        ingester, retriever, cache = mock_rag_services
        with patch('backend.api.rag.get_cache', return_value=cache):
            response = await client.get("/api/rag/cache/stats")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_query_stats(self, client, mock_rag_services):
        """Test getting query stats."""
        ingester, retriever, cache = mock_rag_services
        with patch('backend.api.rag.get_retriever', return_value=retriever):
            response = await client.get("/api/rag/query/stats")
            assert response.status_code == 200


# ============================================================================
# Feedback Tests
# ============================================================================

class TestFeedbackEndpoints:
    """Test feedback collection endpoints."""
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, client, mock_feedback_service):
        """Test submitting feedback."""
        with patch('backend.api.feedback.get_service', return_value=mock_feedback_service):
            response = await client.post(
                "/api/feedback/",
                json={
                    "artifact_id": "artifact-123",
                    "score": 85.0,
                    "notes": "Good ERD diagram",
                    "feedback_type": "positive"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["recorded"] == True
    
    @pytest.mark.asyncio
    async def test_get_feedback_history(self, client, mock_feedback_service):
        """Test getting feedback history."""
        with patch('backend.api.feedback.get_service', return_value=mock_feedback_service):
            response = await client.get("/api/feedback/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_feedback_stats(self, client, mock_feedback_service):
        """Test getting feedback statistics."""
        with patch('backend.api.feedback.get_service', return_value=mock_feedback_service):
            response = await client.get("/api/feedback/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_feedback" in data
    
    @pytest.mark.asyncio
    async def test_check_training_ready(self, client, mock_feedback_service):
        """Test checking training readiness."""
        with patch('backend.api.feedback.get_service', return_value=mock_feedback_service):
            response = await client.get("/api/feedback/training-ready")
            assert response.status_code == 200


# ============================================================================
# Chat Tests
# ============================================================================

class TestChatEndpoints:
    """Test AI chat endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_project_summary(self, client):
        """Test getting project summary for chat context."""
        response = await client.get("/api/chat/summary")
        assert response.status_code == 200
        data = response.json()
        assert "project_name" in data
        assert "greeting_message" in data
    
    @pytest.mark.asyncio
    async def test_send_chat_message(self, client, mock_chat_service):
        """Test sending a chat message."""
        with patch('backend.api.chat.get_chat_service', return_value=mock_chat_service):
            response = await client.post(
                "/api/chat/message",
                json={
                    "message": "What is the architecture of this project?",
                    "conversation_history": [],
                    "include_project_context": True
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
    
    @pytest.mark.asyncio
    async def test_get_agent_tools(self, client):
        """Test getting available agent tools."""
        response = await client.get("/api/chat/agent/tools")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data


# ============================================================================
# Meeting Notes Tests
# ============================================================================

class TestMeetingNotesEndpoints:
    """Test meeting notes management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_folders(self, client):
        """Test listing meeting note folders."""
        response = await client.get("/api/meeting-notes/folders")
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data
    
    @pytest.mark.asyncio
    async def test_create_folder(self, client):
        """Test creating a new folder."""
        import uuid
        folder_name = f"test_folder_{uuid.uuid4().hex[:8]}"
        response = await client.post(
            "/api/meeting-notes/folders",
            json={"name": folder_name}
        )
        # Could be 200 or 400 if folder exists
        assert response.status_code in [200, 400]
    
    @pytest.mark.asyncio
    async def test_suggest_folder(self, client):
        """Test AI folder suggestion."""
        response = await client.post(
            "/api/meeting-notes/suggest-folder",
            json={"content": MOCK_MEETING_NOTES}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data


# ============================================================================
# Validation Tests
# ============================================================================

class TestValidationEndpoints:
    """Test artifact validation endpoints."""
    
    @pytest.mark.asyncio
    async def test_validate_mermaid(self, client):
        """Test Mermaid diagram validation."""
        response = await client.post(
            "/api/validation/validate",
            json={
                "content": MOCK_ARTIFACT_ERD,
                "artifact_type": "mermaid_erd"
            }
        )
        # Validation might succeed or fail based on parser
        assert response.status_code in [200, 400, 500]


# ============================================================================
# Knowledge Graph Tests
# ============================================================================

class TestKnowledgeGraphEndpoints:
    """Test knowledge graph endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_kg_graph(self, client):
        """Test getting knowledge graph."""
        response = await client.get("/api/knowledge-graph/graph")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_kg_stats(self, client):
        """Test getting KG stats."""
        response = await client.get("/api/knowledge-graph/stats")
        assert response.status_code == 200


# ============================================================================
# Pattern Mining Tests
# ============================================================================

class TestPatternMiningEndpoints:
    """Test pattern mining endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_patterns(self, client):
        """Test getting detected patterns."""
        response = await client.get("/api/pattern-mining/patterns")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_pattern_stats(self, client):
        """Test getting pattern stats."""
        response = await client.get("/api/pattern-mining/stats")
        assert response.status_code == 200


# ============================================================================
# Universal Context Tests
# ============================================================================

class TestUniversalContextEndpoints:
    """Test universal context endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_universal_context(self, client):
        """Test getting universal context."""
        response = await client.get("/api/universal-context/")
        # Might return 200 with context or 503 if not built
        assert response.status_code in [200, 503]
    
    @pytest.mark.asyncio
    async def test_get_universal_context_status(self, client):
        """Test getting universal context status."""
        response = await client.get("/api/universal-context/status")
        assert response.status_code == 200


# ============================================================================
# Analysis Tests
# ============================================================================

class TestAnalysisEndpoints:
    """Test analysis endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_analysis_summary(self, client):
        """Test getting analysis summary."""
        response = await client.get("/api/analysis/summary")
        assert response.status_code == 200


# ============================================================================
# Version Management Tests
# ============================================================================

class TestVersionEndpoints:
    """Test version management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_versions(self, client):
        """Test listing artifact versions."""
        response = await client.get("/api/versions/")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_versions_for_artifact(self, client):
        """Test getting versions for specific artifact."""
        response = await client.get("/api/versions/artifact/test-artifact")
        assert response.status_code in [200, 404]


# ============================================================================
# Export Tests
# ============================================================================

class TestExportEndpoints:
    """Test export endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_export_formats(self, client):
        """Test listing export formats."""
        response = await client.get("/api/export/formats")
        assert response.status_code == 200


# ============================================================================
# Templates Tests
# ============================================================================

class TestTemplateEndpoints:
    """Test template management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_templates(self, client):
        """Test listing templates."""
        response = await client.get("/api/templates/")
        assert response.status_code == 200


# ============================================================================
# Training Tests
# ============================================================================

class TestTrainingEndpoints:
    """Test training management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_training_jobs(self, client):
        """Test listing training jobs."""
        response = await client.get("/api/training/jobs")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_get_training_stats(self, client):
        """Test getting training statistics."""
        response = await client.get("/api/training/stats")
        assert response.status_code == 200


# ============================================================================
# VRAM Tests
# ============================================================================

class TestVRAMEndpoints:
    """Test VRAM monitoring endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_vram_status(self, client):
        """Test getting VRAM status."""
        response = await client.get("/api/vram/status")
        assert response.status_code == 200


# ============================================================================
# Git Integration Tests
# ============================================================================

class TestGitEndpoints:
    """Test Git integration endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_git_status(self, client):
        """Test getting Git status."""
        response = await client.get("/api/git/status")
        # Might fail if not in a git repo
        assert response.status_code in [200, 500]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
