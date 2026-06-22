import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class Patient(Base):
    """
    tenant_id = id del consultorio (Tenant). RLS aísla entre consultorios.
    Dentro del consultorio, quién accede a este paciente lo define patient_access.
    """
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    treatment_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    session_fee: Mapped[float | None] = mapped_column(nullable=True)
    fee_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)  # ARS, MXN, COP, USD
    payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="patients")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    access_grants: Mapped[list["PatientAccess"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    clinical_file: Mapped["ClinicalFile"] = relationship(back_populates="patient", uselist=False, cascade="all, delete-orphan")
