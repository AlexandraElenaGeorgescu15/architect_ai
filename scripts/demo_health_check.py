#!/usr/bin/env python3
"""
Demo Health Check - Verify Architect.AI is ready for demo
Run this before any presentation to catch issues early.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Disable telemetry noise
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"

def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print('='*60)

def check_ok(name: str):
    print(f"  ✅ {name}")

def check_fail(name: str, error: str = ""):
    print(f"  ❌ {name}")
    if error:
        print(f"     └─ {error}")

def check_warn(name: str, msg: str = ""):
    print(f"  ⚠️  {name}")
    if msg:
        print(f"     └─ {msg}")

def main():
    print_header("ARCHITECT.AI DEMO HEALTH CHECK")
    
    all_passed = True
    warnings = []
    
    # =========================================================================
    # 1. Python Imports
    # =========================================================================
    print("\n[1/6] Checking Python imports...")
    
    try:
        from backend.main import app
        check_ok("FastAPI app imports")
    except Exception as e:
        check_fail("FastAPI app imports", str(e))
        all_passed = False
    
    try:
        from backend.services.generation_service import get_service
        check_ok("Generation service")
    except Exception as e:
        check_fail("Generation service", str(e))
        all_passed = False
    
    try:
        from backend.services.agentic_chat_service import get_agentic_chat_service
        check_ok("Agentic chat service")
    except Exception as e:
        check_fail("Agentic chat service", str(e))
        all_passed = False
    
    try:
        from backend.services.custom_artifact_service import get_service as get_custom_service
        check_ok("Custom artifact service")
    except Exception as e:
        check_fail("Custom artifact service", str(e))
        all_passed = False
    
    # =========================================================================
    # 2. Meeting Notes Folders
    # =========================================================================
    print("\n[2/6] Checking demo meeting notes...")
    
    meeting_notes_dir = project_root / "data" / "meeting_notes"
    demo_folders = ["ecommerce_platform", "healthcare_api", "fintech_dashboard"]
    
    for folder in demo_folders:
        folder_path = meeting_notes_dir / folder
        if folder_path.exists():
            files = list(folder_path.glob("*.md"))
            if files:
                check_ok(f"Demo folder: {folder} ({len(files)} files)")
            else:
                check_warn(f"Demo folder: {folder}", "No .md files found")
                warnings.append(f"Add meeting notes to {folder}")
        else:
            check_warn(f"Demo folder: {folder}", "Not found - creating...")
            folder_path.mkdir(parents=True, exist_ok=True)
            warnings.append(f"Created empty folder: {folder}")
    
    # =========================================================================
    # 3. Ollama Connection
    # =========================================================================
    print("\n[3/6] Checking Ollama connection...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                check_ok(f"Ollama running ({len(models)} models available)")
                # List first 3 models
                for m in models[:3]:
                    print(f"     └─ {m.get('name', 'unknown')}")
                if len(models) > 3:
                    print(f"     └─ ... and {len(models)-3} more")
            else:
                check_warn("Ollama running but no models", "Run: ollama pull llama3:8b-instruct-q4_K_M")
                warnings.append("No Ollama models - pull some models for local generation")
        else:
            check_fail("Ollama not responding")
            all_passed = False
    except Exception as e:
        check_warn("Ollama not running", "Local models won't work, but cloud models will")
        warnings.append("Ollama not running - start it for local model support")
    
    # =========================================================================
    # 4. API Keys
    # =========================================================================
    print("\n[4/6] Checking API keys...")
    
    from backend.core.config import settings
    
    if settings.groq_api_key:
        check_ok("Groq API key configured (for fast AI suggestions)")
    else:
        check_warn("Groq API key not set", "AI model suggestions will use fallback heuristics")
        warnings.append("Set GROQ_API_KEY for AI-powered model suggestions")
    
    if settings.google_api_key or settings.gemini_api_key:
        check_ok("Google/Gemini API key configured")
    else:
        check_warn("Google/Gemini API key not set", "Cloud fallback limited")
    
    if settings.openai_api_key:
        check_ok("OpenAI API key configured")
    else:
        check_warn("OpenAI API key not set", "GPT-4 fallback unavailable")
    
    # =========================================================================
    # 5. Database & Storage
    # =========================================================================
    print("\n[5/6] Checking storage...")
    
    db_path = project_root / "data" / "architect_ai.db"
    if db_path.exists():
        size_mb = db_path.stat().st_size / (1024 * 1024)
        check_ok(f"SQLite database exists ({size_mb:.1f} MB)")
    else:
        check_warn("SQLite database not found", "Will be created on first run")
    
    rag_index = project_root / "rag" / "index"
    if rag_index.exists() and any(rag_index.iterdir()):
        check_ok("RAG index exists")
    else:
        check_warn("RAG index empty", "Run 'Build Context' in the UI to populate")
        warnings.append("RAG index empty - index a project before demo")
    
    outputs_dir = project_root / "outputs"
    if outputs_dir.exists():
        check_ok("Outputs directory exists")
    else:
        outputs_dir.mkdir(parents=True, exist_ok=True)
        check_ok("Outputs directory created")
    
    # =========================================================================
    # 6. Frontend Build
    # =========================================================================
    print("\n[6/6] Checking frontend...")
    
    frontend_dir = project_root / "frontend"
    node_modules = frontend_dir / "node_modules"
    
    if node_modules.exists():
        check_ok("Node modules installed")
    else:
        check_fail("Node modules not installed", "Run: cd frontend && npm install")
        all_passed = False
    
    package_json = frontend_dir / "package.json"
    if package_json.exists():
        check_ok("package.json exists")
    else:
        check_fail("package.json missing")
        all_passed = False
    
    # =========================================================================
    # Summary
    # =========================================================================
    print_header("HEALTH CHECK SUMMARY")
    
    if all_passed and not warnings:
        print("\n  🎉 ALL CHECKS PASSED - Ready for demo!")
        print("\n  Start the app with: launch.bat (Windows) or ./launch.sh (Linux/Mac)")
        return 0
    elif all_passed:
        print(f"\n  ✅ Core checks passed with {len(warnings)} warning(s)")
        print("\n  Warnings to address (optional):")
        for w in warnings:
            print(f"    • {w}")
        print("\n  You can proceed with the demo, but consider fixing these.")
        return 0
    else:
        print("\n  ❌ Some checks failed - fix issues before demo")
        print("\n  Required fixes:")
        print("    • See failed checks above")
        if warnings:
            print("\n  Optional improvements:")
            for w in warnings:
                print(f"    • {w}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
