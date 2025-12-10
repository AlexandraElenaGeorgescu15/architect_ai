#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick verification that imports work for Architect.AI v3.5.2"""
import sys
import os

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError):
        pass

print("\n" + "="*60)
print("QUICK IMPORT VERIFICATION - Architect.AI v3.5.2")
print("="*60 + "\n")

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

tests_passed = 0
tests_total = 6

# Test 1: Agent import
print("[1/6] Testing agents.universal_agent...")
try:
    from agents.universal_agent import UniversalArchitectAgent
    print("  ✅ SUCCESS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 2: Backend services import
print("\n[2/6] Testing backend services...")
try:
    from backend.services.knowledge_graph import KnowledgeGraphBuilder
    from backend.services.pattern_mining import PatternMiner
    print("  ✅ SUCCESS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 3: Validation import
print("\n[3/6] Testing validation...")
try:
    from validation.output_validator import ArtifactValidator
    print("  ✅ SUCCESS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 4: AI modules
print("\n[4/6] Testing ai modules...")
try:
    from ai.ollama_client import OllamaClient
    from ai.model_router import ModelRouter
    print("  ✅ SUCCESS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 5: RAG modules
print("\n[5/6] Testing rag modules...")
try:
    from rag.chromadb_config import get_global_chroma_client
    from rag.retrieve import vector_search
    print("  ✅ SUCCESS")
    tests_passed += 1
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Test 6: Backend FastAPI app
print("\n[6/6] Testing backend FastAPI app...")
try:
    from pathlib import Path
    app_path = Path("backend/main.py")
    if app_path.exists():
        # Try to import the FastAPI app
        from backend.main import app
        print("  ✅ SUCCESS")
        tests_passed += 1
    else:
        print("  ❌ FAILED: backend/main.py not found")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Summary
print("\n" + "="*60)
print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
print("="*60)

if tests_passed == tests_total:
    print("\n✅ ALL IMPORTS WORKING - Verification successful!")
    sys.exit(0)
else:
    print(f"\n⚠️  {tests_total - tests_passed} test(s) failed")
    sys.exit(1)
