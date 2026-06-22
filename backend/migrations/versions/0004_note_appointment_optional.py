"""clinical_notes.appointment_id opcional

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-22

Una nota clínica puede existir sin un turno formal previo (menos fricción).
appointment_id pasa a nullable y la FK a ON DELETE SET NULL.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_clinical_notes_appointment_id_appointments", "clinical_notes", type_="foreignkey")
    op.alter_column("clinical_notes", "appointment_id", nullable=True)
    op.create_foreign_key(
        "fk_clinical_notes_appointment_id_appointments", "clinical_notes", "appointments",
        ["appointment_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_clinical_notes_appointment_id_appointments", "clinical_notes", type_="foreignkey")
    op.alter_column("clinical_notes", "appointment_id", nullable=False)
    op.create_foreign_key(
        "fk_clinical_notes_appointment_id_appointments", "clinical_notes", "appointments",
        ["appointment_id"], ["id"], ondelete="CASCADE",
    )
