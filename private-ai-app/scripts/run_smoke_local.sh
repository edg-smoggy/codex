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

echo "[INFO] Installing backend requirements..."
pip install -r requirements.txt

echo "[INFO] Ensuring local env file..."
if [[ ! -f .env.local ]]; then
  cp .env.local.example .env.local
fi

echo "[INFO] Running local smoke checks..."
export ENV_FILE=".env.local"
PYTHONPATH=. python scripts/smoke_local.py
