#!/usr/bin/env python3
"""
Quick setup verification script for Architect.AI
Run this to check if everything is configured correctly
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

print("=" * 60)
print("🔍 Architect.AI Setup Verification")
print("=" * 60)
print()

# Check 1: Python Version
print("✓ Python Version:")
print(f"  {sys.version}")
print()

# Check 2: HuggingFace Token
print("✓ HuggingFace Token:")
hf_token = os.environ.get('HF_TOKEN')
if hf_token and hf_token.startswith('hf_'):
    print(f"  ✅ Set (starts with: {hf_token[:15]}...)")
else:
    print(f"  ⚠️  Not set (optional - only needed for model downloads)")
print()

# Check 3: Ollama Installation
print("✓ Ollama Installation:")
try:
    result = subprocess.run(['ollama', '--version'], 
                          capture_output=True, 
                          text=True, 
                          timeout=5)
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"  ✅ Installed: {version}")
    else:
        print(f"  ❌ Not installed")
except FileNotFoundError:
    print(f"  ❌ Not found in PATH")
except subprocess.TimeoutExpired:
    print(f"  ⚠️  Command timed out")
except Exception as e:
    print(f"  ❌ Error: {e}")
print()

# Check 4: Ollama Server Status
print("✓ Ollama Server:")
try:
    response = requests.get('http://localhost:11434/api/tags', timeout=2)
    if response.status_code == 200:
        print(f"  ✅ Running on http://localhost:11434")
        models = response.json().get('models', [])
        if models:
            print(f"  ✅ {len(models)} model(s) downloaded:")
            for model in models:
                name = model.get('name', 'unknown')
                size_gb = model.get('size', 0) / (1024**3)
                print(f"     • {name} ({size_gb:.1f} GB)")
        else:
            print(f"  ⚠️  Server running but no models downloaded")
            print(f"     Run: ollama pull llama3.2:3b")
    else:
        print(f"  ❌ Server responded with status {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ❌ Not running (connection refused)")
    print(f"     The 'bind' error you saw means it's already running!")
    print(f"     Try: ollama list")
except requests.exceptions.Timeout:
    print(f"  ⚠️  Server not responding (timeout)")
except Exception as e:
    print(f"  ❌ Error: {e}")
print()

# Check 5: Project Structure
print("✓ Project Structure:")
project_root = Path(__file__).parent
key_dirs = ['app', 'components', 'agents', 'rag', 'outputs']
all_exist = True
for dir_name in key_dirs:
    dir_path = project_root / dir_name
    if dir_path.exists():
        print(f"  ✅ {dir_name}/ exists")
    else:
        print(f"  ❌ {dir_name}/ missing")
        all_exist = False
print()

# Check 6: Key Files
print("✓ Key Files:")
key_files = ['launch.py', 'app/app_v2.py', 'components/mermaid_preprocessor.py']
for file_name in key_files:
    file_path = project_root / file_name
    if file_path.exists():
        print(f"  ✅ {file_name}")
    else:
        print(f"  ❌ {file_name} missing")
print()

# Check 7: Dependencies
print("✓ Python Dependencies:")
try:
    import streamlit
    print(f"  ✅ streamlit {streamlit.__version__}")
except ImportError:
    print(f"  ❌ streamlit not installed")

try:
    import chromadb
    print(f"  ✅ chromadb installed")
except ImportError:
    print(f"  ❌ chromadb not installed")

try:
    import groq
    print(f"  ✅ groq installed")
except ImportError:
    print(f"  ⚠️  groq not installed (optional)")

try:
    import google.generativeai
    print(f"  ✅ google-generativeai installed")
except ImportError:
    print(f"  ⚠️  google-generativeai not installed (optional)")
print()

# Summary
print("=" * 60)
print("📊 Summary:")
print("=" * 60)

issues = []
if not hf_token:
    issues.append("HuggingFace token not set (optional)")

# Try to check models via subprocess
try:
    result = subprocess.run(['ollama', 'list'], 
                          capture_output=True, 
                          text=True, 
                          timeout=5)
    if result.returncode == 0 and 'NAME' in result.stdout:
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:  # Only header, no models
            issues.append("No Ollama models downloaded")
except:
    issues.append("Could not check Ollama models")

if issues:
    print("\n⚠️  Minor issues found:")
    for issue in issues:
        print(f"  • {issue}")
    print("\n💡 Recommendations:")
    if "No Ollama models downloaded" in str(issues):
        print("  Run: ollama pull llama3.2:3b")
    if "HuggingFace token not set" in str(issues):
        print("  Set HF_TOKEN environment variable (optional)")
else:
    print("\n✅ Everything looks good!")

print("\n🚀 Ready to launch:")
print("   python launch.py")
print()

