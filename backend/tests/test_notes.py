"""
Tests del agente de notas (unit) y endpoints (integration con LLM fake inyectado).
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from llm.client import LLMClient, LLMResult, get_llm_client
from agents.notes import generate_clinical_note
from main import app


# ---------------------------------------------------------------- unit ---- #
@pytest.mark.unit
def test_agent_builds_prompt_with_bullets_and_returns_tokens():
    seen = {}

    def fake_backend(messages, model, max_tokens, temperature):
        seen["messages"] = messages
        return LLMResult(text="Nota de evolución...", model=model, input_tokens=120, output_tokens=80)

    res = generate_clinical_note("paciente refiere ansiedad; trabajó respiración", client=LLMClient(backend=fake_backend))
    assert res.text.startswith("Nota")
    assert res.total_tokens == 200
    # los bullets viajan en el prompt del usuario
    assert "ansiedad" in seen["messages"][1]["content"]
    # hay system prompt clínico
    assert seen["messages"][0]["role"] == "system"


@pytest.mark.unit
def test_agent_soap_usa_prompt_estructurado():
    seen = {}

    def fake_backend(messages, model, max_tokens, temperature):
        seen["system"] = messages[0]["content"]
        seen["user"] = messages[1]["content"]
        return LLMResult(text="## Subjetivo (S)\n...", model=model, input_tokens=10, output_tokens=20)

    # formato libre → prompt sin secciones SOAP
    generate_clinical_note("ansiedad", note_format="libre", client=LLMClient(backend=fake_backend))
    assert "## Subjetivo (S)" not in seen["system"]

    # formato soap → prompt con las 4 secciones SOAP
    generate_clinical_note("ansiedad", note_format="soap", client=LLMClient(backend=fake_backend))
    for sec in ("## Subjetivo (S)", "## Objetivo (O)", "## Análisis (A)", "## Plan (P)"):
        assert sec in seen["system"]
    assert "SOAP" in seen["user"]


# --------------------------------------------------------- integration ---- #
integration = pytest.mark.integration


@pytest.fixture
def fake_llm():
    """Override del LLM client por uno fake (sin litellm ni API key)."""
    def fake_backend(messages, model, max_tokens, temperature):
        return LLMResult(text="BORRADOR: el paciente trabajó técnicas de respiración.", model=model, input_tokens=100, output_tokens=50)
    app.dependency_overrides[get_llm_client] = lambda: LLMClient(backend=fake_backend)
    yield
    app.dependency_overrides.pop(get_llm_client, None)


@pytest.fixture
async def cleanup():
    emails: list[str] = []
    yield emails
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        for email in emails:
            uid = (await conn.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email})).scalar()
            if uid:
                tids = (await conn.execute(text("SELECT tenant_id FROM memberships WHERE user_id=:u"), {"u": str(uid)})).scalars().all()
                for t in tids:
                    await conn.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": str(t)})
                await conn.execute(text("DELETE FROM users WHERE id=:u"), {"u": str(uid)})
    await engine.dispose()


async def _register(client, cleanup) -> str:
    email = f"nt_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. NT"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


@integration
async def test_generate_save_list_and_feedback(client, cleanup, fake_llm):
    token = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token), json={"full_name": "Pac Notas"})).json()["id"]

    # generar borrador (no guarda)
    r = await client.post(f"/patients/{pid}/notes/generate", headers=_auth(token),
                          json={"input_bullets": "ansiedad; trabajó respiración"})
    assert r.status_code == 200, r.text
    gen = r.json()
    assert "respiración" in gen["content"]
    assert gen["tokens_used"] == 150

    # guardar (editada)
    r = await client.post(f"/patients/{pid}/notes", headers=_auth(token), json={
        "input_bullets": "ansiedad; trabajó respiración",
        "content": gen["content"] + " (editado)",
        "model_used": gen["model_used"], "tokens_used": gen["tokens_used"], "is_edited": True,
    })
    assert r.status_code == 201, r.text
    note_id = r.json()["id"]

    # listar
    r = await client.get(f"/patients/{pid}/notes", headers=_auth(token))
    assert any(n["id"] == note_id for n in r.json())

    # feedback
    r = await client.post(f"/notes/{note_id}/feedback", headers=_auth(token), json={"rating": 3, "comment": "muy bien"})
    assert r.status_code == 201, r.text


@integration
async def test_generate_requires_clinical_access(client, cleanup, fake_llm):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token_a), json={"full_name": "Pac A"})).json()["id"]
    # B (otro consultorio) no puede generar nota sobre paciente de A
    r = await client.post(f"/patients/{pid}/notes/generate", headers=_auth(token_b), json={"input_bullets": "x"})
    assert r.status_code == 404
