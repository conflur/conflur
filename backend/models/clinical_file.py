import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class ClinicalFile(Base):
    """
    Ficha clínica del paciente (una por paciente). Contenido sensible.

    Va en tabla separada del perfil del paciente a propósito: el perfil
    (demográfico/contacto) lo ven los roles operativos (owner/assistant); el
    CONTENIDO clínico de la ficha solo lo ve quien tiene acceso clínico activo
    (patient_access) — ni la secretaría. RLS aísla entre consultorios.

    `values` = JSONB validado contra el `ficha_schema` de la especialidad.
    `specialty_code` es un snapshot de qué esquema se usó.
    """
    __tablename__ = "clinical_files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    specialty_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("specialties.code", ondelete="RESTRICT"), nullable=False
    )
    values: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship(back_populates="clinical_file")
