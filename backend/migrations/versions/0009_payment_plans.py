"""finanzas — planes de cuotas (paciente / proveedor) + cuotas

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-25

Aditiva. payment_plans (financiación en cuotas, dirección patient|provider) +
payment_installments (cuotas con vencimiento y estado). Cierre del plan al
pagarse la última cuota se maneja en la app. RLS en ambas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
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
        "payment_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("counterparty_name", sa.String(length=255), nullable=True),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("installments_count", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_payment_plans_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_payment_plans_patient_id_patients", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_plans"),
    )
    op.create_index("ix_payment_plans_tenant_id", "payment_plans", ["tenant_id"])

    op.create_table(
        "payment_installments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_payment_installments_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["payment_plans.id"], name="fk_payment_installments_plan_id_payment_plans", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_payment_installments"),
        sa.UniqueConstraint("plan_id", "number", name="uq_payment_installments_plan_id_number"),
    )
    op.create_index("ix_payment_installments_tenant_id", "payment_installments", ["tenant_id"])
    op.create_index("ix_payment_installments_plan_id", "payment_installments", ["plan_id"])

    _enable_rls("payment_plans")
    _enable_rls("payment_installments")


def downgrade() -> None:
    for t in ("payment_installments", "payment_plans"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
    op.drop_table("payment_installments")
    op.drop_table("payment_plans")
