from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Conversation, Message, MessageRole, utcnow
from app.providers.router import generate_reply, list_supported_models
from app.schemas import ChatStreamRequest
from app.services.audit import log_action
from app.services.auth import require_active_user
from app.services.quota import apply_usage, check_quota_before_chat

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _split_chunks(text: str, chunk_size: int = 32) -> list[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]


@router.post("/stream")
async def stream_chat(
    payload: ChatStreamRequest,
    user=Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    enabled_models = {
        item["model"]: item
        for item in list_supported_models()
        if item["enabled"]
    }
    if payload.model not in enabled_models:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Model unavailable")

    await check_quota_before_chat(db, user=user, input_text=payload.message)

    conversation: Optional[Conversation]
    if payload.conversation_id:
        conversation = await db.scalar(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.user_id == user.id,
            )
        )
        if not conversation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    else:
        conversation = Conversation(
            user_id=user.id,
            title=payload.message.strip().replace("\n", " ")[:40] or "New Chat",
            model=payload.model,
        )
        db.add(conversation)
        await db.flush()

    conversation.model = payload.model
    conversation.updated_at = utcnow()

    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.message,
        model=payload.model,
        provider=enabled_models[payload.model]["provider"],
        input_tokens=0,
        output_tokens=0,
        cost=0,
    )
    db.add(user_msg)
    await db.flush()

    history_rows = await db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = [
        {"role": row.role.value, "content": row.content}
        for row in history_rows.all()
        if row.role in {MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM}
    ]

    try:
        result = await generate_reply(payload.model, messages)
    except httpx.HTTPStatusError as exc:
        await log_action(
            db,
            user_id=user.id,
            action="chat.provider_error",
            detail={
                "model": payload.model,
                "status_code": exc.response.status_code,
                "body": exc.response.text[:300],
            },
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Provider request failed") from exc
    except Exception as exc:
        await log_action(
            db,
            user_id=user.id,
            action="chat.runtime_error",
            detail={"model": payload.model, "error": str(exc)[:300]},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Chat failed") from exc

    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=result.content,
        model=result.model,
        provider=result.provider,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost=result.cost,
    )
    db.add(assistant_msg)

    usage = await apply_usage(
        db,
        user_id=user.id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_cost=result.cost,
    )

    await log_action(
        db,
        user_id=user.id,
        action="chat.completed",
        detail={
            "conversation_id": conversation.id,
            "model": result.model,
            "provider": result.provider,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cost": result.cost,
        },
    )

    await db.commit()
    await db.refresh(assistant_msg)

    async def event_gen() -> AsyncIterator[str]:
        yield _sse(
            "meta",
            {
                "conversation_id": conversation.id,
                "assistant_message_id": assistant_msg.id,
                "model": result.model,
                "provider": result.provider,
            },
        )
        for chunk in _split_chunks(result.content, 36):
            yield _sse("chunk", {"delta": chunk})
            await asyncio.sleep(0.01)
        yield _sse(
            "done",
            {
                "usage": {
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "cost": result.cost,
                    "daily_total_tokens": usage.input_tokens + usage.output_tokens,
                    "daily_total_cost": usage.total_cost,
                }
            },
        )

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
