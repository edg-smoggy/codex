from __future__ import annotations

from datetime import date
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import UsageDaily, User, UserStatus
from app.schemas import (
    AdminUsageItem,
    AdminUserItem,
    UserBlockRequest,
    UserQuotaUpdateRequest,
)
from app.services.audit import log_action
from app.services.auth import require_admin_user
from app.services.quota import today_utc_date

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserItem])
async def admin_list_users(
    _admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserItem]:
    rows = await db.scalars(select(User).order_by(User.created_at.asc()))
    return [
        AdminUserItem(
            id=user.id,
            username=user.username,
            role=user.role,
            status=user.status,
            daily_token_limit=user.daily_token_limit,
            daily_cost_limit=user.daily_cost_limit,
            created_at=user.created_at,
        )
        for user in rows.all()
    ]


@router.get("/usage/daily", response_model=list[AdminUsageItem])
async def admin_usage_daily(
    usage_date: Optional[date] = Query(default=None),
    _admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUsageItem]:
    target_date = usage_date or today_utc_date()

    stmt = (
        select(UsageDaily, User)
        .join(User, User.id == UsageDaily.user_id)
        .where(UsageDaily.usage_date == target_date)
        .order_by(UsageDaily.total_cost.desc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        AdminUsageItem(
            user_id=user.id,
            username=user.username,
            usage_date=usage.usage_date,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
            total_cost=usage.total_cost,
        )
        for usage, user in rows
    ]


@router.post("/users/{user_id}/block")
async def admin_block_user(
    user_id: str,
    payload: UserBlockRequest,
    admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.status = UserStatus.BLOCKED if payload.blocked else UserStatus.ACTIVE
    await log_action(
        db,
        user_id=admin.id,
        action="admin.user.block",
        detail={"target_user_id": user.id, "blocked": payload.blocked},
    )
    await db.commit()

    return {"status": user.status.value}


@router.post("/users/{user_id}/quota")
async def admin_update_quota(
    user_id: str,
    payload: UserQuotaUpdateRequest,
    admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Union[float, int]]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.daily_token_limit = payload.daily_token_limit
    user.daily_cost_limit = payload.daily_cost_limit

    await log_action(
        db,
        user_id=admin.id,
        action="admin.user.quota.update",
        detail={
            "target_user_id": user.id,
            "daily_token_limit": payload.daily_token_limit,
            "daily_cost_limit": payload.daily_cost_limit,
        },
    )
    await db.commit()

    return {
        "daily_token_limit": user.daily_token_limit,
        "daily_cost_limit": user.daily_cost_limit,
    }


@router.post("/users/{user_id}/usage/reset")
async def admin_reset_usage(
    user_id: str,
    usage_date: Optional[date] = Query(default=None),
    admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target_date = usage_date or today_utc_date()
    usage = await db.scalar(
        select(UsageDaily).where(
            UsageDaily.user_id == user.id,
            UsageDaily.usage_date == target_date,
        )
    )
    if usage:
        usage.input_tokens = 0
        usage.output_tokens = 0
        usage.total_cost = 0.0

    await log_action(
        db,
        user_id=admin.id,
        action="admin.usage.reset",
        detail={"target_user_id": user.id, "usage_date": target_date.isoformat()},
    )
    await db.commit()

    return {"status": "ok"}
