#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple generation test with longer timeout."""

import asyncio
import httpx
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

async def test_generation():
    """Test generation endpoint with 120s timeout."""
    print("Testing generation endpoint with 120s timeout...")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("Sending generation request...")
            response = await client.post(
                'http://localhost:8000/api/generation/generate',
                json={
                    'artifact_type': 'mermaid_flowchart',
                    'meeting_notes': 'Create a simple flowchart for user login: enter credentials, validate, if valid go to dashboard, if invalid show error.',
                    'options': {'max_retries': 1, 'temperature': 0.2}
                }
            )
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Job ID: {data.get('job_id', 'N/A')}")
                print(f"Status: {data.get('status', 'N/A')}")
                
                if data.get('artifact'):
                    artifact = data['artifact']
                    print(f"\n=== Artifact Generated ===")
                    print(f"Artifact Type: {artifact.get('artifact_type', 'N/A')}")
                    print(f"Model Used: {artifact.get('model_used', 'N/A')}")
                    
                    validation = artifact.get('validation', {})
                    print(f"Validation Score: {validation.get('score', 0)}")
                    print(f"Is Valid: {validation.get('is_valid', False)}")
                    
                    content = artifact.get('content', '')
                    print(f"Content Length: {len(content)} chars")
                    print(f"\n=== Content Preview (first 800 chars) ===")
                    print(content[:800])
                    print("=" * 50)
                    return True
                else:
                    print("Note: Artifact not yet ready, check via WebSocket or job status")
                    return True
            else:
                print(f"Error Response: {response.text[:500]}")
                return False
                
        except httpx.ReadTimeout:
            print("ERROR: Request timed out after 120s")
            return False
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
            return False

async def test_artifact_types():
    """Test listing artifact types."""
    print("\nTesting artifact types listing...")
    print("-" * 50)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get('http://localhost:8000/api/generation/artifact-types')
            print(f"Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                types = data.get('artifact_types', [])
                print(f"Total artifact types: {len(types)}")
                
                # Group by category
                categories = {}
                for t in types:
                    cat = t.get('category', 'unknown')
                    categories[cat] = categories.get(cat, 0) + 1
                
                print("By category:")
                for cat, count in categories.items():
                    print(f"  - {cat}: {count} types")
                return True
            else:
                print(f"Error: {response.text[:300]}")
                return False
        except Exception as e:
            print(f"ERROR: {e}")
            return False

async def test_custom_artifact_crud():
    """Test custom artifact type CRUD."""
    print("\nTesting custom artifact CRUD...")
    print("-" * 50)
    
    import time
    test_id = f"test_type_{int(time.time())}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # CREATE
        print(f"Creating custom type: {test_id}")
        create_resp = await client.post(
            'http://localhost:8000/api/generation/artifact-types/custom',
            params={
                'type_id': test_id,
                'name': 'Test Custom Type',
                'category': 'Testing',
                'prompt_template': 'Generate a test for: {meeting_notes}',
                'description': 'Test custom type'
            }
        )
        print(f"  CREATE: {create_resp.status_code}")
        
        # READ
        read_resp = await client.get(f'http://localhost:8000/api/generation/artifact-types/custom/{test_id}')
        print(f"  READ: {read_resp.status_code}")
        
        # UPDATE
        update_resp = await client.put(
            f'http://localhost:8000/api/generation/artifact-types/custom/{test_id}',
            params={'description': 'Updated description'}
        )
        print(f"  UPDATE: {update_resp.status_code}")
        
        # DELETE
        delete_resp = await client.delete(f'http://localhost:8000/api/generation/artifact-types/custom/{test_id}')
        print(f"  DELETE: {delete_resp.status_code}")
        
        success = all([
            create_resp.status_code == 200,
            read_resp.status_code == 200,
            update_resp.status_code == 200,
            delete_resp.status_code == 200
        ])
        print(f"CRUD Test: {'PASSED' if success else 'FAILED'}")
        return success

async def main():
    """Run all tests."""
    print("=" * 60)
    print("FOCUSED ENDPOINT TESTS")
    print("=" * 60)
    
    results = []
    
    # Test artifact types first (faster)
    results.append(("Artifact Types", await test_artifact_types()))
    
    # Test custom artifact CRUD
    results.append(("Custom Artifact CRUD", await test_custom_artifact_crud()))
    
    # Test generation (slower, do last)
    results.append(("Generation", await test_generation()))
    
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "PASS" if success else "FAIL"
        emoji = "[OK]" if success else "[X]"
        print(f"  {emoji} {name}: {status}")
    
    passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {passed}/{len(results)} tests passed")

if __name__ == "__main__":
    asyncio.run(main())
