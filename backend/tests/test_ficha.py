"""
Tests de ficha clínica (integration). Propiedad clave: el contenido clínico solo
lo ve quien tiene acceso clínico (patient_access), no los roles operativos.
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from auth.security import hash_password

pytestmark = pytest.mark.integration


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
    email = f"fc_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. FC"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def test_ficha_save_validate_and_read(client, cleanup):
    token = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token), json={"full_name": "Paciente Ficha"})).json()["id"]

    # GET inicial: ficha vacía + schema
    r = await client.get(f"/patients/{pid}/ficha", headers=_auth(token))
    assert r.status_code == 200, r.text
    assert r.json()["values"] == {}
    assert any(s["key"] == "riesgo" for s in r.json()["ficha_schema"]["sections"])

    # PUT válido
    r = await client.put(f"/patients/{pid}/ficha", headers=_auth(token), json={"values": {
        "descripcion": "Ansiedad generalizada", "riesgo_suicida": "bajo", "obra_social": "OSDE",
    }})
    assert r.status_code == 200, r.text
    assert r.json()["values"]["riesgo_suicida"] == "bajo"

    # PUT inválido (opción de select inexistente) → 422
    r = await client.put(f"/patients/{pid}/ficha", headers=_auth(token), json={"values": {
        "descripcion": "x", "riesgo_suicida": "altisimo",
    }})
    assert r.status_code == 422


async def test_ficha_cross_tenant_isolation(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token_a), json={"full_name": "Pac A"})).json()["id"]
    # B no ve la ficha de un paciente de A
    assert (await client.get(f"/patients/{pid}/ficha", headers=_auth(token_b))).status_code == 404


async def test_secretaria_ve_perfil_pero_no_ficha(client, cleanup):
    """La secretaría (rol operativo sin patient_access) ve el perfil, no la ficha."""
    token_owner = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token_owner), json={"full_name": "Paciente Privado"})).json()["id"]
    me = (await client.get("/auth/me", headers=_auth(token_owner))).json()
    tenant_id = me["tenant_id"]

    # Crear secretaria (rol assistant) en el mismo consultorio, directo en DB.
    email_sec = f"fc_{uuid.uuid4().hex}@example.com"
    cleanup.append(email_sec)
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        sid = uuid.uuid4()
        await conn.execute(text(
            "INSERT INTO users (id, email, hashed_password, full_name, is_platform_admin, is_active) "
            "VALUES (:id, :e, :p, 'Secre', false, true)"
        ), {"id": str(sid), "e": email_sec, "p": hash_password("contraseña-segura-123")})
        await conn.execute(text(
            "INSERT INTO memberships (id, tenant_id, user_id, role, status) "
            "VALUES (:id, :t, :u, 'assistant', 'active')"
        ), {"id": str(uuid.uuid4()), "t": tenant_id, "u": str(sid)})
    await engine.dispose()

    token_sec = (await client.post("/auth/login", json={"email": email_sec, "password": "contraseña-segura-123"})).json()["access_token"]

    # La secretaría SÍ ve el perfil del paciente (rol operativo)...
    assert (await client.get(f"/patients/{pid}", headers=_auth(token_sec))).status_code == 200
    # ...pero NO la ficha clínica (no tiene patient_access).
    assert (await client.get(f"/patients/{pid}/ficha", headers=_auth(token_sec))).status_code == 404
