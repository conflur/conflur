"""Endpoints de pacientes. RLS aísla entre consultorios; patient_access adentro."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from models import Patient, PatientAccess, Membership
from auth.dependencies import CurrentPrincipal, TenantSession
from patients.schemas import (
    PatientCreate, PatientUpdate, PatientOut, ShareRequest, AccessOut,
)
from patients.access import (
    can_view_patient_profile, has_clinical_access, accessible_patients_stmt,
    OPERATIONAL_ROLES,
)

router = APIRouter(prefix="/patients", tags=["patients"])


async def _is_member(session, tenant_id, user_id) -> bool:
    stmt = select(Membership.id).where(
        Membership.tenant_id == tenant_id,
        Membership.user_id == user_id,
        Membership.status == "active",
    )
    return await session.scalar(stmt) is not None


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(body: PatientCreate, principal: CurrentPrincipal, session: TenantSession):
    patient = Patient(
        tenant_id=principal.tenant_id,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        date_of_birth=body.date_of_birth,
        treatment_start_date=body.treatment_start_date,
        session_fee=body.session_fee,
        fee_currency=body.fee_currency,
        payment_method=body.payment_method,
        notes=body.notes,
    )
    session.add(patient)
    await session.flush()

    # Definir el profesional principal: el indicado, o el creador si es clínico.
    primary_id = body.primary_professional_user_id
    if primary_id is None and principal.role != "assistant":
        primary_id = principal.user.id

    if primary_id is not None:
        if not await _is_member(session, principal.tenant_id, primary_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="El profesional principal no es miembro del consultorio")
        session.add(PatientAccess(
            tenant_id=principal.tenant_id,
            patient_id=patient.id,
            professional_user_id=primary_id,
            access_type="primary",
            granted_by_user_id=principal.user.id,
        ))

    await session.commit()
    return PatientOut.model_validate(patient)


@router.get("", response_model=list[PatientOut])
async def list_patients(principal: CurrentPrincipal, session: TenantSession):
    patients = (await session.scalars(accessible_patients_stmt(principal))).all()
    return [PatientOut.model_validate(p) for p in patients]


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(patient_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    if not await can_view_patient_profile(session, principal, patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    patient = await session.get(Patient, patient_id)
    return PatientOut.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientOut)
async def update_patient(patient_id: uuid.UUID, body: PatientUpdate, principal: CurrentPrincipal, session: TenantSession):
    if not await can_view_patient_profile(session, principal, patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    patient = await session.get(Patient, patient_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    await session.commit()
    return PatientOut.model_validate(patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_patient(patient_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    if not await can_view_patient_profile(session, principal, patient_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    patient = await session.get(Patient, patient_id)
    patient.is_active = False  # baja lógica (no se borra historia clínica)
    await session.commit()


# --------------------------------------------------------- interconsulta -- #
async def _can_share(session, principal, patient_id) -> bool:
    """Compartir lo puede hacer el owner o un profesional con acceso al paciente."""
    if principal.role == "owner":
        return await session.get(Patient, patient_id) is not None
    return await has_clinical_access(session, principal.user.id, patient_id)


@router.post("/{patient_id}/share", response_model=AccessOut, status_code=status.HTTP_201_CREATED)
async def share_patient(patient_id: uuid.UUID, body: ShareRequest, principal: CurrentPrincipal, session: TenantSession):
    if not await _can_share(session, principal, patient_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés compartir este paciente")
    if not await _is_member(session, principal.tenant_id, body.professional_user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El profesional no es miembro del consultorio")

    # Reusar la fila si ya existe (unique patient_id + professional_user_id).
    existing = await session.scalar(
        select(PatientAccess).where(
            PatientAccess.patient_id == patient_id,
            PatientAccess.professional_user_id == body.professional_user_id,
        )
    )
    if existing is not None:
        if existing.access_type == "primary":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese profesional ya es el principal")
        existing.revoked_at = None
        existing.expires_at = body.expires_at
        existing.granted_by_user_id = principal.user.id
        existing.granted_at = datetime.now(timezone.utc)
        access = existing
    else:
        access = PatientAccess(
            tenant_id=principal.tenant_id,
            patient_id=patient_id,
            professional_user_id=body.professional_user_id,
            access_type="shared",
            granted_by_user_id=principal.user.id,
            expires_at=body.expires_at,
        )
        session.add(access)

    await session.commit()
    return AccessOut.model_validate(access)


@router.delete("/{patient_id}/share/{professional_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(patient_id: uuid.UUID, professional_user_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    if not await _can_share(session, principal, patient_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No podés revocar el acceso")
    access = await session.scalar(
        select(PatientAccess).where(
            PatientAccess.patient_id == patient_id,
            PatientAccess.professional_user_id == professional_user_id,
            PatientAccess.access_type == "shared",
        )
    )
    if access is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acceso compartido no encontrado")
    access.revoked_at = datetime.now(timezone.utc)
    await session.commit()
