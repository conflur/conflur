"""finanzas — ingresos (devengado) + cobros (percibido); drop payments legacy

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-23

Crea income_records (devengado) y collection_records (percibido) con RLS.
Elimina la tabla payments legacy (placeholder del scaffold, sin uso, superado
por el modelo devengado/percibido).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
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
    # --- drop payments legacy (RLS policy + tabla) ---
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON payments")
    op.drop_table("payments")

    # --- income_records (devengado) ---
    op.create_table(
        "income_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("professional_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_income_records_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_income_records_patient_id_patients", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_user_id"], ["users.id"], name="fk_income_records_professional_user_id_users", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_type_id"], ["session_types.id"], name="fk_income_records_session_type_id_session_types", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], name="fk_income_records_appointment_id_appointments", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_income_records"),
    )
    op.create_index("ix_income_records_tenant_id", "income_records", ["tenant_id"])
    op.create_index("ix_income_records_fecha", "income_records", ["fecha"])
    op.create_index("ix_income_records_patient_id", "income_records", ["patient_id"])

    # --- collection_records (percibido) ---
    op.create_table(
        "collection_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("income_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_collection_records_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_collection_records_patient_id_patients", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["income_record_id"], ["income_records.id"], name="fk_collection_records_income_record_id_income_records", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_collection_records"),
    )
    op.create_index("ix_collection_records_tenant_id", "collection_records", ["tenant_id"])
    op.create_index("ix_collection_records_fecha", "collection_records", ["fecha"])
    op.create_index("ix_collection_records_patient_id", "collection_records", ["patient_id"])

    for t in ("income_records", "collection_records"):
        _enable_rls(t)


def downgrade() -> None:
    for t in ("collection_records", "income_records"):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {t}")
        op.execute(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")
    op.drop_table("collection_records")
    op.drop_table("income_records")

    # recrea payments (estructura original de 0001) por reversibilidad
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(100), nullable=True),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_payments_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_payments_patient_id_patients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], name="fk_payments_appointment_id_appointments", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_payments"),
    )
    op.execute("ALTER TABLE payments ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payments FORCE ROW LEVEL SECURITY")
    op.execute(_RLS.format(t="payments"))
