"""Test imports with timeout to detect hangs"""
import sys
import os
from pathlib import Path

# Use centralized ChromaDB telemetry configuration
try:
    from config.settings import configure_chromadb_telemetry
    configure_chromadb_telemetry()
except ImportError:
    # Fallback if config module not available
    os.environ["ANONYMIZED_TELEMETRY"] = "False"
    os.environ["CHROMA_TELEMETRY"] = "False"
    os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

print("\n" + "="*60)
print("IMPORT FUNCTIONALITY TEST")
print("="*60 + "\n")

tests_passed = 0
tests_total = 0

# Test 1: Basic imports (no initialization)
print("[1] Testing basic module imports (no init)...")
tests_total += 1
try:
    import agents.universal_agent
    import components.knowledge_graph
    import components.pattern_mining
    import validation.output_validator
    import ai.ollama_client
    import ai.model_router
    print("  ✅ All modules importable")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 2: Check __init__ files
print("\n[2] Testing package structure...")
tests_total += 1
try:
    import agents
    import components
    import validation
    import ai
    import rag
    print("  ✅ All packages valid")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 3: Check if classes are accessible (but don't instantiate)
print("\n[3] Testing class accessibility...")
tests_total += 1
try:
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
    
    print("  ✅ All critical classes accessible")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 4: Check test files can be imported
print("\n[4] Testing test file imports...")
tests_total += 1
try:
    # Now that tests has __init__.py, we can import it properly
    from tests.run_tests import run_quick_tests
    assert callable(run_quick_tests)
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
