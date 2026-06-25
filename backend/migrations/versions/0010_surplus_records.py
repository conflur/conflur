"""finanzas — excedentes (4 fuentes + registro de acción)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-25

Aditiva. surplus_records: excedentes por fuente (ahorro|amortizaciones|
cobros_anticipados|excedente_caja) con registro de la acción decidida. RLS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "surplus_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("action_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_surplus_records_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_surplus_records"),
    )
    op.create_index("ix_surplus_records_tenant_id", "surplus_records", ["tenant_id"])

    op.execute("ALTER TABLE surplus_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE surplus_records FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON surplus_records
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON surplus_records")
    op.execute("ALTER TABLE surplus_records DISABLE ROW LEVEL SECURITY")
    op.drop_table("surplus_records")
