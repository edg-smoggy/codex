#!/bin/bash
set -euo pipefail

PROJECT_DIR="/Users/bytedance/Documents/codex1/emotion_agent"
cd "$PROJECT_DIR"

# 优先使用当前环境变量；如果没设置，则尝试从 macOS Keychain 读取
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  OPENAI_API_KEY="$(
    security find-generic-password -a "$USER" -s emotion-agent-kimi-key -w 2>/dev/null \
      || security find-generic-password -a "$USER" -s emotion-agent-openai-key -w 2>/dev/null \
      || true
  )"
  export OPENAI_API_KEY
fi

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "未找到 OPENAI_API_KEY。"
  echo "请先执行："
  echo "security add-generic-password -a \"$USER\" -s emotion-agent-kimi-key -w 'sk-xxx' -U"
  read -r -p "按回车键退出..."
  exit 1
fi

# 防止误用占位 key 导致“看起来启动成功但每次都报技术问题”
if [[ "${OPENAI_API_KEY}" == "sk-你的key" || "${OPENAI_API_KEY}" == "sk-placeholder" || "${OPENAI_API_KEY}" == *"your-api-key"* ]]; then
  echo "检测到占位 OPENAI_API_KEY（不是可用的真实密钥）。"
  echo "请先写入真实 Kimi Key："
  echo "security add-generic-password -a \"$USER\" -s emotion-agent-kimi-key -w 'sk-你的真实KimiKey' -U"
  read -r -p "按回车键退出..."
  exit 1
fi

# 懒人模式：固定使用 Kimi 官方 OpenAI 兼容端点和模型，避免被旧环境变量覆盖
export OPENAI_BASE_URL="https://api.moonshot.cn/v1"
export OPENAI_MODEL="kimi-k2.5"
export GRADIO_SERVER_NAME="${GRADIO_SERVER_NAME:-127.0.0.1}"
export GRADIO_SERVER_PORT="${GRADIO_SERVER_PORT:-7860}"
export NO_PROXY="${NO_PROXY:-127.0.0.1,localhost}"
export no_proxy="${no_proxy:-127.0.0.1,localhost}"

echo "Using OPENAI_BASE_URL=${OPENAI_BASE_URL}"
echo "Using OPENAI_MODEL=${OPENAI_MODEL}"

python3 app.py &
APP_PID=$!

for _ in {1..30}; do
  if curl -sS "http://127.0.0.1:${GRADIO_SERVER_PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

open "http://127.0.0.1:${GRADIO_SERVER_PORT}"
wait "$APP_PID"
