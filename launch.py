#!/usr/bin/env python3
"""
Architect.AI Universal Launcher - FastAPI + React Edition
Cross-platform launcher for the Architect.AI application

Version: 3.5.2
"""
import os
import sys
import subprocess
import platform
import time
from pathlib import Path

# Disable telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True"


def main():
    """Launch Architect.AI with FastAPI backend and React frontend"""
    
    # Configure UTF-8 output for Windows
    if platform.system() == 'Windows':
        try:
            import io
            if not isinstance(sys.stdout, io.TextIOWrapper) or sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            if not isinstance(sys.stderr, io.TextIOWrapper) or sys.stderr.encoding != 'utf-8':
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, OSError, ValueError):
            pass
    
    banner = """
    ============================================================
       Architect.AI v3.5.2 - FastAPI + React Edition
    ============================================================
    
    Features:
      - FastAPI Backend (REST API + WebSocket)
      - React Frontend (TypeScript + Tailwind CSS)
      - Real-time Updates (WebSocket)
      - Artifact Generation (24+ types)
      - Model Management (Ollama, HuggingFace, Cloud)
      - Training System (LoRA/QLoRA)
      - RAG + Knowledge Graph + Pattern Mining
    
    Version: 3.5.2
    """
    print(banner)
    
    # Get project root
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.resolve()
    os.chdir(project_root)
    
    print(f"Project root: {project_root}\n")
    
    # Check Python version
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
        print("❌ ERROR: Python 3.9+ required")
        print(f"   Current: {py_version.major}.{py_version.minor}.{py_version.micro}")
        sys.exit(1)
    
    print(f"✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    # Check Node.js
    try:
        node_version = subprocess.check_output(['node', '--version'], stderr=subprocess.DEVNULL).decode().strip()
        print(f"✅ Node.js {node_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ERROR: Node.js 18+ required")
        print("   Install from https://nodejs.org/")
        sys.exit(1)
    
    # Check backend dependencies
    try:
        import fastapi
        print("✅ Backend dependencies installed")
    except ImportError:
        print("Installing backend dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Backend dependencies installed")
    
    # Check frontend dependencies
    frontend_dir = project_root / "frontend"
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.check_call(["npm", "install"], cwd=frontend_dir)
        print("✅ Frontend dependencies installed")
    else:
        print("✅ Frontend dependencies installed")
    
    print("\n" + "="*60)
    print("Starting Architect.AI...")
    print("="*60)
    print("\nBackend API:  http://localhost:8000")
    print("Frontend App: http://localhost:3000")
    print("API Docs:     http://localhost:8000/api/docs")
    print("\nPress Ctrl+C to stop both servers\n")
    
    # Start backend
    backend_cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--reload",
        "--host", "localhost",
        "--port", "8000",
        "--log-level", "debug",
        "--use-colors"
    ]
    
    # Start frontend
    frontend_cmd = ["npm", "run", "dev"]
    
    try:
        if platform.system() == 'Windows':
            # Windows: Start in separate windows
            # Windows: Start in separate windows (Frontend only)
            # Backend runs in same console to show logs
            subprocess.Popen(backend_cmd)
            time.sleep(3)
            subprocess.Popen(frontend_cmd, cwd=frontend_dir, creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("✅ Both servers started in separate windows")
            print("\nClose the windows to stop the servers")
            input("\nPress Enter to exit this launcher...")
        else:
            # Unix: Start in background
            backend_process = subprocess.Popen(backend_cmd)
            time.sleep(3)
            frontend_process = subprocess.Popen(frontend_cmd, cwd=frontend_dir)
            
            print("✅ Both servers started")
            print(f"   Backend PID: {backend_process.pid}")
            print(f"   Frontend PID: {frontend_process.pid}")
            print("\nPress Ctrl+C to stop...")
            
            try:
                backend_process.wait()
                frontend_process.wait()
            except KeyboardInterrupt:
                print("\n\nStopping servers...")
                backend_process.terminate()
                frontend_process.terminate()
                backend_process.wait()
                frontend_process.wait()
                print("✅ Servers stopped")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

