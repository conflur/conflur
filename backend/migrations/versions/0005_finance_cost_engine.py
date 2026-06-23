"""finanzas — motor de costos: expenses, recurring_expenses, monthly_settings

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-23

Aditiva. Carga por compra (Expense) + costos fijos recurrentes (RecurringExpense)
+ configuración mensual (MonthlySetting). Todas tenant-scoped con RLS.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RLS = """
CREATE POLICY tenant_isolation ON {t}
USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
"""


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(_RLS.format(t=table))


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("monto", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="paid"),
        sa.Column("useful_life_months", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_expenses_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_expenses"),
    )
    op.create_index("ix_expenses_tenant_id", "expenses", ["tenant_id"])
    op.create_index("ix_expenses_fecha", "expenses", ["fecha"])

    op.create_table(
        "recurring_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concepto", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("monthly_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_recurring_expenses_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_recurring_expenses"),
    )
    op.create_index("ix_recurring_expenses_tenant_id", "recurring_expenses", ["tenant_id"])

    op.create_table(
        "monthly_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("planned_hours", sa.Numeric(6, 1), nullable=False),
        sa.Column("opening_cash_balance", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_monthly_settings_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_monthly_settings"),
        sa.UniqueConstraint("tenant_id", "year", "month", name="uq_monthly_settings_tenant_id_year_month"),
    )
    op.create_index("ix_monthly_settings_tenant_id", "monthly_settings", ["tenant_id"])

    for t in ("expenses", "recurring_expenses", "monthly_settings"):
        _enable_rls(t)


def downgrade() -> None:
    for t in ("expenses", "recurring_expenses", "monthly_settings"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
    op.drop_table("monthly_settings")
    op.drop_table("recurring_expenses")
    op.drop_table("expenses")
