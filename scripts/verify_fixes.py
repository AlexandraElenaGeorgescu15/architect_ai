import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings
from backend.services.design_review import get_design_review_service
from backend.api.config import save_api_key, get_api_key, ApiKeyRequest
from backend.models.dto import UserPublic
from fastapi import Request

async def verify_api_keys():
    print("\n[VERIFY] API Key Management...")
    
    # Mock request and user
    mock_request = Request({"type": "http"})
    mock_user = UserPublic(username="test_user", id="test_id")
    
    test_provider = "groq"
    test_key = "gsk_test_key_12345"
    
    # 1. Save Key
    print(f"   Saving {test_provider} key...")
    try:
        await save_api_key(
            mock_request,
            ApiKeyRequest(provider=test_provider, api_key=test_key),
            mock_user
        )
        print("   [OK] Save successful")
    except Exception as e:
        print(f"   [FAIL] Save failed: {e}")
        return

    # 2. Retrieve Key
    print(f"   Retrieving {test_provider} key...")
    try:
        result = await get_api_key(test_provider, mock_user)
        retrieved_key = result.get("api_key")
        if retrieved_key == test_key:
            print(f"   [OK] Retrieval successful. Key matches.")
        else:
            print(f"   [FAIL] Retrieval mismatch. Expected {test_key}, got {retrieved_key}")
    except Exception as e:
        print(f"   [FAIL] Retrieval failed: {e}")

async def verify_design_review():
    print("\n[VERIFY] Design Review Fallback...")
    
    service = get_design_review_service()
    
    # Use a small directory for testing
    test_dir = project_root / "backend" / "api"
    
    print(f"   Running full_review on {test_dir} (No Diagram provided)...")
    try:
        # Mock generation service to avoid actual LLM calls if possible, 
        # but here we want to test the FLOW.
        # We'll just run it and see if it crashes or returns usage of "code_quality"
        
        result = await service.full_review(
            directory=str(test_dir),
            architecture_diagram=None, # Explicitly None to trigger fallback
            meeting_notes="Test notes"
        )
        
        print(f"   Review generated. ID: {result.review_id}")
        
        # Check findings
        print(f"   Findings count: {len(result.findings)}")
        if len(result.findings) > 0:
            print("   [OK] Findings returned (Fallback active)")
        else:
            print("   [WARN] No findings returned (Check if AI was called)")
            
    except Exception as e:
        print(f"   [FAIL] Design Review failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_api_keys())
    asyncio.run(verify_design_review())
