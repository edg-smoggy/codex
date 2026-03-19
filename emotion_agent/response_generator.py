"""
response_generator.py — Layer 3: 回复生成层
将策略注入 System Prompt，调用 LLM 生成最终的安抚回复。
"""

import time
from typing import Iterator, List

from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)
from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    GENERATOR_MODEL,
    GENERATOR_TEMPERATURE,
    GENERATOR_MAX_TOKENS,
    CONTEXT_WINDOW_RESPONSE,
    GENERATOR_TIMEOUT_SECONDS,
    GENERATOR_RETRY_MAX,
)
from prompts import RESPONSE_SYSTEM_PROMPT_TEMPLATE


class ResponseGenerator:
    """回复生成器：基于策略和情绪状态生成安抚回复。"""
    FALLBACK_REPLY: str = "我在认真听你说。刚刚网络有点慢，你可以再说一句，我会继续陪着你。"

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
        )

    def _resolve_model(self) -> str:
        return GENERATOR_MODEL or LLM_MODEL

    def _resolve_temperature(self, model_name: str) -> float:
        # Kimi K2 系列当前要求 temperature 固定为 1
        if isinstance(model_name, str) and model_name.startswith("kimi-k2"):
            return 1
        return GENERATOR_TEMPERATURE

    def _build_messages(
        self,
        user_input: str,
        emotion_result: dict,
        strategy: dict,
        trend: dict,
        conversation_history: list,
    ) -> List[dict]:
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
        messages: List[dict] = [{"role": "system", "content": system_prompt}]

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
        return messages

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError)):
            return True
        message = str(exc).lower()
        return "429" in message or "overloaded" in message or "timeout" in message

    def generate_stream(
        self,
        user_input: str,
        emotion_result: dict,
        strategy: dict,
        trend: dict,
        conversation_history: list,
    ) -> Iterator[str]:
        """
        以流式方式生成安抚回复。

        Args:
            user_input: 用户当前输入的消息文本。
            emotion_result: Layer 1 的情绪分析结果 dict。
            strategy: Layer 2 的策略决策结果 dict。
            trend: Layer 2 的趋势检测结果 dict。
            conversation_history: Gradio chatbot 格式的对话历史，
                                  每个元素是 [user_msg, assistant_msg]。
        """
        model_name = self._resolve_model()
        temperature = self._resolve_temperature(model_name)
        messages = self._build_messages(
            user_input=user_input,
            emotion_result=emotion_result,
            strategy=strategy,
            trend=trend,
            conversation_history=conversation_history,
        )

        generated_any = False
        attempts = 1 + max(0, GENERATOR_RETRY_MAX)
        for attempt in range(attempts):
            try:
                stream = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=GENERATOR_MAX_TOKENS,
                    stream=True,
                    timeout=GENERATOR_TIMEOUT_SECONDS,
                )
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    piece = delta.content if delta and delta.content else ""
                    if piece:
                        generated_any = True
                        yield piece

                if generated_any:
                    return
            except Exception as e:
                if generated_any:
                    print(f"[ResponseGenerator] 流式中断（保留已生成内容）: {e}")
                    return
                can_retry = attempt < attempts - 1 and self._is_retryable(e)
                if can_retry:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                print(f"[ResponseGenerator] LLM 调用失败: {e}")
                break

            # 没有内容时尝试一次快速重试
            if not generated_any and attempt < attempts - 1:
                time.sleep(0.2)
                continue

        if not generated_any:
            yield self.FALLBACK_REPLY

    def generate(
        self,
        user_input: str,
        emotion_result: dict,
        strategy: dict,
        trend: dict,
        conversation_history: list,
    ) -> str:
        """
        兼容非流式调用：内部复用 generate_stream 聚合完整文本。
        """
        chunks = []
        for piece in self.generate_stream(
            user_input=user_input,
            emotion_result=emotion_result,
            strategy=strategy,
            trend=trend,
            conversation_history=conversation_history,
        ):
            chunks.append(piece)

        reply = "".join(chunks).strip()
        return reply or self.FALLBACK_REPLY
