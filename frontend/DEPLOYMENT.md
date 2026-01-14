# Architect.AI Frontend Deployment Guide

## 🚀 Deploy to Vercel

### Option 1: Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click **"New Project"**
3. Import your GitHub repository
4. Set the **Root Directory** to `frontend`
5. Vercel will auto-detect Vite settings
6. Click **Deploy**

### Option 2: Deploy via CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Navigate to frontend folder
cd frontend

# Deploy
vercel

# For production
vercel --prod
```

---

## 🔧 Connecting to Your Local Backend

After deploying the frontend to Vercel, you need to connect it to your local backend:

### Step 1: Start your local backend

```bash
# In your project root
python launch.py
```

This starts the backend at `http://localhost:8000`

### Step 2: Expose your backend with ngrok

Since Vercel uses HTTPS and your local backend uses HTTP, browsers will block the connection. Use ngrok to get an HTTPS URL:

```bash
# Install ngrok (one time)
npm i -g ngrok

# Or download from https://ngrok.com/download

# Expose your local backend
ngrok http 8000
```

You'll get output like:
```
Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
```

### Step 3: Configure the frontend

1. Open your deployed Vercel app
2. Click the **connection indicator** in the bottom-right corner (shows "Disconnected")
3. Enter your ngrok HTTPS URL: `https://abc123.ngrok-free.app`
4. Click **Test** to verify the connection
5. Click **Save & Reconnect**

---

## 🌐 Architecture

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│     Vercel (Frontend)       │     │   Your PC (Backend)         │
│  ┌───────────────────────┐  │     │  ┌───────────────────────┐  │
│  │   React App (Static)  │──┼─────┼──│   FastAPI Server      │  │
│  │   architect-ai.vercel │  │     │  │   localhost:8000      │  │
│  │   .app                │  │HTTPS│  │                       │  │
│  └───────────────────────┘  │ API │  │   ┌─────────────────┐ │  │
│                             │     │  │   │ ChromaDB/RAG    │ │  │
│   ✅ No Python needed       │     │  │   │ Ollama Models   │ │  │
│   ✅ Access from anywhere   │     │  │   │ Local Codebase  │ │  │
│                             │     │  │   └─────────────────┘ │  │
└─────────────────────────────┘     │  └───────────────────────┘  │
                                    │                             │
                                    │  ngrok tunnel (HTTPS)       │
                                    │  https://xxx.ngrok-free.app │
                                    └─────────────────────────────┘
```

---

## ⚠️ Important Notes

### Security
- Your ngrok URL is **publicly accessible** - anyone with the URL can access your backend
- Use ngrok's authentication features for sensitive data
- Consider using a paid ngrok plan for static URLs

### Free Tier Limitations
- ngrok free tier: URL changes every restart
- Vercel free tier: Limited bandwidth

### Alternative Tunnels
- [localtunnel](https://localtunnel.github.io/www/): `npx localtunnel --port 8000`
- [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/): More stable URLs

---

## 🔒 Environment Variables (Optional)

For production, you can set these in Vercel:

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Default backend URL | `""` (relative) |

Go to Vercel Dashboard → Your Project → Settings → Environment Variables

---

## 🐛 Troubleshooting

### "Mixed Content" Error
- Your backend must use HTTPS (use ngrok)
- Or both frontend and backend must be local

### "CORS Error"
- Backend already allows all origins (`*`)
- Check that your ngrok URL is correct

### "Connection Refused"
- Ensure backend is running: `python launch.py`
- Ensure ngrok is running: `ngrok http 8000`
- Check the ngrok URL hasn't changed

### Backend URL Not Saving
- Check browser localStorage permissions
- Try clearing localStorage and reconfiguring
