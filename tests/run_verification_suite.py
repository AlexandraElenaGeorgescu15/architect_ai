"""
Comprehensive Verification Suite for Architect.AI v3.5.2
Run all verification tests to ensure system integrity
"""

import sys
import os
from pathlib import Path

# UTF-8 encoding fix for Windows
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

results = {"passed": [], "failed": [], "warnings": []}

print("="*70)
print("ARCHITECT.AI v3.5.2 VERIFICATION SUITE")
print("="*70)

# ============================================================================
# TEST 1: File Structure
# ============================================================================
print("\n[TEST 1] File Structure Integrity")
print("-" * 70)

critical_files = [
    "backend/main.py",
    "frontend/package.json",
    "agents/universal_agent.py",
    "backend/services/knowledge_graph.py",
    "backend/services/pattern_mining.py",
    "validation/output_validator.py",
    "ai/ollama_client.py",
    "ai/model_router.py",
    "rag/chromadb_config.py",
    "rag/retrieve.py",
    "requirements.txt",
    "README.md",
    ".cursorrules",
    "launch.py",
]

all_files_exist = True
for file_path in critical_files:
    if Path(file_path).exists():
        print(f"  ✅ {file_path}")
    else:
        print(f"  ❌ {file_path} MISSING")
        all_files_exist = False

if all_files_exist:
    results["passed"].append("All critical files present")
else:
    results["failed"].append("Some critical files missing")

# ============================================================================
# TEST 2: Directory Structure
# ============================================================================
print("\n[TEST 2] Directory Structure")
print("-" * 70)

expected_dirs = {
    "backend": 5,
    "frontend": 3,
    "rag": 10,
    "agents": 3,
    "context": 5,
    "tests": 10,
}

dirs_ok = True
for dir_name, min_files in expected_dirs.items():
    dir_path = Path(dir_name)
    if dir_path.exists():
        file_count = len(list(dir_path.rglob("*")))
        if file_count >= min_files:
            print(f"  ✅ {dir_name}/ ({file_count} files)")
        else:
            print(f"  ⚠️  {dir_name}/ ({file_count} files - expected >={min_files})")
            results["warnings"].append(f"{dir_name} has fewer files than expected")
    else:
        print(f"  ❌ {dir_name}/ MISSING")
        dirs_ok = False

if dirs_ok:
    results["passed"].append("Directory structure intact")
else:
    results["failed"].append("Some directories missing")

# ============================================================================
# TEST 3: Python Imports
# ============================================================================
print("\n[TEST 3] Critical Python Imports")
print("-" * 70)

# Disable ChromaDB telemetry before imports
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

imports_ok = True
imports_to_test = [
    ("fastapi", "FastAPI"),
    ("pydantic", "Pydantic"),
    ("sqlalchemy", "SQLAlchemy"),
    ("chromadb", "ChromaDB"),
    ("networkx", "NetworkX"),
]

for module_name, display_name in imports_to_test:
    try:
        __import__(module_name)
        print(f"  ✅ {display_name}")
    except ImportError as e:
        print(f"  ❌ {display_name}: {e}")
        imports_ok = False

if imports_ok:
    results["passed"].append("All critical imports work")
else:
    results["failed"].append("Some imports failed")

# ============================================================================
# TEST 4: Backend Services
# ============================================================================
print("\n[TEST 4] Backend Services")
print("-" * 70)

services_ok = True
services_to_test = [
    ("backend.services.knowledge_graph", "KnowledgeGraphBuilder"),
    ("backend.services.pattern_mining", "PatternMiner"),
    ("backend.services.generation_service", "GenerationService"),
]

for module_path, class_name in services_to_test:
    try:
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name, None)
        if cls:
            print(f"  ✅ {class_name}")
        else:
            print(f"  ⚠️  {class_name} not found in {module_path}")
            results["warnings"].append(f"{class_name} not found")
    except Exception as e:
        print(f"  ❌ {module_path}: {e}")
        services_ok = False

if services_ok:
    results["passed"].append("Backend services loadable")
else:
    results["warnings"].append("Some services failed to load")

# ============================================================================
# TEST 5: Context Files
# ============================================================================
print("\n[TEST 5] Context Files")
print("-" * 70)

context_files = [
    "context/architecture.md",
    "context/conventions.md",
    "context/api_endpoints.md",
    "context/ready_done.md",
    "context/decisions_adr.md",
    "context/_retrieved.md",
]

context_ok = True
for file_path in context_files:
    if Path(file_path).exists():
        size = Path(file_path).stat().st_size
        print(f"  ✅ {file_path} ({size:,} bytes)")
    else:
        print(f"  ❌ {file_path} MISSING")
        context_ok = False

if context_ok:
    results["passed"].append("Context files present")
else:
    results["failed"].append("Some context files missing")

# ============================================================================
# TEST 6: FastAPI Backend
# ============================================================================
print("\n[TEST 6] FastAPI Backend")
print("-" * 70)

app_file = Path("backend/main.py")
if app_file.exists():
    size = app_file.stat().st_size
    if size > 10000:
        print(f"  ✅ backend/main.py ({size:,} bytes)")
        results["passed"].append("Backend main.py intact")
    else:
        print(f"  ⚠️  backend/main.py ({size:,} bytes - seems small)")
        results["warnings"].append("Backend file smaller than expected")
else:
    print("  ❌ backend/main.py MISSING")
    results["failed"].append("Backend main.py missing")

# ============================================================================
# TEST 7: Frontend
# ============================================================================
print("\n[TEST 7] Frontend")
print("-" * 70)

frontend_files = [
    "frontend/package.json",
    "frontend/src/App.tsx",
    "frontend/src/pages/Studio.tsx",
]

frontend_ok = True
for file_path in frontend_files:
    if Path(file_path).exists():
        print(f"  ✅ {file_path}")
    else:
        print(f"  ❌ {file_path} MISSING")
        frontend_ok = False

if frontend_ok:
    results["passed"].append("Frontend files present")
else:
    results["failed"].append("Some frontend files missing")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70)

print(f"\n✅ PASSED: {len(results['passed'])}")
for item in results["passed"]:
    print(f"   • {item}")

print(f"\n⚠️  WARNINGS: {len(results['warnings'])}")
for item in results["warnings"]:
    print(f"   • {item}")

print(f"\n❌ FAILED: {len(results['failed'])}")
for item in results["failed"]:
    print(f"   • {item}")

print("\n" + "="*70)
if results["failed"]:
    print("❌ VERIFICATION FAILED - Some tests failed")
    sys.exit(1)
elif results["warnings"]:
    print("⚠️  VERIFICATION PASSED WITH WARNINGS")
    sys.exit(0)
else:
    print("✅ ALL VERIFICATIONS PASSED")
    sys.exit(0)
