#!/usr/bin/env bash
# Starts the FastAPI engine (internal, localhost only) and the Node gateway
# (public, bound to $PORT) in one container. Node proxies /api/* to FastAPI.
set -e

DATA_DIR="${DATA_DIR:-/app/data}"
mkdir -p "$DATA_DIR" "${EMBEDDINGS_DIR:-/app/embeddings}" "${GRAPH_DIR:-/app/graph}"
if [ ! -f "$DATA_DIR/sample_ecommerce.db" ]; then
  cp -r /app/data_seed/. "$DATA_DIR/"
fi

PYTHONPATH=/app python -m uvicorn backend_fastapi.src.main:app \
  --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

cd /app/backend-node
PORT="${PORT:-3001}" FASTAPI_URL="http://127.0.0.1:8000" node src/server.js &
NODE_PID=$!

trap 'kill $FASTAPI_PID $NODE_PID 2>/dev/null' TERM INT

# Exit (and let the platform restart the container) if either process dies.
wait -n "$FASTAPI_PID" "$NODE_PID"
kill $FASTAPI_PID $NODE_PID 2>/dev/null
wait
