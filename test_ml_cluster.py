
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT = "/api/analysis/ml-features/project/cluster"

print(f"Testing {BASE_URL}{ENDPOINT}...")

try:
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}{ENDPOINT}",
        json={"n_clusters": 3, "max_files": 10},
        timeout=30  # 30 second timeout
    )
    elapsed = time.time() - start_time
    
    print(f"Status Code: {response.status_code}")
    print(f"Time Taken: {elapsed:.2f}s")
    
    if response.status_code == 200:
        print("Success!")
        print(json.dumps(response.json(), indent=2))
    else:
        print("Error:")
        print(response.text)
        
except Exception as e:
    print(f"Exception: {e}")
