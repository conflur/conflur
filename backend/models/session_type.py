import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Numeric, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class SessionType(Base):
    """
    Tipo de prestación/sesión del consultorio (tenant-scoped, RLS).

    Reemplaza el "tratamiento" del referente odontológico. En psicología:
    sesión individual, de pareja, familiar, etc. — duración + precio base.
    El precio inteligente (costo-hora × duración × margen) se calcula en el
    módulo de finanzas (SEB-178); acá vive la definición de la prestación.
    """
    __tablename__ = "session_types"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    specialty_code: Mapped[str] = mapped_column(
        String(50), ForeignKey("specialties.code", ondelete="RESTRICT"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    base_price: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ARS, MXN, COP, USD
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="session_types")
