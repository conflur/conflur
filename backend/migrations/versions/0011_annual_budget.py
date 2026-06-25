"""finanzas — presupuesto anual proyectado (inflación compuesta)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-25

Aditiva. annual_budgets: parámetros de proyección anual (ingreso base + growth,
costo base + inflación mensual compuesta). Uno por (tenant, año). RLS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "annual_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("estimated_monthly_income", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("income_growth_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("base_monthly_cost", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("monthly_inflation_pct", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_annual_budgets_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_annual_budgets"),
        sa.UniqueConstraint("tenant_id", "year", name="uq_annual_budgets_tenant_id_year"),
    )
    op.create_index("ix_annual_budgets_tenant_id", "annual_budgets", ["tenant_id"])

    op.execute("ALTER TABLE annual_budgets ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE annual_budgets FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON annual_budgets
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON annual_budgets")
    op.execute("ALTER TABLE annual_budgets DISABLE ROW LEVEL SECURITY")
    op.drop_table("annual_budgets")
