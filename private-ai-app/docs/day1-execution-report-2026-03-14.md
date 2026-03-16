# Day1 执行报告（2026-03-14）

## 已完成

- 后端虚拟环境与依赖安装完成。
- 增加 SQLite 本地 fallback（无 Docker 也可跑通 API 链路）。
- 增加环境自检脚本：`scripts/env_doctor.sh`。
- 增加本地后端启动脚本：`scripts/run_backend_local.sh`。
- 增加本地冒烟脚本：`scripts/run_smoke_local.sh` + `backend/scripts/smoke_local.py`。
- 冒烟覆盖项扩展到 13 项（注册、登录、refresh、模型、SSE、历史、用量、管理员、token/cost 配额、封禁）。
- 生成冒烟报告：
  - `backend/artifacts/smoke-report-20260314-222548.json`
  - `backend/artifacts/smoke-report-20260314-222648.json`

## 关键结果

- 最新 smoke 结果：13/13 通过。
- SSE 顺序验证通过：`meta -> chunk -> done`。
- 配额拦截验证通过：token 与 cost 均返回 429。
- 管理员封禁/解封与额度调整/重置验证通过。

## 修复项（本轮新增）

- 修复 Python 3.9 兼容问题：将 `|` 联合类型改为 `Optional/Union`。
- 修复 CSV 模型环境变量解析失败（`NoDecode + CSV validator`）。
- 修复 SQLite 下邀请码过期时间比较的时区兼容问题。
- 修复 `passlib + bcrypt` 版本兼容（固定 `bcrypt==4.0.1`）。
- 补充 SQLAlchemy async 运行依赖（`greenlet==3.1.1`）。

## 当前阻塞

- 本机仍缺少：`node`、`npm`、`docker`、`rustc`、`cargo`。
- 因此 Day2 的 Tauri 联调和 Docker 模式联调尚未执行。

## Day2 建议动作

1. 安装 Node.js + npm + Rust toolchain（用于 Tauri）。
2. 若要走容器链路，再安装 Docker Desktop。
3. 执行 `desktop` 联调并按 `docs/acceptance-checklist.md` 做人工验收。
