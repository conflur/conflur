import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class DiscoverySession(Base):
    """
    Sesión del Agente de Descubrimiento (canal web).

    Sin RLS: el UUID token (128 bits, impredecible) es el control de acceso.
    La psicóloga accede con el link sin necesitar cuenta en Conflur.
    """
    __tablename__ = "discovery_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    referidor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("discovery_findings.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
