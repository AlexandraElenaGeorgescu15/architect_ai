"""Verify file structure for Architect.AI v3.5.2 (FastAPI + React)"""
from pathlib import Path
import importlib.util

print("\n" + "="*60)
print("STRUCTURE VERIFICATION - Architect.AI v3.5.2")
print("="*60 + "\n")

# Check critical files exist
print("[1] Checking critical files exist...")
critical_files = [
    "backend/main.py",
    "frontend/package.json",
    "agents/universal_agent.py",
    "backend/services/knowledge_graph.py",
    "backend/services/pattern_mining.py",
    "validation/output_validator.py",
    "ai/ollama_client.py",
    "rag/chromadb_config.py",
    "requirements.txt",
    ".cursorrules",
    "launch.py",
]

all_exist = True
for file_path in critical_files:
    exists = Path(file_path).exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {file_path}")
    if not exists:
        all_exist = False

# Check directory structure
print("\n[2] Checking directory structure...")
required_dirs = {
    "backend": ["main.py", "api/__init__.py", "services/__init__.py", "core/__init__.py"],
    "frontend": ["package.json", "src/App.tsx"],
    "rag": ["ingest.py", "retrieve.py"],
    "context": ["architecture.md", "conventions.md"],
    "agents": ["universal_agent.py"],
    "tests": ["check_setup.py"],
}

for dir_name, expected_files in required_dirs.items():
    dir_path = Path(dir_name)
    if dir_path.exists():
        file_count = len(list(dir_path.glob("*")))
        print(f"  ✅ {dir_name}/ ({file_count} items)")
        for expected in expected_files:
            if (dir_path / expected).exists():
                print(f"     ✅ {expected}")
            else:
                print(f"     ⚠️  {expected} missing")
    else:
        print(f"  ❌ {dir_name}/ not found")
        all_exist = False

# Check Python can find modules
print("\n[3] Checking Python module structure...")
modules_to_check = [
    "agents",
    "backend", 
    "validation",
    "ai",
    "rag",
]

for module_name in modules_to_check:
    spec = importlib.util.find_spec(module_name)
    if spec:
        print(f"  ✅ {module_name} - {spec.origin}")
    else:
        print(f"  ❌ {module_name} - NOT FOUND")

# Check archived files exist
print("\n[4] Checking archive structure...")
archive_dir = Path("archive/legacy_streamlit")
if archive_dir.exists():
    print(f"  ✅ archive/legacy_streamlit/")
    if (archive_dir / "app_v2.py").exists():
        print(f"     ✅ app_v2.py (legacy Streamlit app)")
    if (archive_dir / "components").exists():
        components_count = len(list((archive_dir / "components").glob("*.py")))
        print(f"     ✅ components/ ({components_count} legacy files)")
else:
    print(f"  ⚠️  archive/legacy_streamlit/ not found")

# Summary
print("\n" + "="*60)
if all_exist:
    print("✅ ALL CRITICAL FILES PRESENT")
    print("✅ STRUCTURE VERIFICATION PASSED")
else:
    print("⚠️  SOME FILES MISSING")
print("="*60 + "\n")
