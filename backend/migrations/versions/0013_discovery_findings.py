"""descubrimiento — hallazgos de charlas del Agente de Descubrimiento

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-01

Aditiva. discovery_findings: hallazgos estructurados (JSONB) + transcript de cada
charla del Agente de Descubrimiento. Datos de instancia, aislados por tenant. RLS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovery_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referidor", sa.String(length=255), nullable=True),
        sa.Column("findings", postgresql.JSONB(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("rol", sa.String(length=40), nullable=True),
        sa.Column("interes", sa.Boolean(), nullable=True),
        sa.Column("contacto", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_discovery_findings_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_findings"),
    )
    op.create_index("ix_discovery_findings_tenant_id", "discovery_findings", ["tenant_id"])

    op.execute("ALTER TABLE discovery_findings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE discovery_findings FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON discovery_findings
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON discovery_findings")
    op.execute("ALTER TABLE discovery_findings DISABLE ROW LEVEL SECURITY")
    op.drop_table("discovery_findings")
