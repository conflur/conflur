import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, Numeric, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class SurplusRecord(Base):
    """
    Registro de excedente (plata disponible por encima de la operación),
    tenant-scoped, RLS.

    Cuatro fuentes (`source`):
    - `ahorro`: reserva apartada deliberadamente.
    - `amortizaciones`: la amortización se computa como costo en el ER pero no se
      paga en efectivo → es caja disponible respaldada por ese cargo.
    - `cobros_anticipados`: cobros percibidos antes de devengarse.
    - `excedente_caja`: superávit de caja del período por encima de lo necesario.

    `action` registra qué se decidió hacer con el excedente (reinvertir,
    distribuir, reservar, etc.) — el "registro de acción". Puede quedar nulo hasta
    que se decida.
    """
    __tablename__ = "surplus_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)  # ahorro|amortizaciones|cobros_anticipados|excedente_caja
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    action: Mapped[str | None] = mapped_column(String(100), nullable=True)  # registro de acción (nulo = sin decidir)
    action_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
