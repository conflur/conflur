import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class DiscoveryFinding(Base):
    """
    Hallazgos de una charla del Agente de Descubrimiento, tenant-scoped, RLS.

    `findings` (JSONB) es la fuente de verdad (todo lo que extrajo la síntesis);
    algunas columnas se materializan aparte solo para consultar/consolidar barato.
    `transcript` guarda la charla cruda. Datos de la instancia (aislados por tenant);
    ingestables a la KM semántica compartida más adelante.
    """
    __tablename__ = "discovery_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    referidor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    findings: Mapped[dict] = mapped_column(JSONB, nullable=False)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    # materializadas para consolidar sin abrir el JSONB
    rol: Mapped[str | None] = mapped_column(String(40), nullable=True)
    interes: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
