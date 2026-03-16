from __future__ import annotations

from typing import Any
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    user_id: Optional[str],
    action: str,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    entry = AuditLog(user_id=user_id, action=action, detail=detail or {})
    db.add(entry)
    await db.flush()
