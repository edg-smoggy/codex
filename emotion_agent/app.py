"""
app.py — Gradio 主应用入口
情绪安抚 Agent 的 Web 界面，包含聊天框和调试面板。
"""

import os
import gradio as gr
from gradio_client import utils as gradio_client_utils
from config import (
    GRADIO_TITLE,
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
    CHATBOT_HEIGHT,
)
from emotion_analyzer import EmotionAnalyzer
from strategy_engine import StrategyEngine
from response_generator import ResponseGenerator


# ─────────────────────────────────────────────
# 兼容补丁：gradio_client bool schema 崩溃
# ─────────────────────────────────────────────
if not getattr(gradio_client_utils, "_bool_schema_patch_applied", False):
    _original_json_schema_to_python_type = gradio_client_utils._json_schema_to_python_type

    def _patched_json_schema_to_python_type(schema, defs=None):
        # 某些版本会把 bool 作为 schema 传入，原实现会在 `if "const" in schema` 崩溃
        if isinstance(schema, bool):
            return "Any"
        return _original_json_schema_to_python_type(schema, defs)

    gradio_client_utils._json_schema_to_python_type = _patched_json_schema_to_python_type
    gradio_client_utils._bool_schema_patch_applied = True


# ─────────────────────────────────────────────
# 初始化三层管道
# ─────────────────────────────────────────────
analyzer = EmotionAnalyzer()
engine = StrategyEngine()
generator = ResponseGenerator()


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────

EMOTION_TYPE_CN: dict = {
    "anger": "愤怒 (anger)",
    "anxiety": "焦虑 (anxiety)",
    "sadness": "悲伤 (sadness)",
    "neutral": "中性 (neutral)",
    "positive": "积极 (positive)",
    "boundary_violation": "越界 (boundary_violation)",
}

STRATEGY_CN: dict = {
    "gentle_acknowledge": "轻度安抚 (gentle_acknowledge)",
    "empathetic_support": "共情支持 (empathetic_support)",
    "deep_empathy": "深度共情 (deep_empathy)",
    "crisis_protocol": "危机干预 (crisis_protocol)",
    "boundary_redirect": "越界重定向 (boundary_redirect)",
}

TREND_CN: dict = {
    "escalating": "⬆️ 情绪升级",
    "deescalating": "⬇️ 情绪好转",
    "shifting": "🔄 情绪转变",
    "stable": "➡️ 相对稳定",
    "confrontation": "🔴 持续对抗",
}


def format_emotion_history(emotion_history: list) -> str:
    """格式化最近 5 轮的情绪历史记录。"""
    recent = emotion_history[-5:]
    if not recent:
        return "暂无记录"

    lines = []
    for i, record in enumerate(recent, 1):
        etype = record.get("emotion_type", "?")
        sub = record.get("sub_type", "?")
        intensity = record.get("intensity", "?")
        lines.append(f"第{i}轮: {etype}({sub}) 强度:{intensity}")
    return "\n".join(lines)


def respond(user_message: str, chat_history: list):
    """
    核心响应函数：执行三层管道并更新 UI。

    Args:
        user_message: 用户输入的文本。
        chat_history: Gradio chatbot 格式的对话历史。

    Returns:
        tuple: (清空输入框, 更新后的chat_history, 情绪类型, 强度,
                趋势, 策略, 对抗轮次, 情绪历史)
    """
    # Gradio 在首轮可能传入 None，统一归一化为空列表
    chat_history = chat_history or []

    if not user_message or not user_message.strip():
        return (
            "",
            chat_history,
            "等待输入...",
            0,
            "等待输入...",
            "等待输入...",
            "0",
            "暂无记录",
        )

    user_message = user_message.strip()

    # Step 1: 情绪分析
    emotion = analyzer.analyze(user_message, chat_history)

    # Step 2: 更新历史 & 检测趋势
    engine.update_history(emotion)
    trend = engine.detect_trend()

    # Step 3: 决策策略
    strategy = engine.decide_strategy(emotion, trend)

    # Step 4: 生成回复
    response = generator.generate(
        user_message, emotion, strategy, trend, chat_history
    )

    # Step 5: 更新对话历史
    chat_history = chat_history + [[user_message, response]]

    # Step 6: 组装调试面板数据
    emotion_type_str = EMOTION_TYPE_CN.get(
        emotion.get("emotion_type", "?"),
        emotion.get("emotion_type", "?"),
    )
    sub_type_str = emotion.get("sub_type", "?")
    display_emotion = f"{emotion_type_str} / {sub_type_str}"

    intensity_val = emotion.get("intensity", 0)

    trend_type = trend.get("trend_type", "stable")
    display_trend = TREND_CN.get(trend_type, trend_type)

    strategy_name = strategy.get("name", "?")
    display_strategy = STRATEGY_CN.get(strategy_name, strategy_name)

    confrontation_rounds = engine.get_confrontation_rounds()
    display_confrontation = str(confrontation_rounds)
    if confrontation_rounds >= 5:
        display_confrontation += " (强烈建议转人工)"
    elif confrontation_rounds >= 3:
        display_confrontation += " (建议转人工)"

    display_history = format_emotion_history(engine.emotion_history)

    return (
        "",                    # 清空输入框
        chat_history,          # 更新后的聊天记录
        display_emotion,       # 情绪类型显示
        intensity_val,         # 情绪强度 slider
        display_trend,         # 趋势显示
        display_strategy,      # 策略显示
        display_confrontation, # 对抗轮次
        display_history,       # 情绪历史
    )


def clear_conversation():
    """清空对话和所有状态。"""
    engine.reset()
    return (
        [],                # 清空聊天记录
        "等待输入...",     # 情绪类型
        0,                 # 强度
        "等待输入...",     # 趋势
        "等待输入...",     # 策略
        "0",               # 对抗轮次
        "暂无记录",        # 情绪历史
    )


# ─────────────────────────────────────────────
# Gradio UI 构建
# ─────────────────────────────────────────────

with gr.Blocks(
    title=GRADIO_TITLE,
    theme=gr.themes.Soft(),
    css="""
    .intensity-low { color: #22c55e !important; }
    .intensity-mid { color: #eab308 !important; }
    .intensity-high { color: #f97316 !important; }
    .intensity-extreme { color: #ef4444 !important; }
    """
) as demo:

    gr.Markdown(
        "# 🫂 情绪安抚 Agent\n"
        "我是你的情绪支持伙伴。如果你现在心情不好，可以跟我聊聊。"
    )

    with gr.Row():
        # ── 左侧：聊天区 ──
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                height=CHATBOT_HEIGHT,
                label="对话",
                placeholder="还没有对话，说说你的感受吧...",
            )
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="说说你的感受...",
                    label="",
                    scale=4,
                    show_label=False,
                )
                send_btn = gr.Button("发送", scale=1, variant="primary")
            clear_btn = gr.Button("🗑️ 清除对话", variant="secondary")

        # ── 右侧：调试面板 ──
        with gr.Column(scale=1):
            with gr.Accordion("📊 情绪分析面板", open=True):
                emotion_type_display = gr.Textbox(
                    label="情绪类型",
                    value="等待输入...",
                    interactive=False,
                )
                intensity_display = gr.Slider(
                    minimum=0,
                    maximum=10,
                    step=1,
                    value=0,
                    label="情绪强度",
                    interactive=False,
                )
                trend_display = gr.Textbox(
                    label="情绪趋势",
                    value="等待输入...",
                    interactive=False,
                )
                strategy_display = gr.Textbox(
                    label="当前策略",
                    value="等待输入...",
                    interactive=False,
                )
                confrontation_display = gr.Textbox(
                    label="对抗轮次",
                    value="0",
                    interactive=False,
                )
                history_display = gr.Textbox(
                    label="情绪历史 (最近5轮)",
                    value="暂无记录",
                    interactive=False,
                    lines=5,
                )

    # ── 输出组件列表 ──
    output_components = [
        msg,
        chatbot,
        emotion_type_display,
        intensity_display,
        trend_display,
        strategy_display,
        confrontation_display,
        history_display,
    ]

    # ── 事件绑定 ──
    # Enter 键发送
    msg.submit(
        fn=respond,
        inputs=[msg, chatbot],
        outputs=output_components,
    )

    # 点击发送按钮
    send_btn.click(
        fn=respond,
        inputs=[msg, chatbot],
        outputs=output_components,
    )

    # 清除对话
    clear_btn.click(
        fn=clear_conversation,
        inputs=[],
        outputs=[
            chatbot,
            emotion_type_display,
            intensity_display,
            trend_display,
            strategy_display,
            confrontation_display,
            history_display,
        ],
    )


# ─────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────
if __name__ == "__main__":
    try:
        demo.launch(
            server_name=GRADIO_SERVER_NAME,
            server_port=GRADIO_SERVER_PORT,
            share=False,
        )
    except ValueError as e:
        if "localhost is not accessible" not in str(e):
            raise
        print("[app] 检测到 localhost 不可访问，自动切换 share=True")
        demo.launch(
            server_name=GRADIO_SERVER_NAME,
            server_port=GRADIO_SERVER_PORT,
            share=True,
        )
