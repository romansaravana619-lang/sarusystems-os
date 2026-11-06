import json
from types import SimpleNamespace

import pytest

from app.ai_assistant import provider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def configure_provider(monkeypatch):
    monkeypatch.setattr(provider.settings, "ai_provider_base_url", "https://ai.example/v1")
    monkeypatch.setattr(provider.settings, "ai_provider_api_key", "test-secret")
    monkeypatch.setattr(provider.settings, "ai_provider_model", "test-model")
    monkeypatch.setattr(provider.settings, "ai_provider_timeout_seconds", 5)


def test_provider_is_not_configured_without_all_environment_values(monkeypatch):
    monkeypatch.setattr(provider.settings, "ai_provider_base_url", "")
    monkeypatch.setattr(provider.settings, "ai_provider_api_key", "test-secret")
    monkeypatch.setattr(provider.settings, "ai_provider_model", "test-model")

    assert provider.provider_is_configured() is False


def test_provider_sends_registered_tools_and_parses_structured_action(monkeypatch):
    configure_provider(monkeypatch)
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "tool_name": "get_tasks",
                        "input": {"status": "ready"},
                        "summary": "Here are your ready tasks.",
                    })
                }
            }]
        })

    monkeypatch.setattr(provider, "urlopen", fake_urlopen)
    result = provider.generate_assistant_action(
        "Show ready tasks",
        [{"name": "get_tasks", "input_schema": {"type": "object"}}],
    )

    assert captured["url"] == "https://ai.example/v1/chat/completions"
    assert captured["authorization"] == "Bearer test-secret"
    assert captured["timeout"] == 5
    assert captured["payload"]["model"] == "test-model"
    assert result["tool_name"] == "get_tasks"
    assert result["input"] == {"status": "ready"}


def test_provider_failure_is_reported_as_safe_unavailable(monkeypatch):
    configure_provider(monkeypatch)

    def fail(*args, **kwargs):
        raise OSError("private transport detail")

    monkeypatch.setattr(provider, "urlopen", fail)
    with pytest.raises(provider.AIProviderUnavailable, match="request failed"):
        provider.generate_assistant_action("Show tasks", [])
