"""Verify file structure after reorganization"""
from pathlib import Path
import importlib.util

print("\n" + "="*60)
print("STRUCTURE VERIFICATION")
print("="*60 + "\n")

# Check critical files exist
print("[1] Checking critical files exist...")
critical_files = [
    "app/app_v2.py",
    "agents/universal_agent.py",
    "components/knowledge_graph.py",
    "components/pattern_mining.py",
    "validation/output_validator.py",
    "ai/ollama_client.py",
    "rag/chromadb_config.py",
    "requirements.txt",
]

all_exist = True
for file_path in critical_files:
    exists = Path(file_path).exists()
    status = "✅" if exists else "❌"
    print(f"  {status} {file_path}")
    if not exists:
        all_exist = False

# Check new directories
print("\n[2] Checking new directory structure...")
new_dirs = {
    "tests": ["run_tests.py", "test_integration.py"],
    "scripts": ["launch.py", "launch.sh", "launch.bat"],
    "documentation": ["README_OLD.md", "TECHNICAL_DOCUMENTATION_OLD.md"],
}

for dir_name, expected_files in new_dirs.items():
    dir_path = Path(dir_name)
    if dir_path.exists():
        file_count = len(list(dir_path.glob("*")))
        print(f"  ✅ {dir_name}/ ({file_count} files)")
        for expected in expected_files:
            if (dir_path / expected).exists():
                print(f"     ✅ {expected}")
            else:
                print(f"     ⚠️  {expected} missing")
    else:
        print(f"  ❌ {dir_name}/ not found")

# Check Python can find modules
print("\n[3] Checking Python module structure...")
modules_to_check = [
    "agents",
    "components", 
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

# Summary
print("\n" + "="*60)
if all_exist:
    print("✅ ALL CRITICAL FILES PRESENT")
    print("✅ REORGANIZATION SUCCESSFUL")
else:
    print("⚠️  SOME FILES MISSING")
print("="*60 + "\n")
