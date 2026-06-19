"""
Test de aislamiento RLS entre consultorios (integration — requiere DB Neon).

Prueba la propiedad de seguridad load-bearing: con app.tenant_id seteado a un
consultorio, solo se ven sus filas, y no se puede insertar en otro consultorio.

Todo corre dentro de una transacción que se hace ROLLBACK — no ensucia la DB.
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import settings

pytestmark = pytest.mark.integration


@pytest.fixture
async def conn():
    # IMPORTANTE: el RLS solo se prueba con un rol SIN bypassrls (conflur_app).
    # neondb_owner saltea el RLS, así que el test debe usar APP_DATABASE_URL.
    url = settings.APP_DATABASE_URL or settings.DATABASE_URL
    engine = create_async_engine(url, connect_args={"ssl": "require"})
    async with engine.connect() as connection:
        trans = await connection.begin()
        try:
            yield connection
        finally:
            await trans.rollback()
    await engine.dispose()


async def _set_tenant(conn, tenant_id):
    # set_config con is_local=true: equivale a SET LOCAL pero acepta parámetros.
    await conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})


async def test_rls_isolates_patients_between_tenants(conn):
    ta, tb = uuid.uuid4(), uuid.uuid4()
    # tenants no tiene RLS — se insertan libremente
    for tid, name in [(ta, "Consultorio A"), (tb, "Consultorio B")]:
        await conn.execute(
            text("INSERT INTO tenants (id, name, type, is_active) VALUES (:id, :n, 'individual', true)"),
            {"id": str(tid), "n": name},
        )

    # Inserto un paciente en cada consultorio, con el tenant activo correcto
    for tid, pname in [(ta, "Paciente A"), (tb, "Paciente B")]:
        await _set_tenant(conn, tid)
        await conn.execute(
            text("INSERT INTO patients (id, tenant_id, full_name, is_active) VALUES (:id, :t, :n, true)"),
            {"id": str(uuid.uuid4()), "t": str(tid), "n": pname},
        )

    # Con tenant A activo: solo veo al paciente de A
    await _set_tenant(conn, ta)
    rows = (await conn.execute(text("SELECT full_name FROM patients"))).scalars().all()
    assert rows == ["Paciente A"], f"RLS no aisló: {rows}"

    # Con tenant B activo: solo veo al paciente de B
    await _set_tenant(conn, tb)
    rows = (await conn.execute(text("SELECT full_name FROM patients"))).scalars().all()
    assert rows == ["Paciente B"], f"RLS no aisló: {rows}"


async def test_rls_with_check_blocks_cross_tenant_insert(conn):
    ta, tb = uuid.uuid4(), uuid.uuid4()
    for tid in (ta, tb):
        await conn.execute(
            text("INSERT INTO tenants (id, name, type, is_active) VALUES (:id, 'C', 'individual', true)"),
            {"id": str(tid)},
        )

    # tenant activo = A, pero intento insertar un paciente del tenant B → WITH CHECK lo bloquea
    await _set_tenant(conn, ta)
    with pytest.raises(Exception):
        await conn.execute(
            text("INSERT INTO patients (id, tenant_id, full_name, is_active) VALUES (:id, :t, 'X', true)"),
            {"id": str(uuid.uuid4()), "t": str(tb)},
        )
