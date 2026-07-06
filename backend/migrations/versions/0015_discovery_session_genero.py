"""discovery_sessions — columna genero

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-06

Aditiva. Agrega columna nullable genero ("M" | "F" | NULL) a discovery_sessions
para que el agente use el pronombre correcto desde el primer mensaje.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "discovery_sessions",
        sa.Column("genero", sa.String(1), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discovery_sessions", "genero")
