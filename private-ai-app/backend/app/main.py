from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db import init_db
from app.providers.router import close_provider_clients, init_provider_clients

# Ensure models are registered before metadata create_all.
from app import models as _models  # noqa: F401

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    await init_provider_clients()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_provider_clients()


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ok"}


app.include_router(api_router, prefix=settings.api_prefix)
