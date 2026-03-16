"""
response_generator.py — Layer 3: 回复生成层
将策略注入 System Prompt，调用 LLM 生成最终的安抚回复。
"""

from openai import OpenAI
from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    GENERATOR_TEMPERATURE,
    GENERATOR_MAX_TOKENS,
    CONTEXT_WINDOW_RESPONSE,
)
from prompts import RESPONSE_SYSTEM_PROMPT_TEMPLATE


class ResponseGenerator:
    """回复生成器：基于策略和情绪状态生成安抚回复。"""

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

    def _resolve_temperature(self) -> float:
        # Kimi K2 系列当前要求 temperature 固定为 1
        if isinstance(LLM_MODEL, str) and LLM_MODEL.startswith("kimi-k2"):
            return 1
        return GENERATOR_TEMPERATURE

    def generate(
        self,
        user_input: str,
        emotion_result: dict,
        strategy: dict,
        trend: dict,
        conversation_history: list,
    ) -> str:
        """
        生成安抚回复。

        Args:
            user_input: 用户当前输入的消息文本。
            emotion_result: Layer 1 的情绪分析结果 dict。
            strategy: Layer 2 的策略决策结果 dict。
            trend: Layer 2 的趋势检测结果 dict。
            conversation_history: Gradio chatbot 格式的对话历史，
                                  每个元素是 [user_msg, assistant_msg]。

        Returns:
            str: 生成的安抚回复文本。
        """
        # Gradio 在首轮可能传入 None，统一归一化为空列表
        conversation_history = conversation_history or []

        # 组装 system prompt
        system_prompt = RESPONSE_SYSTEM_PROMPT_TEMPLATE.format(
            emotion_type=emotion_result.get("emotion_type", "neutral"),
            sub_type=emotion_result.get("sub_type", "未知"),
            intensity=emotion_result.get("intensity", 1),
            trend=trend.get("description", "情绪状态相对稳定"),
            strategy_name=strategy.get("name", "gentle_acknowledge"),
            strategy_instructions=strategy.get("instructions", ""),
            response_constraints=strategy.get("response_constraints", ""),
            confrontation_info=strategy.get("confrontation_info", "无"),
        )

        # 构建消息列表：system + 最近 N 轮历史 + 当前用户消息
        messages = [{"role": "system", "content": system_prompt}]

        # 取最近 CONTEXT_WINDOW_RESPONSE 轮对话
        recent_history = conversation_history[-CONTEXT_WINDOW_RESPONSE:]
        for turn in recent_history:
            if len(turn) >= 2:
                if turn[0]:
                    messages.append({"role": "user", "content": turn[0]})
                if turn[1]:
                    messages.append({"role": "assistant", "content": turn[1]})

        # 添加当前用户消息
        messages.append({"role": "user", "content": user_input})

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=self._resolve_temperature(),
                max_tokens=GENERATOR_MAX_TOKENS,
            )
            reply = response.choices[0].message.content.strip()
            return reply
        except Exception as e:
            print(f"[ResponseGenerator] LLM 调用失败: {e}")
            return "我现在遇到了一些技术问题，但我仍然在这里。你可以继续跟我说，我会尽力回应你。"
