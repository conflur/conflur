"""Schemas pydantic de auth."""
import uuid
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    # Nombre del consultorio. Si no se da, se deriva del nombre del profesional.
    practice_name: str | None = Field(default=None, max_length=255)
    # Vertical del consultorio. MVP: psicología por default.
    specialty_code: str = Field(default="psicologia", max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_platform_admin: bool


class PrincipalOut(BaseModel):
    """Identidad + contexto del tenant activo de la request."""
    user: UserOut
    tenant_id: uuid.UUID
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    principal: PrincipalOut
