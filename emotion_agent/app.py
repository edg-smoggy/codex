"""
app.py — Gradio 主应用入口
情绪安抚 Agent 的 Web 界面，包含聊天框和调试面板。
"""

import time
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


def build_debug_snapshot(emotion: dict, trend: dict, strategy: dict) -> tuple:
    """组装调试面板的静态字段。"""
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
        display_emotion,
        intensity_val,
        display_trend,
        display_strategy,
        display_confrontation,
        display_history,
    )


def respond(user_message: str, chat_history: list):
    """
    核心响应函数：执行三层管道并更新 UI。

    Args:
        user_message: 用户输入的文本。
        chat_history: Gradio chatbot 格式的对话历史。

    Yields:
        tuple: (清空输入框, 更新后的chat_history, 情绪类型, 强度,
                趋势, 策略, 对抗轮次, 情绪历史, 本轮耗时)
    """
    # Gradio 在首轮可能传入 None，统一归一化为空列表
    chat_history = chat_history or []

    if not user_message or not user_message.strip():
        yield (
            "",
            [turn[:] for turn in chat_history],
            "等待输入...",
            0,
            "等待输入...",
            "等待输入...",
            "0",
            "暂无记录",
            "等待输入...",
        )
        return

    user_message = user_message.strip()
    turn_start = time.perf_counter()

    # Step 1: 情绪分析
    analyzer_start = time.perf_counter()
    emotion = analyzer.analyze(user_message, chat_history)
    analyzer_ms = int((time.perf_counter() - analyzer_start) * 1000)

    # Step 2: 更新历史 & 检测趋势
    engine.update_history(emotion)
    trend = engine.detect_trend()

    # Step 3: 决策策略
    strategy = engine.decide_strategy(emotion, trend)

    # Step 4: 先插入空 assistant 气泡，立即刷新 UI
    chat_history = chat_history + [[user_message, ""]]
    (
        display_emotion,
        intensity_val,
        display_trend,
        display_strategy,
        display_confrontation,
        display_history,
    ) = build_debug_snapshot(emotion, trend, strategy)
    yield (
        "",
        [turn[:] for turn in chat_history],
        display_emotion,
        intensity_val,
        display_trend,
        display_strategy,
        display_confrontation,
        display_history,
        f"analyzer={analyzer_ms}ms | first_token=-- | total=--",
    )

    # Step 5: 流式生成回复
    first_token_ms = None
    chunks = []
    for piece in generator.generate_stream(
        user_input=user_message,
        emotion_result=emotion,
        strategy=strategy,
        trend=trend,
        conversation_history=chat_history[:-1],
    ):
        if piece and first_token_ms is None:
            first_token_ms = int((time.perf_counter() - turn_start) * 1000)

        chunks.append(piece)
        chat_history[-1][1] = "".join(chunks)

        total_ms = int((time.perf_counter() - turn_start) * 1000)
        first_token_display = str(first_token_ms) if first_token_ms is not None else "--"
        yield (
            "",
            [turn[:] for turn in chat_history],
            display_emotion,
            intensity_val,
            display_trend,
            display_strategy,
            display_confrontation,
            display_history,
            f"analyzer={analyzer_ms}ms | first_token={first_token_display}ms | total={total_ms}ms",
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
        "等待输入...",     # 本轮耗时
    )


# ─────────────────────────────────────────────
# Gradio UI 构建
# ─────────────────────────────────────────────

with gr.Blocks(
    title=GRADIO_TITLE,
    theme=gr.themes.Soft(),
    css="""
    :root {
        --primary-color: #6366f1;
        --secondary-color: #818cf8;
        --bg-color: #f8fafc;
        --text-color: #334155;
        --panel-bg: #ffffff;
        --border-color: #e2e8f0;
    }

    body {
        background-color: var(--bg-color) !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }

    .gradio-container {
        max-width: 1200px !important;
        margin: auto;
        padding: 2rem !important;
        background: transparent !important;
    }

    .header-area {
        text-align: center;
        margin-bottom: 2rem;
        padding: 1.5rem;
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
        border-radius: 1rem;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }

    .header-area h1 {
        color: white !important;
        margin-bottom: 0.5rem !important;
        font-weight: 700;
        font-size: 2.2rem;
    }

    .header-area p {
        font-size: 1.1rem;
        opacity: 0.9;
        margin: 0;
    }

    .chat-wrapper {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        height: 100%;
    }

    .chat-container {
        border-radius: 1rem !important;
        background: var(--panel-bg) !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05) !important;
        overflow: hidden;
    }

    .chatbot-box {
        border: none !important;
        background: transparent !important;
    }

    .message {
        border-radius: 1rem !important;
        padding: 1rem 1.2rem !important;
        line-height: 1.5 !important;
    }

    .user-message {
        background: #f1f5f9 !important;
        border-bottom-right-radius: 0.2rem !important;
    }

    .bot-message {
        background: linear-gradient(135deg, #e0e7ff, #ede9fe) !important;
        border-bottom-left-radius: 0.2rem !important;
    }

    .input-area {
        background: var(--panel-bg) !important;
        border-radius: 1rem !important;
        padding: 0.5rem !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        margin: 0 !important;
        align-items: center !important;
    }

    .input-textbox textarea {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        resize: none !important;
    }

    .input-textbox textarea:focus {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    .send-btn {
        background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
        color: white !important;
        border: none !important;
        border-radius: 0.75rem !important;
        font-weight: 600 !important;
        transition: transform 0.1s, box-shadow 0.1s !important;
        height: 100% !important;
        min-height: 3.5rem !important;
        margin: 0.5rem !important;
    }

    .send-btn:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
    }

    .send-btn:active {
        transform: translateY(1px) !important;
    }

    .clear-btn {
        background: transparent !important;
        border: 1px dashed #cbd5e1 !important;
        color: #64748b !important;
        border-radius: 0.75rem !important;
        margin-top: 0.5rem !important;
        width: 100% !important;
    }

    .clear-btn:hover {
        background: #f8fafc !important;
        color: #ef4444 !important;
        border-color: #ef4444 !important;
    }

    .dashboard-panel {
        background: var(--panel-bg) !important;
        border-radius: 1rem !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05) !important;
        padding: 1rem !important;
        height: 100% !important;
    }

    .dashboard-accordion {
        border: none !important;
        background: transparent !important;
    }

    .dashboard-accordion > button {
        background: #f8fafc !important;
        border-radius: 0.75rem !important;
        font-weight: 600 !important;
        color: var(--text-color) !important;
        padding: 1rem !important;
        margin-bottom: 1rem !important;
    }

    .status-card {
        background: #f8fafc !important;
        border-radius: 0.75rem !important;
        padding: 0.75rem !important;
        margin-bottom: 0.75rem !important;
        border: 1px solid #e2e8f0 !important;
        transition: all 0.2s ease !important;
    }

    .status-card:hover {
        border-color: #cbd5e1 !important;
        background: white !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
    }

    .status-card input, .status-card textarea {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: 500 !important;
        color: var(--text-color) !important;
    }

    .intensity-low { color: #10b981 !important; font-weight: bold; }
    .intensity-mid { color: #f59e0b !important; font-weight: bold; }
    .intensity-high { color: #f97316 !important; font-weight: bold; }
    .intensity-extreme { color: #ef4444 !important; font-weight: bold; }
    """
) as demo:

    with gr.Column(elem_classes="header-area"):
        gr.Markdown(
            "<h1>🫂 情绪安抚 Agent</h1>\n"
            "<p>我是你的情绪支持伙伴。如果你现在心情不好，可以跟我聊聊，我会在这里倾听。</p>"
        )

    with gr.Row():
        # ── 左侧：聊天区 ──
        with gr.Column(scale=7, elem_classes="chat-wrapper"):
            with gr.Column(elem_classes="chat-container"):
                chatbot = gr.Chatbot(
                    height=CHATBOT_HEIGHT,
                    label="",
                    elem_classes="chatbot-box",
                    show_label=False,
                    bubble_full_width=False,
                    avatar_images=(
                        None,
                        "https://api.dicebear.com/7.x/bottts/svg?seed=Felix&backgroundColor=e0e7ff",
                    ),
                    placeholder="还没有对话，说说你的感受吧...",
                )

            with gr.Row(elem_classes="input-area"):
                msg = gr.Textbox(
                    placeholder="在这里输入你的感受... (按 Enter 发送)",
                    label=" ",
                    scale=5,
                    show_label=False,
                    elem_classes="input-textbox",
                    lines=2,
                    max_lines=5,
                )
                send_btn = gr.Button("发送 ✨", scale=1, variant="primary", elem_classes="send-btn")

            clear_btn = gr.Button("🗑️ 清空对话记录", variant="secondary", elem_classes="clear-btn", size="sm")

        # ── 右侧：调试面板 ──
        with gr.Column(scale=3, elem_classes="dashboard-panel"):
            with gr.Accordion("📊 情绪状态洞察", open=True, elem_classes="dashboard-accordion"):
                emotion_type_display = gr.Textbox(
                    label="情绪类型",
                    value="等待输入...",
                    interactive=False,
                    elem_classes="status-card",
                )
                intensity_display = gr.Slider(
                    minimum=0,
                    maximum=10,
                    step=1,
                    value=0,
                    label="情绪强度",
                    interactive=False,
                    elem_classes="status-card",
                )
                trend_display = gr.Textbox(
                    label="情绪趋势",
                    value="等待输入...",
                    interactive=False,
                    elem_classes="status-card",
                )
                strategy_display = gr.Textbox(
                    label="当前策略",
                    value="等待输入...",
                    interactive=False,
                    elem_classes="status-card",
                )
                confrontation_display = gr.Textbox(
                    label="对抗轮次",
                    value="0",
                    interactive=False,
                    elem_classes="status-card",
                )
                history_display = gr.Textbox(
                    label="情绪历史 (最近5轮)",
                    value="暂无记录",
                    interactive=False,
                    lines=5,
                    elem_classes="status-card",
                )
                latency_display = gr.Textbox(
                    label="本轮耗时 (ms)",
                    value="等待输入...",
                    interactive=False,
                    elem_classes="status-card",
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
        latency_display,
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
            latency_display,
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
