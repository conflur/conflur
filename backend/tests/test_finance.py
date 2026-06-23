"""Tests del motor de costos (integration). Carga por compra + costo-hora."""
import uuid
from datetime import date
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
    email = f"fin_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Fin"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def test_costo_hora_con_fijos_y_amortizacion(client, cleanup):
    token = await _register(client, cleanup)

    # Costo fijo recurrente: alquiler 100.000/mes desde enero 2026
    r = await client.post("/finanzas/recurrentes", headers=_auth(token), json={
        "concepto": "Alquiler", "monthly_amount": 100000, "valid_from": "2026-01-01", "categoria": "alquiler",
    })
    assert r.status_code == 201, r.text

    # Sueldo del profesional como costo fijo recurrente
    await client.post("/finanzas/recurrentes", headers=_auth(token), json={
        "concepto": "Sueldo", "monthly_amount": 500000, "valid_from": "2026-01-01", "categoria": "sueldo",
    })

    # Bien durable: notebook 1.200.000, amortización 24 meses → 50.000/mes
    r = await client.post("/finanzas/gastos", headers=_auth(token), json={
        "fecha": "2026-03-10", "tipo": "durable", "descripcion": "Notebook", "monto": 1200000, "useful_life_months": 24,
    })
    assert r.status_code == 201, r.text

    # Configuración de marzo: 100 horas productivas
    r = await client.put("/finanzas/configuracion-mensual", headers=_auth(token), json={
        "year": 2026, "month": 3, "planned_hours": 100, "opening_cash_balance": 0,
    })
    assert r.status_code == 200, r.text

    # Costo-hora de marzo 2026: (100000 + 500000 + 50000) / 100 = 6500
    r = await client.get("/finanzas/costo-hora", params={"year": 2026, "month": 3}, headers=_auth(token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total_fixed"] == 650000.0
    assert data["amortization"] == 50000.0
    assert data["costo_hora"] == 6500.0
    assert data["needs_setup"] is False


async def test_durable_requiere_vida_util(client, cleanup):
    token = await _register(client, cleanup)
    r = await client.post("/finanzas/gastos", headers=_auth(token), json={
        "fecha": "2026-03-10", "tipo": "durable", "descripcion": "Equipo", "monto": 50000,
    })
    assert r.status_code == 400


async def test_cambiar_monto_recurrente_cierra_historial(client, cleanup):
    token = await _register(client, cleanup)
    rid = (await client.post("/finanzas/recurrentes", headers=_auth(token), json={
        "concepto": "Alquiler", "monthly_amount": 100000, "valid_from": "2026-01-01",
    })).json()["id"]

    # Cambio de monto desde junio → cierra el viejo, crea uno nuevo
    r = await client.post(f"/finanzas/recurrentes/{rid}/cambiar-monto", headers=_auth(token), json={
        "new_monthly_amount": 130000, "effective_from": "2026-06-01",
    })
    assert r.status_code == 201, r.text
    assert r.json()["monthly_amount"] == 130000.0
    assert r.json()["valid_from"] == "2026-06-01"

    # Hay 2 registros: el viejo cerrado (valid_until 2026-05-31) + el nuevo vigente
    rows = (await client.get("/finanzas/recurrentes", headers=_auth(token))).json()
    assert len(rows) == 2
    viejo = next(x for x in rows if x["id"] == rid)
    assert viejo["valid_until"] == "2026-05-31"


async def test_costo_hora_sin_setup_needs_setup(client, cleanup):
    token = await _register(client, cleanup)
    r = await client.get("/finanzas/costo-hora", params={"year": 2026, "month": 7}, headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["needs_setup"] is True
    assert r.json()["costo_hora"] is None


async def test_finance_isolation_between_tenants(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    await client.post("/finanzas/recurrentes", headers=_auth(token_a), json={
        "concepto": "Alquiler A", "monthly_amount": 100000, "valid_from": "2026-01-01",
    })
    # B no ve los recurrentes de A
    rows = (await client.get("/finanzas/recurrentes", headers=_auth(token_b))).json()
    assert rows == []
