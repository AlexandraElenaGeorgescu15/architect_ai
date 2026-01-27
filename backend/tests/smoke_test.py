
import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}", flush=True)

def test_backend_health():
    log("Checking Backend Health...")
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=10)
        if resp.status_code == 200:
            log("Backend is UP", "PASS")
        else:
            log(f"Backend returned {resp.status_code}", "FAIL")
            sys.exit(1)
    except Exception as e:
        log(f"Could not connect to backend: {e}", "FAIL")
        sys.exit(1)

def test_generation_flow():
    log("Testing Artifact Generation Flow...")
    payload = {
        "artifact_type": "mermaid_erd",
        "meeting_notes": "A simple user management system with Users and Roles",
        "email": "test@example.com"
    }
    
    try:
        log(f"Sending POST to {BASE_URL}/api/generation/generate ...")
        resp = requests.post(f"{BASE_URL}/api/generation/generate", json=payload, timeout=120)
        log(f"Response status: {resp.status_code}")
        if resp.status_code != 200:
            log(f"Generation failed: {resp.text}", "FAIL")
            return
            
        data = resp.json()
        artifact_id = data.get("artifact_id")
        log(f"Generation started. Artifact ID: {artifact_id}", "PASS")
        
        # Poll for completion (max 20s)
        for _ in range(10):
            time.sleep(2)
            check = requests.get(f"{BASE_URL}/api/generation/artifacts/{artifact_id}", timeout=10)
            if check.status_code == 200:
                artifact = check.json()
                content = artifact.get("content", "")
                if content and len(content) > 10:
                    log(f"Artifact content generated: {len(content)} chars", "PASS")
                    return
        log("Generation timed out or returned empty content", "WARN")
        
    except Exception as e:
        log(f"Generation flow error: {e}", "FAIL")

def test_chat_flow():
    log("Testing Agent Chat Flow...")
    payload = {
        "message": "What is the architecture of this project?", 
        "conversation_history": [],
        "include_project_context": True
    }
    
    try:
        log(f"Sending POST to {BASE_URL}/api/chat/message ...")
        resp = requests.post(f"{BASE_URL}/api/chat/message", json=payload, timeout=120)
        log(f"Response status: {resp.status_code}")
        if resp.status_code == 200:
            log("Chat endpoint responsive", "PASS")
        else:
            log(f"Chat failed: {resp.status_code} - {resp.text}", "FAIL")
            
    except Exception as e:
        log(f"Chat flow error: {e}", "FAIL")

def run_all():
    print("[START] STARTING SMOKE TEST", flush=True)
    test_backend_health()
    test_generation_flow()
    test_chat_flow()
    print("[DONE] SMOKE TEST COMPLETE", flush=True)

if __name__ == "__main__":
    run_all()
