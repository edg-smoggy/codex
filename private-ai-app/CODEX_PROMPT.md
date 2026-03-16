# AI Hub — Codex 提示词 (前端 UI 重构)

你是一个高级前端工程师。你的任务是将现有的 AI Hub 项目的前端 UI 重构为高质量的、可维护的生产级代码。

## 项目背景

AI Hub 是一个多模型 AI 聊天平台（类似 Poe），允许管理员将自己的 GPT/Claude/Gemini/DeepSeek 等模型额度共享给朋友使用。项目包含两个前端界面：

1. **用户端** (`index.html`) — 朋友们使用的聊天界面，可选择模型、创建对话、发送消息
2. **管理端** (`admin.html`) — 管理员后台，包含仪表盘、用户管理、模型管理、API 密钥管理、日志、系统设置

## 当前状态

目前有两个 **纯前端 HTML Demo**（`index.html` 和 `admin.html`），它们：
- 已经具有完整的 UI 设计和交互逻辑
- 使用了统一的暗色主题和设计系统（CSS Variables）
- 数据是模拟的（硬编码 + setTimeout 模拟 AI 回复）

## 你的核心任务

请基于这两个 HTML 文件的 **设计语言和视觉风格**，将项目重构为一个正式的前端工程。具体要求：

### 1. 工程化重构
- 使用 **React + TypeScript** (或 Vue 3 + TypeScript，你选择一个更适合的)
- 使用 **Vite** 作为构建工具
- 使用 **Tailwind CSS** 或提取出统一的 CSS 设计系统
- 组件化拆分：每个 UI 模块独立为组件
- 路由：用户端和管理端为两个独立路由（或两个入口）

### 2. 严格还原设计风格
**最重要的一条：必须 100% 还原 `index.html` 和 `admin.html` 中的视觉设计。** 包括但不限于：
- 暗色主题配色（`--bg-primary: #0a0a0f`, `--accent: #6c5ce7` 等）
- 渐变色、发光阴影、圆角
- 动画效果（消息出现动画、浮动动画、打字指示器）
- 模型选择器弹窗的搜索和分类布局
- 管理端的卡片布局、表格样式、甜甜圈图、柱状图
- 所有的 hover 效果和过渡动画

### 3. 接口对接准备
将模拟数据替换为标准的 API 调用结构，使用 mock / placeholder 函数：

```typescript
// api/chat.ts
export async function sendChatMessage(params: {
  model: string;
  messages: Message[];
  stream?: boolean;
}) : Promise<ReadableStream | ChatResponse> {
  // TODO: 对接实际后端 API
}

// api/admin.ts
export async function getUsers(params: PaginationParams): Promise<UserListResponse> { ... }
export async function getModels(): Promise<ModelConfig[]> { ... }
export async function updateModelStatus(modelId: string, enabled: boolean): Promise<void> { ... }
export async function getApiKeys(): Promise<ApiKey[]> { ... }
export async function getDashboardStats(): Promise<DashboardStats> { ... }
export async function getLogs(params: LogFilterParams): Promise<LogEntry[]> { ... }
```

### 4. 状态管理
- 用户端：当前选中模型、对话列表、当前对话消息、输入状态
- 管理端：当前页面、用户列表、模型配置、API 密钥列表、日志、设置
- 使用 Zustand / Pinia 或 React Context

### 5. 流式响应支持 (用户端)
用户端的 AI 回复需要支持 **SSE (Server-Sent Events) 流式输出**：
- 收到消息后逐字/逐 token 渲染
- 显示打字指示器 → 流式内容 → 完成
- 支持中途停止生成

### 6. 目录结构建议

```
ai-hub/
├── src/
│   ├── components/
│   │   ├── chat/              # 聊天相关组件
│   │   │   ├── ChatMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   ├── ModelSelector.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── WelcomeScreen.tsx
│   │   ├── admin/             # 管理端组件
│   │   │   ├── Dashboard.tsx
│   │   │   ├── UserTable.tsx
│   │   │   ├── ModelManager.tsx
│   │   │   ├── ApiKeyManager.tsx
│   │   │   ├── LogViewer.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── StatsCard.tsx
│   │   └── shared/            # 共享组件
│   │       ├── Button.tsx
│   │       ├── Badge.tsx
│   │       ├── Toggle.tsx
│   │       ├── Table.tsx
│   │       └── Modal.tsx
│   ├── api/                   # API 层
│   ├── stores/                # 状态管理
│   ├── types/                 # TypeScript 类型定义
│   ├── styles/                # 全局样式 / 设计 token
│   ├── hooks/                 # 自定义 hooks
│   ├── pages/
│   │   ├── ChatPage.tsx
│   │   └── AdminPage.tsx
│   └── App.tsx
├── public/
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tailwind.config.ts
```

### 7. 关键设计 Token（必须使用）

```css
/* 从 Demo 中提取的设计系统 */
--bg-primary: #0a0a0f;
--bg-secondary: #12121a;
--bg-tertiary: #1a1a26;
--surface: #16161f;
--border: rgba(255,255,255,0.06);
--text-primary: #f0f0f5;
--text-secondary: #9090a8;
--text-tertiary: #606078;
--accent: #6c5ce7;         /* 主色调：紫色 */
--green: #00cec9;           /* 在线/成功 */
--orange: #f39c12;          /* 警告 */
--red: #ff6b6b;             /* 错误/危险 */
--blue: #74b9ff;            /* 信息 */
--pink: #fd79a8;            /* 创意 */
--radius-sm: 8px;
--radius-md: 12px;
--radius-lg: 16px;
```

### 8. 注意事项
- **不要降低视觉质量**：Demo 中所有的渐变、阴影、动画都必须保留
- **不要简化布局**：管理端的 6 个页面（仪表盘、用户、模型、密钥、日志、设置）全部保留
- **Markdown 渲染**：用户端的 AI 回复需要支持 Markdown（代码高亮、列表、粗体等）
- **响应式**：在窄屏下隐藏侧边栏
- **无障碍**：按钮有 aria-label，键盘可操作

## 参考文件

请仔细阅读附带的 `index.html`（用户端）和 `admin.html`（管理端），它们是你的 **设计权威参考**。所有视觉细节以这两个文件为准。
