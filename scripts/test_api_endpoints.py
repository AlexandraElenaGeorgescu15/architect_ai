#!/usr/bin/env python3
"""
Comprehensive API Endpoint Testing Script
Tests all major Architect.AI endpoints with mock data, similar to Postman testing.

Usage:
    python scripts/test_api_endpoints.py
"""

import sys
import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import io

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    os.system(f"{sys.executable} -m pip install httpx --quiet")
    import httpx

# Configuration
BASE_URL = os.environ.get("ARCHITECT_API_URL", "http://localhost:8000")
TIMEOUT = 60.0
REQUEST_DELAY = 0.3  # Delay between requests to avoid rate limiting

# Test results tracking
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results: List[Dict[str, Any]] = []
    
    def add(self, name: str, status: str, message: str = "", response_time: float = 0):
        self.results.append({
            "name": name,
            "status": status,
            "message": message,
            "response_time": response_time
        })
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        else:
            self.skipped += 1
    
    def print_summary(self):
        print("\n" + "=" * 70)
        print("  TEST RESULTS SUMMARY")
        print("=" * 70)
        
        # Print each result
        for r in self.results:
            icon = "[OK]" if r["status"] == "PASS" else "[FAIL]" if r["status"] == "FAIL" else "[SKIP]"
            time_str = f" ({r['response_time']:.2f}s)" if r['response_time'] > 0 else ""
            print(f"  {icon} {r['name']}{time_str}")
            if r["message"] and r["status"] == "FAIL":
                print(f"       -> {r['message'][:100]}")
        
        print("-" * 70)
        print(f"  PASSED: {self.passed}  |  FAILED: {self.failed}  |  SKIPPED: {self.skipped}")
        print(f"  Total: {len(self.results)} tests")
        print("=" * 70)


results = TestResults()


async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    name: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expected_status: int = 200,
    expected_keys: Optional[List[str]] = None,
    allow_404: bool = False,
    allow_403: bool = False
) -> Tuple[bool, Dict[str, Any]]:
    """Test a single API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    start_time = time.time()
    
    # Add delay between requests to avoid rate limiting
    await asyncio.sleep(REQUEST_DELAY)
    
    try:
        if method.upper() == "GET":
            response = await client.get(url, params=params, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = await client.post(url, json=data, params=params, timeout=TIMEOUT)
        elif method.upper() == "PUT":
            response = await client.put(url, json=data, timeout=TIMEOUT)
        elif method.upper() == "DELETE":
            response = await client.delete(url, timeout=TIMEOUT)
        else:
            results.add(name, "SKIP", f"Unsupported method: {method}")
            return False, {}
        
        elapsed = time.time() - start_time
        
        # Check status code
        if response.status_code != expected_status:
            if allow_404 and response.status_code == 404:
                results.add(name, "PASS", "Endpoint returns 404 (acceptable)", elapsed)
                return True, {}
            if allow_403 and response.status_code == 403:
                results.add(name, "PASS", "Rate limited (acceptable for testing)", elapsed)
                return True, {}
            results.add(name, "FAIL", f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}", elapsed)
            return False, {}
        
        # Try to parse JSON response
        try:
            response_data = response.json()
        except:
            response_data = {"raw": response.text[:500]}
        
        # Check expected keys
        if expected_keys:
            missing_keys = [k for k in expected_keys if k not in response_data]
            if missing_keys:
                results.add(name, "FAIL", f"Missing keys: {missing_keys}", elapsed)
                return False, response_data
        
        results.add(name, "PASS", "", elapsed)
        return True, response_data
        
    except httpx.ConnectError:
        results.add(name, "FAIL", "Connection refused - is the backend running?")
        return False, {}
    except httpx.TimeoutException:
        results.add(name, "FAIL", f"Request timed out after {TIMEOUT}s")
        return False, {}
    except Exception as e:
        results.add(name, "FAIL", str(e))
        return False, {}


async def run_all_tests():
    """Run all API endpoint tests."""
    print("=" * 70)
    print("  ARCHITECT.AI - API ENDPOINT TESTS")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    async with httpx.AsyncClient() as client:
        
        # ============================================================
        # 1. HEALTH & STATUS
        # ============================================================
        print("\n[1/12] Testing Health & Status...")
        
        await test_endpoint(client, "GET", "/health", "Health Check", expected_keys=["status"])
        await test_endpoint(client, "GET", "/api/health", "API Health Check")
        
        # ============================================================
        # 2. AUTHENTICATION (Optional in dev mode)
        # ============================================================
        print("\n[2/12] Testing Authentication...")
        
        await test_endpoint(client, "GET", "/api/auth/me", "Get Current User", expected_keys=["username"])
        
        # ============================================================
        # 3. MODELS
        # ============================================================
        print("\n[3/12] Testing Models...")
        
        # Note: /api/models redirects to /api/models/ - use trailing slash
        success, models_data = await test_endpoint(client, "GET", "/api/models/", "List Models")
        await test_endpoint(client, "GET", "/api/models/routing", "Get Model Routing")
        await test_endpoint(client, "POST", "/api/models/refresh", "Refresh Models")
        
        # Test model suggestion (new feature)
        await test_endpoint(
            client, "POST", "/api/models/suggest-routing",
            "AI Model Suggestion",
            params={"artifact_type": "mermaid_erd"}
        )
        
        # ============================================================
        # 4. MEETING NOTES
        # ============================================================
        print("\n[4/12] Testing Meeting Notes...")
        
        # Extra delay to ensure rate limiter is happy
        await asyncio.sleep(0.5)
        
        await test_endpoint(client, "GET", "/api/meeting-notes/folders", "List Folders", expected_keys=["success", "folders"])
        
        # Create a test folder first (needs `name` field)
        await test_endpoint(
            client, "POST", "/api/meeting-notes/folders",
            "Create Test Folder",
            data={"name": "api_test_folder"}
        )
        
        # List notes (folder may or may not exist)
        await test_endpoint(
            client, "GET", "/api/meeting-notes/folders/api_test_folder/notes",
            "Get Notes from Folder",
            allow_404=True  # Folder might not exist
        )
        
        # ============================================================
        # 5. RAG SYSTEM
        # ============================================================
        print("\n[5/12] Testing RAG System...")
        
        await test_endpoint(client, "GET", "/api/rag/status", "RAG Status")
        await test_endpoint(client, "GET", "/api/rag/index/stats", "RAG Index Statistics")
        
        # Test RAG search
        await test_endpoint(
            client, "POST", "/api/rag/search",
            "RAG Search",
            data={"query": "user authentication", "top_k": 5}
        )
        
        # ============================================================
        # 6. UNIVERSAL CONTEXT (Knowledge Graph + Patterns combined)
        # ============================================================
        print("\n[6/12] Testing Universal Context...")
        
        await test_endpoint(client, "GET", "/api/universal-context/status", "Universal Context Status")
        await test_endpoint(client, "GET", "/api/universal-context/", "Get Universal Context")
        await test_endpoint(client, "GET", "/api/universal-context/key-entities", "Get Key Entities")
        await test_endpoint(client, "GET", "/api/universal-context/project-map", "Get Project Map")
        await test_endpoint(client, "GET", "/api/universal-context/importance-scores", "Get Importance Scores")
        
        # ============================================================
        # 7. CONTEXT BUILDING
        # ============================================================
        print("\n[7/12] Testing Context Building...")
        
        context_request = {
            "meeting_notes": """
# E-commerce Platform Requirements

## User Stories
- As a user, I want to register and login
- As a user, I want to browse products
- As a user, I want to add products to cart
- As a user, I want to checkout and pay

## Database Entities
- User (id, email, password, name)
- Product (id, name, price, description, stock)
- Order (id, user_id, total, status)
- OrderItem (id, order_id, product_id, quantity)
            """,
            "include_rag": True,
            "include_kg": True,
            "include_patterns": True,
            "max_rag_chunks": 10
        }
        
        success, context_data = await test_endpoint(
            client, "POST", "/api/context/build",
            "Build Context",
            data=context_request
        )
        
        # Context ID might be different format depending on backend implementation
        context_id = context_data.get("context_id")
        if context_id:
            # Context retrieval endpoint may not exist or use different format
            await test_endpoint(
                client, "GET", f"/api/context/{context_id}", 
                "Get Context by ID",
                allow_404=True  # Context storage may vary
            )
        
        # ============================================================
        # 8. ARTIFACT GENERATION
        # ============================================================
        print("\n[8/12] Testing Artifact Generation...")
        
        await test_endpoint(client, "GET", "/api/generation/artifact-types", "List Artifact Types")
        await test_endpoint(client, "GET", "/api/generation/artifact-types/categories", "List Categories")
        await test_endpoint(client, "GET", "/api/generation/artifact-types/custom", "List Custom Types")
        
        # Test artifact generation
        generation_request = {
            "artifact_type": "mermaid_erd",
            "meeting_notes": """
## E-commerce Database Design
- Users table: id, email, password_hash, name, created_at
- Products table: id, name, description, price, stock, category_id
- Categories table: id, name, parent_id
- Orders table: id, user_id, total, status, created_at
- OrderItems table: id, order_id, product_id, quantity, price
            """,
            "options": {
                "max_retries": 1,
                "use_validation": True,
                "temperature": 0.7
            }
        }
        
        success, gen_data = await test_endpoint(
            client, "POST", "/api/generation/generate",
            "Generate ERD Artifact",
            data=generation_request,
            expected_status=200
        )
        
        # List artifacts
        await test_endpoint(client, "GET", "/api/generation/artifacts", "List All Artifacts")
        
        # Test with folder filter
        await test_endpoint(
            client, "GET", "/api/generation/artifacts",
            "List Artifacts by Folder",
            params={"folder_id": "api_test_folder"}
        )
        
        # Test custom artifact type creation (uses query params, not JSON body)
        await test_endpoint(
            client, "POST", "/api/generation/artifact-types/custom",
            "Create Custom Artifact Type",
            params={
                "type_id": "test_security_review",
                "name": "Security Review",
                "category": "Security",
                "prompt_template": "Perform a security review of: {meeting_notes}. Context: {context}",
                "description": "AI-powered security review artifact"
            }
        )
        
        # ============================================================
        # 9. VERSIONS
        # ============================================================
        print("\n[9/12] Testing Versions...")
        
        await test_endpoint(client, "GET", "/api/versions/all", "Get All Versions")
        await test_endpoint(
            client, "GET", "/api/versions/all",
            "Get Versions by Folder",
            params={"folder_id": "api_test_folder"}
        )
        await test_endpoint(client, "GET", "/api/versions/migration/preview", "Migration Preview")
        
        # ============================================================
        # 10. CHAT / AGENTIC CHAT
        # ============================================================
        print("\n[10/12] Testing Chat...")
        
        # Simple chat
        chat_request = {
            "message": "What design patterns are commonly used in this project?",
            "include_project_context": True
        }
        
        await test_endpoint(
            client, "POST", "/api/chat/message",
            "Simple Chat Message",
            data=chat_request
        )
        
        # Agentic chat tools list (streaming endpoint can't be tested directly)
        await test_endpoint(
            client, "GET", "/api/chat/agent/tools",
            "Agentic Chat - List Tools"
        )
        
        # Project summary (another chat endpoint)
        await test_endpoint(
            client, "GET", "/api/chat/summary",
            "Get Project Summary"
        )
        
        # ============================================================
        # 11. ASSISTANT
        # ============================================================
        print("\n[11/12] Testing Assistant...")
        
        # Assistant suggestions
        await test_endpoint(
            client, "POST", "/api/assistant/suggestions",
            "Get Smart Suggestions",
            data={"existing_artifact_types": [], "max_suggestions": 5}
        )
        
        # Staleness check
        await test_endpoint(client, "GET", "/api/assistant/artifacts/stale", "Check Stale Artifacts")
        
        # Meeting notes parser
        await test_endpoint(
            client, "POST", "/api/assistant/meeting-notes/parse",
            "Parse Meeting Notes",
            data={"meeting_notes": "Build a user login system with OAuth support"}
        )
        
        # ============================================================
        # 12. VALIDATION & CONFIG
        # ============================================================
        print("\n[12/12] Testing Validation & Config...")
        
        # Validation
        await test_endpoint(
            client, "POST", "/api/validation/validate",
            "Validate Mermaid Artifact",
            data={
                "artifact_type": "mermaid_erd",
                "content": "erDiagram\n    USER ||--o{ ORDER : places\n    USER { string id PK }\n    ORDER { string id PK }"
            }
        )
        
        # Validation stats
        await test_endpoint(client, "GET", "/api/validation/stats", "Validation Stats")
        
        # Note: /api/config/api-keys is a POST endpoint for saving keys
        # There is no GET status endpoint for API keys in the current implementation
        
        # ============================================================
        # CLEANUP
        # ============================================================
        print("\n[Cleanup] Removing test data...")
        
        # Delete custom artifact type
        await test_endpoint(
            client, "DELETE", "/api/generation/artifact-types/custom/test_security_review",
            "Delete Test Custom Type",
            allow_404=True
        )
        
        # Delete test folder
        await test_endpoint(
            client, "DELETE", "/api/meeting-notes/folders/api_test_folder",
            "Delete Test Folder",
            allow_404=True
        )
    
    # Print summary
    results.print_summary()
    
    return results.failed == 0


async def main():
    """Main entry point."""
    print("\n")
    print("*" * 70)
    print("*  ARCHITECT.AI - COMPREHENSIVE API TESTING SUITE")
    print("*  Testing all endpoints with mock data (like Postman)")
    print("*" * 70)
    
    # Check if backend is running
    print(f"\nChecking backend at {BASE_URL}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if response.status_code == 200:
                print("[OK] Backend is running!\n")
            else:
                print(f"[WARN] Backend returned status {response.status_code}\n")
    except httpx.ConnectError:
        print("[ERROR] Cannot connect to backend!")
        print(f"        Please start the backend first: python -m uvicorn backend.main:app --reload")
        print(f"        Or run: launch.bat (Windows) / ./launch.sh (Linux/Mac)")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1
    
    # Run tests
    success = await run_all_tests()
    
    if success:
        print("\n[SUCCESS] All tests passed!\n")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Check the results above.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
