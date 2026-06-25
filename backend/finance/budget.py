"""
Presupuesto anual proyectado vs real. La proyección aplica crecimiento compuesto
al ingreso e inflación compuesta al costo, mes a mes. El real reusa el mismo
cómputo de costos que el dashboard (recurrentes vigentes + amortización +
variables) y los ingresos devengados. Acceso restringido a roles operativos.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func

from models import AnnualBudget, IncomeRecord, Expense
from auth.dependencies import TenantSession
from finance.router import FinancePrincipal
from finance.service import costo_hora, _month_bounds

router = APIRouter(prefix="/finanzas/presupuesto", tags=["presupuesto"])


# --------------------------------------------------------------- schemas ---- #
class BudgetUpsert(BaseModel):
    year: int = Field(ge=2020, le=2100)
    estimated_monthly_income: float = Field(ge=0, default=0)
    income_growth_pct: float = Field(default=0)
    base_monthly_cost: float = Field(ge=0, default=0)
    monthly_inflation_pct: float = Field(default=0)
    currency: str | None = Field(default=None, max_length=10)
    notes: str | None = None


class BudgetOut(BaseModel):
    year: int
    estimated_monthly_income: float
    income_growth_pct: float
    base_monthly_cost: float
    monthly_inflation_pct: float
    currency: str | None
    notes: str | None

    class Config:
        from_attributes = True


class MonthProjection(BaseModel):
    month: int
    ingreso_proyectado: float
    costo_proyectado: float
    resultado_proyectado: float


class Totales(BaseModel):
    ingresos: float
    costos: float
    resultado: float


class DesvioOut(BaseModel):
    ingresos: float
    costos: float
    resultado: float
    ingresos_pct: float | None
    costos_pct: float | None


class BudgetProjectionOut(BaseModel):
    year: int
    needs_setup: bool
    meses: list[MonthProjection]
    proyectado: Totales
    real: Totales
    desvio: DesvioOut


# --------------------------------------------------------------- endpoints -- #
@router.put("", response_model=BudgetOut)
async def upsert_budget(body: BudgetUpsert, principal: FinancePrincipal, session: TenantSession):
    budget = await session.scalar(select(AnnualBudget).where(AnnualBudget.year == body.year))
    if budget is None:
        budget = AnnualBudget(tenant_id=principal.tenant_id, **body.model_dump())
        session.add(budget)
    else:
        for field, value in body.model_dump().items():
            setattr(budget, field, value)
    await session.flush()
    await session.refresh(budget)
    await session.commit()
    return BudgetOut.model_validate(budget)


@router.get("", response_model=BudgetOut)
async def get_budget(year: int, principal: FinancePrincipal, session: TenantSession):
    budget = await session.scalar(select(AnnualBudget).where(AnnualBudget.year == year))
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin presupuesto para ese año")
    return BudgetOut.model_validate(budget)


async def _real_anual(session, year: int) -> tuple[float, float]:
    """Real del año: ingresos devengados + costos efectivos (mismo cómputo que el dashboard)."""
    y_start, _ = _month_bounds(year, 1)
    _, y_end = _month_bounds(year, 12)
    ingresos = float(await session.scalar(
        select(func.coalesce(func.sum(IncomeRecord.amount), 0)).where(
            IncomeRecord.fecha >= y_start, IncomeRecord.fecha <= y_end)
    ))
    costos = 0.0
    for m in range(1, 13):
        start, end = _month_bounds(year, m)
        var = float(await session.scalar(
            select(func.coalesce(func.sum(Expense.monto), 0)).where(
                Expense.tipo == "variable", Expense.fecha >= start, Expense.fecha <= end)
        ))
        ch = await costo_hora(session, year, m)
        costos += var + ch["total_fixed"]
    return round(ingresos, 2), round(costos, 2)


@router.get("/proyeccion", response_model=BudgetProjectionOut)
async def proyeccion(year: int, principal: FinancePrincipal, session: TenantSession):
    budget = await session.scalar(select(AnnualBudget).where(AnnualBudget.year == year))

    meses: list[MonthProjection] = []
    proy_ing = proy_cost = 0.0
    if budget is not None:
        g = float(budget.income_growth_pct) / 100
        infl = float(budget.monthly_inflation_pct) / 100
        base_ing = float(budget.estimated_monthly_income)
        base_cost = float(budget.base_monthly_cost)
        for i in range(12):
            ing = round(base_ing * (1 + g) ** i, 2)
            cost = round(base_cost * (1 + infl) ** i, 2)
            meses.append(MonthProjection(
                month=i + 1, ingreso_proyectado=ing, costo_proyectado=cost,
                resultado_proyectado=round(ing - cost, 2),
            ))
            proy_ing += ing
            proy_cost += cost

    proy_ing = round(proy_ing, 2)
    proy_cost = round(proy_cost, 2)
    real_ing, real_cost = await _real_anual(session, year)

    def _pct(real: float, proy: float) -> float | None:
        return round((real - proy) / proy * 100, 1) if proy else None

    return BudgetProjectionOut(
        year=year,
        needs_setup=budget is None,
        meses=meses,
        proyectado=Totales(ingresos=proy_ing, costos=proy_cost, resultado=round(proy_ing - proy_cost, 2)),
        real=Totales(ingresos=real_ing, costos=real_cost, resultado=round(real_ing - real_cost, 2)),
        desvio=DesvioOut(
            ingresos=round(real_ing - proy_ing, 2),
            costos=round(real_cost - proy_cost, 2),
            resultado=round((real_ing - real_cost) - (proy_ing - proy_cost), 2),
            ingresos_pct=_pct(real_ing, proy_ing),
            costos_pct=_pct(real_cost, proy_cost),
        ),
    )
