import json
import logging
import os
import time
from typing import Optional, Set

import requests
import lark_oapi as lark
from dotenv import load_dotenv
from lark_oapi.api.im.v1 import (
    P2ImMessageReceiveV1,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    ReplyMessageResponse,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("feishu-bot")

load_dotenv()


APP_ID = os.getenv("APP_ID", "").strip()
APP_SECRET = os.getenv("APP_SECRET", "").strip()
VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "").strip()
ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "").strip()

AGENT_API_URL = os.getenv("AGENT_API_URL", "").strip()
AGENT_API_TIMEOUT_SEC = float(os.getenv("AGENT_API_TIMEOUT_SEC", "6"))
REPLY_PREFIX = os.getenv("REPLY_PREFIX", "客服助手")

if not APP_ID or not APP_SECRET:
    raise RuntimeError("APP_ID / APP_SECRET is required.")


def _safe_get_open_id(event: P2ImMessageReceiveV1) -> str:
    sender = getattr(event.event, "sender", None)
    sender_id = getattr(sender, "sender_id", None)
    open_id = getattr(sender_id, "open_id", None)
    return open_id or "unknown_user"


def _safe_get_session_id(event: P2ImMessageReceiveV1) -> str:
    message = event.event.message
    chat_id = getattr(message, "chat_id", "") or "unknown_chat"
    open_id = _safe_get_open_id(event)
    return f"{chat_id}:{open_id}"


def _text_from_message_content(content: str) -> str:
    if not content:
        return ""
    try:
        payload = json.loads(content)
        if isinstance(payload, dict):
            return str(payload.get("text", "")).strip()
        return ""
    except json.JSONDecodeError:
        return ""


def _to_text_content(reply_text: str) -> str:
    return json.dumps({"text": reply_text}, ensure_ascii=False)


def _call_agent_api(session_id: str, user_id: str, text: str) -> Optional[str]:
    if not AGENT_API_URL:
        return None

    payload = {
        "session_id": session_id,
        "user_id": user_id,
        "text": text,
        "channel": "feishu",
    }
    try:
        resp = requests.post(AGENT_API_URL, json=payload, timeout=AGENT_API_TIMEOUT_SEC)
        resp.raise_for_status()
        data = resp.json()
        reply_text = data.get("reply_text")
        if isinstance(reply_text, str) and reply_text.strip():
            return reply_text.strip()
    except Exception as exc:
        logger.exception("agent api call failed: %s", exc)
    return None


def _build_reply(event: P2ImMessageReceiveV1) -> str:
    message = event.event.message
    if message.message_type != "text":
        return f"{REPLY_PREFIX}：暂时只支持文本消息。"

    user_text = _text_from_message_content(message.content)
    if not user_text:
        return f"{REPLY_PREFIX}：消息解析失败，请重新发送文本。"

    session_id = _safe_get_session_id(event)
    user_id = _safe_get_open_id(event)

    agent_reply = _call_agent_api(session_id=session_id, user_id=user_id, text=user_text)
    if agent_reply:
        return agent_reply

    return f"{REPLY_PREFIX}：收到你的消息「{user_text}」"


_handled_event_ids: Set[str] = set()
_handled_events_max = 5000


def _is_duplicate(event_id: str) -> bool:
    if not event_id:
        return False
    if event_id in _handled_event_ids:
        return True
    if len(_handled_event_ids) >= _handled_events_max:
        _handled_event_ids.clear()
    _handled_event_ids.add(event_id)
    return False


def _reply_message(message_id: str, reply_text: str) -> None:
    request: ReplyMessageRequest = (
        ReplyMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            ReplyMessageRequestBody.builder()
            .msg_type("text")
            .content(_to_text_content(reply_text))
            .build()
        )
        .build()
    )

    response: ReplyMessageResponse = client.im.v1.message.reply(request)
    if not response.success():
        raise RuntimeError(
            "reply failed, code=%s, msg=%s, log_id=%s"
            % (response.code, response.msg, response.get_log_id())
        )


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    header = getattr(data, "header", None)
    event_id = getattr(header, "event_id", "")
    if _is_duplicate(event_id):
        logger.info("skip duplicate event_id=%s", event_id)
        return

    sender = getattr(data.event, "sender", None)
    sender_type = getattr(sender, "sender_type", "")
    if sender_type and sender_type != "user":
        logger.info("skip non-user sender_type=%s", sender_type)
        return

    message = data.event.message
    logger.info(
        "received event_id=%s message_id=%s message_type=%s chat_id=%s",
        event_id,
        message.message_id,
        message.message_type,
        message.chat_id,
    )

    reply_text = _build_reply(data)
    _reply_message(message.message_id, reply_text)
    logger.info("replied message_id=%s", message.message_id)


event_handler = (
    lark.EventDispatcherHandler.builder(VERIFICATION_TOKEN, ENCRYPT_KEY)
    .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
    .build()
)

client = lark.Client.builder().app_id(APP_ID).app_secret(APP_SECRET).build()

ws_client = lark.ws.Client(
    APP_ID,
    APP_SECRET,
    event_handler=event_handler,
    log_level=lark.LogLevel.INFO,
)


def main() -> None:
    logger.info("feishu bot started in websocket mode")
    logger.info("agent_api=%s", AGENT_API_URL if AGENT_API_URL else "disabled")
    while True:
        try:
            ws_client.start()
        except Exception as exc:
            logger.exception("ws client exited with error: %s", exc)
            time.sleep(3)


if __name__ == "__main__":
    main()
