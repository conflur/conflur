import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, Numeric, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class MonthlySetting(Base):
    """
    Configuración mensual del consultorio (tenant-scoped, RLS).

    - `planned_hours`: horas de consulta productivas del mes → denominador del
      Costo Hora/Consulta.
    - `opening_cash_balance`: saldo inicial de caja del mes → base del flujo de caja.
    """
    __tablename__ = "monthly_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", "month", name="uq_monthly_settings_tenant_id_year_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_hours: Mapped[float] = mapped_column(Numeric(6, 1), nullable=False)
    opening_cash_balance: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
