"""Tests de planes de cuotas (integration). Generación, pago, cierre, RLS."""
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
    email = f"plan_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Plan"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def _patient(client, h) -> str:
    return (await client.post("/patients", headers=h, json={"full_name": "Pac Plan"})).json()["id"]


async def test_crear_plan_paciente_genera_cuotas(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    pid = await _patient(client, h)

    # 10.000 en 3 cuotas desde 2026-03-15
    r = await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "patient", "patient_id": pid, "descripcion": "Tratamiento financiado",
        "total_amount": 10000, "installments_count": 3, "start_date": "2026-03-15", "currency": "ARS",
    })
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "active"
    assert len(d["installments"]) == 3

    montos = [c["amount"] for c in d["installments"]]
    # reparto parejo, última absorbe el redondeo: 3333.33 + 3333.33 + 3333.34 = 10000
    assert montos == [3333.33, 3333.33, 3333.34]
    assert round(sum(montos), 2) == 10000.0

    # vencimientos mensuales
    vencs = [c["due_date"] for c in d["installments"]]
    assert vencs == ["2026-03-15", "2026-04-15", "2026-05-15"]
    assert d["pending_amount"] == 10000.0
    assert d["paid_amount"] == 0.0
    assert d["next_due_date"] == "2026-03-15"


async def test_pagar_todas_cierra_el_plan(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    pid = await _patient(client, h)
    plan = (await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "patient", "patient_id": pid, "descripcion": "Plan", "total_amount": 9000,
        "installments_count": 3, "start_date": "2026-03-01",
    })).json()
    plan_id = plan["id"]

    # pagar cuotas 1 y 2 → sigue activo
    for n in (1, 2):
        r = await client.post(f"/finanzas/planes-cuotas/{plan_id}/cuotas/{n}/pagar", headers=h, json={})
        assert r.status_code == 200, r.text
    mid = r.json()
    assert mid["status"] == "active"
    assert mid["paid_count"] == 2
    assert mid["paid_amount"] == 6000.0
    assert mid["next_due_date"] == "2026-05-01"

    # pagar la última → cierre automático
    r = await client.post(f"/finanzas/planes-cuotas/{plan_id}/cuotas/3/pagar", headers=h, json={"paid_date": "2026-05-02"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "completed"
    assert d["paid_count"] == 3
    assert d["pending_amount"] == 0.0
    assert d["next_due_date"] is None
    cuota3 = next(c for c in d["installments"] if c["number"] == 3)
    assert cuota3["status"] == "paid" and cuota3["paid_date"] == "2026-05-02"

    # no se puede pagar dos veces
    r = await client.post(f"/finanzas/planes-cuotas/{plan_id}/cuotas/1/pagar", headers=h, json={})
    assert r.status_code == 400


async def test_plan_proveedor_y_validaciones(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)

    # proveedor: requiere counterparty_name, no patient_id
    r = await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "provider", "counterparty_name": "Tecno SA", "descripcion": "Notebook financiada",
        "total_amount": 600000, "installments_count": 12, "start_date": "2026-03-01",
    })
    assert r.status_code == 201, r.text
    assert r.json()["counterparty_name"] == "Tecno SA"
    assert len(r.json()["installments"]) == 12

    # proveedor sin counterparty_name → 400
    r = await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "provider", "descripcion": "x", "total_amount": 1000, "installments_count": 2, "start_date": "2026-03-01",
    })
    assert r.status_code == 400

    # paciente sin patient_id → 400
    r = await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "patient", "descripcion": "x", "total_amount": 1000, "installments_count": 2, "start_date": "2026-03-01",
    })
    assert r.status_code == 400


async def test_atraso_y_cancelacion(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    # plan con vencimientos en el pasado → cuotas atrasadas
    plan = (await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "provider", "counterparty_name": "Prov", "descripcion": "Viejo",
        "total_amount": 2000, "installments_count": 2, "start_date": "2020-01-01",
    })).json()
    plan_id = plan["id"]
    assert plan["overdue_count"] == 2
    assert all(c["is_overdue"] for c in plan["installments"])

    # cancelar
    r = await client.delete(f"/finanzas/planes-cuotas/{plan_id}", headers=h)
    assert r.status_code == 204
    d = (await client.get(f"/finanzas/planes-cuotas/{plan_id}", headers=h)).json()
    assert d["status"] == "cancelled"
    # no se puede pagar una cuota de un plan cancelado
    r = await client.post(f"/finanzas/planes-cuotas/{plan_id}/cuotas/1/pagar", headers=h, json={})
    assert r.status_code == 400


async def test_listado_y_filtros(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    pid = await _patient(client, h)
    await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "patient", "patient_id": pid, "descripcion": "P1", "total_amount": 1000,
        "installments_count": 2, "start_date": "2026-03-01"})
    await client.post("/finanzas/planes-cuotas", headers=h, json={
        "direction": "provider", "counterparty_name": "X", "descripcion": "P2", "total_amount": 2000,
        "installments_count": 2, "start_date": "2026-03-01"})

    todos = (await client.get("/finanzas/planes-cuotas", headers=h)).json()
    assert len(todos) == 2
    solo_pac = (await client.get("/finanzas/planes-cuotas", params={"direction": "patient"}, headers=h)).json()
    assert len(solo_pac) == 1 and solo_pac[0]["direction"] == "patient"


async def test_isolation_entre_tenants(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    await client.post("/finanzas/planes-cuotas", headers=_auth(token_a), json={
        "direction": "provider", "counterparty_name": "Solo A", "descripcion": "A",
        "total_amount": 1000, "installments_count": 2, "start_date": "2026-01-01"})
    rows = (await client.get("/finanzas/planes-cuotas", headers=_auth(token_b))).json()
    assert rows == []
