#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# NL→SQL Assistant — Start All Services
# ──────────────────────────────────────────────────────────────
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Load env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

FASTAPI_PORT=${FASTAPI_PORT:-8000}
NODE_PORT=${PORT:-3001}

echo "╔═══════════════════════════════════════════════╗"
echo "║    ⚡  NL→SQL Hybrid RAG Assistant            ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

# ── 1. Create sample database if needed ──────────────────────
if [ ! -f data/sample_ecommerce.db ]; then
  echo "📦 Creating sample database..."
  python data/create_sample_db.py
fi

# ── 2. Run schema ingestion if needed ────────────────────────
if [ ! -f embeddings/index.pkl ]; then
  echo "🧮 Running schema ingestion..."
  python -c "
import sys; sys.path.insert(0, '.')
from backend_fastapi.src.modules.schema_ingestion import SchemaIngestion
ing = SchemaIngestion()
ing.ingest()
"
fi

# ── 3. Start FastAPI (background) ────────────────────────────
echo "🐍 Starting FastAPI on port $FASTAPI_PORT..."
cd "$ROOT"
PYTHONPATH="$ROOT" python -m uvicorn backend_fastapi.src.main:app \
  --host 0.0.0.0 --port "$FASTAPI_PORT" --reload &
FASTAPI_PID=$!

sleep 2

# ── 4. Start Node.js Gateway (background) ────────────────────
echo "🟢 Starting Node.js Gateway on port $NODE_PORT..."
cd "$ROOT/backend-node"
PORT=$NODE_PORT FASTAPI_URL="http://localhost:$FASTAPI_PORT" \
  node src/server.js &
NODE_PID=$!

sleep 1

# ── 5. Start React Frontend ─────────────────────────────────
echo "⚛️  Starting React frontend on port 5173..."
cd "$ROOT/frontend"
npx vite --host 0.0.0.0 &
VITE_PID=$!

echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ All services running!"
echo ""
echo "  Frontend:    http://localhost:5173"
echo "  API Gateway: http://localhost:$NODE_PORT"
echo "  AI Engine:   http://localhost:$FASTAPI_PORT"
echo "  API Docs:    http://localhost:$FASTAPI_PORT/docs"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════"

# Trap SIGINT to kill all processes
cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  kill $FASTAPI_PID $NODE_PID $VITE_PID 2>/dev/null
  wait 2>/dev/null
  echo "✅ All services stopped."
}
trap cleanup SIGINT SIGTERM

# Wait for any process to exit
wait
