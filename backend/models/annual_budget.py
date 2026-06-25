import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class AnnualBudget(Base):
    """
    Presupuesto anual proyectado, tenant-scoped, RLS. Uno por (tenant, año).

    Parámetros de proyección (la proyección mes a mes se computa, no se persiste):
    - `estimated_monthly_income` + `income_growth_pct`: ingreso base mensual y su
      crecimiento compuesto mes a mes.
    - `base_monthly_cost` + `monthly_inflation_pct`: costo base mensual y la
      inflación compuesta que se le aplica mes a mes.

    Se compara contra el real (ingresos devengados + costos efectivos del año).
    """
    __tablename__ = "annual_budgets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_monthly_income: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    income_growth_pct: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    base_monthly_cost: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    monthly_inflation_pct: Mapped[float] = mapped_column(Numeric(6, 3), nullable=False, default=0)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
