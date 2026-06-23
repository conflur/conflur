"""
Tests de pacientes (integration — requieren DB Neon).

Cubren la propiedad load-bearing: aislamiento entre consultorios (RLS) y
visibilidad dentro del consultorio (patient_access / interconsulta).
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
    """Borra usuarios y sus consultorios al terminar (rol owner, saltea RLS)."""
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


async def _register(client, cleanup) -> tuple[str, str]:
    """Registra un profesional nuevo (= consultorio propio). Devuelve (email, token)."""
    email = f"pt_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={
        "email": email, "password": "contraseña-segura-123", "full_name": "Dra. Test",
    })
    assert r.status_code == 201, r.text
    return email, r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_list_get_patient(client, cleanup):
    _, token = await _register(client, cleanup)

    r = await client.post("/patients", headers=_auth(token), json={"full_name": "Juan Paciente", "session_fee": 5000, "fee_currency": "ARS"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = await client.get("/patients", headers=_auth(token))
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())

    r = await client.get(f"/patients/{pid}", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["full_name"] == "Juan Paciente"

    # PATCH (cubre serialización post-update: updated_at con onupdate)
    r = await client.patch(f"/patients/{pid}", headers=_auth(token), json={"phone": "1122334455"})
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == "1122334455"


async def test_cross_tenant_isolation(client, cleanup):
    # Dos profesionales = dos consultorios distintos.
    _, token_a = await _register(client, cleanup)
    _, token_b = await _register(client, cleanup)

    r = await client.post("/patients", headers=_auth(token_a), json={"full_name": "Paciente de A"})
    pid_a = r.json()["id"]

    # B no ve el paciente de A (RLS entre consultorios).
    r = await client.get(f"/patients/{pid_a}", headers=_auth(token_b))
    assert r.status_code == 404
    r = await client.get("/patients", headers=_auth(token_b))
    assert all(p["id"] != pid_a for p in r.json())


async def test_interconsulta_share_and_revoke(client, cleanup):
    email_a, token_a = await _register(client, cleanup)

    # Crear paciente (A es principal).
    r = await client.post("/patients", headers=_auth(token_a), json={"full_name": "Paciente compartido"})
    pid = r.json()["id"]
    me_a = (await client.get("/auth/me", headers=_auth(token_a))).json()
    tenant_id = me_a["tenant_id"]

    # Insertar un segundo profesional B en el MISMO consultorio (directo en DB).
    email_b = f"pt_{uuid.uuid4().hex}@example.com"
    cleanup.append(email_b)
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        bid = uuid.uuid4()
        await conn.execute(text(
            "INSERT INTO users (id, email, hashed_password, full_name, is_platform_admin, is_active) "
            "VALUES (:id, :e, :p, 'Dr. B', false, true)"
        ), {"id": str(bid), "e": email_b, "p": hash_password("contraseña-segura-123")})
        await conn.execute(text(
            "INSERT INTO memberships (id, tenant_id, user_id, role, status) "
            "VALUES (:id, :t, :u, 'professional', 'active')"
        ), {"id": str(uuid.uuid4()), "t": tenant_id, "u": str(bid)})
    await engine.dispose()

    token_b = (await client.post("/auth/login", json={"email": email_b, "password": "contraseña-segura-123"})).json()["access_token"]

    # B (profesional sin acceso) NO ve el paciente.
    assert (await client.get(f"/patients/{pid}", headers=_auth(token_b))).status_code == 404

    # A comparte el paciente con B (interconsulta).
    r = await client.post(f"/patients/{pid}/share", headers=_auth(token_a), json={"professional_user_id": str(bid)})
    assert r.status_code == 201, r.text

    # Ahora B sí lo ve.
    assert (await client.get(f"/patients/{pid}", headers=_auth(token_b))).status_code == 200

    # A revoca el acceso.
    r = await client.delete(f"/patients/{pid}/share/{bid}", headers=_auth(token_a))
    assert r.status_code == 204

    # B vuelve a no verlo.
    assert (await client.get(f"/patients/{pid}", headers=_auth(token_b))).status_code == 404
