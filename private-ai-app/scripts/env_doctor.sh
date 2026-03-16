#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -s "$HOME/.cargo/env" ]]; then
  # shellcheck disable=SC1090
  . "$HOME/.cargo/env"
fi

if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1090
  . "$HOME/.nvm/nvm.sh"
  nvm use default >/dev/null 2>&1 || true
fi

check_cmd() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    echo "[OK] $name -> $(command -v "$name")"
  else
    echo "[MISSING] $name"
  fi
}

echo "== Private AI Hub Environment Doctor =="
check_cmd python3
if command -v pip >/dev/null 2>&1; then
  echo "[OK] pip -> $(command -v pip)"
elif command -v pip3 >/dev/null 2>&1; then
  echo "[OK] pip3 -> $(command -v pip3)"
elif python3 -m pip --version >/dev/null 2>&1; then
  echo "[OK] python3 -m pip"
else
  echo "[MISSING] pip"
fi
check_cmd node
check_cmd npm
check_cmd docker
check_cmd rustc
check_cmd cargo

echo
echo "== Backend venv =="
if [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  echo "[OK] backend venv exists"
  "$ROOT_DIR/backend/.venv/bin/python" --version
else
  echo "[MISSING] backend/.venv"
fi

echo
echo "== Config files =="
if [[ -f "$ROOT_DIR/backend/.env" ]]; then
  echo "[OK] backend/.env"
elif [[ -f "$ROOT_DIR/backend/.env.local" ]]; then
  echo "[OK] backend/.env.local"
else
  echo "[MISSING] backend/.env or backend/.env.local"
fi

if [[ -f "$ROOT_DIR/desktop/.env" ]]; then
  echo "[OK] desktop/.env"
else
  echo "[MISSING] desktop/.env"
fi
