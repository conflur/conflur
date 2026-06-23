"""
Finanzas — motor de costos. Carga por compra (Expense) → costo-hora.
Acceso restringido a roles operativos (owner/assistant); el professional puro no
ve las finanzas del consultorio.
"""
import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from datetime import date as date_type

from models import Expense, RecurringExpense, MonthlySetting, IncomeRecord, CollectionRecord
from auth.dependencies import CurrentPrincipal, TenantSession
from auth.schemas import PrincipalOut
from patients.access import OPERATIONAL_ROLES
from finance.schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    RecurringExpenseCreate, RecurringExpenseOut, RecurringChangeAmount,
    MonthlySettingUpsert, MonthlySettingOut, CostoHoraOut, TIPOS,
    IncomeCreate, IncomeOut, CollectionCreate, CollectionOut,
    DashboardOut,
)
from finance.service import costo_hora
from finance.reports import dashboard as compute_dashboard

router = APIRouter(prefix="/finanzas", tags=["finanzas"])


def require_operational(principal: CurrentPrincipal) -> PrincipalOut:
    if principal.role not in OPERATIONAL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenés acceso a las finanzas del consultorio")
    return principal


FinancePrincipal = Annotated[PrincipalOut, Depends(require_operational)]


# ----------------------------------------------------------------- gastos -- #
@router.post("/gastos", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_expense(body: ExpenseCreate, principal: FinancePrincipal, session: TenantSession):
    if body.tipo not in TIPOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo inválido (durable|fijo|variable)")
    if body.tipo == "durable" and not body.useful_life_months:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un bien durable requiere meses de amortización")
    exp = Expense(tenant_id=principal.tenant_id, **body.model_dump())
    session.add(exp)
    await session.commit()
    return ExpenseOut.model_validate(exp)


@router.get("/gastos", response_model=list[ExpenseOut])
async def list_expenses(principal: FinancePrincipal, session: TenantSession,
                        desde: date | None = None, hasta: date | None = None):
    stmt = select(Expense)
    if desde:
        stmt = stmt.where(Expense.fecha >= desde)
    if hasta:
        stmt = stmt.where(Expense.fecha <= hasta)
    rows = (await session.scalars(stmt.order_by(Expense.fecha.desc()))).all()
    return [ExpenseOut.model_validate(e) for e in rows]


@router.patch("/gastos/{expense_id}", response_model=ExpenseOut)
async def update_expense(expense_id: uuid.UUID, body: ExpenseUpdate, principal: FinancePrincipal, session: TenantSession):
    exp = await session.get(Expense, expense_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
    await session.flush()
    await session.refresh(exp)
    await session.commit()
    return ExpenseOut.model_validate(exp)


@router.delete("/gastos/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(expense_id: uuid.UUID, principal: FinancePrincipal, session: TenantSession):
    exp = await session.get(Expense, expense_id)
    if exp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gasto no encontrado")
    await session.delete(exp)
    await session.commit()


# ------------------------------------------------------ costos recurrentes -- #
@router.post("/recurrentes", response_model=RecurringExpenseOut, status_code=status.HTTP_201_CREATED)
async def create_recurring(body: RecurringExpenseCreate, principal: FinancePrincipal, session: TenantSession):
    rec = RecurringExpense(tenant_id=principal.tenant_id, **body.model_dump())
    session.add(rec)
    await session.commit()
    return RecurringExpenseOut.model_validate(rec)


@router.get("/recurrentes", response_model=list[RecurringExpenseOut])
async def list_recurring(principal: FinancePrincipal, session: TenantSession, solo_vigentes: bool = False):
    stmt = select(RecurringExpense)
    if solo_vigentes:
        stmt = stmt.where(RecurringExpense.valid_until.is_(None))
    rows = (await session.scalars(stmt.order_by(RecurringExpense.valid_from.desc()))).all()
    return [RecurringExpenseOut.model_validate(r) for r in rows]


@router.post("/recurrentes/{rec_id}/cambiar-monto", response_model=RecurringExpenseOut, status_code=status.HTTP_201_CREATED)
async def change_recurring_amount(rec_id: uuid.UUID, body: RecurringChangeAmount, principal: FinancePrincipal, session: TenantSession):
    """Cierra el registro vigente y crea uno nuevo desde la fecha efectiva (historial natural)."""
    current = await session.get(RecurringExpense, rec_id)
    if current is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Costo recurrente no encontrado")
    if current.valid_until is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ese registro ya no está vigente")
    current.valid_until = body.effective_from - timedelta(days=1)
    nuevo = RecurringExpense(
        tenant_id=principal.tenant_id,
        concepto=current.concepto,
        categoria=current.categoria,
        monthly_amount=body.new_monthly_amount,
        currency=current.currency,
        valid_from=body.effective_from,
    )
    session.add(nuevo)
    await session.commit()
    return RecurringExpenseOut.model_validate(nuevo)


@router.delete("/recurrentes/{rec_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(rec_id: uuid.UUID, principal: FinancePrincipal, session: TenantSession):
    rec = await session.get(RecurringExpense, rec_id)
    if rec is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Costo recurrente no encontrado")
    await session.delete(rec)
    await session.commit()


# ----------------------------------------------------- configuración mensual -- #
@router.put("/configuracion-mensual", response_model=MonthlySettingOut)
async def upsert_monthly_setting(body: MonthlySettingUpsert, principal: FinancePrincipal, session: TenantSession):
    setting = await session.scalar(
        select(MonthlySetting).where(MonthlySetting.year == body.year, MonthlySetting.month == body.month)
    )
    if setting is None:
        setting = MonthlySetting(tenant_id=principal.tenant_id, **body.model_dump())
        session.add(setting)
    else:
        setting.planned_hours = body.planned_hours
        setting.opening_cash_balance = body.opening_cash_balance
    await session.flush()
    await session.refresh(setting)
    await session.commit()
    return MonthlySettingOut.model_validate(setting)


@router.get("/configuracion-mensual", response_model=MonthlySettingOut)
async def get_monthly_setting(year: int, month: int, principal: FinancePrincipal, session: TenantSession):
    setting = await session.scalar(
        select(MonthlySetting).where(MonthlySetting.year == year, MonthlySetting.month == month)
    )
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin configuración para ese mes")
    return MonthlySettingOut.model_validate(setting)


# ------------------------------------------------- ingresos (devengado) ----- #
@router.post("/ingresos", response_model=IncomeOut, status_code=status.HTTP_201_CREATED)
async def create_income(body: IncomeCreate, principal: FinancePrincipal, session: TenantSession):
    inc = IncomeRecord(tenant_id=principal.tenant_id, **body.model_dump())
    session.add(inc)
    await session.commit()
    return IncomeOut.model_validate(inc)


@router.get("/ingresos", response_model=list[IncomeOut])
async def list_income(principal: FinancePrincipal, session: TenantSession,
                      desde: date_type | None = None, hasta: date_type | None = None):
    stmt = select(IncomeRecord)
    if desde:
        stmt = stmt.where(IncomeRecord.fecha >= desde)
    if hasta:
        stmt = stmt.where(IncomeRecord.fecha <= hasta)
    rows = (await session.scalars(stmt.order_by(IncomeRecord.fecha.desc()))).all()
    return [IncomeOut.model_validate(i) for i in rows]


# ------------------------------------------------- cobros (percibido) ------- #
@router.post("/cobros", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
async def create_collection(body: CollectionCreate, principal: FinancePrincipal, session: TenantSession):
    col = CollectionRecord(tenant_id=principal.tenant_id, **body.model_dump())
    session.add(col)
    await session.commit()
    return CollectionOut.model_validate(col)


@router.get("/cobros", response_model=list[CollectionOut])
async def list_collections(principal: FinancePrincipal, session: TenantSession,
                           desde: date_type | None = None, hasta: date_type | None = None):
    stmt = select(CollectionRecord)
    if desde:
        stmt = stmt.where(CollectionRecord.fecha >= desde)
    if hasta:
        stmt = stmt.where(CollectionRecord.fecha <= hasta)
    rows = (await session.scalars(stmt.order_by(CollectionRecord.fecha.desc()))).all()
    return [CollectionOut.model_validate(c) for c in rows]


# --------------------------------------------------------------- costo-hora -- #
@router.get("/costo-hora", response_model=CostoHoraOut)
async def get_costo_hora(year: int, month: int, principal: FinancePrincipal, session: TenantSession):
    return CostoHoraOut(**await costo_hora(session, year, month))


# --------------------------------------------------------------- dashboard -- #
@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(year: int, month: int, principal: FinancePrincipal, session: TenantSession):
    return DashboardOut(**await compute_dashboard(session, year, month))
