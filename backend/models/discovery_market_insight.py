import uuid
from datetime import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from .base import Base


class DiscoveryMarketInsight(Base):
    """
    Síntesis cross-session del Agente de Descubrimiento.

    Se genera (o actualiza) cada vez que se cierra una sesión y hay ≥3 charlas.
    El campo `narrative` se inyecta en el system prompt del agente para que
    las próximas charlas partan del conocimiento acumulado.
    """
    __tablename__ = "discovery_market_insights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sessions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
