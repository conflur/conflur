"""
Autorización dentro del consultorio (capa de app, sobre el RLS por tenant).

Dos niveles distintos:
- Perfil del paciente (nombre, contacto, cobro): lo ven los roles operativos
  (owner / assistant) y los profesionales con acceso clínico.
- Acceso clínico (notas): SOLO profesionales con un patient_access ACTIVO.
  La secretaría/admin nunca, sin importar el rol. (Lo usará SEB-169.)
"""
from datetime import datetime, timezone

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Patient, PatientAccess

OPERATIONAL_ROLES = ("owner", "assistant")


def _active_access_conditions():
    now = datetime.now(timezone.utc)
    return (
        PatientAccess.revoked_at.is_(None),
        or_(PatientAccess.expires_at.is_(None), PatientAccess.expires_at > now),
    )


async def has_clinical_access(session: AsyncSession, user_id, patient_id) -> bool:
    """True si el usuario tiene un patient_access activo sobre el paciente."""
    stmt = select(PatientAccess.id).where(
        PatientAccess.patient_id == patient_id,
        PatientAccess.professional_user_id == user_id,
        *_active_access_conditions(),
    )
    return await session.scalar(stmt) is not None


async def can_view_patient_profile(session: AsyncSession, principal, patient_id) -> bool:
    """Roles operativos ven todos los perfiles del tenant; profesionales, los suyos."""
    # RLS ya garantiza que el paciente sea del tenant activo.
    patient = await session.get(Patient, patient_id)
    if patient is None:
        return False
    if principal.role in OPERATIONAL_ROLES:
        return True
    return await has_clinical_access(session, principal.user.id, patient_id)


def accessible_patients_stmt(principal):
    """Statement de los pacientes visibles para el principal (perfil)."""
    base = select(Patient).where(Patient.is_active.is_(True))
    if principal.role in OPERATIONAL_ROLES:
        return base  # RLS limita al tenant
    # profesional: solo pacientes con acceso clínico activo
    return (
        base.join(PatientAccess, PatientAccess.patient_id == Patient.id)
        .where(
            PatientAccess.professional_user_id == principal.user.id,
            *_active_access_conditions(),
        )
    )
