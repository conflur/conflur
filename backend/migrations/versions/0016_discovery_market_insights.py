"""discovery_market_insights — capa de aprendizaje del Agente de Descubrimiento

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-06

Aditiva. Crea tabla discovery_market_insights que almacena síntesis cross-session
generadas por LLM. El campo `narrative` se inyecta en el system prompt del agente
para que las próximas charlas partan del conocimiento acumulado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovery_market_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sessions_count", sa.Integer, nullable=False),
        sa.Column("insights", JSONB, nullable=False),
        sa.Column("narrative", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("discovery_market_insights")
