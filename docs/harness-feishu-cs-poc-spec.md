# 客服 Agent 小场景复现方案（Harness 架构 + 飞书接入）

- 版本：v1.0
- 日期：2026-03-10（Asia/Shanghai）
- 目标交付日：2026-03-13
- 文档类型：实施 Spec（3 天可落地）

## 1. 目标与范围

### 1.1 目标
在 3 天内复现一个可上线灰度的小场景客服能力，效果为：
- 用户可在飞书中与客服 Agent 对话。
- Agent 能基于小场景知识正确答复并执行有限工具动作。
- 对不确定、超范围、风险操作自动兜底转人工。

### 1.2 范围（In Scope）
- 仅做 1 个小场景（建议：`订单进度查询 + 异常转人工`）。
- 覆盖从“飞书消息进入”到“Agent 回复/转人工”的全链路。
- 迁移旧系统中的该小场景业务逻辑（不迁移旧画布引擎）。

### 1.3 非目标（Out of Scope）
- 不复刻完整 workflow 画布能力。
- 不做多场景通用编排平台。
- 不做复杂多 Agent 协同。

## 2. 核心约束与原则

### 2.1 约束
- 时间固定：2026-03-10 到 2026-03-13（3 天）。
- 团队对 Harness 细节不熟，需要“最小闭环”优先。
- 旧系统核心逻辑在画布/流程中，直接复制成本高。

### 2.2 原则
- 迁移“业务语义”而非“画布形态”。
- 先跑通闭环，再提升泛化能力。
- 所有关键决策可观测、可回放、可审计。

## 3. 目标架构（最小可复现）

```text
Feishu Bot
  -> Feishu Webhook Adapter
    -> Session Router (open_id/chat_id -> session_id)
      -> Harness Agent Runtime
         |- Policy/Guardrail
         |- Intent + Slot Filling
         |- Knowledge Retriever (RAG)
         |- Tool Caller
      -> Response Composer
    -> Feishu Reply API

Side Systems:
- Knowledge Store (小场景知识库)
- Tool APIs (查单/建单/转人工)
- Trace & Metrics (日志、链路、评测)
```

### 3.1 组件职责
- `Feishu Webhook Adapter`：签名校验、事件解析、幂等去重、快速 ACK。
- `Session Router`：同一用户会话上下文归一。
- `Harness Agent Runtime`：执行推理、检索、工具调用、策略控制。
- `Knowledge Store`：存放场景 SOP/FAQ/边界条件。
- `Tool APIs`：封装可执行动作，返回结构化结果。
- `Trace & Metrics`：记录每轮输入、判定、工具调用、输出与耗时。

## 4. 旧画布逻辑迁移方法（关键）

将旧 workflow 画布抽取为 3 类资产：

1. 知识资产：FAQ、SOP、话术模板、边界定义。
2. 规则资产：决策表（条件 -> 动作 -> 兜底）。
3. 动作资产：可调用接口（查单、建单、转人工）。

### 4.1 场景卡（必须先产出）

每个小场景统一产出一张 `Scene Card`：
- 场景名
- 用户意图列表
- 必填槽位（如订单号、手机号后四位）
- 决策规则（命中条件、优先级、冲突处理）
- 工具映射（规则 -> API）
- 回复模板（成功/失败/追问）
- 风险边界（哪些情况必须转人工）

### 4.2 决策表模板

| Rule ID | 条件 | 动作 | 回复模板 | 失败兜底 |
|---|---|---|---|---|
| R1 | 有订单号且可查到状态 | `get_order_status` | T_SUCCESS | T_FALLBACK |
| R2 | 缺订单号 | 追问订单号 | T_ASK_ORDER_ID | T_FALLBACK |
| R3 | 命中异常关键词（投诉/退款争议） | `handoff_to_human` | T_HANDOFF | T_HANDOFF |

## 5. Harness 侧实现规范

> 说明：此处按“通用 Harness Agent Runtime”模式定义，重点是接口与流程，不依赖完整画布能力。

### 5.1 运行链路

1. 读取会话上下文 + 当前用户消息。
2. 先做策略检查（敏感词、越权、风险操作）。
3. 做意图识别与槽位提取。
4. 如果缺关键槽位，先追问，不调用工具。
5. 执行知识检索，拼接上下文。
6. 按决策表判断是否调用工具。
7. 生成回复；若失败/不确定 -> 转人工。
8. 写入 trace + metrics。

### 5.2 Prompt 分层
- `System Prompt`：角色、边界、风格、禁止事项。
- `Policy Prompt`：风险与转人工规则。
- `Scene Prompt`：当前场景决策表、可用工具说明。
- `Context Prompt`：检索片段 + 会话摘要。

### 5.3 工具契约（示例）

#### Tool: `get_order_status`
- 输入：
```json
{
  "order_id": "string",
  "user_id": "string"
}
```
- 输出：
```json
{
  "success": true,
  "status": "delivered|shipping|pending|failed",
  "eta": "2026-03-12",
  "reason_code": "string",
  "reason_text": "string"
}
```

#### Tool: `handoff_to_human`
- 输入：
```json
{
  "session_id": "string",
  "reason": "string",
  "summary": "string"
}
```
- 输出：
```json
{
  "success": true,
  "ticket_id": "CS123456",
  "queue": "order_support"
}
```

## 6. 知识喂数方案（3 天可执行）

### 6.1 数据来源
- 旧系统该场景 FAQ。
- 旧画布节点文案（用户可见文案、条件描述）。
- 客服 SOP 文档。

### 6.2 数据处理
- 去重与统一术语（订单、运单、签收等同义词统一）。
- 按“问题-答案-边界”切块（300-600 字/块）。
- 每块附 metadata：`scene`, `intent`, `priority`, `updated_at`。

### 6.3 检索策略
- TopK=3（首版）。
- 命中置信度低时：不硬答，转追问或转人工。
- 永远优先“规则资产”再“知识资产”。

## 7. 飞书打通 Spec

### 7.1 接入流程
1. 创建飞书机器人应用，开通消息事件订阅。
2. 配置回调 URL：`POST /api/feishu/webhook`。
3. 实现签名校验与事件去重（event_id + timestamp）。
4. 3 秒内 ACK；异步调用 Agent 再回消息。

### 7.2 会话与身份
- 主键映射：`tenant_key + open_id + chat_id -> session_id`。
- 会话 TTL：30 分钟无消息自动新会话。
- 落库存字段：消息原文、解析结果、响应、trace_id。

### 7.3 异常处理
- 回调失败重试要幂等。
- Agent 超时（>8s）时返回兜底文案并转人工。
- 工具接口失败时不暴露系统错误，返回业务可读提示。

### 7.4 安全
- 验签失败直接拒绝。
- 日志脱敏（手机号、订单号中间位打码）。
- 风险请求（退款/改地址）强制二次确认或转人工。

## 8. API 约定（MVP）

### 8.1 Feishu Webhook
- `POST /api/feishu/webhook`
- 入参：飞书事件 payload
- 出参：`{"code":0}`（快速 ACK）

### 8.2 Agent Chat
- `POST /api/agent/chat`
- 入参：
```json
{
  "session_id": "string",
  "user_id": "string",
  "text": "用户消息",
  "channel": "feishu"
}
```
- 出参：
```json
{
  "reply_text": "string",
  "action": "reply|handoff",
  "trace_id": "string"
}
```

## 9. 可观测性与评测

### 9.1 必采指标
- 端到端延迟 P50/P95。
- 工具调用成功率。
- 首轮命中率（无需追问即可完成）。
- 转人工率。
- 幻觉率（答非所问或编造）。

### 9.2 最小评测集（上线前）
- 30-50 条真实/半真实对话。
- 覆盖：正常查询、缺槽位、异常投诉、越界问题、工具失败。
- 通过阈值（建议）：
  - 任务完成率 >= 75%
  - 幻觉率 <= 5%
  - 转人工率 <= 35%
  - P95 响应 <= 6s

## 10. 三天实施计划（含具体日期）

### Day 1（2026-03-11）
- 锁定唯一小场景与边界。
- 产出 Scene Card + 决策表 + 工具清单。
- 完成飞书 webhook 验签、ACK、消息收发最小链路。
- 准备 20 条初始测试语料。

### Day 2（2026-03-12）
- 接入 Harness Agent Runtime（意图/槽位/检索/工具调用）。
- 完成知识库导入与检索配置。
- 完成 `get_order_status` 与 `handoff_to_human`（可先 mock）。
- 打通端到端联调，产出 trace。

### Day 3（2026-03-13）
- 用 30-50 条语料回放评测并调参。
- 修正高频失败路径（缺槽位追问、异常兜底）。
- 上线灰度（小群/白名单）并设人工值守。
- 交付验收报告 + 已知问题清单 + 下一阶段计划。

## 11. 交付物清单

1. 实施 Spec（本文档）。
2. `Scene Card`（目标场景 1 份）。
3. 决策表（规则资产 1 份）。
4. 工具 API 契约与 mock 服务。
5. 飞书 webhook 服务与会话路由。
6. 评测集与评测报告。
7. 上线回滚预案。

## 12. 验收标准（Definition of Done）

- 飞书内可稳定完成目标场景问答与动作调用。
- 缺槽位能追问；高风险/不确定能转人工。
- 全链路有 trace_id，可定位每轮决策与工具调用。
- 指标达成第 9.2 节阈值。

## 13. 风险与兜底

### 风险 R1：Harness 细节不熟导致落地慢
- 兜底：先实现固定流程 Agent（规则优先），Harness 只承载推理与工具调用。

### 风险 R2：飞书权限或配置延迟
- 兜底：先用本地 webhook 回放 + 沙箱群验证，正式权限到位后切换。

### 风险 R3：后端业务接口不稳定
- 兜底：工具层加熔断与超时，失败自动转人工。

### 风险 R4：知识质量差导致答非所问
- 兜底：低置信度不直接回答，改为追问或转人工。

## 14. 附录：可直接复用的场景配置样例

```yaml
scene_id: order_status_v1
intents:
  - query_order_status
required_slots:
  - order_id
rules:
  - id: R1
    when: "intent == query_order_status && has(order_id)"
    action: "tool:get_order_status"
    on_success_template: "订单{{order_id}}当前状态：{{status}}，预计{{eta}}。"
    on_fail: "handoff_to_human"
  - id: R2
    when: "intent == query_order_status && !has(order_id)"
    action: "ask_slot:order_id"
fallback:
  strategy: "handoff_to_human"
  message: "我先帮你转人工同学继续处理。"
```

## 15. 启动清单（今天立刻执行）

1. 选定唯一小场景名称与成功定义。
2. 指定 1 人负责飞书接入、1 人负责 Agent/工具、1 人负责语料评测。
3. 当天结束前必须产出：
   - Scene Card
   - 决策表
   - 飞书消息收发通路

## 16. 开发任务拆解（到小时，建议）

### 16.1 Day 1（2026-03-11）
- 10:00-12:00：从旧画布抽取 Scene Card 与规则表。
- 13:30-15:30：完成飞书 webhook、验签、幂等、ACK。
- 15:30-18:00：打通回消息能力（文本消息先行）。
- 20:00 前：准备 20 条基础语料。

### 16.2 Day 2（2026-03-12）
- 10:00-12:00：接入 Agent Runtime + Prompt 分层。
- 13:30-15:30：导入知识库并调试检索（TopK、阈值）。
- 15:30-18:00：接入工具（至少 1 真 1 mock）。
- 20:00 前：完成端到端联调与 trace 落库。

### 16.3 Day 3（2026-03-13）
- 10:00-12:00：50 条回放评测，出失败 Top10。
- 13:30-15:30：修正高频失败路径与兜底逻辑。
- 15:30-17:00：灰度发布（白名单群）。
- 17:00-18:00：输出验收报告与回滚确认单。

## 17. 上线与回滚 Runbook

### 17.1 上线步骤
1. 配置开关：`agent_scene_order_status_v1 = ON`（仅白名单）。
2. 灰度群验证 20 条标准语料。
3. 指标观察 30 分钟（失败率、超时率、转人工率）。
4. 指标达标后扩大白名单。

### 17.2 回滚触发条件
- 5 分钟内连续 3 次严重错误（工具调用失败且未兜底）。
- P95 响应时延 > 10s 持续 10 分钟。
- 幻觉率在抽检中 > 10%。

### 17.3 回滚动作
1. 关闭开关：`agent_scene_order_status_v1 = OFF`。
2. 飞书端统一返回“系统升级中，已转人工”文案。
3. 保留 trace，导出失败样本进入修复列表。

## 18. 需你当天拍板的 5 个参数

1. 小场景最终名称（建议：订单进度查询）。
2. 低置信度阈值（建议：0.65）。
3. 工具超时阈值（建议：3s）。
4. 自动转人工阈值（建议：单会话 2 次失败）。
5. 灰度白名单范围（建议：1 个内部群 + 10 位试用用户）。
