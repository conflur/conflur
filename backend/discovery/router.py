"""
Agente de Descubrimiento — canal web (Fase 3).

Endpoints públicos: el UUID token de la URL es el control de acceso.
Endpoints autenticados: crear sesiones y ver hallazgos consolidados.
"""
import asyncio
import uuid
from sqlalchemy import select
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from db import AsyncSessionLocal, set_tenant
from models import DiscoverySession, DiscoveryFinding, DiscoveryMarketInsight
from auth.dependencies import TenantSession, CurrentPrincipal
from agents.discovery import (
    discovery_reply, synthesize_discovery, synthesize_market_insights, _transcript_text,
)
from agents.discovery_store import aggregate_findings
from config import settings

router = APIRouter(prefix="/discovery", tags=["discovery"])

# Mínimo de charlas cerradas para disparar la síntesis de aprendizaje
_MIN_SESSIONS_FOR_INSIGHTS = 3


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


# --- Helpers internos ---

async def _get_latest_narrative(session, tenant_id: uuid.UUID) -> str | None:
    """Devuelve el narrative del insight más reciente del tenant, o None."""
    row = await session.scalar(
        select(DiscoveryMarketInsight)
        .where(DiscoveryMarketInsight.tenant_id == tenant_id)
        .order_by(DiscoveryMarketInsight.created_at.desc())
        .limit(1)
    )
    return row.narrative if row else None


async def _refresh_insights(tenant_id: uuid.UUID) -> None:
    """Fire-and-forget: sintetiza insights de todas las charlas cerradas del tenant."""
    async with AsyncSessionLocal() as session:
        await set_tenant(session, str(tenant_id))
        findings_rows = list(await session.scalars(
            select(DiscoveryFinding).where(DiscoveryFinding.tenant_id == tenant_id)
        ))
        if len(findings_rows) < _MIN_SESSIONS_FOR_INSIGHTS:
            return
        findings_list = [r.findings for r in findings_rows if r.findings]
        if not findings_list:
            return
        insights, narrative = synthesize_market_insights(findings_list)
        session.add(DiscoveryMarketInsight(
            tenant_id=tenant_id,
            sessions_count=len(findings_list),
            insights=insights,
            narrative=narrative,
        ))
        await session.commit()


# --- Endpoints autenticados ---

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionBody,
    principal: CurrentPrincipal,
    session: TenantSession,
):
    """Crea una sesión y genera el mensaje de apertura. Devuelve la URL a compartir."""
    referidor = body.referidor or "tu colega"
    market_context = await _get_latest_narrative(session, principal.tenant_id)
    result = discovery_reply(
        [], nombre=body.nombre, referidor=referidor,
        genero=body.genero, market_context=market_context,
    )
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
    """Sesiones del tenant + hallazgos consolidados + último insight de aprendizaje."""
    sessions_rows = list(await session.scalars(
        select(DiscoverySession)
        .where(DiscoverySession.tenant_id == principal.tenant_id)
        .order_by(DiscoverySession.created_at.desc())
    ))
    findings_rows = list(await session.scalars(
        select(DiscoveryFinding).order_by(DiscoveryFinding.created_at.desc())
    ))
    consolidated = aggregate_findings(findings_rows)

    latest_insight = await session.scalar(
        select(DiscoveryMarketInsight)
        .where(DiscoveryMarketInsight.tenant_id == principal.tenant_id)
        .order_by(DiscoveryMarketInsight.created_at.desc())
        .limit(1)
    )

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
        "market_insight": {
            "sessions_count": latest_insight.sessions_count,
            "narrative": latest_insight.narrative,
            "insights": latest_insight.insights,
            "created_at": latest_insight.created_at.isoformat(),
        } if latest_insight else None,
    }


@router.post("/insights/refresh", status_code=status.HTTP_202_ACCEPTED)
async def refresh_insights(principal: CurrentPrincipal):
    """Dispara la síntesis de aprendizaje manualmente. Retorna inmediatamente."""
    asyncio.create_task(_refresh_insights(principal.tenant_id))
    return {"status": "enqueued"}


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

        market_context = await _get_latest_narrative(session, disc_sess.tenant_id)
        new_history = list(disc_sess.history) + [{"role": "user", "content": body.content}]
        referidor = disc_sess.referidor or "tu colega"
        result = discovery_reply(
            new_history, nombre=disc_sess.nombre, referidor=referidor,
            genero=disc_sess.genero, market_context=market_context,
        )
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
        tenant_id = disc_sess.tenant_id

        await set_tenant(session, str(tenant_id))

        finding = DiscoveryFinding(
            tenant_id=tenant_id,
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

        # Auto-refresh de insights en background — _refresh_insights verifica el umbral mínimo internamente
        try:
            asyncio.create_task(_refresh_insights(tenant_id))
        except RuntimeError:
            pass  # fuera de event loop (tests sync)

        return {"finding_id": str(finding.id), "findings": findings}
