#!/usr/bin/env bash
# Run FastAPI AI Engine standalone
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Create sample DB if needed
if [ ! -f data/sample_ecommerce.db ]; then
  python data/create_sample_db.py
fi

PYTHONPATH="$ROOT" python -m uvicorn backend_fastapi.src.main:app \
  --host 0.0.0.0 \
  --port "${FASTAPI_PORT:-8000}" \
  --reload
