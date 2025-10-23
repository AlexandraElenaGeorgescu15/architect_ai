#!/usr/bin/env python3
"""
Architect.AI Universal Launcher
Cross-platform launcher for the Architect.AI application

Version: 2.1.0
Author: Alexandru Stefan (alestef81@gmail.com)
License: Proprietary - Internal use only
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def main():
    """Launch Architect.AI with proper environment setup"""
    
    # Configure UTF-8 output for Windows
    if platform.system() == 'Windows':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    
    # ASCII Art Banner (safe characters only)
    banner = """
    ============================================================
       Architect.AI v2.1 - Production Dual-Mode System
    ============================================================
    
    Starting the application with:
      - Developer Mode (Technical diagrams, ERD, code)
      - Product/PM Mode (Visual playground, Ask AI)
    
    Version: 2.1.0
    Contact: alestef81@gmail.com
    
    """
    print(banner)
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)
    
    print(f"Current directory: {script_dir}\n")
    
    # Check Python version
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 9):
        print("❌ ERROR: Python 3.9+ required")
        print(f"   Current version: {py_version.major}.{py_version.minor}.{py_version.micro}")
        sys.exit(1)
    
    print(f"✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    # Check if requirements are installed
    try:
        import streamlit
        print("✅ Streamlit installed")
    except ImportError:
        print("❌ Streamlit not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed")
    
    # Check for API key
    env_file = script_dir / ".env"
    has_api_key = False
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('GEMINI_API_KEY=') and len(line.strip()) > 16:
                    has_api_key = True
                    break
    
    if has_api_key:
        print("✅ API key found in .env")
    else:
        print("⚠️  No API key in .env - you'll need to enter it in the app")
    
    # Prepare Streamlit command
    app_path = script_dir / "app" / "app_v2.py"
    
    if not app_path.exists():
        print(f"❌ ERROR: Application file not found: {app_path}")
        sys.exit(1)
    
    print(f"\nLaunching Streamlit app...")
    print(f"App path: {app_path}")
    print(f"\nThe app will open in your browser automatically")
    print(f"URL: http://localhost:8501\n")
    print(f"Keep this window open while using the app")
    print(f"Press Ctrl+C to stop the app\n")
    print("="*60)
    
    # Launch Streamlit
    try:
        # Use streamlit run with proper arguments
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            str(app_path),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.fileWatcherType", "none"
        ]
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n\n✅ Application stopped by user")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR: Application failed to start")
        print(f"   Error code: {e.returncode}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

