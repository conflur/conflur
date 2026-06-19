import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Membership(Base):
    """
    Liga un usuario (identidad global) a un tenant (consultorio) con un rol.

    Roles dentro del consultorio:
      - owner        → dueño: gestiona miembros, billing, agenda. Configurable si
                       ve contenido clínico ajeno (por default NO).
      - professional → psicólogo: SUS pacientes y SUS notas (vía patient_access).
      - assistant    → secretaría/administrativo: agenda + cobros + contacto.
                       NUNCA accede al contenido de las notas clínicas.

    El rol de plataforma (Sebas / soporte EMPRESAS-IA) NO vive acá — es
    `users.is_platform_admin`, separado del rol dentro de un consultorio.
    """
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_id_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # owner | professional | assistant
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active | invited | suspended
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship(back_populates="memberships")
