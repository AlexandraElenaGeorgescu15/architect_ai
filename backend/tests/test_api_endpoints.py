"""
API endpoint integration tests.
Tests FastAPI endpoints with test client.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from starlette.middleware.trustedhost import TrustedHostMiddleware

# Disable TrustedHostMiddleware for testing
app.user_middleware = [m for m in app.user_middleware if m.cls != TrustedHostMiddleware]
app.middleware_stack = app.build_middleware_stack()

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Status can be 'ready', 'initializing', etc.
    assert data["status"] in ["ready", "initializing", "starting"]


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


# def test_auth_endpoints():
#     """Test authentication endpoints."""
#     # Test login (would need valid credentials)
#     response = client.post(
#         "/api/auth/login",
#         data={"username": "testuser", "password": "password"}
#     )
#     # Should either succeed or return 401
#     assert response.status_code in [200, 401]


def test_rag_endpoints():
    """Test RAG endpoints (requires authentication)."""
    # These would require authentication in production
    # For now, just test that endpoints exist
    response = client.get("/api/rag/index/stats")
    # Should return 401 (unauthorized) or 200 if auth is optional
    assert response.status_code in [200, 401, 422]


def test_knowledge_graph_endpoints():
    """Test Knowledge Graph endpoints."""
    response = client.get("/api/knowledge-graph/stats")
    assert response.status_code in [200, 401, 422]


def test_validation_endpoints():
    """Test Validation endpoints."""
    # Test validation endpoint structure
    response = client.post(
        "/api/validation/validate",
        json={
            "artifact_type": "mermaid_erd",
            "content": "erDiagram\nUser ||--o{ Post"
        }
    )
    # Should return 401 (unauthorized) or validation result
    assert response.status_code in [200, 401, 422]


def test_openapi_schema():
    """Test OpenAPI schema generation."""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema



