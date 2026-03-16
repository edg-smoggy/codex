#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$BACKEND_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  echo "[INFO] Creating backend virtualenv..."
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

if [[ ! -f .env.local ]]; then
  cp .env.local.example .env.local
fi

PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --env-file .env.local
