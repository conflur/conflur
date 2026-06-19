"""Lógica compartida de auth (reusada por login password y login passkey)."""
from fastapi import HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Membership
from auth.security import create_access_token
from auth.schemas import TokenOut, PrincipalOut, UserOut

# Orden de preferencia al elegir el tenant activo (MVP: normalmente una membresía).
_ROLE_PRIORITY = {"owner": 0, "professional": 1, "assistant": 2}


async def issue_login_token(session: AsyncSession, user: User) -> TokenOut:
    """Resuelve el tenant activo del usuario y emite el access token."""
    # La policy de memberships permite ver las propias membresías con app.user_id.
    await session.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user.id)})
    memberships = (
        await session.scalars(
            select(Membership).where(
                Membership.user_id == user.id, Membership.status == "active"
            )
        )
    ).all()
    if not memberships:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El usuario no tiene un consultorio activo")

    membership = min(memberships, key=lambda m: _ROLE_PRIORITY.get(m.role, 99))
    token = create_access_token(user_id=str(user.id), tenant_id=str(membership.tenant_id), role=membership.role)
    return TokenOut(
        access_token=token,
        principal=PrincipalOut(
            user=UserOut(
                id=user.id, email=user.email,
                full_name=user.full_name, is_platform_admin=user.is_platform_admin,
            ),
            tenant_id=membership.tenant_id,
            role=membership.role,
        ),
    )
