"""Anthropic-compatible HTTP proxy views for OpenRouter Bridge."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator

import aiohttp
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, OPENROUTER_BASE_URL, DEFAULT_MODEL, STATS_KEY

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=300, connect=15)

OPENROUTER_HEADERS_BASE = {
    "HTTP-Referer": "https://homeassistant.local",
    "X-Title": "HA OpenRouter Bridge",
    "Content-Type": "application/json",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_entry_data(hass: HomeAssistant) -> dict | None:
    """Return config data for the first (and typically only) config entry."""
    domain_data = hass.data.get(DOMAIN, {})
    for val in domain_data.values():
        if isinstance(val, dict) and "api_key" in val:
            return val
    return None


def _extract_api_key(request: web.Request, fallback_key: str) -> str:
    """Extract OpenRouter API key from Authorization header or fall back."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        key = auth[7:].strip()
        # Ignore obvious placeholder keys from Claude Code
        if key and not key.startswith("sk-ant-api03-placeholder"):
            return key
    return fallback_key


def _update_stats(hass: HomeAssistant, model: str) -> None:
    """Increment request counters."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    stats = domain_data.setdefault(STATS_KEY, {
        "total_requests": 0,
        "last_model": "",
        "requests_by_model": {},
    })
    stats["total_requests"] += 1
    stats["last_model"] = model
    stats["requests_by_model"][model] = stats["requests_by_model"].get(model, 0) + 1


# ---------------------------------------------------------------------------
# Request translation: Anthropic → OpenAI
# ---------------------------------------------------------------------------

def _translate_content_to_openai(content: str | list) -> tuple[str | None, list]:
    """Convert Anthropic content to (text, tool_calls).

    Returns:
        (text_or_none, tool_calls_list)
    """
    if isinstance(content, str):
        return content, []

    if not isinstance(content, list):
        return str(content), []

    text_parts: list[str] = []
    tool_calls: list[dict] = []

    for block in content:
        btype = block.get("type", "")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            tool_calls.append({
                "id": block["id"],
                "type": "function",
                "function": {
                    "name": block["name"],
                    "arguments": json.dumps(block.get("input", {})),
                },
            })

    return ("\n".join(text_parts) or None), tool_calls


def _translate_messages(messages: list, system: str | list | None) -> list:
    """Translate Anthropic messages array to OpenAI format."""
    result: list[dict] = []

    # System prompt → first message
    if system:
        if isinstance(system, str):
            result.append({"role": "system", "content": system})
        elif isinstance(system, list):
            text = "\n".join([b.get("text", "") for b in system if b.get("type") == "text"])
            if text:
                result.append({"role": "system", "content": text})

    for msg in messages:
        role: str = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        if not isinstance(content, list):
            result.append({"role": role, "content": str(content)})
            continue

        # Detect content block types
        tool_results = [b for b in content if b.get("type") == "tool_result"]

        if tool_results:
            # Each tool_result → separate "tool" role message
            for tr in tool_results:
                tr_content = tr.get("content", "")
                if isinstance(tr_content, list):
                    tr_content = "\n".join(
                        [b.get("text", "") for b in tr_content if b.get("type") == "text"]
                    )
                result.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_use_id"],
                    "content": tr_content or "",
                })
        else:
            # Normal assistant/user message, possibly with tool_use blocks
            text, tool_calls = _translate_content_to_openai(content)
            oai_msg: dict[str, Any] = {"role": role, "content": text}
            if tool_calls:
                oai_msg["tool_calls"] = tool_calls
            result.append(oai_msg)

    return result


def _translate_tools(tools: list) -> list:
    """Convert Anthropic tools to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in tools
    ]


def _translate_tool_choice(tc: Any) -> Any:
    """Convert Anthropic tool_choice to OpenAI format."""
    if not tc:
        return None
    if isinstance(tc, str):
        return tc
    tc_type = tc.get("type", "auto")
    if tc_type == "auto":
        return "auto"
    if tc_type == "any":
        return "required"
    if tc_type == "tool":
        return {"type": "function", "function": {"name": tc.get("name", "")}}
    return "none"


def build_openai_request(
    anthropic_data: dict, model: str, allow_override: bool, hass: HomeAssistant | None = None
) -> dict:
    """Build complete OpenAI request dict from Anthropic request dict."""
    effective_model = model

    # Dashboard-modellväljare har högst prioritet
    if hass is not None:
        dashboard_model = hass.states.get("input_select.openrouter_bridge_model")
        if dashboard_model and dashboard_model.state not in ("unknown", "unavailable", ""):
            effective_model = dashboard_model.state

    if allow_override and "model" in anthropic_data:
        effective_model = anthropic_data["model"]

    oai: dict[str, Any] = {
        "model": effective_model,
        "messages": _translate_messages(
            anthropic_data.get("messages", []),
            anthropic_data.get("system"),
        ),
        "max_tokens": anthropic_data.get("max_tokens", 4096),
        "stream": anthropic_data.get("stream", False),
    }

    for passthrough in ("temperature", "top_p"):
        if passthrough in anthropic_data:
            oai[passthrough] = anthropic_data[passthrough]

    if "stop_sequences" in anthropic_data:
        oai["stop"] = anthropic_data["stop_sequences"]

    if "tools" in anthropic_data:
        oai["tools"] = _translate_tools(anthropic_data["tools"])

    if "tool_choice" in anthropic_data:
        tc = _translate_tool_choice(anthropic_data["tool_choice"])
        if tc is not None:
            oai["tool_choice"] = tc

    return oai


# ---------------------------------------------------------------------------
# Response translation: OpenAI → Anthropic
# ---------------------------------------------------------------------------

def build_anthropic_response(oai_response: dict, model: str) -> dict:
    """Build Anthropic response dict from OpenAI response dict."""
    choices = oai_response.get("choices") or [{}]
    choice = choices[0]
    message = choice.get("message", {})
    finish_reason = choice.get("finish_reason", "stop")

    content: list[dict] = []

    msg_text = message.get("content")
    if msg_text:
        content.append({"type": "text", "text": msg_text})

    for tc in message.get("tool_calls") or []:
        func = tc.get("function", {})
        try:
            input_data = json.loads(func.get("arguments", "{}"))
        except (json.JSONDecodeError, TypeError):
            input_data = {}
        content.append({
            "type": "tool_use",
            "id": tc.get("id", f"toolu_{uuid.uuid4().hex[:12]}"),
            "name": func.get("name", ""),
            "input": input_data,
        })

    stop_reason_map = {
        "stop": "end_turn",
        "tool_calls": "tool_use",
        "length": "max_tokens",
        "content_filter": "stop_sequence",
    }
    stop_reason = stop_reason_map.get(finish_reason, "end_turn")

    oai_usage = oai_response.get("usage", {})

    return {
        "id": oai_response.get("id", f"msg_{uuid.uuid4().hex}"),
        "type": "message",
        "role": "assistant",
        "content": content,
        "model": model,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {
            "input_tokens": oai_usage.get("prompt_tokens", 0),
            "output_tokens": oai_usage.get("completion_tokens", 0),
        },
    }


# ---------------------------------------------------------------------------
# Streaming translation: OpenAI SSE → Anthropic SSE
# ---------------------------------------------------------------------------

async def _stream_translate(
    upstream: aiohttp.ClientResponse, model: str
) -> AsyncGenerator[bytes, None]:
    """Translate OpenAI Server-Sent Events to Anthropic SSE format."""
    msg_id = f"msg_{uuid.uuid4().hex}"

    def _evt(event: str, data: dict) -> bytes:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode()

    # ── Message start ──────────────────────────────────────────────────────
    yield _evt("message_start", {
        "type": "message_start",
        "message": {
            "id": msg_id, "type": "message", "role": "assistant",
            "content": [], "model": model,
            "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 0, "output_tokens": 1},
        },
    })
    yield _evt("ping", {"type": "ping"})

    # Track open content blocks
    text_idx: int | None = None
    text_open = False
    tool_blocks: dict[int, tuple[str, int]] = {}  # oai_index → (tc_id, block_idx)
    next_idx = 0
    stop_reason = "end_turn"
    output_tokens = 0

    async for raw in upstream.content:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break

        try:
            chunk = json.loads(data_str)
        except json.JSONDecodeError:
            continue

        # Usage info (some providers send at end)
        if "usage" in chunk:
            output_tokens = chunk["usage"].get("completion_tokens", output_tokens)

        choices = chunk.get("choices") or []
        if not choices:
            continue

        choice = choices[0]
        delta = choice.get("delta", {})
        finish_reason = choice.get("finish_reason")

        # ── Text delta ─────────────────────────────────────────────────────
        text_chunk = delta.get("content") or ""
        if text_chunk:
            if text_idx is None:
                text_idx = next_idx
                next_idx += 1
                yield _evt("content_block_start", {
                    "type": "content_block_start",
                    "index": text_idx,
                    "content_block": {"type": "text", "text": ""},
                })
                text_open = True
            yield _evt("content_block_delta", {
                "type": "content_block_delta",
                "index": text_idx,
                "delta": {"type": "text_delta", "text": text_chunk},
            })

        # ── Tool call deltas ───────────────────────────────────────────────
        for tc in delta.get("tool_calls") or []:
            oai_idx: int = tc.get("index", 0)

            if oai_idx not in tool_blocks:
                # Close text block before starting tool block
                if text_open and text_idx is not None:
                    yield _evt("content_block_stop", {
                        "type": "content_block_stop", "index": text_idx,
                    })
                    text_open = False

                tc_id = tc.get("id") or f"toolu_{uuid.uuid4().hex[:12]}"
                tc_name = (tc.get("function") or {}).get("name", "")
                block_idx = next_idx
                next_idx += 1
                tool_blocks[oai_idx] = (tc_id, block_idx)

                yield _evt("content_block_start", {
                    "type": "content_block_start",
                    "index": block_idx,
                    "content_block": {
                        "type": "tool_use",
                        "id": tc_id,
                        "name": tc_name,
                        "input": {},
                    },
                })

            args_delta = (tc.get("function") or {}).get("arguments", "")
            if args_delta:
                _, block_idx = tool_blocks[oai_idx]
                yield _evt("content_block_delta", {
                    "type": "content_block_delta",
                    "index": block_idx,
                    "delta": {"type": "input_json_delta", "partial_json": args_delta},
                })

        # ── Finish reason ──────────────────────────────────────────────────
        if finish_reason:
            stop_reason_map = {
                "stop": "end_turn",
                "tool_calls": "tool_use",
                "length": "max_tokens",
            }
            stop_reason = stop_reason_map.get(finish_reason, "end_turn")

    # ── Close open blocks ──────────────────────────────────────────────────
    if text_open and text_idx is not None:
        yield _evt("content_block_stop", {"type": "content_block_stop", "index": text_idx})

    for _, (_, block_idx) in sorted(tool_blocks.items(), key=lambda x: x[1][1]):
        yield _evt("content_block_stop", {"type": "content_block_stop", "index": block_idx})

    yield _evt("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": stop_reason, "stop_sequence": None},
        "usage": {"output_tokens": output_tokens},
    })
    yield _evt("message_stop", {"type": "message_stop"})


# ---------------------------------------------------------------------------
# HTTP Views
# ---------------------------------------------------------------------------

class OpenRouterMessagesView(HomeAssistantView):
    """POST /api/openrouter_bridge/v1/messages — main proxy endpoint."""

    url = "/api/openrouter_bridge/v1/messages"
    name = "api:openrouter_bridge:messages"
    requires_auth = True
    cors_allowed = True

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        self.hass = hass

    async def post(self, request: web.Request) -> web.StreamResponse | web.Response:
        """Handle POST request from Claude Code (Anthropic format)."""
        try:
            data: dict = await request.json()
        except Exception:
            return web.Response(
                status=400,
                content_type="application/json",
                text='{"type":"error","error":{"type":"invalid_request_error","message":"Invalid JSON"}}',
            )

        entry_data = _get_entry_data(self.hass)
        if not entry_data:
            return web.Response(
                status=503,
                content_type="application/json",
                text='{"type":"error","error":{"type":"api_error","message":"OpenRouter Bridge not configured"}}',
            )

        api_key = _extract_api_key(request, entry_data.get("api_key", ""))
        if not api_key:
            return web.Response(
                status=401,
                content_type="application/json",
                text='{"type":"error","error":{"type":"authentication_error","message":"No API key. Set ANTHROPIC_API_KEY to your OpenRouter key."}}',
            )

        model = entry_data.get("default_model", DEFAULT_MODEL)
        allow_override = entry_data.get("allow_model_override", False)

        oai_request = build_openai_request(data, model, allow_override, self.hass)
        effective_model: str = oai_request["model"]
        is_stream: bool = oai_request.get("stream", False)

        _update_stats(self.hass, effective_model)

        headers = {
            **OPENROUTER_HEADERS_BASE,
            "Authorization": f"Bearer {api_key}",
        }

        session = async_get_clientsession(self.hass)

        try:
            if is_stream:
                stream_resp = web.StreamResponse(headers={
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                })
                await stream_resp.prepare(request)

                async with session.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    json=oai_request,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                ) as upstream:
                    if upstream.status != 200:
                        err = await upstream.text()
                        _LOGGER.warning("OpenRouter error %s for model %s: %s", upstream.status, effective_model, err[:300])
                        # Map HTTP status to Anthropic error types so Claude Code shows the real reason
                        if upstream.status == 404:
                            err_type = "not_found_error"
                        elif upstream.status in (401, 403):
                            err_type = "authentication_error"
                        elif upstream.status == 402:
                            err_type = "permission_error"
                        elif upstream.status == 429:
                            err_type = "rate_limit_error"
                        else:
                            err_type = "api_error"
                        # Try to extract a readable message from OpenRouter's JSON error
                        try:
                            err_json = json.loads(err)
                            readable = (err_json.get("error", {}).get("message")
                                        or err_json.get("message")
                                        or err[:300])
                        except Exception:
                            readable = err[:300]
                        error_evt = (
                            f"event: error\ndata: {json.dumps({'type':'error','error':{'type':err_type,'message':f'[OpenRouter {upstream.status}] {readable}'}})}\n\n"
                        )
                        await stream_resp.write(error_evt.encode())
                    else:
                        async for chunk in _stream_translate(upstream, effective_model):
                            await stream_resp.write(chunk)

                await stream_resp.write_eof()
                return stream_resp

            else:
                async with session.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    json=oai_request,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                ) as upstream:
                    if upstream.status != 200:
                        err = await upstream.text()
                        _LOGGER.warning("OpenRouter error %s for model %s: %s", upstream.status, effective_model, err[:300])
                        if upstream.status == 404:
                            err_type = "not_found_error"
                        elif upstream.status in (401, 403):
                            err_type = "authentication_error"
                        elif upstream.status == 402:
                            err_type = "permission_error"
                        elif upstream.status == 429:
                            err_type = "rate_limit_error"
                        else:
                            err_type = "api_error"
                        try:
                            err_json = json.loads(err)
                            readable = (err_json.get("error", {}).get("message")
                                        or err_json.get("message")
                                        or err[:300])
                        except Exception:
                            readable = err[:300]
                        return web.Response(
                            status=upstream.status,
                            content_type="application/json",
                            text=json.dumps({
                                "type": "error",
                                "error": {"type": err_type, "message": f"[OpenRouter {upstream.status}] {readable}"},
                            }),
                        )
                    oai_response = await upstream.json()

                anthropic_response = build_anthropic_response(oai_response, effective_model)
                return web.json_response(anthropic_response)

        except aiohttp.ClientConnectorError as exc:
            _LOGGER.error("Cannot connect to OpenRouter: %s", exc)
            return web.Response(
                status=502,
                content_type="application/json",
                text=json.dumps({"type": "error", "error": {"type": "api_error", "message": "Cannot connect to OpenRouter"}}),
            )
        except aiohttp.ClientError as exc:
            _LOGGER.error("OpenRouter request failed: %s", exc)
            return web.Response(
                status=502,
                content_type="application/json",
                text=json.dumps({"type": "error", "error": {"type": "api_error", "message": str(exc)}}),
            )


class OpenRouterModelsView(HomeAssistantView):
    """GET /api/openrouter_bridge/v1/models — model list in Anthropic format."""

    url = "/api/openrouter_bridge/v1/models"
    name = "api:openrouter_bridge:models"
    requires_auth = True
    cors_allowed = True

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return available OpenRouter models in Anthropic-compatible format."""
        entry_data = _get_entry_data(self.hass)
        if not entry_data:
            return web.json_response({"data": []})

        api_key = _extract_api_key(request, entry_data.get("api_key", ""))
        if not api_key:
            return web.json_response({"data": []})

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}", **OPENROUTER_HEADERS_BASE},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    return web.json_response({"data": []})
                raw = await resp.json()
        except aiohttp.ClientError:
            return web.json_response({"data": []})

        # Translate to Anthropic model list format
        anthropic_models = [
            {
                "type": "model",
                "id": m.get("id", ""),
                "display_name": m.get("name", m.get("id", "")),
                "created_at": None,
            }
            for m in (raw.get("data") or [])
            if m.get("id")
        ]

        return web.json_response({"data": anthropic_models})


class OpenRouterHealthView(HomeAssistantView):
    """GET /api/openrouter_bridge — health check / info endpoint."""

    url = "/api/openrouter_bridge"
    name = "api:openrouter_bridge:health"
    requires_auth = True
    cors_allowed = True

    def __init__(self, hass: HomeAssistant) -> None:  # noqa: D107
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return integration status."""
        entry_data = _get_entry_data(self.hass)
        configured = entry_data is not None
        model = (entry_data or {}).get("default_model", DEFAULT_MODEL)
        stats = self.hass.data.get(DOMAIN, {}).get(STATS_KEY, {})

        return web.json_response({
            "status": "ok" if configured else "unconfigured",
            "default_model": model,
            "total_requests": stats.get("total_requests", 0),
            "last_model": stats.get("last_model", ""),
            "endpoints": {
                "messages": "/api/openrouter_bridge/v1/messages",
                "models": "/api/openrouter_bridge/v1/models",
            },
            "claude_code_env": {
                "ANTHROPIC_BASE_URL": "http://<ha-ip>:8123/api/openrouter_bridge",
                "ANTHROPIC_API_KEY": "<your-openrouter-api-key>",
            },
        })
