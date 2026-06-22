"""Schemas de especialidades y prestaciones."""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SpecialtyOut(BaseModel):
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class SpecialtyDetailOut(SpecialtyOut):
    ficha_schema: dict


class SessionTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    duration_minutes: int = Field(default=50, ge=1, le=600)
    base_price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    # Si se omite, se usa la especialidad del consultorio.
    specialty_code: str | None = None


class SessionTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    duration_minutes: int | None = Field(default=None, ge=1, le=600)
    base_price: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None


class SessionTypeOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    specialty_code: str
    name: str
    duration_minutes: int
    base_price: float | None
    currency: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
