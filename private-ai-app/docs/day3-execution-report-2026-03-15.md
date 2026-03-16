# Day3 执行报告（2026-03-15）

## 目标

- 完成管理员/成员身份明确区分（单入口登录，不新增专用管理员登录 API）。
- 切换到真 Key（`ALLOW_MOCK_PROVIDER=false`）并完成 OpenAI / Gemini / Kimi 三模型回归。
- 验证异常场景（超时 / 429 / 5xx）在前端与后端均可追踪。

## 当前状态

- 结论：Day3 已执行，结果为“部分通过（OpenAI 按用户要求豁免；Gemini 因上游配额不足未通过；Kimi 通过可用）”。

## 已完成项

- 管理员区分改造已完成：
  - 新增管理员角色切换脚本：`backend/scripts/promote_admin.py`
  - 登录页改为三入口：`管理员登录 / 成员登录 / 成员注册`
  - 登录时增加角色强校验（入口与账号角色不匹配时直接拒绝）
  - 登录后账号区与主聊天栏新增管理员/成员 badge
- 验证结果：
  - 前端构建通过：`desktop npm run build`
  - smoke 持续通过（13/13）：`backend/artifacts/smoke-report-20260315-153500.json`
  - 管理员权限边界验证通过（admin=200, member=403）：
    - `backend/artifacts/day3-admin-role-check-20260315-153454.json`
  - 管理员封禁/解封链路复测通过：
    - `backend/artifacts/day3-admin-block-unblock-20260315-213843.json`
  - `promote_admin.py` 提升/回滚验证通过（`member_demo` 账号已回滚为 `member`）

## 真 Key 回归结果

- 配置已就绪：
  - `ALLOW_MOCK_PROVIDER=false`
  - `OPENAI_API_KEY` 已清空（按用户要求本轮不验收 OpenAI）
  - `GEMINI_API_KEY/KIMI_API_KEY` 已设置
- 证据：
  - `backend/artifacts/day3-key-readiness-20260315-213817.json`
- Gemini/Kimi 真实请求回归（OpenAI 已豁免）：
  - 结果：Gemini `502`（上游 429），Kimi `200`（通过）
  - 报告：`backend/artifacts/day3-gemini-kimi-check-20260315-225626.json`
  - 上游错误证据：`backend/artifacts/day3-provider-error-evidence-20260315-225648.json`
- 会话与用量一致性：`usage_status=200`、`conversations_status=200`（同回归报告）。
- 核心链路稳定性（真实 provider）：
  - Kimi 连续 20 次通过：`backend/artifacts/day3-stability-20ops-kimi-20260315-214116.json`
- `kimi-k2.5` 接入回归（2026-03-16）：
  - 首次失败原因：上游 `400 invalid temperature: only 1 is allowed for this model`
  - 修复：后端针对 `kimi-k2.5` 使用 `temperature=1`（其余模型保持原默认）
  - 修复后结果：`/models` 包含 `kimi-k2.5` 且 `/chat/stream` 返回 `200`（含 `meta/chunk/done`）
  - 证据：`backend/artifacts/day3-kimi-k25-regression-fix-20260316-021601.json`

## 异常场景回归（完成）

- 429 / 500 / timeout 三场景均完成并通过断言：
  - 汇总：`backend/artifacts/day3-exception-regression-20260315-213757.json`
  - 429、500 返回 `502: Provider request failed`（`chat.provider_error`）
  - timeout 返回 `500: Chat failed`（`chat.runtime_error`）
- 前端可读错误验证：
  - `frontend_message_example` 已记录在异常回归报告中，格式如 `502: Provider request failed`、`500: Chat failed`。

## 验收判定

- [x] 管理员/成员身份区分清晰（登录文案 + 界面 badge + 权限边界）
- [x] `ALLOW_MOCK_PROVIDER=false`
- [x] OpenAI 至少 1 模型通过（豁免：用户明确本轮不验收 OpenAI）
- [ ] Gemini 至少 1 模型通过（失败原因：上游 429 配额不足）
- [x] Kimi 至少 1 模型通过
- [x] 至少 1 家真实模型可稳定使用（Kimi 通过且 20 次稳定性通过）
- [x] 超时 / 429 / 5xx 异常场景完成并留证
