# Backend (FastAPI)

## 本地开发（SQLite fallback）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.local.example .env.local
set -a
source .env.local
set +a
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

## Docker 开发（PostgreSQL + Redis）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
cp backend/.env.example backend/.env
docker compose up -d --build postgres redis backend
```

## 初始化管理员

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/backend
source .venv/bin/activate
PYTHONPATH=. python scripts/bootstrap_admin.py \
  --admin-username admin \
  --admin-password 'ChangeMe123!' \
  --invite-code 'FRIEND-ONLY-001'
```

## 本地冒烟

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
./scripts/run_smoke_local.sh
```
