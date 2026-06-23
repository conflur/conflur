"""Endpoints de especialidades (catálogo) y prestaciones (session types)."""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from models import Specialty, SessionType, Tenant
from auth.dependencies import CurrentPrincipal, TenantSession
from specialties.schemas import (
    SpecialtyOut, SpecialtyDetailOut,
    SessionTypeCreate, SessionTypeUpdate, SessionTypeOut,
)

router = APIRouter(tags=["specialties"])


# ----------------------------------------------------- catálogo verticales -- #
@router.get("/specialties", response_model=list[SpecialtyOut])
async def list_specialties(principal: CurrentPrincipal, session: TenantSession):
    rows = (await session.scalars(
        select(Specialty).where(Specialty.is_active.is_(True)).order_by(Specialty.name)
    )).all()
    return [SpecialtyOut.model_validate(s) for s in rows]


@router.get("/specialties/{code}", response_model=SpecialtyDetailOut)
async def get_specialty(code: str, principal: CurrentPrincipal, session: TenantSession):
    sp = await session.get(Specialty, code)
    if sp is None or not sp.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")
    return SpecialtyDetailOut.model_validate(sp)


# -------------------------------------------------------- prestaciones ------ #
@router.get("/session-types", response_model=list[SessionTypeOut])
async def list_session_types(principal: CurrentPrincipal, session: TenantSession):
    rows = (await session.scalars(
        select(SessionType).where(SessionType.is_active.is_(True)).order_by(SessionType.name)
    )).all()
    return [SessionTypeOut.model_validate(s) for s in rows]


@router.post("/session-types", response_model=SessionTypeOut, status_code=status.HTTP_201_CREATED)
async def create_session_type(body: SessionTypeCreate, principal: CurrentPrincipal, session: TenantSession):
    specialty_code = body.specialty_code
    if specialty_code is None:
        tenant = await session.get(Tenant, principal.tenant_id)
        specialty_code = tenant.specialty_code if tenant else None
    if specialty_code is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay especialidad definida para el consultorio")
    if await session.get(Specialty, specialty_code) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Especialidad inexistente")

    st = SessionType(
        tenant_id=principal.tenant_id,
        specialty_code=specialty_code,
        name=body.name,
        duration_minutes=body.duration_minutes,
        base_price=body.base_price,
        currency=body.currency,
    )
    session.add(st)
    await session.commit()
    return SessionTypeOut.model_validate(st)


@router.patch("/session-types/{st_id}", response_model=SessionTypeOut)
async def update_session_type(st_id: uuid.UUID, body: SessionTypeUpdate, principal: CurrentPrincipal, session: TenantSession):
    st = await session.get(SessionType, st_id)
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestación no encontrada")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(st, field, value)
    await session.flush()
    await session.refresh(st)  # updated_at dentro de la tx (RLS activo)
    await session.commit()
    return SessionTypeOut.model_validate(st)


@router.delete("/session-types/{st_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_session_type(st_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    st = await session.get(SessionType, st_id)
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prestación no encontrada")
    st.is_active = False
    await session.commit()
