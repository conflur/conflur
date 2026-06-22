from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class Specialty(Base):
    """
    Catálogo de especialidades/verticales (global, NO por tenant).

    Cada especialidad define la "skin vertical": el esquema de la ficha clínica
    (campos por sección, JSONB) y la terminología. Sumar una vertical = cargar
    una fila acá, no una migración. El precio/prestaciones son del tenant
    (ver SessionType); acá vive la definición común de la vertical.

    PK = code (slug legible: 'psicologia', 'kinesiologia', ...).
    """
    __tablename__ = "specialties"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Esquema de la ficha clínica: { version, sections: [{key,label,fields:[...]}] }.
    # Define los campos clínicos extendidos (más allá de los demográficos de Patient).
    ficha_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
