"""
Primitivas de auth: hashing de contraseñas (bcrypt) y JWT (jose).

El backend es dueño de la verificación de credenciales (D11). NextAuth usa un
Credentials provider que llama a los endpoints /auth/* y guarda el access token
que emite este módulo; el frontend lo manda como Bearer y FastAPI lo valida.
"""
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt, JWTError

from config import settings

ALGORITHM = "HS256"
# 30 días de duración máxima de sesión (architecture.md D7).
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60

# bcrypt opera sobre los primeros 72 bytes; truncamos explícito para evitar el
# ValueError de bcrypt>=5 con secretos más largos.
_BCRYPT_MAX_BYTES = 72


def _secret() -> str:
    if not settings.NEXTAUTH_SECRET:
        raise RuntimeError("NEXTAUTH_SECRET no configurado — no se pueden firmar tokens")
    return settings.NEXTAUTH_SECRET


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    pw = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(pw, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, user_id: str, tenant_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Devuelve los claims si el token es válido y no expiró; None si no."""
    try:
        return jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except JWTError:
        return None


# --- WebAuthn challenge tokens -------------------------------------------- #
# El challenge se devuelve al cliente dentro de un JWT corto firmado, y el
# cliente lo reenvía en el verify. Así el challenge queda ligado al servidor
# (firma + expiración) sin necesidad de estado en DB ni en memoria — funciona
# con múltiples instancias. Vida corta (5 min); single-use no se garantiza sin
# estado (aceptable en M0 por la ventana corta).
CHALLENGE_EXPIRE_MINUTES = 5


def create_challenge_token(*, challenge_b64: str, subject: str, purpose: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "challenge": challenge_b64,
        "sub": subject,            # user_id (registro) o email (login)
        "purpose": purpose,        # "passkey_register" | "passkey_login"
        "iat": now,
        "exp": now + timedelta(minutes=CHALLENGE_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def decode_challenge_token(token: str, *, purpose: str) -> dict | None:
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except JWTError:
        return None
    if claims.get("purpose") != purpose:
        return None
    return claims
