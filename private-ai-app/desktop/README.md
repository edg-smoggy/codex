# Desktop (Tauri + React)

## 开发运行

```bash
cd /Users/bytedance/Documents/codex1/private-ai-app/desktop
cp .env.example .env
npm install
npm run tauri:dev
```

## 打包

```bash
npm run tauri:build
```

## 配置

- `VITE_API_BASE_URL`: 后端 API 根路径（默认 `http://localhost:8000/api/v1`）
- `VITE_DATA_SOURCE_MODE`: 前端数据源模式，`real | mock | hybrid`（默认 `hybrid`）
