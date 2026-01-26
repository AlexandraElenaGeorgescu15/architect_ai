
import asyncio
import httpx
import sys
import json
import logging
from typing import Dict, Any

# Configure logging
sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"
USERNAME = "admin"
PASSWORD = "admin"

async def run_workflow_test():
    """Run comprehensive workflow tests against the running backend."""
    
    logger.info("🚀 STARTING WORKFLOW SIMULATION")
    logger.info(f"Target: {BASE_URL}")
    
    # Enable redirect following
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Debug: Check Health
        try:
             resp = await client.get(f"{BASE_URL}/api/health")
             logger.info(f"Health Check: {resp.status_code}")
        except Exception as e:
             logger.error(f"Health Check Failed: {e}")

        HEADERS = {}

        # ======================================================================
        # 1. AUTHENTICATION WORKFLOW
        # ======================================================================
        logger.info("\nChecking Auth Workflow...")
        try:
            # Login
            login_url = f"{BASE_URL}/api/auth/token"
            logger.info(f"POST {login_url}")
            response = await client.post(
                login_url,
                data={"username": USERNAME, "password": PASSWORD}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data["access_token"]
                logger.info("✅ Login successful")
                
                # Set headers for future requests
                HEADERS = {"Authorization": f"Bearer {access_token}"}
            else:
                logger.error(f"❌ Login failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
            # Verify Token (/users/me)
            response = await client.get(f"{BASE_URL}/api/auth/me", headers=HEADERS)
            if response.status_code == 200:
                user_data = response.json()
                logger.info(f"✅ Verified User: {user_data.get('username')}")
            else:
                logger.error(f"❌ Failed to verify user: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Auth Exception: {e}")
            return False

        # ======================================================================
        # 2. MODEL MANAGEMENT WORKFLOW
        # ======================================================================
        logger.info("\nChecking Model Management Workflow...")
        try:
            # Endpoints often redirect /foo -> /foo/
            response = await client.get(f"{BASE_URL}/api/models/", headers=HEADERS)
            if response.status_code == 200:
                models = response.json()
                logger.info(f"✅ Retrieved {len(models)} models")
                # Check for at least one model
                if len(models) > 0:
                     logger.info(f"   Sample: {models[0].get('id')}")
            else:
                logger.warning(f"⚠️ Failed to list models: {response.status_code}")
        except Exception as e:
             logger.error(f"❌ Model Mgmt Exception: {e}")


        # ======================================================================
        # 3. CHAT WORKFLOW
        # ======================================================================
        logger.info("\nChecking Chat Workflow...")
        try:
            # Simple chat message
            chat_payload = {
                "message": "Hello, are you ready?",
                "conversation_history": [],
                "session_id": "test-session-1",
                "include_project_context": False
            }
            
            # Endpoint: /api/chat/message (POST)
            response = await client.post(f"{BASE_URL}/api/chat/message", json=chat_payload, headers=HEADERS)
            
            if response.status_code == 200:
                try:
                    chat_response = response.json()
                    logger.info(f"✅ Chat Response Received: {chat_response.get('message', '')[:50]}...")
                except:
                     logger.info(f"✅ Chat Response Received (Raw): {response.text[:50]}...")

            else:
                # 422 is common if schema mismatch, 500 if backend error
                logger.warning(f"⚠️ Chat request failed: {response.status_code}")
                logger.warning(f"Response: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Chat Exception: {e}")

        # ======================================================================
        # 4. GENERATION WORKFLOW (Templates)
        # ======================================================================
        logger.info("\nChecking Templates Workflow...")
        try:
            # List templates
            response = await client.get(f"{BASE_URL}/api/templates/", headers=HEADERS)
            if response.status_code == 200:
                 templates = response.json()
                 logger.info(f"✅ Retrieved Templates: {len(templates)}")
            else:
                 logger.warning(f"⚠️ Templates request failed: {response.status_code}")
            
        except Exception as e:
             logger.error(f"❌ Generation/Template Exception: {e}")

    logger.info("\n✅ WORKFLOW SIMULATION COMPLETE")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(run_workflow_test())
    except KeyboardInterrupt:
        logger.info("Test cancelled.")
