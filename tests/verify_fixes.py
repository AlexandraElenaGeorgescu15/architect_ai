import sys
from pathlib import Path
import os
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    print("Testing imports...")
    try:
        from backend.services.meeting_notes_service import get_meeting_notes_service
        print("✅ meeting_notes_service.get_meeting_notes_service imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import get_meeting_notes_service: {e}")

    try:
        from ai.ollama_client import get_client
        print("✅ ollama_client.get_client imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import get_client: {e}")
        
    try:
        from backend.services.llm_judge import LLMJudge
        import asyncio
        print("✅ llm_judge imported successfully (asyncio check)")
    except Exception as e:
        print(f"❌ Failed to import llm_judge: {e}")

def test_filename_sanitization():
    print("\nTesting filename sanitization...")
    from backend.services.version_service import VersionService
    
    # Mock settings
    class MockSettings:
        base_path = str(project_root)
    
    import backend.services.version_service as vs
    vs.settings = MockSettings()
    
    service = VersionService()
    
    # Test creating version with colon
    artifact_id = "test:artifact:with:colons"
    try:
        service.create_version(
            artifact_id=artifact_id,
            artifact_type="test",
            content="test content"
        )
        
        # Check if file exists with underscores
        sanitized_id = artifact_id.replace(":", "_")
        expected_file = service.versions_dir / f"{sanitized_id}.json"
        
        if expected_file.exists():
            print(f"✅ Version file created with sanitized name: {expected_file.name}")
            # Cleanup
            expected_file.unlink()
            print("   (Cleaned up test file)")
        else:
            print(f"❌ Version file NOT found at expected path: {expected_file}")
            
    except OSError as e:
        if "Invalid argument" in str(e):
             print(f"❌ Failed: OSError raised - sanitization didn't work. {e}")
        else:
             print(f"❌ Failed with OSError: {e}")
    except Exception as e:
        print(f"❌ Failed with unexpected error: {e}")

if __name__ == "__main__":
    print("=== VERIFYING FIXES ===")
    test_imports()
    test_filename_sanitization()
    print("\n=== DONE ===")
