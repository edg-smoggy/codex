# Private AI Hub (Desktop + Gateway)

私用多模型桌面应用（Windows 优先）MVP，包含：
- `backend`：FastAPI 网关（鉴权、邀请码、模型路由、配额、会话、管理接口）
- `desktop`：Tauri + React 桌面端（登录注册、模型切换、流式聊天、历史会话、用量展示）
- `scripts`：环境自检、本地后端启动、本地冒烟脚本
- `docs`：验收清单、内测操作手册、执行日志模板

## 目录结构

```text
private-ai-app/
  backend/
  desktop/
  docs/
  scripts/
  infra/
  docker-compose.yml
```

## 0) Mac 一键图标启动（推荐）

首次生成启动器：

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
./scripts/build_mac_launcher.sh
```

后续直接双击项目根目录里的 `Private AI Hub.app` 即可启动（自动拉起/复用后端，并打开桌面端）。

如需手动停止本地后端：

```bash
pkill -f "uvicorn app.main:app --host 0.0.0.0 --port 8000" || true
```

## 1) 推荐先跑（本地 fallback，无 Docker）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
./scripts/env_doctor.sh
./scripts/run_smoke_local.sh
```

说明：
- 本路径使用 `backend/.env.local`（基于 SQLite + mock provider）快速完成 API 验收。
- 适合当前机器缺少 Docker/Node 时先完成 Day1 验证。

## 2) 后端启动（Docker 模式）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
cp backend/.env.example backend/.env

docker compose up -d --build postgres redis backend
```

## 3) 后端启动（本地模式）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app
./scripts/run_backend_local.sh
```

默认后端地址：
- `http://localhost:8000/api/v1`

## 4) 初始化管理员与邀请码

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/backend
source .venv/bin/activate
PYTHONPATH=. python scripts/bootstrap_admin.py \
  --admin-username admin \
  --admin-password 'ChangeMe123!' \
  --invite-code 'FRIEND-ONLY-001'
```

## 5) 桌面端启动（开发）

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/desktop
cp .env.example .env
npm install
export VITE_API_BASE_URL=http://localhost:8000/api/v1
npm run tauri:dev
```

## 6) Windows 打包

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/desktop
npm install
npm run tauri:build
```

产物通常在：
- `desktop/src-tauri/target/release/bundle/`

## 7) 已实现 API

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/models`
- `POST /api/v1/chat/stream`
- `GET /api/v1/conversations`
- `GET /api/v1/conversations/{id}/messages`
- `GET /api/v1/usage/me/daily`
- `GET /api/v1/admin/users`
- `GET /api/v1/admin/usage/daily`
- `POST /api/v1/admin/users/{id}/block`
- `POST /api/v1/admin/users/{id}/quota`
- `POST /api/v1/admin/users/{id}/usage/reset`
- `GET /api/v1/health`

## 8) 环境变量说明

真实模型回归时，在 `backend/.env`（或 `.env.local`）配置：
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `KIMI_API_KEY`
- `SECRET_KEY`

mock 联调阶段可保留：
- `ALLOW_MOCK_PROVIDER=true`

真 key 回归阶段切换：
- `ALLOW_MOCK_PROVIDER=false`

## 9) 交付文档

- `docs/acceptance-checklist.md`
- `docs/internal-beta-runbook.md`
- `docs/smoke-log-template.md`
- `docs/day1-execution-report-2026-03-14.md`

## 10) 安全建议（上线前）

- 关闭 CORS 全开放，仅允许必要来源。
- 使用高强度 `SECRET_KEY` 并固定不随意变更。
- 把数据库和 Redis 端口限制在内网。
- 管理员强密码 + 定期轮换邀请码。
