#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Architect.AI - Production Test Suite
Quick smoke test to verify all critical components are working
Run this before deploying or after major changes
"""

import sys
import os
from pathlib import Path

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Disable ChromaDB telemetry before any imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

# Add parent directory to path so we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_quick_tests():
    """Run quick smoke tests"""
    print("=" * 60)
    print("ARCHITECT.AI - QUICK SMOKE TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Imports
    print("\n[TEST 1/5] Testing critical imports...")
    tests_total += 1
    try:
        from agents.universal_agent import UniversalArchitectAgent
        from components.mermaid_syntax_corrector import validate_mermaid_syntax
        from rag.chromadb_config import get_global_chroma_client
        print("  [PASS] All critical imports successful")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] Import error: {e}")
    
    # Test 2: ChromaDB
    print("\n[TEST 2/5] Testing ChromaDB connection...")
    tests_total += 1
    try:
        from rag.chromadb_config import get_global_chroma_client
        client, collection = get_global_chroma_client("rag/index", "repo")
        client.heartbeat()
        count = collection.count()
        print(f"  [PASS] ChromaDB connected ({count} documents indexed)")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] ChromaDB error: {e}")
    
    # Test 3: Agent
    print("\n[TEST 3/5] Testing AI agent...")
    tests_total += 1
    try:
        from agents.universal_agent import UniversalArchitectAgent
        agent = UniversalArchitectAgent()
        assert hasattr(agent, 'generate_erd_only')
        print("  [PASS] Agent initialized successfully")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] Agent error: {e}")
    
    # Test 4: Validation
    print("\n[TEST 4/5] Testing validation system...")
    tests_total += 1
    try:
        from validation.output_validator import ArtifactValidator
        validator = ArtifactValidator()
        test_erd = "erDiagram\n    USER ||--o{ ORDER : places"
        result = validator.validate("erd", test_erd, {})
        print(f"  [PASS] Validation works (score: {result.score:.1f}/100)")
        tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] Validation error: {e}")
    
    # Test 5: File System
    print("\n[TEST 5/5] Testing file system...")
    tests_total += 1
    try:
        outputs_dir = Path("outputs")
        if outputs_dir.exists():
            file_count = sum(1 for _ in outputs_dir.rglob("*") if _.is_file())
            print(f"  [PASS] Outputs directory exists ({file_count} files)")
            tests_passed += 1
        else:
            print("  [WARN] Outputs directory doesn't exist (will be created on first use)")
            tests_passed += 1
    except Exception as e:
        print(f"  [FAIL] File system error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("\n[SUCCESS] All tests passed! Application is ready.")
        return True
    else:
        print(f"\n[WARNING] {tests_total - tests_passed} test(s) failed.")
        return False

if __name__ == "__main__":
    success = run_quick_tests()
    sys.exit(0 if success else 1)


