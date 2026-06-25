import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class PaymentPlan(Base):
    """
    Plan de cuotas (financiación en cuotas), tenant-scoped, RLS.

    Dos direcciones (`direction`):
    - `patient`: el paciente le paga al profesional en cuotas (vinculado a un
      paciente del consultorio vía `patient_id`).
    - `provider`: el profesional le paga a un proveedor en cuotas (ej. compró un
      equipo financiado). La contraparte es texto libre (`counterparty_name`).

    Al crear el plan se generan N `PaymentInstallment` (cuotas) con vencimientos
    mensuales. El plan se cierra automáticamente (`status=completed`) cuando se
    cobra/paga la última cuota.
    """
    __tablename__ = "payment_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # patient | provider
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    counterparty_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    installments_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active|completed|cancelled
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
