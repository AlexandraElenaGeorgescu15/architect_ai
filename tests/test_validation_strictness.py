
import asyncio
import sys
from pathlib import Path

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.validation_service import ValidationService
from backend.models.dto import ArtifactType

async def test_validation():
    service = ValidationService()
    
    # Test Content 1: Valid Mermaid
    valid_mermaid = """
    erDiagram
    USER ||--o{ POST : writes
    USER {
        int id PK
        string username
    }
    POST {
        int id PK
        string content
        int user_id FK
    }
    """
    
    # Test Content 2: Invalid Mermaid (Critical: Unbalanced braces)
    invalid_mermaid_critical = """
    erDiagram
    USER ||--o{ POST : writes
    USER {
        int id PK
        string username
    
    POST {
        id int
    }
    """
    
    # Test Content 3: Invalid Mermaid (Common AI Hallucination: empty brackets)
    invalid_mermaid_syntax = """
    flowchart TD
    A[Start] --> B[]
    """
    
    print("\n--- TEST 1: Valid Mermaid ---")
    result1 = await service.validate_artifact(ArtifactType.MERMAID_ERD, valid_mermaid, use_llm_judge=False)
    print(f"Score: {result1.score}")
    print(f"Valid: {result1.is_valid}")
    print(f"Errors: {result1.errors}")
    
    print("\n--- TEST 2: Invalid Mermaid (Critical) ---")
    result2 = await service.validate_artifact(ArtifactType.MERMAID_ERD, invalid_mermaid_critical, use_llm_judge=False)
    print(f"Score: {result2.score}")
    print(f"Valid: {result2.is_valid}")
    print(f"Errors: {result2.errors}")
    
    print("\n--- TEST 3: Invalid Mermaid (Syntax) ---")
    result3 = await service.validate_artifact(ArtifactType.MERMAID_FLOWCHART, invalid_mermaid_syntax, use_llm_judge=False)
    print(f"Score: {result3.score}")
    print(f"Valid: {result3.is_valid}")
    print(f"Errors: {result3.errors}")

if __name__ == "__main__":
    asyncio.run(test_validation())
