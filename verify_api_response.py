
import sys
import os
import asyncio
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

async def verify_api_response():
    print("Verifying API Project Target Response...")
    
    try:
        from backend.api.project_target import get_target_info, TargetResponse
        
        # Mock settings if needed (though config imports should handle it)
        
        response = await get_target_info()
        print("\nAPI Response:")
        # Convert pydantic model to dict
        data = response.model_dump()
        print(json.dumps(data, indent=2))
        
        projects = data.get("available_projects", [])
        print(f"\nProjects Found in API: {len(projects)}")
        for p in projects:
            print(f"- {p['name']} (Score: {p['score']})")
            
    except Exception as e:
        print(f"Error calling API function: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_api_response())
