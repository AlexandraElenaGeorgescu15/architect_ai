import asyncio
import aiohttp
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connectivity(url):
    logger.info(f"Checking connectivity to {url}")
    
    # 1. Test HTTP Health
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/api/health") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("✅ HTTP Health Check: OK")
                    logger.info(f"Backend Status: {data.get('status')}")
                    logger.info(f"Ready: {data.get('ready')}")
                else:
                    logger.error(f"❌ HTTP Health Check failed with status {response.status}")
                    return False
    except Exception as e:
        logger.error(f"❌ HTTP connectivity error: {e}")
        return False

    # 2. Test WebSocket connection
    ws_url = url.replace("http", "ws") + "/ws/test_room"
    logger.info(f"Checking WebSocket connectivity to {ws_url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                logger.info("✅ WebSocket Connection: Established")
                
                # Check for connection established message
                msg = await ws.receive_json(timeout=5)
                if msg.get("type") == "connection.established":
                    logger.info("✅ WebSocket Protocol: OK (Received connection.established)")
                else:
                    logger.warning(f"⚠️ Received unexpected WS message: {msg}")

                # Test Ping/Pong
                await ws.send_json({"type": "ping"})
                msg = await ws.receive_json(timeout=2)
                if msg.get("type") == "pong":
                    logger.info("✅ WebSocket Roundtrip: OK (Received pong)")
                else:
                    logger.warning(f"⚠️ Did not receive pong: {msg}")

                await ws.close()
                logger.info("✅ WebSocket closed gracefully")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        return False

    return True

if __name__ == "__main__":
    target_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    
    asyncio.run(test_connectivity(target_url))
