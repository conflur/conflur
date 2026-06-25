"""
Excedentes — registro de plata disponible por encima de la operación, por fuente
(ahorro, amortizaciones, cobros anticipados, excedente de caja) + la acción que se
decide tomar con cada uno. Acceso restringido a roles operativos.
"""
import uuid
from collections import defaultdict
from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from models import SurplusRecord
from auth.dependencies import TenantSession
from finance.router import FinancePrincipal

router = APIRouter(prefix="/finanzas/excedentes", tags=["excedentes"])

SOURCES = ("ahorro", "amortizaciones", "cobros_anticipados", "excedente_caja")


class SurplusCreate(BaseModel):
    fecha: date
    source: str
    amount: float = Field(gt=0)
    currency: str | None = Field(default=None, max_length=10)
    action: str | None = Field(default=None, max_length=100)
    action_date: date | None = None
    notes: str | None = None


class SurplusUpdate(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    action: str | None = Field(default=None, max_length=100)
    action_date: date | None = None
    notes: str | None = None


class SurplusOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    fecha: date
    source: str
    amount: float
    currency: str | None
    action: str | None
    action_date: date | None
    notes: str | None

    class Config:
        from_attributes = True


class SurplusResumenOut(BaseModel):
    total: float
    por_fuente: dict[str, float]
    sin_accion: float  # excedentes registrados todavía sin decisión de acción


@router.post("", response_model=SurplusOut, status_code=status.HTTP_201_CREATED)
async def create_surplus(body: SurplusCreate, principal: FinancePrincipal, session: TenantSession):
    if body.source not in SOURCES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Fuente inválida ({'|'.join(SOURCES)})")
    rec = SurplusRecord(tenant_id=principal.tenant_id, **body.model_dump())
    session.add(rec)
    await session.commit()
    return SurplusOut.model_validate(rec)


@router.get("", response_model=list[SurplusOut])
async def list_surplus(principal: FinancePrincipal, session: TenantSession,
                       source: str | None = None, desde: date | None = None, hasta: date | None = None):
    stmt = select(SurplusRecord)
    if source:
        stmt = stmt.where(SurplusRecord.source == source)
    if desde:
        stmt = stmt.where(SurplusRecord.fecha >= desde)
    if hasta:
        stmt = stmt.where(SurplusRecord.fecha <= hasta)
    rows = (await session.scalars(stmt.order_by(SurplusRecord.fecha.desc()))).all()
    return [SurplusOut.model_validate(r) for r in rows]


@router.get("/resumen", response_model=SurplusResumenOut)
async def resumen_surplus(principal: FinancePrincipal, session: TenantSession,
                          desde: date | None = None, hasta: date | None = None):
    stmt = select(SurplusRecord)
    if desde:
        stmt = stmt.where(SurplusRecord.fecha >= desde)
    if hasta:
        stmt = stmt.where(SurplusRecord.fecha <= hasta)
    rows = (await session.scalars(stmt)).all()

    por_fuente: dict[str, float] = defaultdict(float)
    total = 0.0
    sin_accion = 0.0
    for r in rows:
        amt = float(r.amount)
        por_fuente[r.source] += amt
        total += amt
        if not r.action:
            sin_accion += amt
    return SurplusResumenOut(
        total=round(total, 2),
        por_fuente={k: round(v, 2) for k, v in por_fuente.items()},
        sin_accion=round(sin_accion, 2),
    )


@router.patch("/{surplus_id}", response_model=SurplusOut)
async def update_surplus(surplus_id: uuid.UUID, body: SurplusUpdate,
                         principal: FinancePrincipal, session: TenantSession):
    rec = await session.get(SurplusRecord, surplus_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Excedente no encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(rec, field, value)
    await session.flush()
    await session.refresh(rec)
    await session.commit()
    return SurplusOut.model_validate(rec)


@router.delete("/{surplus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_surplus(surplus_id: uuid.UUID, principal: FinancePrincipal, session: TenantSession):
    rec = await session.get(SurplusRecord, surplus_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Excedente no encontrado")
    await session.delete(rec)
    await session.commit()
