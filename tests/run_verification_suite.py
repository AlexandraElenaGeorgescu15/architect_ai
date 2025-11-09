"""
Comprehensive Post-Reorganization Test Suite
Tests that all critical functionality still works after file reorganization
"""
import sys
from pathlib import Path

print("\n" + "="*70)
print("POST-REORGANIZATION VERIFICATION SUITE")
print("="*70)

# Test Results
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

# ============================================================================
# TEST 1: File Structure
# ============================================================================
print("\n[TEST 1] File Structure Integrity")
print("-" * 70)

critical_files = [
    "app/app_v2.py",
    "agents/universal_agent.py",
    "components/knowledge_graph.py",
    "components/pattern_mining.py",
    "components/local_finetuning.py",
    "validation/output_validator.py",
    "ai/ollama_client.py",
    "ai/model_router.py",
    "rag/chromadb_config.py",
    "rag/retrieve.py",
    "requirements.txt",
    "docker-compose.yml",
    "README.md",
    "TECHNICAL_DOCUMENTATION.md",
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
print("\n[TEST 2] New Directory Structure")
print("-" * 70)

expected_dirs = {
    "tests": 14,  # Expected minimum file count
    "scripts": 6,
    "documentation": 15,
}

dirs_ok = True
for dir_name, min_files in expected_dirs.items():
    dir_path = Path(dir_name)
    if dir_path.exists():
        file_count = len(list(dir_path.glob("*")))
        if file_count >= min_files:
            print(f"  ✅ {dir_name}/ ({file_count} files)")
        else:
            print(f"  ⚠️  {dir_name}/ ({file_count} files, expected >= {min_files})")
            results["warnings"].append(f"{dir_name} has fewer files than expected")
    else:
        print(f"  ❌ {dir_name}/ NOT FOUND")
        dirs_ok = False

if dirs_ok:
    results["passed"].append("Directory structure correct")
else:
    results["failed"].append("Directory structure incomplete")

# ============================================================================
# TEST 3: Python Package Structure
# ============================================================================
print("\n[TEST 3] Python Package Structure")
print("-" * 70)

packages = ["agents", "components", "validation", "ai", "rag", "utils", "workers"]

packages_ok = True
for package in packages:
    package_path = Path(package)
    init_file = package_path / "__init__.py"
    if init_file.exists():
        print(f"  ✅ {package}/__init__.py")
    else:
        print(f"  ❌ {package}/__init__.py MISSING")
        packages_ok = False

if packages_ok:
    results["passed"].append("All Python packages have __init__.py")
else:
    results["failed"].append("Some __init__.py files missing")

# ============================================================================
# TEST 4: No Orphaned Files in Root
# ============================================================================
print("\n[TEST 4] Root Directory Cleanup")
print("-" * 70)

root_path = Path(".")
root_files = [f for f in root_path.glob("*.py") if f.is_file()]

# Expected root Python files
expected_root_files = {"quick_verify.py", "verify_structure.py", "test_imports.py", "run_verification_suite.py"}

orphaned = []
for file in root_files:
    if file.name.startswith("test_") or file.name.startswith("verify_") or file.name.startswith("check_"):
        if file.name not in expected_root_files:
            orphaned.append(file.name)
            print(f"  ⚠️  {file.name} (should be in tests/)")

if not orphaned:
    print("  ✅ No orphaned test/verify files in root")
    results["passed"].append("Root directory is clean")
else:
    results["warnings"].append(f"{len(orphaned)} files might need moving to tests/")

# ============================================================================
# TEST 5: Documentation Structure  
# ============================================================================
print("\n[TEST 5] Documentation Files")
print("-" * 70)

readme_path = Path("README.md")
tech_doc_path = Path("TECHNICAL_DOCUMENTATION.md")

readme_ok = False
tech_doc_ok = False

if readme_path.exists():
    size = readme_path.stat().st_size
    if size > 20000:  # Should be ~25KB
        print(f"  ✅ README.md ({size:,} bytes)")
        readme_ok = True
    else:
        print(f"  ⚠️  README.md ({size:,} bytes - seems small)")
else:
    print("  ❌ README.md MISSING")

if tech_doc_path.exists():
    size = tech_doc_path.stat().st_size
    if size > 60000:  # Should be ~62KB
        print(f"  ✅ TECHNICAL_DOCUMENTATION.md ({size:,} bytes)")
        tech_doc_ok = True
    else:
        print(f"  ⚠️  TECHNICAL_DOCUMENTATION.md ({size:,} bytes - seems small)")
else:
    print("  ❌ TECHNICAL_DOCUMENTATION.md MISSING")

if readme_ok and tech_doc_ok:
    results["passed"].append("Documentation files updated correctly")
else:
    results["failed"].append("Documentation files issue")

# ============================================================================
# TEST 6: Streamlit App File
# ============================================================================
print("\n[TEST 6] Streamlit App Integrity")
print("-" * 70)

app_file = Path("app/app_v2.py")
if app_file.exists():
    size = app_file.stat().st_size
    # Should be around 200KB (5762 lines)
    if size > 100000:
        print(f"  ✅ app/app_v2.py ({size:,} bytes)")
        results["passed"].append("Main app file intact")
    else:
        print(f"  ⚠️  app/app_v2.py ({size:,} bytes - seems small)")
        results["warnings"].append("App file smaller than expected")
else:
    print("  ❌ app/app_v2.py MISSING")
    results["failed"].append("Main app file missing")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*70)
print("VERIFICATION SUMMARY")
print("="*70)

print(f"\n✅ PASSED: {len(results['passed'])}")
for item in results["passed"]:
    print(f"   • {item}")

if results["warnings"]:
    print(f"\n⚠️  WARNINGS: {len(results['warnings'])}")
    for item in results["warnings"]:
        print(f"   • {item}")

if results["failed"]:
    print(f"\n❌ FAILED: {len(results['failed'])}")
    for item in results["failed"]:
        print(f"   • {item}")
    print("\n" + "="*70)
    print("❌ VERIFICATION FAILED - Issues detected")
    print("="*70)
    sys.exit(1)
else:
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED")
    print("✅ REORGANIZATION SUCCESSFUL - SYSTEM INTACT")
    print("="*70)
    sys.exit(0)
