"""session_types: target_margin + variable_cost (precio inteligente)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24

Aditiva. Campos para el precio inteligente por prestación.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_types", sa.Column("target_margin", sa.Numeric(5, 2), nullable=True))
    op.add_column("session_types", sa.Column("variable_cost", sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("session_types", "variable_cost")
    op.drop_column("session_types", "target_margin")
