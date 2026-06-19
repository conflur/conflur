import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Appointment(Base):
    """
    tenant_id = id del consultorio (Tenant). RLS habilitado.
    professional_user_id = profesional con quien es el turno (para la agenda por
    profesional y el control de acceso dentro del consultorio).
    """
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professional_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="scheduled"
    )  # scheduled | completed | cancelled | no_show
    session_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    clinical_notes: Mapped[list["ClinicalNote"]] = relationship(back_populates="appointment", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="appointment")
