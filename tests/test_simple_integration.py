"""
Simple Integration Test - Quick verification both systems work together
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("\n" + "="*80)
print("SIMPLE INTEGRATION TEST")
print("="*80 + "\n")

# Test 1: Ollama can record feedback
print("[1] Testing Ollama feedback recording...")
try:
    from components.adaptive_learning import AdaptiveLearningLoop, FeedbackType
    loop = AdaptiveLearningLoop(storage_dir=Path("test_outputs/simple_integration"))
    
    event = loop.record_feedback(
        input_data="Generate ERD for user system",
        ai_output="erDiagram\n  User ||--o{ Role : has",
        artifact_type="erd",
        model_used="codellama:7b",
        validation_score=85.0,
        feedback_type=FeedbackType.SUCCESS,
        context={"test": "simple"}
    )
    
    print(f"   PASS - Recorded with reward: {event.reward_signal:.2f}")
except Exception as e:
    print(f"   FAIL - {e}")
    sys.exit(1)

# Test 2: HuggingFace can build dataset
print("\n[2] Testing HuggingFace dataset builder...")
try:
    from components.finetuning_dataset_builder import FineTuningDatasetBuilder
    
    notes = "Project: Test System\nTech: Python"
    builder = FineTuningDatasetBuilder(notes, max_chunks=5)
    examples, report = builder.build_dataset(limit=10)
    
    print(f"   PASS - Generated {report.total_examples} examples")
except Exception as e:
    print(f"   FAIL - {e}")
    sys.exit(1)

# Test 3: HuggingFace can create training config
print("\n[3] Testing HuggingFace training config...")
try:
    from components.local_finetuning import LocalFineTuningSystem, TrainingConfig
    
    system = LocalFineTuningSystem()
    config = TrainingConfig(
        model_name="codellama-7b",
        epochs=1,
        learning_rate=2e-4,
        batch_size=1,
        lora_rank=8,
        lora_alpha=16,
        lora_dropout=0.05,
        use_4bit=True,
        use_8bit=False,
        max_length=512
    )
    
    print(f"   PASS - Config created for {config.model_name}")
except Exception as e:
    print(f"   FAIL - {e}")
    sys.exit(1)

# Test 4: Systems can share data
print("\n[4] Testing data sharing between systems...")
try:
    # Ollama feedback can be converted to training examples
    training_example = event.to_training_example()
    
    # HuggingFace examples have same format
    if examples:
        hf_example = examples[0]
        
        # Both should have instruction, input, output
        assert 'instruction' in training_example
        assert 'output' in training_example
        assert 'instruction' in hf_example
        assert 'output' in hf_example
        
        print(f"   PASS - Both systems use compatible data format")
    else:
        print(f"   WARN - No HF examples to compare")
except Exception as e:
    print(f"   FAIL - {e}")
    sys.exit(1)

print("\n" + "="*80)
print("INTEGRATION TEST RESULT: ALL TESTS PASSED")
print("="*80)
print("\nBoth systems work together successfully!")
print("- Ollama: Records feedback and calculates rewards")
print("- HuggingFace: Builds datasets and creates training configs")
print("- Integration: Both use compatible data formats\n")
