import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Float, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Payment(Base):
    """
    tenant_id = id del consultorio (Tenant). RLS habilitado.
    Monto en moneda local del profesional (ARS, MXN, COP, etc.).
    """
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)  # ARS, MXN, COP, USD
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending | paid | debt
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    patient: Mapped["Patient"] = relationship(back_populates="payments")
    appointment: Mapped["Appointment"] = relationship(back_populates="payments")
