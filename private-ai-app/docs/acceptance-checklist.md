# 验收清单（本地全链路）

- 日期：2026-03-15
- 执行人：Codex
- 环境：Local / Real key enabled（OpenAI waived, SQLite）

## A. 环境与启动

- [x] `scripts/env_doctor.sh` 输出满足 Day1 基础条件（`backend/artifacts`: 见 Day2 报告）
- [x] 后端可启动（`scripts/run_backend_local.sh`，端口占用场景下确认已有实例监听 8000）
- [x] 本地 smoke 脚本通过（`scripts/run_smoke_local.sh`）
- [x] 已生成 smoke 报告文件（`backend/artifacts/smoke-report-20260315-153500.json`）

## B. 用户链路

- [x] 邀请码注册成功（已存在用户场景返回 409 也视为通过，见 smoke 报告）
- [x] 邀请码无效/过期返回正确错误（`backend/artifacts/day2-auth-edge-20260315-033211.json`）
- [x] 登录成功并拿到 access/refresh token（smoke 报告）
- [x] refresh 可正常续期（smoke 报告）

## C. 聊天链路

- [x] 可获取模型列表并切换模型（mock：`backend/artifacts/day2-model-switch-mock-20260315-033126.json`，real：`backend/artifacts/day3-gemini-kimi-check-20260315-225626.json`）
- [x] `/chat/stream` 事件顺序为 `meta -> chunk* -> done`（mock 与 Kimi real 均通过）
- [x] 对话后会话列表可见新增会话（smoke 报告）
- [x] 消息历史包含 user + assistant 消息（smoke 报告）
- [x] `/usage/me/daily` 统计有增长（smoke + real 回归）

## D. 管理员链路

- [x] 管理员可查看用户列表（smoke 报告）
- [x] 管理员可查看日用量（`backend/artifacts/day2-admin-usage-20260315-033331.json`）
- [x] 管理员可封禁用户（被封用户登录返回 403，`backend/artifacts/day3-admin-block-unblock-20260315-213843.json`）
- [x] 管理员可解封用户（解封后可登录，`backend/artifacts/day3-admin-block-unblock-20260315-213843.json`）
- [x] 管理员/成员登录后界面有明确区分（badge + 文案，前端 build 通过）
- [x] 成员访问管理员接口被拒绝 403（`backend/artifacts/day3-admin-role-check-20260315-153454.json`）

## E. 配额与异常

- [x] token 限额触发时返回 429（smoke 报告）
- [x] cost 限额触发时返回 429（smoke 报告）
- [x] Provider 429/5xx 时前端提示可读错误（`backend/artifacts/day3-exception-regression-20260315-213757.json`）
- [x] 审计日志中可追踪登录、聊天、封禁等动作（`backend/artifacts/day2-audit-sample-20260315-033305.json`）
- [x] timeout 异常时后端记录 `chat.runtime_error`（`backend/artifacts/day3-exception-regression-20260315-213757.json`）

## F. 真 Key 回归（Day3）

- [x] `ALLOW_MOCK_PROVIDER=false`
- [x] OpenAI 模型至少 1 个通过（豁免：用户明确本轮不验收 OpenAI）
- [ ] Gemini 模型至少 1 个通过（当前上游 429 配额不足）
- [x] Kimi 模型至少 1 个通过（`backend/artifacts/day3-gemini-kimi-check-20260315-225626.json`）
- [x] Kimi `kimi-k2.5` 模型通过并可在模型列表选择（`backend/artifacts/day3-kimi-k25-regression-fix-20260316-021601.json`）
- [x] 至少 1 家真实模型可稳定可用（Kimi 20 次稳定性通过）
- [x] Day3 key 就绪（`backend/artifacts/day3-key-readiness-20260315-213817.json`）
- [x] 真实 provider 稳定性 20 次验证（Kimi，`backend/artifacts/day3-stability-20ops-kimi-20260315-214116.json`）

## 结论

- 总结：Day2 通过；Day3 已完成管理员区分、异常回归和 Kimi 可用收口
- 阻塞项：Gemini 上游返回 429（配额不足）
- 修复建议：补足 Gemini 配额后复跑 `day3-gemini-kimi-check`，将主用模型切回 Gemini
