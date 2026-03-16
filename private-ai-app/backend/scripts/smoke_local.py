from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Ensure settings are loaded with local-safe defaults before importing app modules.
env_file = Path(os.environ.get("ENV_FILE", ".env.local"))
if env_file.exists():
    load_dotenv(env_file, override=False)

os.environ.setdefault("ENV", "local")
os.environ.setdefault("SECRET_KEY", "smoke-local-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./private_ai_smoke.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ALLOW_MOCK_PROVIDER", "true")

import httpx
from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal, init_db
from app.main import app
from app.models import Invite, User, UserRole, UserStatus


class SmokeCheckError(Exception):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeCheckError(message)


async def seed_admin_and_invite() -> tuple[str, str]:
    username = "admin"
    password = "ChangeMe123!"
    invite_code = "FRIEND-ONLY-001"

    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(User.username == username))
        if not admin:
            admin = User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                daily_token_limit=1_000_000,
                daily_cost_limit=100.0,
            )
            db.add(admin)
            await db.flush()

        invite = await db.scalar(select(Invite).where(Invite.code == invite_code))
        if not invite:
            invite = Invite(
                code=invite_code,
                created_by=admin.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                is_active=True,
            )
            db.add(invite)

        await db.commit()

    return username, password


def parse_sse_events(raw: str) -> list[str]:
    events: list[str] = []
    for block in raw.split("\n\n"):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        event = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("event:")), None)
        if event:
            events.append(event)
    return events


async def run() -> int:
    await init_db()
    admin_username, admin_password = await seed_admin_and_invite()

    checks: list[dict[str, str]] = []
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        member_username = "member_demo"
        member_password = "MemberDemo123!"

        r = await client.post(
            "/api/v1/auth/register",
            json={
                "invite_code": "FRIEND-ONLY-001",
                "username": member_username,
                "password": member_password,
            },
        )
        require(r.status_code in (200, 409), f"register failed: {r.status_code} {r.text}")
        checks.append({"name": "register", "status": "pass", "detail": str(r.status_code)})

        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"username": member_username, "password": member_password},
        )
        require(login_resp.status_code == 200, f"member login failed: {login_resp.status_code} {login_resp.text}")
        member_bundle = login_resp.json()
        member_access = member_bundle["token"]["access_token"]
        checks.append({"name": "login_member", "status": "pass", "detail": "ok"})

        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": member_bundle["token"]["refresh_token"]},
        )
        require(refresh_resp.status_code == 200, f"refresh failed: {refresh_resp.status_code} {refresh_resp.text}")
        checks.append({"name": "refresh", "status": "pass", "detail": "ok"})

        models_resp = await client.get(
            "/api/v1/models",
            headers={"Authorization": f"Bearer {member_access}"},
        )
        require(models_resp.status_code == 200, f"models failed: {models_resp.status_code} {models_resp.text}")
        models = models_resp.json()
        enabled_models = [m["model"] for m in models if m["enabled"]]
        require(bool(enabled_models), "no enabled models")
        selected_model = enabled_models[0]
        checks.append({"name": "models", "status": "pass", "detail": selected_model})

        async with client.stream(
            "POST",
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {member_access}"},
            json={
                "model": selected_model,
                "message": "hello smoke check",
            },
        ) as stream_resp:
            require(stream_resp.status_code == 200, f"chat stream failed: {stream_resp.status_code}")
            payload = (await stream_resp.aread()).decode("utf-8")

        events = parse_sse_events(payload)
        require(events[:1] == ["meta"], f"sse missing meta: {events}")
        require("done" in events, f"sse missing done: {events}")
        checks.append({"name": "chat_sse", "status": "pass", "detail": ",".join(events[:5])})

        conv_resp = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {member_access}"},
        )
        require(conv_resp.status_code == 200, f"conversations failed: {conv_resp.status_code} {conv_resp.text}")
        conversations = conv_resp.json()
        require(len(conversations) >= 1, "conversation not created")
        conversation_id = conversations[0]["id"]
        checks.append({"name": "conversations", "status": "pass", "detail": conversation_id})

        msg_resp = await client.get(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers={"Authorization": f"Bearer {member_access}"},
        )
        require(msg_resp.status_code == 200, f"messages failed: {msg_resp.status_code} {msg_resp.text}")
        require(len(msg_resp.json()) >= 2, "messages not persisted")
        checks.append({"name": "messages", "status": "pass", "detail": str(len(msg_resp.json()))})

        usage_resp = await client.get(
            "/api/v1/usage/me/daily",
            headers={"Authorization": f"Bearer {member_access}"},
        )
        require(usage_resp.status_code == 200, f"usage failed: {usage_resp.status_code} {usage_resp.text}")
        checks.append({"name": "usage", "status": "pass", "detail": str(usage_resp.json().get("total_tokens", 0))})

        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"username": admin_username, "password": admin_password},
        )
        require(admin_login.status_code == 200, f"admin login failed: {admin_login.status_code} {admin_login.text}")
        admin_access = admin_login.json()["token"]["access_token"]

        admin_users = await client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_access}"},
        )
        require(admin_users.status_code == 200, f"admin users failed: {admin_users.status_code} {admin_users.text}")
        users = admin_users.json()
        member = next((u for u in users if u["username"] == member_username), None)
        require(member is not None, "member not found in admin users")
        checks.append({"name": "admin_users", "status": "pass", "detail": str(len(users))})

        member_id = member["id"]

        quota_token_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/quota",
            headers={"Authorization": f"Bearer {admin_access}"},
            json={"daily_token_limit": 1, "daily_cost_limit": 999.0},
        )
        require(quota_token_resp.status_code == 200, f"quota update(token) failed: {quota_token_resp.status_code}")

        token_block_resp = await client.post(
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {member_access}"},
            json={"model": selected_model, "message": "quota token test"},
        )
        require(token_block_resp.status_code == 429, f"token quota expected 429 got {token_block_resp.status_code}")
        checks.append({"name": "quota_token_limit", "status": "pass", "detail": "429"})

        quota_cost_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/quota",
            headers={"Authorization": f"Bearer {admin_access}"},
            json={"daily_token_limit": 999999, "daily_cost_limit": 0.000001},
        )
        require(quota_cost_resp.status_code == 200, f"quota update(cost) failed: {quota_cost_resp.status_code}")

        cost_block_resp = await client.post(
            "/api/v1/chat/stream",
            headers={"Authorization": f"Bearer {member_access}"},
            json={"model": selected_model, "message": "quota cost test"},
        )
        require(cost_block_resp.status_code == 429, f"cost quota expected 429 got {cost_block_resp.status_code}")
        checks.append({"name": "quota_cost_limit", "status": "pass", "detail": "429"})

        reset_usage_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/usage/reset",
            headers={"Authorization": f"Bearer {admin_access}"},
        )
        require(reset_usage_resp.status_code == 200, f"usage reset failed: {reset_usage_resp.status_code}")

        quota_restore_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/quota",
            headers={"Authorization": f"Bearer {admin_access}"},
            json={"daily_token_limit": 250000, "daily_cost_limit": 20.0},
        )
        require(quota_restore_resp.status_code == 200, f"quota restore failed: {quota_restore_resp.status_code}")
        checks.append({"name": "admin_quota_and_reset", "status": "pass", "detail": "ok"})

        block_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/block",
            headers={"Authorization": f"Bearer {admin_access}"},
            json={"blocked": True},
        )
        require(block_resp.status_code == 200, f"block failed: {block_resp.status_code} {block_resp.text}")

        blocked_login = await client.post(
            "/api/v1/auth/login",
            json={"username": member_username, "password": member_password},
        )
        require(blocked_login.status_code == 403, f"blocked login expected 403 got {blocked_login.status_code}")

        unblock_resp = await client.post(
            f"/api/v1/admin/users/{member_id}/block",
            headers={"Authorization": f"Bearer {admin_access}"},
            json={"blocked": False},
        )
        require(unblock_resp.status_code == 200, f"unblock failed: {unblock_resp.status_code} {unblock_resp.text}")
        checks.append({"name": "admin_block_unblock", "status": "pass", "detail": "ok"})

    artifacts_dir = Path("./artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    report_path = artifacts_dir / f"smoke-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    report_path.write_text(json.dumps({"checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Smoke checks passed: {len(checks)}")
    print(f"Report: {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(run())
    except SmokeCheckError as exc:
        print(f"Smoke check failed: {exc}")
        raise SystemExit(1)
    raise SystemExit(exit_code)
