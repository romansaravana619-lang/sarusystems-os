"""OpenAI-compatible chat-completions provider adapter.

Credentials are read only from server environment settings and are never returned by APIs.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


class AIProviderUnavailable(RuntimeError):
    """Raised when provider configuration is absent or the provider cannot be reached."""


def provider_is_configured() -> bool:
    return bool(
        settings.ai_provider_base_url.strip()
        and settings.ai_provider_api_key.strip()
        and settings.ai_provider_model.strip()
    )


def generate_assistant_action(message: str, tools: list[dict]) -> dict:
    """Ask an OpenAI-compatible provider for one structured, registered tool action."""
    if not provider_is_configured():
        raise AIProviderUnavailable("AI provider is not configured.")
    url = settings.ai_provider_base_url.strip().rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    payload = {
        "model": settings.ai_provider_model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the Saru Systems Founder Assistant. Select exactly one tool from "
                    "the supplied registered tools. Return JSON only with keys tool_name, input, "
                    "and summary. Never invent IDs or values. If required details are missing, "
                    "return tool_name='clarify', input={}, and ask one concise question in summary. "
                    "For write tools, the application will only create a confirmation preview; "
                    "never claim a write has already happened."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"request": message, "registered_tools": tools},
                    ensure_ascii=False,
                ),
            },
        ],
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.ai_provider_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.ai_provider_timeout_seconds) as response:
            response_body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise AIProviderUnavailable("AI provider request failed.") from exc
    try:
        content = response_body["choices"][0]["message"]["content"]
        result = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIProviderUnavailable("AI provider returned an invalid response.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("tool_name"), str):
        raise AIProviderUnavailable("AI provider returned an invalid action.")
    if not isinstance(result.get("input", {}), dict):
        raise AIProviderUnavailable("AI provider returned invalid action input.")
    if not isinstance(result.get("summary", ""), str):
        raise AIProviderUnavailable("AI provider returned an invalid summary.")
    return result
