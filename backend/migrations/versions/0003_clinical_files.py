"""clinical_files (ficha clínica por paciente)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-22

Aditiva. Ficha clínica del paciente (values JSONB validados contra el
ficha_schema de la especialidad). RLS por tenant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty_code", sa.String(50), nullable=False),
        sa.Column("values", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_clinical_files_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_clinical_files_patient_id_patients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialty_code"], ["specialties.code"], name="fk_clinical_files_specialty_code_specialties", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_clinical_files"),
        sa.UniqueConstraint("patient_id", name="uq_clinical_files_patient_id"),
    )
    op.create_index("ix_clinical_files_tenant_id", "clinical_files", ["tenant_id"])

    op.execute("ALTER TABLE clinical_files ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clinical_files FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON clinical_files
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON clinical_files")
    op.execute("ALTER TABLE clinical_files DISABLE ROW LEVEL SECURITY")
    op.drop_table("clinical_files")
