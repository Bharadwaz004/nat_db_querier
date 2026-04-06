#!/bin/bash

WORKDIR="/workspaces/$(basename $PWD)"
cd "$WORKDIR"

# Load .env if present (won't exist in Codespaces — use Codespaces secrets instead)
if [ -f .env ]; then
  export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

# Kill any leftover processes
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3001/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

echo ""
echo "Starting FastAPI on port 8000..."
uvicorn backend_fastapi.src.main:app --host 0.0.0.0 --port 8000 >> /tmp/fastapi.log 2>&1 &

echo "Starting Node gateway on port 3001..."
FASTAPI_URL=http://localhost:8000 \
JWT_SECRET="${JWT_SECRET:-nlsql-dev-secret}" \
node backend-node/src/server.js >> /tmp/gateway.log 2>&1 &

echo "Starting Vite frontend on port 5173..."
cd frontend && npm run dev -- --host 0.0.0.0 >> /tmp/frontend.log 2>&1 &

# Wait for all 3 services to be ready
echo ""
echo "Waiting for services..."
for port in 8000 3001 5173; do
  for i in $(seq 1 20); do
    if ss -tlnp | grep -q ":$port "; then
      case $port in
        8000) echo "  FastAPI   ready on port 8000" ;;
        3001) echo "  Gateway   ready on port 3001" ;;
        5173) echo "  Frontend  ready on port 5173 (open this in browser)" ;;
      esac
      break
    fi
    sleep 1
  done
done

echo ""
echo "Done. Open port 5173 from the Ports tab."
echo "To view logs: tail -f /tmp/fastapi.log /tmp/gateway.log /tmp/frontend.log"
