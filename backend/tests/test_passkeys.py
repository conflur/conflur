"""
Tests de passkeys. La ceremonia WebAuthn completa requiere un autenticador real
(la hace el navegador), así que acá cubrimos lo verificable server-side:
challenge token, generación de opciones (protegida) y rechazo de challenge inválido.
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings
from auth.security import create_challenge_token, decode_challenge_token

unit = pytest.mark.unit
integration = pytest.mark.integration


@unit
def test_challenge_token_roundtrip_and_purpose():
    tok = create_challenge_token(challenge_b64="Y2hhbGxlbmdl", subject="user-1", purpose="passkey_register")
    claims = decode_challenge_token(tok, purpose="passkey_register")
    assert claims and claims["challenge"] == "Y2hhbGxlbmdl"
    assert claims["sub"] == "user-1"
    # purpose equivocado → None (no se acepta un token de login para registro)
    assert decode_challenge_token(tok, purpose="passkey_login") is None
    # token alterado → None
    assert decode_challenge_token(tok + "x", purpose="passkey_register") is None


@pytest.fixture
async def cleanup_emails():
    emails: list[str] = []
    yield emails
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        for email in emails:
            uid = (await conn.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})).scalar()
            if uid:
                tids = (await conn.execute(text("SELECT tenant_id FROM memberships WHERE user_id = :u"), {"u": str(uid)})).scalars().all()
                for tid in tids:
                    await conn.execute(text("DELETE FROM tenants WHERE id = :t"), {"t": str(tid)})
                await conn.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(uid)})
    await engine.dispose()


async def _register_and_token(client, email):
    r = await client.post("/auth/register", json={
        "email": email, "password": "contraseña-segura-123", "full_name": "Passkey Test",
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


@integration
async def test_register_options_requires_auth(client):
    r = await client.post("/auth/passkey/register/options")
    assert r.status_code in (401, 403)


@integration
async def test_register_options_returns_options_and_challenge(client, cleanup_emails):
    email = f"pk_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    token = await _register_and_token(client, email)

    r = await client.post("/auth/passkey/register/options", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "challenge_token" in data
    assert data["options"]["rp"]["id"] == settings.webauthn_rp_id
    assert "challenge" in data["options"]
    # el challenge_token es un token de propósito passkey_register válido
    assert decode_challenge_token(data["challenge_token"], purpose="passkey_register") is not None


@integration
async def test_register_verify_rejects_bad_challenge(client, cleanup_emails):
    email = f"pk_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    token = await _register_and_token(client, email)

    # challenge_token de otro usuario / inválido → 400
    bogus = create_challenge_token(challenge_b64="eHh4", subject=str(uuid.uuid4()), purpose="passkey_register")
    r = await client.post(
        "/auth/passkey/register/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"credential": {"id": "x"}, "challenge_token": bogus},
    )
    assert r.status_code == 400


@integration
async def test_login_options_404_without_passkeys(client, cleanup_emails):
    email = f"pk_{uuid.uuid4().hex}@example.com"
    cleanup_emails.append(email)
    await _register_and_token(client, email)
    # el usuario existe pero no registró passkeys aún
    r = await client.post("/auth/passkey/login/options", json={"email": email})
    assert r.status_code == 404
