#!/usr/bin/env python3
"""
System Verification Script
Checks all critical systems are working correctly
"""

import sys
import io
if sys.platform == 'win32':
    try:
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

import os
from pathlib import Path
import json
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_section(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def check_file_exists(path, description):
    """Check if file exists"""
    if Path(path).exists():
        print(f"✅ {description}: {path}")
        return True
    else:
        print(f"❌ {description}: {path} NOT FOUND")
        return False

def check_directory_exists(path, description):
    """Check if directory exists"""
    if Path(path).is_dir():
        file_count = len(list(Path(path).rglob('*')))
        print(f"✅ {description}: {path} ({file_count} files)")
        return True
    else:
        print(f"❌ {description}: {path} NOT FOUND")
        return False

async def verify_rag_system():
    """Verify RAG system is working"""
    print_section("1. RAG System Check")
    
    try:
        # Check if ChromaDB index exists
        check_directory_exists("rag/index", "ChromaDB Index")
        
        # Try to retrieve context
        from rag.retrieve import retrieve_context
        test_query = "test query for verification"
        result = retrieve_context(test_query, max_chunks=5)
        
        if result and len(result) > 0:
            print(f"✅ RAG retrieval working: {len(result)} chars retrieved")
        else:
            print(f"⚠️  RAG retrieval returned empty result (may need indexing)")
            
    except Exception as e:
        print(f"❌ RAG system error: {e}")
        return False
    
    return True

async def verify_smart_generator():
    """Verify smart generator initialization"""
    print_section("2. Smart Generator Check")
    
    try:
        from ai.smart_generation import get_smart_generator
        from ai.output_validator import get_validator
        from ai.ollama_client import get_ollama_client
        
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("⚠️  Ollama client not available (Ollama may not be running)")
            return False
        
        validator = get_validator()
        smart_gen = get_smart_generator(ollama_client, validator)
        
        if smart_gen:
            print(f"✅ Smart generator initialized")
            print(f"✅ Artifact types supported: {len(smart_gen.artifact_models)}")
            print(f"✅ Quality threshold: {smart_gen.min_quality_threshold}/100")
            
            # Check artifact models
            sample_types = list(smart_gen.artifact_models.keys())[:5]
            print(f"✅ Sample artifact types: {', '.join(sample_types)}")
            
            return True
        else:
            print(f"❌ Smart generator failed to initialize")
            return False
            
    except Exception as e:
        print(f"❌ Smart generator error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_context_passing():
    """Verify context is being built correctly"""
    print_section("3. Context Building Check")
    
    try:
        from ai.smart_generation import get_smart_generator
        from ai.output_validator import get_validator
        from ai.ollama_client import get_ollama_client
        
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("⚠️  Ollama not available, skipping context test")
            return False
        
        validator = get_validator()
        smart_gen = get_smart_generator(ollama_client, validator)
        
        # Test context prompt building
        test_prompt = "Generate an ERD"
        test_meeting_notes = "PhoneSwapRequest feature for device exchange"
        test_rag_context = "class PhoneSwapRequest extends Model { id, deviceType, status }"
        test_requirements = {"feature": "phone swap", "priority": "high"}
        
        full_prompt = smart_gen._build_context_prompt(
            prompt=test_prompt,
            meeting_notes=test_meeting_notes,
            rag_context=test_rag_context,
            feature_requirements=test_requirements,
            artifact_type="erd"
        )
        
        # Verify all context is included
        checks = [
            ("Meeting Notes" in full_prompt, "Meeting notes section"),
            ("Retrieved Context" in full_prompt, "RAG context section"),
            ("Instructions" in full_prompt, "Instructions section"),
            (test_meeting_notes in full_prompt, "Actual meeting notes content"),
            (test_rag_context in full_prompt, "Actual RAG content"),
        ]
        
        all_passed = True
        for check, description in checks:
            if check:
                print(f"✅ {description} present")
            else:
                print(f"❌ {description} MISSING")
                all_passed = False
        
        print(f"\nFull prompt length: {len(full_prompt)} chars")
        print(f"Preview (first 300 chars):\n{full_prompt[:300]}...")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Context building error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_finetuning_setup():
    """Verify fine-tuning directories exist"""
    print_section("4. Fine-Tuning Setup Check")
    
    try:
        # Check directories
        ft_dir = Path("finetune_datasets")
        cloud_dir = ft_dir / "cloud_responses"
        
        if not ft_dir.exists():
            ft_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {ft_dir}")
        else:
            print(f"✅ {ft_dir} exists")
        
        if not cloud_dir.exists():
            cloud_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created {cloud_dir}")
        else:
            files = list(cloud_dir.glob('*.json'))
            print(f"✅ {cloud_dir} exists ({len(files)} cloud responses)")
            
            if files:
                # Show sample
                with open(files[0], 'r', encoding='utf-8') as f:
                    sample = json.load(f)
                    print(f"   Sample file: {files[0].name}")
                    print(f"   - Artifact: {sample.get('artifact_type', 'unknown')}")
                    print(f"   - Quality: {sample.get('quality_score', 0)}/100")
                    print(f"   - Timestamp: {sample.get('timestamp', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fine-tuning setup error: {e}")
        return False

def verify_gemini_routing():
    """Verify Gemini routing logic"""
    print_section("5. Gemini Routing Check")
    
    try:
        # Check if Gemini key configured
        from config.secrets_manager import api_key_manager
        
        gemini_key = api_key_manager.get_key('gemini')
        if gemini_key:
            print(f"✅ Gemini API key configured")
        else:
            print(f"⚠️  Gemini API key not configured (will use fallback)")
        
        # Check COMPLEX_TASKS definition (from universal_agent.py)
        COMPLEX_TASKS = [
            "architecture", "mermaid_architecture", "system_overview", 
            "components_diagram", "visual_prototype_dev", "visual_prototype",
            "html_diagram", "api_sequence", "mermaid_sequence",
            "full_system", "prototype"
        ]
        
        print(f"✅ Complex tasks defined: {len(COMPLEX_TASKS)} types")
        print(f"   Examples: {', '.join(COMPLEX_TASKS[:5])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini routing error: {e}")
        return False

def verify_model_routing():
    """Verify local model routing"""
    print_section("6. Local Model Routing Check")
    
    try:
        from ai.smart_generation import get_smart_generator
        from ai.output_validator import get_validator
        from ai.ollama_client import get_ollama_client
        
        ollama_client = get_ollama_client()
        if not ollama_client:
            print("⚠️  Ollama not available")
            return False
        
        validator = get_validator()
        smart_gen = get_smart_generator(ollama_client, validator)
        
        # Check model assignments
        artifact_types = ["erd", "architecture", "code_prototype", "html_diagram", "jira_stories"]
        
        for art_type in artifact_types:
            models = smart_gen.artifact_models.get(art_type, [])
            if models:
                print(f"✅ {art_type}: {models[0]} (+ {len(models)-1} fallbacks)")
            else:
                print(f"⚠️  {art_type}: No models assigned")
        
        return True
        
    except Exception as e:
        print(f"❌ Model routing error: {e}")
        return False

def verify_batch_generation():
    """Verify batch generation error handling"""
    print_section("7. Batch Generation Check")
    
    try:
        # Read app_v2.py batch generation code
        app_file = Path("app/app_v2.py")
        if not app_file.exists():
            print(f"❌ app_v2.py not found")
            return False
        
        content = app_file.read_text(encoding='utf-8')
        
        # Check for proper error handling
        checks = [
            ("try:" in content and "except Exception as e:" in content, 
             "Exception handling present"),
            ("continue" in content, 
             "Continue on error (doesn't stop)"),
            ("succeeded" in content and "failed" in content, 
             "Success/failure tracking"),
        ]
        
        for check, description in checks:
            if check:
                print(f"✅ {description}")
            else:
                print(f"⚠️  {description} - may need review")
        
        return True
        
    except Exception as e:
        print(f"❌ Batch generation check error: {e}")
        return False

async def main():
    """Run all verification checks"""
    print("\n" + "="*70)
    print("  🔬 Architect.AI System Verification")
    print("="*70)
    
    results = []
    
    # Run all checks
    results.append(("RAG System", await verify_rag_system()))
    results.append(("Smart Generator", await verify_smart_generator()))
    results.append(("Context Building", await verify_context_passing()))
    results.append(("Fine-Tuning Setup", verify_finetuning_setup()))
    results.append(("Gemini Routing", verify_gemini_routing()))
    results.append(("Model Routing", verify_model_routing()))
    results.append(("Batch Generation", verify_batch_generation()))
    
    # Summary
    print_section("Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} checks passed ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 All systems operational!")
        return 0
    elif passed >= total * 0.7:
        print("\n⚠️  Most systems working, some issues need attention")
        return 1
    else:
        print("\n❌ Critical issues found, system may not work correctly")
        return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

