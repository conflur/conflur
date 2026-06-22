"""Schemas de pacientes."""
import uuid
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    treatment_start_date: date | None = None
    session_fee: float | None = Field(default=None, ge=0)
    fee_currency: str | None = Field(default=None, max_length=10)
    payment_method: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    # Profesional principal del paciente. Si se omite y el creador es professional/
    # owner, el creador queda como principal.
    primary_professional_user_id: uuid.UUID | None = None


class PatientUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    date_of_birth: date | None = None
    treatment_start_date: date | None = None
    session_fee: float | None = Field(default=None, ge=0)
    fee_currency: str | None = Field(default=None, max_length=10)
    payment_method: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    is_active: bool | None = None


class PatientOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    date_of_birth: date | None
    treatment_start_date: date | None
    session_fee: float | None
    fee_currency: str | None
    payment_method: str | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShareRequest(BaseModel):
    """Interconsulta: compartir un paciente con otro profesional del consultorio."""
    professional_user_id: uuid.UUID
    expires_at: datetime | None = None  # null = permanente


class AccessOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_user_id: uuid.UUID
    access_type: str
    granted_by_user_id: uuid.UUID | None
    granted_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None

    class Config:
        from_attributes = True
