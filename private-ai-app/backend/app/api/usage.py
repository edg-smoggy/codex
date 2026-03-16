from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import UsageDaily
from app.schemas import UsageMeResponse
from app.services.auth import require_active_user
from app.services.quota import get_or_create_today_usage, today_utc_date

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me/daily", response_model=UsageMeResponse)
async def usage_me_daily(
    user=Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> UsageMeResponse:
    usage = await db.scalar(
        select(UsageDaily).where(
            UsageDaily.user_id == user.id,
            UsageDaily.usage_date == today_utc_date(),
        )
    )
    if not usage:
        usage = await get_or_create_today_usage(db, user.id)
        await db.commit()

    total_tokens = usage.input_tokens + usage.output_tokens
    return UsageMeResponse(
        usage_date=usage.usage_date,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=total_tokens,
        total_cost=usage.total_cost,
        daily_token_limit=user.daily_token_limit,
        daily_cost_limit=user.daily_cost_limit,
    )
