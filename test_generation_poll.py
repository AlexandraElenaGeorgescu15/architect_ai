
import asyncio
import httpx
import sys
import time
import json

async def poll_generation():
    print("Starting generation polling test...")
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Start generation
        print("Sending generation request...")
        response = await client.post(
            'http://localhost:8000/api/generation/generate',
            json={
                'artifact_type': 'mermaid_flowchart',
                'meeting_notes': 'Create a simple flowchart for user login: enter credentials, validate, if valid go to dashboard, if invalid show error.',
                'options': {'max_retries': 2, 'temperature': 0.1} 
            }
        )
        
        if response.status_code != 200:
            print(f"Failed to start generation: {response.text}")
            return
            
        data = response.json()
        job_id = data.get('job_id')
        print(f"Job ID: {job_id}")
        
        # Poll status
        start_time = time.time()
        while time.time() - start_time < 120:
            status_resp = await client.get(f'http://localhost:8000/api/generation/jobs/{job_id}')
            if status_resp.status_code != 200:
                print(f"Failed to get status: {status_resp.status_code}")
                await asyncio.sleep(2)
                continue
                
            status_data = status_resp.json()
            status = status_data.get('status')
            print(f"Status: {status}")
            
            if status == 'completed':
                print("Generation COMPLETED!")
                print(json.dumps(status_data, indent=2))
                return
            elif status == 'failed':
                print("Generation FAILED!")
                print(json.dumps(status_data, indent=2))
                return
                
            await asyncio.sleep(2)
            
        print("Timed out waiting for generation")

if __name__ == "__main__":
    asyncio.run(poll_generation())
