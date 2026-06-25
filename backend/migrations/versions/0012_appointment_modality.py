"""agenda — modalidad (presencial/telepsicología) + meeting_url

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-25

Aditiva. Turnos suman modalidad (presencial|telepsicologia) y meeting_url
(link de videollamada autogenerado para telepsicología).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("modality", sa.String(length=20), nullable=False, server_default="presencial"))
    op.add_column("appointments", sa.Column("meeting_url", sa.String(length=500), nullable=True))
    # quitar el server_default una vez backfilleadas las filas existentes
    op.alter_column("appointments", "modality", server_default=None)


def downgrade() -> None:
    op.drop_column("appointments", "meeting_url")
    op.drop_column("appointments", "modality")
