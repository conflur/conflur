import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class PatientAccess(Base):
    """
    Acceso clínico de un profesional a un paciente, DENTRO de un consultorio.

    El RLS por `tenant_id` aísla entre consultorios. Esta tabla resuelve el
    aislamiento DENTRO del consultorio: dos psicólogos del mismo consultorio
    comparten `tenant_id`, así que la nota de uno no queda protegida de otro solo
    con RLS — la protege esta tabla (capa de autorización de la app).

    Regla de visibilidad clínica:
      - access_type='primary' → un profesional principal por paciente.
      - access_type='shared'  → interconsulta: el principal comparte el paciente
        con otro profesional, de forma explícita, registrada, revocable y
        opcionalmente temporal (expires_at).
      - Una nota clínica la ve quien tiene un PatientAccess ACTIVO sobre el
        paciente (no vencido, no revocado). La secretaría/admin NUNCA.

    Toda creación/revocación es un evento auditable (granted_by_user_id + fechas).
    """
    __tablename__ = "patient_access"
    __table_args__ = (
        UniqueConstraint("patient_id", "professional_user_id", name="uq_patient_access_patient_id_professional_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # primary | shared
    granted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # null = permanente; fecha = interconsulta temporal
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # corte manual del acceso

    patient: Mapped["Patient"] = relationship(back_populates="access_grants")
