import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.main import app
from backend.models.dto import ArtifactType

# Client for testing API
client = TestClient(app, base_url="http://localhost")

@pytest.fixture
def mock_generation_service():
    """Mock the generation service to return predictable AI responses."""
    with patch("backend.api.ai.get_generation_service") as mock_get:
        service = AsyncMock()
        mock_get.return_value = service
        yield service

@pytest.fixture
def mock_version_service():
    """Mock the version service."""
    with patch("backend.api.versions.get_version_service") as mock_get:
        service = AsyncMock()
        mock_get.return_value = service
        yield service

@pytest.fixture
def auth_bypass():
    """Bypass authentication."""
    async def mock_get_current_user():
        return {"id": "test_user", "email": "test@example.com"}
    
    app.dependency_overrides["backend.core.auth.get_current_user"] = mock_get_current_user
    yield
    app.dependency_overrides = {}

def test_repair_diagram_rule_based(mock_generation_service, auth_bypass):
    """Test repair-diagram with a simple error that rule-based fixer handles."""
    # Input with a common error (missing brackets for node)
    # The UniversalDiagramFixer should fix this without AI
    broken_code = """
    graph TD
    A[Start] --> B(End
    """
    
    response = client.post("/api/ai/repair-diagram", json={
        "mermaid_code": broken_code,
        "diagram_type": "mermaid_flowchart",
        "error_message": "Parse error"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Rule based fixer should close the parenthesis
    assert "B(End)" in data["improved_code"]
    assert "Rule-based" in str(data["improvements_made"])

def test_repair_diagram_ai_fallback(mock_generation_service, auth_bypass):
    """Test repair-diagram falling back to AI when rule-based fails."""
    broken_code = "graph TD\n This is complete gibberish"
    
    # Mock AI response
    mock_generation_service.generate_with_fallback.return_value.success = True
    mock_generation_service.generate_with_fallback.return_value.content = "graph TD\n A[Start] --> B[End]"
    
    response = client.post("/api/ai/repair-diagram", json={
        "mermaid_code": broken_code,
        "diagram_type": "mermaid_flowchart",
        "error_message": "Syntax error"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "graph TD" in data["improved_code"]
    # Should show AI involvement in improvements log
    assert any("AI" in imp for imp in data["improvements_made"])

def test_improve_diagram(mock_generation_service, auth_bypass):
    """Test improve-diagram endpoint."""
    input_code = "graph TD\nA-->B"
    
    # Mock AI response with improved code (styles added)
    mock_generation_service.generate_with_fallback.return_value.success = True
    mock_generation_service.generate_with_fallback.return_value.content = """
    graph TD
    classDef default fill:#f9f,stroke:#333,stroke-width:2px;
    A[Start] --> B[End]
    """
    
    response = client.post("/api/ai/improve-diagram", json={
        "mermaid_code": input_code,
        "diagram_type": "mermaid_flowchart",
        "improvement_focus": ["styles", "labels"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "classDef" in data["improved_code"]

def test_create_version(mock_version_service, auth_bypass):
    """Test creating a new version."""
    mock_version_service.create_version.return_value = {
        "version": 2,
        "artifact_id": "test_artifact",
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    response = client.post("/api/versions/create", json={
        "artifact_id": "test_artifact",
        "artifact_type": "mermaid_flowchart",
        "content": "graph TD\nA-->B",
        "metadata": {"source": "test"}
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == 2
    mock_version_service.create_version.assert_called_once()
