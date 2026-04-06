#!/bin/bash

WORKDIR="/workspaces/$(basename $PWD)"
cd "$WORKDIR"

# Kill any leftover processes
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "server.js" 2>/dev/null || true

echo "Starting FastAPI on port 8000..."
uvicorn backend_fastapi.src.main:app --host 0.0.0.0 --port 8000 \
  >> /tmp/fastapi.log 2>&1 &

echo "Starting Node gateway on port 3001..."
FASTAPI_URL=http://localhost:8000 \
JWT_SECRET="${JWT_SECRET:-nlsql-dev-secret}" \
node backend-node/src/server.js \
  >> /tmp/gateway.log 2>&1 &

echo "Starting Vite frontend on port 5173..."
cd frontend && npm run dev -- --host 0.0.0.0 \
  >> /tmp/frontend.log 2>&1 &

echo ""
echo "All services started."
echo "  Frontend : port 5173 (check Ports tab)"
echo "  Gateway  : port 3001"
echo "  FastAPI  : port 8000"
echo ""
echo "Logs: /tmp/fastapi.log | /tmp/gateway.log | /tmp/frontend.log"
