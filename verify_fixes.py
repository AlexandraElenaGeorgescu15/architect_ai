
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_auth_bypass():
    print("\n[TEST] Testing Auth Bypass...")
    try:
        from backend.core.auth import require_auth
        # Call without any credentials
        result = require_auth(credentials=None, api_key=None)
        
        assert result["type"] == "jwt"
        assert result["data"]["sub"] == "admin"
        assert result["data"]["role"] == "admin"
        print("[PASS] Auth Bypass works: Returned admin user without credentials")
        return True
    except Exception as e:
        print(f"[FAIL] Auth Bypass Failed: {e}")
        return False

async def test_generation_repair_logic():
    print("\n[TEST] Testing Generation Loop (Agentic Repair)...")
    try:
        # Mock dependencies
        mock_ollama = AsyncMock()
        mock_hf = AsyncMock()
        mock_validation = AsyncMock()
        mock_model_service = MagicMock()
        
        # Setup Validation Service to fail first, then pass
        # Attempt 1: Fail (returns errors)
        # Attempt 2: Pass (returns is_valid=True)
        fail_result = MagicMock()
        fail_result.is_valid = False
        fail_result.score = 60.0
        fail_result.errors = ["Syntax error line 5", "Missing node"]
        
        pass_result = MagicMock()
        pass_result.is_valid = True
        pass_result.score = 90.0
        pass_result.errors = []
        
        mock_validation.validate_artifact = AsyncMock(side_effect=[fail_result, pass_result])
        
        # Setup Ollama to return dummy content
        response_1 = MagicMock()
        response_1.success = True
        response_1.content = "Bad Diagram"
        
        response_2 = MagicMock()
        response_2.success = True
        response_2.content = "Good Diagram"
        
        mock_ollama.generate = AsyncMock(side_effect=[response_1, response_2])
        mock_ollama.ensure_model_available = AsyncMock()
        
        # Setup Model Service to return one model
        mock_model_service.get_models_for_artifact.return_value = ["test_model"]
        mock_model_service.get_preferred_model_for_artifact.return_value = None
        
        # Import the service class (we need to mock imports inside it potentially, but we'll try to just instantiate)
        # We might need to patch 'backend.services.enhanced_generation.logger' or similar
        from backend.services.enhanced_generation import EnhancedGenerationService
        
        service = EnhancedGenerationService()
        service.ollama_client = mock_ollama
        service.hf_client = mock_hf
        service.validation_service = mock_validation
        service.model_service = mock_model_service
        
        # OPTIONS
        opts = {
            "max_retries": 1,
            "temperature": 0.7,
            "validation_threshold": 80.0
        }
        
        print("   Running generate_with_pipeline...")
        result = await service.generate_with_pipeline(
            artifact_type="mermaid_flowchart",
            meeting_notes="Draw a chart",
            options=opts
        )
        
        # VERIFICATIONS for Agentic Repair
        
        # 1. Did it retry? (Should call validate twice)
        assert mock_validation.validate_artifact.call_count == 2, f"Expected 2 validation calls, got {mock_validation.validate_artifact.call_count}"
        
        # 2. Did the second generation call include repair instructions?
        # Check call args for the second call
        second_gen_call = mock_ollama.generate.call_args_list[1]
        prompt_arg = second_gen_call.kwargs.get("prompt")
        
        if "CRITICAL FIX REQUIRED" in prompt_arg and "Syntax error line 5" in prompt_arg:
            print("[PASS] Agentic Repair Verified: Prompt contained injected errors on retry.")
            print(f"   Injected chunk snippet: '{prompt_arg[-150:]}'")
        else:
            print("[FAIL] Agentic Repair Failed: Prompt did not contain error injection.")
            print(f"   Prompt was: {prompt_arg}")
            return False
            
        # 3. Did it succeed?
        if result["success"] and result["validation_score"] == 90.0:
            print("[PASS] Generation Loop Verified: Successfully recovered on retry.")
            return True
        else:
            print(f"[FAIL] Generation Loop Failed: Result was {result}")
            return False
            
    except Exception as e:
        print(f"[FAIL] Test Crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("========================================")
    print("    VERIFYING DEEP FIXES")
    print("========================================")
    
    auth_ok = await test_auth_bypass()
    gen_ok = await test_generation_repair_logic()
    
    if auth_ok and gen_ok:
        print("\n[ALL PASS] ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n[FAIL] SOME TESTS FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
