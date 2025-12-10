#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick setup verification script for Architect.AI v3.5.2
Run this to check if everything is configured correctly
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

# Enable UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, OSError):
        pass

print("=" * 60)
print("🔍 Architect.AI v3.5.2 Setup Verification")
print("=" * 60)
print()

# Check 1: Python Version
print("✓ Python Version:")
print(f"  {sys.version}")
if sys.version_info < (3, 10):
    print("  ⚠️  Python 3.10+ recommended")
print()

# Check 2: Node.js Version
print("✓ Node.js Version:")
try:
    result = subprocess.run(['node', '--version'], 
                          capture_output=True, 
                          text=True, 
                          timeout=5)
    if result.returncode == 0:
        version = result.stdout.strip()
        print(f"  ✅ {version}")
    else:
        print(f"  ❌ Not installed")
except FileNotFoundError:
    print(f"  ❌ Not found in PATH")
except Exception as e:
    print(f"  ❌ Error: {e}")
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
        print(f"  ⚠️  Not installed (optional - for local models)")
except FileNotFoundError:
    print(f"  ⚠️  Not found in PATH (optional - for local models)")
except subprocess.TimeoutExpired:
    print(f"  ⚠️  Command timed out")
except Exception as e:
    print(f"  ⚠️  Error: {e}")
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
            for model in models[:5]:  # Show first 5
                name = model.get('name', 'unknown')
                size_gb = model.get('size', 0) / (1024**3)
                print(f"     • {name} ({size_gb:.1f} GB)")
            if len(models) > 5:
                print(f"     ... and {len(models) - 5} more")
        else:
            print(f"  ⚠️  Server running but no models downloaded")
            print(f"     Run: ollama pull deepseek-coder:6.7b")
    else:
        print(f"  ⚠️  Server responded with status {response.status_code}")
except requests.exceptions.ConnectionError:
    print(f"  ⚠️  Not running (optional - for local models)")
except requests.exceptions.Timeout:
    print(f"  ⚠️  Server not responding (timeout)")
except Exception as e:
    print(f"  ⚠️  Error: {e}")
print()

# Check 5: Project Structure
print("✓ Project Structure:")
project_root = Path(__file__).parent.parent
key_dirs = ['backend', 'frontend', 'rag', 'agents', 'data', 'outputs', 'context']
all_exist = True
for dir_name in key_dirs:
    dir_path = project_root / dir_name
    if dir_path.exists():
        print(f"  ✅ {dir_name}/ exists")
    else:
        print(f"  ⚠️  {dir_name}/ missing")
        all_exist = False
print()

# Check 6: Key Files
print("✓ Key Files:")
key_files = [
    'launch.py',
    'backend/main.py',
    'frontend/package.json',
    'requirements.txt',
    '.cursorrules'
]
for file_name in key_files:
    file_path = project_root / file_name
    if file_path.exists():
        print(f"  ✅ {file_name}")
    else:
        print(f"  ❌ {file_name} missing")
print()

# Check 7: Python Dependencies
print("✓ Python Dependencies:")
dependencies = [
    ('fastapi', 'FastAPI'),
    ('uvicorn', 'Uvicorn'),
    ('pydantic', 'Pydantic'),
    ('sqlalchemy', 'SQLAlchemy'),
    ('chromadb', 'ChromaDB'),
    ('sentence_transformers', 'Sentence Transformers'),
    ('networkx', 'NetworkX'),
]

for module_name, display_name in dependencies:
    try:
        module = __import__(module_name)
        version = getattr(module, '__version__', 'installed')
        print(f"  ✅ {display_name} ({version})")
    except ImportError:
        print(f"  ❌ {display_name} not installed")

# Optional dependencies
optional_deps = [
    ('groq', 'Groq'),
    ('google.generativeai', 'Google Generative AI'),
    ('openai', 'OpenAI'),
    ('anthropic', 'Anthropic'),
]

print("\n  Optional AI providers:")
for module_name, display_name in optional_deps:
    try:
        __import__(module_name)
        print(f"  ✅ {display_name}")
    except ImportError:
        print(f"  ⚠️  {display_name} (optional)")
print()

# Check 8: Frontend Dependencies
print("✓ Frontend Dependencies:")
node_modules = project_root / 'frontend' / 'node_modules'
if node_modules.exists():
    print(f"  ✅ node_modules exists")
else:
    print(f"  ❌ node_modules missing")
    print(f"     Run: cd frontend && npm install")
print()

# Check 9: API Keys
print("✓ API Keys:")
api_keys = [
    ('GEMINI_API_KEY', 'Gemini'),
    ('GOOGLE_API_KEY', 'Gemini (alt)'),
    ('GROQ_API_KEY', 'Groq'),
    ('OPENAI_API_KEY', 'OpenAI'),
    ('ANTHROPIC_API_KEY', 'Anthropic'),
]

keys_found = 0
for env_var, display_name in api_keys:
    value = os.environ.get(env_var)
    if value:
        keys_found += 1
        print(f"  ✅ {display_name} ({env_var[:10]}...)")

if keys_found == 0:
    print(f"  ⚠️  No API keys found in environment")
    print(f"     Create .env file or set environment variables")
print()

# Summary
print("=" * 60)
print("📊 Summary:")
print("=" * 60)

issues = []
warnings = []

# Check critical dependencies
try:
    import fastapi
except ImportError:
    issues.append("FastAPI not installed - run: pip install -r requirements.txt")

if not (project_root / 'backend' / 'main.py').exists():
    issues.append("Backend main.py missing")

if not node_modules.exists():
    warnings.append("Frontend dependencies not installed - run: cd frontend && npm install")

if keys_found == 0:
    warnings.append("No API keys configured (cloud models won't work)")

if issues:
    print("\n❌ Critical issues found:")
    for issue in issues:
        print(f"  • {issue}")

if warnings:
    print("\n⚠️  Warnings:")
    for warning in warnings:
        print(f"  • {warning}")

if not issues and not warnings:
    print("\n✅ Everything looks good!")

print("\n🚀 To launch Architect.AI:")
print("   python launch.py")
print()
print("   This will start:")
print("   • Backend API:  http://localhost:8000")
print("   • Frontend App: http://localhost:3000")
print("   • API Docs:     http://localhost:8000/api/docs")
print()
