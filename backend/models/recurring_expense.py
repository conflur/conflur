import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class RecurringExpense(Base):
    """
    Costo fijo recurrente (alquiler, sueldo del profesional, servicios, abonos).
    tenant-scoped, RLS.

    Historial natural sin edición destructiva: un cambio de monto (sube el
    alquiler) se hace cerrando el registro vigente (`valid_until`) y creando uno
    nuevo, NO editando el monto. Así el costo-hora de meses pasados no se altera.

    Se usa para: (a) el costo fijo mensual vigente que alimenta el costo-hora y
    el precio inteligente, (b) proyección de presupuesto.
    """
    __tablename__ = "recurring_expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monthly_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)  # null = vigente
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
