# 飞书客服 Agent（3 天 POC 最小打通版）

此实现使用飞书事件长连接（WebSocket）模式，不依赖公网回调地址，适合先快速打通“能对话”。

## 1. 前置条件

- Python 3.9+
- 飞书自建应用（企业内部应用）
- 应用已开启机器人能力
- 事件订阅中开启 `im.message.receive_v1`

## 2. 飞书后台配置

1. 打开飞书开放平台，进入你的应用。
2. 在「机器人」里开启机器人能力。
3. 在「事件订阅」里开启长连接模式（或允许 SDK 长连接接收事件）。
4. 订阅事件：`im.message.receive_v1`。
5. 发布应用版本并安装到企业。
6. 在需要测试的群聊/私聊里把机器人加入会话。

说明：如果你配置了 `Verification Token` / `Encrypt Key`，请同步写入 `.env`。

## 3. 本地运行

```bash
cd /Users/bytedance/Documents/codex1/feishu_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，至少填写：

```bash
APP_ID=cli_xxx
APP_SECRET=xxx
```

启动：

```bash
python3 main.py
```

启动后，给机器人发送文本消息，默认会回：
- `客服助手：收到你的消息「...」`

一键启动（自动安装依赖）：

```bash
./start.sh
```

## 4. 对接你的 Harness Agent

如果你已经有 Agent HTTP 接口，设置：

```bash
AGENT_API_URL=http://127.0.0.1:8000/api/agent/chat
```

请求体约定：

```json
{
  "session_id": "chat_id:open_id",
  "user_id": "open_id",
  "text": "用户消息",
  "channel": "feishu"
}
```

返回体约定：

```json
{
  "reply_text": "给飞书用户的回复",
  "action": "reply|handoff",
  "trace_id": "optional"
}
```

当前版本只读取 `reply_text` 进行回复。

## 5. 常见问题

- 收不到消息：
  - 检查应用是否发布并安装。
  - 检查机器人是否在当前会话中。
  - 检查是否订阅 `im.message.receive_v1`。
- 启动报鉴权失败：
  - 核对 `APP_ID` / `APP_SECRET` 是否来自同一个应用。
- 重复回复：
  - 程序内已做 event_id 去重；若仍重复，检查飞书侧重试和多实例部署。

## 6. 参考

- 飞书开放平台 Echo Bot 示例（官方）：
  - <https://github.com/larksuite/lark-samples/tree/main/echo_bot/python>
