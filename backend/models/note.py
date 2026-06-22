import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class ClinicalNote(Base):
    """
    tenant_id = id del consultorio (Tenant). RLS aísla entre consultorios.
    DENTRO del consultorio la visibilidad la define patient_access: la nota la ve
    quien tiene acceso clínico activo al paciente (author_user_id incluido).
    La secretaría/admin NUNCA accede al contenido.
    NUNCA loguear el contenido de notas clínicas.
    """
    __tablename__ = "clinical_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    input_bullets: Mapped[str] = mapped_column(Text, nullable=False)  # bullets ingresados por el profesional
    content: Mapped[str] = mapped_column(Text, nullable=False)         # nota generada por la IA
    template_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="psychology_session"
    )
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(nullable=True)
    is_edited: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="clinical_notes")
    feedback: Mapped[list["NoteFeedback"]] = relationship(back_populates="note", cascade="all, delete-orphan")
