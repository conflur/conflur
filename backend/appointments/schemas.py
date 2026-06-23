"""Schemas de turnos (agenda)."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field

ESTADOS = ("scheduled", "completed", "cancelled", "no_show")


class AppointmentCreate(BaseModel):
    patient_id: uuid.UUID
    starts_at: datetime
    duration_minutes: int = Field(default=50, ge=1, le=600)
    # Si se omite, el profesional del turno es el usuario actual.
    professional_user_id: uuid.UUID | None = None
    session_number: int | None = None
    internal_notes: str | None = None


class AppointmentUpdate(BaseModel):
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    status: str | None = None
    session_number: int | None = None
    internal_notes: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    professional_user_id: uuid.UUID
    patient_id: uuid.UUID
    starts_at: datetime
    duration_minutes: int
    status: str
    session_number: int | None
    internal_notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
