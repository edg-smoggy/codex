"""
strategy_engine.py — Layer 2: 策略决策层
纯 Python 规则引擎。根据 情绪类型 × 强度 × 历史趋势 → 选择安抚策略。
"""

from config import (
    INTENSITY_MILD_MAX,
    INTENSITY_MODERATE_MAX,
    INTENSITY_STRONG_MAX,
    CONFRONTATION_INTENSITY_THRESHOLD,
    CONFRONTATION_ROUNDS_THRESHOLD,
    ESCALATION_SUGGEST_ROUND,
    ESCALATION_URGE_ROUND,
    MAX_EMOTION_HISTORY,
)
from typing import List

from prompts import (
    STRATEGY_GENTLE_ACKNOWLEDGE,
    STRATEGY_EMPATHETIC_SUPPORT,
    STRATEGY_DEEP_EMPATHY,
    STRATEGY_CRISIS_PROTOCOL,
    STRATEGY_BOUNDARY_REDIRECT,
    TREND_ESCALATING,
    TREND_DEESCALATING,
    TREND_SHIFTING,
    TREND_STABLE,
    TREND_CONFRONTATION_ESCALATION,
    ESCALATION_MESSAGE_SUGGEST,
    ESCALATION_MESSAGE_URGE,
)


class StrategyEngine:
    """策略决策引擎：基于规则的安抚策略选择器。"""

    def __init__(self) -> None:
        self.emotion_history: List[dict] = []

    def update_history(self, emotion_result: dict) -> None:
        """
        将最新的情绪分析结果追加到历史记录。
        保留最近 MAX_EMOTION_HISTORY 轮。
        """
        self.emotion_history.append(emotion_result)
        if len(self.emotion_history) > MAX_EMOTION_HISTORY:
            self.emotion_history = self.emotion_history[-MAX_EMOTION_HISTORY:]

    def detect_trend(self) -> dict:
        """
        检测情绪趋势。对比最近 2 轮的 emotion_type 和 intensity。

        Returns:
            dict: {
                "trend_type": "escalating|deescalating|shifting|stable|confrontation",
                "description": str,
                "old_emotion": str,
                "new_emotion": str,
            }
        """
        if len(self.emotion_history) < 2:
            return {
                "trend_type": "stable",
                "description": TREND_STABLE,
                "old_emotion": "",
                "new_emotion": "",
            }

        prev = self.emotion_history[-2]
        curr = self.emotion_history[-1]

        prev_type = prev.get("emotion_type", "neutral")
        curr_type = curr.get("emotion_type", "neutral")
        prev_intensity = prev.get("intensity", 1)
        curr_intensity = curr.get("intensity", 1)

        # 优先检查：连续高强度对抗
        confrontation_rounds = self.get_confrontation_rounds()
        if confrontation_rounds >= CONFRONTATION_ROUNDS_THRESHOLD:
            if confrontation_rounds >= ESCALATION_URGE_ROUND:
                escalation_msg = ESCALATION_MESSAGE_URGE
            elif confrontation_rounds >= ESCALATION_SUGGEST_ROUND:
                escalation_msg = ESCALATION_MESSAGE_SUGGEST
            else:
                escalation_msg = ""

            description = TREND_CONFRONTATION_ESCALATION.format(
                n=confrontation_rounds,
                escalation_message=escalation_msg,
            )
            return {
                "trend_type": "confrontation",
                "description": description,
                "old_emotion": prev_type,
                "new_emotion": curr_type,
            }

        # 从负面情绪转为 positive（优先于 shifting 检测）
        if curr_type == "positive" and prev_type in ("anger", "anxiety", "sadness"):
            return {
                "trend_type": "deescalating",
                "description": TREND_DEESCALATING,
                "old_emotion": prev_type,
                "new_emotion": curr_type,
            }

        # 情绪类型发生变化（排除 neutral、boundary_violation 和已处理的 positive）
        if prev_type != curr_type and curr_type not in ("neutral", "positive", "boundary_violation"):
            description = TREND_SHIFTING.format(
                old_emotion=prev_type,
                new_emotion=curr_type,
            )
            return {
                "trend_type": "shifting",
                "description": description,
                "old_emotion": prev_type,
                "new_emotion": curr_type,
            }

        # 强度变化
        intensity_diff = curr_intensity - prev_intensity
        if intensity_diff >= 2:
            return {
                "trend_type": "escalating",
                "description": TREND_ESCALATING,
                "old_emotion": prev_type,
                "new_emotion": curr_type,
            }
        elif intensity_diff <= -2:
            return {
                "trend_type": "deescalating",
                "description": TREND_DEESCALATING,
                "old_emotion": prev_type,
                "new_emotion": curr_type,
            }

        return {
            "trend_type": "stable",
            "description": TREND_STABLE,
            "old_emotion": prev_type,
            "new_emotion": curr_type,
        }

    def decide_strategy(self, emotion_result: dict, trend: dict) -> dict:
        """
        根据情绪分析结果和趋势，决定使用哪种安抚策略。

        优先级（从高到低）：
        1. 自伤信号 → crisis_protocol
        2. boundary_violation → boundary_redirect
        3. intensity 9-10 → crisis_protocol
        4. intensity 7-8 → deep_empathy
        5. intensity 4-6 → empathetic_support
        6. intensity 1-3 → gentle_acknowledge

        Returns:
            dict: {
                "name": str,
                "instructions": str,
                "response_constraints": str,
                "confrontation_info": str,
            }
        """
        emotion_type = emotion_result.get("emotion_type", "neutral")
        intensity = emotion_result.get("intensity", 1)
        has_self_harm = emotion_result.get("has_self_harm_signal", False)

        confrontation_info = ""
        if trend.get("trend_type") == "confrontation":
            confrontation_info = trend.get("description", "")

        # 优先级 1：自伤信号
        if has_self_harm:
            return {
                "name": "crisis_protocol",
                "instructions": STRATEGY_CRISIS_PROTOCOL,
                "response_constraints": "3-5句话。必须提供心理援助热线。语气温和坚定。",
                "confrontation_info": confrontation_info,
            }

        # 优先级 2：越界
        if emotion_type == "boundary_violation":
            return {
                "name": "boundary_redirect",
                "instructions": STRATEGY_BOUNDARY_REDIRECT,
                "response_constraints": "1-2句话。温和拒绝 + 开放情绪入口。",
                "confrontation_info": confrontation_info,
            }

        # 优先级 3-6：按强度分级
        if intensity >= 9:
            return {
                "name": "crisis_protocol",
                "instructions": STRATEGY_CRISIS_PROTOCOL,
                "response_constraints": "3-5句话。表达深切关心。建议专业支持。",
                "confrontation_info": confrontation_info,
            }
        elif intensity >= CONFRONTATION_INTENSITY_THRESHOLD:  # 7-8
            return {
                "name": "deep_empathy",
                "instructions": STRATEGY_DEEP_EMPATHY,
                "response_constraints": "3-5句话。全力共情，不转折，不给建议。",
                "confrontation_info": confrontation_info,
            }
        elif intensity > INTENSITY_MILD_MAX:  # 4-6
            return {
                "name": "empathetic_support",
                "instructions": STRATEGY_EMPATHETIC_SUPPORT,
                "response_constraints": "2-3句话。共情 + 适当询问。不给建议。",
                "confrontation_info": confrontation_info,
            }
        else:  # 1-3
            return {
                "name": "gentle_acknowledge",
                "instructions": STRATEGY_GENTLE_ACKNOWLEDGE,
                "response_constraints": "1-2句话。轻松简短，点到即止。",
                "confrontation_info": confrontation_info,
            }

    def get_confrontation_rounds(self) -> int:
        """
        返回从末尾往前连续高强度（intensity >= CONFRONTATION_INTENSITY_THRESHOLD）
        的轮次数。只统计负面情绪（anger, anxiety, sadness）。
        """
        count = 0
        for record in reversed(self.emotion_history):
            intensity = record.get("intensity", 0)
            emotion_type = record.get("emotion_type", "neutral")
            if (
                intensity >= CONFRONTATION_INTENSITY_THRESHOLD
                and emotion_type in ("anger", "anxiety", "sadness")
            ):
                count += 1
            else:
                break
        return count

    def reset(self) -> None:
        """清空情绪历史记录。"""
        self.emotion_history.clear()
