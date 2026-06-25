"""Tests de presupuesto anual (integration). Proyección compuesta vs real."""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings

pytestmark = pytest.mark.integration


@pytest.fixture
async def cleanup():
    emails: list[str] = []
    yield emails
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": "require"})
    async with engine.begin() as conn:
        for email in emails:
            uid = (await conn.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email})).scalar()
            if uid:
                tids = (await conn.execute(text("SELECT tenant_id FROM memberships WHERE user_id=:u"), {"u": str(uid)})).scalars().all()
                for t in tids:
                    await conn.execute(text("DELETE FROM tenants WHERE id=:t"), {"t": str(t)})
                await conn.execute(text("DELETE FROM users WHERE id=:u"), {"u": str(uid)})
    await engine.dispose()


async def _register(client, cleanup) -> str:
    email = f"bud_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Bud"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def test_proyeccion_inflacion_compuesta(client, cleanup):
    h = _auth(await _register(client, cleanup))

    r = await client.put("/finanzas/presupuesto", headers=h, json={
        "year": 2026, "estimated_monthly_income": 100000, "income_growth_pct": 0,
        "base_monthly_cost": 100000, "monthly_inflation_pct": 5,
    })
    assert r.status_code == 200, r.text

    d = (await client.get("/finanzas/presupuesto/proyeccion", params={"year": 2026}, headers=h)).json()
    assert d["needs_setup"] is False
    assert len(d["meses"]) == 12

    # inflación compuesta 5% mensual sobre el costo
    assert d["meses"][0]["costo_proyectado"] == 100000.0
    assert d["meses"][1]["costo_proyectado"] == 105000.0
    assert d["meses"][2]["costo_proyectado"] == 110250.0
    # ingreso sin crecimiento → constante
    assert all(m["ingreso_proyectado"] == 100000.0 for m in d["meses"])
    assert d["proyectado"]["ingresos"] == 1200000.0


async def test_proyectado_vs_real_y_desvio(client, cleanup):
    h = _auth(await _register(client, cleanup))

    # real: costo fijo recurrente 100.000/mes todo el año + ingresos devengados 100.000
    await client.post("/finanzas/recurrentes", headers=h, json={
        "concepto": "Alquiler", "monthly_amount": 100000, "valid_from": "2026-01-01"})
    for _ in range(2):
        await client.post("/finanzas/ingresos", headers=h, json={"fecha": "2026-03-10", "amount": 50000})

    # presupuesto: ingreso 100.000/mes, costo 100.000/mes, sin inflación
    await client.put("/finanzas/presupuesto", headers=h, json={
        "year": 2026, "estimated_monthly_income": 100000, "base_monthly_cost": 100000,
        "income_growth_pct": 0, "monthly_inflation_pct": 0})

    d = (await client.get("/finanzas/presupuesto/proyeccion", params={"year": 2026}, headers=h)).json()
    assert d["proyectado"]["ingresos"] == 1200000.0
    assert d["proyectado"]["costos"] == 1200000.0
    # real
    assert d["real"]["ingresos"] == 100000.0
    assert d["real"]["costos"] == 1200000.0  # 12 × 100.000 recurrente
    # desvíos
    assert d["desvio"]["ingresos"] == -1100000.0
    assert d["desvio"]["costos"] == 0.0
    assert d["desvio"]["ingresos_pct"] == round(-1100000 / 1200000 * 100, 1)


async def test_needs_setup_sin_presupuesto(client, cleanup):
    h = _auth(await _register(client, cleanup))
    d = (await client.get("/finanzas/presupuesto/proyeccion", params={"year": 2030}, headers=h)).json()
    assert d["needs_setup"] is True
    assert d["meses"] == []
    assert d["proyectado"]["ingresos"] == 0.0
    assert d["real"]["ingresos"] == 0.0
