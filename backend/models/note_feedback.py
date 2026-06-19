import uuid
from datetime import datetime
from sqlalchemy import Integer, DateTime, ForeignKey, Text, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class NoteFeedback(Base):
    """
    Feedback del profesional sobre la nota generada por IA.
    Rating 1-3: 1=no refleja lo que pasó / 2=ok / 3=perfecto.
    Los patrones destilados de este feedback van al KM (tenant_id='eia1') — ver M1.
    """
    __tablename__ = "note_feedback"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 3", name="ck_note_feedback_rating"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clinical_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    edit_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)  # chars editados
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    note: Mapped["ClinicalNote"] = relationship(back_populates="feedback")
