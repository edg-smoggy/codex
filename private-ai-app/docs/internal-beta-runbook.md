# 内测操作手册（好友内测级）

## 1. Day1：本地后端与 mock 跑通

1. 运行环境自检：`./scripts/env_doctor.sh`
2. 初始化本地后端：`./scripts/run_backend_local.sh`
3. 另开终端执行冒烟：`./scripts/run_smoke_local.sh`
4. 记录报告路径：`backend/artifacts/smoke-report-*.json`

## 2. Day2：桌面端联调

1. 在具备 `node/npm/rust/cargo` 的机器执行：
2. `cd desktop && cp .env.example .env`
3. 设置 `VITE_API_BASE_URL=http://localhost:8000/api/v1`
4. `npm install && npm run tauri:dev`
5. 人工验证：注册、登录、模型切换、聊天、历史、用量、管理员封禁

### 一键启动（推荐）

- 在项目根目录运行：`./scripts/open_app_local.sh`
- 行为：自动检查/启动后端，再拉起 Tauri 桌面端。

## 3. Day3：切真 Key 回归

1. `cp backend/.env.example backend/.env`（或更新现有 `.env.local`）
2. 设置 `OPENAI_API_KEY/GEMINI_API_KEY/KIMI_API_KEY`
3. 设置 `ALLOW_MOCK_PROVIDER=false`
4. 设置 `KIMI_MODELS=kimi-k2.5,moonshot-v1-8k,moonshot-v1-32k`
5. 按地区设置 Kimi 端点：国内 `KIMI_BASE_URL=https://api.moonshot.cn/v1`，国际 `https://api.moonshot.ai/v1`
6. 重启后端并执行完整验收清单

## 4. 管理员初始化

- 命令：
`cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/bootstrap_admin.py --admin-username admin --admin-password 'ChangeMe123!' --invite-code 'FRIEND-ONLY-001'`

- 使用规则：
1. 管理员账号不走“成员注册”，只走“管理员登录”。
2. 成员首次使用走“成员注册”（邀请码），之后走“成员登录”。
3. 登录后若入口与账号角色不匹配，前端会直接提示并拒绝进入。

## 5. 管理员角色调整（提升/回滚）

- 提升普通账号为管理员：
`cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/promote_admin.py --username <your_username>`

- 回滚为普通成员：
`cd backend && source .venv/bin/activate && PYTHONPATH=. python scripts/promote_admin.py --username <your_username> --demote`

- 验证方式：
1. 目标账号重新登录。
2. 设置页看到“管理员”标识且管理员面板可见（若提升成功）。
3. 访问管理员接口应分别返回 200（管理员）/403（成员）。

## 6. 常见故障处理

- 问题：模型列表空
- 处理：检查 `ALLOW_MOCK_PROVIDER` 与 API key；调用 `/api/v1/models` 查看 `enabled`

- 问题：聊天失败 502
- 处理：检查 provider key/base url；检查网络是否可达第三方接口

- 问题：Gemini 返回 429（配额不足）
- 处理：先补 Gemini 计费/配额；过渡期可切换 Kimi 保障可用

- 问题：`kimi-k2.5` 返回 400 `invalid temperature`
- 处理：确保后端对 `kimi-k2.5` 请求使用 `temperature=1`（不要用 0.7）

- 问题：登录后马上失效
- 处理：确认 `SECRET_KEY` 未变更；检查客户端 token 是否被旧值覆盖

- 问题：健康检查 Redis error
- 处理：本地无 Redis 可忽略（不影响主聊天链路）；上线时再补 Redis 服务
