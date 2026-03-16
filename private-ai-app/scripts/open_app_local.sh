#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT=8000
BACKEND_STARTED=0
BACKEND_PID=""

cleanup() {
  if [[ "$BACKEND_STARTED" -eq 1 && -n "$BACKEND_PID" ]]; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[INFO] Backend already listening on :${BACKEND_PORT}"
else
  echo "[INFO] Starting backend on :${BACKEND_PORT} ..."
  (
    cd "$ROOT_DIR"
    ./scripts/run_backend_local.sh
  ) &
  BACKEND_PID=$!
  BACKEND_STARTED=1

  for _ in $(seq 1 30); do
    if curl -sS "http://127.0.0.1:${BACKEND_PORT}/api/v1/health" >/dev/null 2>&1; then
      echo "[INFO] Backend is ready."
      break
    fi
    sleep 1
  done
fi

cd "$ROOT_DIR/desktop"
source ~/.nvm/nvm.sh
nvm use 20 >/dev/null
source ~/.cargo/env

echo "[INFO] Launching desktop app..."
npm run tauri:dev
