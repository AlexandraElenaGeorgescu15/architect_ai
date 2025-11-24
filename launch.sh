#!/bin/bash
# Architect.AI FastAPI + React Launcher for Linux/Mac
# Launches both backend (FastAPI) and frontend (React) servers

echo ""
echo "============================================================"
echo "   🏗️ Architect.AI v3.5.2 - FastAPI + React Edition"
echo "============================================================"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: Python 3 not found"
    echo "   Please install Python 3.9+ from https://www.python.org/"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ ERROR: Node.js not found"
    echo "   Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

echo "✅ Python and Node.js found"
echo ""

# Check if backend dependencies are installed
echo "Checking backend dependencies..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "Installing backend dependencies..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to install backend dependencies"
        exit 1
    fi
fi

# Check if frontend dependencies are installed
echo "Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ ERROR: Failed to install frontend dependencies"
        cd ..
        exit 1
    fi
    cd ..
fi

echo ""
echo "============================================================"
echo "   Starting Architect.AI..."
echo "============================================================"
echo ""
echo "Backend API:  http://localhost:8000"
echo "Frontend App: http://localhost:3000"
echo "API Docs:     http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend server..."
cd "$SCRIPT_DIR"
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend server..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Both servers are running..."
echo "   Backend PID: $BACKEND_PID"
echo "   Frontend PID: $FRONTEND_PID"
echo ""
echo "   Close with Ctrl+C"
echo ""

# Wait for both processes
wait

