"""finanzas — annual_goals (metas anuales de KPIs)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24

Aditiva. Metas anuales por consultorio (margen neto, ticket promedio,
rentabilidad/hora) para comparar vs real en el dashboard. RLS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annual_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("meta_margen_neto", sa.Numeric(5, 2), nullable=True),
        sa.Column("meta_ticket_promedio", sa.Numeric(15, 2), nullable=True),
        sa.Column("meta_rentabilidad_por_hora", sa.Numeric(15, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_annual_goals_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_annual_goals"),
        sa.UniqueConstraint("tenant_id", "year", name="uq_annual_goals_tenant_id_year"),
    )
    op.create_index("ix_annual_goals_tenant_id", "annual_goals", ["tenant_id"])

    op.execute("ALTER TABLE annual_goals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE annual_goals FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON annual_goals
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON annual_goals")
    op.execute("ALTER TABLE annual_goals DISABLE ROW LEVEL SECURITY")
    op.drop_table("annual_goals")
