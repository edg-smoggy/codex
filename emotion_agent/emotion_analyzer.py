"""
emotion_analyzer.py — Layer 1: 情绪感知层
使用 LLM 分析用户消息中的情绪状态，输出结构化的情绪分析结果。
"""

from openai import OpenAI
from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    ANALYZER_TEMPERATURE,
    ANALYZER_MAX_TOKENS,
    CONTEXT_WINDOW_ANALYSIS,
)
from prompts import EMOTION_ANALYSIS_PROMPT
from utils import format_history_for_context, safe_json_parse


class EmotionAnalyzer:
    """情绪分析器：调用 LLM 对用户输入进行情绪分类和强度打分。"""

    # 当 LLM 返回无法解析的结果时使用的默认值
    DEFAULT_RESULT: dict = {
        "emotion_type": "neutral",
        "sub_type": "平静",
        "intensity": 1,
        "has_self_harm_signal": False,
        "reasoning": "无法解析情绪分析结果，使用默认值",
    }

    VALID_EMOTION_TYPES: set = {
        "anger",
        "anxiety",
        "sadness",
        "neutral",
        "positive",
        "boundary_violation",
    }

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

    def _resolve_temperature(self) -> float:
        # Kimi K2 系列当前要求 temperature 固定为 1
        if isinstance(LLM_MODEL, str) and LLM_MODEL.startswith("kimi-k2"):
            return 1
        return ANALYZER_TEMPERATURE

    def analyze(self, user_input: str, conversation_history: list) -> dict:
        """
        分析用户输入的情绪状态。

        Args:
            user_input: 用户当前输入的消息文本。
            conversation_history: Gradio chatbot 格式的对话历史，
                                  每个元素是 [user_msg, assistant_msg]。

        Returns:
            dict: 包含 emotion_type, sub_type, intensity,
                  has_self_harm_signal, reasoning 的字典。
        """
        # 构造上下文：最近 N 轮对话 + 当前输入
        context_text = format_history_for_context(
            conversation_history, max_turns=CONTEXT_WINDOW_ANALYSIS
        )

        if context_text:
            user_message_content = (
                f"以下是最近的对话上下文：\n{context_text}\n\n"
                f"请分析用户的最新消息：\n{user_input}"
            )
        else:
            user_message_content = f"请分析用户的最新消息：\n{user_input}"

        messages = [
            {"role": "system", "content": EMOTION_ANALYSIS_PROMPT},
            {"role": "user", "content": user_message_content},
        ]

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=self._resolve_temperature(),
                max_tokens=ANALYZER_MAX_TOKENS,
            )
            raw_text = response.choices[0].message.content.strip()
            result = safe_json_parse(raw_text)

            if result is None:
                return dict(self.DEFAULT_RESULT)

            # 校验和修正字段
            result = self._validate_and_fix(result)
            return result

        except Exception as e:
            print(f"[EmotionAnalyzer] LLM 调用失败: {e}")
            return dict(self.DEFAULT_RESULT)

    def _validate_and_fix(self, result: dict) -> dict:
        """校验 LLM 返回的 JSON 字段，修正不合法的值。"""
        # emotion_type
        if result.get("emotion_type") not in self.VALID_EMOTION_TYPES:
            result["emotion_type"] = "neutral"
            result["sub_type"] = "平静"

        # sub_type
        if not isinstance(result.get("sub_type"), str) or not result["sub_type"]:
            result["sub_type"] = "未知"

        # intensity
        try:
            intensity = int(result.get("intensity", 1))
            result["intensity"] = max(1, min(10, intensity))
        except (ValueError, TypeError):
            result["intensity"] = 1

        # has_self_harm_signal
        if not isinstance(result.get("has_self_harm_signal"), bool):
            result["has_self_harm_signal"] = False

        # reasoning
        if not isinstance(result.get("reasoning"), str):
            result["reasoning"] = ""

        return result
