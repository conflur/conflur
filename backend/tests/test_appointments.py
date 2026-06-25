"""Tests de agenda (integration). RLS entre consultorios + CRUD + estados."""
import uuid
from datetime import datetime, timezone, timedelta
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
    email = f"ag_{uuid.uuid4().hex}@example.com"
    cleanup.append(email)
    r = await client.post("/auth/register", json={"email": email, "password": "contraseña-segura-123", "full_name": "Dra. Ag"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t): return {"Authorization": f"Bearer {t}"}


async def test_create_list_update_cancel(client, cleanup):
    token = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token), json={"full_name": "Pac Agenda"})).json()["id"]
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # crear turno (profesional = usuario actual por default)
    r = await client.post("/appointments", headers=_auth(token), json={"patient_id": pid, "starts_at": starts, "duration_minutes": 50})
    assert r.status_code == 201, r.text
    appt = r.json()
    assert appt["status"] == "scheduled"
    aid = appt["id"]

    # listar por rango (incluye el turno de mañana). params dict → httpx codifica el +00:00.
    desde = datetime.now(timezone.utc).isoformat()
    hasta = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    r = await client.get("/appointments", params={"desde": desde, "hasta": hasta}, headers=_auth(token))
    assert r.status_code == 200, r.text
    assert any(a["id"] == aid for a in r.json())

    # marcar completado
    r = await client.patch(f"/appointments/{aid}", headers=_auth(token), json={"status": "completed"})
    assert r.status_code == 200 and r.json()["status"] == "completed"

    # estado inválido → 400
    r = await client.patch(f"/appointments/{aid}", headers=_auth(token), json={"status": "inventado"})
    assert r.status_code == 400

    # cancelar (baja lógica)
    r = await client.delete(f"/appointments/{aid}", headers=_auth(token))
    assert r.status_code == 204
    r = await client.get(f"/appointments/{aid}", headers=_auth(token))
    assert r.json()["status"] == "cancelled"


async def test_cross_tenant_isolation(client, cleanup):
    token_a = await _register(client, cleanup)
    token_b = await _register(client, cleanup)
    pid = (await client.post("/patients", headers=_auth(token_a), json={"full_name": "Pac A"})).json()["id"]
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    aid = (await client.post("/appointments", headers=_auth(token_a), json={"patient_id": pid, "starts_at": starts})).json()["id"]
    # B no ve el turno de A
    assert (await client.get(f"/appointments/{aid}", headers=_auth(token_b))).status_code == 404


async def test_create_appointment_unknown_patient_404(client, cleanup):
    token = await _register(client, cleanup)
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = await client.post("/appointments", headers=_auth(token), json={"patient_id": str(uuid.uuid4()), "starts_at": starts})
    assert r.status_code == 404


async def test_telepsicologia_genera_link_automatico(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    pid = (await client.post("/patients", headers=h, json={"full_name": "Pac Tele"})).json()["id"]
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    # presencial (default) → sin link
    r = await client.post("/appointments", headers=h, json={"patient_id": pid, "starts_at": starts})
    assert r.status_code == 201
    assert r.json()["modality"] == "presencial"
    assert r.json()["meeting_url"] is None

    # telepsicología sin link → se autogenera
    r = await client.post("/appointments", headers=h, json={
        "patient_id": pid, "starts_at": starts, "modality": "telepsicologia"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["modality"] == "telepsicologia"
    assert d["meeting_url"] and d["meeting_url"].startswith("https://")

    # telepsicología con link propio → se respeta
    r = await client.post("/appointments", headers=h, json={
        "patient_id": pid, "starts_at": starts, "modality": "telepsicologia",
        "meeting_url": "https://meet.example.com/sala-propia"})
    assert r.json()["meeting_url"] == "https://meet.example.com/sala-propia"

    # modalidad inválida → 400
    r = await client.post("/appointments", headers=h, json={
        "patient_id": pid, "starts_at": starts, "modality": "zoomba"})
    assert r.status_code == 400


async def test_cambio_modalidad_reconcilia_link(client, cleanup):
    token = await _register(client, cleanup)
    h = _auth(token)
    pid = (await client.post("/patients", headers=h, json={"full_name": "Pac Mod"})).json()["id"]
    starts = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    aid = (await client.post("/appointments", headers=h, json={"patient_id": pid, "starts_at": starts})).json()["id"]

    # presencial → telepsicología: genera link
    r = await client.patch(f"/appointments/{aid}", headers=h, json={"modality": "telepsicologia"})
    assert r.status_code == 200, r.text
    assert r.json()["meeting_url"] and r.json()["meeting_url"].startswith("https://")

    # telepsicología → presencial: limpia el link
    r = await client.patch(f"/appointments/{aid}", headers=h, json={"modality": "presencial"})
    assert r.status_code == 200
    assert r.json()["meeting_url"] is None
