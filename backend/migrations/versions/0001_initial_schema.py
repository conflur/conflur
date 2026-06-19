"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-19

Modelo de tenancy de primera clase:
  tenants (consultorio) ← memberships → users (identidad global)
  recursos clínicos/operativos cuelgan del tenant (tenant_id = tenants.id)
  patient_access resuelve la visibilidad clínica DENTRO del consultorio
  RLS sobre tenant_id aísla ENTRE consultorios
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tenants (consultorio) ---
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="individual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tenants"),
    )

    # --- users (identidad global) ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- memberships (user ↔ tenant + rol) ---
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),  # owner | professional | assistant
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_memberships_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_memberships_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_id_user_id"),
    )
    op.create_index("ix_memberships_tenant_id", "memberships", ["tenant_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])

    # --- user_passkeys (WebAuthn por dispositivo) ---
    op.create_table(
        "user_passkeys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_id", sa.LargeBinary(), nullable=False),
        sa.Column("public_key", sa.LargeBinary(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_passkeys_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_passkeys"),
        sa.UniqueConstraint("credential_id", name="uq_user_passkeys_credential_id"),
    )
    op.create_index("ix_user_passkeys_user_id", "user_passkeys", ["user_id"])

    # --- patients ---
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("treatment_start_date", sa.Date(), nullable=True),
        sa.Column("session_fee", sa.Float(), nullable=True),
        sa.Column("fee_currency", sa.String(10), nullable=True),
        sa.Column("payment_method", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_patients_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
    )
    op.create_index("ix_patients_tenant_id", "patients", ["tenant_id"])

    # --- patient_access (acceso clínico dentro del consultorio) ---
    op.create_table(
        "patient_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_type", sa.String(50), nullable=False),  # primary | shared
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_patient_access_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_patient_access_patient_id_patients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_user_id"], ["users.id"], name="fk_patient_access_professional_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], name="fk_patient_access_granted_by_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_patient_access"),
        sa.UniqueConstraint("patient_id", "professional_user_id", name="uq_patient_access_patient_id_professional_user_id"),
    )
    op.create_index("ix_patient_access_tenant_id", "patient_access", ["tenant_id"])
    op.create_index("ix_patient_access_patient_id", "patient_access", ["patient_id"])
    op.create_index("ix_patient_access_professional_user_id", "patient_access", ["professional_user_id"])

    # --- appointments ---
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("professional_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(50), nullable=False, server_default="scheduled"),
        sa.Column("session_number", sa.Integer(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_appointments_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["professional_user_id"], ["users.id"], name="fk_appointments_professional_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_appointments_patient_id_patients", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
    )
    op.create_index("ix_appointments_tenant_id", "appointments", ["tenant_id"])
    op.create_index("ix_appointments_professional_user_id", "appointments", ["professional_user_id"])
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_starts_at", "appointments", ["starts_at"])

    # --- clinical_notes ---
    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("input_bullets", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("template_type", sa.String(100), nullable=False, server_default="psychology_session"),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_clinical_notes_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], name="fk_clinical_notes_patient_id_patients", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], name="fk_clinical_notes_author_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], name="fk_clinical_notes_appointment_id_appointments", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_clinical_notes"),
    )
    op.create_index("ix_clinical_notes_tenant_id", "clinical_notes", ["tenant_id"])
    op.create_index("ix_clinical_notes_patient_id", "clinical_notes", ["patient_id"])
    op.create_index("ix_clinical_notes_author_user_id", "clinical_notes", ["author_user_id"])
    op.create_index("ix_clinical_notes_appointment_id", "clinical_notes", ["appointment_id"])

    # --- payments ---
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
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_index("ix_payments_patient_id", "payments", ["patient_id"])
    op.create_index("ix_payments_appointment_id", "payments", ["appointment_id"])

    # --- subscriptions (del consultorio) ---
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="freemium"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("provider_subscription_id", sa.String(255), nullable=True),
        sa.Column("provider_customer_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_subscriptions_tenant_id_tenants", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint("provider_subscription_id", name="uq_subscriptions_provider_subscription_id"),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])

    # --- note_feedback ---
    op.create_table(
        "note_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("edit_distance", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rating BETWEEN 1 AND 3", name="ck_note_feedback_rating"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_note_feedback_tenant_id_tenants", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["clinical_notes.id"], name="fk_note_feedback_note_id_clinical_notes", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_note_feedback"),
    )
    op.create_index("ix_note_feedback_tenant_id", "note_feedback", ["tenant_id"])
    op.create_index("ix_note_feedback_note_id", "note_feedback", ["note_id"])

    # ------------------------------------------------------------------ #
    # RLS — aislamiento ENTRE consultorios (tenant_id = tenants.id)
    # ------------------------------------------------------------------ #
    # app.tenant_id se setea al inicio de cada request (ver db.set_tenant()).
    # El aislamiento DENTRO del consultorio (visibilidad clínica por
    # patient_access) se aplica en la capa de autorización de la app; app.user_id
    # queda disponible en la sesión para una política RLS más fina a futuro.
    # Tablas con aislamiento estricto por tenant activo.
    tenant_only_tables = [
        "patients",
        "patient_access",
        "appointments",
        "clinical_notes",
        "payments",
        "subscriptions",
        "note_feedback",
    ]
    # NULLIF(..., '') porque current_setting(name, true) devuelve '' (no NULL)
    # cuando el GUC no fue seteado; ''::uuid lanzaría error. Con NULLIF, sin
    # tenant activo la comparación da NULL → cero filas (falla cerrado).
    for table in tenant_only_tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            """
        )

    # memberships: además del tenant activo, un usuario SIEMPRE puede ver sus
    # propias membresías. Esto resuelve el bootstrap de login (user → tenant) sin
    # romper el aislamiento: estando en el tenant A no se ven membresías del B.
    # WITH CHECK exige tenant activo (alta de miembros solo dentro del tenant).
    op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON memberships
        USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            OR user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
        )
        WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """
    )

    # Superuser/service role bypasses RLS — el connection role de la app usa un
    # rol sin BYPASSRLS (conflur_app).


def downgrade() -> None:
    rls_tables = [
        "memberships",
        "patients",
        "patient_access",
        "appointments",
        "clinical_notes",
        "payments",
        "subscriptions",
        "note_feedback",
    ]
    for table in rls_tables:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("note_feedback")
    op.drop_table("subscriptions")
    op.drop_table("payments")
    op.drop_table("clinical_notes")
    op.drop_table("appointments")
    op.drop_table("patient_access")
    op.drop_table("patients")
    op.drop_table("user_passkeys")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("tenants")
