"""Endpoints de auth: /auth/register, /auth/login, /auth/me."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from db import AsyncSessionLocal
from models import User, Tenant, Membership, Subscription
from auth.security import hash_password, verify_password, create_access_token
from auth.schemas import (
    RegisterRequest, LoginRequest, TokenOut, PrincipalOut, UserOut,
)
from auth.dependencies import CurrentPrincipal
from auth.service import issue_login_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user: User, tenant_id, role: str) -> TokenOut:
    token = create_access_token(user_id=str(user.id), tenant_id=str(tenant_id), role=role)
    return TokenOut(
        access_token=token,
        principal=PrincipalOut(
            user=UserOut(
                id=user.id, email=user.email,
                full_name=user.full_name, is_platform_admin=user.is_platform_admin,
            ),
            tenant_id=tenant_id,
            role=role,
        ),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    """
    Alta de un profesional. Crea su identidad (user) + su consultorio (tenant) +
    la membresía owner + la suscripción freemium. Lo deja logueado (devuelve token).
    """
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(select(User).where(User.email == body.email))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name,
        )
        tenant = Tenant(
            name=body.practice_name or f"Consultorio de {body.full_name}",
            type="individual",
            specialty_code=body.specialty_code,
        )
        session.add_all([user, tenant])
        await session.flush()  # obtiene user.id y tenant.id

        # A partir de acá, las tablas con RLS (memberships, subscriptions) exigen
        # app.tenant_id seteado al tenant recién creado (WITH CHECK).
        await session.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant.id)})
        await session.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": str(user.id)})

        session.add(Membership(tenant_id=tenant.id, user_id=user.id, role="owner", status="active"))
        session.add(Subscription(tenant_id=tenant.id, plan="freemium", status="active"))

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

        return _token_response(user, tenant.id, "owner")


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest):
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == body.email))
        if user is None or not user.hashed_password or not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

        return await issue_login_token(session, user)


@router.get("/me", response_model=PrincipalOut)
async def me(principal: CurrentPrincipal):
    return principal
