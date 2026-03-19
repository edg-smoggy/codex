from __future__ import annotations

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
from app.providers.router import ProviderResult, generate_reply_stream, list_supported_models
from app.schemas import ChatStreamRequest
from app.services.audit import log_action
from app.services.auth import require_active_user
from app.services.quota import apply_usage, check_quota_before_chat

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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

    await db.commit()

    async def event_gen() -> AsyncIterator[str]:
        full_content = ""
        final_result: Optional[ProviderResult] = None
        provider = enabled_models[payload.model]["provider"]

        yield _sse(
            "meta",
            {
                "conversation_id": conversation.id,
                "assistant_message_id": "",
                "model": payload.model,
                "provider": provider,
            },
        )

        try:
            async for chunk in generate_reply_stream(payload.model, messages):
                if isinstance(chunk, str):
                    if not chunk:
                        continue
                    full_content += chunk
                    yield _sse("chunk", {"delta": chunk})
                    continue
                final_result = chunk

            if not final_result:
                raise RuntimeError("Provider stream ended without final result")

            assistant_content = full_content or final_result.content
            assistant_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=assistant_content,
                model=final_result.model,
                provider=final_result.provider,
                input_tokens=final_result.input_tokens,
                output_tokens=final_result.output_tokens,
                cost=final_result.cost,
            )
            db.add(assistant_msg)

            usage = await apply_usage(
                db,
                user_id=user.id,
                input_tokens=final_result.input_tokens,
                output_tokens=final_result.output_tokens,
                total_cost=final_result.cost,
            )

            await log_action(
                db,
                user_id=user.id,
                action="chat.completed",
                detail={
                    "conversation_id": conversation.id,
                    "model": final_result.model,
                    "provider": final_result.provider,
                    "input_tokens": final_result.input_tokens,
                    "output_tokens": final_result.output_tokens,
                    "cost": final_result.cost,
                },
            )
            await db.commit()
            await db.refresh(assistant_msg)

            yield _sse(
                "done",
                {
                    "usage": {
                        "input_tokens": final_result.input_tokens,
                        "output_tokens": final_result.output_tokens,
                        "cost": final_result.cost,
                        "daily_total_tokens": usage.input_tokens + usage.output_tokens,
                        "daily_total_cost": usage.total_cost,
                    },
                    "assistant_message_id": assistant_msg.id,
                },
            )
        except httpx.HTTPStatusError as exc:
            await log_action(
                db,
                user_id=user.id,
                action="chat.provider_error",
                detail={
                    "conversation_id": conversation.id,
                    "model": payload.model,
                    "status_code": exc.response.status_code,
                    "body": exc.response.text[:300],
                },
            )
            await db.commit()
            yield _sse("error", {"detail": "Provider request failed"})
        except Exception as exc:
            await log_action(
                db,
                user_id=user.id,
                action="chat.runtime_error",
                detail={
                    "conversation_id": conversation.id,
                    "model": payload.model,
                    "error": str(exc)[:300],
                },
            )
            await db.commit()
            yield _sse("error", {"detail": "Chat failed"})

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)
