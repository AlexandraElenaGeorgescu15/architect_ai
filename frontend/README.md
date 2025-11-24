# Architect.AI Frontend

React + TypeScript frontend for Architect.AI, built with Vite.

## Tech Stack

- **React 18+** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **Zustand** for state management
- **React Router** for routing
- **Axios** for API calls
- **Lucide React** for icons

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000`

### Installation

```bash
npm install
```

**Note for Windows Users:** If you encounter a PowerShell execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try `npm install` again.

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

### Build

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── pages/              # Page components
│   ├── components/         # Reusable components
│   │   ├── layout/         # Layout components
│   │   ├── artifacts/      # Artifact display
│   │   ├── canvas/         # Diagram editor
│   │   └── charts/         # Visualization charts
│   ├── services/           # API clients
│   ├── stores/             # Zustand stores
│   ├── hooks/              # Custom hooks
│   ├── types/              # TypeScript types
│   └── App.tsx             # Root component
├── public/                 # Static assets
└── package.json
```

## API Integration

The frontend connects to the FastAPI backend at `http://localhost:8000`.

### WebSocket

WebSocket connections are made to `ws://localhost:8000/ws/{room_id}` for real-time updates.

## Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

## Development Notes

- The Vite proxy is configured to forward `/api` requests to the backend
- WebSocket connections are proxied through `/ws`
- Path aliases are configured: `@/` maps to `src/`



