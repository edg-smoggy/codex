from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import AuditLog, Conversation, Message, MessageRole, UsageDaily, User, UserStatus
from app.providers.router import list_supported_models
from app.schemas import (
    AuditLogItem,
    AdminUsageItem,
    AdminUserItem,
    DashboardResponse,
    DailyUsage7d,
    UserBlockRequest,
    UserQuotaUpdateRequest,
)
from app.services.audit import log_action
from app.services.auth import require_admin_user
from app.services.quota import today_utc_date

router = APIRouter(prefix="/admin", tags=["admin"])


def _utc_day_bounds(target_day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target_day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


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


@router.get("/dashboard", response_model=DashboardResponse)
async def admin_dashboard(
    _admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    today = today_utc_date()
    today_start, tomorrow_start = _utc_day_bounds(today)
    seven_day_start = today - timedelta(days=6)
    seven_day_start_dt, _ = _utc_day_bounds(seven_day_start)

    total_users = int((await db.scalar(select(func.count(User.id)))) or 0)
    active_users_today = int(
        (
            await db.scalar(
                select(func.count(func.distinct(UsageDaily.user_id))).where(UsageDaily.usage_date == today)
            )
        )
        or 0
    )
    total_conversations = int((await db.scalar(select(func.count(Conversation.id)))) or 0)
    total_messages_today = int(
        (
            await db.scalar(
                select(func.count(Message.id)).where(
                    Message.created_at >= today_start,
                    Message.created_at < tomorrow_start,
                )
            )
        )
        or 0
    )
    total_cost_today = float(
        (
            await db.scalar(
                select(func.coalesce(func.sum(UsageDaily.total_cost), 0.0)).where(UsageDaily.usage_date == today)
            )
        )
        or 0.0
    )
    total_tokens_today = int(
        (
            await db.scalar(
                select(func.coalesce(func.sum(UsageDaily.input_tokens + UsageDaily.output_tokens), 0)).where(
                    UsageDaily.usage_date == today
                )
            )
        )
        or 0
    )
    models_enabled = sum(1 for item in list_supported_models() if item.get("enabled"))

    usage_rows = (
        await db.scalars(
            select(UsageDaily).where(
                UsageDaily.usage_date >= seven_day_start,
                UsageDaily.usage_date <= today,
            )
        )
    ).all()
    tokens_by_day: dict[date, int] = defaultdict(int)
    cost_by_day: dict[date, float] = defaultdict(float)
    for item in usage_rows:
        tokens_by_day[item.usage_date] += item.input_tokens + item.output_tokens
        cost_by_day[item.usage_date] += item.total_cost

    request_timestamps = (
        await db.scalars(
            select(Message.created_at).where(
                Message.role == MessageRole.ASSISTANT,
                Message.created_at >= seven_day_start_dt,
                Message.created_at < tomorrow_start,
            )
        )
    ).all()
    requests_by_day: dict[date, int] = defaultdict(int)
    for created_at in request_timestamps:
        requests_by_day[created_at.date()] += 1

    daily_usage_7d = []
    for offset in range(7):
        usage_day = seven_day_start + timedelta(days=offset)
        daily_usage_7d.append(
            DailyUsage7d(
                date=usage_day,
                tokens=tokens_by_day[usage_day],
                cost=round(cost_by_day[usage_day], 6),
                requests=requests_by_day[usage_day],
            )
        )

    return DashboardResponse(
        total_users=total_users,
        active_users_today=active_users_today,
        total_conversations=total_conversations,
        total_messages_today=total_messages_today,
        total_cost_today=total_cost_today,
        total_tokens_today=total_tokens_today,
        models_enabled=models_enabled,
        daily_usage_7d=daily_usage_7d,
    )


@router.get("/logs", response_model=list[AuditLogItem])
async def admin_logs(
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _admin=Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogItem]:
    stmt = (
        select(AuditLog, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)

    rows = (await db.execute(stmt)).all()
    return [
        AuditLogItem(
            id=audit.id,
            user_id=audit.user_id,
            username=username,
            action=audit.action,
            detail=audit.detail or {},
            created_at=audit.created_at,
        )
        for audit, username in rows
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
