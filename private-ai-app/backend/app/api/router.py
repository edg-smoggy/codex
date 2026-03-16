from __future__ import annotations

from fastapi import APIRouter

from app.api import admin, auth, chat, conversations, health, models, usage

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(models.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(usage.router)
api_router.include_router(admin.router)
api_router.include_router(health.router)
