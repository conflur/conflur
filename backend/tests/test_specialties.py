"""Tests de verticales: catálogo de especialidades, ficha schema, prestaciones."""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from specialties.ficha_schema import PSICOLOGIA_FICHA_SCHEMA, validate_ficha

unit = pytest.mark.unit
integration = pytest.mark.integration


# ---------------------------------------------------------------- unit ---- #
@unit
def test_validate_ficha_ok():
    values = {
        "obra_social": "OSDE",
        "descripcion": "Ansiedad",
        "riesgo_suicida": "bajo",
        "es_presuntivo": True,
    }
    assert validate_ficha(values, PSICOLOGIA_FICHA_SCHEMA) == []


@unit
def test_validate_ficha_required_and_unknown_and_type():
    # falta requerido (descripcion, riesgo_suicida), campo desconocido, tipo malo
    errs = validate_ficha({"foo": "bar", "es_presuntivo": "no-bool"}, PSICOLOGIA_FICHA_SCHEMA)
    assert any("descripcion" in e for e in errs)
    assert any("riesgo_suicida" in e for e in errs)
    assert any("foo" in e for e in errs)
    assert any("es_presuntivo" in e for e in errs)


@unit
def test_validate_ficha_select_option():
    errs = validate_ficha({"descripcion": "x", "riesgo_suicida": "altisimo"}, PSICOLOGIA_FICHA_SCHEMA)
    assert any("riesgo_suicida" in e for e in errs)


# --------------------------------------------------------- integration ---- #
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
    email = f"sp_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Sp"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


@integration
async def test_specialties_catalog_and_schema(client, cleanup):
    token = await _register(client, cleanup)
    r = await client.get("/specialties", headers=_auth(token))
    assert r.status_code == 200
    assert any(s["code"] == "psicologia" for s in r.json())

    r = await client.get("/specialties/psicologia", headers=_auth(token))
    assert r.status_code == 200
    schema = r.json()["ficha_schema"]
    keys = {f["key"] for sec in schema["sections"] for f in sec["fields"]}
    assert "riesgo_suicida" in keys  # campo de primera clase


@integration
async def test_session_types_crud_and_isolation(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)

    # A crea una prestación (hereda especialidad del consultorio)
    r = await client.post("/session-types", headers=_auth(token_a), json={"name": "Sesión individual", "duration_minutes": 50, "base_price": 8000, "currency": "ARS"})
    assert r.status_code == 201, r.text
    st = r.json()
    assert st["specialty_code"] == "psicologia"
    st_id = st["id"]

    # A la ve en su lista
    r = await client.get("/session-types", headers=_auth(token_a))
    assert any(x["id"] == st_id for x in r.json())

    # B (otro consultorio) NO la ve (RLS)
    r = await client.get("/session-types", headers=_auth(token_b))
    assert all(x["id"] != st_id for x in r.json())
