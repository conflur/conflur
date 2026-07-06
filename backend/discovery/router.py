"""
Agente de Descubrimiento — canal web (Fase 3).

Endpoints públicos: el UUID token de la URL es el control de acceso.
Endpoints autenticados: crear sesiones y ver hallazgos consolidados.
"""
import uuid
from sqlalchemy import select
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from db import AsyncSessionLocal, set_tenant
from models import DiscoverySession, DiscoveryFinding
from auth.dependencies import TenantSession, CurrentPrincipal
from agents.discovery import discovery_reply, synthesize_discovery, _transcript_text
from agents.discovery_store import aggregate_findings
from config import settings

router = APIRouter(prefix="/discovery", tags=["discovery"])


# --- Schemas ---

class CreateSessionBody(BaseModel):
    nombre: str
    referidor: str | None = None
    genero: str | None = None  # "M" | "F" | None


class SessionOut(BaseModel):
    token: str
    url: str
    nombre: str
    referidor: str | None
    history: list[dict]
    closed: bool


class MessageBody(BaseModel):
    content: str


class MessageOut(BaseModel):
    reply: str
    closed: bool


# --- Endpoints autenticados ---

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionBody,
    principal: CurrentPrincipal,
    session: TenantSession,
):
    """Crea una sesión y genera el mensaje de apertura. Devuelve la URL a compartir."""
    referidor = body.referidor or "tu colega"
    result = discovery_reply([], nombre=body.nombre, referidor=referidor, genero=body.genero)
    opening = [{"role": "assistant", "content": result.text}]

    disc_sess = DiscoverySession(
        tenant_id=principal.tenant_id,
        nombre=body.nombre,
        referidor=body.referidor,
        genero=body.genero,
        history=opening,
    )
    session.add(disc_sess)
    await session.flush()
    await session.refresh(disc_sess)
    await session.commit()

    return SessionOut(
        token=str(disc_sess.id),
        url=f"{settings.FRONTEND_URL}/discovery/{disc_sess.id}",
        nombre=disc_sess.nombre,
        referidor=disc_sess.referidor,
        history=disc_sess.history,
        closed=disc_sess.closed,
    )


@router.get("/findings")
async def list_findings(principal: CurrentPrincipal, session: TenantSession):
    """Sesiones del tenant + hallazgos consolidados."""
    sessions_rows = list(await session.scalars(
        select(DiscoverySession)
        .where(DiscoverySession.tenant_id == principal.tenant_id)
        .order_by(DiscoverySession.created_at.desc())
    ))
    findings_rows = list(await session.scalars(
        select(DiscoveryFinding).order_by(DiscoveryFinding.created_at.desc())
    ))
    consolidated = aggregate_findings(findings_rows)

    return {
        "sessions": [
            {
                "token": str(s.id),
                "nombre": s.nombre,
                "referidor": s.referidor,
                "closed": s.closed,
                "finding_id": str(s.finding_id) if s.finding_id else None,
                "created_at": s.created_at.isoformat(),
                "url": f"{settings.FRONTEND_URL}/discovery/{s.id}",
            }
            for s in sessions_rows
        ],
        "consolidated": consolidated,
    }


# --- Endpoints públicos (autenticación = el UUID token) ---

@router.get("/sessions/{token}", response_model=SessionOut)
async def get_session(token: uuid.UUID):
    """Estado de la sesión. Sin auth requerida."""
    async with AsyncSessionLocal() as session:
        disc_sess = await session.get(DiscoverySession, token)
        if disc_sess is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
        return SessionOut(
            token=str(disc_sess.id),
            url=f"{settings.FRONTEND_URL}/discovery/{disc_sess.id}",
            nombre=disc_sess.nombre,
            referidor=disc_sess.referidor,
            history=disc_sess.history,
            closed=disc_sess.closed,
        )


@router.post("/sessions/{token}/message", response_model=MessageOut)
async def send_message(token: uuid.UUID, body: MessageBody):
    """Agrega el mensaje del usuario y devuelve la respuesta del agente. Sin auth."""
    async with AsyncSessionLocal() as session:
        disc_sess = await session.get(DiscoverySession, token)
        if disc_sess is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
        if disc_sess.closed:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta conversación ya fue cerrada")

        new_history = list(disc_sess.history) + [{"role": "user", "content": body.content}]
        referidor = disc_sess.referidor or "tu colega"
        result = discovery_reply(new_history, nombre=disc_sess.nombre, referidor=referidor, genero=disc_sess.genero)
        new_history = new_history + [{"role": "assistant", "content": result.text}]

        disc_sess.history = new_history
        await session.flush()
        await session.refresh(disc_sess)
        await session.commit()

        return MessageOut(reply=result.text, closed=False)


@router.post("/sessions/{token}/close")
async def close_session(token: uuid.UUID):
    """Cierra la sesión, sintetiza hallazgos y los guarda. Sin auth."""
    async with AsyncSessionLocal() as session:
        disc_sess = await session.get(DiscoverySession, token)
        if disc_sess is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")

        if disc_sess.closed:
            return {"finding_id": str(disc_sess.finding_id) if disc_sess.finding_id else None, "already_closed": True}

        history = list(disc_sess.history)

        if len(history) < 2:
            disc_sess.closed = True
            await session.commit()
            return {"finding_id": None, "already_closed": False}

        findings = synthesize_discovery(history)
        transcript = _transcript_text(history)

        # set_tenant necesario para que RLS de discovery_findings permita el INSERT
        await set_tenant(session, str(disc_sess.tenant_id))

        finding = DiscoveryFinding(
            tenant_id=disc_sess.tenant_id,
            findings=findings,
            transcript=transcript,
            referidor=disc_sess.referidor,
            rol=findings.get("rol"),
            interes=findings.get("interes"),
            contacto=findings.get("contacto"),
        )
        session.add(finding)
        await session.flush()

        disc_sess.closed = True
        disc_sess.finding_id = finding.id
        await session.commit()

        return {"finding_id": str(finding.id), "findings": findings}
