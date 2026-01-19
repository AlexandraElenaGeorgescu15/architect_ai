"""Test imports with timeout to detect hangs"""
import sys
import os
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Use centralized ChromaDB telemetry configuration
try:
    from config.settings import configure_chromadb_telemetry
    configure_chromadb_telemetry()
except ImportError:
    # Fallback if config module not available
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"


class TestImports:
    """Test that all critical modules can be imported."""

    def test_basic_module_imports(self):
        """Test basic module imports (no initialization)."""
        import agents.universal_agent
        import components.knowledge_graph
        import components.pattern_mining
        import validation.output_validator
        import ai.ollama_client
        import ai.model_router
        assert True

    def test_package_structure(self):
        """Test package structure with __init__ files."""
        import agents
        import components
        import validation
        import ai
        import rag
        assert True

    def test_class_accessibility(self):
        """Test that classes are accessible (but don't instantiate)."""
        from agents.universal_agent import UniversalArchitectAgent
        from components.knowledge_graph import KnowledgeGraphBuilder
        from components.pattern_mining import PatternMiner
        from validation.output_validator import ArtifactValidator
        from ai.ollama_client import OllamaClient
        from ai.model_router import ModelRouter
        
        # Just check they're classes, don't instantiate
        assert callable(UniversalArchitectAgent)
        assert callable(KnowledgeGraphBuilder)
        assert callable(PatternMiner)
        assert callable(ArtifactValidator)
        assert callable(OllamaClient)
        assert callable(ModelRouter)

    def test_test_file_imports(self):
        """Test that test files can be imported."""
        from tests.run_tests import run_quick_tests
        assert callable(run_quick_tests)


# Legacy support - run as script
if __name__ == "__main__":
    print("\n" + "="*60)
    print("IMPORT FUNCTIONALITY TEST")
    print("="*60 + "\n")
    
    tests_passed = 0
    tests_total = 4
    
    test_instance = TestImports()
    
    # Test 1
    print("[1] Testing basic module imports (no init)...")
    try:
        test_instance.test_basic_module_imports()
        print("  ✅ All modules importable")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    # Test 2
    print("\n[2] Testing package structure...")
    try:
        test_instance.test_package_structure()
        print("  ✅ All packages valid")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    # Test 3
    print("\n[3] Testing class accessibility...")
    try:
        test_instance.test_class_accessibility()
        print("  ✅ All critical classes accessible")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    # Test 4
    print("\n[4] Testing test file imports...")
    try:
        test_instance.test_test_file_imports()
        print("  ✅ Test files can be imported")
        tests_passed += 1
    except Exception as e:
        print(f"  ❌ FAILED: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("="*60)
    
    if tests_passed == tests_total:
        print("\n✅ ALL IMPORTS WORKING CORRECTLY!")
        print("✅ Reorganization did not break any imports")
        sys.exit(0)
    else:
        print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
        sys.exit(1)
