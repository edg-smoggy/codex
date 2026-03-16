from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.quota import estimate_tokens

settings = get_settings()


@dataclass
class ProviderResult:
    provider: str
    model: str
    content: str
    input_tokens: int
    output_tokens: int
    cost: float
    raw: dict[str, Any]


def _estimate_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    # USD per 1K token (rough defaults, can be tuned in env-managed config later).
    rates = {
        "openai": {
            "default": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "gpt-4.1-mini": (0.0004, 0.0016),
        },
        "gemini": {
            "default": (0.00035, 0.00105),
            "gemini-2.0-flash": (0.0003, 0.001),
            "gemini-1.5-pro": (0.00125, 0.005),
        },
        "kimi": {
            "default": (0.0002, 0.001),
            # Placeholder rate; align with default until official kimi-k2.5 pricing is finalized.
            "kimi-k2.5": (0.0002, 0.001),
            "moonshot-v1-8k": (0.00015, 0.0008),
            "moonshot-v1-32k": (0.0003, 0.0015),
        },
    }

    provider_rates = rates.get(provider, {})
    in_rate, out_rate = provider_rates.get(model, provider_rates.get("default", (0.001, 0.002)))
    return round(((input_tokens / 1000) * in_rate) + ((output_tokens / 1000) * out_rate), 6)


def provider_for_model(model: str) -> str:
    lower = model.lower()
    # Resolve by configured model lists first so aliases like "kimi-k2.5" map correctly.
    for configured_model in settings.openai_models:
        if configured_model == model or configured_model.lower() == lower:
            return "openai"
    for configured_model in settings.gemini_models:
        if configured_model == model or configured_model.lower() == lower:
            return "gemini"
    for configured_model in settings.kimi_models:
        if configured_model == model or configured_model.lower() == lower:
            return "kimi"

    if lower.startswith("gpt") or lower.startswith("o"):
        return "openai"
    if "gemini" in lower:
        return "gemini"
    if "moonshot" in lower or "kimi" in lower:
        return "kimi"
    raise ValueError(f"Unsupported model: {model}")


def list_supported_models() -> list[dict[str, Any]]:
    return [
        *[
            {
                "model": model,
                "provider": "openai",
                "enabled": bool(settings.openai_api_key) or settings.allow_mock_provider,
            }
            for model in settings.openai_models
        ],
        *[
            {
                "model": model,
                "provider": "gemini",
                "enabled": bool(settings.gemini_api_key) or settings.allow_mock_provider,
            }
            for model in settings.gemini_models
        ],
        *[
            {
                "model": model,
                "provider": "kimi",
                "enabled": bool(settings.kimi_api_key) or settings.allow_mock_provider,
            }
            for model in settings.kimi_models
        ],
    ]


async def _mock_reply(model: str, message: str) -> ProviderResult:
    content = f"[MOCK:{model}] {message[:200]}"
    input_tokens = estimate_tokens(message)
    output_tokens = estimate_tokens(content)
    provider = provider_for_model(model)
    return ProviderResult(
        provider=provider,
        model=model,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost(provider, model, input_tokens, output_tokens),
        raw={"mock": True},
    )


async def _call_openai_style(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    provider: str,
) -> ProviderResult:
    url = f"{base_url.rstrip('/')}/chat/completions"
    temperature = 0.7
    # Moonshot kimi-k2.5 only accepts temperature=1 in OpenAI-compatible mode.
    if provider == "kimi" and model.lower().startswith("kimi-k2.5"):
        temperature = 1

    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        resp = await client.post(url, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()

    message = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )

    usage = data.get("usage", {})
    input_tokens = int(usage.get("prompt_tokens") or estimate_tokens(str(messages)))
    output_tokens = int(usage.get("completion_tokens") or estimate_tokens(message))

    return ProviderResult(
        provider=provider,
        model=model,
        content=message,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost(provider, model, input_tokens, output_tokens),
        raw=data,
    )


async def _call_gemini(
    *,
    model: str,
    api_key: str,
    messages: list[dict[str, str]],
) -> ProviderResult:
    url = f"{settings.gemini_base_url.rstrip('/')}/models/{model}:generateContent"
    params = {"key": api_key}

    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    body = {"contents": contents}

    async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
        resp = await client.post(url, params=params, json=body)
        resp.raise_for_status()
        data = resp.json()

    parts = (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [])
    )
    content = "\n".join(part.get("text", "") for part in parts).strip()

    input_tokens = estimate_tokens(str(messages))
    output_tokens = estimate_tokens(content)

    return ProviderResult(
        provider="gemini",
        model=model,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost("gemini", model, input_tokens, output_tokens),
        raw=data,
    )


async def generate_reply(model: str, messages: list[dict[str, str]]) -> ProviderResult:
    provider = provider_for_model(model)
    latest_user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    if provider == "openai":
        if not settings.openai_api_key:
            if settings.allow_mock_provider:
                return await _mock_reply(model, latest_user_text)
            raise RuntimeError("OPENAI_API_KEY is missing")
        return await _call_openai_style(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=model,
            messages=messages,
            provider="openai",
        )

    if provider == "kimi":
        if not settings.kimi_api_key:
            if settings.allow_mock_provider:
                return await _mock_reply(model, latest_user_text)
            raise RuntimeError("KIMI_API_KEY is missing")
        return await _call_openai_style(
            base_url=settings.kimi_base_url,
            api_key=settings.kimi_api_key,
            model=model,
            messages=messages,
            provider="kimi",
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            if settings.allow_mock_provider:
                return await _mock_reply(model, latest_user_text)
            raise RuntimeError("GEMINI_API_KEY is missing")
        return await _call_gemini(model=model, api_key=settings.gemini_api_key, messages=messages)

    raise RuntimeError("Provider not implemented")
