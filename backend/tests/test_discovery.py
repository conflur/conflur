"""Tests del Agente de Descubrimiento (unit) — composición de prompt + turno + consolidación."""
from types import SimpleNamespace
import pytest
from llm.client import LLMClient, LLMResult
from agents.discovery import build_system_prompt, discovery_reply, synthesize_discovery, CONFLUR


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


@pytest.mark.unit
def test_sintesis_parsea_json():
    seen = {}

    def fake_backend(messages, model, max_tokens, temperature):
        seen["user"] = messages[1]["content"]
        # el modelo devuelve el JSON envuelto en fences (caso a manejar)
        return LLMResult(
            text='```json\n{"rol": "solo", "dolores": ["notas se acumulan"], "interes": true}\n```',
            model=model, input_tokens=100, output_tokens=30,
        )

    history = [
        {"role": "assistant", "content": "¿Trabajás sola?"},
        {"role": "user", "content": "Sí, sola. Las notas se me acumulan."},
    ]
    out = synthesize_discovery(history, client=LLMClient(backend=fake_backend))
    assert out["rol"] == "solo"
    assert out["dolores"] == ["notas se acumulan"]
    assert out["interes"] is True
    # la transcripción viaja al prompt con etiquetas legibles
    assert "PERSONA:" in seen["user"] and "ASISTENTE:" in seen["user"]


@pytest.mark.unit
def test_consolidacion_agrega_hallazgos():
    from agents.discovery_store import aggregate_findings

    def row(rol, dolores, terms, interes, contacto):
        return SimpleNamespace(
            rol=rol, interes=interes, contacto=contacto,
            findings={"rol": rol, "dolores": dolores, "terminos": terms, "interes": interes, "contacto": contacto},
        )

    rows = [
        row("solo", ["notas se acumulan", "no lleva la cuenta"],
            {"turno_o_cita": "turno", "paciente_o_consultante": "paciente", "nombre_seccion_finanzas": "finanzas"}, True, "a@mail.com"),
        row("solo", ["notas se acumulan"],
            {"turno_o_cita": "turno", "paciente_o_consultante": "consultante", "nombre_seccion_finanzas": "finanzas"}, False, None),
        row("consultorio_con_equipo", ["cobrar es tedioso"],
            {"turno_o_cita": "cita"}, True, "b@mail.com"),
    ]
    out = aggregate_findings(rows)
    assert out["total_charlas"] == 3
    assert out["por_rol"] == {"solo": 2, "consultorio_con_equipo": 1}
    assert out["dolores_frecuentes"][0] == ("notas se acumulan", 2)
    assert out["terminos"]["turno_vs_cita"] == {"turno": 2, "cita": 1}
    assert out["terminos"]["nombre_seccion_finanzas"] == {"finanzas": 2}
    assert out["interesados"] == 2
    assert out["pct_interes"] == 66.7
    assert set(out["contactos"]) == {"a@mail.com", "b@mail.com"}
