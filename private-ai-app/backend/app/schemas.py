from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import MessageRole, UserRole, UserStatus


class RegisterRequest(BaseModel):
    invite_code: str = Field(min_length=4, max_length=64)
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: UserRole
    status: UserStatus
    daily_token_limit: int
    daily_cost_limit: float


class AuthBundle(BaseModel):
    user: UserInfo
    token: TokenResponse


class ModelInfo(BaseModel):
    model: str
    provider: str
    enabled: bool


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    model: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    created_at: datetime


class ChatStreamRequest(BaseModel):
    conversation_id: Optional[str] = None
    model: str = Field(min_length=2, max_length=120)
    message: Optional[str] = Field(default=None, max_length=20000)
    thinking_mode: Literal["standard", "thinking"] = "standard"
    regenerate_assistant_id: Optional[str] = None


class UsageMeResponse(BaseModel):
    usage_date: date
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float
    daily_token_limit: int
    daily_cost_limit: float


class AdminUsageItem(BaseModel):
    user_id: str
    username: str
    usage_date: date
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_cost: float


class DailyUsage7d(BaseModel):
    date: date
    tokens: int
    cost: float
    requests: int


class DashboardResponse(BaseModel):
    total_users: int
    active_users_today: int
    total_conversations: int
    total_messages_today: int
    total_cost_today: float
    total_tokens_today: int
    models_enabled: int
    daily_usage_7d: list[DailyUsage7d]


class AdminUserItem(BaseModel):
    id: str
    username: str
    role: UserRole
    status: UserStatus
    daily_token_limit: int
    daily_cost_limit: float
    created_at: datetime


class UserBlockRequest(BaseModel):
    blocked: bool


class UserQuotaUpdateRequest(BaseModel):
    daily_token_limit: int = Field(gt=0)
    daily_cost_limit: float = Field(gt=0)


class AuditLogItem(BaseModel):
    id: str
    user_id: Optional[str]
    username: Optional[str]
    action: str
    detail: dict[str, Any]
    created_at: datetime


class HealthResponse(BaseModel):
    api: str
    db: str
    redis: str
