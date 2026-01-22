"""
Simple API Endpoint Tests with Mock Data

Tests major API endpoints in the Architect.AI backend.
Run with: python tests/test_api_simple.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"


# ============================================================================
# Mock Data
# ============================================================================

MOCK_MEETING_NOTES = """
# Project Requirements Meeting - E-Commerce Platform

## Requirements
1. User Authentication System
   - OAuth2 integration with Google and GitHub
   - JWT-based session management

2. Product Catalog
   - Categories with hierarchical structure
   - Product variants (size, color)

3. Shopping Cart
   - Persistent cart for logged-in users
   - Apply discount codes

## Technical Decisions
- Backend: FastAPI with Python 3.11
- Database: PostgreSQL with SQLAlchemy
- Frontend: React with TypeScript
"""

MOCK_ARTIFACT_ERD = """erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id PK
        string email UK
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        int id PK
        int user_id FK
    }
"""


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def record_pass(self, test_name):
        self.passed += 1
        print(f"  ✅ {test_name}")
    
    def record_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, str(error)))
        print(f"  ❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed}/{total} tests passed")
        if self.errors:
            print("\nFailed tests:")
            for name, err in self.errors:
                print(f"  - {name}: {err}")
        print("="*60)
        return self.failed == 0


def run_sync_tests():
    """Run synchronous endpoint tests."""
    results = TestResults()
    
    print("\n" + "="*60)
    print("ARCHITECT.AI API ENDPOINT TESTS")
    print("="*60)
    
    # Test 1: Import FastAPI app
    print("\n[1] Testing FastAPI app import...")
    try:
        from backend.main import app
        results.record_pass("FastAPI app imports correctly")
    except Exception as e:
        results.record_fail("FastAPI app import", e)
        return results
    
    # Test 2: Test health endpoint structure
    print("\n[2] Testing health endpoint...")
    try:
        # Import the endpoint directly
        from backend.main import health_check
        import asyncio
        
        # Run async function
        result = asyncio.get_event_loop().run_until_complete(health_check())
        
        assert "status" in result, "Missing 'status' in health response"
        assert "version" in result, "Missing 'version' in health response"
        results.record_pass("Health endpoint returns expected fields")
    except Exception as e:
        results.record_fail("Health endpoint", e)
    
    # Test 3: Test DTO models
    print("\n[3] Testing DTO models...")
    try:
        from backend.models.dto import (
            ArtifactType,
            GenerationStatus,
            ContextRequest,
            FeedbackRequest,
            ChatRequest
        )
        
        # Test ArtifactType enum
        assert ArtifactType.MERMAID_ERD.value == "mermaid_erd"
        
        # Test GenerationStatus enum
        assert GenerationStatus.COMPLETED.value == "completed"
        
        # Test FeedbackRequest model
        feedback = FeedbackRequest(
            artifact_id="test-123",
            score=85.0,
            feedback_type="positive"
        )
        assert feedback.artifact_id == "test-123"
        
        # Test ChatRequest model
        chat = ChatRequest(
            message="Hello AI",
            conversation_history=[],
            include_project_context=True
        )
        assert chat.message == "Hello AI"
        
        results.record_pass("All DTO models work correctly")
    except Exception as e:
        results.record_fail("DTO models", e)
    
    # Test 4: Test service imports
    print("\n[4] Testing service imports...")
    try:
        from backend.services.generation_service import get_service as get_gen_service
        from backend.services.model_service import get_service as get_model_service
        from backend.services.context_builder import get_builder
        from backend.services.feedback_service import get_service as get_feedback_service
        from backend.services.chat_service import get_chat_service
        
        results.record_pass("All services import correctly")
    except Exception as e:
        results.record_fail("Service imports", e)
    
    # Test 5: Test API router imports
    print("\n[5] Testing API router imports...")
    try:
        from backend.api import (
            auth,
            generation,
            models,
            context,
            rag,
            feedback,
            chat,
            meeting_notes,
            knowledge_graph,
            pattern_mining,
            validation
        )
        
        # Check routers exist
        assert hasattr(auth, 'router')
        assert hasattr(generation, 'router')
        assert hasattr(models, 'router')
        
        results.record_pass("All API routers import correctly")
    except Exception as e:
        results.record_fail("API router imports", e)
    
    # Test 6: Test model DTOs
    print("\n[6] Testing model DTOs...")
    try:
        from backend.models.dto import (
            ModelInfoDTO,
            ModelRoutingDTO,
            GenerationRequest,
            GenerationResponse,
            GenerationOptions
        )
        
        # Test GenerationOptions defaults
        opts = GenerationOptions()
        assert opts.max_retries == 3
        assert opts.use_validation == True
        
        # Test GenerationRequest
        req = GenerationRequest(
            artifact_type=ArtifactType.MERMAID_ERD,
            meeting_notes=MOCK_MEETING_NOTES
        )
        assert req.artifact_type == ArtifactType.MERMAID_ERD
        
        results.record_pass("Model DTOs work correctly")
    except Exception as e:
        results.record_fail("Model DTOs", e)
    
    # Test 7: Test validation service
    print("\n[7] Testing validation service...")
    try:
        from backend.services.validation_service import get_service as get_val_service
        from backend.models.dto import ArtifactType
        import asyncio
        
        val_service = get_val_service()
        
        # Test Mermaid ERD validation (async method with enum type)
        async def run_validation():
            return await val_service.validate_artifact(
                content=MOCK_ARTIFACT_ERD,
                artifact_type=ArtifactType.MERMAID_ERD
            )
        
        result = asyncio.get_event_loop().run_until_complete(run_validation())
        
        # Result could be a dict or an object
        if isinstance(result, dict):
            assert "is_valid" in result, "Missing validation result"
        else:
            assert hasattr(result, "is_valid"), "Missing validation result"
        results.record_pass("Validation service works correctly")
    except Exception as e:
        results.record_fail("Validation service", e)
    
    # Test 8: Test auth helpers
    print("\n[8] Testing auth helpers...")
    try:
        from backend.core.auth import create_access_token, generate_api_key
        
        # Test token creation
        token = create_access_token(data={"sub": "test_user"})
        assert token is not None
        assert len(token) > 20
        
        # Test API key generation
        api_key = generate_api_key()
        assert api_key is not None
        assert len(api_key) > 20
        
        results.record_pass("Auth helpers work correctly")
    except Exception as e:
        results.record_fail("Auth helpers", e)
    
    # Test 9: Test config settings
    print("\n[9] Testing config settings...")
    try:
        from backend.core.config import settings
        
        assert settings.app_name == "Architect.AI API"
        assert hasattr(settings, 'app_version')
        assert hasattr(settings, 'cors_origins')
        
        results.record_pass("Config settings accessible")
    except Exception as e:
        results.record_fail("Config settings", e)
    
    # Test 10: Test RAG services
    print("\n[10] Testing RAG services...")
    try:
        from backend.services.rag_retriever import get_retriever
        from backend.services.rag_cache import get_cache
        
        retriever = get_retriever()
        cache = get_cache()
        
        # Check methods exist
        assert hasattr(retriever, 'hybrid_search')
        assert hasattr(cache, 'get_context')
        
        results.record_pass("RAG services accessible")
    except Exception as e:
        results.record_fail("RAG services", e)
    
    # Test 11: Test Knowledge Graph
    print("\n[11] Testing Knowledge Graph service...")
    try:
        from backend.services.knowledge_graph import get_builder as get_kg_builder
        
        kg_builder = get_kg_builder()
        stats = kg_builder.get_stats()
        
        assert stats is not None
        results.record_pass("Knowledge Graph service works")
    except Exception as e:
        results.record_fail("Knowledge Graph service", e)
    
    # Test 12: Test Pattern Mining
    print("\n[12] Testing Pattern Mining service...")
    try:
        from backend.services.pattern_mining import get_miner
        
        miner = get_miner()
        assert hasattr(miner, 'analyze_project')
        
        results.record_pass("Pattern Mining service accessible")
    except Exception as e:
        results.record_fail("Pattern Mining service", e)
    
    # Test 13: Test Meeting Notes service
    print("\n[13] Testing Meeting Notes service...")
    try:
        from backend.services.meeting_notes_service import get_service as get_notes_service
        
        notes_service = get_notes_service()
        assert hasattr(notes_service, 'suggest_folder')
        
        results.record_pass("Meeting Notes service accessible")
    except Exception as e:
        results.record_fail("Meeting Notes service", e)
    
    # Test 14: Test Context Builder
    print("\n[14] Testing Context Builder...")
    try:
        from backend.services.context_builder import get_builder
        
        builder = get_builder()
        assert hasattr(builder, 'build_context')
        
        results.record_pass("Context Builder accessible")
    except Exception as e:
        results.record_fail("Context Builder", e)
    
    # Test 15: Test Universal Context
    print("\n[15] Testing Universal Context service...")
    try:
        from backend.services.universal_context import get_universal_context_service
        
        uc_service = get_universal_context_service()
        assert hasattr(uc_service, 'build_universal_context')
        
        results.record_pass("Universal Context service accessible")
    except Exception as e:
        results.record_fail("Universal Context service", e)
    
    return results


def run_async_tests():
    """Run async endpoint tests."""
    import asyncio
    results = TestResults()
    
    print("\n" + "="*60)
    print("ASYNC API TESTS")
    print("="*60)
    
    async def run_all_async():
        # Test async context build
        print("\n[A1] Testing async context build...")
        try:
            from backend.services.context_builder import get_builder
            
            builder = get_builder()
            context = await builder.build_context(
                meeting_notes=MOCK_MEETING_NOTES,
                include_rag=False,  # Skip RAG for quick test
                include_kg=False,
                include_patterns=False
            )
            
            assert "assembled_context" in context
            results.record_pass("Async context build works")
        except Exception as e:
            results.record_fail("Async context build", e)
        
        # Test async model list
        print("\n[A2] Testing async model list...")
        try:
            from backend.services.model_service import get_service as get_model_service
            
            service = get_model_service()
            models = await service.list_models()
            
            assert isinstance(models, list)
            results.record_pass("Async model list works")
        except Exception as e:
            results.record_fail("Async model list", e)
        
        # Test chat service
        print("\n[A3] Testing chat service (structure only)...")
        try:
            from backend.services.chat_service import get_chat_service
            
            service = get_chat_service()
            assert hasattr(service, 'chat')
            results.record_pass("Chat service accessible")
        except Exception as e:
            results.record_fail("Chat service", e)
    
    # Run async tests
    asyncio.get_event_loop().run_until_complete(run_all_async())
    
    return results


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print(" ARCHITECT.AI API ENDPOINT TESTS WITH MOCK DATA ")
    print("="*70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    
    # Run synchronous tests
    sync_results = run_sync_tests()
    
    # Run async tests
    async_results = run_async_tests()
    
    # Final summary
    total_passed = sync_results.passed + async_results.passed
    total_failed = sync_results.failed + async_results.failed
    total = total_passed + total_failed
    
    print("\n" + "="*70)
    print(" FINAL SUMMARY ")
    print("="*70)
    print(f"\nTotal tests: {total}")
    print(f"✅ Passed: {total_passed}")
    print(f"❌ Failed: {total_failed}")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total_failed} test(s) failed")
        all_errors = sync_results.errors + async_results.errors
        print("\nFailed tests:")
        for name, err in all_errors:
            print(f"  - {name}: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
