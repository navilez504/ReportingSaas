"""stripe billing and email reminder tracking

Revision ID: 003_stripe
Revises: 002_subscription
Create Date: 2026-04-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_stripe"
down_revision: Union[str, None] = "002_subscription"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("trial_reminder_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("file_limit_email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_users_stripe_customer_id"), "users", ["stripe_customer_id"], unique=False)
    op.create_index(
        op.f("ix_users_stripe_subscription_id"), "users", ["stripe_subscription_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_users_stripe_subscription_id"), table_name="users")
    op.drop_index(op.f("ix_users_stripe_customer_id"), table_name="users")
    op.drop_column("users", "file_limit_email_sent_at")
    op.drop_column("users", "trial_reminder_email_sent_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
