"""stripe webhook event ids for idempotency

Revision ID: 005_stripe_webhook_events
Revises: 004_sessions_audit
Create Date: 2026-04-06

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005_stripe_webhook_events"
down_revision: Union[str, None] = "004_sessions_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stripe_webhook_events_event_id"), "stripe_webhook_events", ["event_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_stripe_webhook_events_event_id"), table_name="stripe_webhook_events")
    op.drop_table("stripe_webhook_events")
