"""Tests de auth: security (unit) + flujo register/login/me (integration)."""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from auth.security import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
)


# ---------------------------------------------------------------- unit ---- #
unit = pytest.mark.unit


@unit
def test_password_hash_roundtrip():
    h = hash_password("un-secreto-largo-123")
    assert h != "un-secreto-largo-123"
    assert verify_password("un-secreto-largo-123", h)
    assert not verify_password("otra-cosa", h)


@unit
def test_password_over_72_bytes_does_not_crash():
    long_pw = "a" * 200
    h = hash_password(long_pw)
    assert verify_password(long_pw, h)


@unit
def test_jwt_roundtrip_and_tamper():
    uid, tid = str(uuid.uuid4()), str(uuid.uuid4())
    token = create_access_token(user_id=uid, tenant_id=tid, role="owner")
    claims = decode_access_token(token)
    assert claims["sub"] == uid
    assert claims["tenant_id"] == tid
    assert claims["role"] == "owner"
    # token alterado → None
    assert decode_access_token(token + "x") is None
    assert decode_access_token("no-es-un-token") is None


# --------------------------------------------------------- integration ---- #
integration = pytest.mark.integration


@pytest.fixture
async def cleanup_emails():
    """Borra usuarios/tenants creados por el test (con rol owner, saltea RLS)."""
    emails: list[str] = []
    yield emails
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        for email in emails:
            uid = (await conn.execute(
                text("SELECT id FROM users WHERE email = :e"), {"e": email}
            )).scalar()
            if uid:
                # tenants del usuario (vía membership) → borrar cascada
                tids = (await conn.execute(
                    text("SELECT tenant_id FROM memberships WHERE user_id = :u"), {"u": str(uid)}
                )).scalars().all()
                for tid in tids:
                    await conn.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": str(tid)})
                await conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(uid)})
    await engine.dispose()


@integration
async def test_register_login_me_flow(client, cleanup_emails):
    email = f"test_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    pw = "contraseña-segura-123"

    # register
    r = await client.post("/auth/register", json={
        "email": email, "password": pw, "full_name": "Dra. Test",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["principal"]["role"] == "owner"
    assert data["principal"]["user"]["email"] == email
    assert data["principal"]["tenant_id"]

    # login
    r = await client.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    # me con token
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == email

    # me sin token → no autorizado
    r = await client.get("/auth/me")
    assert r.status_code in (401, 403)


@integration
async def test_register_duplicate_email_conflicts(client, cleanup_emails):
    email = f"test_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    payload = {"email": email, "password": "contraseña-segura-123", "full_name": "Dup"}
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201, r1.text
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 409


@integration
async def test_login_wrong_password_rejected(client, cleanup_emails):
    email = f"test_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    await client.post("/auth/register", json={
        "email": email, "password": "contraseña-segura-123", "full_name": "X",
    })
    r = await client.post("/auth/login", json={"email": email, "password": "incorrecta"})
    assert r.status_code == 401
