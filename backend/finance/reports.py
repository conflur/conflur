"""
Dashboard financiero: Estado de Resultado (devengado), Flujo de Caja (percibido),
Matriz de Salud Financiera y KPIs. Cálculo puro sobre los datos existentes.
"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import IncomeRecord, CollectionRecord, Expense, MonthlySetting, AnnualGoal
from finance.service import costo_hora, _month_bounds


async def _sum(session, column, *conditions) -> float:
    stmt = select(func.coalesce(func.sum(column), 0))
    for c in conditions:
        stmt = stmt.where(c)
    return float(await session.scalar(stmt))


async def _count(session, *conditions) -> int:
    stmt = select(func.count())
    for c in conditions:
        stmt = stmt.where(c)
    return int(await session.scalar(stmt.select_from(IncomeRecord)))


def _cuadrante(resultado: float, caja: float) -> dict:
    if resultado >= 0 and caja >= 0:
        return {"codigo": "verde", "label": "Zona ideal", "detalle": "Rentable y con caja positiva"}
    if resultado >= 0 and caja < 0:
        return {"codigo": "amarillo", "label": "Cuidado con la caja", "detalle": "Rentable pero la caja quedó negativa"}
    if resultado < 0 and caja >= 0:
        return {"codigo": "naranja", "label": "Viviendo de reservas", "detalle": "Caja positiva pero sin rentabilidad"}
    return {"codigo": "rojo", "label": "Zona crítica", "detalle": "Sin rentabilidad y con caja negativa"}


async def dashboard(session: AsyncSession, year: int, month: int) -> dict:
    start, end = _month_bounds(year, month)
    in_month = (IncomeRecord.fecha >= start, IncomeRecord.fecha <= end)
    col_month = (CollectionRecord.fecha >= start, CollectionRecord.fecha <= end)
    exp_month = (Expense.fecha >= start, Expense.fecha <= end)

    # --- Estado de Resultado (devengado) ---
    ingresos = await _sum(session, IncomeRecord.amount, *in_month)
    costos_variables = await _sum(session, Expense.monto, Expense.tipo == "variable", *exp_month)
    ch = await costo_hora(session, year, month)
    costos_fijos = ch["total_fixed"]  # recurrentes vigentes + amortización
    resultado_neto = round(ingresos - costos_variables - costos_fijos, 2)
    margen_neto = round(resultado_neto / ingresos * 100, 1) if ingresos > 0 else None

    estado_resultado = {
        "ingresos": round(ingresos, 2),
        "costos_variables": round(costos_variables, 2),
        "costos_fijos": round(costos_fijos, 2),
        "resultado_neto": resultado_neto,
        "margen_neto_pct": margen_neto,
    }

    # --- Flujo de Caja (percibido) ---
    setting = await session.scalar(
        select(MonthlySetting).where(MonthlySetting.year == year, MonthlySetting.month == month)
    )
    saldo_inicial = float(setting.opening_cash_balance) if setting else 0.0
    entradas = await _sum(session, CollectionRecord.amount, *col_month)
    salidas = await _sum(session, Expense.monto, Expense.payment_status == "paid", *exp_month)
    flujo_neto = round(entradas - salidas, 2)
    saldo_final = round(saldo_inicial + flujo_neto, 2)

    flujo_caja = {
        "saldo_inicial": round(saldo_inicial, 2),
        "entradas": round(entradas, 2),
        "salidas": round(salidas, 2),
        "flujo_neto": flujo_neto,
        "saldo_final": saldo_final,
    }

    # --- KPIs ---
    atenciones = await _count(session, *in_month)
    planned = ch["planned_hours"]
    kpis = {
        "atenciones": atenciones,
        "ticket_promedio": round(ingresos / atenciones, 2) if atenciones else None,
        "pct_cobro": round(entradas / ingresos * 100, 1) if ingresos > 0 else None,
        "costo_por_paciente": round((costos_fijos + costos_variables) / atenciones, 2) if atenciones else None,
        "rentabilidad_por_hora": round(resultado_neto / planned, 2) if planned and planned > 0 else None,
    }

    # --- Alertas ---
    alertas = []
    if ch["needs_setup"]:
        alertas.append("Falta configurar las horas del mes (afecta costo-hora y rentabilidad/hora).")
    if resultado_neto < 0:
        alertas.append("Rentabilidad negativa este mes.")
    if saldo_final < 0:
        alertas.append("Saldo de caja negativo.")

    # Metas anuales (para comparar vs real en la UI)
    goal = await session.scalar(select(AnnualGoal).where(AnnualGoal.year == year))
    metas = {
        "year": year,
        "meta_margen_neto": float(goal.meta_margen_neto) if goal and goal.meta_margen_neto is not None else None,
        "meta_ticket_promedio": float(goal.meta_ticket_promedio) if goal and goal.meta_ticket_promedio is not None else None,
        "meta_rentabilidad_por_hora": float(goal.meta_rentabilidad_por_hora) if goal and goal.meta_rentabilidad_por_hora is not None else None,
    } if goal else None

    return {
        "year": year,
        "month": month,
        "estado_resultado": estado_resultado,
        "flujo_caja": flujo_caja,
        "matriz_salud": _cuadrante(resultado_neto, saldo_final),
        "kpis": kpis,
        "metas": metas,
        "alertas": alertas,
    }
