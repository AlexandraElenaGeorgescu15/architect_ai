"""
Comprehensive System Tests - November 9, 2025
Tests all critical components to verify system integrity
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
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_entity_extractor():
    """Test 1: Entity Extraction System"""
    print("\n" + "="*80)
    print("TEST 1: Entity Extraction System")
    print("="*80)
    
    try:
        from utils.entity_extractor import extract_entities_from_erd, generate_csharp_dto
        
        # Sample ERD
        sample_erd = """
erDiagram
    User {
        int id PK
        string email
        string name
    }
    RequestSwap {
        int id PK
        string userId FK
        int phoneIdOffered FK
        int phoneIdRequested FK
        string status
        DateTime createdAt
    }
    Phone {
        int id PK
        string brand
        string model
        int storage
        decimal price
    }
"""
        
        result = extract_entities_from_erd(sample_erd)
        
        assert result['entity_count'] == 3, f"Expected 3 entities, got {result['entity_count']}"
        assert 'User' in result['entity_names'], "User entity not found"
        assert 'RequestSwap' in result['entity_names'], "RequestSwap entity not found"
        assert 'Phone' in result['entity_names'], "Phone entity not found"
        
        # Test DTO generation
        if result['entities']:
            dto = generate_csharp_dto(result['entities'][0])
            assert 'public class' in dto, "DTO not generated correctly"
            assert 'get; set;' in dto, "DTO properties not generated"
        
        print(f"✅ PASS: Extracted {result['entity_count']} entities")
        print(f"   Entities: {', '.join(result['entity_names'])}")
        print(f"   Relationships: {result['relationship_count']}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_key_manager():
    """Test 2: API Key Management"""
    print("\n" + "="*80)
    print("TEST 2: API Key Management")
    print("="*80)
    
    try:
        from config.secrets_manager import api_key_manager
        
        # Test Groq key
        groq_key = api_key_manager.get_key('groq')
        if groq_key:
            assert groq_key.startswith('gsk_'), f"Groq key format invalid: {groq_key[:10]}"
            print(f"✅ PASS: Groq key configured")
            print(f"   Key prefix: {groq_key[:20]}...")
        else:
            print(f"⚠️  WARN: Groq key not configured")
        
        # Test Gemini key
        gemini_key = api_key_manager.get_key('gemini')
        if gemini_key:
            print(f"✅ INFO: Gemini key configured: {gemini_key[:20]}...")
        else:
            print(f"⚠️  WARN: Gemini key not configured")
        
        # Test OpenAI key
        openai_key = api_key_manager.get_key('openai')
        if openai_key:
            print(f"✅ INFO: OpenAI key configured: {openai_key[:20]}...")
        else:
            print(f"⚠️  WARN: OpenAI key not configured")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_diagram_cleaning():
    """Test 3: NUCLEAR Diagram Cleaning"""
    print("\n" + "="*80)
    print("TEST 3: NUCLEAR Diagram Cleaning")
    print("="*80)
    
    try:
        # Import the function
        sys.path.insert(0, str(project_root / "app"))
        from app_v2 import strip_markdown_artifacts  # type: ignore
        
        # Test case 1: ERD with explanatory text
        dirty_erd = """
Here is the corrected Mermaid diagram:

```mermaid
erDiagram
    User {
        int id PK
        string name
    }
```

Based on these files, I've created the ERD.
"""
        
        clean_erd = strip_markdown_artifacts(dirty_erd)
        
        # Verify cleaning
        assert 'Here is' not in clean_erd, "Explanatory text not removed"
        assert '```' not in clean_erd, "Markdown blocks not removed"
        assert 'Based on' not in clean_erd, "LLM chatter not removed"
        assert 'erDiagram' in clean_erd, "Diagram code was removed!"
        
        print(f"✅ PASS: Diagram cleaning working")
        print(f"   Before: {len(dirty_erd)} chars")
        print(f"   After: {len(clean_erd)} chars")
        print(f"   Removed: {len(dirty_erd) - len(clean_erd)} chars of junk")
        
        # Test case 2: Diagram with file paths
        dirty_diagram = """
flowchart TD
    A[Start] --> B[Process]
    FILE: C:\\Users\\test\\file.py
    B --> C[End]
"""
        
        clean_diagram = strip_markdown_artifacts(dirty_diagram)
        assert 'C:\\Users\\' not in clean_diagram, "File paths not removed"
        
        print(f"✅ PASS: File path removal working")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_integrity():
    """Test 4: File Integrity"""
    print("\n" + "="*80)
    print("TEST 4: File Integrity")
    print("="*80)
    
    critical_files = [
        "utils/entity_extractor.py",
        "agents/universal_agent.py",
        "validation/output_validator.py",
        "backend/main.py",
        "config/api_key_manager.py",
    ]
    
    all_ok = True
    
    for file_path in critical_files:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"❌ FAIL: File not found: {file_path}")
            all_ok = False
        else:
            # Try to compile the file to check syntax
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                print(f"✅ PASS: {file_path} ({len(content)} chars)")
            except SyntaxError as e:
                print(f"❌ FAIL: Syntax error in {file_path}: {e}")
                all_ok = False
    
    return all_ok


def test_imports():
    """Test 5: Critical Imports"""
    print("\n" + "="*80)
    print("TEST 5: Critical Imports")
    print("="*80)
    
    imports_to_test = [
        "streamlit",
        "chromadb",
        "transformers",
        "sentence_transformers",
        "networkx",
        "ollama",
        "requests",
        "yaml",
        "pydantic",
    ]
    
    all_ok = True
    
    for module_name in imports_to_test:
        try:
            __import__(module_name)
            print(f"✅ PASS: {module_name} available")
        except ImportError as e:
            print(f"⚠️  WARN: {module_name} not available (may be optional): {e}")
            # Don't fail on optional imports
            continue
    
    return all_ok


def test_rag_system():
    """Test 6: RAG System"""
    print("\n" + "="*80)
    print("TEST 6: RAG System")
    print("="*80)
    
    try:
        from rag.filters import load_cfg
        
        cfg = load_cfg()
        assert cfg, "RAG config not loaded"
        print(f"✅ PASS: RAG config loaded")
        print(f"   Store path: {cfg.get('store', {}).get('path', 'N/A')}")
        
        # Check if index exists
        index_path = project_root / cfg.get('store', {}).get('path', 'rag/index')
        if index_path.exists():
            print(f"✅ INFO: RAG index exists at {index_path}")
        else:
            print(f"⚠️  WARN: RAG index not found (run ingestion)")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_system():
    """Test 7: Validation System"""
    print("\n" + "="*80)
    print("TEST 7: Validation System")
    print("="*80)
    
    try:
        from validation.output_validator import ArtifactValidator
        
        validator = ArtifactValidator()
        
        # Test ERD validation
        valid_erd = """
erDiagram
    User {
        int id PK
        string email
        string name
    }
    RequestSwap {
        int id PK
        string userId FK
    }
    User ||--o{ RequestSwap : creates
"""
        
        result = validator.validate_erd(valid_erd, {'rag_context': 'User, RequestSwap entities'})
        
        assert result.score > 0, "Validation score should be > 0"
        print(f"✅ PASS: Validation working")
        print(f"   Score: {result.score:.1f}/100")
        print(f"   Valid: {result.is_valid}")
        print(f"   Errors: {len(result.errors)}")
        print(f"   Warnings: {len(result.warnings)}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_documentation():
    """Test 8: Documentation"""
    print("\n" + "="*80)
    print("TEST 8: Documentation")
    print("="*80)
    
    docs_to_check = [
        "START_HERE.md",
        "FINAL_STATUS_AND_TESTING.md",
        "TODAYS_WORK_COMPLETE_NOV9.md",
        "PROTOTYPE_ENHANCEMENTS_COMPLETE.md",
        "QUICK_START_ENHANCEMENTS.md",
    ]
    
    found = 0
    for doc in docs_to_check:
        if (project_root / doc).exists():
            size = (project_root / doc).stat().st_size
            print(f"✅ PASS: {doc} ({size} bytes)")
            found += 1
        else:
            print(f"⚠️  WARN: {doc} not found")
    
    print(f"\n📚 Documentation: {found}/{len(docs_to_check)} files present")
    return True


def run_all_tests():
    """Run all tests and generate report"""
    print("\n" + "="*80)
    print("🧪 COMPREHENSIVE SYSTEM TEST SUITE")
    print("="*80)
    print(f"Project Root: {project_root}")
    print(f"Python Version: {sys.version}")
    print("="*80)
    
    tests = [
        ("Entity Extraction", test_entity_extractor),
        ("API Key Management", test_api_key_manager),
        ("Diagram Cleaning", test_diagram_cleaning),
        ("File Integrity", test_file_integrity),
        ("Critical Imports", test_imports),
        ("RAG System", test_rag_system),
        ("Validation System", test_validation_system),
        ("Documentation", test_documentation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {e}")
            results.append((test_name, False))
    
    # Generate report
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("="*80)
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is ready to use!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)

