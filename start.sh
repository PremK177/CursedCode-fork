#!/bin/bash
# One-command startup script for DebugDojo (CursedCode)
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PATH="$DIR/server/.venv/bin:$PATH"
cd "$DIR"

echo "=== Starting DebugDojo ==="

# 1. Start FastAPI Backend (with bwrap local sandbox)
echo "Starting FastAPI server on port 8000..."
cd "$DIR/server"
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv --system-site-packages .venv
    .venv/bin/pip install -q -r requirements.txt
fi
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# 2. Start Frontend
cd "$DIR/client"
if command -v npm >/dev/null 2>&1; then
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi
    echo "Starting Vite client on port 5173..."
    npm run dev -- --host 0.0.0.0 --port 5173 &
    CLIENT_PID=$!
    echo "Client started (PID: $CLIENT_PID)"
else
    echo "Warning: npm not found on PATH; skipping Vite dev server."
fi

echo "=== Services running ==="
echo "Frontend: http://localhost:5173"
echo "Backend:  http://localhost:8000"

trap "kill $BACKEND_PID $CLIENT_PID 2>/dev/null || true; exit" SIGINT SIGTERM EXIT
wait
