#!/bin/bash
set -e

WORKDIR="/workspaces/$(basename $PWD)"
cd "$WORKDIR"

echo "Installing Python dependencies..."
pip install --quiet -r backend_fastapi/requirements.txt

echo "Installing Node gateway dependencies..."
cd backend-node && npm ci --production && cd ..

echo "Installing frontend dependencies..."
cd frontend && npm ci && cd ..

echo "Creating sample database..."
python data/create_sample_db.py

echo "Setup complete."
