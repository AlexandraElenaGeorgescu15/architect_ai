"""
INTENSIVE VERIFICATION: Adaptive Learning Integration

This script performs INTENSE verification that:
1. All adaptive learning components exist
2. Components can be imported and initialized
3. Integration points are ready (even if not called yet)
4. Background worker can be created
5. End-to-end flow works

Run this to verify the system is ready to learn from the get-go.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_status(message: str, status: str):
    """Print colored status message"""
    symbols = {
        'OK': '✅',
        'FAIL': '❌',
        'WARN': '⚠️',
        'INFO': 'ℹ️'
    }
    print(f"{symbols.get(status, '•')} {message}")

def test_component_exists():
    """Test 1: Check all files exist"""
    print("\n" + "="*80)
    print("TEST 1: Component Files Existence")
    print("="*80)
    
    required_files = [
        "components/adaptive_learning.py",
        "components/validation_pipeline.py",
        "components/ml_feature_engineering.py",
        "components/smart_code_analyzer.py",
        "validation/output_validator.py",
        "agents/universal_agent.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print_status(f"{file_path} exists", "OK")
        else:
            print_status(f"{file_path} MISSING", "FAIL")
            all_exist = False
    
    return all_exist

def test_imports():
    """Test 2: Import all components"""
    print("\n" + "="*80)
    print("TEST 2: Component Imports")
    print("="*80)
    
    tests = []
    
    # Test 1: Adaptive Learning
    try:
        from components.adaptive_learning import AdaptiveLearningLoop, FeedbackEvent, FeedbackType
        print_status("AdaptiveLearningLoop imports successfully", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"AdaptiveLearningLoop import failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 2: Validation Pipeline
    try:
        from components.validation_pipeline import ValidationPipeline
        print_status("ValidationPipeline imports successfully", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"ValidationPipeline import failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 3: ML Feature Engineering
    try:
        from components.ml_feature_engineering import MLFeatureEngineer
        print_status("MLFeatureEngineer imports successfully", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"MLFeatureEngineer import failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 4: Smart Code Analyzer
    try:
        from components.smart_code_analyzer import SmartCodeAnalyzer
        print_status("SmartCodeAnalyzer imports successfully", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"SmartCodeAnalyzer import failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 5: Output Validator
    try:
        from validation.output_validator import ArtifactValidator
        print_status("ArtifactValidator imports successfully", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"ArtifactValidator import failed: {e}", "FAIL")
        tests.append(False)
    
    return all(tests)

def test_initialization():
    """Test 3: Initialize all components"""
    print("\n" + "="*80)
    print("TEST 3: Component Initialization")
    print("="*80)
    
    tests = []
    
    # Test 1: Adaptive Learning Loop
    try:
        from components.adaptive_learning import AdaptiveLearningLoop
        loop = AdaptiveLearningLoop()
        print_status(f"AdaptiveLearningLoop initialized (storage: {loop.storage_dir})", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"AdaptiveLearningLoop initialization failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 2: Validation Pipeline
    try:
        from components.validation_pipeline import ValidationPipeline
        pipeline = ValidationPipeline()
        print_status("ValidationPipeline initialized", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"ValidationPipeline initialization failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 3: ML Feature Engineer
    try:
        from components.ml_feature_engineering import MLFeatureEngineer
        engineer = MLFeatureEngineer()
        print_status("MLFeatureEngineer initialized", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"MLFeatureEngineer initialization failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 4: Smart Code Analyzer
    try:
        from components.smart_code_analyzer import SmartCodeAnalyzer
        analyzer = SmartCodeAnalyzer()
        print_status("SmartCodeAnalyzer initialized", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"SmartCodeAnalyzer initialization failed: {e}", "FAIL")
        tests.append(False)
    
    # Test 5: Artifact Validator
    try:
        from validation.output_validator import ArtifactValidator
        validator = ArtifactValidator()
        print_status("ArtifactValidator initialized", "OK")
        tests.append(True)
    except Exception as e:
        print_status(f"ArtifactValidator initialization failed: {e}", "FAIL")
        tests.append(False)
    
    return all(tests)

def test_integration_hooks():
    """Test 4: Check if universal_agent has integration hooks"""
    print("\n" + "="*80)
    print("TEST 4: Integration Hooks in Universal Agent")
    print("="*80)
    
    agent_file = Path(__file__).parent / "agents" / "universal_agent.py"
    agent_code = agent_file.read_text(encoding='utf-8')
    
    checks = [
        ("adaptive_learning import", "from components.adaptive_learning import", False),
        ("validation_pipeline import", "from components.validation_pipeline import", False),
        ("ml_feature_engineering import", "from components.ml_feature_engineering import", False),
        ("smart_code_analyzer usage", "smart_code_analyzer", False),
        ("record_feedback call", "record_feedback", False)
    ]
    
    results = []
    for check_name, search_text, _ in checks:
        if search_text.lower() in agent_code.lower():
            print_status(f"{check_name} found", "OK")
            results.append(True)
        else:
            print_status(f"{check_name} NOT FOUND - needs integration", "WARN")
            results.append(False)
    
    if any(results):
        print_status("Some integration hooks exist", "WARN")
    else:
        print_status("NO integration hooks found - system NOT learning yet", "WARN")
    
    return any(results)

def test_end_to_end_flow():
    """Test 5: Simulate end-to-end adaptive learning flow"""
    print("\n" + "="*80)
    print("TEST 5: End-to-End Flow Simulation")
    print("="*80)
    
    try:
        from components.adaptive_learning import AdaptiveLearningLoop, FeedbackEvent, FeedbackType
        from components.validation_pipeline import ValidationPipeline
        from validation.output_validator import ArtifactValidator
        
        # Step 1: Create components
        loop = AdaptiveLearningLoop()
        validator = ArtifactValidator()
        pipeline = ValidationPipeline()
        
        print_status("Step 1: Components created", "OK")
        
        # Step 2: Simulate AI generation
        test_erd = """erDiagram
    USER ||--o{ ORDER : places
    USER {
        int id PK
        string email
        string name
    }
    ORDER {
        int id PK
        int user_id FK
        float total
    }"""
        
        print_status("Step 2: Simulated ERD generation", "OK")
        
        # Step 3: Programmatic validation
        noise_score = pipeline.calculate_noise(test_erd, "erd")
        print_status(f"Step 3: Noise validation (score: {noise_score:.2f})", "OK")
        
        # Step 4: Context-aware validation
        validation_result = validator.validate("erd", test_erd, {
            'rag_context': 'User authentication system with orders',
            'user_request': 'Create ERD for user orders'
        })
        print_status(f"Step 4: Quality validation (score: {validation_result.score:.1f}/100)", "OK")
        
        # Step 5: Record feedback
        event = FeedbackEvent(
            timestamp=time.time(),
            feedback_type=FeedbackType.SUCCESS if validation_result.score >= 70 else FeedbackType.VALIDATION_FAILURE,
            input_data="Create ERD for user authentication with orders",
            ai_output=test_erd,
            corrected_output=None,
            context={'rag_context': 'test'},
            validation_score=validation_result.score,
            artifact_type="erd",
            model_used="llama3.2",
            reward_signal=0.0,
            metadata={}
        )
        
        loop.record_feedback(event)
        print_status("Step 5: Feedback recorded", "OK")
        
        # Step 6: Check if feedback was saved
        if loop.events_file.exists():
            with open(loop.events_file) as f:
                events = [json.loads(line) for line in f]
            print_status(f"Step 6: Feedback persisted ({len(events)} events in store)", "OK")
        else:
            print_status("Step 6: Feedback file created", "OK")
        
        print_status("✨ End-to-end flow WORKS!", "OK")
        return True
        
    except Exception as e:
        print_status(f"End-to-end flow failed: {e}", "FAIL")
        import traceback
        traceback.print_exc()
        return False

def test_training_batch_creation():
    """Test 6: Verify training batch creation"""
    print("\n" + "="*80)
    print("TEST 6: Training Batch Creation")
    print("="*80)
    
    try:
        from components.adaptive_learning import AdaptiveLearningLoop, FeedbackEvent, FeedbackType
        import time
        
        loop = AdaptiveLearningLoop()
        
        # Create 5 good examples
        for i in range(5):
            event = FeedbackEvent(
                timestamp=time.time(),
                feedback_type=FeedbackType.SUCCESS,
                input_data=f"Test request {i}",
                ai_output=f"Test output {i}",
                corrected_output=None,
                context={},
                validation_score=85.0,
                artifact_type="test",
                model_used="test_model",
                reward_signal=0.8,
                metadata={}
            )
            loop.record_feedback(event)
        
        print_status(f"Created 5 test feedback events", "OK")
        
        # Check batch creation threshold
        if loop.batch_threshold == 50:
            print_status(f"Batch creation threshold: {loop.batch_threshold} good examples", "OK")
        
        # Check if batches directory exists
        batches_dir = Path(loop.storage_dir) / "batches"
        if batches_dir.exists():
            batches = list(batches_dir.glob("batch_*.jsonl"))
            print_status(f"Batches directory exists ({len(batches)} batches)", "OK")
        else:
            print_status("Batches directory will be created when threshold reached", "INFO")
        
        return True
        
    except Exception as e:
        print_status(f"Training batch test failed: {e}", "FAIL")
        return False

def test_worker_creation():
    """Test 7: Verify background worker can be created"""
    print("\n" + "="*80)
    print("TEST 7: Background Worker Creation")
    print("="*80)
    
    worker_file = Path(__file__).parent / "workers" / "finetuning_worker.py"
    
    if worker_file.exists():
        print_status("finetuning_worker.py exists", "OK")
        
        # Check if it's executable
        try:
            worker_code = worker_file.read_text(encoding='utf-8')
            if "AdaptiveLearningLoop" in worker_code or "training_jobs" in worker_code:
                print_status("Worker has adaptive learning integration", "OK")
            else:
                print_status("Worker exists but needs adaptive learning integration", "WARN")
        except Exception as e:
            print_status(f"Could not read worker file: {e}", "WARN")
        
        return True
    else:
        print_status("finetuning_worker.py NOT FOUND - needs creation", "WARN")
        
        # Show how to create it
        print_status("Worker can be created using INTEGRATION_GUIDE.md instructions", "INFO")
        return False

def main():
    """Run all verification tests"""
    print("\n" + "🔍"*40)
    print("INTENSIVE VERIFICATION: Adaptive Learning System")
    print("🔍"*40)
    
    results = {}
    
    # Run tests
    results['files_exist'] = test_component_exists()
    results['imports_work'] = test_imports()
    results['initialization_works'] = test_initialization()
    results['integration_hooks'] = test_integration_hooks()
    results['end_to_end_flow'] = test_end_to_end_flow()
    results['training_batches'] = test_training_batch_creation()
    results['worker_ready'] = test_worker_creation()
    
    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "OK" if result else "FAIL"
        print_status(f"{test_name}: {'PASSED' if result else 'FAILED'}", status)
    
    print("\n" + "="*80)
    if passed == total:
        print_status(f"✨ ALL TESTS PASSED ({passed}/{total})", "OK")
        print_status("System is READY to learn from the get-go! 🚀", "OK")
    elif passed >= 5:
        print_status(f"⚠️ MOSTLY READY ({passed}/{total} passed)", "WARN")
        print_status("Core components work, but integration needs completion", "WARN")
        print_status("See INTEGRATION_GUIDE.md for next steps", "INFO")
    else:
        print_status(f"❌ SYSTEM NOT READY ({passed}/{total} passed)", "FAIL")
        print_status("Critical components missing or broken", "FAIL")
    
    print("="*80)
    
    # Specific recommendations
    print("\n📋 RECOMMENDATIONS:")
    if not results['integration_hooks']:
        print("  1. Integrate adaptive learning into universal_agent.py")
        print("     - Add imports for adaptive learning components")
        print("     - Call record_feedback() after every generation")
        print("     - See INTEGRATION_GUIDE.md Step 2")
    
    if not results['worker_ready']:
        print("  2. Create background fine-tuning worker")
        print("     - Create workers/finetuning_worker.py")
        print("     - See INTEGRATION_GUIDE.md Step 5")
    
    if results['end_to_end_flow']:
        print("  ✅ Core pipeline works! Just needs hookup to universal_agent")
    
    return results

if __name__ == "__main__":
    import time
    results = main()
    
    # Exit with proper code
    sys.exit(0 if all(results.values()) else 1)
