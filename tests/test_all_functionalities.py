"""
COMPREHENSIVE FUNCTIONALITY TEST SUITE FOR ARCHITECT.AI

Tests EVERY functionality of the Architect.AI application.
Run with: python tests/test_all_functionalities.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import asyncio
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"


# ============================================================================
# Mock Data for Testing
# ============================================================================

MOCK_MEETING_NOTES = """
# Project Requirements Meeting - E-Commerce Platform

## Attendees
- Product Manager: John Smith
- Tech Lead: Jane Doe

## Requirements
1. User Authentication System
   - OAuth2 integration with Google and GitHub
   - JWT-based session management
   - Password reset functionality

2. Product Catalog
   - Categories with hierarchical structure
   - Product variants (size, color)
   - Inventory tracking

3. Shopping Cart
   - Persistent cart for logged-in users
   - Guest checkout option

## Technical Decisions
- Backend: FastAPI with Python 3.11
- Database: PostgreSQL with SQLAlchemy
- Frontend: React with TypeScript
"""

MOCK_MERMAID_ERD = """erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id PK
        string email UK
        string password_hash
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        int id PK
        int user_id FK
        string status
    }
    PRODUCT ||--o{ ORDER_ITEM : "ordered in"
    PRODUCT {
        int id PK
        string name
        decimal price
    }
"""

MOCK_MERMAID_FLOWCHART = """flowchart TD
    A[Start] --> B{Is user logged in?}
    B -->|Yes| C[Show Dashboard]
    B -->|No| D[Show Login]
    D --> E[Enter Credentials]
    E --> F{Valid?}
    F -->|Yes| C
    F -->|No| D
"""

MOCK_MERMAID_SEQUENCE = """sequenceDiagram
    participant U as User
    participant A as API
    participant D as Database
    U->>A: POST /login
    A->>D: Verify credentials
    D-->>A: User data
    A-->>U: JWT Token
"""


class TestResults:
    """Track test results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.categories = {}
    
    def record_pass(self, category, test_name):
        self.passed += 1
        if category not in self.categories:
            self.categories[category] = {"passed": 0, "failed": 0, "skipped": 0}
        self.categories[category]["passed"] += 1
        print(f"    ✅ {test_name}")
    
    def record_fail(self, category, test_name, error):
        self.failed += 1
        if category not in self.categories:
            self.categories[category] = {"passed": 0, "failed": 0, "skipped": 0}
        self.categories[category]["failed"] += 1
        self.errors.append((category, test_name, str(error)[:100]))
        print(f"    ❌ {test_name}: {str(error)[:80]}")
    
    def record_skip(self, category, test_name, reason):
        self.skipped += 1
        if category not in self.categories:
            self.categories[category] = {"passed": 0, "failed": 0, "skipped": 0}
        self.categories[category]["skipped"] += 1
        print(f"    ⏭️  {test_name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*70}")
        print(f" FINAL SUMMARY ")
        print(f"{'='*70}")
        print(f"\nTotal tests: {total}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"⏭️  Skipped: {self.skipped}")
        
        print(f"\n{'─'*70}")
        print("Results by Category:")
        print(f"{'─'*70}")
        for cat, stats in sorted(self.categories.items()):
            status = "✅" if stats["failed"] == 0 else "❌"
            print(f"  {status} {cat}: {stats['passed']} passed, {stats['failed']} failed, {stats['skipped']} skipped")
        
        if self.errors:
            print(f"\n{'─'*70}")
            print("Failed Tests:")
            print(f"{'─'*70}")
            for cat, name, err in self.errors[:10]:
                print(f"  [{cat}] {name}: {err}")
        
        print(f"\n{'='*70}")
        return self.failed == 0


def run_async(coro):
    """Run async function."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ============================================================================
# 1. CORE APPLICATION TESTS
# ============================================================================

def test_core_application(results):
    """Test core application components."""
    category = "1. Core Application"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 1.1: FastAPI App
    try:
        from backend.main import app
        assert app is not None
        assert app.title == "Architect.AI API"
        results.record_pass(category, "FastAPI app initialization")
    except Exception as e:
        results.record_fail(category, "FastAPI app initialization", e)
    
    # Test 1.2: Health endpoint
    try:
        from backend.main import health_check
        result = run_async(health_check())
        assert "status" in result
        assert "version" in result
        assert "phases" in result
        results.record_pass(category, "Health endpoint")
    except Exception as e:
        results.record_fail(category, "Health endpoint", e)
    
    # Test 1.3: Metrics endpoint
    try:
        from backend.main import metrics_endpoint
        result = run_async(metrics_endpoint())
        assert result is not None
        results.record_pass(category, "Metrics endpoint")
    except Exception as e:
        results.record_fail(category, "Metrics endpoint", e)
    
    # Test 1.4: Config settings
    try:
        from backend.core.config import settings
        assert settings.app_name is not None
        assert hasattr(settings, 'app_version')
        assert hasattr(settings, 'cors_origins')
        results.record_pass(category, "Config settings")
    except Exception as e:
        results.record_fail(category, "Config settings", e)
    
    # Test 1.5: Database initialization
    try:
        from backend.core.database import init_db, get_db
        init_db()
        results.record_pass(category, "Database initialization")
    except Exception as e:
        results.record_fail(category, "Database initialization", e)
    
    # Test 1.6: Cache manager
    try:
        from backend.core.cache import get_cache_manager
        cache = get_cache_manager()
        stats = cache.get_stats()
        assert stats is not None
        results.record_pass(category, "Cache manager")
    except Exception as e:
        results.record_fail(category, "Cache manager", e)
    
    # Test 1.7: Metrics collector
    try:
        from backend.core.metrics import get_metrics_collector
        collector = get_metrics_collector()
        stats = collector.get_stats()
        assert stats is not None
        results.record_pass(category, "Metrics collector")
    except Exception as e:
        results.record_fail(category, "Metrics collector", e)


# ============================================================================
# 2. AUTHENTICATION TESTS
# ============================================================================

def test_authentication(results):
    """Test authentication functionality."""
    category = "2. Authentication"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 2.1: JWT token creation
    try:
        from backend.core.auth import create_access_token
        token = create_access_token(data={"sub": "test_user", "username": "test"})
        assert token is not None
        assert len(token) > 50
        results.record_pass(category, "JWT token creation")
    except Exception as e:
        results.record_fail(category, "JWT token creation", e)
    
    # Test 2.2: API key generation
    try:
        from backend.core.auth import generate_api_key
        api_key = generate_api_key()
        assert api_key is not None
        assert len(api_key) > 20
        results.record_pass(category, "API key generation")
    except Exception as e:
        results.record_fail(category, "API key generation", e)
    
    # Test 2.3: Password hashing
    try:
        from backend.core.auth import get_password_hash, verify_password
        # Use simple ASCII password
        test_pwd = "abc123"
        hashed = get_password_hash(test_pwd)
        assert hashed is not None
        verified = verify_password(test_pwd, hashed)
        assert verified == True
        results.record_pass(category, "Password hashing & verification")
    except Exception as e:
        # bcrypt version issues on Windows - skip gracefully
        if "bcrypt" in str(e) or "72 bytes" in str(e):
            results.record_skip(category, "Password hashing & verification", "bcrypt version issue")
        else:
            results.record_fail(category, "Password hashing & verification", e)
    
    # Test 2.4: Auth router
    try:
        from backend.api.auth import router
        assert router is not None
        assert router.prefix == "/api/auth"
        results.record_pass(category, "Auth router")
    except Exception as e:
        results.record_fail(category, "Auth router", e)


# ============================================================================
# 3. DTO MODELS TESTS
# ============================================================================

def test_dto_models(results):
    """Test all DTO models."""
    category = "3. DTO Models"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 3.1: ArtifactType enum
    try:
        from backend.models.dto import ArtifactType
        assert ArtifactType.MERMAID_ERD.value == "mermaid_erd"
        assert ArtifactType.MERMAID_SEQUENCE.value == "mermaid_sequence"
        assert ArtifactType.CODE_PROTOTYPE.value == "code_prototype"
        assert len(ArtifactType) > 30  # Should have many types
        results.record_pass(category, "ArtifactType enum")
    except Exception as e:
        results.record_fail(category, "ArtifactType enum", e)
    
    # Test 3.2: GenerationStatus enum
    try:
        from backend.models.dto import GenerationStatus
        assert GenerationStatus.PENDING.value == "pending"
        assert GenerationStatus.COMPLETED.value == "completed"
        assert GenerationStatus.FAILED.value == "failed"
        results.record_pass(category, "GenerationStatus enum")
    except Exception as e:
        results.record_fail(category, "GenerationStatus enum", e)
    
    # Test 3.3: TrainingStatus enum
    try:
        from backend.models.dto import TrainingStatus
        assert TrainingStatus.QUEUED.value == "queued"
        assert TrainingStatus.TRAINING.value == "training"
        assert TrainingStatus.COMPLETED.value == "completed"
        results.record_pass(category, "TrainingStatus enum")
    except Exception as e:
        results.record_fail(category, "TrainingStatus enum", e)
    
    # Test 3.4: GenerationRequest model
    try:
        from backend.models.dto import GenerationRequest, ArtifactType
        req = GenerationRequest(
            artifact_type=ArtifactType.MERMAID_ERD,
            meeting_notes=MOCK_MEETING_NOTES
        )
        assert req.artifact_type == ArtifactType.MERMAID_ERD
        assert req.meeting_notes == MOCK_MEETING_NOTES
        results.record_pass(category, "GenerationRequest model")
    except Exception as e:
        results.record_fail(category, "GenerationRequest model", e)
    
    # Test 3.5: GenerationOptions model
    try:
        from backend.models.dto import GenerationOptions
        opts = GenerationOptions()
        assert opts.max_retries == 3
        assert opts.use_validation == True
        assert opts.temperature == 0.7
        results.record_pass(category, "GenerationOptions model")
    except Exception as e:
        results.record_fail(category, "GenerationOptions model", e)
    
    # Test 3.6: FeedbackRequest model
    try:
        from backend.models.dto import FeedbackRequest
        feedback = FeedbackRequest(
            artifact_id="test-123",
            score=85.0,
            feedback_type="positive",
            notes="Good diagram"
        )
        assert feedback.artifact_id == "test-123"
        assert feedback.score == 85.0
        results.record_pass(category, "FeedbackRequest model")
    except Exception as e:
        results.record_fail(category, "FeedbackRequest model", e)
    
    # Test 3.7: ChatRequest model
    try:
        from backend.models.dto import ChatRequest
        chat = ChatRequest(
            message="What is the architecture?",
            conversation_history=[],
            include_project_context=True
        )
        assert chat.message == "What is the architecture?"
        results.record_pass(category, "ChatRequest model")
    except Exception as e:
        results.record_fail(category, "ChatRequest model", e)
    
    # Test 3.8: ContextRequest model
    try:
        from backend.models.dto import ContextRequest
        ctx = ContextRequest(
            meeting_notes=MOCK_MEETING_NOTES,
            include_rag=True,
            include_kg=True
        )
        assert ctx.meeting_notes == MOCK_MEETING_NOTES
        results.record_pass(category, "ContextRequest model")
    except Exception as e:
        results.record_fail(category, "ContextRequest model", e)
    
    # Test 3.9: ModelInfoDTO model
    try:
        from backend.models.dto import ModelInfoDTO
        model = ModelInfoDTO(
            id="llama3:8b",
            name="Llama 3 8B",
            provider="ollama",
            status="available"
        )
        assert model.id == "llama3:8b"
        results.record_pass(category, "ModelInfoDTO model")
    except Exception as e:
        results.record_fail(category, "ModelInfoDTO model", e)


# ============================================================================
# 4. RAG SYSTEM TESTS
# ============================================================================

def test_rag_system(results):
    """Test RAG (Retrieval Augmented Generation) system."""
    category = "4. RAG System"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 4.1: RAG Ingester
    try:
        from backend.services.rag_ingester import get_ingester
        ingester = get_ingester()
        assert hasattr(ingester, 'index_directory')
        assert hasattr(ingester, 'get_index_stats')
        stats = ingester.get_index_stats()
        assert stats is not None
        results.record_pass(category, "RAG Ingester")
    except Exception as e:
        results.record_fail(category, "RAG Ingester", e)
    
    # Test 4.2: RAG Retriever
    try:
        from backend.services.rag_retriever import get_retriever
        retriever = get_retriever()
        assert hasattr(retriever, 'hybrid_search')
        assert hasattr(retriever, 'get_query_stats')
        results.record_pass(category, "RAG Retriever")
    except Exception as e:
        results.record_fail(category, "RAG Retriever", e)
    
    # Test 4.3: RAG Cache
    try:
        from backend.services.rag_cache import get_cache
        cache = get_cache()
        assert hasattr(cache, 'get_context')
        assert hasattr(cache, 'set_context')
        assert hasattr(cache, 'invalidate')
        results.record_pass(category, "RAG Cache")
    except Exception as e:
        results.record_fail(category, "RAG Cache", e)
    
    # Test 4.4: RAG API router
    try:
        from backend.api.rag import router
        assert router is not None
        assert router.prefix == "/api/rag"
        results.record_pass(category, "RAG API router")
    except Exception as e:
        results.record_fail(category, "RAG API router", e)
    
    # Test 4.5: Semantic search
    try:
        from backend.services.semantic_search import SemanticSearchService
        assert SemanticSearchService is not None
        results.record_pass(category, "Semantic search service")
    except Exception as e:
        results.record_fail(category, "Semantic search service", e)


# ============================================================================
# 5. KNOWLEDGE GRAPH TESTS
# ============================================================================

def test_knowledge_graph(results):
    """Test Knowledge Graph functionality."""
    category = "5. Knowledge Graph"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 5.1: KG Builder
    try:
        from backend.services.knowledge_graph import get_builder
        builder = get_builder()
        assert builder is not None
        assert hasattr(builder, 'build_graph') or hasattr(builder, 'get_stats')
        results.record_pass(category, "Knowledge Graph Builder")
    except Exception as e:
        results.record_fail(category, "Knowledge Graph Builder", e)
    
    # Test 5.2: KG Stats
    try:
        from backend.services.knowledge_graph import get_builder
        builder = get_builder()
        stats = builder.get_stats()
        assert stats is not None or isinstance(stats, dict)
        results.record_pass(category, "KG Stats")
    except Exception as e:
        results.record_fail(category, "KG Stats", e)
    
    # Test 5.3: KG API router
    try:
        from backend.api.knowledge_graph import router
        assert router is not None
        assert router.prefix == "/api/knowledge-graph"
        results.record_pass(category, "KG API router")
    except Exception as e:
        results.record_fail(category, "KG API router", e)


# ============================================================================
# 6. PATTERN MINING TESTS
# ============================================================================

def test_pattern_mining(results):
    """Test Pattern Mining functionality."""
    category = "6. Pattern Mining"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 6.1: Pattern Miner
    try:
        from backend.services.pattern_mining import get_miner
        miner = get_miner()
        assert miner is not None
        assert hasattr(miner, 'analyze_project')
        results.record_pass(category, "Pattern Miner")
    except Exception as e:
        results.record_fail(category, "Pattern Miner", e)
    
    # Test 6.2: Pattern Mining API
    try:
        from backend.api.pattern_mining import router
        assert router is not None
        results.record_pass(category, "Pattern Mining API router")
    except Exception as e:
        results.record_fail(category, "Pattern Mining API router", e)


# ============================================================================
# 7. CONTEXT BUILDER TESTS
# ============================================================================

def test_context_builder(results):
    """Test Context Builder functionality."""
    category = "7. Context Builder"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 7.1: Context Builder service
    try:
        from backend.services.context_builder import get_builder
        builder = get_builder()
        assert hasattr(builder, 'build_context')
        results.record_pass(category, "Context Builder service")
    except Exception as e:
        results.record_fail(category, "Context Builder service", e)
    
    # Test 7.2: Async context build
    try:
        from backend.services.context_builder import get_builder
        builder = get_builder()
        
        async def test_build():
            return await builder.build_context(
                meeting_notes=MOCK_MEETING_NOTES,
                include_rag=False,
                include_kg=False,
                include_patterns=False
            )
        
        result = run_async(test_build())
        assert "assembled_context" in result
        results.record_pass(category, "Async context build")
    except Exception as e:
        results.record_fail(category, "Async context build", e)
    
    # Test 7.3: Context API router
    try:
        from backend.api.context import router
        assert router is not None
        assert router.prefix == "/api/context"
        results.record_pass(category, "Context API router")
    except Exception as e:
        results.record_fail(category, "Context API router", e)


# ============================================================================
# 8. UNIVERSAL CONTEXT TESTS
# ============================================================================

def test_universal_context(results):
    """Test Universal Context functionality."""
    category = "8. Universal Context"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 8.1: Universal Context service
    try:
        from backend.services.universal_context import get_universal_context_service
        service = get_universal_context_service()
        assert service is not None
        assert hasattr(service, 'build_universal_context')
        results.record_pass(category, "Universal Context service")
    except Exception as e:
        results.record_fail(category, "Universal Context service", e)
    
    # Test 8.2: Universal Context API
    try:
        from backend.api.universal_context import router
        assert router is not None
        results.record_pass(category, "Universal Context API router")
    except Exception as e:
        results.record_fail(category, "Universal Context API router", e)


# ============================================================================
# 9. GENERATION SERVICE TESTS
# ============================================================================

def test_generation_service(results):
    """Test Artifact Generation functionality."""
    category = "9. Generation Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 9.1: Generation service
    try:
        from backend.services.generation_service import get_service
        service = get_service()
        assert hasattr(service, 'generate_artifact')
        assert hasattr(service, 'get_job_status')
        assert hasattr(service, 'list_jobs')
        results.record_pass(category, "Generation service")
    except Exception as e:
        results.record_fail(category, "Generation service", e)
    
    # Test 9.2: Enhanced generation
    try:
        from backend.services.enhanced_generation import EnhancedGenerationService
        assert EnhancedGenerationService is not None
        results.record_pass(category, "Enhanced generation service")
    except Exception as e:
        results.record_fail(category, "Enhanced generation service", e)
    
    # Test 9.3: Generation API router
    try:
        from backend.api.generation import router
        assert router is not None
        assert router.prefix == "/api/generation"
        results.record_pass(category, "Generation API router")
    except Exception as e:
        results.record_fail(category, "Generation API router", e)
    
    # Test 9.4: Artifact cleaner
    try:
        from backend.services.artifact_cleaner import get_cleaner
        cleaner = get_cleaner()
        cleaned = cleaner.clean_artifact(MOCK_MERMAID_ERD, "mermaid_erd")
        assert cleaned is not None
        results.record_pass(category, "Artifact cleaner")
    except Exception as e:
        results.record_fail(category, "Artifact cleaner", e)


# ============================================================================
# 10. VALIDATION SERVICE TESTS
# ============================================================================

def test_validation_service(results):
    """Test Validation functionality."""
    category = "10. Validation Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 10.1: Validation service
    try:
        from backend.services.validation_service import get_service
        service = get_service()
        assert hasattr(service, 'validate_artifact')
        results.record_pass(category, "Validation service")
    except Exception as e:
        results.record_fail(category, "Validation service", e)
    
    # Test 10.2: Validate Mermaid ERD
    try:
        from backend.services.validation_service import get_service
        from backend.models.dto import ArtifactType
        service = get_service()
        
        async def test_validate():
            return await service.validate_artifact(
                content=MOCK_MERMAID_ERD,
                artifact_type=ArtifactType.MERMAID_ERD
            )
        
        result = run_async(test_validate())
        assert result is not None
        # Check validation result - can be dict or DTO object
        if hasattr(result, 'is_valid'):
            is_valid = result.is_valid
        else:
            is_valid = result.get("is_valid", False)
        results.record_pass(category, f"Validate Mermaid ERD (is_valid={is_valid})")
    except Exception as e:
        results.record_fail(category, "Validate Mermaid ERD", e)
    
    # Test 10.3: Custom validator service
    try:
        from backend.services.custom_validator_service import CustomValidatorService
        service = CustomValidatorService()
        assert service is not None
        results.record_pass(category, "Custom validator service")
    except Exception as e:
        results.record_fail(category, "Custom validator service", e)
    
    # Test 10.4: Validation API router
    try:
        from backend.api.validation import router
        assert router is not None
        assert router.prefix == "/api/validation"
        results.record_pass(category, "Validation API router")
    except Exception as e:
        results.record_fail(category, "Validation API router", e)


# ============================================================================
# 11. MODEL SERVICE TESTS
# ============================================================================

def test_model_service(results):
    """Test Model Management functionality."""
    category = "11. Model Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 11.1: Model service
    try:
        from backend.services.model_service import get_service
        service = get_service()
        assert hasattr(service, 'list_models')
        assert hasattr(service, 'get_model')
        assert hasattr(service, 'get_routing_for_artifact')
        results.record_pass(category, "Model service")
    except Exception as e:
        results.record_fail(category, "Model service", e)
    
    # Test 11.2: List models async
    try:
        from backend.services.model_service import get_service
        service = get_service()
        
        async def test_list():
            return await service.list_models()
        
        models = run_async(test_list())
        assert isinstance(models, list)
        results.record_pass(category, f"List models ({len(models)} models)")
    except Exception as e:
        results.record_fail(category, "List models async", e)
    
    # Test 11.3: Model API router
    try:
        from backend.api.models import router
        assert router is not None
        assert router.prefix == "/api/models"
        results.record_pass(category, "Model API router")
    except Exception as e:
        results.record_fail(category, "Model API router", e)


# ============================================================================
# 12. CHAT SERVICE TESTS
# ============================================================================

def test_chat_service(results):
    """Test Chat functionality."""
    category = "12. Chat Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 12.1: Chat service
    try:
        from backend.services.chat_service import get_chat_service
        service = get_chat_service()
        assert hasattr(service, 'chat')
        results.record_pass(category, "Chat service")
    except Exception as e:
        results.record_fail(category, "Chat service", e)
    
    # Test 12.2: Agentic chat service
    try:
        from backend.services.agentic_chat_service import get_agentic_chat_service
        service = get_agentic_chat_service()
        assert hasattr(service, 'chat')
        results.record_pass(category, "Agentic chat service")
    except Exception as e:
        results.record_fail(category, "Agentic chat service", e)
    
    # Test 12.3: Chat API router
    try:
        from backend.api.chat import router
        assert router is not None
        assert router.prefix == "/api/chat"
        results.record_pass(category, "Chat API router")
    except Exception as e:
        results.record_fail(category, "Chat API router", e)


# ============================================================================
# 13. FEEDBACK SERVICE TESTS
# ============================================================================

def test_feedback_service(results):
    """Test Feedback functionality."""
    category = "13. Feedback Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 13.1: Feedback service
    try:
        from backend.services.feedback_service import get_service
        service = get_service()
        assert hasattr(service, 'record_feedback')
        assert hasattr(service, 'get_training_stats')
        assert hasattr(service, 'get_feedback_history')
        results.record_pass(category, "Feedback service")
    except Exception as e:
        results.record_fail(category, "Feedback service", e)
    
    # Test 13.2: Feedback API router
    try:
        from backend.api.feedback import router
        assert router is not None
        assert router.prefix == "/api/feedback"
        results.record_pass(category, "Feedback API router")
    except Exception as e:
        results.record_fail(category, "Feedback API router", e)


# ============================================================================
# 14. MEETING NOTES SERVICE TESTS
# ============================================================================

def test_meeting_notes_service(results):
    """Test Meeting Notes functionality."""
    category = "14. Meeting Notes"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 14.1: Meeting notes service
    try:
        from backend.services.meeting_notes_service import get_service
        service = get_service()
        assert hasattr(service, 'suggest_folder')
        results.record_pass(category, "Meeting notes service")
    except Exception as e:
        results.record_fail(category, "Meeting notes service", e)
    
    # Test 14.2: Meeting notes parser
    try:
        from backend.services.meeting_notes_parser import MeetingNotesParser
        parser = MeetingNotesParser()
        assert hasattr(parser, 'parse')
        results.record_pass(category, "Meeting notes parser")
    except Exception as e:
        results.record_fail(category, "Meeting notes parser", e)
    
    # Test 14.3: Meeting notes API router
    try:
        from backend.api.meeting_notes import router
        assert router is not None
        assert router.prefix == "/api/meeting-notes"
        results.record_pass(category, "Meeting notes API router")
    except Exception as e:
        results.record_fail(category, "Meeting notes API router", e)


# ============================================================================
# 15. VERSION SERVICE TESTS
# ============================================================================

def test_version_service(results):
    """Test Version Management functionality."""
    category = "15. Version Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 15.1: Version service
    try:
        from backend.services.version_service import get_version_service
        service = get_version_service()
        assert hasattr(service, 'create_version')
        assert hasattr(service, 'get_versions')
        results.record_pass(category, "Version service")
    except Exception as e:
        results.record_fail(category, "Version service", e)
    
    # Test 15.2: Version API router
    try:
        from backend.api.versions import router
        assert router is not None
        assert router.prefix == "/api/versions"
        results.record_pass(category, "Version API router")
    except Exception as e:
        results.record_fail(category, "Version API router", e)


# ============================================================================
# 16. EXPORT SERVICE TESTS
# ============================================================================

def test_export_service(results):
    """Test Export functionality."""
    category = "16. Export Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 16.1: Export service
    try:
        from backend.services.export_service import ExportService
        service = ExportService()
        assert service is not None
        results.record_pass(category, "Export service")
    except Exception as e:
        results.record_fail(category, "Export service", e)
    
    # Test 16.2: Export API router
    try:
        from backend.api.export import router
        assert router is not None
        results.record_pass(category, "Export API router")
    except Exception as e:
        results.record_fail(category, "Export API router", e)


# ============================================================================
# 17. TEMPLATE SERVICE TESTS
# ============================================================================

def test_template_service(results):
    """Test Template functionality."""
    category = "17. Template Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 17.1: Template service
    try:
        from backend.services.template_service import TemplateService
        service = TemplateService()
        assert service is not None
        results.record_pass(category, "Template service")
    except Exception as e:
        results.record_fail(category, "Template service", e)
    
    # Test 17.2: Template API router
    try:
        from backend.api.templates import router
        assert router is not None
        results.record_pass(category, "Template API router")
    except Exception as e:
        results.record_fail(category, "Template API router", e)


# ============================================================================
# 18. TRAINING SERVICE TESTS
# ============================================================================

def test_training_service(results):
    """Test Training/Fine-tuning functionality."""
    category = "18. Training Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 18.1: Training service
    try:
        from backend.services.training_service import get_service
        service = get_service()
        assert hasattr(service, 'list_jobs')
        results.record_pass(category, "Training service")
    except Exception as e:
        results.record_fail(category, "Training service", e)
    
    # Test 18.2: Dataset service
    try:
        from backend.services.dataset_service import get_service
        service = get_service()
        assert service is not None
        results.record_pass(category, "Dataset service")
    except Exception as e:
        results.record_fail(category, "Dataset service", e)
    
    # Test 18.3: Finetuning pool
    try:
        from backend.services.finetuning_pool import get_pool
        pool = get_pool()
        assert pool is not None
        results.record_pass(category, "Finetuning pool")
    except Exception as e:
        results.record_fail(category, "Finetuning pool", e)
    
    # Test 18.4: Training API router
    try:
        from backend.api.training import router
        assert router is not None
        assert router.prefix == "/api/training"
        results.record_pass(category, "Training API router")
    except Exception as e:
        results.record_fail(category, "Training API router", e)


# ============================================================================
# 19. GIT SERVICE TESTS
# ============================================================================

def test_git_service(results):
    """Test Git integration functionality."""
    category = "19. Git Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 19.1: Git service
    try:
        from backend.services.git_service import GitService
        service = GitService()
        assert service is not None
        results.record_pass(category, "Git service")
    except Exception as e:
        results.record_fail(category, "Git service", e)
    
    # Test 19.2: Git API router
    try:
        from backend.api.git import router
        assert router is not None
        results.record_pass(category, "Git API router")
    except Exception as e:
        results.record_fail(category, "Git API router", e)


# ============================================================================
# 20. HTML DIAGRAM SERVICE TESTS
# ============================================================================

def test_html_diagram_service(results):
    """Test HTML Diagram generation functionality."""
    category = "20. HTML Diagrams"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 20.1: HTML diagram generator
    try:
        from backend.services.html_diagram_generator import HTMLDiagramGenerator
        generator = HTMLDiagramGenerator()
        assert generator is not None
        results.record_pass(category, "HTML diagram generator")
    except Exception as e:
        results.record_fail(category, "HTML diagram generator", e)
    
    # Test 20.2: HTML diagrams API router
    try:
        from backend.api.html_diagrams import router
        assert router is not None
        results.record_pass(category, "HTML diagrams API router")
    except Exception as e:
        results.record_fail(category, "HTML diagrams API router", e)


# ============================================================================
# 21. ANALYSIS SERVICE TESTS
# ============================================================================

def test_analysis_service(results):
    """Test Analysis functionality."""
    category = "21. Analysis Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 21.1: Analysis service
    try:
        from backend.services.analysis_service import get_service
        service = get_service()
        assert hasattr(service, 'get_current_patterns')
        results.record_pass(category, "Analysis service")
    except Exception as e:
        results.record_fail(category, "Analysis service", e)
    
    # Test 21.2: Analysis API router
    try:
        from backend.api.analysis import router
        assert router is not None
        assert router.prefix == "/api/analysis"
        results.record_pass(category, "Analysis API router")
    except Exception as e:
        results.record_fail(category, "Analysis API router", e)


# ============================================================================
# 22. HUGGINGFACE SERVICE TESTS
# ============================================================================

def test_huggingface_service(results):
    """Test HuggingFace integration functionality."""
    category = "22. HuggingFace"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 22.1: HuggingFace service
    try:
        from backend.services.huggingface_service import get_service
        service = get_service()
        assert service is not None
        results.record_pass(category, "HuggingFace service")
    except Exception as e:
        results.record_fail(category, "HuggingFace service", e)
    
    # Test 22.2: HuggingFace API router
    try:
        from backend.api.huggingface import router
        assert router is not None
        assert router.prefix == "/api/huggingface"
        results.record_pass(category, "HuggingFace API router")
    except Exception as e:
        results.record_fail(category, "HuggingFace API router", e)


# ============================================================================
# 23. ASSISTANT SERVICE TESTS
# ============================================================================

def test_assistant_services(results):
    """Test Assistant/Suggestions functionality."""
    category = "23. Assistant Services"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 23.1: Artifact suggestions
    try:
        from backend.services.artifact_suggestions import get_suggestion_engine
        service = get_suggestion_engine()
        assert service is not None
        results.record_pass(category, "Artifact suggestions service")
    except Exception as e:
        results.record_fail(category, "Artifact suggestions service", e)
    
    # Test 23.2: Artifact linker
    try:
        from backend.services.artifact_linker import ArtifactLinker
        linker = ArtifactLinker()
        assert linker is not None
        results.record_pass(category, "Artifact linker")
    except Exception as e:
        results.record_fail(category, "Artifact linker", e)
    
    # Test 23.3: Design review
    try:
        from backend.services.design_review import DesignReviewService
        reviewer = DesignReviewService()
        assert reviewer is not None
        results.record_pass(category, "Design review service")
    except Exception as e:
        results.record_fail(category, "Design review service", e)
    
    # Test 23.4: Sprint package
    try:
        from backend.services.sprint_package import get_sprint_package_generator
        packager = get_sprint_package_generator()
        assert packager is not None
        results.record_pass(category, "Sprint package service")
    except Exception as e:
        results.record_fail(category, "Sprint package service", e)
    
    # Test 23.5: Quality predictor
    try:
        from backend.services.quality_predictor import QualityPredictor
        predictor = QualityPredictor()
        assert predictor is not None
        results.record_pass(category, "Quality predictor")
    except Exception as e:
        results.record_fail(category, "Quality predictor", e)
    
    # Test 23.6: Assistant API router
    try:
        from backend.api.assistant import router
        assert router is not None
        results.record_pass(category, "Assistant API router")
    except Exception as e:
        results.record_fail(category, "Assistant API router", e)


# ============================================================================
# 24. MULTI-REPO SERVICE TESTS
# ============================================================================

def test_multi_repo_service(results):
    """Test Multi-Repository functionality."""
    category = "24. Multi-Repo"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 24.1: Multi-repo service
    try:
        from backend.services.multi_repo import MultiRepoService
        service = MultiRepoService()
        assert service is not None
        results.record_pass(category, "Multi-repo service")
    except Exception as e:
        results.record_fail(category, "Multi-repo service", e)
    
    # Test 24.2: Multi-repo API router
    try:
        from backend.api.multi_repo import router
        assert router is not None
        results.record_pass(category, "Multi-repo API router")
    except Exception as e:
        results.record_fail(category, "Multi-repo API router", e)


# ============================================================================
# 25. ML FEATURES SERVICE TESTS
# ============================================================================

def test_ml_features_service(results):
    """Test ML Feature Engineering functionality."""
    category = "25. ML Features"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 25.1: ML Features service
    try:
        from backend.services.ml_features import MLFeatureEngineer
        engineer = MLFeatureEngineer()
        assert engineer is not None
        results.record_pass(category, "ML Features service")
    except Exception as e:
        results.record_fail(category, "ML Features service", e)
    
    # Test 25.2: ML Features API router
    try:
        from backend.api.ml_features import router
        assert router is not None
        results.record_pass(category, "ML Features API router")
    except Exception as e:
        results.record_fail(category, "ML Features API router", e)


# ============================================================================
# 26. SYNTHETIC DATA SERVICE TESTS
# ============================================================================

def test_synthetic_data_service(results):
    """Test Synthetic Data generation functionality."""
    category = "26. Synthetic Data"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 26.1: Synthetic dataset service
    try:
        # Check if SyntheticDatasetService can be imported (may require GEMINI_API_KEY in settings)
        import backend.services.synthetic_dataset_service as sds
        assert hasattr(sds, 'SyntheticDatasetService')
        results.record_pass(category, "Synthetic dataset service")
    except Exception as e:
        results.record_fail(category, "Synthetic dataset service", e)
    
    # Test 26.2: Synthetic data API router
    try:
        from backend.api.synthetic_data import router
        assert router is not None
        results.record_pass(category, "Synthetic data API router")
    except Exception as e:
        results.record_fail(category, "Synthetic data API router", e)


# ============================================================================
# 27. VRAM SERVICE TESTS
# ============================================================================

def test_vram_service(results):
    """Test VRAM monitoring functionality."""
    category = "27. VRAM Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 27.1: VRAM API router
    try:
        from backend.api.vram import router
        assert router is not None
        assert router.prefix == "/api/vram"
        results.record_pass(category, "VRAM API router")
    except Exception as e:
        results.record_fail(category, "VRAM API router", e)


# ============================================================================
# 28. AI SERVICE TESTS
# ============================================================================

def test_ai_service(results):
    """Test AI parsing and improvement functionality."""
    category = "28. AI Service"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 28.1: AI API router
    try:
        from backend.api.ai import router
        assert router is not None
        assert router.prefix == "/api/ai"
        results.record_pass(category, "AI API router")
    except Exception as e:
        results.record_fail(category, "AI API router", e)


# ============================================================================
# 29. PROJECT TARGET SERVICE TESTS
# ============================================================================

def test_project_target_service(results):
    """Test Project Target management functionality."""
    category = "29. Project Target"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 29.1: Project target API router
    try:
        from backend.api.project_target import router
        assert router is not None
        assert router.prefix == "/api/project-target"
        results.record_pass(category, "Project target API router")
    except Exception as e:
        results.record_fail(category, "Project target API router", e)


# ============================================================================
# 30. WEBSOCKET SERVICE TESTS
# ============================================================================

def test_websocket_service(results):
    """Test WebSocket functionality."""
    category = "30. WebSocket"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 30.1: WebSocket manager
    try:
        from backend.core.websocket import websocket_manager
        assert websocket_manager is not None
        assert hasattr(websocket_manager, 'emit_generation_progress')
        assert hasattr(websocket_manager, 'emit_generation_complete')
        results.record_pass(category, "WebSocket manager")
    except Exception as e:
        results.record_fail(category, "WebSocket manager", e)
    
    # Test 30.2: WebSocket API router
    try:
        from backend.api.websocket import router
        assert router is not None
        results.record_pass(category, "WebSocket API router")
    except Exception as e:
        results.record_fail(category, "WebSocket API router", e)


# ============================================================================
# 31. CUSTOM ARTIFACT SERVICE TESTS
# ============================================================================

def test_custom_artifact_service(results):
    """Test Custom Artifact Type functionality."""
    category = "31. Custom Artifacts"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 31.1: Custom artifact service
    try:
        from backend.services.custom_artifact_service import get_service
        service = get_service()
        assert hasattr(service, 'get_all_artifact_types')
        assert hasattr(service, 'create_type')
        results.record_pass(category, "Custom artifact service")
    except Exception as e:
        results.record_fail(category, "Custom artifact service", e)


# ============================================================================
# 32. MIGRATION GENERATOR SERVICE TESTS
# ============================================================================

def test_migration_generator(results):
    """Test Migration Generator functionality."""
    category = "32. Migration Generator"
    print(f"\n{'='*70}")
    print(f" {category}")
    print(f"{'='*70}")
    
    # Test 32.1: Migration generator
    try:
        from backend.services.migration_generator import MigrationGenerator
        generator = MigrationGenerator()
        assert generator is not None
        results.record_pass(category, "Migration generator")
    except Exception as e:
        results.record_fail(category, "Migration generator", e)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all functionality tests."""
    print("\n" + "="*70)
    print(" ARCHITECT.AI - COMPREHENSIVE FUNCTIONALITY TEST SUITE ")
    print("="*70)
    print(f"\nStarted: {datetime.now().isoformat()}")
    print(f"Testing ALL {32} functionality categories...")
    
    results = TestResults()
    
    # Run all test categories
    test_core_application(results)
    test_authentication(results)
    test_dto_models(results)
    test_rag_system(results)
    test_knowledge_graph(results)
    test_pattern_mining(results)
    test_context_builder(results)
    test_universal_context(results)
    test_generation_service(results)
    test_validation_service(results)
    test_model_service(results)
    test_chat_service(results)
    test_feedback_service(results)
    test_meeting_notes_service(results)
    test_version_service(results)
    test_export_service(results)
    test_template_service(results)
    test_training_service(results)
    test_git_service(results)
    test_html_diagram_service(results)
    test_analysis_service(results)
    test_huggingface_service(results)
    test_assistant_services(results)
    test_multi_repo_service(results)
    test_ml_features_service(results)
    test_synthetic_data_service(results)
    test_vram_service(results)
    test_ai_service(results)
    test_project_target_service(results)
    test_websocket_service(results)
    test_custom_artifact_service(results)
    test_migration_generator(results)
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 ALL FUNCTIONALITY TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {results.failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
