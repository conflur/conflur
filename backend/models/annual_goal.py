import uuid
from datetime import datetime
from sqlalchemy import DateTime, Integer, Numeric, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class AnnualGoal(Base):
    """
    Metas anuales de KPIs del consultorio (tenant-scoped, RLS). Todas opcionales:
    el profesional define solo las que quiere. Se comparan vs el real en el dashboard.
    """
    __tablename__ = "annual_goals"
    __table_args__ = (
        UniqueConstraint("tenant_id", "year", name="uq_annual_goals_tenant_id_year"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_margen_neto: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)        # %
    meta_ticket_promedio: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)   # $
    meta_rentabilidad_por_hora: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)  # $
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
