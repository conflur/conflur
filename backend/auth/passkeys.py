"""
Passkeys / WebAuthn (D7). El backend (FastAPI) verifica las ceremonias con
py_webauthn; el navegador hace la ceremonia con @simplewebauthn/browser.

Flujo (4 endpoints):
  registro:  /register/options (protegido) → navegador crea credencial → /register/verify
  login:     /login/options (por email)    → navegador firma assertion  → /login/verify

El challenge viaja en un JWT corto firmado (ver security.create_challenge_token)
para no necesitar estado server-side.
"""
import json
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from webauthn import (
    generate_registration_options, verify_registration_response,
    generate_authentication_options, verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import PublicKeyCredentialDescriptor

from config import settings
from db import AsyncSessionLocal
from models import User, UserPasskey
from auth.security import create_challenge_token, decode_challenge_token
from auth.dependencies import CurrentPrincipal
from auth.service import issue_login_token

router = APIRouter(prefix="/auth/passkey", tags=["auth", "passkeys"])


class VerifyRegistration(BaseModel):
    credential: dict
    challenge_token: str
    device_name: str | None = None


class LoginOptionsRequest(BaseModel):
    email: EmailStr


class VerifyAuthentication(BaseModel):
    credential: dict
    challenge_token: str


# ---------------------------------------------------------------- registro -- #
@router.post("/register/options")
async def register_options(principal: CurrentPrincipal):
    """Genera las opciones de creación de credencial para el usuario logueado."""
    async with AsyncSessionLocal() as session:
        existing = (
            await session.scalars(
                select(UserPasskey).where(UserPasskey.user_id == principal.user.id)
            )
        ).all()

    options = generate_registration_options(
        rp_id=settings.webauthn_rp_id,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_id=str(principal.user.id).encode("utf-8"),
        user_name=principal.user.email,
        user_display_name=principal.user.full_name or principal.user.email,
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=p.credential_id) for p in existing
        ],
    )
    challenge_token = create_challenge_token(
        challenge_b64=bytes_to_base64url(options.challenge),
        subject=str(principal.user.id),
        purpose="passkey_register",
    )
    return {"options": json.loads(options_to_json(options)), "challenge_token": challenge_token}


@router.post("/register/verify")
async def register_verify(body: VerifyRegistration, principal: CurrentPrincipal):
    claims = decode_challenge_token(body.challenge_token, purpose="passkey_register")
    if not claims or claims.get("sub") != str(principal.user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Challenge inválido o expirado")

    try:
        verification = verify_registration_response(
            credential=json.dumps(body.credential),
            expected_challenge=base64url_to_bytes(claims["challenge"]),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origin,
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo verificar la passkey")

    async with AsyncSessionLocal() as session:
        session.add(UserPasskey(
            user_id=principal.user.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            device_name=body.device_name,
        ))
        await session.commit()
    return {"status": "ok"}


# ------------------------------------------------------------------- login -- #
@router.post("/login/options")
async def login_options(body: LoginOptionsRequest):
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == body.email))
        passkeys = []
        if user is not None:
            passkeys = (
                await session.scalars(
                    select(UserPasskey).where(UserPasskey.user_id == user.id)
                )
            ).all()
    if user is None or not passkeys:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay passkeys para este email")

    options = generate_authentication_options(
        rp_id=settings.webauthn_rp_id,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=p.credential_id) for p in passkeys
        ],
    )
    challenge_token = create_challenge_token(
        challenge_b64=bytes_to_base64url(options.challenge),
        subject=str(user.id),
        purpose="passkey_login",
    )
    return {"options": json.loads(options_to_json(options)), "challenge_token": challenge_token}


@router.post("/login/verify")
async def login_verify(body: VerifyAuthentication):
    claims = decode_challenge_token(body.challenge_token, purpose="passkey_login")
    if not claims:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Challenge inválido o expirado")

    raw_id = body.credential.get("rawId") or body.credential.get("id")
    if not raw_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credencial inválida")
    credential_id = base64url_to_bytes(raw_id)

    async with AsyncSessionLocal() as session:
        passkey = await session.scalar(
            select(UserPasskey).where(
                UserPasskey.credential_id == credential_id,
                UserPasskey.user_id == uuid.UUID(claims["sub"]),
            )
        )
        if passkey is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Passkey no reconocida")

        try:
            verification = verify_authentication_response(
                credential=json.dumps(body.credential),
                expected_challenge=base64url_to_bytes(claims["challenge"]),
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=settings.webauthn_origin,
                credential_public_key=passkey.public_key,
                credential_current_sign_count=passkey.sign_count,
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Falló la verificación de la passkey")

        from datetime import datetime, timezone
        passkey.sign_count = verification.new_sign_count
        passkey.last_used_at = datetime.now(timezone.utc)

        user = await session.get(User, passkey.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
        token = await issue_login_token(session, user)
        await session.commit()
    return token
