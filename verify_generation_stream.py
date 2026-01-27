
import asyncio
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock dependencies BEFORE importing generation_service
sys.modules["backend.core.config"] = MagicMock()
sys.modules["backend.core.logger"] = MagicMock()
sys.modules["backend.services.context_builder"] = MagicMock()
sys.modules["backend.services.enhanced_generation"] = MagicMock()
sys.modules["backend.services.quality_predictor"] = MagicMock()

# Creating a proper class for ArtifactType so isinstance works
dto_mock = MagicMock()
class MockArtifactType:
    value = "mock_type"
dto_mock.ArtifactType = MockArtifactType
dto_mock.GenerationStatus = MagicMock()
sys.modules["backend.models.dto"] = dto_mock

sys.modules["backend.services.artifact_cleaner"] = MagicMock()
sys.modules["backend.services.validation_service"] = MagicMock()
sys.modules["backend.services.finetuning_pool"] = MagicMock()
sys.modules["backend.services.html_diagram_generator"] = MagicMock()
sys.modules["backend.services.version_service"] = MagicMock()

# Import service to test
from backend.services.generation_service import GenerationService

async def main():
    print("Starting verification...")
    
    # 1. Setup Service and Mocks
    service = GenerationService()
    
    # Mock context builder
    context_mock = AsyncMock()
    context_mock.build_context.return_value = {"assembled_context": "test context"}
    service.context_builder = context_mock
    
    # Mock quality predictor
    qp_mock = MagicMock()
    qp_mock.predict.return_value = MagicMock(label="high", confidence=0.9, score=90)
    service.quality_predictor = qp_mock

    # Mock Enhanced Generation to simulate slow progress
    async def mock_generate_pipeline(*args, **kwargs):
        callback = kwargs.get("progress_callback")
        print("  [MockGen] Start generation...")
        if callback:
            await asyncio.sleep(0.5)
            print("  [MockGen] Sending progress 10%...")
            await callback(10.0, "Step 1")
            
            await asyncio.sleep(0.5)
            print("  [MockGen] Sending progress 50%...")
            await callback(50.0, "Step 2")
            
            await asyncio.sleep(0.5)
            print("  [MockGen] Sending progress 90%...")
            await callback(90.0, "Step 3")

            # Simulate chunks
            for token in ["Hello", " ", "World", "!"]:
                await asyncio.sleep(0.1)
                await callback(90.0, f"||CHUNK||{token}")
        
        return {
            "success": True, 
            "content": "Artifact Content", 
            "validation_score": 95.0, 
            "model_used": "test-model"
        }

    service.enhanced_gen = AsyncMock()
    service.enhanced_gen.generate_with_pipeline = mock_generate_pipeline

    # 2. Run Generation
    print("\nCalling generate_artifact(stream=True)...")
    start_time = time.time()
    
    async for update in service.generate_artifact(
        artifact_type="test_artifact",
        meeting_notes="test notes",
        stream=True
    ):
        elapsed = time.time() - start_time
        msg = update.get("message", "")
        progress = update.get("progress", 0)
        status = update.get("status", "")
        print(f"  [Receive] T+{elapsed:.2f}s | Status: {status} | Progress: {progress}% | Msg: {msg}")

    print("\nVerification complete.")

if __name__ == "__main__":
    asyncio.run(main())
