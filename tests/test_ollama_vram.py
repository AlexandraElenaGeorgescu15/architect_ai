"""
Test VRAM management and model loading in Ollama client
Critical for 12GB RTX 3500 Ada constraint
"""

import sys
if sys.platform == 'win32':
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass

import unittest
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOllamaVRAM(unittest.TestCase):
    """Test Ollama VRAM management"""
    
    def test_vram_limit_initialization(self):
        """Test that VRAM limit is set correctly"""
        from ai.ollama_client import OllamaClient
        
        client = OllamaClient(vram_limit_gb=12.0)
        self.assertEqual(client.vram_limit_gb, 12.0, "VRAM limit should be 12GB")
    
    def test_model_sizes_defined(self):
        """Test that model sizes are defined for VRAM management"""
        from ai.ollama_client import OllamaClient
        
        client = OllamaClient(vram_limit_gb=12.0)
        
        # Check that model sizes are defined
        self.assertIn("codellama:7b-instruct-q4_K_M", client.model_sizes)
        self.assertIn("llama3:8b-instruct-q4_K_M", client.model_sizes)
        
        # Check that sizes are reasonable (< VRAM limit)
        for model, size_gb in client.model_sizes.items():
            self.assertLess(size_gb, 12.0, f"Model {model} size should be less than VRAM limit")
    
    def test_persistent_models_tracking(self):
        """Test that persistent models are tracked"""
        from ai.ollama_client import OllamaClient
        
        client = OllamaClient(vram_limit_gb=12.0)
        
        # Check that persistent and active model sets exist
        self.assertIsInstance(client.persistent_models, set)
        self.assertIsInstance(client.active_models, set)
    
    def test_model_status_enum(self):
        """Test ModelStatus enum values"""
        from ai.ollama_client import ModelStatus
        
        # Check that all expected statuses exist
        self.assertEqual(ModelStatus.NOT_LOADED.value, "not_loaded")
        self.assertEqual(ModelStatus.LOADING.value, "loading")
        self.assertEqual(ModelStatus.READY.value, "ready")
        self.assertEqual(ModelStatus.IN_USE.value, "in_use")
        self.assertEqual(ModelStatus.ERROR.value, "error")


class TestLocalFinetuningVRAM(unittest.TestCase):
    """Test local fine-tuning VRAM management"""
    
    def test_model_ram_requirements(self):
        """Test that model RAM requirements are defined"""
        from components.local_finetuning import LocalFineTuningSystem
        
        system = LocalFineTuningSystem()
        
        # Check that all models have RAM requirements
        for model_key, model_info in system.available_models.items():
            self.assertGreater(model_info.ram_required, 0, 
                             f"Model {model_key} should have RAM requirement")
            self.assertLess(model_info.ram_required, 32,
                          f"Model {model_key} RAM requirement should be reasonable")
    
    def test_4bit_quantization_support(self):
        """Test that 4-bit quantization is supported for VRAM optimization"""
        from components.local_finetuning import TrainingConfig
        
        config = TrainingConfig(
            model_name="codellama-7b",
            epochs=1,
            learning_rate=2e-4,
            batch_size=1,
            lora_rank=16,
            lora_alpha=32,
            lora_dropout=0.05,
            use_4bit=True,
            use_8bit=False,
            max_length=512
        )
        
        self.assertTrue(config.use_4bit, "4-bit quantization should be supported")


def run_vram_tests():
    """Run VRAM management tests"""
    print("=" * 80)
    print("🔧 VRAM MANAGEMENT TESTS")
    print("=" * 80)
    print()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOllamaVRAM))
    suite.addTests(loader.loadTestsFromTestCase(TestLocalFinetuningVRAM))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 80)
    print("📊 VRAM TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Tests run: {result.testsRun}")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"❌ Errors: {len(result.errors)}")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_vram_tests()
    sys.exit(exit_code)

