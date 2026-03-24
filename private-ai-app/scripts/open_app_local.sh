#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PORT=8000
BACKEND_STARTED=0
BACKEND_PID=""
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FORCE_RESTART_BACKEND="${PRIVATE_AI_FORCE_RESTART_BACKEND:-1}"

cleanup() {
  if [[ "$BACKEND_STARTED" -eq 1 && -n "$BACKEND_PID" ]]; then
    pkill -P "$BACKEND_PID" >/dev/null 2>&1 || true
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

backend_is_compatible() {
  local openapi
  local tmp_openapi
  if ! openapi="$(curl -fsS "${BACKEND_URL}/openapi.json" 2>/dev/null)"; then
    return 1
  fi

  tmp_openapi="$(mktemp)"
  printf '%s' "$openapi" >"$tmp_openapi"

  if ! python3 - "$tmp_openapi" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

paths = data.get("paths", {})
conversation_ops = paths.get("/api/v1/conversations/{conversation_id}", {})
chat_props = (
    data.get("components", {})
    .get("schemas", {})
    .get("ChatStreamRequest", {})
    .get("properties", {})
)

sys.exit(0 if "delete" in conversation_ops and "thinking_mode" in chat_props else 1)
PY
  then
    rm -f "$tmp_openapi"
    return 1
  fi

  rm -f "$tmp_openapi"
}

restart_backend() {
  local existing_pids
  existing_pids="$(lsof -tiTCP:${BACKEND_PORT} -sTCP:LISTEN || true)"
  if [[ -n "$existing_pids" ]]; then
    echo "[WARN] Restarting backend on :${BACKEND_PORT} ..."
    while IFS= read -r pid; do
      [[ -n "$pid" ]] || continue
      kill "$pid" >/dev/null 2>&1 || true
    done <<< "$existing_pids"

    for _ in $(seq 1 20); do
      if ! lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done
  fi

  echo "[INFO] Starting backend on :${BACKEND_PORT} ..."
  (
    cd "$ROOT_DIR"
    ./scripts/run_backend_local.sh
  ) &
  BACKEND_PID=$!
  BACKEND_STARTED=1

  for _ in $(seq 1 30); do
    if curl -sS "${BACKEND_URL}/api/v1/health" >/dev/null 2>&1 && backend_is_compatible; then
      echo "[INFO] Backend is ready."
      return 0
    fi
    sleep 1
  done

  echo "[ERROR] Backend failed compatibility checks after restart." >&2
  return 1
}

if [[ "$FORCE_RESTART_BACKEND" == "1" ]]; then
  restart_backend
elif lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
  if backend_is_compatible; then
    echo "[INFO] Backend already listening on :${BACKEND_PORT}"
  else
    restart_backend
  fi
else
  restart_backend
fi

cd "$ROOT_DIR/desktop"
source ~/.nvm/nvm.sh
nvm use 20 >/dev/null
source ~/.cargo/env

echo "[INFO] Launching desktop app..."
npm run tauri:dev
