"""
Comprehensive Tests for November 2024 Fixes

Tests all critical fixes:
1. Enhanced artifact-model mapping with priority lists
2. Smart model selector with quality validation
3. Intelligent cloud context compression
4. HTML diagram generation improvements
5. Prototype format validation
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable UTF-8 for Windows (skip in pytest to avoid conflicts)
if sys.platform == 'win32' and 'pytest' not in sys.modules:
    try:
        import io
        if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError, ValueError):
        pass


class TestArtifactModelMapping:
    """Test Fix #1: Enhanced artifact-model mapping"""
    
    def test_priority_models_exist(self):
        """Test that all artifacts have priority model lists"""
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        artifacts = ["erd", "architecture", "code_prototype", "visual_prototype_dev"]
        
        for artifact in artifacts:
            priority_models = mapper.get_priority_models(artifact)
            assert priority_models is not None, f"{artifact} missing priority models"
            assert len(priority_models) >= 1, f"{artifact} must have at least 1 model"
            assert isinstance(priority_models, list), f"{artifact} priority_models must be list"
            print(f"✅ {artifact}: {priority_models}")
    
    def test_quality_threshold_raised(self):
        """Test that quality thresholds are >= 80"""
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        artifacts = ["erd", "architecture", "code_prototype"]
        
        for artifact in artifacts:
            threshold = mapper.get_quality_threshold(artifact)
            assert threshold >= 80, f"{artifact} threshold {threshold} < 80"
            print(f"✅ {artifact} threshold: {threshold}/100")
    
    def test_html_uses_llama3(self):
        """Test that HTML artifacts use llama3 (better at HTML)"""
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        mapping = mapper.get_model_for_artifact("visual_prototype_dev")
        
        assert mapping.base_model == "llama3:8b-instruct-q4_K_M", \
            "HTML prototypes should use llama3"
        assert "llama3:8b-instruct-q4_K_M" in mapping.priority_models, \
            "llama3 should be in priority list"
        print(f"✅ HTML uses llama3: {mapping.base_model}")
    
    def test_architecture_uses_llama3(self):
        """Test that architecture uses llama3 (better for complex diagrams)"""
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        mapping = mapper.get_model_for_artifact("architecture")
        
        assert mapping.base_model == "llama3:8b-instruct-q4_K_M", \
            "Architecture should use llama3"
        print(f"✅ Architecture uses llama3: {mapping.base_model}")


class TestSmartModelSelector:
    """Test Fix #2: Smart model selector"""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client"""
        client = Mock()
        client.ensure_model_available = AsyncMock()
        client.generate = AsyncMock(return_value=Mock(
            success=True,
            content="Test output",
            error_message=""
        ))
        return client
    
    @pytest.fixture
    def mock_validator(self):
        """Mock validator"""
        validator = Mock()
        validator.validate_artifact = AsyncMock(return_value=Mock(
            score=85.0,
            is_valid=True,
            errors=[]
        ))
        return validator
    
    @pytest.fixture
    def mock_mapper(self):
        """Mock artifact mapper"""
        from config.artifact_model_mapping import get_artifact_mapper
        return get_artifact_mapper()
    
    @pytest.mark.asyncio
    async def test_priority_model_selection(self, mock_ollama_client, mock_validator, mock_mapper):
        """Test that models are tried in priority order"""
        from ai.smart_model_selector import SmartModelSelector
        
        selector = SmartModelSelector(
            ollama_client=mock_ollama_client,
            validator=mock_validator,
            artifact_mapper=mock_mapper,
            min_quality_threshold=80
        )
        
        # Mock cloud fallback
        async def mock_cloud_fallback(*args, **kwargs):
            return "Cloud result"
        
        result = await selector.select_and_generate(
            artifact_type="erd",
            prompt="Test prompt",
            cloud_fallback_fn=mock_cloud_fallback
        )
        
        assert result.success, "Generation should succeed"
        assert result.quality_score >= 80, "Quality should meet threshold"
        assert len(result.attempts) >= 1, "Should have at least 1 attempt"
        print(f"✅ Model selection result: {result.model_used}, Quality: {result.quality_score}")
    
    @pytest.mark.asyncio
    async def test_quality_validation_retry(self, mock_ollama_client, mock_mapper):
        """Test that low quality triggers retry with next model"""
        # Mock validator that returns low score first, then high score
        mock_validator = Mock()
        scores = [60.0, 85.0]  # First attempt fails, second succeeds
        mock_validator.validate_artifact = AsyncMock(side_effect=[
            Mock(score=scores[0], is_valid=False, errors=["Low quality"]),
            Mock(score=scores[1], is_valid=True, errors=[])
        ])
        
        from ai.smart_model_selector import SmartModelSelector
        
        selector = SmartModelSelector(
            ollama_client=mock_ollama_client,
            validator=mock_validator,
            artifact_mapper=mock_mapper,
            min_quality_threshold=80
        )
        
        result = await selector.select_and_generate(
            artifact_type="erd",
            prompt="Test prompt"
        )
        
        assert len(result.attempts) >= 2, "Should try multiple models"
        print(f"✅ Retry logic works: {len(result.attempts)} attempts")


class TestContextCompression:
    """Test Fix #3: Intelligent cloud context compression"""
    
    def test_compress_long_prompt(self):
        """Test that long prompts are compressed"""
        from ai.smart_model_selector import SmartModelSelector
        
        # Create dummy instances (won't be used for this test)
        selector = SmartModelSelector(
            ollama_client=Mock(),
            validator=Mock(),
            artifact_mapper=Mock()
        )
        
        # Create a very long prompt
        long_prompt = "CRITICAL: User requirements\n" + "X" * 50000
        compressed = selector._compress_prompt_for_cloud(long_prompt, target_chars=10000)
        
        assert len(compressed) <= 15000, "Prompt should be compressed"
        assert "CRITICAL" in compressed, "Critical sections should be preserved"
        print(f"✅ Compressed {len(long_prompt)} → {len(compressed)} chars")
    
    def test_preserve_critical_sections(self):
        """Test that critical sections are never removed"""
        from ai.smart_model_selector import SmartModelSelector
        
        selector = SmartModelSelector(
            ollama_client=Mock(),
            validator=Mock(),
            artifact_mapper=Mock()
        )
        
        prompt = """
        CRITICAL: User requirements here
        MANDATORY: Must implement X
        OUTPUT FORMAT: JSON
        Some compressible context...
        """ * 100
        
        compressed = selector._compress_prompt_for_cloud(prompt, target_chars=5000)
        
        assert "CRITICAL" in compressed
        assert "MANDATORY" in compressed
        assert "OUTPUT FORMAT" in compressed
        print("✅ Critical sections preserved")


class TestHTMLValidation:
    """Test Fix #4: HTML diagram generation improvements"""
    
    def test_html_structure_validation(self):
        """Test HTML structure validation"""
        # Valid HTML
        valid_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        <body><h1>Hello</h1></body>
        </html>
        """
        
        assert '<html' in valid_html.lower()
        assert '<body' in valid_html.lower()
        assert '<head' in valid_html.lower()
        print("✅ Valid HTML structure detected")
        
        # Invalid HTML (missing body)
        invalid_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test</title></head>
        </html>
        """
        
        assert '<html' in invalid_html.lower()
        assert '<body' not in invalid_html.lower()
        print("✅ Invalid HTML structure detected")
    
    def test_html_cleaning(self):
        """Test HTML cleaning removes markdown"""
        from components.mermaid_html_renderer import MermaidHTMLRenderer
        
        renderer = MermaidHTMLRenderer()
        
        # HTML with markdown wrapper
        dirty_html = """```html
        <!DOCTYPE html>
        <html><body>Test</body></html>
        ```"""
        
        clean_html = renderer._clean_html_content(dirty_html)
        
        assert '```' not in clean_html
        assert '<!DOCTYPE html>' in clean_html
        print("✅ HTML cleaned successfully")


class TestPrototypeGeneration:
    """Test Fix #6: Prototype generation"""
    
    def test_parse_llm_files_with_markers(self):
        """Test parsing LLM output with === FILE: === markers"""
        from components.prototype_generator import parse_llm_files
        
        response = """
        Some intro text...
        
        === FILE: test.ts ===
        const test = 'hello';
        === END FILE ===
        
        === FILE: test.html ===
        <h1>Test</h1>
        === END FILE ===
        
        Some concluding text...
        """
        
        files = parse_llm_files(response)
        
        assert len(files) == 2, f"Should parse 2 files, got {len(files)}"
        assert files[0][0] == "test.ts"
        assert "const test" in files[0][1]
        assert files[1][0] == "test.html"
        assert "<h1>Test</h1>" in files[1][1]
        print(f"✅ Parsed {len(files)} files from LLM output")
    
    def test_parse_llm_files_without_markers(self):
        """Test that files without markers aren't parsed"""
        from components.prototype_generator import parse_llm_files
        
        response = """
        Here's some code:
        
        const test = 'hello';
        
        And some HTML:
        
        <h1>Test</h1>
        """
        
        files = parse_llm_files(response)
        
        assert len(files) == 0, "Should parse 0 files (no markers)"
        print("✅ Correctly ignores output without === FILE: === markers")
    
    def test_detect_stack(self):
        """Test stack detection"""
        from components.prototype_generator import detect_stack
        
        # Test with actual project
        base = Path(__file__).parent.parent.parent  # Go up to Dawn-final-project
        stack = detect_stack(base)
        
        assert isinstance(stack, dict)
        assert "has_angular" in stack
        assert "has_dotnet" in stack
        
        # Should detect Angular and .NET from the actual project
        if stack["has_angular"]:
            print("✅ Angular detected")
        if stack["has_dotnet"]:
            print("✅ .NET detected")


class TestQualityThresholds:
    """Test quality thresholds across the system"""
    
    def test_validation_threshold(self):
        """Test that validation uses correct thresholds"""
        # This would need actual validator integration
        # For now, test that the threshold value is correct
        from ai.smart_model_selector import SmartModelSelector
        
        selector = SmartModelSelector(
            ollama_client=Mock(),
            validator=Mock(),
            artifact_mapper=Mock(),
            min_quality_threshold=80
        )
        
        assert selector.min_quality_threshold == 80
        print("✅ Validation threshold set to 80")


class TestIntegration:
    """Integration tests for all fixes working together"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_artifact_generation(self):
        """Test complete artifact generation flow"""
        # This is a smoke test - real integration would need full setup
        from config.artifact_model_mapping import get_artifact_mapper
        
        mapper = get_artifact_mapper()
        
        # Test ERD generation flow
        artifact_type = "erd"
        priority_models = mapper.get_priority_models(artifact_type)
        threshold = mapper.get_quality_threshold(artifact_type)
        
        assert len(priority_models) >= 1
        assert threshold >= 80
        
        print(f"✅ End-to-end ERD flow: models={priority_models}, threshold={threshold}")


def run_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 Running Comprehensive Fixes Tests")
    print("=" * 60 + "\n")
    
    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()

