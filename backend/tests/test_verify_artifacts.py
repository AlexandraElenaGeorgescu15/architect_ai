"""
Verification script for Artifact Logic.
Tests standard and custom artifact lifecycles including:
- Creation/Generation
- Reading
- Updating
- Deletion (for custom types)
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.dto import ArtifactType
from backend.services.generation_service import get_service as get_generation_service
from backend.services.custom_artifact_service import get_service as get_custom_artifact_service
from backend.services.version_service import get_version_service
from backend.services.context_builder import ContextBuilder
import backend.services.generation_service
import backend.services.enhanced_generation
import backend.services.validation_service

# Mock user for testing
MOCK_USER = MagicMock()
MOCK_USER.username = "test_user"

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before each test to ensure mocks are picked up."""
    backend.services.generation_service._service = None
    backend.services.enhanced_generation._enhanced_service = None
    backend.services.validation_service._service = None
    yield
    # Cleanup
    backend.services.generation_service._service = None
    backend.services.enhanced_generation._enhanced_service = None
    backend.services.validation_service._service = None

@pytest.fixture
def mock_ollama():
    """Mock the Ollama client to avoid actual model calls."""
    with patch("backend.services.enhanced_generation.OllamaClient") as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        
        # Mock ensure_model_available
        mock_instance.ensure_model_available = AsyncMock(return_value=True)
        
        # Mock generate
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = "Mocked Artifact Content\nGraph TD;\nA-->B;"
        mock_response.model_used = "mock-model"
        mock_response.generation_time = 0.5
        mock_response.tokens_generated = 50
        
        mock_instance.generate = AsyncMock(return_value=mock_response)
        
        # Mock generate_stream
        async def mock_stream(*args, **kwargs):
            yield "Mocked "
            yield "Content"
        
        mock_instance.generate_stream = mock_stream
        
        # Mock persistent attributes
        mock_instance.persistent_models = []
        mock_instance.unload_model = AsyncMock()

        yield mock_instance

@pytest.fixture
def mock_validation_service():
    """Mock validation service to always pass."""
    with patch("backend.services.enhanced_generation.get_validation_service") as mock_get_val_service:
        mock_validator = AsyncMock()
        
        # Mock validate_artifact
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.score = 90.0
        mock_result.errors = []
        
        mock_validator.validate_artifact.return_value = mock_result
        
        # Mock _extract_mermaid_diagram (used in generation service)
        mock_validator._extract_mermaid_diagram.side_effect = lambda x: x
        
        mock_get_val_service.return_value = mock_validator
        yield mock_validator

@pytest.fixture
def mock_context_builder():
    """Mock context builder to return simple context."""
    with patch("backend.services.generation_service.get_context_builder") as mock_get_builder:
        mock_builder = AsyncMock()
        
        long_context = "## Requirements\n" + "Test Requirements " * 10
        mock_builder.build_context.return_value = {
            "meeting_notes": "Test Requirements",
            "assembled_context": long_context,
            "rag": True
        }
        mock_builder.get_context_by_id.return_value = {
            "meeting_notes": "Test Requirements",
            "assembled_context": long_context
        }
        
        # Mock synchronous _assemble_context
        mock_builder._assemble_context = MagicMock(return_value={"content": long_context})
        
        # Also patch it in enhanced_generation
        with patch("backend.services.enhanced_generation.get_context_builder", return_value=mock_builder):
            mock_get_builder.return_value = mock_builder
            yield mock_builder

@pytest.mark.asyncio
async def test_standard_artifact_lifecycle(mock_ollama, mock_validation_service, mock_context_builder):
    """
    Test lifecycle of a standard artifact (Mermaid ERD).
    1. Generate (Create)
    2. Read (Verify creation)
    3. Update
    4. Read (Verify update)
    """
    print("\n\n=== Testing Standard Artifact Lifecycle ===")
    
    gen_service = get_generation_service()
    version_service = get_version_service()
    
    # 1. Generate
    print("1. Generating artifact...")
    meeting_notes = "Create a login system ERD"
    artifact_type = ArtifactType.MERMAID_ERD
    
    result = None
    async for update in gen_service.generate_artifact(
        artifact_type=artifact_type,
        meeting_notes=meeting_notes,
        stream=False
    ):
        result = update
        if update.get("status") == "failed":
            print(f"Generation failed: {update.get('error')}")
    
    if not result or "artifact" not in result:
        print(f"Final Result: {result}")
        
    assert result is not None
    assert result["status"] == "completed"
    assert "artifact" in result
    
    artifact = result["artifact"]
    artifact_id = artifact["id"]
    print(f"   Generated artifact ID: {artifact_id}")
    
    assert artifact_id == artifact_type.value
    assert "Mocked Artifact Content" in artifact["content"]
    
    # 2. Read (Verify creation in VersionService)
    print("2. Verifying persistence...")
    versions = version_service.get_versions(artifact_id)
    assert len(versions) > 0
    latest = version_service.get_current_version(artifact_id)
    assert latest["artifact_type"] == artifact_type.value
    assert "Mocked Artifact Content" in latest["content"]
    print("   Artifact persisted successfully.")
    
    # 3. Update
    print("3. Updating artifact...")
    new_content = "flowchart TD;\nLogin-->Success;"
    updated = gen_service.update_artifact(
        artifact_id=artifact_id,
        content=new_content,
        metadata={"updated_by": "test_user"}
    )
    
    assert updated is not None
    assert updated["content"] == new_content
    
    # 4. Read (Verify update)
    print("4. Verifying update...")
    latest_after_update = version_service.get_current_version(artifact_id)
    assert latest_after_update["content"] == new_content
    # Check version increment
    assert len(version_service.get_versions(artifact_id)) >= 2
    print("   Artifact updated successfully.")

@pytest.mark.asyncio
async def test_custom_artifact_lifecycle(mock_ollama, mock_validation_service, mock_context_builder):
    """
    Test lifecycle of a custom artifact.
    1. Create Custom Type
    2. Generate Artifact of that Type
    3. Read
    4. Update
    5. Delete Type
    """
    print("\n\n=== Testing Custom Artifact Lifecycle ===")
    
    custom_service = get_custom_artifact_service()
    gen_service = get_generation_service()
    version_service = get_version_service()
    
    custom_type_id = "test_custom_report"
    
    # Clean up if exists
    if custom_service.get_type(custom_type_id):
        custom_service.delete_type(custom_type_id)
    
    # 1. Create Custom Type
    print(f"1. Creating custom artifact type: {custom_type_id}")
    custom_type = custom_service.create_type(
        id=custom_type_id,
        name="Test Custom Report",
        category="Testing",
        prompt_template="Generate a report for: {{meeting_notes}}",
        description="A test report type"
    )
    
    assert custom_type is not None
    assert custom_type.id == custom_type_id
    
    # Verify it exists in list
    types = custom_service.list_types()
    assert any(t.id == custom_type_id for t in types)
    print("   Custom type created.")
    
    # 2. Generate Artifact
    print("2. Generating custom artifact...")
    meeting_notes = "Report requirements"
    
    result = None
    # Pass string ID for custom type
    async for update in gen_service.generate_artifact(
        artifact_type=custom_type_id,
        meeting_notes=meeting_notes,
        stream=False
    ):
        result = update
        
    assert result is not None
    assert result["status"] == "completed"
    artifact = result["artifact"]
    
    # For generated custom artifacts, the ID is typically the type ID in the current implementation
    # unless folder-scoped
    artifact_id = artifact["id"]
    print(f"   Generated custom artifact ID: {artifact_id}")
    
    assert artifact["artifact_type"] == custom_type_id
    assert "Mocked Artifact Content" in artifact["content"]
    
    # 3. Read & Verify Persistence
    print("3. Verifying persistence...")
    versions = version_service.get_versions(artifact_id)
    assert len(versions) > 0
    latest = version_service.get_current_version(artifact_id)
    assert latest["artifact_type"] == custom_type_id
    print("   Custom artifact persisted.")
    
    # 4. Update
    print("4. Updating custom artifact...")
    new_content = "Updated Report Content"
    updated = gen_service.update_artifact(
        artifact_id=artifact_id,
        content=new_content
    )
    
    assert updated is not None
    assert updated["content"] == new_content
    
    latest_update = version_service.get_current_version(artifact_id)
    assert latest_update["content"] == new_content
    print("   Custom artifact updated.")
    
    # 5. Cleanup (Delete Type)
    print("5. Cleaning up (Deleting type)...")
    deleted = custom_service.delete_type(custom_type_id)
    assert deleted is True
    assert custom_service.get_type(custom_type_id) is None
    print("   Custom type deleted.")
