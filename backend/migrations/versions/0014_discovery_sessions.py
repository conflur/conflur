"""descubrimiento — sesiones del canal web

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-02

Aditiva. discovery_sessions: una sesión de charla = un link compartido con una psicóloga.
Sin RLS: el UUID token (128 bits) es el control de acceso. Tiene FK a tenants y,
al cierre, a discovery_findings.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovery_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("referidor", sa.String(length=255), nullable=True),
        sa.Column("history", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("closed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"],
            name="fk_discovery_sessions_tenant_id_tenants", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["finding_id"], ["discovery_findings.id"],
            name="fk_discovery_sessions_finding_id_discovery_findings",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_discovery_sessions"),
    )
    op.create_index("ix_discovery_sessions_tenant_id", "discovery_sessions", ["tenant_id"])
    # Sin RLS — el UUID token es el control de acceso


def downgrade() -> None:
    op.drop_index("ix_discovery_sessions_tenant_id", table_name="discovery_sessions")
    op.drop_table("discovery_sessions")
