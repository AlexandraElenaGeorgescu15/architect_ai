# Remote Access Guide

Access your Architect.AI backend from the deployed frontend at:
**https://architect-ai-mvm.vercel.app/**

## Quick Start

### 1. Install ngrok (one-time setup)

1. Download from [ngrok.com/download](https://ngrok.com/download)
2. Extract and add to your PATH
3. Sign up for free at [ngrok.com](https://ngrok.com)
4. Get your auth token and run:
   ```bash
   ngrok config add-authtoken YOUR_AUTH_TOKEN
   ```

### 2. Start the Backend

**Windows (PowerShell - Recommended):**
```powershell
.\start-backend-remote.ps1
```

**Windows (Command Prompt):**
```cmd
start-backend-remote.bat
```

**Manual Start:**
```bash
# Terminal 1: Start backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start ngrok tunnel
ngrok http 8000
```

### 3. Connect the Frontend

1. Open https://architect-ai-mvm.vercel.app/
2. Click the **connection indicator** (WiFi icon) in the bottom-left corner
3. Enter your ngrok URL (e.g., `https://abc123.ngrok-free.app`)
4. Click **Save & Connect**

## Architecture

```
┌─────────────────────────────────────┐
│  Vercel (Cloud)                     │
│  https://architect-ai-mvm.vercel.app│
│  ┌─────────────────────────────┐    │
│  │  React Frontend             │    │
│  │  (Static Files)             │    │
│  └─────────────────────────────┘    │
└──────────────────┬──────────────────┘
                   │ HTTPS
                   ▼
┌─────────────────────────────────────┐
│  ngrok (Tunnel)                     │
│  https://xxxx.ngrok-free.app        │
└──────────────────┬──────────────────┘
                   │ localhost:8000
                   ▼
┌─────────────────────────────────────┐
│  Your Computer                      │
│  ┌─────────────────────────────┐    │
│  │  FastAPI Backend            │    │
│  │  + Ollama (AI Models)       │    │
│  │  + RAG Index                │    │
│  │  + Knowledge Graph          │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

## Why This Setup?

- **Frontend on Vercel**: Fast, globally distributed, always available
- **Backend on Your Machine**: 
  - Uses YOUR project files (RAG indexing)
  - Uses YOUR Ollama models (GPU acceleration)
  - Uses YOUR API keys (secure, not stored in cloud)
  - No cloud compute costs

## Troubleshooting

### ngrok URL not showing
- Check http://localhost:4040 for the ngrok dashboard
- Make sure ngrok is authenticated: `ngrok config add-authtoken YOUR_TOKEN`

### Connection refused
- Make sure the backend is running on port 8000
- Check firewall settings
- Try `http://localhost:8000/api/health` directly

### CORS errors
- The backend is configured to accept all origins
- If issues persist, check browser console for details

### Frontend shows "Disconnected"
- The ngrok URL changes each time you restart
- Re-enter the new URL in the frontend settings

## Free ngrok Limitations

- URL changes on each restart (need to update frontend settings)
- Rate limited (sufficient for personal use)
- Sessions timeout after ~2 hours of inactivity

For persistent URLs, consider ngrok paid plans or alternatives like:
- [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/) (free)
- [localtunnel](https://localtunnel.me/) (free, less reliable)
- [Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel/) (free tier available)
