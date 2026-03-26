# AI Hub Direct

无后端直连版桌面 App。用于可信朋友之间直接分发安装包，不依赖登录、邀请码、管理员后台或云服务器。

## 特性

- Tauri + React + TypeScript
- 本地保存会话历史
- 直接连接 Gemini / Kimi / Claude(OpenRouter)
- 流式聊天
- Kimi 和 Claude 4.6 支持思考模式

## 目录说明

- `src/`: 前端界面和本地状态
- `src-tauri/src/main.rs`: 本地原生命令、流式请求、会话持久化
- `src-tauri/resources/providers.json`: 安装包内预置 provider 配置模板

## 首次配置

先复制一份本地真实配置：

```bash
cp src-tauri/resources/providers.example.json src-tauri/resources/providers.json
```

然后编辑：

`src-tauri/resources/providers.json`

填入你要随安装包分发的 key，例如：

```json
{
  "providers": [
    {
      "provider": "gemini",
      "api_key": "YOUR_GEMINI_KEY",
      "base_url": "https://generativelanguage.googleapis.com/v1beta",
      "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
      "enabled": true
    },
    {
      "provider": "kimi",
      "api_key": "YOUR_KIMI_KEY",
      "base_url": "https://api.moonshot.cn/v1",
      "models": ["kimi-k2.5", "moonshot-v1-8k", "moonshot-v1-32k"],
      "enabled": true
    },
    {
      "provider": "openrouter",
      "api_key": "YOUR_OPENROUTER_KEY",
      "base_url": "https://openrouter.ai/api/v1",
      "models": ["anthropic/claude-opus-4.6", "anthropic/claude-sonnet-4.6"],
      "enabled": true,
      "title": "AI Hub Direct"
    }
  ]
}
```

说明：

- `providers.json` 已被 `.gitignore` 忽略，不应提交到仓库。
- 首次启动时，App 会把这个文件复制到本地数据目录。
- 后续运行优先读取本地副本。
- 如果你更新 key，最稳妥的方式是重新打包新版本。

## 本地运行

```bash
cd /Users/bytedance/Documents/codex1/private-ai-direct-app
npm install
npm run tauri:dev
```

## 构建 Windows 安装包

```bash
cd /Users/bytedance/Documents/codex1/private-ai-direct-app
npm run tauri:build
```

默认 Tauri Windows 打包目标是 `nsis`。

## GitHub Actions 打 Windows 包

仓库已包含：

`/.github/workflows/build-direct-windows.yml`

它会在 Windows runner 上生成安装包。你需要先在 GitHub 仓库 Secrets 里配置：

- `GEMINI_API_KEY`
- `KIMI_API_KEY`
- `OPENROUTER_API_KEY`

然后在 Actions 里手动运行 `Build Direct App (Windows)`，下载产物即可。

## 本地数据位置

应用运行后会在系统本地数据目录创建：

- `providers.json`
- `conversations.json`

它们位于 `AIHubDirect` 目录下。

## 本版范围

本工程是直连版，不包含：

- 登录 / 注册
- 邀请码
- 管理员后台
- 配额 / 审计 / 封禁
- 远程后端 API
