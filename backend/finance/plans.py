"""
Planes de cuotas (financiación) — paciente y proveedor.

Al crear el plan se generan N cuotas con vencimientos mensuales y montos parejos
(la última cuota absorbe el redondeo). Pagar una cuota la marca `paid`; cuando se
pagan todas, el plan se cierra solo (`status=completed`).

Acceso restringido a roles operativos (owner/assistant), igual que el resto de
finanzas.
"""
import uuid
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from models import PaymentPlan, PaymentInstallment, Patient
from auth.dependencies import TenantSession
from finance.router import FinancePrincipal

router = APIRouter(prefix="/finanzas/planes-cuotas", tags=["planes-cuotas"])

DIRECTIONS = ("patient", "provider")


# --------------------------------------------------------------- schemas ---- #
class PaymentPlanCreate(BaseModel):
    direction: str  # patient | provider
    descripcion: str = Field(min_length=1, max_length=255)
    total_amount: float = Field(gt=0)
    installments_count: int = Field(ge=1, le=120)
    start_date: date
    patient_id: uuid.UUID | None = None
    counterparty_name: str | None = Field(default=None, max_length=255)
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class InstallmentOut(BaseModel):
    id: uuid.UUID
    number: int
    due_date: date
    amount: float
    status: str
    paid_date: date | None
    is_overdue: bool

    class Config:
        from_attributes = True


class PaymentPlanOut(BaseModel):
    id: uuid.UUID
    direction: str
    patient_id: uuid.UUID | None
    counterparty_name: str | None
    descripcion: str
    total_amount: float
    currency: str | None
    installments_count: int
    start_date: date
    status: str
    notes: str | None
    paid_amount: float
    pending_amount: float
    paid_count: int
    overdue_count: int
    next_due_date: date | None


class PaymentPlanDetailOut(PaymentPlanOut):
    installments: list[InstallmentOut]


class InstallmentPay(BaseModel):
    paid_date: date | None = None


# ----------------------------------------------------------------- helpers -- #
def _add_months(d: date, n: int) -> date:
    """Suma n meses clampando el día al último válido del mes destino."""
    total = d.month - 1 + n
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _split_amounts(total: float, n: int) -> list[float]:
    """Reparte `total` en n cuotas parejas; la última absorbe el redondeo."""
    t = Decimal(str(total))
    base = (t / n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    amounts = [base] * (n - 1)
    amounts.append(t - base * (n - 1))
    return [float(a) for a in amounts]


def _to_installment_out(ins: PaymentInstallment, today: date) -> InstallmentOut:
    return InstallmentOut(
        id=ins.id, number=ins.number, due_date=ins.due_date, amount=float(ins.amount),
        status=ins.status, paid_date=ins.paid_date,
        is_overdue=(ins.status == "pending" and ins.due_date < today),
    )


def _to_plan_out(plan: PaymentPlan, installments: list[PaymentInstallment], today: date) -> PaymentPlanOut:
    paid = [i for i in installments if i.status == "paid"]
    pending = [i for i in installments if i.status == "pending"]
    return PaymentPlanOut(
        id=plan.id, direction=plan.direction, patient_id=plan.patient_id,
        counterparty_name=plan.counterparty_name, descripcion=plan.descripcion,
        total_amount=float(plan.total_amount), currency=plan.currency,
        installments_count=plan.installments_count, start_date=plan.start_date,
        status=plan.status, notes=plan.notes,
        paid_amount=round(sum(float(i.amount) for i in paid), 2),
        pending_amount=round(sum(float(i.amount) for i in pending), 2),
        paid_count=len(paid),
        overdue_count=sum(1 for i in pending if i.due_date < today),
        next_due_date=min((i.due_date for i in pending), default=None),
    )


async def _load_installments(session, plan_id: uuid.UUID) -> list[PaymentInstallment]:
    rows = (await session.scalars(
        select(PaymentInstallment).where(PaymentInstallment.plan_id == plan_id).order_by(PaymentInstallment.number)
    )).all()
    return list(rows)


# --------------------------------------------------------------- endpoints -- #
@router.post("", response_model=PaymentPlanDetailOut, status_code=status.HTTP_201_CREATED)
async def create_plan(body: PaymentPlanCreate, principal: FinancePrincipal, session: TenantSession):
    if body.direction not in DIRECTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dirección inválida (patient|provider)")
    if body.direction == "patient":
        if body.patient_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un plan de paciente requiere patient_id")
        if await session.get(Patient, body.patient_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    else:  # provider
        if not body.counterparty_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un plan de proveedor requiere counterparty_name")

    plan = PaymentPlan(
        tenant_id=principal.tenant_id,
        direction=body.direction,
        patient_id=body.patient_id if body.direction == "patient" else None,
        counterparty_name=body.counterparty_name if body.direction == "provider" else None,
        descripcion=body.descripcion,
        total_amount=body.total_amount,
        currency=body.currency,
        installments_count=body.installments_count,
        start_date=body.start_date,
        notes=body.notes,
        status="active",
    )
    session.add(plan)
    await session.flush()  # obtener plan.id dentro de la tx (RLS activo)

    amounts = _split_amounts(body.total_amount, body.installments_count)
    for i, amount in enumerate(amounts):
        session.add(PaymentInstallment(
            tenant_id=principal.tenant_id,
            plan_id=plan.id,
            number=i + 1,
            due_date=_add_months(body.start_date, i),
            amount=amount,
        ))
    await session.flush()
    installments = await _load_installments(session, plan.id)
    await session.commit()

    today = date.today()
    out = _to_plan_out(plan, installments, today)
    return PaymentPlanDetailOut(**out.model_dump(), installments=[_to_installment_out(i, today) for i in installments])


@router.get("", response_model=list[PaymentPlanOut])
async def list_plans(principal: FinancePrincipal, session: TenantSession,
                     direction: str | None = None, estado: str | None = None):
    stmt = select(PaymentPlan)
    if direction:
        stmt = stmt.where(PaymentPlan.direction == direction)
    if estado:
        stmt = stmt.where(PaymentPlan.status == estado)
    plans = (await session.scalars(stmt.order_by(PaymentPlan.start_date.desc()))).all()

    # Cuotas de todos los planes en una sola query.
    plan_ids = [p.id for p in plans]
    by_plan: dict[uuid.UUID, list[PaymentInstallment]] = {pid: [] for pid in plan_ids}
    if plan_ids:
        rows = (await session.scalars(
            select(PaymentInstallment).where(PaymentInstallment.plan_id.in_(plan_ids))
        )).all()
        for ins in rows:
            by_plan[ins.plan_id].append(ins)

    today = date.today()
    return [_to_plan_out(p, by_plan[p.id], today) for p in plans]


@router.get("/{plan_id}", response_model=PaymentPlanDetailOut)
async def get_plan(plan_id: uuid.UUID, principal: FinancePrincipal, session: TenantSession):
    plan = await session.get(PaymentPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    installments = await _load_installments(session, plan.id)
    today = date.today()
    out = _to_plan_out(plan, installments, today)
    return PaymentPlanDetailOut(**out.model_dump(), installments=[_to_installment_out(i, today) for i in installments])


@router.post("/{plan_id}/cuotas/{number}/pagar", response_model=PaymentPlanDetailOut)
async def pay_installment(plan_id: uuid.UUID, number: int, body: InstallmentPay,
                          principal: FinancePrincipal, session: TenantSession):
    plan = await session.get(PaymentPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    if plan.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El plan está cancelado")

    ins = await session.scalar(
        select(PaymentInstallment).where(
            PaymentInstallment.plan_id == plan_id, PaymentInstallment.number == number
        )
    )
    if ins is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuota no encontrada")
    if ins.status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La cuota ya está pagada")

    ins.status = "paid"
    ins.paid_date = body.paid_date or date.today()
    await session.flush()

    installments = await _load_installments(session, plan_id)
    # Cierre automático: si no queda ninguna pendiente, el plan se completa.
    if all(i.status == "paid" for i in installments):
        plan.status = "completed"
    await session.flush()
    await session.refresh(plan)
    await session.commit()

    today = date.today()
    out = _to_plan_out(plan, installments, today)
    return PaymentPlanDetailOut(**out.model_dump(), installments=[_to_installment_out(i, today) for i in installments])


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_plan(plan_id: uuid.UUID, principal: FinancePrincipal, session: TenantSession):
    """Cancela el plan (baja lógica: status=cancelled). Las cuotas quedan como historial."""
    plan = await session.get(PaymentPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan no encontrado")
    plan.status = "cancelled"
    await session.commit()
