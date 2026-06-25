"""Tests de excedentes (integration). Fuentes, resumen, acción, RLS."""
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
    email = f"surp_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Surp"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def test_crear_listar_filtrar_y_validar(client, cleanup):
    h = _auth(await _register(client, cleanup))

    r = await client.post("/finanzas/excedentes", headers=h, json={
        "fecha": "2026-03-31", "source": "ahorro", "amount": 50000})
    assert r.status_code == 201, r.text
    await client.post("/finanzas/excedentes", headers=h, json={
        "fecha": "2026-03-31", "source": "amortizaciones", "amount": 50000})

    todos = (await client.get("/finanzas/excedentes", headers=h)).json()
    assert len(todos) == 2
    solo = (await client.get("/finanzas/excedentes", params={"source": "ahorro"}, headers=h)).json()
    assert len(solo) == 1 and solo[0]["source"] == "ahorro"

    # fuente inválida
    r = await client.post("/finanzas/excedentes", headers=h, json={
        "fecha": "2026-03-31", "source": "loteria", "amount": 1000})
    assert r.status_code == 400


async def test_resumen_y_registro_de_accion(client, cleanup):
    h = _auth(await _register(client, cleanup))

    # con acción decidida
    await client.post("/finanzas/excedentes", headers=h, json={
        "fecha": "2026-03-31", "source": "excedente_caja", "amount": 80000,
        "action": "reinvertir", "action_date": "2026-04-01"})
    # sin acción (pendiente de decidir)
    rec = (await client.post("/finanzas/excedentes", headers=h, json={
        "fecha": "2026-03-31", "source": "cobros_anticipados", "amount": 20000})).json()

    r = await client.get("/finanzas/excedentes/resumen", headers=h)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["total"] == 100000.0
    assert res["por_fuente"]["excedente_caja"] == 80000.0
    assert res["por_fuente"]["cobros_anticipados"] == 20000.0
    assert res["sin_accion"] == 20000.0

    # registrar la acción del pendiente → baja sin_accion
    r = await client.patch(f"/finanzas/excedentes/{rec['id']}", headers=h, json={"action": "reservar"})
    assert r.status_code == 200 and r.json()["action"] == "reservar"
    res2 = (await client.get("/finanzas/excedentes/resumen", headers=h)).json()
    assert res2["sin_accion"] == 0.0


async def test_eliminar_e_isolation(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    rec = (await client.post("/finanzas/excedentes", headers=_auth(token_a), json={
        "fecha": "2026-01-31", "source": "ahorro", "amount": 1000})).json()

    # B no ve los de A
    assert (await client.get("/finanzas/excedentes", headers=_auth(token_b))).json() == []
    # B no puede borrar el de A (RLS → no lo encuentra)
    assert (await client.delete(f"/finanzas/excedentes/{rec['id']}", headers=_auth(token_b))).status_code == 404

    # A sí lo borra
    assert (await client.delete(f"/finanzas/excedentes/{rec['id']}", headers=_auth(token_a))).status_code == 204
    assert (await client.get("/finanzas/excedentes", headers=_auth(token_a))).json() == []
