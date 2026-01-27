
import sys
import asyncio
import json
import urllib.request
import urllib.error

def trigger_api():
    print("Calling API to reindex user projects...")
    url = "http://localhost:8000/api/rag/reindex-user-projects"
    
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print("Response:")
            print(json.dumps(data, indent=2))
            
            if data.get("success"):
                print("✅ Successfully triggered reindex API.")
            else:
                print("API returned failure.")
                
    except urllib.error.URLError as e:
        print(f"Could not connect to backend at {url}")
        print(f"Reason: {e}")
        print("Make sure the backend is running!")
        
    # Also check status after a brief pause
    print("\nChecking status...")
    status_url = "http://localhost:8000/api/rag/status"
    try:
        with urllib.request.urlopen(status_url) as response:
            data = json.loads(response.read().decode())
            print("Current Status:")
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error checking status: {e}")

if __name__ == "__main__":
    trigger_api()
