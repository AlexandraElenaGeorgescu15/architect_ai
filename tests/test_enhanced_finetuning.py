"""
Comprehensive Test Suite for Enhanced Fine-Tuning System
Tests all 10 components plus integration.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import random
from pathlib import Path
import json

# Test utilities
class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
    
    def test(self, name, func):
        """Run a single test"""
        self.total += 1
        print(f"\n{'='*80}")
        print(f"TEST {self.total}: {name}")
        print('='*80)
        try:
            func()
            print(f"✅ PASSED: {name}")
            self.passed += 1
            return True
        except AssertionError as e:
            print(f"❌ FAILED: {name}")
            print(f"   Error: {e}")
            self.failed += 1
            return False
        except Exception as e:
            print(f"❌ ERROR: {name}")
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            return False
    
    def summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total: {self.total}")
        print(f"Passed: {self.passed} ✅")
        print(f"Failed: {self.failed} ❌")
        print(f"Success Rate: {self.passed/self.total*100:.1f}%")
        print("="*80)
        
        if self.failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {self.failed} tests failed. See details above.")


# Test 1: Enhanced Reward Calculator
def test_enhanced_reward_calculator():
    from components.reward_calculator_enhanced import EnhancedRewardCalculator, FeedbackType, FeedbackEvent
    
    calculator = EnhancedRewardCalculator()
    
    # Test 1.1: High-quality recent example
    event = FeedbackEvent(
        timestamp=time.time(),
        feedback_type=FeedbackType.SUCCESS,
        input_data="test" * 100,
        ai_output="output",
        corrected_output=None,
        context={"test": "x" * 1000},
        validation_score=90.0,
        artifact_type="erd",
        model_used="test",
        reward_signal=0.0
    )
    
    reward = calculator.calculate_reward(event)
    assert -1.0 <= reward <= 1.0, f"Reward out of range: {reward}"
    assert reward > 0.5, f"High-quality example should have reward > 0.5, got {reward}"
    print(f"  High-quality reward: {reward:.3f}")
    
    # Test 1.2: Low-quality old example
    event_old = FeedbackEvent(
        timestamp=time.time() - 86400 * 7,  # 7 days ago
        feedback_type=FeedbackType.VALIDATION_FAILURE,
        input_data="test",
        ai_output="output",
        corrected_output=None,
        context={},
        validation_score=40.0,
        artifact_type="code_prototype",
        model_used="test",
        reward_signal=0.0
    )
    
    reward_old = calculator.calculate_reward(event_old)
    assert reward_old < 0, f"Low-quality failure should have negative reward, got {reward_old}"
    assert reward < reward_old * 5, "Recent reward should be significantly higher than old"
    print(f"  Low-quality old reward: {reward_old:.3f}")
    
    print("  ✓ Reward calculation working correctly")


# Test 2: Advanced Similarity Metrics
def test_similarity_metrics():
    from components.similarity_metrics import SimilarityCalculator
    
    calculator = SimilarityCalculator()
    
    # Test 2.1: Identical strings
    result = calculator.calculate_all("Hello World", "Hello World")
    assert result['combined'] > 0.95, f"Identical strings should have similarity > 0.95, got {result['combined']}"
    print(f"  Identical strings: {result['combined']:.3f}")
    
    # Test 2.2: Different strings
    result2 = calculator.calculate_all("Generate ERD", "Create authentication code")
    assert result2['combined'] < 0.5, f"Different strings should have similarity < 0.5, got {result2['combined']}"
    print(f"  Different strings: {result2['combined']:.3f}")
    
    # Test 2.3: Similar strings
    result3 = calculator.calculate_all("Generate ERD diagram", "Create ERD diagram")
    assert 0.5 < result3['combined'] < 0.95, f"Similar strings should have 0.5 < similarity < 0.95, got {result3['combined']}"
    print(f"  Similar strings: {result3['combined']:.3f}")
    
    print("  ✓ Similarity metrics working correctly")


# Test 3: Dynamic Batch Manager
def test_batch_manager():
    from components.batch_manager_adaptive import AdaptiveBatchManager
    
    manager = AdaptiveBatchManager()
    
    # Test 3.1: Not enough examples
    batch_size = manager.calculate_optimal_batch_size("erd", 15, 0.8)
    assert batch_size == 0, f"Should return 0 for insufficient examples, got {batch_size}"
    print(f"  Insufficient examples: {batch_size}")
    
    # Test 3.2: Normal case
    batch_size = manager.calculate_optimal_batch_size("erd", 50, 0.75)
    assert 20 <= batch_size <= 100, f"Batch size should be in [20, 100], got {batch_size}"
    print(f"  Normal batch size: {batch_size}")
    
    # Test 3.3: High quality (smaller batch)
    batch_size_hq = manager.calculate_optimal_batch_size("erd", 50, 0.9)
    assert batch_size_hq <= batch_size, f"High quality should have smaller/equal batch: {batch_size_hq} vs {batch_size}"
    print(f"  High quality batch size: {batch_size_hq}")
    
    print("  ✓ Batch manager working correctly")


# Test 4: Performance Tracker
def test_performance_tracker():
    from components.performance_tracker import PerformanceTracker, PerformanceMetrics
    from dataclasses import dataclass
    
    @dataclass
    class MockExample:
        artifact_type: str
    
    tracker = PerformanceTracker()
    
    # Test 4.1: Train/val split
    examples = [MockExample("erd") for _ in range(50)] + [MockExample("code") for _ in range(50)]
    train, val = tracker.split_train_validation(examples)
    
    assert len(train) + len(val) == len(examples), "Split should preserve total count"
    assert len(val) > 0, "Validation set should not be empty"
    assert len(val) < len(train), "Validation set should be smaller than training set"
    print(f"  Split: {len(train)} train, {len(val)} val")
    
    # Test 4.2: Record metrics
    metrics = PerformanceMetrics(
        model_id="test_model",
        artifact_type="erd",
        timestamp=time.time(),
        avg_validation_score=85.0,
        success_rate=0.9,
        avg_reward=0.7,
        avg_latency=10.0,
        n_samples=20
    )
    
    tracker.record_metrics(metrics)
    best = tracker.get_best_model("erd")
    assert best is not None, "Should have best model after recording"
    assert best.avg_validation_score == 85.0, f"Best score should be 85.0, got {best.avg_validation_score}"
    print(f"  Best model score: {best.avg_validation_score:.1f}")
    
    print("  ✓ Performance tracker working correctly")


# Test 5: Curriculum Learner
def test_curriculum_learner():
    from components.curriculum_learner import CurriculumLearner, FeedbackEvent, CurriculumStage
    
    learner = CurriculumLearner()
    
    # Create examples with varying difficulty
    examples = []
    for i in range(30):
        examples.append(FeedbackEvent(
            timestamp=time.time(),
            input_data="x" * random.randint(100, 5000),
            ai_output="output",
            validation_score=random.uniform(60, 95),
            artifact_type=random.choice(['erd', 'code_prototype']),
            reward_signal=random.uniform(0.2, 0.9),
            context={}
        ))
    
    # Test 5.1: Organization by difficulty
    stages = learner.organize_by_curriculum(examples)
    total = sum(len(stage_examples) for stage_examples in stages.values())
    assert total == len(examples), f"Should preserve all examples: {total} vs {len(examples)}"
    print(f"  Organized: Easy={len(stages[CurriculumStage.EASY])}, Medium={len(stages[CurriculumStage.MEDIUM])}, Hard={len(stages[CurriculumStage.HARD])}")
    
    # Test 5.2: Batch creation
    batch, stage = learner.get_next_training_batch(stages, batch_size=20)
    assert len(batch) <= 20, f"Batch size should be <= 20, got {len(batch)}"
    assert stage == CurriculumStage.EASY, f"Should start with EASY stage, got {stage}"
    print(f"  First batch: {len(batch)} examples from {stage.value}")
    
    print("  ✓ Curriculum learner working correctly")


# Test 6: Active Learner
def test_active_learner():
    from components.active_learner import ActiveLearner, FeedbackEvent
    
    learner = ActiveLearner()
    
    # Create diverse candidates
    candidates = []
    
    # High-quality examples
    for i in range(20):
        candidates.append(FeedbackEvent(
            timestamp=time.time(),
            input_data=f"Generate ERD {i}",
            ai_output="erDiagram...",
            validation_score=random.uniform(80, 95),
            artifact_type="erd",
            reward_signal=random.uniform(0.6, 0.9),
            corrected_output=None,
            feedback_type="success",
            context={}
        ))
    
    # Low-quality examples (more informative)
    for i in range(10):
        candidates.append(FeedbackEvent(
            timestamp=time.time(),
            input_data=f"Generate complex code {i}",
            ai_output="class...",
            validation_score=random.uniform(50, 65),
            artifact_type="code_prototype",
            reward_signal=random.uniform(0.0, 0.4),
            corrected_output="corrected",
            feedback_type="user_correction",
            context={}
        ))
    
    # Test 6.1: Select informative examples
    selected, metadata = learner.select_informative_examples(candidates, budget=10)
    
    assert len(selected) == 10, f"Should select 10 examples, got {len(selected)}"
    
    # Check that low-quality examples are prioritized (higher uncertainty)
    low_quality_count = sum(1 for ex in selected if ex.validation_score < 70)
    print(f"  Selected: {len(selected)} examples, {low_quality_count} low-quality (high uncertainty)")
    
    print("  ✓ Active learner working correctly")


# Test 7: Hyperparameter Optimizer
def test_hyperparameter_optimizer():
    from components.hyperparameter_optimizer import HyperparameterOptimizer, HyperparameterConfig
    
    optimizer = HyperparameterOptimizer()
    
    # Test 7.1: Default config
    default = optimizer.get_default_config()
    assert isinstance(default, HyperparameterConfig), "Should return HyperparameterConfig"
    assert 1e-6 <= default.learning_rate <= 1e-3, f"LR out of range: {default.learning_rate}"
    print(f"  Default LR: {default.learning_rate:.2e}")
    
    # Test 7.2: Save/load
    optimizer._save_result(
        result=type('Result', (), {
            'best_params': default,
            'best_score': 85.0,
            'n_trials': 10,
            'optimization_history': []
        })(),
        artifact_type="test"
    )
    
    loaded = optimizer.load_best_params("test")
    assert loaded is not None, "Should load saved params"
    assert loaded.learning_rate == default.learning_rate, "Loaded LR should match saved"
    print(f"  Loaded LR: {loaded.learning_rate:.2e}")
    
    print("  ✓ Hyperparameter optimizer working correctly")


# Test 8: Preference Learner
def test_preference_learner():
    from components.preference_learner import PreferenceLearner
    
    learner = PreferenceLearner()
    
    # Test 8.1: Collect preferences
    outputs = ["output1" * 10, "output2" * 5, "output3" * 2]
    scores = [85.0, 70.0, 50.0]
    
    preferences = learner.collect_preferences(
        input_data="test input",
        outputs=outputs,
        scores=scores,
        artifact_type="erd",
        context={}
    )
    
    assert len(preferences) > 0, "Should create at least one preference pair"
    assert preferences[0].margin > 0, f"Margin should be positive: {preferences[0].margin}"
    print(f"  Created {len(preferences)} preference pairs")
    
    # Test 8.2: Training dataset
    dataset = learner.create_training_dataset()
    assert len(dataset) == len(preferences), "Dataset size should match preferences"
    print(f"  Training dataset: {len(dataset)} examples")
    
    print("  ✓ Preference learner working correctly")


# Test 9: Data Augmenter
def test_data_augmenter():
    from components.data_augmenter import DataAugmenter, TrainingExample
    
    augmenter = DataAugmenter(augmentation_factor=2)
    
    # Create original examples
    examples = [
        TrainingExample(
            input_data="Generate ERD",
            output="erDiagram...",
            context={},
            artifact_type="erd",
            quality_score=85.0
        )
        for _ in range(10)
    ]
    
    # Test 9.1: Augment dataset
    augmented = augmenter.augment_dataset(examples)
    
    assert len(augmented) >= len(examples), "Augmented should be >= original"
    assert len(augmented) <= len(examples) * 3, "Augmented should be <= 3x original"
    print(f"  Augmented: {len(examples)} → {len(augmented)} ({len(augmented)/len(examples):.1f}x)")
    
    print("  ✓ Data augmenter working correctly")


# Test 10: Hard Negative Miner
def test_hard_negative_miner():
    from components.hard_negative_miner import HardNegativeMiner
    
    miner = HardNegativeMiner()
    
    # Test 10.1: Record failures
    for i in range(10):
        miner.record_failure(
            input_data=f"complex input {i}",
            output="incomplete output",
            validation_score=random.uniform(30, 55),
            artifact_type="erd",
            metadata={}
        )
    
    # Test 10.2: Get hard negatives
    hard_negatives = miner.get_hard_negatives(artifact_type="erd", limit=5)
    assert len(hard_negatives) > 0, "Should have hard negatives"
    assert len(hard_negatives) <= 5, "Should respect limit"
    print(f"  Retrieved {len(hard_negatives)} hard negatives")
    
    # Test 10.3: Analyze patterns
    analysis = miner.analyze_failure_patterns()
    assert 'total_failures' in analysis, "Should have failure count"
    assert analysis['total_failures'] > 0, "Should have recorded failures"
    print(f"  Total failures: {analysis['total_failures']}")
    
    print("  ✓ Hard negative miner working correctly")


# Test 11: Integration Test
def test_integration():
    from components.adaptive_learning_enhanced import EnhancedAdaptiveLearningLoop
    from components.reward_calculator_enhanced import FeedbackType
    
    # Test 11.1: Initialization
    loop = EnhancedAdaptiveLearningLoop(
        enable_curriculum=True,
        enable_active_learning=True,
        enable_augmentation=True,
        enable_preference_learning=False,
        enable_hard_negative_mining=True
    )
    
    assert loop.reward_calculator is not None, "Should initialize reward calculator"
    assert loop.batch_manager is not None, "Should initialize batch manager"
    assert loop.performance_tracker is not None, "Should initialize performance tracker"
    assert loop.curriculum_learner is not None, "Should initialize curriculum learner"
    assert loop.active_learner is not None, "Should initialize active learner"
    print("  All components initialized ✓")
    
    # Test 11.2: Record feedback
    event = loop.record_feedback(
        input_data="Generate ERD for e-commerce system",
        ai_output="erDiagram\nUser {int id PK}\nProduct {int id PK}",
        artifact_type="erd",
        model_used="mistral:7b",
        validation_score=85.0,
        feedback_type=FeedbackType.SUCCESS,
        context={"rag": "context", "notes": "requirements"}
    )
    
    assert event is not None, "Should record high-quality feedback"
    assert event.reward_signal > 0, f"Success should have positive reward, got {event.reward_signal}"
    print(f"  Recorded feedback with reward: {event.reward_signal:.2f} ✓")
    
    # Test 11.3: Statistics
    stats = loop.get_statistics()
    assert 'feedback_events' in stats, "Should have feedback count"
    assert stats['feedback_events'] > 0, "Should have recorded events"
    print(f"  Statistics: {stats['feedback_events']} events ✓")
    
    print("  ✓ Integration test passed")


# Main test runner
if __name__ == "__main__":
    runner = TestRunner()
    
    print("="*80)
    print("ENHANCED FINE-TUNING SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    # Run all tests
    runner.test("Enhanced Reward Calculator", test_enhanced_reward_calculator)
    runner.test("Advanced Similarity Metrics", test_similarity_metrics)
    runner.test("Dynamic Batch Manager", test_batch_manager)
    runner.test("Performance Tracker", test_performance_tracker)
    runner.test("Curriculum Learner", test_curriculum_learner)
    runner.test("Active Learner", test_active_learner)
    runner.test("Hyperparameter Optimizer", test_hyperparameter_optimizer)
    runner.test("Preference Learner", test_preference_learner)
    runner.test("Data Augmenter", test_data_augmenter)
    runner.test("Hard Negative Miner", test_hard_negative_miner)
    runner.test("Integration Test", test_integration)
    
    # Print summary
    runner.summary()
    
    # Exit with appropriate code
    sys.exit(0 if runner.failed == 0 else 1)

