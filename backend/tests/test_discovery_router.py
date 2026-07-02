"""
Tests del router del Agente de Descubrimiento — endpoints crear/leer/message/close/findings.

Integración: usa la DB real. Las llamadas LLM se mockean con monkeypatch sobre el
módulo del router (los endpoints públicos llaman a discovery_reply/synthesize_discovery
directamente, sin DI de FastAPI).
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from llm.client import LLMResult
import discovery.router as dr_module


# --------------------------------------------------------- helpers ---- #

integration = pytest.mark.integration


async def _register(client, cleanup) -> str:
    email = f"disc_{uuid.uuid4().hex[:8]}@example.com"
    cleanup.append(email)
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "clave-segura-999", "full_name": "Dr. Discovery"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _fake_reply(text_out="Hola, ¿cómo estás?"):
    def fake(history, *, nombre, referidor, cfg=None, client=None, model=None):
        return LLMResult(text=text_out, model="fake", input_tokens=10, output_tokens=20)
    return fake


def _fake_synth(out=None):
    default = {
        "rol": "solo", "dolores": ["notas acumuladas"], "terminos": {},
        "separacion_consultorio_personal": None, "reaccion_concepto": "positiva",
        "feedback_bot": "bueno", "interes": True, "contacto": "ana@ejemplo.com",
        "resumen": "psicóloga sola, dolores en notas.",
    }
    def fake(history, *, client=None, model=None):
        return out or default
    return fake


@pytest.fixture
async def cleanup():
    emails: list[str] = []
    yield emails
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        for email in emails:
            uid = (await conn.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email})).scalar()
            if uid:
                tids = list((await conn.execute(
                    text("SELECT tenant_id FROM memberships WHERE user_id=:u"), {"u": str(uid)}
                )).scalars())
                for t in tids:
                    # sessions y findings quedan en cascada al borrar el tenant
                    await conn.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": str(t)})
                await conn.execute(text("DELETE FROM users WHERE id=:u"), {"u": str(uid)})
    await engine.dispose()


# --------------------------------------------------------- tests ---- #

@integration
async def test_create_session_devuelve_url_con_apertura(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("Hola Ana!"))
    token = await _register(client, cleanup)

    r = await client.post(
        "/discovery/sessions",
        headers=_auth(token),
        json={"nombre": "Ana García", "referidor": "María"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["nombre"] == "Ana García"
    assert "/discovery/" in data["url"]
    assert data["history"][0]["role"] == "assistant"
    assert data["history"][0]["content"] == "Hola Ana!"
    assert not data["closed"]
    return data["token"]


@integration
async def test_get_session_publica(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply())
    token = await _register(client, cleanup)
    r = await client.post("/discovery/sessions", headers=_auth(token), json={"nombre": "Laura"})
    sess_token = r.json()["token"]

    r2 = await client.get(f"/discovery/sessions/{sess_token}")
    assert r2.status_code == 200
    assert r2.json()["nombre"] == "Laura"
    assert not r2.json()["closed"]


@integration
async def test_send_message_agrega_turnos(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("Apertura"))
    token = await _register(client, cleanup)
    sess_token = (await client.post(
        "/discovery/sessions", headers=_auth(token), json={"nombre": "Laura"}
    )).json()["token"]

    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("¿Y cómo lo llevás?"))
    r = await client.post(f"/discovery/sessions/{sess_token}/message", json={"content": "Hola, sí"})
    assert r.status_code == 200, r.text
    assert r.json()["reply"] == "¿Y cómo lo llevás?"

    # verifica que el historial creció
    r2 = await client.get(f"/discovery/sessions/{sess_token}")
    history = r2.json()["history"]
    assert len(history) == 3  # apertura + user + agent
    assert history[1] == {"role": "user", "content": "Hola, sí"}
    assert history[2] == {"role": "assistant", "content": "¿Y cómo lo llevás?"}


@integration
async def test_close_sintetiza_y_guarda_finding(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("Apertura"))
    token = await _register(client, cleanup)
    sess_token = (await client.post(
        "/discovery/sessions", headers=_auth(token), json={"nombre": "Ana", "referidor": "María"}
    )).json()["token"]

    # agrega turno para que el historial tenga ≥2 mensajes
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("Pregunta"))
    await client.post(f"/discovery/sessions/{sess_token}/message", json={"content": "Respuesta"})

    monkeypatch.setattr(dr_module, "synthesize_discovery", _fake_synth())
    r = await client.post(f"/discovery/sessions/{sess_token}/close")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["finding_id"] is not None
    assert data["findings"]["rol"] == "solo"

    # la sesión queda cerrada
    r2 = await client.get(f"/discovery/sessions/{sess_token}")
    assert r2.json()["closed"] is True

    # close idempotente
    r3 = await client.post(f"/discovery/sessions/{sess_token}/close")
    assert r3.json()["already_closed"] is True


@integration
async def test_message_en_sesion_cerrada_da_409(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply())
    token = await _register(client, cleanup)
    sess_token = (await client.post(
        "/discovery/sessions", headers=_auth(token), json={"nombre": "Laura"}
    )).json()["token"]

    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("x"))
    await client.post(f"/discovery/sessions/{sess_token}/message", json={"content": "ok"})

    monkeypatch.setattr(dr_module, "synthesize_discovery", _fake_synth())
    await client.post(f"/discovery/sessions/{sess_token}/close")

    r = await client.post(f"/discovery/sessions/{sess_token}/message", json={"content": "otro"})
    assert r.status_code == 409


@integration
async def test_list_findings_requiere_auth(client, cleanup, monkeypatch):
    r = await client.get("/discovery/findings")
    assert r.status_code == 403


@integration
async def test_list_findings_devuelve_sesiones_y_consolidado(client, cleanup, monkeypatch):
    monkeypatch.setattr(dr_module, "discovery_reply", _fake_reply("Apertura"))
    token = await _register(client, cleanup)
    await client.post("/discovery/sessions", headers=_auth(token), json={"nombre": "Bea"})

    r = await client.get("/discovery/findings", headers=_auth(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["sessions"]) >= 1
    assert data["sessions"][0]["nombre"] == "Bea"
    assert "total_charlas" in data["consolidated"]
