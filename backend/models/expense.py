import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Integer, Numeric, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Expense(Base):
    """
    Gasto/compra puntual (tenant-scoped, RLS). Puerta única de carga de costos:
    el `tipo` deriva a dónde va el gasto.

      - durable → bien amortizable; `useful_life_months` define la amortización
        mensual (monto / vida). Ej: equipamiento, arreglos del consultorio.
      - fijo    → costo fijo del mes (alquiler, servicios, seguros, impuestos…)
        cuando es un pago puntual. Los fijos RECURRENTES (alquiler/sueldo) se
        modelan en RecurringExpense para tener su monto vigente y proyectarlo.
      - variable → costo variable (mínimo en psicología; sin insumos).

    Inventario/materiales NO se modela acá: es un módulo aditivo por-vertical
    (se suma cuando entre una profesión con insumos, sin tocar esto).
    """
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # durable | fijo | variable
    descripcion: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)  # alquiler|sueldo|servicios|equipamiento|impuestos|otro
    monto: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="paid")  # paid | unpaid
    # Solo para durable: meses de amortización.
    useful_life_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
