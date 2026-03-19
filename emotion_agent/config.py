"""
config.py — 全局配置
所有可调参数集中在此文件。通过环境变量覆盖，均有合理默认值。
"""

import os


# ─────────────────────────────────────────────
# LLM API 配置
# ─────────────────────────────────────────────
LLM_API_KEY: str = os.environ.get("OPENAI_API_KEY", "sk-placeholder")
LLM_BASE_URL: str = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
# 回复生成层可单独指定模型；未设置时回退到 OPENAI_MODEL
GENERATOR_MODEL: str = os.environ.get("OPENAI_GENERATOR_MODEL", LLM_MODEL)

# 情绪分析层使用的 temperature（越低越稳定）
ANALYZER_TEMPERATURE: float = 0.1
# 回复生成层使用的 temperature（稍高以增加自然感）
GENERATOR_TEMPERATURE: float = 0.7
# LLM 最大 token 数
ANALYZER_MAX_TOKENS: int = 512
GENERATOR_MAX_TOKENS: int = 320
# 回复生成层调用超时时间（秒）
GENERATOR_TIMEOUT_SECONDS: int = int(os.environ.get("GENERATOR_TIMEOUT_SECONDS", "20"))
# 回复生成层重试次数（不含首次调用）
GENERATOR_RETRY_MAX: int = int(os.environ.get("GENERATOR_RETRY_MAX", "1"))


# ─────────────────────────────────────────────
# 情绪分级阈值
# ─────────────────────────────────────────────
INTENSITY_MILD_MAX: int = 3       # 1-3: 轻微
INTENSITY_MODERATE_MAX: int = 6   # 4-6: 中等
INTENSITY_STRONG_MAX: int = 8     # 7-8: 强烈
# 9-10: 极端（无需单独定义上限）


# ─────────────────────────────────────────────
# 兜底/对抗升级配置
# ─────────────────────────────────────────────
# 连续高强度（intensity >= 此值）的轮次阈值
CONFRONTATION_INTENSITY_THRESHOLD: int = 7
# 连续多少轮高强度触发 "confrontation" 趋势
CONFRONTATION_ROUNDS_THRESHOLD: int = 3
# 第一次建议转人工的轮次（连续高强度的第 N 轮）
ESCALATION_SUGGEST_ROUND: int = 3
# 强烈建议转人工的轮次
ESCALATION_URGE_ROUND: int = 5

# 情绪历史最大保留轮次
MAX_EMOTION_HISTORY: int = 20
# 构造 LLM 上下文时使用的最近对话轮次数
CONTEXT_WINDOW_ANALYSIS: int = 3   # 用于情绪分析
CONTEXT_WINDOW_RESPONSE: int = 4  # 用于回复生成


# ─────────────────────────────────────────────
# Gradio UI 配置
# ─────────────────────────────────────────────
GRADIO_TITLE: str = "情绪安抚 Agent"
GRADIO_SERVER_NAME: str = os.environ.get("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_SERVER_PORT: int = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
CHATBOT_HEIGHT: int = 500
