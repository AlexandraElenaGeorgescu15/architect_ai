import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.dto import ArtifactType, ValidationResultDTO
from backend.services.validation_service import ValidationService

async def test_validation_strictness():
    print("\n--- Testing Validation Strictness ---")
    validator = ValidationService()
    
    # Test case: Broken Mermaid diagram
    broken_content = """
    graph TD
    A[Start] -->
    B[End
    """ # Missing closing bracket, incomplete arrow
    
    print(f"Testing broken content: {broken_content.strip()}")
    # Call public API (validate_artifact) to ensure all checks run
    # Disable LLM judge for faster/deterministic test
    result = await validator.validate_artifact(
        ArtifactType.MERMAID_FLOWCHART, 
        broken_content,
        use_llm_judge=False
    )
    
    print(f"Score: {result.score}")
    print(f"Is Valid: {result.is_valid}")
    print(f"Errors: {result.errors}")
    
    if result.score <= 40.0 and not result.is_valid:
        print("[PASS] Broken content capped at score 40.0 and marked invalid")
    else:
        print("[FAIL] Strict validation failed")
        print(f"Expected score <= 40.0, got {result.score}")
        print(f"Expected is_valid=False, got {result.is_valid}")

async def main():
    await test_validation_strictness()

if __name__ == "__main__":
    asyncio.run(main())
