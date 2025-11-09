"""
Startup Validation Script for Architect.AI
Run this before starting the application to validate configuration
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import centralized config
from config.settings import (
    configure_chromadb_telemetry,
    validate_configuration,
    has_api_key,
    get_api_key,
    ROOT_DIR,
    OUTPUTS_DIR,
    RAG_INDEX_DIR,
    MODELS_DIR,
    OLLAMA_BASE_URL
)


def check_python_version():
    """Check Python version"""
    print("\n[1/8] Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"  ❌ Python 3.9+ required, found {version.major}.{version.minor}")
        return False
    print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def check_dependencies():
    """Check critical dependencies"""
    print("\n[2/8] Checking dependencies...")
    critical_deps = [
        'streamlit',
        'chromadb',
        'sentence_transformers',
        'httpx',
    ]
    
    missing = []
    for dep in critical_deps:
        try:
            __import__(dep)
            print(f"  ✅ {dep}")
        except ImportError:
            print(f"  ❌ {dep} not installed")
            missing.append(dep)
    
    if missing:
        print(f"\n  Install missing packages: pip install {' '.join(missing)}")
        return False
    
    return True


def check_api_keys():
    """Check AI provider API keys"""
    print("\n[3/8] Checking AI provider configuration...")
    
    providers_available = []
    
    if get_api_key('groq'):
        print("  ✅ Groq API key configured")
        providers_available.append('Groq')
    
    if get_api_key('openai'):
        print("  ✅ OpenAI API key configured")
        providers_available.append('OpenAI')
    
    if get_api_key('gemini'):
        print("  ✅ Gemini API key configured")
        providers_available.append('Gemini')
    
    # Check Ollama
    try:
        import httpx
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            print(f"  ✅ Ollama available at {OLLAMA_BASE_URL}")
            providers_available.append('Ollama')
    except Exception:
        print(f"  ⚠️  Ollama not available at {OLLAMA_BASE_URL}")
    
    if not providers_available:
        print("\n  ❌ No AI providers configured!")
        print("  Set at least one API key in .env or start Ollama")
        return False
    
    print(f"\n  Available providers: {', '.join(providers_available)}")
    return True


def check_directories():
    """Check required directories exist"""
    print("\n[4/8] Checking directory structure...")
    
    dirs_to_check = [
        ('Root', ROOT_DIR),
        ('Outputs', OUTPUTS_DIR),
        ('RAG Index', RAG_INDEX_DIR),
        ('Models', MODELS_DIR),
    ]
    
    all_exist = True
    for name, dir_path in dirs_to_check:
        if dir_path.exists():
            print(f"  ✅ {name}: {dir_path}")
        else:
            print(f"  ⚠️  {name} not found, creating: {dir_path}")
            dir_path.mkdir(parents=True, exist_ok=True)
    
    return all_exist


def check_chromadb():
    """Check ChromaDB can be initialized"""
    print("\n[5/8] Checking ChromaDB...")
    
    try:
        configure_chromadb_telemetry()
        import chromadb
        from chromadb.config import Settings
        
        # Try to create a test client
        client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True
        ))
        
        # Test collection creation
        collection = client.get_or_create_collection("startup_test")
        client.delete_collection("startup_test")
        
        print("  ✅ ChromaDB initialized successfully")
        return True
    except Exception as e:
        print(f"  ❌ ChromaDB error: {e}")
        return False


def check_imports():
    """Check critical imports"""
    print("\n[6/8] Checking critical imports...")
    
    critical_imports = [
        ('agents.universal_agent', 'UniversalArchitectAgent'),
        ('components.knowledge_graph', 'KnowledgeGraphBuilder'),
        ('validation.output_validator', 'ArtifactValidator'),
        ('ai.model_router', 'ModelRouter'),
    ]
    
    all_ok = True
    for module_name, class_name in critical_imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"  ✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"  ❌ {module_name}.{class_name}: {e}")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check if .env file exists"""
    print("\n[7/8] Checking environment configuration...")
    
    env_file = ROOT_DIR / '.env'
    env_example = ROOT_DIR / '.env.example'
    
    if env_file.exists():
        print(f"  ✅ .env file found")
        return True
    else:
        print(f"  ⚠️  .env file not found")
        if env_example.exists():
            print(f"  💡 Copy .env.example to .env and configure your API keys")
        return False


def check_secrets():
    """Check secrets configuration"""
    print("\n[8/8] Checking secrets configuration...")
    
    try:
        from config.secrets_manager import api_key_manager
        keys = api_key_manager.get_all_keys()
        
        configured = sum(1 for k, v in keys.items() if v)
        print(f"  ✅ Secrets manager initialized ({configured} keys configured)")
        return True
    except Exception as e:
        print(f"  ⚠️  Secrets manager: {e}")
        return True  # Not critical


def main():
    """Run all validation checks"""
    print("=" * 70)
    print("ARCHITECT.AI - STARTUP VALIDATION")
    print("=" * 70)
    
    checks = [
        check_python_version(),
        check_dependencies(),
        check_directories(),
        check_env_file(),
        check_api_keys(),
        check_chromadb(),
        check_imports(),
        check_secrets(),
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    print("\n" + "=" * 70)
    print(f"VALIDATION RESULTS: {passed}/{total} checks passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✅ ALL CHECKS PASSED - Ready to start!")
        print("\nStart the application with:")
        print("  streamlit run app/app_v2.py")
        return 0
    elif passed >= total - 2:
        print(f"\n⚠️  {total - passed} warnings - Application may work with limited functionality")
        return 0
    else:
        print(f"\n❌ {total - passed} critical issues - Please fix before starting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
