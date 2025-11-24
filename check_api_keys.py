"""
API Key Configuration Checker
Helps diagnose API key configuration issues
"""

import os
from pathlib import Path
from backend.core.config import settings

print("=" * 60)
print("API KEY CONFIGURATION CHECK")
print("=" * 60)
print()

# Check .env file locations
env_files = [".env", "../.env", "../../.env"]
print("📁 Checking .env file locations:")
for env_file in env_files:
    env_path = Path(env_file)
    if env_path.exists():
        print(f"  ✅ Found: {env_path.resolve()}")
    else:
        print(f"  ❌ Not found: {env_file}")
print()

# Check what the settings object has loaded
print("🔑 API Keys loaded by settings:")
print(f"  OPENAI_API_KEY: {'✅ SET' if settings.openai_api_key else '❌ NOT SET'}")
if settings.openai_api_key:
    print(f"    Value preview: {settings.openai_api_key[:10]}...")
    
print(f"  GROQ_API_KEY: {'✅ SET' if settings.groq_api_key else '❌ NOT SET'}")
if settings.groq_api_key:
    print(f"    Value preview: {settings.groq_api_key[:10]}...")
    
print(f"  GOOGLE_API_KEY (Gemini): {'✅ SET' if settings.google_api_key else '❌ NOT SET'}")
if settings.google_api_key:
    print(f"    Value preview: {settings.google_api_key[:10]}...")
    
print(f"  GEMINI_API_KEY: {'✅ SET' if settings.gemini_api_key else '❌ NOT SET'}")
if settings.gemini_api_key:
    print(f"    Value preview: {settings.gemini_api_key[:10]}...")
    
print(f"  XAI_API_KEY (Grok): {'✅ SET' if settings.xai_api_key else '❌ NOT SET'}")
if settings.xai_api_key:
    print(f"    Value preview: {settings.xai_api_key[:10]}...")
    
print(f"  ANTHROPIC_API_KEY: {'✅ SET' if settings.anthropic_api_key else '❌ NOT SET'}")
if settings.anthropic_api_key:
    print(f"    Value preview: {settings.anthropic_api_key[:10]}...")
print()

# Check environment variables directly
print("🌍 Environment variables (direct check):")
env_keys = [
    "OPENAI_API_KEY",
    "GROQ_API_KEY", 
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "XAI_API_KEY",
    "ANTHROPIC_API_KEY"
]

for key in env_keys:
    value = os.getenv(key)
    if value:
        print(f"  ✅ {key}: {value[:10]}...")
    else:
        print(f"  ❌ {key}: Not set in environment")
print()

# Provide recommendations
print("=" * 60)
print("💡 RECOMMENDATIONS:")
print("=" * 60)

issues = []

if settings.openai_api_key and not settings.groq_api_key:
    issues.append("⚠️  You have OpenAI key but NO Groq key")
    print("⚠️  Issue: OpenAI key is set, but Groq key is missing")
    print("   Fix: Add to .env file:")
    print("   GROQ_API_KEY=gsk_your_groq_api_key_here")
    print()

if not settings.groq_api_key and not settings.xai_api_key:
    print("❌ No Groq/Grok API key detected")
    print("   To add Groq API key, add to .env file:")
    print("   GROQ_API_KEY=gsk_...")
    print()

if settings.openai_api_key:
    print("✅ OpenAI key is configured")
    print("   Models available: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo")
    print()
    
if not settings.openai_api_key:
    print("ℹ️  No OpenAI key (this is fine if you don't use it)")
    print()

# Check model registry
try:
    from backend.services.model_service import get_service
    model_service = get_service()
    
    print("=" * 60)
    print("📊 MODEL AVAILABILITY:")
    print("=" * 60)
    
    providers = {}
    for model_id, model in model_service.models.items():
        provider = model.provider
        if provider not in providers:
            providers[provider] = {"available": 0, "no_key": 0, "total": 0}
        
        providers[provider]["total"] += 1
        if model.status == "available":
            providers[provider]["available"] += 1
        elif model.status == "no_api_key":
            providers[provider]["no_key"] += 1
    
    for provider, counts in sorted(providers.items()):
        status = "✅" if counts["available"] > 0 else "❌"
        print(f"{status} {provider.upper()}: {counts['available']}/{counts['total']} available")
        if counts["no_key"] > 0:
            print(f"   ({counts['no_key']} models need API key)")
    print()
    
except Exception as e:
    print(f"Could not load model service: {e}")
    print()

print("=" * 60)
print("🔧 QUICK FIX:")
print("=" * 60)
print("1. Edit your .env file (in architect_ai_cursor_poc/.env)")
print("2. Add/fix these lines:")
print()
print("   # Groq API (for Llama/Mixtral models)")
print("   GROQ_API_KEY=gsk_your_key_here")
print()
print("   # OpenAI API (if you use it)")
print("   OPENAI_API_KEY=sk-your_key_here")
print()
print("   # Remove any API keys you don't have:")
print("   # Just delete or comment out (#) those lines")
print()
print("3. Restart the backend:")
print("   Ctrl+C (stop)")
print("   python launch.py (start)")
print()
print("=" * 60)

