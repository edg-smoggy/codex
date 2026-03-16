"""
utils.py — 工具函数
"""

import json
import re
from typing import Optional


def format_history_for_context(history: list, max_turns: int = 3) -> str:
    """
    将 Gradio chatbot 格式的对话历史格式化为供 LLM 阅读的纯文本。

    Args:
        history: Gradio chatbot 格式的对话历史，每个元素是 [user_msg, assistant_msg]。
        max_turns: 最多取最近几轮。

    Returns:
        str: 格式化后的文本。如果没有历史则返回空字符串。
    """
    if not history:
        return ""

    recent = history[-max_turns:]
    lines = []
    for turn in recent:
        if len(turn) >= 2:
            if turn[0]:
                lines.append(f"用户：{turn[0]}")
            if turn[1]:
                lines.append(f"安抚师：{turn[1]}")
    return "\n".join(lines)


def safe_json_parse(text: str) -> Optional[dict]:
    """
    安全解析 JSON 字符串。支持从 Markdown code block 中提取 JSON。

    Args:
        text: 可能包含 JSON 的文本。

    Returns:
        dict: 解析成功返回 dict；失败返回 None。
    """
    if not text:
        return None

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown code block 中提取
    # 匹配 ```json ... ``` 或 ``` ... ```
    patterns = [
        r"```json\s*\n?(.*?)\n?\s*```",
        r"```\s*\n?(.*?)\n?\s*```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    # 尝试找到第一个 { 和最后一个 } 之间的内容
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            return json.loads(text[first_brace : last_brace + 1])
        except json.JSONDecodeError:
            pass

    print(f"[safe_json_parse] 无法解析 JSON: {text[:200]}")
    return None
