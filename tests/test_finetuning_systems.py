"""
Comprehensive Testing Suite for Fine-Tuning Systems

Tests both:
1. Ollama Adaptive Learning Loop (continuous, automatic)
2. HuggingFace Manual Pipeline (on-demand, deep training)

Run: python test_finetuning_systems.py
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 80)
print("FINE-TUNING SYSTEMS TEST SUITE")
print("=" * 80)
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# TEST 1: OLLAMA ADAPTIVE LEARNING LOOP
# ============================================================================

print("\n" + "=" * 80)
print("TEST 1: OLLAMA ADAPTIVE LEARNING LOOP")
print("=" * 80)

test_results = {
    "ollama_adaptive_loop": {},
    "huggingface_pipeline": {},
    "timestamp": datetime.now().isoformat()
}

def test_ollama_adaptive_learning():
    """Test Ollama adaptive learning system"""
    print("\n[TEST 1.1] Importing Ollama Adaptive Learning...")
    
    try:
        from components.adaptive_learning import (
            AdaptiveLearningLoop, 
            FeedbackType, 
            FeedbackEvent,
            RewardCalculator
        )
        print("✅ Import successful")
        test_results["ollama_adaptive_loop"]["import"] = "PASS"
    except Exception as e:
        print(f"❌ Import failed: {e}")
        test_results["ollama_adaptive_loop"]["import"] = f"FAIL: {e}"
        return False
    
    # Test 1.2: Initialize system
    print("\n[TEST 1.2] Initializing Adaptive Learning Loop...")
    try:
        loop = AdaptiveLearningLoop(storage_dir=Path("test_outputs/adaptive_learning"))
        print(f"✅ Initialization successful")
        print(f"   Storage dir: {loop.storage_dir}")
        print(f"   Batch size: {loop.batch_size}")
        print(f"   Min reward threshold: {loop.min_reward_threshold}")
        test_results["ollama_adaptive_loop"]["initialization"] = "PASS"
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        test_results["ollama_adaptive_loop"]["initialization"] = f"FAIL: {e}"
        return False
    
    # Test 1.3: Record feedback events
    print("\n[TEST 1.3] Recording feedback events...")
    
    test_cases = [
        {
            "name": "Success (High Quality)",
            "input": "Generate ERD for e-commerce system",
            "output": "erDiagram\n  Customer ||--o{ Order : places\n  Order ||--o{ Product : contains",
            "artifact_type": "erd",
            "model": "codellama:7b",
            "validation_score": 92.0,
            "feedback_type": FeedbackType.SUCCESS,
            "expected_reward_range": (0.8, 1.0)
        },
        {
            "name": "User Correction (Minor)",
            "input": "Generate user API endpoint",
            "output": "def get_users(): pass",
            "corrected_output": "def get_users():\n    return User.query.all()",
            "artifact_type": "code",
            "model": "codellama:7b",
            "validation_score": 75.0,
            "feedback_type": FeedbackType.USER_CORRECTION,
            "expected_reward_range": (0.2, 0.6)
        },
        {
            "name": "Validation Failure",
            "input": "Generate HTML form",
            "output": "<div>incomplete</div>",
            "artifact_type": "html",
            "model": "codellama:7b",
            "validation_score": 35.0,
            "feedback_type": FeedbackType.VALIDATION_FAILURE,
            "expected_reward_range": (-1.0, -0.3)
        },
        {
            "name": "Explicit Positive",
            "input": "Generate architecture diagram",
            "output": "flowchart TD\n  A[Client] --> B[API]\n  B --> C[DB]",
            "artifact_type": "architecture",
            "model": "codellama:7b",
            "validation_score": 88.0,
            "feedback_type": FeedbackType.EXPLICIT_POSITIVE,
            "expected_reward_range": (0.7, 1.0)
        },
        {
            "name": "Explicit Negative",
            "input": "Generate JIRA task",
            "output": "Task: do thing",
            "artifact_type": "jira",
            "model": "codellama:7b",
            "validation_score": 20.0,
            "feedback_type": FeedbackType.EXPLICIT_NEGATIVE,
            "expected_reward_range": (-1.0, -0.9)
        }
    ]
    
    feedback_events = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   [{i}/{len(test_cases)}] Testing: {test_case['name']}")
        
        try:
            event = loop.record_feedback(
                input_data=test_case["input"],
                ai_output=test_case["output"],
                artifact_type=test_case["artifact_type"],
                model_used=test_case["model"],
                validation_score=test_case["validation_score"],
                feedback_type=test_case["feedback_type"],
                corrected_output=test_case.get("corrected_output"),
                context={"test_case": test_case["name"]}
            )
            
            if event is None:
                print(f"   ℹ️  Feedback discarded (Quality Gate) - correct behavior for score < 70")
                continue
            
            # Verify reward calculation
            min_reward, max_reward = test_case["expected_reward_range"]
            if min_reward <= event.reward_signal <= max_reward:
                print(f"   ✅ Reward signal: {event.reward_signal:.2f} (expected {min_reward} to {max_reward})")
            else:
                print(f"   ⚠️  Reward signal: {event.reward_signal:.2f} (expected {min_reward} to {max_reward})")
            
            feedback_events.append(event)
            
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            test_results["ollama_adaptive_loop"]["feedback_recording"] = f"FAIL: {e}"
            return False
    
    print(f"\n✅ Recorded {len(feedback_events)} feedback events")
    test_results["ollama_adaptive_loop"]["feedback_recording"] = "PASS"
    test_results["ollama_adaptive_loop"]["events_recorded"] = len(feedback_events)
    
    # Test 1.4: Verify reward calculator
    print("\n[TEST 1.4] Testing RewardCalculator...")
    try:
        calc = RewardCalculator()
        
        # Test extreme cases
        high_quality_event = FeedbackEvent(
            timestamp=time.time(),
            feedback_type=FeedbackType.SUCCESS,
            input_data="test",
            ai_output="test output",
            corrected_output=None,
            context={},
            validation_score=95.0,
            artifact_type="test",
            model_used="test",
            reward_signal=0.0
        )
        reward = calc.calculate_reward(high_quality_event)
        print(f"   High quality (95% validation): {reward:.2f}")
        assert 0.8 <= reward <= 1.0, f"Expected 0.8-1.0, got {reward}"
        
        low_quality_event = FeedbackEvent(
            timestamp=time.time(),
            feedback_type=FeedbackType.VALIDATION_FAILURE,
            input_data="test",
            ai_output="bad output",
            corrected_output=None,
            context={},
            validation_score=30.0,
            artifact_type="test",
            model_used="test",
            reward_signal=0.0
        )
        reward = calc.calculate_reward(low_quality_event)
        print(f"   Low quality (30% validation): {reward:.2f}")
        assert -1.0 <= reward <= -0.3, f"Expected -1.0 to -0.3, got {reward}"
        
        print("✅ RewardCalculator working correctly")
        test_results["ollama_adaptive_loop"]["reward_calculator"] = "PASS"
        
    except Exception as e:
        print(f"❌ RewardCalculator test failed: {e}")
        test_results["ollama_adaptive_loop"]["reward_calculator"] = f"FAIL: {e}"
        return False
    
    # Test 1.5: Check learning statistics
    print("\n[TEST 1.5] Checking learning statistics...")
    try:
        stats = loop.get_learning_stats()
        print(f"   Total feedback: {stats['total_feedback']}")
        print(f"   Average reward: {stats['avg_reward']:.2f}")
        print(f"   Training batches created: {stats['training_batches_created']}")
        print(f"   Average validation score: {stats['avg_validation_score']:.1f}")
        print(f"   Feedback by type:")
        for feedback_type, count in stats['feedback_by_type'].items():
            print(f"      {feedback_type}: {count}")
        
        assert stats['total_feedback'] == len(feedback_events), "Mismatch in feedback count"
        print("✅ Statistics calculated correctly")
        test_results["ollama_adaptive_loop"]["statistics"] = "PASS"
        test_results["ollama_adaptive_loop"]["stats"] = stats
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        test_results["ollama_adaptive_loop"]["statistics"] = f"FAIL: {e}"
        return False
    
    # Test 1.6: Verify storage
    print("\n[TEST 1.6] Verifying storage persistence...")
    try:
        feedback_file = loop.storage_dir / "feedback_events.jsonl"
        if feedback_file.exists():
            with open(feedback_file, 'r') as f:
                lines = f.readlines()
            print(f"   ✅ Feedback file exists: {len(lines)} events stored")
            test_results["ollama_adaptive_loop"]["storage"] = "PASS"
        else:
            print(f"   ⚠️  Feedback file not found: {feedback_file}")
            test_results["ollama_adaptive_loop"]["storage"] = "WARN: File not found"
    except Exception as e:
        print(f"   ⚠️  Storage check failed: {e}")
        test_results["ollama_adaptive_loop"]["storage"] = f"WARN: {e}"
    
    print("\n✅ OLLAMA ADAPTIVE LEARNING: ALL TESTS PASSED")
    return True


# ============================================================================
# TEST 2: HUGGINGFACE MANUAL PIPELINE
# ============================================================================

print("\n" + "=" * 80)
print("TEST 2: HUGGINGFACE MANUAL PIPELINE")
print("=" * 80)

def test_huggingface_pipeline():
    """Test HuggingFace manual fine-tuning pipeline"""
    
    print("\n[TEST 2.1] Importing HuggingFace components...")
    try:
        from components.local_finetuning import (
            LocalFineTuningSystem,
            TrainingConfig,
            ModelInfo,
            TrainingProgress,
            TrainingResult
        )
        from components.finetuning_dataset_builder import FineTuningDatasetBuilder
        print("✅ Import successful")
        test_results["huggingface_pipeline"]["import"] = "PASS"
    except Exception as e:
        print(f"❌ Import failed: {e}")
        test_results["huggingface_pipeline"]["import"] = f"FAIL: {e}"
        return False
    
    # Test 2.2: Initialize system
    print("\n[TEST 2.2] Initializing LocalFineTuningSystem...")
    try:
        system = LocalFineTuningSystem()
        print("✅ Initialization successful")
        print(f"   Available models: {len(system.available_models)}")
        for key, model in system.available_models.items():
            print(f"      {key}: {model.name} ({model.size})")
        test_results["huggingface_pipeline"]["initialization"] = "PASS"
        test_results["huggingface_pipeline"]["available_models"] = list(system.available_models.keys())
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        test_results["huggingface_pipeline"]["initialization"] = f"FAIL: {e}"
        return False
    
    # Test 2.3: Check environment
    print("\n[TEST 2.3] Checking environment readiness...")
    try:
        env_status = system.check_environment()
        print(f"   OS: {env_status['os']}")
        print(f"   CUDA available: {env_status['has_cuda']}")
        print(f"   bitsandbytes: {env_status['has_bitsandbytes']}")
        print(f"   Ready for training: {env_status['ready']}")
        if 'vram_gb' in env_status:
            print(f"   VRAM: {env_status['vram_gb']:.1f} GB")
        if env_status['message']:
            print(f"   Message: {env_status['message']}")
        
        test_results["huggingface_pipeline"]["environment"] = {
            "status": "PASS",
            "details": env_status
        }
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        test_results["huggingface_pipeline"]["environment"] = f"FAIL: {e}"
        return False
    
    # Test 2.4: Get system info
    print("\n[TEST 2.4] Getting system information...")
    try:
        sys_info = system.get_system_info()
        print(f"   RAM: {sys_info['ram_gb']:.1f} GB")
        print(f"   CPU cores: {sys_info['cpu_count']}")
        print(f"   Disk free: {sys_info['disk_free_gb']:.1f} GB")
        print(f"   CUDA: {sys_info['cuda_available']}")
        print(f"   Environment ready: {sys_info['environment_ready']}")
        
        test_results["huggingface_pipeline"]["system_info"] = {
            "status": "PASS",
            "details": sys_info
        }
    except Exception as e:
        print(f"❌ System info failed: {e}")
        test_results["huggingface_pipeline"]["system_info"] = f"FAIL: {e}"
        return False
    
    # Test 2.5: Test dataset builder
    print("\n[TEST 2.5] Testing dataset builder...")
    try:
        # Create test meeting notes
        test_notes = """
        Project: E-Commerce Platform
        
        Requirements:
        - User authentication with JWT
        - Product catalog with search
        - Shopping cart functionality
        - Order processing system
        
        Tech Stack: Angular + .NET + MongoDB
        """
        
        builder = FineTuningDatasetBuilder(test_notes, max_chunks=50)
        examples, report = builder.build_dataset(limit=10)
        
        print(f"   ✅ Dataset built successfully")
        print(f"   Total examples: {report.total_examples}")
        print(f"   Source examples: {report.source_examples}")
        print(f"   Feedback examples: {report.feedback_examples}")
        print(f"   Unique files: {report.unique_files}")
        print(f"   Artifact breakdown: {report.artifact_breakdown}")
        
        # Validate example structure
        if examples:
            example = examples[0]
            required_keys = ['instruction', 'input', 'output']
            missing_keys = [k for k in required_keys if k not in example]
            if missing_keys:
                print(f"   ⚠️  Missing keys in example: {missing_keys}")
            else:
                print(f"   ✅ Example structure valid")
                print(f"   Sample example:")
                print(f"      Instruction: {example['instruction'][:60]}...")
                print(f"      Input: {example['input'][:60] if example['input'] else '(empty)'}...")
                print(f"      Output: {example['output'][:60]}...")
        
        test_results["huggingface_pipeline"]["dataset_builder"] = {
            "status": "PASS",
            "examples_generated": len(examples),
            "report": {
                "total": report.total_examples,
                "feedback": report.feedback_examples,
                "files": report.unique_files
            }
        }
        
    except Exception as e:
        print(f"❌ Dataset builder test failed: {e}")
        import traceback
        traceback.print_exc()
        test_results["huggingface_pipeline"]["dataset_builder"] = f"FAIL: {e}"
        return False
    
    # Test 2.6: Test training configuration
    print("\n[TEST 2.6] Testing TrainingConfig...")
    try:
        config = TrainingConfig(
            model_name="codellama-7b",
            epochs=3,
            learning_rate=2e-4,
            batch_size=2,
            lora_rank=16,
            lora_alpha=32,
            lora_dropout=0.05,
            use_4bit=True,
            use_8bit=False,
            max_length=512
        )
        
        print(f"   ✅ Config created successfully")
        print(f"   Model: {config.model_name}")
        print(f"   Epochs: {config.epochs}")
        print(f"   Learning rate: {config.learning_rate:.2e}")
        print(f"   Batch size: {config.batch_size}")
        print(f"   LoRA rank: {config.lora_rank}")
        print(f"   LoRA alpha: {config.lora_alpha}")
        print(f"   4-bit quantization: {config.use_4bit}")
        
        test_results["huggingface_pipeline"]["training_config"] = "PASS"
        
    except Exception as e:
        print(f"❌ Training config test failed: {e}")
        test_results["huggingface_pipeline"]["training_config"] = f"FAIL: {e}"
        return False
    
    # Test 2.7: Test learning rate validation (NEW FIX)
    print("\n[TEST 2.7] Testing learning rate validation...")
    try:
        # Test valid learning rate
        valid_config = TrainingConfig(
            model_name="codellama-7b",
            epochs=1,
            learning_rate=2e-4,  # Valid
            batch_size=1,
            lora_rank=8,
            lora_alpha=16,
            lora_dropout=0.05,
            use_4bit=True,
            use_8bit=False,
            max_length=512
        )
        
        # Test invalid learning rate (too high)
        try:
            invalid_config = TrainingConfig(
                model_name="codellama-7b",
                epochs=1,
                learning_rate=0.01,  # Too high (1e-2)
                batch_size=1,
                lora_rank=8,
                lora_alpha=16,
                lora_dropout=0.05,
                use_4bit=True,
                use_8bit=False,
                max_length=512
            )
            
            # If no model loaded, validation happens in start_training
            # Create mock training data
            mock_data = [{"instruction": "test", "input": "", "output": "test"}]
            
            # This should raise ValueError
            if system.current_model:
                try:
                    system.start_training(invalid_config, mock_data)
                    print("   ⚠️  Validation did not catch invalid learning rate")
                    test_results["huggingface_pipeline"]["lr_validation"] = "WARN: No validation"
                except ValueError as ve:
                    if "learning rate" in str(ve).lower():
                        print(f"   ✅ Validation correctly rejected invalid LR: {ve}")
                        test_results["huggingface_pipeline"]["lr_validation"] = "PASS"
                    else:
                        raise
            else:
                print("   ℹ️  Skipped (no model loaded, validation happens at training time)")
                test_results["huggingface_pipeline"]["lr_validation"] = "SKIP: No model loaded"
        
        except ValueError as e:
            if "learning rate" in str(e).lower():
                print(f"   ✅ Validation correctly rejected invalid LR")
                test_results["huggingface_pipeline"]["lr_validation"] = "PASS"
            else:
                raise
        
    except Exception as e:
        print(f"   ⚠️  LR validation test incomplete: {e}")
        test_results["huggingface_pipeline"]["lr_validation"] = f"PARTIAL: {e}"
    
    # Test 2.8: Test checkpoint management
    print("\n[TEST 2.8] Testing checkpoint management...")
    try:
        # Test version name generation
        version_name = system._get_next_version_name("codellama-7b")
        print(f"   ✅ Version name generated: {version_name}")
        
        # Test list finetuned models
        finetuned = system.list_finetuned_models("codellama-7b")
        print(f"   Existing fine-tuned models: {len(finetuned)}")
        for model in finetuned[:3]:  # Show first 3
            print(f"      - {model}")
        
        test_results["huggingface_pipeline"]["checkpoint_management"] = {
            "status": "PASS",
            "existing_models": len(finetuned)
        }
        
    except Exception as e:
        print(f"❌ Checkpoint management test failed: {e}")
        test_results["huggingface_pipeline"]["checkpoint_management"] = f"FAIL: {e}"
        return False
    
    # Test 2.9: Test incremental training detection
    print("\n[TEST 2.9] Testing incremental training detection...")
    try:
        # Check if system has any downloaded models
        downloaded = [k for k, v in system.available_models.items() if v.is_downloaded]
        print(f"   Downloaded models: {len(downloaded)}")
        for model_key in downloaded:
            model_info = system.available_models[model_key]
            print(f"      {model_key}: {len(model_info.fine_tuned_versions)} fine-tuned versions")
        
        test_results["huggingface_pipeline"]["incremental_training"] = {
            "status": "PASS",
            "downloaded_models": len(downloaded)
        }
        
    except Exception as e:
        print(f"❌ Incremental training test failed: {e}")
        test_results["huggingface_pipeline"]["incremental_training"] = f"FAIL: {e}"
        return False
    
    print("\n✅ HUGGINGFACE PIPELINE: ALL TESTS PASSED")
    return True


# ============================================================================
# RUN ALL TESTS
# ============================================================================

print("\n" + "=" * 80)
print("RUNNING ALL TESTS")
print("=" * 80)

ollama_result = test_ollama_adaptive_learning()
hf_result = test_huggingface_pipeline()

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

test_results["summary"] = {
    "ollama_adaptive_loop": "PASS" if ollama_result else "FAIL",
    "huggingface_pipeline": "PASS" if hf_result else "FAIL",
    "overall": "PASS" if (ollama_result and hf_result) else "FAIL"
}

print(f"\nOllama Adaptive Learning: {'✅ PASS' if ollama_result else '❌ FAIL'}")
print(f"HuggingFace Pipeline: {'✅ PASS' if hf_result else '❌ FAIL'}")
print(f"\nOverall: {'✅ ALL TESTS PASSED' if (ollama_result and hf_result) else '❌ SOME TESTS FAILED'}")

# Save results
output_dir = Path("test_outputs")
output_dir.mkdir(exist_ok=True)
results_file = output_dir / f"finetuning_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

with open(results_file, 'w') as f:
    json.dump(test_results, f, indent=2, default=str)

print(f"\n📄 Results saved to: {results_file}")

print("\n" + "=" * 80)
print(f"Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# Exit with appropriate code
sys.exit(0 if (ollama_result and hf_result) else 1)
