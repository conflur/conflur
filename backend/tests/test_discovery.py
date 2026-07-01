"""Tests del Agente de Descubrimiento (unit) — composición de prompt + turno."""
import pytest
from llm.client import LLMClient, LLMResult
from agents.discovery import build_system_prompt, discovery_reply, CONFLUR


@pytest.mark.unit
def test_prompt_encapsula_criterios_y_contexto():
    p = build_system_prompt(nombre="Laura", referidor="Martín")
    # contexto de la charla
    assert "Laura" in p and "Martín" in p
    # voz: producto por el valor, no "herramienta"
    assert "administración del consultorio" in p
    assert 'NUNCA lo llames "una herramienta para psicólogos"' in p
    # forma (Grice) + anti-patrones
    assert "UN mensaje" in p
    assert "te lo digo derecho" in p  # listado como anti-patrón a evitar
    # disclosure oportuna
    assert "NO en el primer mensaje" in p
    # ejemplares (mostrar, no decir)
    assert "Apertura correcta" in p
    # config de instancia inyectada (glosario + incentivo)
    assert "consultante" in p
    assert "meses gratis" in p


@pytest.mark.unit
def test_reply_manda_system_mas_historial():
    seen = {}

    def fake_backend(messages, model, max_tokens, temperature):
        seen["messages"] = messages
        seen["model"] = model
        return LLMResult(text="Hola Laura, ¿cómo estás?", model=model, input_tokens=50, output_tokens=20)

    history = [
        {"role": "assistant", "content": "Hola Laura, ¿cómo estás?"},
        {"role": "user", "content": "Bien, ¿quién sos?"},
    ]
    res = discovery_reply(history, nombre="Laura", referidor="Martín", client=LLMClient(backend=fake_backend))
    assert res.text.startswith("Hola")
    # el primer mensaje es el system; el historial va después
    assert seen["messages"][0]["role"] == "system"
    assert seen["messages"][1:] == history
    # modelo configurable por agente
    assert "sonnet" in seen["model"]


@pytest.mark.unit
def test_apertura_con_historial_vacio():
    def fake_backend(messages, model, max_tokens, temperature):
        # con historial vacío: system + un disparador de usuario (Anthropic exige ≥1 user)
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        return LLMResult(text="Hola Laura, ¿cómo estás? Te escribo de parte de Conflur…", model=model, input_tokens=40, output_tokens=15)

    res = discovery_reply([], nombre="Laura", referidor="Martín", client=LLMClient(backend=fake_backend))
    assert "Conflur" in res.text
