from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.models import Invite, User, UserRole, UserStatus


async def run(args: argparse.Namespace) -> None:
    await init_db()
    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(User.username == args.admin_username))
        if not admin:
            admin = User(
                username=args.admin_username,
                password_hash=hash_password(args.admin_password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                daily_token_limit=args.daily_token_limit,
                daily_cost_limit=args.daily_cost_limit,
            )
            db.add(admin)
            await db.flush()
            print(f"Created admin user: {admin.username}")
        else:
            print(f"Admin already exists: {admin.username}")

        invite = await db.scalar(select(Invite).where(Invite.code == args.invite_code))
        if not invite:
            expires_at = datetime.now(timezone.utc) + timedelta(days=args.invite_expiry_days)
            invite = Invite(
                code=args.invite_code,
                created_by=admin.id,
                expires_at=expires_at,
                is_active=True,
            )
            db.add(invite)
            await db.flush()
            print(f"Created invite code: {invite.code} (expires {expires_at.isoformat()})")
        else:
            print(f"Invite already exists: {invite.code}")

        await db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap admin account and invite code")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", default="ChangeMe123!")
    parser.add_argument("--invite-code", default="FRIEND-ONLY-001")
    parser.add_argument("--invite-expiry-days", type=int, default=365)
    parser.add_argument("--daily-token-limit", type=int, default=1_000_000)
    parser.add_argument("--daily-cost-limit", type=float, default=100.0)
    cli_args = parser.parse_args()

    asyncio.run(run(cli_args))
