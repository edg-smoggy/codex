from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Optional, Union

import httpx

from app.core.config import get_settings
from app.services.quota import estimate_tokens

settings = get_settings()
_CLIENT_LIMITS = httpx.Limits(max_connections=80, max_keepalive_connections=20, keepalive_expiry=60.0)
_provider_clients: dict[str, httpx.AsyncClient] = {}


def _build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.request_timeout_seconds,
        limits=_CLIENT_LIMITS,
    )


def _get_provider_client(provider: str) -> httpx.AsyncClient:
    client = _provider_clients.get(provider)
    if client is None:
        client = _build_client()
        _provider_clients[provider] = client
    return client


async def init_provider_clients() -> None:
    for provider in ("openai", "gemini", "kimi"):
        _get_provider_client(provider)


async def close_provider_clients() -> None:
    for client in _provider_clients.values():
        await client.aclose()
    _provider_clients.clear()


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


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return ""


def _kimi_thinking_overrides(thinking_mode: str) -> list[Optional[dict[str, Any]]]:
    if thinking_mode != "thinking":
        return [None]
    return [
        {"thinking": {"enabled": True}},
        {"thinking": {"type": "enabled"}},
        {"thinking": {"mode": "enabled"}},
        {"thinking": True},
    ]


def _openai_stream_delta(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    delta = first.get("delta")
    if not isinstance(delta, dict):
        return ""
    return _to_text(delta.get("content"))


def _gemini_stream_delta(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ""

    texts: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        parts = content.get("parts")
        if not isinstance(parts, list):
            continue
        for part in parts:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                texts.append(text)
    return "".join(texts)


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


async def _mock_reply_stream(
    model: str,
    message: str,
) -> AsyncIterator[Union[str, ProviderResult]]:
    content = f"[MOCK:{model}] {message[:200]}"
    provider = provider_for_model(model)
    for idx in range(0, len(content), 5):
        delta = content[idx : idx + 5]
        if delta:
            yield delta
            await asyncio.sleep(0.03)

    input_tokens = estimate_tokens(message)
    output_tokens = estimate_tokens(content)
    yield ProviderResult(
        provider=provider,
        model=model,
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost(provider, model, input_tokens, output_tokens),
        raw={"mock": True, "stream": True},
    )


async def _call_openai_style(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    provider: str,
    thinking_mode: str = "standard",
) -> ProviderResult:
    url = f"{base_url.rstrip('/')}/chat/completions"
    temperature = 0.7
    # Moonshot kimi-k2.5 only accepts temperature=1 in OpenAI-compatible mode.
    if provider == "kimi" and model.lower().startswith("kimi-k2.5"):
        temperature = 1

    base_body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    client = _get_provider_client(provider)
    last_error: Optional[httpx.HTTPStatusError] = None
    for idx, override in enumerate(_kimi_thinking_overrides(thinking_mode) if provider == "kimi" else [None]):
        body = dict(base_body)
        if override:
            body.update(override)
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code >= 400:
            status_error = httpx.HTTPStatusError(
                message=f"Provider returned status {resp.status_code}",
                request=resp.request,
                response=resp,
            )
            can_retry = (
                provider == "kimi"
                and thinking_mode == "thinking"
                and idx < len(_kimi_thinking_overrides(thinking_mode)) - 1
                and resp.status_code in {400, 422}
            )
            if can_retry:
                last_error = status_error
                continue
            raise status_error
        data = resp.json()
        break
    else:
        if last_error:
            raise last_error
        raise RuntimeError("Provider request failed")

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


async def _call_openai_style_stream(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    provider: str,
    thinking_mode: str = "standard",
) -> AsyncIterator[Union[str, ProviderResult]]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    temperature = 0.7
    # Moonshot kimi-k2.5 only accepts temperature=1 in OpenAI-compatible mode.
    if provider == "kimi" and model.lower().startswith("kimi-k2.5"):
        temperature = 1

    base_body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    # OpenAI can emit usage in stream end chunks.
    if provider == "openai":
        base_body["stream_options"] = {"include_usage": True}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    content_parts: list[str] = []
    usage_data: dict[str, Any] = {}
    client = _get_provider_client(provider)
    thinking_overrides = _kimi_thinking_overrides(thinking_mode) if provider == "kimi" else [None]
    last_error: Optional[httpx.HTTPStatusError] = None
    for idx, override in enumerate(thinking_overrides):
        body = dict(base_body)
        if override:
            body.update(override)

        async with client.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                status_error = httpx.HTTPStatusError(
                    message=f"Provider returned status {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
                can_retry = (
                    provider == "kimi"
                    and thinking_mode == "thinking"
                    and idx < len(thinking_overrides) - 1
                    and resp.status_code in {400, 422}
                )
                if can_retry:
                    last_error = status_error
                    continue
                raise status_error

            async for line in resp.aiter_lines():
                if not line:
                    continue
                if not line.startswith("data:"):
                    continue
                data_raw = line[len("data:") :].strip()
                if not data_raw:
                    continue
                if data_raw == "[DONE]":
                    break

                try:
                    payload = json.loads(data_raw)
                except json.JSONDecodeError:
                    continue

                if not isinstance(payload, dict):
                    continue

                usage_candidate = payload.get("usage")
                if isinstance(usage_candidate, dict):
                    usage_data = usage_candidate

                delta = _openai_stream_delta(payload)
                if delta:
                    content_parts.append(delta)
                    yield delta
            break
    else:
        if last_error:
            raise last_error
        raise RuntimeError("Provider request failed")

    if not content_parts and not usage_data and provider == "kimi" and thinking_mode == "thinking":
        # Defensive check for empty retry output.
        raise RuntimeError("Kimi thinking mode returned empty stream")

    full_content = "".join(content_parts)
    input_tokens = int(usage_data.get("prompt_tokens") or estimate_tokens(str(messages)))
    output_tokens = int(usage_data.get("completion_tokens") or estimate_tokens(full_content))

    yield ProviderResult(
        provider=provider,
        model=model,
        content=full_content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost(provider, model, input_tokens, output_tokens),
        raw={"stream": True, "usage": usage_data},
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

    client = _get_provider_client("gemini")
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


async def _call_gemini_stream(
    *,
    model: str,
    api_key: str,
    messages: list[dict[str, str]],
) -> AsyncIterator[Union[str, ProviderResult]]:
    url = f"{settings.gemini_base_url.rstrip('/')}/models/{model}:streamGenerateContent"
    params = {"key": api_key, "alt": "sse"}

    contents = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body = {"contents": contents}

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    content_parts: list[str] = []
    usage_meta: dict[str, Any] = {}
    client = _get_provider_client("gemini")
    async with client.stream("POST", url, params=params, headers=headers, json=body) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line:
                continue
            if not line.startswith("data:"):
                continue
            data_raw = line[len("data:") :].strip()
            if not data_raw:
                continue

            try:
                payload = json.loads(data_raw)
            except json.JSONDecodeError:
                continue

            if not isinstance(payload, dict):
                continue

            usage_candidate = payload.get("usageMetadata")
            if isinstance(usage_candidate, dict):
                usage_meta = usage_candidate

            delta = _gemini_stream_delta(payload)
            if delta:
                content_parts.append(delta)
                yield delta

    full_content = "".join(content_parts)
    input_tokens = int(usage_meta.get("promptTokenCount") or estimate_tokens(str(messages)))
    output_tokens = int(usage_meta.get("candidatesTokenCount") or estimate_tokens(full_content))

    yield ProviderResult(
        provider="gemini",
        model=model,
        content=full_content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=_estimate_cost("gemini", model, input_tokens, output_tokens),
        raw={"stream": True, "usage_metadata": usage_meta},
    )


async def generate_reply_stream(
    model: str,
    messages: list[dict[str, str]],
    thinking_mode: str = "standard",
) -> AsyncIterator[Union[str, ProviderResult]]:
    provider = provider_for_model(model)
    latest_user_text = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    if provider == "openai":
        if not settings.openai_api_key:
            if settings.allow_mock_provider:
                async for chunk in _mock_reply_stream(model, latest_user_text):
                    yield chunk
                return
            raise RuntimeError("OPENAI_API_KEY is missing")
        async for chunk in _call_openai_style_stream(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            model=model,
            messages=messages,
            provider="openai",
            thinking_mode=thinking_mode,
        ):
            yield chunk
        return

    if provider == "kimi":
        if not settings.kimi_api_key:
            if settings.allow_mock_provider:
                async for chunk in _mock_reply_stream(model, latest_user_text):
                    yield chunk
                return
            raise RuntimeError("KIMI_API_KEY is missing")
        async for chunk in _call_openai_style_stream(
            base_url=settings.kimi_base_url,
            api_key=settings.kimi_api_key,
            model=model,
            messages=messages,
            provider="kimi",
            thinking_mode=thinking_mode,
        ):
            yield chunk
        return

    if provider == "gemini":
        if not settings.gemini_api_key:
            if settings.allow_mock_provider:
                async for chunk in _mock_reply_stream(model, latest_user_text):
                    yield chunk
                return
            raise RuntimeError("GEMINI_API_KEY is missing")
        async for chunk in _call_gemini_stream(model=model, api_key=settings.gemini_api_key, messages=messages):
            yield chunk
        return

    raise RuntimeError("Provider not implemented")


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
            thinking_mode="standard",
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
            thinking_mode="standard",
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            if settings.allow_mock_provider:
                return await _mock_reply(model, latest_user_text)
            raise RuntimeError("GEMINI_API_KEY is missing")
        return await _call_gemini(model=model, api_key=settings.gemini_api_key, messages=messages)

    raise RuntimeError("Provider not implemented")
