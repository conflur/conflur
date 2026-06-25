"""
Agenda — CRUD de turnos. RLS aísla entre consultorios.

Autorización por rol dentro del consultorio (el turno es operativo, no contenido
clínico): owner/assistant ven y gestionan todos los turnos del consultorio; el
professional ve/gestiona los suyos. (Google Calendar + recordatorios WhatsApp =
follow-up, requieren credenciales externas.)
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from models import Appointment, Patient, Membership
from auth.dependencies import CurrentPrincipal, TenantSession
from patients.access import OPERATIONAL_ROLES
from appointments.schemas import (
    AppointmentCreate, AppointmentUpdate, AppointmentOut, ESTADOS, MODALIDADES,
)
from appointments.meeting import generate_meeting_link

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def _is_member(session, tenant_id, user_id) -> bool:
    return await session.scalar(
        select(Membership.id).where(
            Membership.tenant_id == tenant_id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    ) is not None


def _can_manage(principal, appt: Appointment) -> bool:
    """owner/assistant: cualquier turno del consultorio; professional: los suyos."""
    if principal.role in OPERATIONAL_ROLES:
        return True
    return appt.professional_user_id == principal.user.id


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def create_appointment(body: AppointmentCreate, principal: CurrentPrincipal, session: TenantSession):
    # El paciente debe existir en el consultorio (RLS garantiza el tenant).
    if await session.get(Patient, body.patient_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    professional_id = body.professional_user_id or principal.user.id
    if not await _is_member(session, principal.tenant_id, professional_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El profesional no es miembro del consultorio")

    if body.modality not in MODALIDADES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modalidad inválida (presencial|telepsicologia)")

    # Telepsicología: si no se provee link, se autogenera. Presencial: sin link.
    if body.modality == "telepsicologia":
        meeting_url = body.meeting_url or generate_meeting_link()
    else:
        meeting_url = None

    appt = Appointment(
        tenant_id=principal.tenant_id,
        professional_user_id=professional_id,
        patient_id=body.patient_id,
        starts_at=body.starts_at,
        duration_minutes=body.duration_minutes,
        modality=body.modality,
        meeting_url=meeting_url,
        session_number=body.session_number,
        internal_notes=body.internal_notes,
    )
    session.add(appt)
    await session.commit()
    return AppointmentOut.model_validate(appt)


@router.get("", response_model=list[AppointmentOut])
async def list_appointments(
    principal: CurrentPrincipal,
    session: TenantSession,
    desde: datetime | None = None,
    hasta: datetime | None = None,
):
    """Vista por rango (semana/día). El professional ve solo sus turnos."""
    stmt = select(Appointment)
    if desde is not None:
        stmt = stmt.where(Appointment.starts_at >= desde)
    if hasta is not None:
        stmt = stmt.where(Appointment.starts_at < hasta)
    if principal.role not in OPERATIONAL_ROLES:
        stmt = stmt.where(Appointment.professional_user_id == principal.user.id)
    stmt = stmt.order_by(Appointment.starts_at)
    rows = (await session.scalars(stmt)).all()
    return [AppointmentOut.model_validate(a) for a in rows]


@router.get("/{appt_id}", response_model=AppointmentOut)
async def get_appointment(appt_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    appt = await session.get(Appointment, appt_id)
    if appt is None or not _can_manage(principal, appt):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    return AppointmentOut.model_validate(appt)


@router.patch("/{appt_id}", response_model=AppointmentOut)
async def update_appointment(appt_id: uuid.UUID, body: AppointmentUpdate, principal: CurrentPrincipal, session: TenantSession):
    appt = await session.get(Appointment, appt_id)
    if appt is None or not _can_manage(principal, appt):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ESTADOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Estado inválido")
    if "modality" in data and data["modality"] not in MODALIDADES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Modalidad inválida (presencial|telepsicologia)")
    for field, value in data.items():
        setattr(appt, field, value)
    # Reconciliar el link con la modalidad final: telepsicología sin link → genera;
    # presencial → sin link.
    if appt.modality == "telepsicologia" and not appt.meeting_url:
        appt.meeting_url = generate_meeting_link()
    elif appt.modality == "presencial":
        appt.meeting_url = None
    # flush→refresh DENTRO de la tx (tenant/RLS activo) para traer updated_at
    # (onupdate server-side) antes del commit; SET LOCAL no sobrevive al commit.
    await session.flush()
    await session.refresh(appt)
    await session.commit()
    return AppointmentOut.model_validate(appt)


@router.delete("/{appt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(appt_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    """Cancela el turno (baja lógica: status=cancelled), no lo borra."""
    appt = await session.get(Appointment, appt_id)
    if appt is None or not _can_manage(principal, appt):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    appt.status = "cancelled"
    await session.commit()
