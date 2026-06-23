"""
Ficha clínica del paciente. Endpoints anidados bajo /patients/{id}/ficha.

Autorización ESTRICTA: leer/escribir la ficha requiere acceso clínico activo
(patient_access). Los roles operativos (owner/assistant) que NO tienen
patient_access no acceden al contenido clínico, aunque sí vean el perfil.
Los valores se validan contra el ficha_schema de la especialidad del tenant.
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from models import Patient, ClinicalFile, Tenant, Specialty
from auth.dependencies import CurrentPrincipal, TenantSession
from patients.access import has_clinical_access
from specialties.ficha_schema import validate_ficha

router = APIRouter(prefix="/patients/{patient_id}/ficha", tags=["fichas"])


class FichaOut(BaseModel):
    patient_id: uuid.UUID
    specialty_code: str
    ficha_schema: dict   # esquema de la especialidad (para render en UI)
    values: dict         # los valores cargados


class FichaUpdate(BaseModel):
    values: dict


async def _require_clinical_access(session, principal, patient_id) -> Patient:
    """Exige que el paciente exista (en el tenant, por RLS) y acceso clínico activo."""
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    if not await has_clinical_access(session, principal.user.id, patient_id):
        # 404 (no revelar existencia de contenido clínico a quien no debe verlo)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ficha no disponible")
    return patient


async def _specialty_schema(session, tenant_id) -> tuple[str, dict]:
    tenant = await session.get(Tenant, tenant_id)
    code = tenant.specialty_code if tenant else None
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El consultorio no tiene especialidad definida")
    sp = await session.get(Specialty, code)
    if sp is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Especialidad inexistente")
    return code, sp.ficha_schema


@router.get("", response_model=FichaOut)
async def get_ficha(patient_id: uuid.UUID, principal: CurrentPrincipal, session: TenantSession):
    await _require_clinical_access(session, principal, patient_id)
    code, schema = await _specialty_schema(session, principal.tenant_id)
    ficha = await session.scalar(select(ClinicalFile).where(ClinicalFile.patient_id == patient_id))
    return FichaOut(
        patient_id=patient_id,
        specialty_code=ficha.specialty_code if ficha else code,
        ficha_schema=schema,
        values=ficha.values if ficha else {},
    )


@router.put("", response_model=FichaOut)
async def upsert_ficha(patient_id: uuid.UUID, body: FichaUpdate, principal: CurrentPrincipal, session: TenantSession):
    await _require_clinical_access(session, principal, patient_id)
    code, schema = await _specialty_schema(session, principal.tenant_id)

    errors = validate_ficha(body.values, schema)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errores": errors})

    ficha = await session.scalar(select(ClinicalFile).where(ClinicalFile.patient_id == patient_id))
    if ficha is None:
        ficha = ClinicalFile(
            tenant_id=principal.tenant_id,
            patient_id=patient_id,
            specialty_code=code,
            values=body.values,
        )
        session.add(ficha)
    else:
        ficha.values = body.values
    await session.flush()
    await session.refresh(ficha)  # updated_at dentro de la tx (RLS activo)
    await session.commit()

    return FichaOut(patient_id=patient_id, specialty_code=ficha.specialty_code, ficha_schema=schema, values=ficha.values)
