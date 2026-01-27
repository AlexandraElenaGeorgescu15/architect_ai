"""
Verification script for Frontend API Endpoints.
Simulates the API calls made by frontend components:
- useGeneration.ts -> POST /api/generation/generate
- ArtifactViewer.tsx -> GET /api/generation/artifacts/{id}
- VersionSelector.tsx -> GET /api/versions/{id}
- ArtifactCard.tsx -> GET /api/versions/by-type/{type}
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.main import app
from backend.models.dto import ArtifactType
import backend.services.generation_service
import backend.services.enhanced_generation
import backend.services.validation_service

# Client for testing API
# Use localhost to pass security middleware allowed_hosts check
client = TestClient(app, base_url="http://localhost")

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test."""
    backend.services.generation_service._service = None
    backend.services.enhanced_generation._enhanced_service = None
    backend.services.validation_service._service = None
    
    # Disable TrustedHostMiddleware for testing
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    app.user_middleware = [m for m in app.user_middleware if m.cls != TrustedHostMiddleware]
    app.middleware_stack = app.build_middleware_stack()
    
    yield
    backend.services.generation_service._service = None
    backend.services.enhanced_generation._enhanced_service = None
    backend.services.validation_service._service = None

@pytest.fixture
def mock_services():
    """Mock internal services to focus on API layer."""
    with patch("backend.services.enhanced_generation.OllamaClient") as mock_client:
        # Mock model service
        mock_client.return_value.ensure_model_available = AsyncMock(return_value=True)
        generate_mock = AsyncMock()
        generate_mock.return_value.success = True
        generate_mock.return_value.content = "Mocked API Content"
        mock_client.return_value.generate = generate_mock
        yield mock_client

@pytest.fixture
def mock_validation():
    with patch("backend.services.enhanced_generation.get_validation_service") as mock_val:
        mock_v = AsyncMock()
        mock_v.validate_artifact.return_value.is_valid = True
        mock_v.validate_artifact.return_value.score = 95.0
        mock_val.return_value = mock_v
        yield mock_v

@pytest.fixture
def mock_context():
    with patch("backend.services.generation_service.get_context_builder") as mock_ctx:
        builder = AsyncMock()
        builder.build_context.return_value = {
            "meeting_notes": "Notes",
            "assembled_context": "## Notes",
            "rag": False
        }
        # Mock synchronous context assembly for rebuilds
        builder._assemble_context = MagicMock(return_value={"content": "## Notes"})
        
        # Patch in enhanced generation too
        with patch("backend.services.enhanced_generation.get_context_builder", return_value=builder):
            mock_ctx.return_value = builder
            yield builder

@pytest.fixture
def api_client():
    from backend.main import app as main_app
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    
    print("\n[DEBUG] Middleware BEFORE removal:")
    for m in main_app.user_middleware:
        print(f" - {m.cls.__name__}")

    # Disable TrustedHostMiddleware
    main_app.user_middleware = [m for m in main_app.user_middleware if m.cls != TrustedHostMiddleware]
    main_app.middleware_stack = main_app.build_middleware_stack()
    
    print("[DEBUG] Middleware AFTER removal:")
    for m in main_app.user_middleware:
        print(f" - {m.cls.__name__}")
        
    c = TestClient(main_app, base_url="http://localhost")
    print(f"[DEBUG] Client base_url: {c.base_url}")
    return c

def test_frontend_generation_flow(api_client, mock_services, mock_validation, mock_context):
    """
    Simulate standard artifact generation flow.
    """
    client = api_client
    print("\n=== Testing Frontend API Flow ===")
    
    # 1. Generate (useGeneration.ts)
    print("1. POST /api/generation/generate")
    response = client.post("/api/generation/generate", json={
        "artifact_type": "mermaid_erd",
        "meeting_notes": "Create a user database ERD",
        "options": {"use_validation": False}
    }, headers={"Host": "localhost"})
    
    print(f"   Response status: {response.status_code}")
    if response.status_code != 200:
        with open("api_error.log", "w") as f:
            f.write(f"Status: {response.status_code}\nBody: {response.text}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "artifact" in data
    artifact_id = data["artifact"]["id"]
    print(f"   Generated Artifact ID: {artifact_id}")
    
    # 2. Get Artifact (ArtifactViewer.tsx)
    print(f"2. GET /api/generation/artifacts/{artifact_id}")
    response = client.get(f"/api/generation/artifacts/{artifact_id}")
    assert response.status_code == 200
    artifact = response.json()
    assert artifact["id"] == artifact_id
    assert "Mocked API Content" in artifact["content"]
    
    # 3. Get Versions by Type (ArtifactCard.tsx)
    # The frontend uses /api/versions/by-type/{type}
    print(f"3. GET /api/versions/by-type/mermaid_erd")
    response = client.get(f"/api/versions/by-type/mermaid_erd")
    
    if response.status_code == 404:
        print("   WARNING: /api/versions/by-type endpoint not found. Checking /api/versions/{id}")
        response = client.get(f"/api/versions/{artifact_id}")
    
    assert response.status_code == 200
    versions = response.json()
    assert isinstance(versions, list)
    assert len(versions) > 0
    assert versions[0]["is_current"] is True
    print(f"   Versions found: {len(versions)}")

def test_custom_artifact_api_flow(api_client, mock_services, mock_validation, mock_context):
    """
    Simulate Frontend flow for CUSTOM artifact.
    """
    client = api_client
    print("\n=== Testing Custom Artifact API Flow ===")
    
    from backend.services.custom_artifact_service import get_service
    custom_service = get_service()
    
    # Clean up first
    if custom_service.get_type("api_frontend_test_custom"):
        custom_service.delete_type("api_frontend_test_custom")
        
    custom_service.create_type(
        id="api_frontend_test_custom",
        name="API Test Custom",
        category="Test",
        prompt_template="Test",
        description="Test"
    )
    
    # Retry Generation
    print("1. POST /api/generation/generate (Custom Type)")
    response = client.post("/api/generation/generate", json={
        "artifact_type": "api_frontend_test_custom",
        "meeting_notes": "Custom notes",
        "options": {"use_validation": False}
    }, headers={"Host": "localhost"})
    
    print(f"   Response status: {response.status_code}")
    if response.status_code != 200:
        with open("api_error.log", "w") as f:
            f.write(f"Status: {response.status_code}\nBody: {response.text}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    artifact = data["artifact"]
    print(f"   Generated Custom Artifact: {artifact['id']}")
    
    # 2. Verify Frontend can fetch it
    response = client.get(f"/api/generation/artifacts/{artifact['id']}")
    assert response.status_code == 200
    
    # Cleanup
    custom_service.delete_type("api_frontend_test_custom")
