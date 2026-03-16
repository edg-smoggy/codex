from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select


async def run(args: argparse.Namespace) -> int:
    env_file = Path(args.env_file)
    if env_file.exists():
        load_dotenv(env_file, override=False)

    # Import after loading env so settings are resolved from the expected local file.
    from app.db import SessionLocal, init_db
    from app.models import User, UserRole

    await init_db()

    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == args.username))
        if not user:
            print(f"User not found: {args.username}")
            return 1

        target_role = UserRole.MEMBER if args.demote else UserRole.ADMIN
        if user.role == target_role:
            print(f"No change needed: {user.username} already {target_role.value}")
            return 0

        old_role = user.role
        user.role = target_role
        await db.commit()
        await db.refresh(user)
        print(f"Updated role: {user.username} {old_role.value} -> {user.role.value}")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote or demote a user role")
    parser.add_argument("--username", required=True, help="Target username")
    parser.add_argument("--demote", action="store_true", help="Set role to member instead of admin")
    parser.add_argument("--env-file", default=".env.local", help="Env file path (default: .env.local)")
    cli_args = parser.parse_args()

    raise SystemExit(asyncio.run(run(cli_args)))
