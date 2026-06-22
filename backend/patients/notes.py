"""
Notas clínicas con IA (SEB-169). Endpoints bajo /patients/{id}/notes + feedback.

Acceso clínico estricto (patient_access), igual que la ficha. El contenido nunca
se loguea. El agente genera un borrador; el profesional edita y guarda.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from models import Patient, ClinicalNote, NoteFeedback
from auth.dependencies import CurrentPrincipal, TenantSession
from patients.access import has_clinical_access
from agents.notes import generate_clinical_note
from llm.client import LLMClient, get_llm_client

router = APIRouter(tags=["notes"])


class NoteGenerateRequest(BaseModel):
    input_bullets: str = Field(min_length=1)
    template_type: str = "psychology_session"


class NoteGenerateResponse(BaseModel):
    content: str
    model_used: str
    tokens_used: int


class NoteCreate(BaseModel):
    input_bullets: str = Field(min_length=1)
    content: str = Field(min_length=1)
    template_type: str = "psychology_session"
    appointment_id: uuid.UUID | None = None
    model_used: str | None = None
    tokens_used: int | None = None
    is_edited: bool = False


class NoteOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    author_user_id: uuid.UUID
    template_type: str
    content: str
    is_edited: bool

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=3)
    comment: str | None = None


async def _require_clinical_access(session, principal, patient_id):
    patient = await session.get(Patient, patient_id)
    if patient is None or not await has_clinical_access(session, principal.user.id, patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no disponible")


@router.post("/patients/{patient_id}/notes/generate", response_model=NoteGenerateResponse)
async def generate_note(
    patient_id: uuid.UUID,
    body: NoteGenerateRequest,
    principal: CurrentPrincipal,
    session: TenantSession,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
):
    await _require_clinical_access(session, principal, patient_id)
    result = generate_clinical_note(body.input_bullets, template_type=body.template_type, client=llm)
    return NoteGenerateResponse(content=result.text, model_used=result.model, tokens_used=result.total_tokens)


@router.post("/patients/{patient_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(patient_id: uuid.UUID, body: NoteCreate, principal: CurrentPrincipal, session: TenantSession):
    await _require_clinical_access(session, principal, patient_id)
    note = ClinicalNote(
        tenant_id=principal.tenant_id,
        patient_id=patient_id,
        author_user_id=principal.user.id,
        appointment_id=body.appointment_id,
        input_bullets=body.input_bullets,
        content=body.content,
        template_type=body.template_type,
        model_used=body.model_used,
        tokens_used=body.tokens_used,
        is_edited=body.is_edited,
    )
    session.add(note)
    await session.commit()
    return NoteOut.model_validate(note)


@router.get("/patients/{patient_id}/notes", response_model=list[NoteOut])
async def list_notes(patient_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    await _require_clinical_access(session, principal, patient_id)
    rows = (await session.scalars(
        select(ClinicalNote).where(ClinicalNote.patient_id == patient_id).order_by(ClinicalNote.created_at.desc())
    )).all()
    return [NoteOut.model_validate(n) for n in rows]


@router.post("/notes/{note_id}/feedback", status_code=status.HTTP_201_CREATED)
async def add_feedback(note_id: uuid.UUID, body: FeedbackCreate, principal: CurrentPrincipal, session: TenantSession):
    note = await session.get(ClinicalNote, note_id)
    if note is None or not await has_clinical_access(session, principal.user.id, note.patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota no encontrada")
    session.add(NoteFeedback(
        tenant_id=principal.tenant_id, note_id=note_id, rating=body.rating, comment=body.comment,
    ))
    await session.commit()
    return {"status": "ok"}
