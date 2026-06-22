"""Tests del cliente LLM (unit — sin litellm ni API key, con backend fake)."""
import pytest

from llm.client import LLMClient, LLMResult
from config import settings

pytestmark = pytest.mark.unit


def test_complete_uses_injected_backend_and_returns_result():
    captured = {}

    def fake_backend(messages, model, max_tokens, temperature):
        captured.update(messages=messages, model=model, max_tokens=max_tokens, temperature=temperature)
        return LLMResult(text="nota generada", model=model, input_tokens=10, output_tokens=20)

    client = LLMClient(backend=fake_backend)
    result = client.complete([{"role": "user", "content": "hola"}], model="claude-test", max_tokens=500)

    assert result.text == "nota generada"
    assert result.total_tokens == 30
    assert captured["model"] == "claude-test"
    assert captured["max_tokens"] == 500


def test_complete_defaults_to_notes_model():
    seen = {}

    def fake_backend(messages, model, max_tokens, temperature):
        seen["model"] = model
        return LLMResult(text="x", model=model, input_tokens=1, output_tokens=1)

    LLMClient(backend=fake_backend).complete([{"role": "user", "content": "x"}])
    assert seen["model"] == settings.NOTES_MODEL  # default configurable por env
