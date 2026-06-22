"""specialties + session_types + tenant.specialty_code (verticales)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-22

Aditiva sobre 0001 (ya hay datos en prod). Agrega:
- specialties (catálogo global de verticales, con ficha_schema JSONB)
- session_types (prestaciones del tenant, RLS)
- tenants.specialty_code (FK a specialties)
- seed de la especialidad 'psicologia' + set de tenants existentes a psicologia
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from specialties.ficha_schema import SEED_SPECIALTIES

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- specialties (catálogo global, sin RLS) ---
    op.create_table(
        "specialties",
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("ficha_schema", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_specialties"),
    )

    # --- session_types (prestaciones del tenant, RLS) ---
    op.create_table(
        "session_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty_code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("base_price", sa.Numeric(15, 2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_session_types_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["specialty_code"], ["specialties.code"], name="fk_session_types_specialty_code_specialties", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_session_types"),
    )
    op.create_index("ix_session_types_tenant_id", "session_types", ["tenant_id"])

    # --- tenants.specialty_code ---
    op.add_column("tenants", sa.Column("specialty_code", sa.String(50), nullable=True))
    op.create_foreign_key(
        "fk_tenants_specialty_code_specialties", "tenants", "specialties",
        ["specialty_code"], ["code"], ondelete="RESTRICT",
    )

    # --- RLS en session_types (igual patrón que el resto) ---
    op.execute("ALTER TABLE session_types ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE session_types FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON session_types
        USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )

    # --- seed de especialidades ---
    for code, data in SEED_SPECIALTIES.items():
        op.execute(
            sa.text(
                "INSERT INTO specialties (code, name, ficha_schema, is_active) "
                "VALUES (:c, :n, CAST(:s AS jsonb), true) ON CONFLICT (code) DO NOTHING"
            ).bindparams(c=code, n=data["name"], s=json.dumps(data["ficha_schema"]))
        )

    # Tenants existentes (cuentas de prueba) → psicologia por default.
    op.execute("UPDATE tenants SET specialty_code = 'psicologia' WHERE specialty_code IS NULL")


def downgrade() -> None:
    op.drop_constraint("fk_tenants_specialty_code_specialties", "tenants", type_="foreignkey")
    op.drop_column("tenants", "specialty_code")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON session_types")
    op.execute("ALTER TABLE session_types DISABLE ROW LEVEL SECURITY")
    op.drop_table("session_types")
    op.drop_table("specialties")
