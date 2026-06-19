"""
Dependencies de auth para FastAPI.

Flujo por request protegida:
  Bearer token → claims → abrir sesión DB → set_tenant(tenant_id, user_id) → RLS activo.

Toda sesión de una request autenticada pasa por acá, así que el contexto de
seguridad (app.tenant_id / app.user_id) queda seteado antes de tocar datos.
"""
from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from db import AsyncSessionLocal, set_tenant
from auth.security import decode_access_token
from auth.schemas import PrincipalOut, UserOut
from models import User

_bearer = HTTPBearer(auto_error=True)


def get_token_claims(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> dict:
    claims = decode_access_token(creds.credentials)
    if not claims or "sub" not in claims or "tenant_id" not in claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


async def get_tenant_session(
    claims: Annotated[dict, Depends(get_token_claims)],
) -> AsyncIterator[AsyncSession]:
    """Sesión con el contexto de seguridad de la request ya seteado (RLS activo)."""
    async with AsyncSessionLocal() as session:
        await set_tenant(session, claims["tenant_id"], claims["sub"])
        yield session


TenantSession = Annotated[AsyncSession, Depends(get_tenant_session)]


async def get_current_principal(
    claims: Annotated[dict, Depends(get_token_claims)],
    session: TenantSession,
) -> PrincipalOut:
    user = await session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inexistente o inactivo",
        )
    return PrincipalOut(
        user=UserOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_platform_admin=user.is_platform_admin,
        ),
        tenant_id=claims["tenant_id"],
        role=claims["role"],
    )


CurrentPrincipal = Annotated[PrincipalOut, Depends(get_current_principal)]
