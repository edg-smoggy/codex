from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import AuthBundle, LoginRequest, RefreshTokenRequest, RegisterRequest, UserInfo
from app.services.auth import login_user, refresh_user_token, register_user, require_active_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthBundle)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthBundle:
    user = await register_user(payload, db)
    _, token = await login_user(LoginRequest(username=payload.username, password=payload.password), db)
    return AuthBundle(user=user, token=token)


@router.post("/login", response_model=AuthBundle)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthBundle:
    user, token = await login_user(payload, db)
    return AuthBundle(user=user, token=token)


@router.post("/refresh", response_model=AuthBundle)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> AuthBundle:
    user, token = await refresh_user_token(payload.refresh_token, db)
    return AuthBundle(user=user, token=token)


@router.get("/me", response_model=UserInfo)
async def me(user=Depends(require_active_user)) -> UserInfo:
    return UserInfo.model_validate(user)
