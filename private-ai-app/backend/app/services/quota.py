from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsageDaily, User


@dataclass
class UsageSnapshot:
    input_tokens: int
    output_tokens: int
    total_cost: float


@dataclass
class QuotaCheckResult:
    usage: UsageSnapshot
    remaining_tokens: int
    remaining_cost: float


def today_utc_date() -> datetime.date:
    return datetime.now(timezone.utc).date()


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


async def get_or_create_today_usage(db: AsyncSession, user_id: str) -> UsageDaily:
    usage_date = today_utc_date()
    usage = await db.scalar(
        select(UsageDaily).where(
            UsageDaily.user_id == user_id,
            UsageDaily.usage_date == usage_date,
        )
    )

    if usage:
        return usage

    usage = UsageDaily(user_id=user_id, usage_date=usage_date)
    db.add(usage)
    await db.flush()
    return usage


async def check_quota_before_chat(
    db: AsyncSession,
    *,
    user: User,
    input_text: str,
    reserve_output_tokens: int = 2000,
) -> QuotaCheckResult:
    usage = await get_or_create_today_usage(db, user.id)

    projected_total_tokens = usage.input_tokens + usage.output_tokens + estimate_tokens(input_text) + reserve_output_tokens
    if projected_total_tokens > user.daily_token_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily token quota exceeded",
        )

    if usage.total_cost >= user.daily_cost_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily cost quota exceeded",
        )

    return QuotaCheckResult(
        usage=UsageSnapshot(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_cost=usage.total_cost,
        ),
        remaining_tokens=max(0, user.daily_token_limit - (usage.input_tokens + usage.output_tokens)),
        remaining_cost=max(0.0, user.daily_cost_limit - usage.total_cost),
    )


async def apply_usage(
    db: AsyncSession,
    *,
    user_id: str,
    input_tokens: int,
    output_tokens: int,
    total_cost: float,
) -> UsageDaily:
    usage = await get_or_create_today_usage(db, user_id)
    usage.input_tokens += max(0, input_tokens)
    usage.output_tokens += max(0, output_tokens)
    usage.total_cost += max(0.0, total_cost)
    await db.flush()
    return usage
