# API Keys Setup Guide 🔑

Complete guide to setting up API keys for Architect.AI's cloud models.

---

## Overview

Architect.AI supports multiple AI providers:

| Provider | Models | Free Tier | Speed | Quality | Best For |
|----------|--------|-----------|-------|---------|----------|
| **Google Gemini** | Gemini 2.0 Flash, 1.5 Pro, 1.5 Flash | ✅ Yes (60 req/min) | ⚡ Fast | ⭐⭐⭐⭐⭐ | General use, diagrams |
| **OpenAI** | GPT-4 Turbo, GPT-4, GPT-3.5 | ❌ No | 🐢 Slow | ⭐⭐⭐⭐⭐ | Complex code, APIs |
| **Groq** | Llama 3.3 70B, Llama 3.1, Mixtral | ✅ Yes | ⚡⚡⚡ Fastest | ⭐⭐⭐⭐ | Fast inference, prototypes |
| **Anthropic** | Claude 3.5 Sonnet, Opus, Sonnet | ❌ No | 🐢 Slow | ⭐⭐⭐⭐⭐ | Documentation, analysis |
| **Ollama (Local)** | DeepSeek, Qwen, Mistral, CodeLlama | ✅ Free | ⚡ Fast | ⭐⭐⭐⭐ | Privacy, no API costs |

**Recommendation:**
- **Best free option**: Gemini 2.0 Flash (60 requests/minute free tier)
- **Best paid option**: OpenAI GPT-4 Turbo + Gemini 1.5 Pro
- **Best for privacy**: Ollama (runs locally, no API calls)

---

## Step-by-Step Setup

### 1. Create `.env` File

In the `architect_ai_cursor_poc/` directory, create a `.env` file:

```bash
# Windows (PowerShell)
New-Item .env -ItemType File

# Linux/Mac
touch .env
```

### 2. Add API Keys

Open `.env` in a text editor and add your keys:

```bash
# Google Gemini (recommended)
GEMINI_API_KEY=AIzaSy...your_key_here

# OpenAI
OPENAI_API_KEY=sk-...your_key_here

# Groq
GROQ_API_KEY=gsk_...your_key_here

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...your_key_here

# X.AI (Grok) - alternative to Groq
XAI_API_KEY=xai-...your_key_here
```

**Important:**
- ✅ No quotes needed around keys
- ✅ One key per line
- ✅ No spaces before/after `=`
- ❌ Don't commit `.env` to Git (already in `.gitignore`)

### 3. Restart the Application

```bash
# Stop the running app (Ctrl+C)
# Restart
python launch.py
```

### 4. Verify Keys

Run the diagnostic script:

```bash
cd architect_ai_cursor_poc
python check_api_keys.py
```

Expected output:
```
🔍 Checking API Keys Configuration...

📋 ENVIRONMENT VARIABLES (from .env):
  ✅ GEMINI_API_KEY: AIza...****
  ❌ OPENAI_API_KEY: Not set
  ✅ GROQ_API_KEY: gsk_...****
  ❌ ANTHROPIC_API_KEY: Not set

📊 MODEL AVAILABILITY:
  ✅ Gemini models: 3 available
  ✅ Groq models: 4 available
  ❌ OpenAI models: 0 available (no API key)
  ❌ Claude models: 0 available (no API key)
  ✅ Ollama models: 7 available
```

---

## Provider-Specific Instructions

### 🟢 Google Gemini (Recommended)

**Why Gemini?**
- Free tier: 60 requests/minute (enough for most users)
- Fast response times (2-5 seconds)
- Excellent quality for diagrams and documentation
- Easy to set up

**Steps:**

1. **Get API Key**
   - Visit: https://ai.google.dev/
   - Click "Get API Key in Google AI Studio"
   - Sign in with Google account
   - Click "Create API Key"
   - Copy the key (starts with `AIzaSy...`)

2. **Add to `.env`**
   ```bash
   GEMINI_API_KEY=AIzaSyABC123...your_actual_key
   ```

3. **Test**
   ```bash
   python check_api_keys.py
   ```

**Pricing:**
- **Free tier**: 60 requests/minute, 1500 requests/day
- **Paid tier**: $0.000125 per 1K characters (very cheap)

**Quota Management:**
- If you hit rate limits, wait 60 seconds
- Or upgrade to paid tier (no monthly fees, pay-per-use)

---

### 🔵 OpenAI (GPT-4)

**Why OpenAI?**
- Industry-leading code generation
- Best for complex API documentation
- Excellent reasoning capabilities

**Steps:**

1. **Create Account**
   - Visit: https://platform.openai.com/signup
   - Add payment method (required, even for testing)
   - Add $5-$20 credit

2. **Get API Key**
   - Go to: https://platform.openai.com/api-keys
   - Click "Create new secret key"
   - Name it: "Architect.AI"
   - Copy the key (starts with `sk-...`)
   - **Important**: Save it immediately (can't view again)

3. **Add to `.env`**
   ```bash
   OPENAI_API_KEY=sk-ABC123...your_actual_key
   ```

4. **Test**
   ```bash
   python check_api_keys.py
   ```

**Pricing:**
- **GPT-4 Turbo**: $0.01 per 1K input tokens, $0.03 per 1K output tokens
- **GPT-3.5 Turbo**: $0.0005 per 1K input tokens, $0.0015 per 1K output tokens
- Typical artifact: $0.02 - $0.10 per generation

**Cost Control:**
- Set usage limits in OpenAI dashboard
- Use GPT-3.5 for cheaper operations
- Use Gemini for free tier

---

### 🟠 Groq (Fast Llama)

**Why Groq?**
- **Fastest inference** in the industry (500+ tokens/second)
- Free tier available
- Runs Llama 3.3 70B, Mixtral 8x7B
- Great for rapid prototyping

**Steps:**

1. **Create Account**
   - Visit: https://console.groq.com/
   - Sign up with email or Google

2. **Get API Key**
   - Go to: https://console.groq.com/keys
   - Click "Create API Key"
   - Name it: "Architect.AI"
   - Copy the key (starts with `gsk_...`)

3. **Add to `.env`**
   ```bash
   GROQ_API_KEY=gsk_ABC123...your_actual_key
   ```

4. **Test**
   ```bash
   python check_api_keys.py
   ```

**Pricing:**
- **Free tier**: 30 requests/minute, 14,400 requests/day
- **Paid tier**: $0.27 per 1M tokens (very affordable)

**Models Available:**
- Llama 3.3 70B Versatile (best quality)
- Llama 3.1 70B Versatile
- Llama 3.1 8B Instant (fastest)
- Mixtral 8x7B (good balance)

---

### 🟣 Anthropic Claude

**Why Claude?**
- Excellent for long-form documentation
- Strong reasoning and analysis
- Best for technical writing

**Steps:**

1. **Create Account**
   - Visit: https://console.anthropic.com/
   - Sign up with email
   - Add payment method ($5 minimum)

2. **Get API Key**
   - Go to: https://console.anthropic.com/settings/keys
   - Click "Create Key"
   - Name it: "Architect.AI"
   - Copy the key (starts with `sk-ant-...`)

3. **Add to `.env`**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-ABC123...your_actual_key
   ```

4. **Test**
   ```bash
   python check_api_keys.py
   ```

**Pricing:**
- **Claude 3.5 Sonnet**: $3 per 1M input tokens, $15 per 1M output tokens
- **Claude 3 Opus**: $15 per 1M input tokens, $75 per 1M output tokens
- Typical artifact: $0.05 - $0.30 per generation

---

### 🟤 Ollama (Local Models)

**Why Ollama?**
- **100% free** (no API costs)
- **Privacy**: All data stays on your machine
- Fast inference on good hardware
- No rate limits
- Works offline

**Requirements:**
- **Minimum**: 8GB RAM, 4GB VRAM (GTX 1060 or better)
- **Recommended**: 16GB RAM, 8GB VRAM (RTX 3060 or better)
- **Optimal**: 32GB RAM, 12GB+ VRAM (RTX 4070+ or A100)

**Steps:**

1. **Install Ollama**
   - Visit: https://ollama.ai
   - Download for your OS (Windows/Mac/Linux)
   - Run installer

2. **Pull Models**
   ```bash
   # Best for code (4GB VRAM)
   ollama pull deepseek-coder:6.7b-instruct-q4_K_M
   
   # Alternative (4GB VRAM)
   ollama pull qwen2.5-coder:7b-instruct-q4_K_M
   
   # Larger model (8GB VRAM)
   ollama pull mistral-nemo:12b-instruct-2407-q4_K_M
   
   # Huge model (16GB+ VRAM)
   ollama pull qwen2.5-coder:14b-instruct-q4_K_M
   ```

3. **Verify**
   ```bash
   ollama list
   ```

4. **No `.env` setup needed** - Ollama runs locally on http://localhost:11434

**Model Recommendations:**
- **Best quality**: `deepseek-coder:6.7b-instruct-q4_K_M`
- **Fastest**: `qwen2.5-coder:7b-instruct-q4_K_M`
- **Balanced**: `mistral-nemo:12b-instruct-2407-q4_K_M`
- **Huge**: `qwen2.5-coder:14b-instruct-q4_K_M` (if you have VRAM)

---

## Model Selection Strategy

### For Different Use Cases

**Diagrams (ERD, Architecture, Sequence, etc.):**
- **Primary**: `deepseek-coder:6.7b` (local, free)
- **Fallback**: Gemini 2.0 Flash (fast, free)

**Code Prototypes:**
- **Primary**: `deepseek-coder:6.7b` (local, understands code structure)
- **Fallback**: GPT-4 Turbo (best quality, paid)

**API Documentation:**
- **Primary**: Gemini 1.5 Pro (excellent formatting)
- **Fallback**: Claude 3.5 Sonnet (technical writing)

**Project Management (Jira, Backlog):**
- **Primary**: Gemini 2.0 Flash (fast, good at structured output)
- **Fallback**: GPT-3.5 Turbo (cheap, good enough)

---

## Troubleshooting

### ❌ "API key not found" error

**Solution:**
1. Check `.env` file exists in `architect_ai_cursor_poc/`
2. Verify key format (no quotes, no spaces)
3. Restart the application
4. Run `python check_api_keys.py`

### ❌ "Invalid API key" error

**Solution:**
1. Copy key again from provider dashboard
2. Ensure no extra spaces/newlines in `.env`
3. Test key directly:
   ```bash
   # Gemini
   curl "https://generativelanguage.googleapis.com/v1/models?key=YOUR_KEY"
   
   # OpenAI
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer YOUR_KEY"
   ```

### ❌ "Rate limit exceeded" error

**Solution:**
- **Gemini**: Wait 60 seconds (60 requests/minute limit)
- **Groq**: Wait 60 seconds (30 requests/minute limit)
- **OpenAI**: Upgrade to Tier 1 (add more credit)
- **Fallback**: Use Ollama (no limits)

### ❌ Ollama models not appearing

**Solution:**
```bash
# Check Ollama is running
ollama list

# Start Ollama service
ollama serve  # Linux/Mac
# Windows: Should start automatically

# Pull a model
ollama pull deepseek-coder:6.7b-instruct-q4_K_M

# Restart Architect.AI
python launch.py
```

### ❌ High API costs

**Solution:**
1. Use Gemini free tier for most operations
2. Reserve GPT-4 for complex code only
3. Fine-tune local Ollama models (free, learns your style)
4. Set up model routing to use cheaper models as fallbacks

---

## Security Best Practices

✅ **DO:**
- Store keys in `.env` file (gitignored)
- Use environment variables
- Rotate keys regularly
- Set usage limits in provider dashboards
- Use separate keys for dev/prod

❌ **DON'T:**
- Commit `.env` to Git
- Share keys publicly
- Hardcode keys in source code
- Use same key across multiple projects
- Leave unused keys active

---

## Cost Optimization Tips

1. **Use free tiers first**: Gemini (60 req/min) + Groq (30 req/min) = 90 free requests/minute
2. **Fine-tune local models**: After 50 feedback examples, train Ollama (free forever)
3. **Smart model routing**: Use cheap models for simple tasks, expensive for complex
4. **Caching**: Enable RAG caching to avoid redundant API calls
5. **Batch generation**: Generate multiple artifacts at once (fewer API calls)

**Example cost breakdown:**
- 100 artifacts with Gemini: **$0 (free tier)**
- 100 artifacts with GPT-4: **$10-$30**
- 100 artifacts with Ollama: **$0 (local)**

---

## Need Help?

- **Verify keys**: `python check_api_keys.py`
- **Check logs**: See terminal output when app starts
- **Test API**: Use provider dashboards to test keys
- **Documentation**: See provider docs for troubleshooting

---

**Last updated: November 24, 2025**

