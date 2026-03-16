from __future__ import annotations

from fastapi import APIRouter, Depends

from app.providers.router import list_supported_models
from app.schemas import ModelInfo
from app.services.auth import require_active_user

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelInfo])
async def get_models(_: object = Depends(require_active_user)) -> list[ModelInfo]:
    return [ModelInfo(**item) for item in list_supported_models()]
