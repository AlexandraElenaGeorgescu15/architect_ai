
import asyncio
import httpx
import sys
import json
import logging
from typing import Dict, Any

# Configure logging to stdout for visibility
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

# Note: Auth is now by-passed, so we don't strictly need a valid token, 
# but we'll use a dummy one just in case middleware expects the header format.
HEADERS = {"Authorization": "Bearer skipped"}

async def run_feature_tests():
    """Run tests for Advanced Features: RAG, KG, Generation, Chat."""
    
    logger.info("🚀 STARTING ADVANCED FEATURE TEST")
    logger.info(f"Target: {BASE_URL}")
    
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        # 1. Health Check
        try:
             resp = await client.get(f"{BASE_URL}/api/health")
             logger.info(f"✅ Health Check: {resp.status_code}")
        except Exception as e:
             logger.error(f"❌ Health Check Failed: {e}")
             return

        # 2. RAG Search Test
        logger.info("\n🔎 Testing RAG Search...")
        try:
            # Search for a common term
            payload = {"query": "architecture", "k": 5}
            resp = await client.post(f"{BASE_URL}/api/rag/search", json=payload, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                logger.info(f"✅ RAG Search returned {len(results)} results")
                if results:
                    logger.info(f"   Snippet 1: {results[0].get('content')[:100]}...")
            else:
                logger.error(f"❌ RAG Search Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"❌ RAG Exception: {e}")

        # 3. Knowledge Graph Stats
        logger.info("\n🕸️ Testing Knowledge Graph...")
        try:
            resp = await client.get(f"{BASE_URL}/api/knowledge-graph/stats", headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"✅ KG Stats: {data}")
            else:
                logger.error(f"❌ KG Stats Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"❌ KG Exception: {e}")

        # 4. Chat Error Reproduction
        logger.info("\n💬 Testing Chat (Reproducing User Issue)...")
        try:
            # Query from user feedback causing error
            chat_payload = {
                "message": "i want to know how phones are ordered",
                "conversation_history": [],
                "session_id": "debug-session-1",
                "include_project_context": True
            }
            resp = await client.post(f"{BASE_URL}/api/chat/message", json=chat_payload, headers=HEADERS)
            if resp.status_code == 200:
                data = resp.json()
                logger.info(f"✅ Chat Success: {data.get('message')[:100]}...")
            else:
                logger.error(f"❌ Chat Failed (AS REPORTED): {resp.status_code}")
                logger.error(f"Response: {resp.text}")
        except Exception as e:
             logger.error(f"❌ Chat Exception: {e}")

        # 5. Generation Test (Real Artifact)
        logger.info("\n⚙️ Testing Generation (Reproducing Light Diagram Issue)...")
        try:
            # Request a code prototype (more complex than diagram) or simple diagram
            gen_payload = {
                "artifact_type": "code_prototype",
                "meeting_notes": "Write a python script that prints hello world.",
                "folder_id": None, 
                "context_id": None,
                "options": {
                    "temperature": 0.5,
                    "max_retries": 1
                }
            }
            # Note: /generate is synchronous-ish but returns job_id if taking long
            resp = await client.post(f"{BASE_URL}/api/generation/generate", json=gen_payload, headers=HEADERS)
            
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                job_id = data.get("job_id")
                logger.info(f"✅ Generation Request Accepted: Status={status}, JobID={job_id}")
                
                # Poll for completion if not done
                if status != "completed" and job_id:
                    for _ in range(10):
                        await asyncio.sleep(2)
                        job_resp = await client.get(f"{BASE_URL}/api/generation/jobs/{job_id}", headers=HEADERS)
                        job_data = job_resp.json()
                        current_status = job_data.get("status")
                        logger.info(f"   Polling Job {job_id}: {current_status}")
                        if current_status in ["completed", "failed"]:
                            if current_status == "completed":
                                content = job_data.get("artifact", {}).get("content", "")
                                logger.info(f"✅ Generation Completed. Content Length: {len(content)}")
                                logger.info(f"Content Preview: {content[:100]}...")
                            else:
                                logger.error(f"❌ Generation Failed: {job_data.get('error')}")
                            break
            else:
                logger.error(f"❌ Generation Request Failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            logger.error(f"❌ Generation Exception: {e}")

    logger.info("\n✅ ADVANCED TEST COMPLETE")

if __name__ == "__main__":
    try:
        asyncio.run(run_feature_tests())
    except KeyboardInterrupt:
        pass
