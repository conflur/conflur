"""
Cálculo del Costo Hora/Consulta (la base del precio inteligente).

Costo fijo del mes = costos fijos recurrentes vigentes + amortización de durables.
Costo Hora = costo fijo del mes / horas productivas del mes.

Se computa en Python sobre los registros del tenant (volumen chico por consultorio);
el filtro de vigencia evita SQL de fechas complejo.
"""
from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import RecurringExpense, Expense, MonthlySetting


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


async def costo_hora(session: AsyncSession, year: int, month: int) -> dict:
    start, end = _month_bounds(year, month)
    target_idx = year * 12 + month

    # Fijos recurrentes vigentes en el mes
    recurrentes = (await session.scalars(select(RecurringExpense))).all()
    fixed_recurring = 0.0
    for r in recurrentes:
        vigente = r.valid_from <= end and (r.valid_until is None or r.valid_until >= start)
        if vigente:
            fixed_recurring += float(r.monthly_amount)

    # Amortización de durables activos en el mes
    durables = (await session.scalars(
        select(Expense).where(Expense.tipo == "durable")
    )).all()
    amortization = 0.0
    for e in durables:
        if not e.useful_life_months or e.useful_life_months <= 0:
            continue
        start_idx = e.fecha.year * 12 + e.fecha.month
        if start_idx <= target_idx < start_idx + e.useful_life_months:
            amortization += float(e.monto) / e.useful_life_months

    total_fixed = round(fixed_recurring + amortization, 2)

    setting = await session.scalar(
        select(MonthlySetting).where(MonthlySetting.year == year, MonthlySetting.month == month)
    )
    planned_hours = float(setting.planned_hours) if setting else None

    costo = round(total_fixed / planned_hours, 2) if planned_hours and planned_hours > 0 else None

    return {
        "year": year,
        "month": month,
        "fixed_recurring": round(fixed_recurring, 2),
        "amortization": round(amortization, 2),
        "total_fixed": total_fixed,
        "planned_hours": planned_hours,
        "costo_hora": costo,
        "needs_setup": planned_hours is None,
    }
