import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Subscription(Base):
    """
    La suscripción es del consultorio (Tenant), no del usuario individual:
    el consultorio es quien paga y el freemium gate (pacientes activos) se mide
    por consultorio.
    """
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="freemium"
    )  # freemium | monthly | annual
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active | past_due | cancelled | trialing
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)  # stripe | mercadopago
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="subscriptions")
