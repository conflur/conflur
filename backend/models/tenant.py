import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Tenant(Base):
    """
    Tenant = consultorio. Entidad de primera clase.

    Es la unidad de aislamiento entre clientes: todo recurso clínico/operativo
    (pacientes, turnos, notas, cobros) cuelga del tenant, y el RLS aísla por
    `tenant_id`. Un profesional individual es simplemente un consultorio con un
    único miembro (type='individual'); un consultorio con varios profesionales y
    secretaría es type='practice'.

    Patrón de plataforma: cualquier instancia de EMPRESAS-IA usa este modelo de
    tenancy de primera clase. Lo que varía por instancia es la *forma* del tenant
    (individuo / organización), no el modelo.
    """
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="individual"
    )  # individual | practice
    # Vertical del consultorio (define la ficha y las prestaciones). MVP: una por
    # tenant; multi-especialidad (clínica) se contempla a futuro.
    specialty_code: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("specialties.code", ondelete="RESTRICT"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    memberships: Mapped[list["Membership"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    patients: Mapped[list["Patient"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    session_types: Mapped[list["SessionType"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
